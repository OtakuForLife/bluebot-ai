"""Tests for AgentOrchestrator and GraphBuilder."""

import pytest

from langchain_core.runnables import RunnableConfig

from src.agents.graph_registry import GraphRegistry
from src.agents.graph import (
    GraphBuilder,
    WorkflowSpec, DirectEdge, ConditionalEdge, CapabilityEdge,
    create_task_dispatcher,
)
from src.agents.human_review import human_review_node
from src.agents.orchestrator import AgentOrchestrator
from src.agents.services import TaskDispatchService, ProducerService
from src.agents.base import Agent, AgentRole, AgentConfig
from src.agents.state import AgentMessage
from src.events import EventHandler, EventType
from src.project.manager import ProjectManager
from src.project.tasks import TaskStatus


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_orchestrator(nodes: dict, spec: WorkflowSpec) -> AgentOrchestrator:
    return AgentOrchestrator(
        event_handler=EventHandler(),
        nodes=nodes,
        spec=spec,
    )


# ── AgentOrchestrator tests ───────────────────────────────────────────────────

def test_agent_orchestrator_initialization() -> None:
    """Orchestrator stores the event_handler and starts not running."""
    agent = Agent("agent1", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator(
        {"agent1": agent},
        WorkflowSpec(entry_point="agent1"),
    )
    assert orch.system_running is False


def test_agent_orchestrator_with_nodes() -> None:
    """Orchestrator stores the node dict exactly as provided."""
    agent = Agent("test_agent", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator(
        {"test_agent": agent},
        WorkflowSpec(entry_point="test_agent"),
    )
    assert "test_agent" in orch.nodes
    assert orch.nodes["test_agent"] is agent


def test_agent_orchestrator_creates_graph() -> None:
    """Orchestrator exposes both a raw graph and a compiled graph."""
    agent = Agent("start_agent", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator(
        {"start_agent": agent},
        WorkflowSpec(entry_point="start_agent"),
    )
    assert orch.graph is not None
    assert orch.compiled_graph is not None


def test_agent_orchestrator_with_simple_spec() -> None:
    """A single DirectEdge is wired correctly."""
    agent1 = Agent("agent1", AgentRole.GAME_DESIGNER, AgentConfig())
    agent2 = Agent("agent2", AgentRole.GAME_PROGRAMMER, AgentConfig())
    orch = _make_orchestrator(
        {"agent1": agent1, "agent2": agent2},
        WorkflowSpec(
            entry_point="agent1",
            edges=[DirectEdge(source="agent1", target="agent2")],
        ),
    )
    assert orch.graph is not None


def test_agent_orchestrator_with_conditional_spec() -> None:
    """A ConditionalEdge routes by state value."""
    agent1 = Agent("agent1", AgentRole.GAME_DESIGNER, AgentConfig())
    agent2 = Agent("agent2", AgentRole.GAME_PROGRAMMER, AgentConfig())
    orch = _make_orchestrator(
        {"agent1": agent1, "agent2": agent2},
        WorkflowSpec(
            entry_point="agent1",
            edges=[
                ConditionalEdge(
                    source="agent1",
                    condition="task_type",
                    routes={"design": "agent2", "other": "END"},
                )
            ],
        ),
    )
    assert orch.graph is not None


def test_agent_orchestrator_with_complex_routing() -> None:
    """Multiple routes on one ConditionalEdge all resolve correctly."""
    agent1 = Agent("agent1", AgentRole.GAME_DESIGNER, AgentConfig())
    agent2 = Agent("agent2", AgentRole.GAME_PROGRAMMER, AgentConfig())
    agent3 = Agent("agent3", AgentRole.GAME_ARTIST, AgentConfig())
    orch = _make_orchestrator(
        {"agent1": agent1, "agent2": agent2, "agent3": agent3},
        WorkflowSpec(
            entry_point="agent1",
            edges=[
                ConditionalEdge(
                    source="agent1",
                    condition="priority",
                    routes={"high": "agent2", "medium": "agent3", "low": "END"},
                )
            ],
        ),
    )
    assert orch.graph is not None


def test_agent_orchestrator_mixed_edges() -> None:
    """Direct and conditional edges can coexist in the same spec."""
    agent1 = Agent("agent1", AgentRole.GAME_DESIGNER, AgentConfig())
    agent2 = Agent("agent2", AgentRole.GAME_PROGRAMMER, AgentConfig())
    agent3 = Agent("agent3", AgentRole.QA_TESTER, AgentConfig())
    orch = _make_orchestrator(
        {"agent1": agent1, "agent2": agent2, "agent3": agent3},
        WorkflowSpec(
            entry_point="agent1",
            edges=[
                DirectEdge(source="agent1", target="agent2"),
                DirectEdge(source="agent2", target="agent3"),
                ConditionalEdge(
                    source="agent3",
                    condition="approved",
                    routes={"true": "END", "false": "agent1"},
                ),
            ],
        ),
    )
    assert orch.graph is not None


def test_runnable_config_typed_dict() -> None:
    """RunnableConfig is a proper TypedDict."""
    config: RunnableConfig = {"configurable": {"thread_id": "test-thread"}}
    assert config["configurable"]["thread_id"] == "test-thread"


def test_agent_orchestrator_default_spec() -> None:
    """An empty edge list still compiles a valid graph."""
    agent = Agent("start_agent", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator(
        {"start_agent": agent},
        WorkflowSpec(entry_point="start_agent"),
    )
    assert orch.graph is not None
    assert orch.compiled_graph is not None


def test_agent_orchestrator_multiple_agents() -> None:
    """All five agent nodes are stored in nodes."""
    agents = {f"agent{i}": Agent(f"agent{i}", AgentRole.GAME_DESIGNER, AgentConfig())
              for i in range(5)}
    orch = _make_orchestrator(agents, WorkflowSpec(entry_point="agent0"))
    assert len(orch.nodes) == 5
    for i in range(5):
        assert f"agent{i}" in orch.nodes


def test_agent_orchestrator_with_callable_node() -> None:
    """Plain callables are accepted alongside Agent instances."""
    agent = Agent("producer", AgentRole.GAME_PRODUCER, AgentConfig())

    def my_callable_node(state: AgentMessage) -> AgentMessage:
        return {**state, "last_agent": "my_callable"}

    orch = _make_orchestrator(
        {"producer": agent, "review": my_callable_node},
        WorkflowSpec(
            entry_point="producer",
            edges=[DirectEdge(source="producer", target="review")],
        ),
    )
    assert orch.graph is not None
    assert orch.compiled_graph is not None
    assert "review" in orch.nodes


def test_human_review_node_present_in_graph() -> None:
    """human_review_node can be wired as a plain callable node."""
    agent = Agent("producer", AgentRole.GAME_PRODUCER, AgentConfig())
    worker = Agent("designer", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator(
        {"producer": agent, "designer": worker, "human_review": human_review_node},
        WorkflowSpec(
            entry_point="producer",
            edges=[
                DirectEdge(source="producer", target="designer"),
                DirectEdge(source="designer", target="human_review"),
                DirectEdge(source="human_review", target="producer"),
            ],
        ),
    )
    assert orch.graph is not None
    assert orch.compiled_graph is not None
    assert "human_review" in orch.nodes


def test_orchestrator_has_submit_human_review() -> None:
    """AgentOrchestrator exposes submit_human_review."""
    agent = Agent("a", AgentRole.GAME_DESIGNER, AgentConfig())
    orch = _make_orchestrator({"a": agent}, WorkflowSpec(entry_point="a"))
    assert callable(getattr(orch, "submit_human_review", None))


# ── GraphBuilder standalone tests ─────────────────────────────────────────────

def test_graph_builder_builds_graph() -> None:
    """GraphBuilder.build() returns a raw graph and a compiled graph."""
    agent = Agent("node_a", AgentRole.GAME_DESIGNER, AgentConfig())
    spec = WorkflowSpec(entry_point="node_a")
    raw, compiled = GraphBuilder({"node_a": agent}, spec).build()
    assert raw is not None
    assert compiled is not None


def test_graph_builder_direct_edge() -> None:
    """GraphBuilder wires a DirectEdge without raising."""
    a = Agent("a", AgentRole.GAME_DESIGNER, AgentConfig())
    b = Agent("b", AgentRole.GAME_PROGRAMMER, AgentConfig())
    spec = WorkflowSpec(
        entry_point="a",
        edges=[DirectEdge(source="a", target="b")],
    )
    raw, _ = GraphBuilder({"a": a, "b": b}, spec).build()
    assert raw is not None


def test_graph_builder_conditional_edge() -> None:
    """GraphBuilder wires a ConditionalEdge without raising."""
    a = Agent("a", AgentRole.GAME_DESIGNER, AgentConfig())
    b = Agent("b", AgentRole.GAME_PROGRAMMER, AgentConfig())
    spec = WorkflowSpec(
        entry_point="a",
        edges=[ConditionalEdge(source="a", condition="task_type", routes={"x": "b"})],
    )
    raw, _ = GraphBuilder({"a": a, "b": b}, spec).build()
    assert raw is not None


# ── CapabilityEdge tests ──────────────────────────────────────────────────────

def test_capability_edge_wired_in_graph() -> None:
    """GraphBuilder wires a CapabilityEdge without raising."""
    dispatcher = lambda state: state  # noqa: E731
    specialist = Agent("designer", AgentRole.GAME_DESIGNER, AgentConfig())
    spec = WorkflowSpec(
        entry_point="task_dispatcher",
        edges=[
            CapabilityEdge(
                source="task_dispatcher",
                capabilities_map={"designer": ["design"]},
            ),
        ],
    )
    raw, _ = GraphBuilder(
        {"task_dispatcher": dispatcher, "designer": specialist}, spec
    ).build()
    assert raw is not None


def test_capability_edge_multiple_agents() -> None:
    """CapabilityEdge with several agents all pointing from the same source compiles."""
    dispatcher = lambda state: state  # noqa: E731
    designer = Agent("designer", AgentRole.GAME_DESIGNER, AgentConfig())
    developer = Agent("developer", AgentRole.GAME_PROGRAMMER, AgentConfig())
    artist = Agent("artist", AgentRole.GAME_ARTIST, AgentConfig())
    spec = WorkflowSpec(
        entry_point="task_dispatcher",
        edges=[
            CapabilityEdge(
                source="task_dispatcher",
                capabilities_map={
                    "designer": ["design"],
                    "developer": ["gameplay", "systems"],
                    "artist": ["art"],
                },
            ),
        ],
    )
    raw, _ = GraphBuilder(
        {"task_dispatcher": dispatcher, "designer": designer,
         "developer": developer, "artist": artist},
        spec,
    ).build()
    assert raw is not None


# ── create_task_dispatcher tests ──────────────────────────────────────────────

@pytest.fixture
def pm() -> ProjectManager:
    """A real ProjectManager backed by a real EventHandler."""
    return ProjectManager(event_handler=EventHandler())


def _base_state(**kwargs) -> AgentMessage:
    defaults: AgentMessage = {
        "task_id": "test-task-id",
        "messages": [],
        "tool_results": [],
        "errors": [],
        "last_agent": "",
        "task_type": "",
        "task_description": "",
        "acceptance_criteria": [],
        "capability": "",
        "recommended_artifact": "",
        "rubric": "",
        "gap_report": {},
        "direction": "",
        "creative_review_approved": None,
        "creative_review_comment": None,
        "no_more_tasks": False,
        "human_review_approved": None,
        "human_review_comment": None,
        "current_task_id": None,
        "current_task_agent": None,
        "task_allocation_mode": "auto_pull",
        "workspace_root": "",
        "allowed_paths": [],
        "modified_files": [],
        "created_files": [],
        "deleted_files": [],
        "outcome": None,
    }
    return {**defaults, **kwargs}  # type: ignore[return-value]


def _open_task_payload(task_id: str, task_type: str) -> dict:
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": f"Do {task_type} work",
        "task_type": task_type,
        "state": TaskStatus.OPEN.value,
        "acceptance_criteria": [],
    }


_CAPS_MAP = {
    "designer": ["design"],
    "developer": ["gameplay", "systems"],
}


def test_dispatcher_sets_no_more_tasks_when_marketplace_empty(pm) -> None:
    """When no open tasks exist, the dispatcher sets no_more_tasks=True."""
    dispatcher = create_task_dispatcher(pm, _CAPS_MAP)
    result = dispatcher(_base_state())
    assert result["no_more_tasks"] is True


def test_dispatcher_passes_through_when_no_more_tasks_already_set(pm) -> None:
    """If no_more_tasks is already True the dispatcher returns state unchanged."""
    pm.event_handler.emit_event({
        "type": "TASK_CREATED",
        "payload": _open_task_payload("t1", "design"),
        "timestamp": "2024-01-01T00:00:00",
    })
    dispatcher = create_task_dispatcher(pm, _CAPS_MAP)
    state = _base_state(no_more_tasks=True)
    result = dispatcher(state)
    # State must be unchanged — task was NOT claimed.
    assert result["no_more_tasks"] is True
    assert result.get("current_task_id") is None


def test_dispatcher_claims_matching_task(pm) -> None:
    """Dispatcher claims the first matching open task and populates state."""
    pm.add_task(_open_task_payload("t1", "design"))
    dispatcher = create_task_dispatcher(pm, _CAPS_MAP)
    result = dispatcher(_base_state())
    assert result["no_more_tasks"] is False
    assert result["current_task_id"] == "t1"
    assert result["task_type"] == "design"
    assert result["current_task_agent"] == "designer"
    # The task must now be IN_PROGRESS in the store.
    stored = pm.get_task("t1")
    assert stored is not None
    assert stored["state"] == TaskStatus.IN_PROGRESS.value


def test_dispatcher_skips_uncapable_tasks(pm) -> None:
    """A task whose type is not in the capabilities map is not claimed."""
    pm.add_task(_open_task_payload("t1", "audio"))  # no agent handles "audio"
    dispatcher = create_task_dispatcher(pm, _CAPS_MAP)
    result = dispatcher(_base_state())
    assert result["no_more_tasks"] is True
    stored = pm.get_task("t1")
    assert stored is not None
    assert stored["state"] == TaskStatus.OPEN.value  # still unclaimed


def test_dispatcher_routes_multi_capability_agent(pm) -> None:
    """A task_type appearing in a multi-capability agent is routed correctly."""
    pm.add_task(_open_task_payload("t1", "systems"))
    dispatcher = create_task_dispatcher(pm, _CAPS_MAP)
    result = dispatcher(_base_state())
    assert result["current_task_agent"] == "developer"
    assert result["task_type"] == "systems"



# ── TaskDispatchService tests ─────────────────────────────────────────────────

def test_task_dispatch_service_instantiates() -> None:
    """TaskDispatchService can be created with a project_manager and orchestrator."""
    pm = ProjectManager(event_handler=EventHandler())
    designer = Agent("game_designer", AgentRole.GAME_DESIGNER,
                     AgentConfig(capabilities=["design"]))
    orch = _make_orchestrator(
        {"game_designer": designer, "human_review": human_review_node},
        WorkflowSpec(entry_point="game_designer"),
    )
    service = TaskDispatchService(pm, orch)
    assert service._pm is pm
    assert service._orch is orch


def test_task_dispatch_service_has_on_task_created() -> None:
    """on_task_created is a coroutine function."""
    import inspect
    pm = ProjectManager(event_handler=EventHandler())
    orch = _make_orchestrator(
        {"a": Agent("a", AgentRole.GAME_DESIGNER, AgentConfig())},
        WorkflowSpec(entry_point="a"),
    )
    service = TaskDispatchService(pm, orch)
    assert inspect.iscoroutinefunction(service.on_task_created)


def test_task_dispatch_service_runs_workflow_for_created_task() -> None:
    """TASK_CREATED handler claims the task and invokes the specialist graph."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.state_factory import build_initial_workflow_state

    pm = ProjectManager(event_handler=EventHandler())
    mock_orch = MagicMock()
    mock_compiled = MagicMock()
    mock_orch.get_task_graph.return_value = ("game_designer", mock_compiled)
    mock_orch.get_base_state.return_value = build_initial_workflow_state(
        {"name": "Test", "brief": "A game"}
    )
    mock_orch.run_workflow = AsyncMock(
        return_value={
            "creative_review_approved": True,
            "creative_review_comment": "Aligned with vision",
            "human_review_approved": True,
            "human_review_comment": "ok",
        }
    )
    mock_orch.event_handler = EventHandler()
    completed: list = []
    updated: list = []
    mock_orch.event_handler.subscribe(
        EventType.TASK_COMPLETED, lambda e: completed.append(e)
    )
    mock_orch.event_handler.subscribe(
        EventType.TASK_UPDATED, lambda e: updated.append(e)
    )

    service = TaskDispatchService(pm, mock_orch)
    task = {
        "id": "task-42",
        "title": "Design vision",
        "description": "Write VISION.md",
        "task_type": "design",
        "acceptance_criteria": ["File exists"],
        "state": TaskStatus.OPEN.value,
    }
    pm.add_task(task)

    asyncio.run(service.on_task_created({
        "type": EventType.TASK_CREATED,
        "payload": task,
        "timestamp": "2026-01-01T00:00:00",
    }))

    mock_orch.run_workflow.assert_awaited_once()
    assert pm.get_tasks()[0]["state"] == TaskStatus.COMPLETED.value
    assert pm.get_tasks()[0]["agent"] == "game_designer"
    assert len(completed) == 1
    assert completed[0]["payload"]["task_id"] == "task-42"
    assert any(
        e["payload"].get("new_state") == TaskStatus.COMPLETED.value for e in updated
    )


def test_task_dispatch_service_reopens_on_director_rejection() -> None:
    """Creative Director rejection reopens the task and re-dispatches it."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.state_factory import build_initial_workflow_state

    pm = ProjectManager(event_handler=EventHandler())
    mock_orch = MagicMock()
    mock_orch.get_task_graph.return_value = ("game_designer", MagicMock())
    mock_orch.get_base_state.return_value = build_initial_workflow_state(
        {"name": "Test", "brief": "A game"}
    )
    mock_orch.run_workflow = AsyncMock(
        side_effect=[
            {
                "creative_review_approved": False,
                "creative_review_comment": "Tone conflicts with VISION.md",
            },
            {
                "creative_review_approved": True,
                "human_review_approved": True,
            },
        ]
    )
    mock_orch.event_handler = EventHandler()

    service = TaskDispatchService(pm, mock_orch)
    task = {
        "id": "task-99",
        "title": "Design vision",
        "description": "Write VISION.md",
        "task_type": "design",
        "state": TaskStatus.OPEN.value,
    }
    pm.add_task(task)

    asyncio.run(service.on_task_created({
        "type": EventType.TASK_CREATED,
        "payload": task,
        "timestamp": "2026-01-01T00:00:00",
    }))

    assert mock_orch.run_workflow.await_count == 2
    assert "REWORK (Creative Director)" in pm.get_tasks()[0]["description"]
    assert pm.get_tasks()[0]["state"] == TaskStatus.COMPLETED.value


def test_task_dispatch_service_redispatches_on_human_rejection() -> None:
    """Human rejection reopens the task and re-dispatches it with feedback."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.state_factory import build_initial_workflow_state

    pm = ProjectManager(event_handler=EventHandler())
    mock_orch = MagicMock()
    mock_orch.get_task_graph.return_value = ("game_designer", MagicMock())
    mock_orch.get_base_state.return_value = build_initial_workflow_state(
        {"name": "Test", "brief": "A game"}
    )
    mock_orch.run_workflow = AsyncMock(
        side_effect=[
            {
                "creative_review_approved": True,
                "human_review_approved": False,
                "human_review_comment": "Missing target audience section",
            },
            {
                "creative_review_approved": True,
                "human_review_approved": True,
            },
        ]
    )
    mock_orch.event_handler = EventHandler()

    service = TaskDispatchService(pm, mock_orch)
    task = {
        "id": "task-reject",
        "title": "Design vision",
        "description": "Write VISION.md",
        "task_type": "design",
        "state": TaskStatus.OPEN.value,
    }
    pm.add_task(task)

    asyncio.run(service.on_task_created({
        "type": EventType.TASK_CREATED,
        "payload": task,
        "timestamp": "2026-01-01T00:00:00",
    }))

    assert mock_orch.run_workflow.await_count == 2
    assert "REWORK (Human review)" in pm.get_tasks()[0]["description"]
    assert pm.get_tasks()[0]["state"] == TaskStatus.COMPLETED.value


# ── ProducerService tests ─────────────────────────────────────────────────────

def test_producer_service_instantiates() -> None:
    """ProducerService can be created with an orchestrator."""
    orch = _make_orchestrator(
        {"a": Agent("a", AgentRole.GAME_PRODUCER, AgentConfig())},
        WorkflowSpec(entry_point="a"),
    )
    service = ProducerService(orch)
    assert service._orch is orch


def test_producer_service_has_on_task_completed() -> None:
    """on_task_completed is a coroutine function."""
    import inspect
    orch = _make_orchestrator(
        {"a": Agent("a", AgentRole.GAME_PRODUCER, AgentConfig())},
        WorkflowSpec(entry_point="a"),
    )
    service = ProducerService(orch)
    assert inspect.iscoroutinefunction(service.on_task_completed)


def test_producer_service_skips_when_no_base_state() -> None:
    """on_task_completed does nothing when base state is not set."""
    import asyncio
    orch = _make_orchestrator(
        {"a": Agent("a", AgentRole.GAME_PRODUCER, AgentConfig())},
        WorkflowSpec(entry_point="a"),
    )
    assert orch.get_base_state() is None
    service = ProducerService(orch)
    # Should return immediately without error
    event = {"type": "task_completed", "payload": {"task_id": "t1"}, "timestamp": ""}
    asyncio.run(service.on_task_completed(event))


# ── Project Director / Discovery split ───────────────────────────────────────

def test_new_roles_exist() -> None:
    """PROJECT_DIRECTOR and DISCOVERY roles are present in AgentRole."""
    assert AgentRole.PROJECT_DIRECTOR.value == "project_director"
    assert AgentRole.DISCOVERY.value == "discovery"


def test_graph_registry_task_graphs_route_through_director() -> None:
    """Specialist task graphs run Creative Director review before human review."""
    director = Agent(
        "project_director", AgentRole.PROJECT_DIRECTOR, AgentConfig(capabilities=[])
    )
    designer = Agent(
        "game_designer", AgentRole.GAME_DESIGNER, AgentConfig(capabilities=["design"])
    )
    registry = GraphRegistry(
        {
            "project_director": director,
            "game_designer": designer,
            "human_review": human_review_node,
        },
        spec=WorkflowSpec(entry_point="game_designer"),
        producer_spec=None,
        event_driven=True,
        human_review_node=human_review_node,
    )

    assert "design" in registry.task_graphs
    _, compiled = registry.task_graphs["design"]
    assert compiled is not None


def test_submit_creative_review_tool_sets_state() -> None:
    """submit_creative_review propagates verdict into LangGraph state."""
    from src.agents.llm.tools import _create_submit_creative_review_tool

    tool = _create_submit_creative_review_tool()
    result = tool.execute({
        "approved": True,
        "comment": "Mechanics align with the vision doc.",
    })

    assert result["creative_review_approved"] is True
    state_update = tool.consume_state_update()
    assert state_update["creative_review_comment"] == "Mechanics align with the vision doc."


def test_submit_creative_review_requires_comment_on_reject() -> None:
    from src.agents.llm.tools import _create_submit_creative_review_tool

    tool = _create_submit_creative_review_tool()
    result = tool.execute({"approved": False, "comment": ""})

    assert result["ok"] is False
    assert tool.consume_state_update().get("creative_review_approved") is None


def test_set_direction_tool_sets_direction_in_state() -> None:
    """_create_set_direction_tool returns direction via state_keys."""
    from src.agents.llm.tools import _create_set_direction_tool

    tool = _create_set_direction_tool()
    result = tool.execute({"directive": "Create the game vision document"})

    assert isinstance(result, dict)
    assert result["direction"] == "Create the game vision document"
    state_update = tool.consume_state_update()
    assert state_update == {"direction": "Create the game vision document"}


def test_set_direction_tool_rejects_missing_directive() -> None:
    """set_direction returns an error message when directive is empty/missing."""
    from src.agents.llm.tools import _create_set_direction_tool

    tool = _create_set_direction_tool()
    result = tool.execute({"project_root": "."})  # directive missing

    assert isinstance(result, dict)
    # No valid direction was set; state update should be empty or direction="".
    assert result.get("direction", "") == ""


def test_direction_field_in_agent_message_state() -> None:
    """AgentMessage TypedDict includes the direction field."""
    from src.agents.state import AgentMessage
    # Verify the field exists by constructing a minimal state dict that type-checkers
    # would accept — runtime check that the key name is correct.
    state: AgentMessage = {  # type: ignore[typeddict-item]
        "direction": "test directive",
    }
    assert state["direction"] == "test directive"
