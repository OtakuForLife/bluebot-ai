"""Output and log viewer panel for monitoring agent activity."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class OutputPanel(QWidget):
    """Panel for viewing agent logs and outputs.
    
    This panel displays real-time logs from agents and allows
    filtering by agent and log level.
    
    Signals:
        clear_requested: Emitted when clear button is clicked.
    """
    
    clear_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the output panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.OutputPanel")
        
        self._setup_ui()
    

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("<h2>Output & Logs</h2>")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter controls
        header_layout.addWidget(QLabel("Filter by Agent:"))
        
        self.agent_filter = QComboBox()
        self.agent_filter.addItem("All Agents")
        self.agent_filter.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.agent_filter)
        
        header_layout.addWidget(QLabel("Log Level:"))
        
        self.level_filter = QComboBox()
        self.level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.level_filter)
        
        # Auto-scroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        header_layout.addWidget(self.autoscroll_check)
        
        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._on_clear_clicked)
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Statistics bar
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("Lines: 0 | Filtered: 0")
        self.stats_label.setStyleSheet("color: gray;")
        stats_layout.addWidget(self.stats_label)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
    
    def add_log(self, message: str, level: str = "INFO", agent: str = "System") -> None:
        """Add a log message to the output.
        
        Args:
            message: Log message text.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            agent: Name of the agent that generated the log.
        """
        # Check filters
        agent_filter = self.agent_filter.currentText()
        level_filter = self.level_filter.currentText()
        
        if agent_filter != "All Agents" and agent != agent_filter:
            return
        
        if level_filter != "ALL" and level != level_filter:
            return
        
        # Format log message with color
        colors = {
            "DEBUG": "#808080",
            "INFO": "#4ec9b0",
            "WARNING": "#dcdcaa",
            "ERROR": "#f48771",
        }
        
        color = colors.get(level, "#d4d4d4")
        
        formatted_message = (
            f'<span style="color: {color};">'
            f'[{level}] [{agent}] {message}'
            f'</span><br>'
        )
        
        # Append to text area
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(formatted_message)
        
        # Auto-scroll if enabled
        if self.autoscroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        # Update statistics
        self._update_stats()
    
    def add_agent_to_filter(self, agent_name: str) -> None:
        """Add an agent to the filter dropdown.

        Args:
            agent_name: Name of the agent to add.
        """
        if self.agent_filter.findText(agent_name) == -1:
            self.agent_filter.addItem(agent_name)

    @Slot()
    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.log_text.clear()
        self._update_stats()
        self.clear_requested.emit()
        self.logger.info("Log output cleared")

    @Slot(str)
    def _on_filter_changed(self, _: str) -> None:
        """Handle filter change.

        Args:
            _: Filter value (unused, filters are applied on new messages).
        """
        self.logger.debug("Filter changed")
        # Note: Filtering is applied when adding new messages
        # To filter existing messages, we would need to re-render

    def _update_stats(self) -> None:
        """Update the statistics label."""
        # Count lines in the text
        text = self.log_text.toPlainText()
        line_count = len(text.split('\n')) if text else 0

        self.stats_label.setText(f"Lines: {line_count}")

    def clear(self) -> None:
        """Clear all log output."""
        self.log_text.clear()
        self._update_stats()

