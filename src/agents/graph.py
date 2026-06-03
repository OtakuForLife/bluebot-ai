"""Workflow graph specification and LangGraph construction."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.base import Agent
from src.agents.state import AgentMessage



# ── Workflow specification types ─────────────────────────────────────────────

@dataclass
class DirectEdge:
    """A simple point-to-point connection between two graph nodes."""
    source: str
    target: str


@dataclass
class ConditionalEdge:
    """Routes to different nodes based on a value found in the workflow state.

    Example::

        ConditionalEdge(
            source="producer",
            condition="task_type",
            routes={"design": "designer", "gameplay": "programmer"},
        )

    If the state value does not match any route key, the router falls
    through to END so the polling loop can re-trigger on the next tick.
    """
    source: str
    condition: str          # key to look up in AgentMessage
    routes: dict[str, str]  # lowercased state value → node name (or "END")


@dataclass
class CapabilityEdge:
    """Routes from a dispatcher node to specialist agents based on task_type.

    Instead of a hardcoded ``routes`` dict, the router is built dynamically
    from ``capabilities_map`` — adding a new agent with capabilities
    automatically makes it reachable without editing any spec.

    Example::

        CapabilityEdge(
            source="task_dispatcher",
            capabilities_map={
                "game_designer": ["design"],
                "game_developer": ["gameplay", "systems"],
                "game_artist":    ["art"],
            },
        )

    The router reads ``state["task_type"]``, scans the map for the first
    agent whose capability list contains that value, and returns that node
    name. Falls through to END if no match is found or if
    ``state["no_more_tasks"]`` is True.
    """
    source: str
    capabilities_map: dict[str, list[str]]  # node_name → list of task_type strings

def build_capabilities_map(agents: dict) -> dict[str, list[str]]:
    """Extract {node_name: capabilities} from the agent dict.

    Only agents with a non-empty capabilities list are included.
    Director-type agents (project_director, discovery_agent) are excluded
    because they create tasks rather than claiming them.
    """
    return {
        name: agent.capabilities
        for name, agent in agents.items()
        if isinstance(agent, Agent) and agent.capabilities
    }

@dataclass
class WorkflowSpec:
    """Complete declaration of the agent workflow graph.

    Pass an instance to AgentOrchestrator instead of a raw dict.
    """
    entry_point: str
    edges: list[DirectEdge | ConditionalEdge | CapabilityEdge] = field(default_factory=list)


def create_workflow_spec(
    producer_name: str,
    dispatcher_name: str,
    capabilities_map: dict[str, list[str]],
) -> WorkflowSpec:
    """Build the task-pull workflow graph specification.

    Flow
    ----
    Director → task_dispatcher → [CapabilityEdge] → specialist → human_review → Director

    The Director places tasks in the marketplace; the task_dispatcher claims
    the next open task and the CapabilityEdge router sends it to the
    specialist whose capabilities include the task_type — no hardcoded map.
    """
    specialist_names = list(capabilities_map.keys())
    return WorkflowSpec(
        entry_point=producer_name,
        edges=[
            # Director always hands off to the dispatcher after its ReAct loop.
            DirectEdge(source=producer_name, target=dispatcher_name),
            # Dispatcher routes by capability — or goes to END if no open task.
            CapabilityEdge(source=dispatcher_name, capabilities_map=capabilities_map),
            # Every specialist feeds into human_review when done.
            *[DirectEdge(source=name, target="human_review") for name in specialist_names],
            # Human review returns control to the Director for the next iteration.
            DirectEdge(source="human_review", target=producer_name),
        ],
    )


# ── GraphBuilder — pure graph construction, no runtime concerns ───────────────

class GraphBuilder:
    """Builds and compiles a LangGraph StateGraph from nodes and a WorkflowSpec.

    Stateless and synchronous — no asyncio, no events.
    Easily tested in isolation without setting up an event loop.
    """

    def __init__(self, nodes: dict[str, Any], spec: WorkflowSpec) -> None:
        self._nodes = nodes
        self._spec = spec
        self._logger = logging.getLogger(f"{__name__}.GraphBuilder")

    def build(self) -> tuple[StateGraph, Any]:
        """Build and compile the graph. Returns (raw_graph, compiled_graph)."""
        graph = self._build_graph()
        compiled = graph.compile(MemorySaver())
        return graph, compiled

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentMessage)

        for name, node in self._nodes.items():
            fn = node.run if isinstance(node, Agent) else node
            graph.add_node(name, fn)

        graph.set_entry_point(self._spec.entry_point)

        direct = [e for e in self._spec.edges if isinstance(e, DirectEdge)]
        cond_by_source: dict[str, list[ConditionalEdge]] = {}
        cap_by_source: dict[str, list[CapabilityEdge]] = {}
        for edge in self._spec.edges:
            if isinstance(edge, ConditionalEdge):
                cond_by_source.setdefault(edge.source, []).append(edge)
            elif isinstance(edge, CapabilityEdge):
                cap_by_source.setdefault(edge.source, []).append(edge)

        for edge in direct:
            graph.add_edge(edge.source, edge.target)

        for source, cond_edges in cond_by_source.items():
            graph.add_conditional_edges(source, self._make_router(cond_edges, source))

        for source, cap_edges in cap_by_source.items():
            # Merge all capability maps for this source into one router.
            merged: dict[str, list[str]] = {}
            for e in cap_edges:
                merged.update(e.capabilities_map)
            graph.add_conditional_edges(source, self._make_capability_router(merged, source))

        return graph

    def _make_router(self, edges: list[ConditionalEdge], source_name: str):
        """Return a routing function closed over the ConditionalEdge list."""
        logger = self._logger

        def router(state: AgentMessage) -> str:
            for edge in edges:
                value = state.get(edge.condition)
                if value is not None:
                    target = (
                        edge.routes.get(str(value).lower())
                        or edge.routes.get(str(value))
                        or edge.routes.get(value)  # type: ignore[arg-type]
                    )
                    if target is not None:
                        return END if target == "END" else target
            # No condition matched → exit cleanly; polling loop re-triggers.
            logger.debug(f"Router ({source_name}): no condition matched → END")
            return END

        return router

    def _make_capability_router(
        self,
        capabilities_map: dict[str, list[str]],
        source_name: str,
    ):
        """Return a routing function driven by agent capabilities.

        Reads ``state["task_type"]`` and returns the first node name whose
        capability list contains that value. Routes to END if no_more_tasks
        is True or if no agent matches.
        """
        logger = self._logger

        def router(state: AgentMessage) -> str:
            if state.get("no_more_tasks"):
                logger.debug(f"CapabilityRouter ({source_name}): no_more_tasks → END")
                return END
            task_type = str(state.get("task_type", "")).lower()
            for node_name, caps in capabilities_map.items():
                if task_type in [c.lower() for c in caps]:
                    logger.debug(
                        f"CapabilityRouter ({source_name}): "
                        f"task_type='{task_type}' → {node_name}"
                    )
                    return node_name
            logger.debug(
                f"CapabilityRouter ({source_name}): "
                f"no agent for task_type='{task_type}' → END"
            )
            return END

        return router


# ── Task dispatcher factory ───────────────────────────────────────────────────

def create_task_dispatcher(
    project_manager: Any,
    capabilities_map: dict[str, list[str]],
) -> Callable[[AgentMessage], AgentMessage]:
    """Build a LangGraph node that pulls the next open task from the marketplace.

    The returned callable is a plain graph node (same signature as Agent.run).
    It queries ProjectManager for the oldest open task whose task_type matches
    any registered agent capability, claims it atomically, and writes the task
    context into the state so the CapabilityEdge router can send it to the
    correct specialist.

    If the Director has set ``no_more_tasks=True``, the dispatcher passes
    state through unchanged so the CapabilityEdge router exits to END.

    If no matching open task exists (marketplace empty or all tasks already
    claimed), the dispatcher sets ``no_more_tasks=True`` itself so the graph
    exits cleanly and the polling loop can re-evaluate on the next tick.

    Args:
        project_manager:  ProjectManager instance (typed as Any to avoid a
                          circular import — duck-typed at runtime).
        capabilities_map: ``{node_name: [task_type, ...]}`` — the same map
                          used by the accompanying CapabilityEdge so that
                          capability lookups are always consistent.

    Returns:
        A callable ``(state: AgentMessage) -> AgentMessage``.
    """
    # Flatten all capabilities so the marketplace query is a single pass.
    all_capabilities: list[str] = [
        cap for caps in capabilities_map.values() for cap in caps
    ]
    logger = logging.getLogger(f"{__name__}.task_dispatcher")

    def task_dispatcher(state: AgentMessage) -> AgentMessage:
        # Director signalled "nothing left to do" — pass through to END.
        if state.get("no_more_tasks"):
            return state

        task = project_manager.get_next_open_task(all_capabilities)

        if task is None:
            logger.info("task_dispatcher: marketplace empty → no_more_tasks=True")
            return {**state, "no_more_tasks": True}

        task_id: str = task["id"]
        task_type: str = task.get("task_type", "")

        # Find which node handles this task_type.
        agent_name: Optional[str] = next(
            (
                node_name
                for node_name, caps in capabilities_map.items()
                if task_type in caps
            ),
            None,
        )

        claimed = project_manager.claim_task(task_id, agent_name or "")
        if not claimed:
            # Race: task was claimed by something else between query and claim.
            # Exit gracefully; the polling loop will retry.
            logger.warning(
                f"task_dispatcher: could not claim task {task_id} "
                f"(already taken?) → no_more_tasks=True"
            )
            return {**state, "no_more_tasks": True}

        logger.info(
            f"task_dispatcher: claimed task {task_id} "
            f"(type='{task_type}') → {agent_name}"
        )
        return {
            **state,
            "task_type": task_type,
            "task_description": task.get("description", ""),
            "acceptance_criteria": task.get("acceptance_criteria", []),
            "current_task_id": task_id,
            "current_task_agent": agent_name,
            "no_more_tasks": False,
        }

    return task_dispatcher
