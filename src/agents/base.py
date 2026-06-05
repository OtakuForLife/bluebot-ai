"""Base agent class for the agent system.

This module provides the Agent class that handles tasks using LLM and tools.
"""

import json as _json
import logging
import re as _re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

from src.agents.config import AgentConfig
from src.agents.llm import LLMConfig, LangChainAdapter
from src.agents.llm.factory import ProviderFactory
from src.agents.llm.tool import AgentTool
from src.agents.llm.tools import _FINISH_TOOL_NAME, _create_finish_tool
from src.agents.roles import AgentRole
from src.agents.state import AgentMessage
from src.events import Event, EventHandler, EventType
from src.project.tasks import AgentTask


def _extract_message_text(content: object) -> str:
    """Normalize AIMessage.content to a plain string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
        return "".join(parts)
    return str(content)


def _parse_single_json_tool_call(text: str) -> list[dict]:
    """Parse a lone JSON object tool call: {"name": "finish", "arguments": {}}."""
    clean = _re.sub(r"```[a-z]*\n?", "", text).strip()
    if not clean.startswith("{"):
        return []
    try:
        parsed = _json.loads(clean)
    except (_json.JSONDecodeError, ValueError):
        return []
    if not isinstance(parsed, dict):
        return []
    name = parsed.get("name") or parsed.get("function")
    args = (
        parsed.get("arguments")
        or parsed.get("args")
        or parsed.get("parameters")
        or {}
    )
    if name and isinstance(args, dict):
        return [{"name": str(name), "args": args, "id": str(uuid4())}]
    return []


def _parse_loose_tool_call(text: str, tool_names: set[str]) -> list[dict]:
    """Parse bare tool names some local models emit as plain text (e.g. 'finish')."""
    clean = text.strip().strip('"\'`')
    if not clean:
        return []

    lower = clean.lower()
    if lower in tool_names:
        return [{"name": lower, "args": {}, "id": str(uuid4())}]

    match = _re.match(r"^([A-Za-z_][\w]*)\s*\(\s*\)$", clean)
    if match and match.group(1).lower() in tool_names:
        return [{"name": match.group(1).lower(), "args": {}, "id": str(uuid4())}]

    call_match = _re.match(
        r"^(?:call\s+)?([A-Za-z_][\w]*)\s*\(\s*\)$",
        clean,
        _re.IGNORECASE,
    )
    if call_match and call_match.group(1).lower() in tool_names:
        return [{"name": call_match.group(1).lower(), "args": {}, "id": str(uuid4())}]

    return []


def _parse_text_tool_calls(text: str, tool_names: set[str] | None = None) -> list[dict]:
    """Try to extract tool calls from a text response that contains JSON.

    Some local models (e.g. small Ollama models) output tool calls as JSON
    text instead of using the native function-calling API.  They typically
    produce a JSON array like:

        [ { "name": "create_file", "arguments": { "path": "...", "content": "..." } } ]

    This parser handles that format and returns a list of dicts compatible
    with LangChain's tool_calls structure: {"name": str, "args": dict, "id": str}.
    Returns an empty list if the text does not look like tool calls.
    """
    if not text:
        return []
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    clean = _re.sub(r"```[a-z]*\n?", "", text).strip()
    # Find the outermost [...] block
    match = _re.search(r"\[.*\]", clean, _re.DOTALL)
    if match:
        try:
            parsed = _json.loads(match.group(0))
        except (_json.JSONDecodeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            calls: list[dict] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("function")
                args = (
                    item.get("arguments")
                    or item.get("args")
                    or item.get("parameters")
                    or {}
                )
                if name and isinstance(args, dict):
                    calls.append({"name": name, "args": args, "id": str(uuid4())})
            if calls:
                return calls

    single = _parse_single_json_tool_call(clean)
    if single:
        return single

    if tool_names:
        loose = _parse_loose_tool_call(clean, tool_names)
        if loose:
            return loose

    return []



class AgentStatus(Enum):
    """Enumeration of possible agent states."""
    IDLE = "idle"
    WORKING = "working"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class _ReActResult:
    """Return value of Agent._react_loop — bundles everything the loop produces."""
    messages: list
    tool_results: list[str]
    errors: list[str]
    state_updates: dict  # merged back into AgentMessage by Agent.run()


def to_langchain_tool(agent_tool: AgentTool) -> BaseTool:
    """Helper method to convert custom AgentTool class to Langchain's BaseTool class"""
    return StructuredTool.from_function(
        func=agent_tool.execute,
        name=agent_tool.name,
        description=agent_tool.description,
    )


class Agent:
    """Agent class that handles tasks using LLM and tools.

    This class provides foundational interface and lifecycle management
    for all agents in the system. It can be used directly with
    different AgentRole values.
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        config: Optional[AgentConfig] = None,
    ) -> None:
        """Initialize the agent.

        Args:
            name: Name of the agent.
            role: Role of the agent.
            config: Agent configuration (event_handler, llm_config, etc.).
        """
        config = config or AgentConfig()
        self.id = uuid4()
        self.name = name
        self.system_prompt = config.system_prompt
        self.role = role
        self._status = AgentStatus.STOPPED
        self._current_task: Optional[AgentTask] = None
        self.event_handler = config.event_handler

        self.capabilities: List[str] = config.capabilities
        self.logger = logging.getLogger(f"agent.{name}")

        # Load role knowledge before binding tools so list/read_knowledge are available.
        self.knowledge_dir = Path(config.knowledge_path) if config.knowledge_path else None
        if self.knowledge_dir:
            from src.agents.knowledge import KnowledgeBase
            self.knowledge_base = KnowledgeBase(str(self.knowledge_dir))
        else:
            self.knowledge_base = None

        knowledge_tools: list[AgentTool] = []
        if self.knowledge_base is not None:
            from src.agents.knowledge_tools import create_knowledge_tools
            knowledge_tools = create_knowledge_tools(self.knowledge_base)

        # finish tool is always available — it is the agent's only exit signal.
        self.tools = list(config.tools) + knowledge_tools + [_create_finish_tool()]
        lc_tools = [to_langchain_tool(t) for t in self.tools]
        self.tool_lookup = {t.name: t for t in self.tools}

        # Create LLM provider using ProviderFactory
        self.llm_config = config.llm_config or LLMConfig()
        self.llm_provider = ProviderFactory.create(self.llm_config)
        self.langchain_model = LangChainAdapter(provider=self.llm_provider).bind_tools(
            lc_tools, agent_tools=self.tools
        )

    def set_provider(self, provider: "BaseLLMProvider") -> None:  # type: ignore[name-defined]
        """Swap the LLM provider at runtime.

        Recreates the LangChain model binding so the new provider takes effect
        on the very next run() call.

        Args:
            provider: The new LLM provider to use.
        """
        from src.agents.llm import LangChainAdapter
        lc_tools = [to_langchain_tool(t) for t in self.tools]
        self.llm_provider = provider
        self.langchain_model = LangChainAdapter(provider=provider).bind_tools(
            lc_tools, agent_tools=self.tools
        )
        self.logger.info(
            f"Provider updated to {provider.__class__.__name__} "
            f"(model={getattr(provider.config, 'model', '?')})"
        )

    @property
    def status(self) -> AgentStatus:
        """Get the current status of the agent."""
        return self._status

    @property
    def current_task(self) -> Optional[AgentTask]:
        """Get the task the agent is currently working on."""
        return self._current_task

    def set_current_task(self, task: Optional[AgentTask]) -> None:
        """Set the task the agent is currently working on and emit event.

        Args:
            task: The task being worked on, or None if no task.
        """
        self._current_task = task
        if self.event_handler:
            self.event_handler.emit_event(Event(
                type=EventType.AGENT_CURRENT_TASK_CHANGED,
                payload={
                    "agent_id": str(self.id),
                    "agent_name": self.name,
                    "task": task if task else None,
                },
                timestamp=datetime.now().isoformat()
            ))

    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set the agent status and emit event."""
        old_status = self._status
        self._status = value
        self.logger.info(f"Status changed from {old_status.value} to {value.value}")

        # Emit status changed event if event handler is available
        if self.event_handler:
            self.event_handler.emit_event(Event(
                type=EventType.AGENT_STATUS_CHANGED,
                payload={
                    "agent_id": str(self.id),
                    "agent_name": self.name,
                    "agent_role": self.role.value,
                    "old_status": old_status.value,
                    "new_status": value.value,
                },
                timestamp=datetime.now().isoformat()
            ))
    
    # ── Public entry point ────────────────────────────────────────────────────

    async def run(self, state: AgentMessage) -> AgentMessage:
        """LangGraph node entry point — runs one complete agent turn.

        Sequence:
          1. Emit kanban 'in_progress' event (specialists only).
          2. Build the initial LLM prompt from state.
          3. Run the ReAct loop (LLM → tools → LLM …).
          4. Emit kanban 'review' event (specialists only).
          5. Return the updated state.
        """
        workspace_root: str = state.get("workspace_root", ".")
        task_preview = state.get("task_description", "")[:120].replace("\n", " ")
        self.logger.info(f"Invoked — task: {task_preview}")

        self._emit_task_started(state)
        prompt = self._build_prompt(state)
        result = await self._react_loop(prompt, workspace_root)
        self._emit_task_finished(state)

        agent_state: AgentMessage = {
            **state,
            **result.state_updates,
            "messages": result.messages,
            "tool_results": list(state.get("tool_results", [])) + result.tool_results,
            "last_agent": self.name,
            "errors": list(state.get("errors", [])) + result.errors,
        }
        return agent_state

    # ── Private helpers ───────────────────────────────────────────────────────

    def _emit_task_started(self, state: AgentMessage) -> None:
        """Notify the kanban board that a specialist has started working.

        Only specialist agents (those with capabilities) emit this event.
        Director-type agents (Project Director, Discovery) do not claim tasks
        from the marketplace, so they never emit kanban progress events.
        """
        if self.capabilities and state.get("current_task_id"):
            if self.event_handler:
                self.event_handler.emit_event(Event(
                    type=EventType.TASK_ASSIGNED,
                    payload={
                        "task_id": state["current_task_id"],
                        "agent_name": self.name,
                        "new_state": "in_progress",
                    },
                    timestamp=datetime.now().isoformat(),
                ))

    def _emit_task_finished(self, state: AgentMessage) -> None:
        """Notify the kanban board that a specialist finished and needs review."""
        if self.capabilities and state.get("current_task_id"):
            if self.event_handler:
                self.event_handler.emit_event(Event(
                    type=EventType.TASK_UPDATED,
                    payload={
                        "task_id": state["current_task_id"],
                        "new_state": "review",
                    },
                    timestamp=datetime.now().isoformat(),
                ))

    def _build_prompt(self, state: AgentMessage) -> list:
        """Build the initial LLM prompt messages from the current workflow state."""
        context_parts: list[str] = [
            f"Workspace: {state.get('workspace_root', '.')}",
            f"Task:\n{state['task_description']}",
        ]
        if self.role == AgentRole.DISCOVERY and self.knowledge_base:
            catalog = self.knowledge_base.get_document("studio_deliverables.md")
            if catalog:
                context_parts.append(f"Studio Deliverables Catalog:\n{catalog}")
        elif state.get("direction"):
            context_parts.append(f"Strategic Direction:\n{state['direction']}")
        if self.role == AgentRole.PROJECT_DIRECTOR:
            artifact = state.get("recommended_artifact") or ""
            if artifact:
                context_parts.append(f"Deliverable under review: {artifact}")
            created = state.get("created_files") or []
            if created:
                files = "\n".join(f"- {path}" for path in created)
                context_parts.append(f"Files produced this task:\n{files}")
        if state.get("recommended_artifact"):
            context_parts.append(
                f"Target artifact: {state['recommended_artifact']}"
            )
        if state.get("capability"):
            context_parts.append(f"Capability: {state['capability']}")
        rubric_id = state.get("rubric")
        if rubric_id:
            from src.agents.rubrics import load_rubric
            rubric_body = load_rubric(rubric_id)
            if rubric_body:
                context_parts.append(
                    f"Quality Rubric ({rubric_id}):\n{rubric_body}"
                )
            else:
                context_parts.append(
                    f"Quality rubric: {rubric_id} (guide file not found in knowledge/)"
                )
        if state.get("acceptance_criteria"):
            criteria = "\n".join(f"- {c}" for c in state["acceptance_criteria"])
            context_parts.append(f"Acceptance Criteria:\n{criteria}")
        if state.get("human_review_approved") is not None:
            verdict = "APPROVED" if state["human_review_approved"] else "REJECTED"
            context_parts.append(f"Human Review: {verdict}")
            if state.get("human_review_comment"):
                context_parts.append(f"Review Comment: {state['human_review_comment']}")
        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n\n".join(context_parts)),
        ]

    async def _react_loop(self, prompt: list, workspace_root: str) -> _ReActResult:
        """Run the Reason + Act loop until the agent calls finish().

        Each iteration:
          1. Call the LLM with the accumulated message history.
          2. Execute every tool the LLM requested.
          3. Append tool results to messages and loop.

        The loop exits only when the agent calls the finish() tool.
        The agent is responsible for deciding when its work is done.
        """
        messages: list = []
        tool_results: list[str] = []
        errors: list[str] = []
        iteration = 0
        finished = False
        _MAX_ITERATIONS = 25

        while not finished:
            iteration += 1
            if iteration > _MAX_ITERATIONS:
                self.logger.error(
                    f"ReAct loop exceeded {_MAX_ITERATIONS} iterations — stopping"
                )
                errors.append(f"Exceeded maximum iterations ({_MAX_ITERATIONS})")
                break
            current_prompt = prompt + messages
            self.logger.info(f"Calling LLM (iteration {iteration})...")
            response: AIMessage = await self.langchain_model.ainvoke(current_prompt)
            messages.append(response)
            self.logger.info(f"LLM responded — {len(response.tool_calls)} tool call(s)")

            # Prefer native tool_calls; fall back to JSON embedded in text.
            # If the model produces plain text, log it and feed it back so it
            # can self-correct on the next iteration.
            tool_calls = list(response.tool_calls)
            tool_names = set(self.tool_lookup.keys())
            if not tool_calls:
                text = _extract_message_text(getattr(response, "content", ""))
                tool_calls = _parse_text_tool_calls(text, tool_names)
                if tool_calls:
                    self.logger.info(
                        f"Parsed {len(tool_calls)} text-format tool call(s) "
                        f"from: {text[:80]!r}"
                    )
                elif text:
                    self.logger.warning(
                        f"LLM produced text instead of a tool call: {str(text)[:300]}"
                    )
                    messages.append(HumanMessage(
                        content=(
                            "You must respond with tool calls only — no prose. "
                            "Use the native tool-calling API, not plain text. "
                            "When done, call the finish tool (not the word 'finish')."
                        )
                    ))

            for call in tool_calls:
                tool_name = call["name"]
                args = {**call["args"], "project_root": workspace_root}
                tool = self.tool_lookup.get(tool_name)

                if tool is None:
                    self.logger.warning(f"Unknown tool: {tool_name}")
                    errors.append(f"Unknown tool: {tool_name}")
                    messages.append(ToolMessage(tool_call_id=call["id"],
                                                content=f"Error: unknown tool '{tool_name}'"))
                    continue

                self.logger.info(
                    f"Tool → {tool_name}("
                    f"{', '.join(f'{k}={v!r}' for k, v in args.items() if k != 'project_root')})"
                )
                try:
                    result = tool.execute(args)
                    self.logger.info(f"Tool ← {tool_name}: {str(result)[:200]}")
                    tool_results.append(f"{tool_name}: {result}")
                    messages.append(ToolMessage(tool_call_id=call["id"], content=str(result)))
                    if tool_name == _FINISH_TOOL_NAME:
                        finished = True
                except Exception as exc:
                    self.logger.error(f"Tool {tool_name} failed: {exc}")
                    errors.append(f"Tool {tool_name} failed: {exc}")
                    messages.append(ToolMessage(tool_call_id=call["id"], content=f"Error: {exc}"))

        # Collect any state updates that tools want to push back into AgentMessage
        state_updates: dict = {}
        for tool in self.tools:
            state_updates.update(tool.consume_state_update())

        return _ReActResult(
            messages=messages,
            tool_results=tool_results,
            errors=errors,
            state_updates=state_updates,
        )
