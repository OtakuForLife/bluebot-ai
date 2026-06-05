from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from src.agents.llm.base_provider import BaseLLMProvider
from src.agents.orchestrator import AgentOrchestrator
from src.agents.state import AgentMessage
from src.events import EventHandler, EventType, Event
from src.commands import CommandBus, Command


class OrchestratorBridge(QObject):
    """UI-facing facade for AgentOrchestrator lifecycle control."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._orchestrator = orchestrator

    def orchestrator(self) -> AgentOrchestrator:
        return self._orchestrator

    def get_agents(self):
        return self._orchestrator.get_agents()

    @Slot(str, bool, str)
    def submit_human_review(self, thread_id: str, approved: bool, comment: str) -> None:
        self._orchestrator.submit_human_review(thread_id, approved, comment)

    @Slot(str, str)
    def request_task_rework(self, task_id: str, comment: str) -> None:
        self._orchestrator.request_task_rework(task_id, comment)

    @Slot(str, str)
    def complete_task_offline(self, task_id: str, comment: str) -> None:
        self._orchestrator.complete_task_offline(task_id, comment)

    @Slot()
    def signal_stop(self) -> None:
        self._orchestrator.signal_stop()

    @Slot(object)
    def update_provider(self, provider: BaseLLMProvider) -> None:
        self._orchestrator.update_provider(provider)

    async def start_event_driven_async(
        self, base_state: AgentMessage, thread_id: str = "default"
    ) -> None:
        await self._orchestrator.start_event_driven(base_state, thread_id)


class QtEventBridge(QObject):

    task_created = Signal(object)
    task_updated = Signal(object)
    task_completed = Signal(object)
    task_assigned = Signal(object)
    task_failed = Signal(object)
    project_created = Signal(object)
    file_created = Signal(object)
    file_updated = Signal(object)
    file_deleted = Signal(object)
    human_input_requested = Signal(object)
    human_input_received = Signal(object)

    agent_status_changed = Signal(object)
    agent_current_task_changed = Signal(object)
    agent_thinking = Signal(object)
    agent_action = Signal(object)

    agentic_system_started = Signal(object)
    agentic_system_stopped = Signal(object)

    def __init__(self, event_handler: EventHandler):
        super().__init__()
        self.event_handler = event_handler
        self.map = {
            EventType.TASK_CREATED: self.task_created,
            EventType.TASK_UPDATED: self.task_updated,
            EventType.TASK_COMPLETED: self.task_completed,
            EventType.TASK_ASSIGNED: self.task_assigned,
            EventType.TASK_FAILED: self.task_failed,
            EventType.PROJECT_CREATED: self.project_created,
            EventType.PROJECT_FILE_CREATED: self.file_created,
            EventType.PROJECT_FILE_UPDATED: self.file_updated,
            EventType.PROJECT_FILE_DELETED: self.file_deleted,
            EventType.HUMAN_INPUT_REQUESTED: self.human_input_requested,
            EventType.HUMAN_INPUT_RECEIVED: self.human_input_received,
            EventType.AGENT_STATUS_CHANGED: self.agent_status_changed,
            EventType.AGENT_CURRENT_TASK_CHANGED: self.agent_current_task_changed,
            EventType.AGENT_THINKING: self.agent_thinking,
            EventType.AGENT_ACTION: self.agent_action,
            EventType.AGENTIC_SYSTEM_STARTED: self.agentic_system_started,
            EventType.AGENTIC_SYSTEM_STOPPED: self.agentic_system_stopped,
        }

        for event_type, signal in self.map.items():
            self.event_handler.subscribe(event_type, self._make_signal_handler(signal))

    def _make_signal_handler(self, signal):
        def handler(event: Event):
            signal.emit(event)
        return handler

    def handle_event(self, event: Event):
        signal = self.map.get(event["type"])
        if signal:
            signal.emit(event)


class QtCommandBridge(QObject):
    """Dispatches commands and orchestrator lifecycle actions from the UI."""

    def __init__(
        self,
        command_bus: CommandBus,
        orchestrator_bridge: Optional[OrchestratorBridge] = None,
    ):
        super().__init__()
        self.command_bus = command_bus
        self.orchestrator = orchestrator_bridge

    @Slot(object)
    def dispatch(self, command: Command):
        self.command_bus.dispatch(command)

    @Slot(str, bool, str)
    def submit_human_review(self, thread_id: str, approved: bool, comment: str) -> None:
        if self.orchestrator:
            self.orchestrator.submit_human_review(thread_id, approved, comment)

    @Slot(str, str)
    def request_task_rework(self, task_id: str, comment: str) -> None:
        if self.orchestrator:
            self.orchestrator.request_task_rework(task_id, comment)

    @Slot(str, str)
    def complete_task_offline(self, task_id: str, comment: str) -> None:
        if self.orchestrator:
            self.orchestrator.complete_task_offline(task_id, comment)

    @Slot()
    def signal_stop(self) -> None:
        if self.orchestrator:
            self.orchestrator.signal_stop()

    @Slot(object)
    def update_provider(self, provider: BaseLLMProvider) -> None:
        if self.orchestrator:
            self.orchestrator.update_provider(provider)

    def get_agents(self):
        if self.orchestrator:
            return self.orchestrator.get_agents()
        return []

    async def start_event_driven_async(
        self, base_state: AgentMessage, thread_id: str = "default"
    ) -> None:
        if self.orchestrator:
            await self.orchestrator.start_event_driven_async(base_state, thread_id)
