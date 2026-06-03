from PySide6.QtCore import QObject, Signal, Slot

from src.events import EventHandler, EventType, Event
from src.commands import CommandBus, Command

class QtEventBridge(QObject):

    task_created = Signal(object)
    task_updated = Signal(object)
    task_completed = Signal(object)
    task_assigned = Signal(object)  # payload: task_id, agent_id, agent_name
    task_failed = Signal(object)  # payload: task_id, agent_id, agent_name, reason
    project_created = Signal(object)
    file_created = Signal(object)
    file_updated = Signal(object)
    file_deleted = Signal(object)
    human_input_requested = Signal(object)
    human_input_received = Signal(object)

    # Agent state and task events
    agent_status_changed = Signal(object)  # payload: agent_id, agent_name, agent_role, old_status, new_status
    agent_current_task_changed = Signal(object)  # payload: agent_id, agent_name, task
    agent_thinking = Signal(object)  # payload: agent_id, agent_name, thought
    agent_action = Signal(object)  # payload: agent_id, agent_name, action, results

    # System control events
    agentic_system_started = Signal(object)  # payload: agents list
    agentic_system_stopped = Signal(object)  # payload: {}

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
            # Agent events
            EventType.AGENT_STATUS_CHANGED: self.agent_status_changed,
            EventType.AGENT_CURRENT_TASK_CHANGED: self.agent_current_task_changed,
            EventType.AGENT_THINKING: self.agent_thinking,
            EventType.AGENT_ACTION: self.agent_action,
            # System control events
            EventType.AGENTIC_SYSTEM_STARTED: self.agentic_system_started,
            EventType.AGENTIC_SYSTEM_STOPPED: self.agentic_system_stopped,
        }

        # Subscribe to all event types
        for event_type, signal in self.map.items():
            self.event_handler.subscribe(event_type, self._make_signal_handler(signal))

    def _make_signal_handler(self, signal):
        """Create a handler function that emits the signal."""
        def handler(event: Event):
            signal.emit(event)
        return handler

    def handle_event(self, event: Event):
        """Handle an event manually (not typically needed with subscription)."""
        signal = self.map.get(event["type"])
        if signal:
            signal.emit(event)

class QtCommandBridge(QObject):

    def __init__(self, command_bus: CommandBus):
        super().__init__()
        self.command_bus = command_bus

    @Slot(object)
    def dispatch(self, command: Command):
        self.command_bus.dispatch(command)
