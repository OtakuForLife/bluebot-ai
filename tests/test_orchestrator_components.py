"""Tests for extracted orchestrator components."""

import asyncio
from unittest.mock import MagicMock

import pytest

from src.agents.base import Agent, AgentConfig, AgentRole
from src.agents.graph import DirectEdge, WorkflowSpec
from src.agents.graph_registry import GraphRegistry
from src.agents.human_review import HumanReviewCoordinator, human_review_node
from src.agents.orchestrator import AgentOrchestrator
from src.events import EventHandler, EventType


@pytest.mark.asyncio
async def test_human_review_coordinator_waits_for_ui_decision() -> None:
    """wait_for_decision blocks until submit_decision is called."""
    handler = EventHandler()
    emitted: list = []
    handler.subscribe(EventType.HUMAN_INPUT_REQUESTED, lambda e: emitted.append(e))
    handler.subscribe(EventType.HUMAN_INPUT_RECEIVED, lambda e: emitted.append(e))

    coord = HumanReviewCoordinator(handler, MagicMock())
    loop = asyncio.get_running_loop()
    coord.bind_loop(loop)

    async def submit_after_delay() -> None:
        await asyncio.sleep(0.05)
        coord.submit_decision("thread-1", True, "approved")

    waiter = asyncio.create_task(
        coord.wait_for_decision("thread-1", {"current_task_id": "t1"})
    )
    await submit_after_delay()
    resume = await waiter

    assert resume.resume == {"approved": True, "comment": "approved"}
    assert len(emitted) == 2
    assert emitted[0]["type"] == EventType.HUMAN_INPUT_REQUESTED
    assert emitted[1]["type"] == EventType.HUMAN_INPUT_RECEIVED


@pytest.mark.asyncio
async def test_workflow_runner_waits_on_ainvoke_interrupt_payload() -> None:
    """LangGraph ainvoke returns __interrupt__ instead of raising GraphInterrupt."""
    from typing import Optional, TypedDict

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt

    from src.agents.workflow_runner import WorkflowRunner

    class State(TypedDict):
        approved: Optional[bool]

    def review_node(state: State) -> State:
        response = interrupt({"current_task_id": "task-1"})
        return {**state, "approved": response.get("approved", False)}

    graph = StateGraph(State)
    graph.add_node("review", review_node)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    compiled = graph.compile(checkpointer=MemorySaver())

    handler = EventHandler()
    coord = HumanReviewCoordinator(handler, MagicMock())
    loop = asyncio.get_running_loop()
    coord.bind_loop(loop)
    runner = WorkflowRunner(compiled, coord, MagicMock())

    async def submit_after_delay() -> None:
        await asyncio.sleep(0.05)
        coord.submit_decision("task-1", True, "looks good")

    task = asyncio.create_task(
        runner.run({"approved": None}, thread_id="task-1", compiled=compiled)
    )
    await submit_after_delay()
    result = await task

    assert result["approved"] is True
    assert "__interrupt__" not in result


def test_graph_registry_builds_task_graphs() -> None:
    """GraphRegistry maps specialist capabilities to compiled graphs."""
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    registry = GraphRegistry(
        {"game_designer": designer, "human_review": human_review_node},
        spec=WorkflowSpec(entry_point="game_designer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )

    assert "design" in registry.task_graphs
    agent_name, compiled = registry.task_graphs["design"]
    assert agent_name == "game_designer"
    assert compiled is not None


def test_graph_registry_builds_producer_for_no_capability_agent() -> None:
    """compiled_producer is set when an agent has an empty capabilities list."""
    producer = Agent("game_producer", AgentRole.GAME_PRODUCER, AgentConfig(capabilities=[]))
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    registry = GraphRegistry(
        {"game_producer": producer, "game_designer": designer},
        spec=WorkflowSpec(entry_point="game_producer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )
    assert registry.compiled_producer is not None


def test_graph_registry_producer_none_when_all_agents_have_capabilities() -> None:
    """compiled_producer is None when every agent has capabilities."""
    designer = Agent("designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"]))
    registry = GraphRegistry(
        {"designer": designer},
        spec=WorkflowSpec(entry_point="designer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )
    assert registry.compiled_producer is None


def test_graph_registry_task_graphs_for_multiple_specialists() -> None:
    """task_graphs maps each capability to the correct agent and compiled graph."""
    producer = Agent("game_producer", AgentRole.GAME_PRODUCER, AgentConfig(capabilities=[]))
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    developer = Agent(
        "game_developer", AgentRole.GAME_PROGRAMMER,
        AgentConfig(capabilities=["gameplay", "systems"]),
    )
    registry = GraphRegistry(
        {
            "game_producer": producer,
            "game_designer": designer,
            "game_developer": developer,
            "human_review": human_review_node,
        },
        spec=WorkflowSpec(entry_point="game_producer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )

    assert "design" in registry.task_graphs
    assert "gameplay" in registry.task_graphs
    assert "systems" in registry.task_graphs
    assert registry.get_task_graph("design") == registry.task_graphs["design"]
    agent_name, compiled = registry.task_graphs["design"]
    assert agent_name == "game_designer"
    assert compiled is not None


def test_graph_registry_task_graphs_empty_when_no_specialists() -> None:
    """task_graphs is empty when the only agent has no capabilities."""
    producer = Agent("game_producer", AgentRole.GAME_PRODUCER, AgentConfig(capabilities=[]))
    registry = GraphRegistry(
        {"game_producer": producer},
        spec=WorkflowSpec(entry_point="game_producer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )
    assert registry.task_graphs == {}


def test_graph_registry_uses_producer_spec_for_discovery_only() -> None:
    """producer_spec can run Discovery alone as the producer chain."""
    discovery = Agent("discovery_agent", AgentRole.DISCOVERY, AgentConfig(capabilities=[]))
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    producer_spec = WorkflowSpec(
        entry_point="discovery_agent",
        edges=[],
    )
    registry = GraphRegistry(
        {
            "discovery_agent": discovery,
            "game_designer": designer,
            "human_review": human_review_node,
        },
        spec=WorkflowSpec(entry_point="discovery_agent"),
        producer_spec=producer_spec,
        event_driven=True,
        human_review_node=human_review_node,
    )

    assert registry.compiled_producer is not None
    assert "design" in registry.task_graphs


def test_graph_registry_uses_producer_spec_for_two_agent_chain() -> None:
    """producer_spec builds a Director → Discovery producer chain."""
    director = Agent("project_director", AgentRole.PROJECT_DIRECTOR, AgentConfig(capabilities=[]))
    discovery = Agent("discovery_agent", AgentRole.DISCOVERY, AgentConfig(capabilities=[]))
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    producer_spec = WorkflowSpec(
        entry_point="project_director",
        edges=[DirectEdge(source="project_director", target="discovery_agent")],
    )
    registry = GraphRegistry(
        {
            "project_director": director,
            "discovery_agent": discovery,
            "game_designer": designer,
            "human_review": human_review_node,
        },
        spec=WorkflowSpec(entry_point="project_director"),
        producer_spec=producer_spec,
        event_driven=True,
        human_review_node=human_review_node,
    )

    assert registry.compiled_producer is not None
    assert "design" in registry.task_graphs
    assert registry.get_task_graph("project_director") is None
    assert registry.get_task_graph("discovery") is None


def test_graph_registry_producer_spec_skips_unknown_nodes() -> None:
    """Nodes in producer_spec not present in the nodes dict are ignored."""
    director = Agent("project_director", AgentRole.PROJECT_DIRECTOR, AgentConfig(capabilities=[]))
    producer_spec = WorkflowSpec(
        entry_point="project_director",
        edges=[DirectEdge(source="project_director", target="missing_node")],
    )
    registry = GraphRegistry(
        {"project_director": director},
        spec=WorkflowSpec(entry_point="project_director"),
        producer_spec=producer_spec,
        event_driven=True,
        human_review_node=human_review_node,
    )
    assert registry.compiled_producer is not None


def test_orchestrator_exposes_graph_registry_and_producer_api() -> None:
    """AgentOrchestrator delegates graph lookup to graph_registry."""
    producer = Agent("game_producer", AgentRole.GAME_PRODUCER, AgentConfig(capabilities=[]))
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    orch = AgentOrchestrator(
        event_handler=EventHandler(),
        nodes={"game_producer": producer, "game_designer": designer},
        spec=WorkflowSpec(entry_point="game_producer"),
        event_driven=True,
    )

    assert orch.get_producer_graph() is not None
    entry = orch.get_task_graph("design")
    assert entry is not None
    assert entry[0] == "game_designer"
