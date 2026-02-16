"""Custom logging handler for routing agent logs to the UI output panel."""

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal


class QtLogHandler(QObject, logging.Handler):
    """Custom logging handler that emits Qt signals for log records.
    
    This handler bridges Python's logging system with Qt's signal/slot
    mechanism, allowing log messages to be displayed in the UI output panel.
    
    Signals:
        log_message: Emitted when a log record is processed.
                     Args: (message: str, level: str, logger_name: str)
    """
    
    log_message = Signal(str, str, str)  # message, level, logger_name
    
    def __init__(self, level: int = logging.NOTSET) -> None:
        """Initialize the Qt log handler.
        
        Args:
            level: Minimum logging level to handle.
        """
        QObject.__init__(self)
        logging.Handler.__init__(self, level)
        
        # Set a formatter for consistent log formatting
        formatter = logging.Formatter(
            '%(message)s'  # Just the message, formatting is done in UI
        )
        self.setFormatter(formatter)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as a Qt signal.
        
        Args:
            record: The log record to emit.
        """
        try:
            # Format the message
            message = self.format(record)
            
            # Get the log level name
            level = record.levelname
            
            # Extract agent name from logger name
            # Logger names are formatted as: "agent.{role}.{id}" or module names
            logger_name = record.name
            agent_name = self._extract_agent_name(logger_name)
            
            # Emit the signal (thread-safe)
            self.log_message.emit(message, level, agent_name)
            
        except Exception:
            # Don't let logging errors crash the application
            self.handleError(record)
    
    def _extract_agent_name(self, logger_name: str) -> str:
        """Extract a friendly agent name from the logger name.
        
        Args:
            logger_name: The full logger name.
            
        Returns:
            A friendly name for display in the UI.
        """
        # Handle agent loggers: "agent.{role}.{id}"
        if logger_name.startswith("agent."):
            parts = logger_name.split(".")
            if len(parts) >= 2:
                role = parts[1]
                # Convert role to friendly name
                role_map = {
                    "game_programmer": "Game Programmer",
                    "game_designer": "Game Designer",
                    "game_producer": "Game Producer",
                    "game_artist": "Game Artist",
                    "audio_engineer": "Audio Engineer",
                    "qa_tester": "QA Tester",
                }
                return role_map.get(role, role.replace("_", " ").title())
        
        # Handle task manager loggers (check before orchestrator)
        if "task_manager" in logger_name:
            return "Task Manager"

        # Handle orchestrator loggers
        if "orchestrator" in logger_name:
            return "Orchestrator"
        
        # Handle UI loggers
        if logger_name.startswith("src.ui."):
            return "UI"
        
        # Default: use the last part of the logger name
        parts = logger_name.split(".")
        return parts[-1].replace("_", " ").title() if parts else "System"


class LoggingBridge:
    """Bridge between Python logging and Qt UI.
    
    This class manages the Qt log handler and provides methods to
    attach it to specific loggers or the root logger.
    """
    
    def __init__(self) -> None:
        """Initialize the logging bridge."""
        self.handler: Optional[QtLogHandler] = None
        self.attached_loggers: list[logging.Logger] = []
    
    def create_handler(self, level: int = logging.DEBUG) -> QtLogHandler:
        """Create and return a Qt log handler.
        
        Args:
            level: Minimum logging level to handle.
            
        Returns:
            The created Qt log handler.
        """
        self.handler = QtLogHandler(level)
        return self.handler
    
    def attach_to_logger(self, logger: logging.Logger) -> None:
        """Attach the Qt handler to a specific logger.
        
        Args:
            logger: The logger to attach to.
        """
        if self.handler and logger not in self.attached_loggers:
            logger.addHandler(self.handler)
            self.attached_loggers.append(logger)
    
    def attach_to_root(self) -> None:
        """Attach the Qt handler to the root logger.
        
        This will capture all log messages from the entire application.
        """
        if self.handler:
            root_logger = logging.getLogger()
            self.attach_to_logger(root_logger)
    
    def detach_all(self) -> None:
        """Detach the Qt handler from all loggers."""
        if self.handler:
            for logger in self.attached_loggers:
                logger.removeHandler(self.handler)
            self.attached_loggers.clear()

