"""Tests for Qt bridge classes."""

import pytest

from src.events import EventHandler, EventType, Event
from src.commands import CommandBus, CreateTaskCommand
from src.ui.bridge import QtEventBridge, QtCommandBridge


def test_qt_event_bridge_initialization() -> None:
    """Test that QtEventBridge initializes correctly."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    assert bridge.event_handler == event_handler
    assert len(bridge.map) > 0


def test_qt_event_bridge_maps_all_event_types() -> None:
    """Test that QtEventBridge maps all event types to signals."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    # Check that key events are mapped
    assert EventType.TASK_CREATED in bridge.map
    assert EventType.TASK_UPDATED in bridge.map
    assert EventType.TASK_COMPLETED in bridge.map
    assert EventType.PROJECT_CREATED in bridge.map
    assert EventType.PROJECT_FILE_CREATED in bridge.map
    assert EventType.AGENT_STATUS_CHANGED in bridge.map
    assert EventType.AGENT_THINKING in bridge.map
    assert EventType.AGENTIC_SYSTEM_STARTED in bridge.map


def test_qt_event_bridge_emits_signals() -> None:
    """Test that QtEventBridge emits signals for events."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    # Track signal emissions
    emitted_tasks = []

    def on_task_created(event: Event) -> None:
        emitted_tasks.append(event)

    bridge.task_created.connect(on_task_created)

    # Emit an event
    test_task = {
        "id": "test-1",
        "title": "Test Task"
    }
    event_handler.emit_event({
        "type": EventType.TASK_CREATED,
        "payload": test_task
    })

    # Verify signal was emitted
    assert len(emitted_tasks) == 1
    assert emitted_tasks[0]["type"] == EventType.TASK_CREATED
    assert emitted_tasks[0]["payload"] == test_task


def test_qt_command_bridge_initialization() -> None:
    """Test that QtCommandBridge initializes correctly."""
    command_bus = CommandBus()
    bridge = QtCommandBridge(command_bus)

    assert bridge.command_bus == command_bus


def test_qt_command_bridge_dispatch() -> None:
    """Test that QtCommandBridge dispatches commands."""
    command_bus = CommandBus()
    bridge = QtCommandBridge(command_bus)

    # Track dispatched commands
    dispatched_commands = []

    def track_command(command: CreateTaskCommand) -> None:
        dispatched_commands.append(command)

    command_bus.register(CreateTaskCommand, track_command)

    # Dispatch a command
    task_data = {"id": "task-1", "title": "Test"}
    command = CreateTaskCommand(task_data)
    bridge.dispatch(command)

    # Verify command was dispatched
    assert len(dispatched_commands) == 1
    assert dispatched_commands[0].payload == task_data


def test_qt_event_bridge_agent_events() -> None:
    """Test that QtEventBridge handles agent-specific events."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    # Track agent events
    events_received = []

    def track_events(event: Event) -> None:
        events_received.append(event["type"])

    # Connect to agent signals
    bridge.agent_status_changed.connect(track_events)
    bridge.agent_thinking.connect(track_events)
    bridge.agent_action.connect(track_events)

    # Emit agent events
    event_handler.emit_event({
        "type": EventType.AGENT_STATUS_CHANGED,
        "payload": {"agent_id": "agent-1"}
    })
    event_handler.emit_event({
        "type": EventType.AGENT_THINKING,
        "payload": {"agent_id": "agent-1"}
    })
    event_handler.emit_event({
        "type": EventType.AGENT_ACTION,
        "payload": {"agent_id": "agent-1"}
    })

    # Verify all agent events were received
    assert EventType.AGENT_STATUS_CHANGED in events_received
    assert EventType.AGENT_THINKING in events_received
    assert EventType.AGENT_ACTION in events_received


def test_qt_event_bridge_system_events() -> None:
    """Test that QtEventBridge handles system control events."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    # Track system events
    events_received = []

    def track_events(event: Event) -> None:
        events_received.append(event["type"])

    # Connect to system signals
    bridge.agentic_system_started.connect(track_events)
    bridge.agentic_system_stopped.connect(track_events)

    # Emit system events
    event_handler.emit_event({
        "type": EventType.AGENTIC_SYSTEM_STARTED,
        "payload": {}
    })
    event_handler.emit_event({
        "type": EventType.AGENTIC_SYSTEM_STOPPED,
        "payload": {}
    })

    # Verify system events were received
    assert EventType.AGENTIC_SYSTEM_STARTED in events_received
    assert EventType.AGENTIC_SYSTEM_STOPPED in events_received


def test_qt_event_bridge_human_input_events() -> None:
    """Test that QtEventBridge handles human input events."""
    event_handler = EventHandler()
    bridge = QtEventBridge(event_handler)

    # Track human input events
    events_received = []

    def track_events(event: Event) -> None:
        events_received.append(event["type"])

    # Connect to human input signals
    bridge.human_input_requested.connect(track_events)
    bridge.human_input_received.connect(track_events)

    # Emit human input events
    event_handler.emit_event({
        "type": EventType.HUMAN_INPUT_REQUESTED,
        "payload": {}
    })
    event_handler.emit_event({
        "type": EventType.HUMAN_INPUT_RECEIVED,
        "payload": {"input": "test input"}
    })

    # Verify human input events were received
    assert EventType.HUMAN_INPUT_REQUESTED in events_received
    assert EventType.HUMAN_INPUT_RECEIVED in events_received


def test_qt_command_bridge_orchestrator_delegation() -> None:
    """QtCommandBridge delegates lifecycle calls to OrchestratorBridge."""
    from unittest.mock import MagicMock

    from src.ui.bridge import OrchestratorBridge

    command_bus = CommandBus()
    mock_orch = MagicMock()
    mock_orch.get_agents.return_value = []
    orch_bridge = OrchestratorBridge(mock_orch)
    bridge = QtCommandBridge(command_bus, orch_bridge)

    bridge.submit_human_review("thread-1", True, "looks good")
    bridge.signal_stop()
    bridge.update_provider(MagicMock())

    mock_orch.submit_human_review.assert_called_once_with(
        "thread-1", True, "looks good"
    )
    mock_orch.signal_stop.assert_called_once()
    mock_orch.update_provider.assert_called_once()
    assert bridge.get_agents() == []
