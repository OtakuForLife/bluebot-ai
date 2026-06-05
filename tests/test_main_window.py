"""Smoke tests for MainWindow wiring."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from src.events import EventHandler
from src.commands import CommandBus
from src.project.files import FileManager
from src.ui.bridge import QtCommandBridge, QtEventBridge
from src.ui.logging_handler import LoggingBridge
from src.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_window_initializes_without_orchestrator(qapp) -> None:
    """MainWindow can be constructed with command/event bridges only."""
    event_handler = EventHandler()
    command_bus = CommandBus()
    qt_event_bridge = QtEventBridge(event_handler)
    qt_command_bridge = QtCommandBridge(command_bus)
    logging_bridge = LoggingBridge()
    qt_log_handler = logging_bridge.create_handler()

    window = MainWindow(
        qt_event_bridge,
        qt_command_bridge,
        qt_log_handler,
        file_manager=FileManager(event_handler),
        selected_project={"name": "Demo", "path": "/tmp/demo", "brief": "Test"},
    )

    assert window.qt_command_bridge is qt_command_bridge
    assert window.tab_widget.count() >= 4
