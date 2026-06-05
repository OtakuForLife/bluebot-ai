"""Agent orchestrator — thin lifecycle coordinator over extracted components."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from src.agents.base import Agent, AgentStatus
from src.agents.graph import WorkflowSpec
from src.agents.graph_registry import GraphRegistry
from src.agents.human_review import HumanReviewCoordinator, human_review_node
from src.agents.llm.base_provider import BaseLLMProvider
from src.agents.state import AgentMessage
from src.agents.state_factory import build_producer_reset_state
from src.agents.workflow_runner import WorkflowRunner
from src.events import Event, EventHandler, EventType


class AgentOrchestrator:
    """Coordinates agent lifecycle, graph execution, and human review."""

    def __init__(
        self,
        event_handler: EventHandler,
        nodes: dict[str, Any] | None = None,
        spec: Optional[WorkflowSpec] = None,
        producer_spec: Optional[WorkflowSpec] = None,
        event_driven: bool = False,
        task_dispatch: "TaskDispatchService | None" = None,
    ) -> None:
        self.event_handler = event_handler
        self.nodes: dict[str, Any] = nodes or {}
        self.logger = logging.getLogger(f"{__name__}.AgentOrchestrator")
        self._event_driven = event_driven
        self._system_running = False
        self._task_dispatch = task_dispatch

        self.graph_registry = GraphRegistry(
            self.nodes, spec, producer_spec, event_driven, human_review_node
        )
        self.graph = self.graph_registry.graph
        self.compiled_graph = self.graph_registry.compiled_graph

        self._review = HumanReviewCoordinator(event_handler, self.logger)
        self._runner = WorkflowRunner(
            self.compiled_graph, self._review, self.logger
        )

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._running_tasks: set[asyncio.Task] = set()
        self._base_state: Optional[AgentMessage] = None

    def _agent_instances(self) -> list[Agent]:
        return [v for v in self.nodes.values() if isinstance(v, Agent)]

    async def start_system(self) -> None:
        self.logger.info("Starting autonomous agent system...")
        self._system_running = True
        for agent in self._agent_instances():
            self.logger.info(f"Setting agent {agent.name} status to WORKING")
            agent.status = AgentStatus.WORKING

        agents_list = [a.name for a in self._agent_instances()]
        self.logger.info(f"Emitting AGENTIC_SYSTEM_STARTED with {len(agents_list)} agents")
        self.event_handler.emit_event(Event(
            type=EventType.AGENTIC_SYSTEM_STARTED,
            payload={"agents": agents_list},
            timestamp=datetime.now().isoformat(),
        ))
        self.logger.info("System started successfully")

    async def stop_system(self) -> None:
        self._system_running = False
        for agent in self._agent_instances():
            agent.status = AgentStatus.STOPPED
            agent.set_current_task(None)

        self.event_handler.emit_event(Event(
            type=EventType.AGENTIC_SYSTEM_STOPPED,
            payload={},
            timestamp=datetime.now().isoformat(),
        ))

    def get_agents(self) -> List[Agent]:
        return self._agent_instances()

    def get_base_state(self) -> Optional[AgentMessage]:
        return self._base_state

    def get_task_graph(self, task_type: str) -> Optional[tuple[str, Any]]:
        return self.graph_registry.get_task_graph(task_type)

    def get_producer_graph(self) -> Optional[Any]:
        return self.graph_registry.compiled_producer

    async def run_producer(self, state: AgentMessage) -> None:
        await self._run_producer(state)

    def update_provider(self, provider: BaseLLMProvider) -> None:
        for agent in self._agent_instances():
            agent.set_provider(provider)
        self.logger.info(
            f"Provider updated for {len(self._agent_instances())} agents"
        )

    @property
    def system_running(self) -> bool:
        return self._system_running

    async def run_workflow(
        self,
        initial_state: AgentMessage,
        thread_id: str = "default",
        compiled: Any = None,
    ) -> AgentMessage:
        self._loop = asyncio.get_running_loop()
        self._review.bind_loop(self._loop)
        return await self._runner.run(initial_state, thread_id, compiled)

    def submit_human_review(self, thread_id: str, approved: bool, comment: str) -> None:
        self._review.submit_decision(thread_id, approved, comment)

    def request_task_rework(
        self, task_id: str, comment: str = "", *, rejected_by: str = "Human review"
    ) -> None:
        """Schedule rework for a rejected task (callable from the Qt main thread)."""
        if not self._system_running or self._task_dispatch is None or self._loop is None:
            return

        async def _run() -> None:
            await self._task_dispatch.reopen_for_rework(
                task_id, comment, rejected_by=rejected_by
            )

        asyncio.run_coroutine_threadsafe(_run(), self._loop)

    def complete_task_offline(self, task_id: str, comment: str = "") -> None:
        """Mark a task complete when no workflow thread is active."""
        if not self._system_running or self._task_dispatch is None or self._loop is None:
            return

        async def _run() -> None:
            await self._task_dispatch.complete_task_offline(task_id, comment)

        asyncio.run_coroutine_threadsafe(_run(), self._loop)

    def signal_stop(self) -> None:
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        self.event_handler.cancel_pending()
        if self._loop and self._polling_task and not self._polling_task.done():
            self._loop.call_soon_threadsafe(self._polling_task.cancel)
        if self._loop:
            for task in list(self._running_tasks):
                if not task.done():
                    self._loop.call_soon_threadsafe(task.cancel)
        self.logger.info("Stop signal sent")

    async def _run_producer(self, state: AgentMessage) -> None:
        producer_graph = self.get_producer_graph()
        if producer_graph is None:
            self.logger.warning("No producer graph compiled — skipping producer run")
            return
        thread_id = f"producer-{uuid.uuid4().hex[:8]}"
        try:
            await self.run_workflow(state, thread_id=thread_id, compiled=producer_graph)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.error(f"Producer run failed: {exc}")

    async def start_event_driven(
        self, base_state: AgentMessage, thread_id: str = "default"
    ) -> None:
        loop = asyncio.get_running_loop()
        self._loop = loop
        self._review.bind_loop(loop)
        self._stop_event = asyncio.Event()
        self.event_handler.set_event_loop(loop)
        self._base_state = base_state

        await self.start_system()

        if self._task_dispatch is not None:
            await self._task_dispatch.on_system_start()

        seed = build_producer_reset_state(base_state)
        try:
            await self._run_producer(seed)
        except asyncio.CancelledError:
            self.logger.info("Producer seed run cancelled during startup")

        await self._stop_event.wait()
        await self.stop_system()

    async def run_polling_workflow(
        self,
        initial_state: AgentMessage,
        thread_id: str = "default",
        interval: int = 10,
    ) -> None:
        self._loop = asyncio.get_running_loop()
        self._review.bind_loop(self._loop)
        self._stop_event = asyncio.Event()
        self._polling_task = asyncio.current_task()

        await self._runner.run_polling_loop(
            run_once=lambda state, tid: self.run_workflow(state, tid),
            initial_state=initial_state,
            thread_id=thread_id,
            interval=interval,
            stop_event=self._stop_event,
        )

    async def stream_workflow(self, initial_state: AgentMessage, thread_id: str = "default"):
        async for state in self._runner.stream(initial_state, thread_id):
            yield state

    def get_workflow_state(self, thread_id: str = "default") -> Optional[AgentMessage]:
        return self._runner.get_state(thread_id)
