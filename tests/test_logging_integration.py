"""Tests for agent logging integration with UI output panel."""

import logging
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from src.ui.logging_handler import LoggingBridge, QtLogHandler


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestQtLogHandler:
    """Tests for QtLogHandler class."""

    def test_handler_creation(self):
        """Test creating a Qt log handler."""
        handler = QtLogHandler(level=logging.DEBUG)
        
        assert handler is not None
        assert handler.level == logging.DEBUG
        assert isinstance(handler, QObject)
        assert isinstance(handler, logging.Handler)

    def test_handler_emits_signal(self, qapp):
        """Test that handler emits signal when log record is processed."""
        handler = QtLogHandler()

        # Track signal emissions
        signal_data = []

        def on_log_message(message, level, agent_name):
            signal_data.append((message, level, agent_name))

        handler.log_message.connect(on_log_message)

        # Create a log record
        logger = logging.getLogger("test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Emit a log message
        logger.info("Test message")

        # Process Qt events
        qapp.processEvents()

        # Verify signal was emitted with correct arguments
        assert len(signal_data) == 1
        message, level, agent_name = signal_data[0]
        assert message == "Test message"
        assert level == "INFO"

    def test_extract_agent_name_from_logger(self):
        """Test extracting agent name from logger name."""
        handler = QtLogHandler()
        
        # Test agent logger names
        assert handler._extract_agent_name("agent.game_programmer.abc123") == "Game Programmer"
        assert handler._extract_agent_name("agent.game_designer.def456") == "Game Designer"
        assert handler._extract_agent_name("agent.game_producer.ghi789") == "Game Producer"
        assert handler._extract_agent_name("agent.game_artist.jkl012") == "Game Artist"
        assert handler._extract_agent_name("agent.audio_engineer.mno345") == "Audio Engineer"
        assert handler._extract_agent_name("agent.qa_tester.pqr678") == "QA Tester"
        
        # Test orchestrator logger
        assert handler._extract_agent_name("src.orchestrator.orchestrator") == "Orchestrator"
        
        # Test task manager logger
        assert handler._extract_agent_name("src.orchestrator.task_manager") == "Task Manager"
        
        # Test UI logger
        assert handler._extract_agent_name("src.ui.main_window") == "UI"
        
        # Test unknown logger
        assert handler._extract_agent_name("some.unknown.logger") == "Logger"

    def test_handler_filters_by_level(self, qapp):
        """Test that handler respects log level filtering."""
        handler = QtLogHandler(level=logging.WARNING)

        logger = logging.getLogger("test_filter_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Track signal emissions
        signal_data = []

        def on_signal(*args):
            signal_data.append(args)

        handler.log_message.connect(on_signal)

        # INFO should not be emitted (below WARNING)
        logger.info("This should not be emitted")
        qapp.processEvents()

        assert len(signal_data) == 0

        # WARNING should be emitted
        logger.warning("This should be emitted")
        qapp.processEvents()

        assert len(signal_data) == 1
        assert signal_data[0][1] == "WARNING"


class TestLoggingBridge:
    """Tests for LoggingBridge class."""

    def test_bridge_creation(self):
        """Test creating a logging bridge."""
        bridge = LoggingBridge()
        
        assert bridge is not None
        assert bridge.handler is None
        assert bridge.attached_loggers == []

    def test_create_handler(self):
        """Test creating a handler through the bridge."""
        bridge = LoggingBridge()
        handler = bridge.create_handler(level=logging.INFO)
        
        assert handler is not None
        assert isinstance(handler, QtLogHandler)
        assert handler.level == logging.INFO
        assert bridge.handler is handler

    def test_attach_to_logger(self):
        """Test attaching handler to a specific logger."""
        bridge = LoggingBridge()
        handler = bridge.create_handler()
        
        test_logger = logging.getLogger("test_attach_logger")
        bridge.attach_to_logger(test_logger)
        
        assert test_logger in bridge.attached_loggers
        assert handler in test_logger.handlers

    def test_attach_to_root(self):
        """Test attaching handler to root logger."""
        bridge = LoggingBridge()
        handler = bridge.create_handler()
        
        # Get root logger before attaching
        root_logger = logging.getLogger()
        initial_handler_count = len(root_logger.handlers)
        
        bridge.attach_to_root()
        
        assert root_logger in bridge.attached_loggers
        assert len(root_logger.handlers) == initial_handler_count + 1
        assert handler in root_logger.handlers

    def test_detach_all(self):
        """Test detaching handler from all loggers."""
        bridge = LoggingBridge()
        handler = bridge.create_handler()
        
        # Attach to multiple loggers
        logger1 = logging.getLogger("test_detach_1")
        logger2 = logging.getLogger("test_detach_2")
        
        bridge.attach_to_logger(logger1)
        bridge.attach_to_logger(logger2)
        
        assert len(bridge.attached_loggers) == 2
        
        # Detach from all
        bridge.detach_all()
        
        assert len(bridge.attached_loggers) == 0
        assert handler not in logger1.handlers
        assert handler not in logger2.handlers

    def test_attach_same_logger_twice(self):
        """Test that attaching the same logger twice doesn't duplicate."""
        bridge = LoggingBridge()
        handler = bridge.create_handler()
        
        test_logger = logging.getLogger("test_duplicate_logger")
        
        bridge.attach_to_logger(test_logger)
        initial_count = len(bridge.attached_loggers)
        
        bridge.attach_to_logger(test_logger)
        
        # Should not add duplicate
        assert len(bridge.attached_loggers) == initial_count

