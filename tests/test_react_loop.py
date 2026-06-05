"""Tests for Agent ReAct loop behavior."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base import Agent, _parse_loose_tool_call, _parse_text_tool_calls
from src.agents.config import AgentConfig
from src.agents.llm import LLMConfig, OllamaProvider, OpenAIProvider
from src.agents.llm.registry import ProviderRegistry
from src.agents.roles import AgentRole
from src.agents.state import AgentMessage
from src.events import EventHandler


@pytest.fixture(autouse=True)
def _register_llm_providers() -> None:
    """Other tests may clear ProviderRegistry; ensure ollama is available."""
    ProviderRegistry.register("ollama", OllamaProvider)
    ProviderRegistry.register("openai", OpenAIProvider)


def _discovery_state(**overrides) -> AgentMessage:
    base: AgentMessage = {
        "task_id": "t1",
        "task_type": "",
        "task_description": "Dark fantasy RPG brief",
        "acceptance_criteria": [],
        "capability": "",
        "recommended_artifact": "",
        "rubric": "",
        "gap_report": {},
        "workspace_root": "/project",
        "allowed_paths": ["/project"],
        "last_agent": None,
        "messages": [],
        "tool_results": [],
        "modified_files": [],
        "created_files": [],
        "deleted_files": [],
        "outcome": None,
        "errors": [],
        "no_more_tasks": False,
        "human_review_approved": None,
        "human_review_comment": None,
        "creative_review_approved": None,
        "creative_review_comment": None,
        "current_task_id": None,
        "current_task_agent": None,
        "task_allocation_mode": "auto_pull",
        "direction": "",
    }
    return {**base, **overrides}  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_react_loop_keeps_system_prompt_on_later_iterations() -> None:
    """Each LLM call must include the original system + task context."""
    from src.agents.llm.tools import _create_finish_tool, _create_list_tasks_tool
    from src.project.manager import ProjectManager

    pm = ProjectManager(event_handler=EventHandler())
    agent = Agent(
        "discovery_agent",
        AgentRole.DISCOVERY,
        AgentConfig(
            event_handler=EventHandler(),
            tools=[_create_list_tasks_tool(pm), _create_finish_tool()],
            system_prompt="Discovery system prompt",
            capabilities=[],
        ),
    )

    captured_prompts: list[list] = []

    async def fake_ainvoke(messages, **kwargs):
        captured_prompts.append(list(messages))
        if len(captured_prompts) == 1:
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "list_tasks",
                    "args": {},
                    "id": "call-1",
                }],
            )
        return AIMessage(
            content="",
            tool_calls=[{
                "name": "finish",
                "args": {"summary": "done"},
                "id": "call-2",
            }],
        )

    agent.langchain_model = MagicMock()
    agent.langchain_model.ainvoke = fake_ainvoke

    state = _discovery_state()
    prompt = agent._build_prompt(state)
    await agent._react_loop(prompt, workspace_root="/project")

    assert len(captured_prompts) == 2
    assert isinstance(captured_prompts[0][0], SystemMessage)
    assert isinstance(captured_prompts[1][0], SystemMessage)
    assert "Discovery system prompt" in captured_prompts[1][0].content
    assert any(
        isinstance(m, HumanMessage) and "Dark fantasy RPG brief" in m.content
        for m in captured_prompts[1]
    )


def test_build_prompt_includes_deliverables_catalog_for_discovery() -> None:
    """Discovery prompt must include the studio deliverables catalog."""
    agent = Agent(
        "discovery_agent",
        AgentRole.DISCOVERY,
        AgentConfig(
            system_prompt="Discovery",
            capabilities=[],
            knowledge_path="discovery/",
        ),
    )
    assert agent.knowledge_base is not None
    prompt = agent._build_prompt(_discovery_state())
    human = next(m for m in prompt if isinstance(m, HumanMessage))
    assert "Studio Deliverables Catalog:" in human.content
    assert "game_vision" in human.content


def test_parse_loose_tool_call_accepts_bare_finish() -> None:
    tools = {"finish", "create_file"}
    calls = _parse_loose_tool_call("finish", tools)
    assert len(calls) == 1
    assert calls[0]["name"] == "finish"


def test_parse_text_tool_calls_accepts_bare_finish() -> None:
    calls = _parse_text_tool_calls("finish", {"finish"})
    assert len(calls) == 1
    assert calls[0]["name"] == "finish"


@pytest.mark.asyncio
async def test_react_loop_treats_bare_finish_text_as_tool_call() -> None:
    """Local models that output the word 'finish' should still exit the loop."""
    from src.agents.llm.tools import _create_finish_tool

    agent = Agent(
        "game_designer",
        AgentRole.GAME_DESIGNER,
        AgentConfig(
            event_handler=EventHandler(),
            tools=[_create_finish_tool()],
            system_prompt="Designer",
            capabilities=["design"],
        ),
    )

    call_count = 0

    async def fake_ainvoke(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return AIMessage(content="", tool_calls=[])
        return AIMessage(content="finish")

    agent.langchain_model = MagicMock()
    agent.langchain_model.ainvoke = fake_ainvoke

    state = _discovery_state()
    prompt = agent._build_prompt(state)
    result = await agent._react_loop(prompt, workspace_root="/project")

    assert call_count == 2
    assert any("finish:" in tr for tr in result.tool_results)
