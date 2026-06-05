"""Compiled LangGraph registry for producer and specialist workflows."""

from typing import Any, Callable, Optional

from src.agents.base import Agent
from src.agents.graph import (
    CapabilityEdge,
    ConditionalEdge,
    DirectEdge,
    GraphBuilder,
    WorkflowSpec,
)
from src.agents.state import AgentMessage


class GraphRegistry:
    """Builds and stores compiled graphs for the agent orchestrator."""

    def __init__(
        self,
        agents: dict[str, Any],
        spec: Optional[WorkflowSpec],
        producer_spec: Optional[WorkflowSpec],
        event_driven: bool,
        human_review_node: Callable[[AgentMessage], AgentMessage],
    ) -> None:
        self.nodes = agents
        self._human_review_node = human_review_node
        self._producer_spec = producer_spec

        if event_driven:
            self.graph = None
            self.compiled_graph = None
        else:
            resolved_spec = spec or WorkflowSpec(entry_point=next(iter(agents), ""))
            self.graph, self.compiled_graph = GraphBuilder(agents, resolved_spec).build()

        self._compiled_producer = self._build_producer_compiled()
        self._task_graphs = self._build_task_graphs()

    @property
    def compiled_producer(self) -> Optional[Any]:
        return self._compiled_producer

    @property
    def task_graphs(self) -> dict[str, tuple[str, Any]]:
        return self._task_graphs

    def get_task_graph(self, task_type: str) -> Optional[tuple[str, Any]]:
        return self._task_graphs.get(task_type.lower())

    def _agent_instances(self) -> list[Agent]:
        return [v for v in self.nodes.values() if isinstance(v, Agent)]

    def _build_producer_compiled(self) -> Optional[Any]:
        if self._producer_spec is not None:
            names_in_spec: set[str] = {self._producer_spec.entry_point}
            for edge in self._producer_spec.edges:
                if isinstance(edge, DirectEdge):
                    names_in_spec.add(edge.source)
                    names_in_spec.add(edge.target)

            known_names = names_in_spec & self.nodes.keys()
            producer_nodes = {name: self.nodes[name] for name in known_names}
            if not producer_nodes:
                return None

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

        producer = next(
            (a for a in self._agent_instances() if not a.capabilities),
            None,
        )
        if producer is None:
            return None
        spec = WorkflowSpec(entry_point=producer.name)
        _, compiled = GraphBuilder({producer.name: producer}, spec).build()
        return compiled

    def _build_task_graphs(self) -> dict[str, tuple[str, Any]]:
        result: dict[str, tuple[str, Any]] = {}
        director = self.nodes.get("project_director")
        for name, agent in self.nodes.items():
            if isinstance(agent, Agent) and agent.capabilities:
                if director is not None:
                    spec = WorkflowSpec(
                        entry_point=name,
                        edges=[
                            DirectEdge(source=name, target="project_director"),
                            ConditionalEdge(
                                source="project_director",
                                condition="creative_review_approved",
                                routes={"true": "human_review", "false": "END"},
                            ),
                        ],
                    )
                    graph_nodes = {
                        name: agent,
                        "project_director": director,
                        "human_review": self._human_review_node,
                    }
                else:
                    spec = WorkflowSpec(
                        entry_point=name,
                        edges=[DirectEdge(source=name, target="human_review")],
                    )
                    graph_nodes = {name: agent, "human_review": self._human_review_node}
                _, compiled = GraphBuilder(graph_nodes, spec).build()
                for cap in agent.capabilities:
                    result[cap.lower()] = (name, compiled)
        return result
