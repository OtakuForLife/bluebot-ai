

# ── AgentOrchestrator — runtime: lifecycle, execution, review, polling ─────────

import asyncio
from datetime import datetime
import logging
from typing import Any, List, Optional, cast
import uuid

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt, Command
from langgraph.errors import GraphInterrupt

from src.agents.base import Agent, AgentStatus
from src.agents.graph import CapabilityEdge, ConditionalEdge, DirectEdge, GraphBuilder, WorkflowSpec
from src.agents.llm.base_provider import BaseLLMProvider
from src.agents.state import AgentMessage
from src.events import Event, EventHandler, EventType


# ── Human review node ─────────────────────────────────────────────────────────

def human_review_node(state: AgentMessage) -> AgentMessage:
    """Human review node — pauses the workflow for user approval.

    Calls LangGraph's interrupt() with a summary of the work done so the UI
    can present it to the user. When the workflow is resumed the node receives
    the reviewer's decision and writes it into the state so the producer can
    use it on the next iteration.
    """
    review_response: dict = interrupt({
        "task_description": state.get("task_description", ""),
        "last_agent": state.get("last_agent"),
        "created_files": state.get("created_files", []),
        "modified_files": state.get("modified_files", []),
        "tool_results": state.get("tool_results", []),
        "current_task_id": state.get("current_task_id"),
    })

    return {
        **state,
        "human_review_approved": review_response.get("approved", False),
        "human_review_comment": review_response.get("comment", ""),
        "last_agent": "human_review",
    }

class AgentOrchestrator:
    """Manages the agent workflow at runtime.

    Responsibilities (each in a clearly labelled section below):
    - System lifecycle  — start / stop all agents
    - Workflow execution — single run or continuous polling loop
    - Human review      — pause / resume the graph via asyncio.Event
    - Provider updates  — hot-swap the LLM at runtime
    """

    def __init__(
        self,
        event_handler: EventHandler,
        nodes: dict[str, Any] = {},
        spec: Optional[WorkflowSpec] = None,
        producer_spec: Optional[WorkflowSpec] = None,
    ) -> None:
        self.event_handler = event_handler
        self._agents: dict[str, Any] = nodes
        self._system_running = False
        self.logger = logging.getLogger(f"{__name__}.AgentOrchestrator")

        # Human-review coordination — keyed by thread_id for concurrent task support
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._review_events: dict[str, asyncio.Event] = {}
        self._pending_reviews: dict[str, dict] = {}

        # Stop coordination
        self._stop_event: Optional[asyncio.Event] = None
        self._polling_task: Optional[asyncio.Task] = None   # polling mode only
        self._running_tasks: set[asyncio.Task] = set()      # event-driven mode

        # Base state stored by start_event_driven; read by TaskDispatchService
        self._base_state: Optional[AgentMessage] = None

        # Optional explicit spec for the producer chain (e.g. Director → Discovery).
        # When provided, _build_producer_compiled uses it instead of auto-detecting
        # the single no-capability agent.
        self._producer_spec: Optional[WorkflowSpec] = producer_spec

        # Build the full polling graph (backward compat)
        resolved_spec = spec or WorkflowSpec(entry_point=next(iter(nodes), ""))
        self.graph, self.compiled_graph = GraphBuilder(nodes, resolved_spec).build()

        # Build per-specialist task graphs for reactive dispatch
        self._compiled_producer: Optional[Any] = self._build_producer_compiled()
        self._task_graphs: dict[str, tuple[str, Any]] = self._build_task_graphs_dict()

    def _agent_instances(self) -> list[Agent]:
        """Return only the Agent instances from the nodes dict (excludes callables)."""
        return [v for v in self._agents.values() if isinstance(v, Agent)]

    def _build_producer_compiled(self) -> Optional[Any]:
        """Compile the producer graph used by start_event_driven.

        When a ``producer_spec`` was supplied at construction time (e.g. a
        Director → Discovery chain), that spec is used directly.  Otherwise
        the method falls back to auto-detecting the single agent that has no
        capabilities and building a one-node graph from it.
        """
        if self._producer_spec is not None:
            # Collect all agent nodes referenced in the explicit producer spec.
            # Only DirectEdge is valid in a producer chain (no capability routing).
            names_in_spec: set[str] = {self._producer_spec.entry_point}
            for edge in self._producer_spec.edges:
                if isinstance(edge, DirectEdge):
                    names_in_spec.add(edge.source)
                    names_in_spec.add(edge.target)

            # Only include nodes that actually exist in the agents dict.
            known_names = names_in_spec & self._agents.keys()
            producer_nodes = {name: self._agents[name] for name in known_names}
            if not producer_nodes:
                return None

            # Strip edges that reference nodes not present in producer_nodes so
            # LangGraph's graph builder doesn't raise for unknown targets.
            valid_edges: list[DirectEdge | ConditionalEdge | CapabilityEdge] = [
                e for e in self._producer_spec.edges
                if isinstance(e, DirectEdge)
                and e.source in known_names
                and e.target in known_names
            ]
            filtered_spec = WorkflowSpec(
                entry_point=self._producer_spec.entry_point,
                edges=valid_edges,
            )
            _, compiled = GraphBuilder(producer_nodes, filtered_spec).build()
            return compiled

        # Fallback: single no-capability agent (original behavior).
        producer = next(
            (a for a in self._agent_instances() if not a.capabilities),
            None,
        )
        if producer is None:
            return None
        spec = WorkflowSpec(entry_point=producer.name)
        _, compiled = GraphBuilder({producer.name: producer}, spec).build()
        return compiled

    def _build_task_graphs_dict(self) -> dict[str, tuple[str, Any]]:
        """Build one compiled graph per specialist (specialist → human_review → END).

        Returns a dict keyed by task_type (lowercased) → (agent_name, compiled_graph).
        """
        result: dict[str, tuple[str, Any]] = {}
        for name, agent in self._agents.items():
            if isinstance(agent, Agent) and agent.capabilities:
                spec = WorkflowSpec(
                    entry_point=name,
                    edges=[DirectEdge(source=name, target="human_review")],
                )
                _, compiled = GraphBuilder(
                    {name: agent, "human_review": human_review_node}, spec
                ).build()
                for cap in agent.capabilities:
                    result[cap.lower()] = (name, compiled)
        return result

    async def start_system(self) -> None:
        """Start the autonomous agent system."""
        self.logger.info("Starting autonomous agent system...")
        self._system_running = True
        for agent in self._agent_instances():
            self.logger.info(f"Setting agent {agent.name} status to WORKING")
            agent.status = AgentStatus.WORKING

        # Emit system started event
        agents_list = [a.name for a in self._agent_instances()]
        self.logger.info(f"Emitting AGENTIC_SYSTEM_STARTED with {len(agents_list)} agents")
        self.event_handler.emit_event(Event(
            type=EventType.AGENTIC_SYSTEM_STARTED,
            payload={"agents": agents_list},
            timestamp=datetime.now().isoformat()
        ))
        self.logger.info("System started successfully")

    async def stop_system(self) -> None:
        """Stop the autonomous agent system."""
        self._system_running = False
        for agent in self._agent_instances():
            agent.status = AgentStatus.STOPPED
            agent.set_current_task(None)

        self.event_handler.emit_event(Event(
            type=EventType.AGENTIC_SYSTEM_STOPPED,
            payload={},
            timestamp=datetime.now().isoformat()
        ))

    def get_agents(self) -> List[Agent]:
        """Get all registered Agent instances (excludes plain callable nodes).

        Returns:
            List of Agent instances only.
        """
        return self._agent_instances()

    def update_provider(self, provider: BaseLLMProvider) -> None:
        """Push a new LLM provider to every Agent in the workflow.

        Called when the user clicks "Apply Configuration" in LLMConfigPanel.
        Plain callable nodes (e.g. human_review_node) are skipped.

        Args:
            provider: The new LLM provider to use for all agents.
        """
        for agent in self._agent_instances():
            agent.set_provider(provider)
        self.logger.info(
            f"Provider updated for {len(self._agent_instances())} agents"
        )

    @property
    def system_running(self) -> bool:
        """Check if the system is currently running."""
        return self._system_running

    async def run_workflow(
        self,
        initial_state: AgentMessage,
        thread_id: str = "default",
        compiled: Any = None,
    ) -> AgentMessage:
        """Run a compiled graph, automatically handling human-review interrupts.

        Loops until the graph reaches END. When a human_review_node calls
        interrupt(), the loop emits HUMAN_INPUT_REQUESTED, waits for
        submit_human_review() to be called from the UI thread, then resumes
        with the reviewer's decision.

        Args:
            initial_state: Initial state to start the workflow.
            thread_id:     Thread ID for checkpointing (also keys the review gate).
            compiled:      Optional compiled graph; defaults to self.compiled_graph.

        Returns:
            Final AgentMessage state after workflow completion.
        """
        self._loop = asyncio.get_running_loop()
        _compiled = compiled if compiled is not None else self.compiled_graph
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        current_input: Any = initial_state

        while True:
            try:
                result = await _compiled.ainvoke(current_input, config)
                return cast(AgentMessage, result)

            except GraphInterrupt as exc:
                # Extract the interrupt value emitted by human_review_node
                interrupts = exc.args[0] if exc.args else []
                interrupt_value: dict = interrupts[0].value if interrupts else {}

                self.logger.info(f"Workflow paused for human review (thread={thread_id})")
                self.event_handler.emit_event(Event(
                    type=EventType.HUMAN_INPUT_REQUESTED,
                    payload={"thread_id": thread_id, **interrupt_value},
                    timestamp=datetime.now().isoformat()
                ))

                # Block until the UI calls submit_human_review() for this thread_id
                review_event = asyncio.Event()
                self._review_events[thread_id] = review_event
                await review_event.wait()
                self._review_events.pop(thread_id, None)

                # Resume the graph with the reviewer's response
                current_input = Command(resume=self._pending_reviews.pop(thread_id, {}))

    def submit_human_review(self, thread_id: str, approved: bool, comment: str) -> None:
        """Submit a human review decision from the UI thread.

        Thread-safe: can be called from the Qt main thread while the workflow
        is running in a background asyncio event loop.

        Args:
            thread_id: The workflow thread_id (for logging/events).
            approved: Whether the reviewer approved the agent's work.
            comment: Reviewer comment visible to the producer on resume.
        """
        self._pending_reviews[thread_id] = {"approved": approved, "comment": comment}

        # Signal the waiting asyncio.Event for this thread from the Qt thread
        if self._loop and thread_id in self._review_events:
            self._loop.call_soon_threadsafe(self._review_events[thread_id].set)

        self.event_handler.emit_event(Event(
            type=EventType.HUMAN_INPUT_RECEIVED,
            payload={"thread_id": thread_id, "approved": approved, "comment": comment},
            timestamp=datetime.now().isoformat()
        ))

    def signal_stop(self) -> None:
        """Signal the system to stop immediately.

        1. Sets the stop event so start_event_driven() / run_polling_workflow() exit.
        2. Cancels in-flight async-subscriber futures (TaskDispatchService tasks, etc.)
           via EventHandler.cancel_pending().
        3. Cancels the polling-mode asyncio.Task if present.
        4. Cancels any explicitly tracked asyncio.Tasks in _running_tasks.

        Thread-safe: called from the Qt main thread.
        """
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        # Cancel in-flight TaskDispatchService / ProducerService futures
        self.event_handler.cancel_pending()
        # Cancel polling-mode task if present
        if self._loop and self._polling_task and not self._polling_task.done():
            self._loop.call_soon_threadsafe(self._polling_task.cancel)
        # Cancel any explicitly tracked tasks (future use)
        if self._loop:
            for task in list(self._running_tasks):
                if not task.done():
                    self._loop.call_soon_threadsafe(task.cancel)
        self.logger.info("Stop signal sent")

    async def _run_producer(self, state: AgentMessage) -> None:
        """Run the producer-only graph once with a fresh thread_id."""
        if self._compiled_producer is None:
            self.logger.warning("No producer graph compiled — skipping producer run")
            return
        thread_id = f"producer-{uuid.uuid4().hex[:8]}"
        try:
            await self.run_workflow(state, thread_id=thread_id,
                                    compiled=self._compiled_producer)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.error(f"Producer run failed: {exc}")

    async def start_event_driven(
        self, base_state: AgentMessage, thread_id: str = "default"
    ) -> None:
        """Start the event-driven (reactive) workflow.

        Steps
        -----
        1. Register this event loop with EventHandler so async subscribers fire.
        2. Start all agents (sets status to WORKING, emits AGENTIC_SYSTEM_STARTED).
        3. Run the Producer once to seed the task marketplace.
        4. Wait for a stop signal — task graphs fire automatically via
           TaskDispatchService as TASK_CREATED events arrive.
        5. Stop all agents on exit.

        Args:
            base_state: Initial AgentMessage containing workspace_root, allowed_paths,
                        task_description (game brief), and other constant fields.
            thread_id:  Not used for routing; kept for API symmetry with run_workflow.
        """
        loop = asyncio.get_running_loop()
        self._loop = loop
        self._stop_event = asyncio.Event()
        self.event_handler.set_event_loop(loop)
        self._base_state = base_state

        await self.start_system()

        # Seed the marketplace — Director analyses the project and Discovery creates tasks
        seed: AgentMessage = {
            **base_state,
            "task_id": str(uuid.uuid4()),
            "messages": [],
            "tool_results": [],
            "created_files": [],
            "modified_files": [],
            "deleted_files": [],
            "errors": [],
            "outcome": None,
            "no_more_tasks": False,
            "human_review_approved": None,
            "human_review_comment": None,
            "current_task_id": None,
            "current_task_agent": None,
            "last_agent": None,
            "direction": "",
        }
        try:
            await self._run_producer(seed)
        except asyncio.CancelledError:
            pass

        # Block here until signal_stop() sets this event
        await self._stop_event.wait()
        await self.stop_system()

    async def run_polling_workflow(
        self,
        initial_state: AgentMessage,
        thread_id: str = "default",
        interval: int = 10,
    ) -> None:
        """Run the Producer in a continuous polling loop.

        Each iteration invokes the full LangGraph workflow (Producer →
        optional specialist → optional human review). After the graph
        reaches END the loop sleeps for *interval* seconds, then runs
        again. The loop exits only when signal_stop() is called from the
        UI thread.

        Args:
            initial_state: Initial workflow state (workspace, brief, etc.).
            thread_id: LangGraph checkpoint thread ID.
            interval: Seconds to wait between Producer checks.
        """
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        # Store the current task so signal_stop() can cancel it immediately
        self._polling_task = asyncio.current_task()

        # Preserve the original game brief so each polling iteration starts
        # with the correct top-level context rather than the last assigned task.
        original_brief: str = initial_state.get("task_description", "")

        state: AgentMessage = initial_state
        iteration = 0

        while not self._stop_event.is_set():
            iteration += 1
            self.logger.info(
                f"Producer polling loop — iteration {iteration} "
                f"(next check in {interval}s after this one finishes)"
            )

            try:
                state = await self.run_workflow(state, thread_id)
            except asyncio.CancelledError:
                self.logger.info("Polling loop cancelled — exiting")
                break
            except Exception as exc:
                self.logger.error(
                    f"Polling iteration {iteration} raised an error: {exc}"
                )

            if self._stop_event.is_set():
                break

            # Reset per-iteration fields.
            # task_description is explicitly restored to the original game brief
            # so the Producer always evaluates the full project goal, not the
            # description of the last task that was assigned.
            state = {
                **state,
                "task_id": str(uuid.uuid4()),
                "task_type": "",
                "task_description": original_brief,
                "last_agent": None,
                "messages": [],
                "tool_results": [],
                "created_files": [],
                "modified_files": [],
                "deleted_files": [],
                "errors": [],
                "outcome": None,
                "human_review_approved": None,
                "human_review_comment": "",
                "current_task_id": None,
                "current_task_agent": None,
            }

            self.logger.info(
                f"Producer polling loop — waiting {interval}s before next check"
            )

            # Sleep for the configured interval, but wake immediately if stop is requested
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=float(interval))
                break  # stop was requested during the sleep
            except asyncio.TimeoutError:
                pass  # normal interval elapsed — continue loop

        self.logger.info("Producer polling loop finished")

    async def stream_workflow(self, initial_state: AgentMessage, thread_id: str = "default"):
        """Stream the agent workflow execution.

        Args:
            initial_state: Initial game state to start the workflow.
            thread_id: Thread ID for checkpointing (default: "default").

        Yields:
            State updates as the workflow progresses.
        """
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        async for state in self.compiled_graph.astream(initial_state, config):
            yield state

    def get_workflow_state(self, thread_id: str = "default") -> Optional[AgentMessage]:
        """Get the current state of a workflow thread.

        Args:
            thread_id: Thread ID to get state for.

        Returns:
            Current game state or None if not found.
        """
        try:
            config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
            state = self.compiled_graph.get_state(config)
            return cast(AgentMessage, state.values) if state else None
        except Exception:
            return None