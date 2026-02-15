"""Task submission panel for sending tasks to agents."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.agents.base import MessageType
from src.orchestrator.orchestrator import Orchestrator


class TaskPanel(QWidget):
    """Panel for submitting tasks to AI agents.
    
    This panel provides an interface for users to submit tasks
    to specific agents with custom parameters.
    
    Signals:
        task_submitted: Emitted when a task is submitted.
    """
    
    task_submitted = Signal(str, str, dict)  # agent_name, task_type, payload
    
    def __init__(self, orchestrator: Orchestrator, parent: Optional[QWidget] = None) -> None:
        """Initialize the task panel.
        
        Args:
            orchestrator: The orchestrator managing the agents.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.TaskPanel")
        self.orchestrator = orchestrator
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Submit Task</h2>")
        layout.addWidget(title)
        
        # Agent selection
        agent_group = QGroupBox("Target Agent")
        agent_layout = QFormLayout(agent_group)
        
        self.agent_combo = QComboBox()
        self._populate_agents()
        agent_layout.addRow("Agent:", self.agent_combo)
        
        layout.addWidget(agent_group)
        
        # Task type selection
        task_group = QGroupBox("Task Type")
        task_layout = QFormLayout(task_group)
        
        self.task_type_combo = QComboBox()
        self.task_type_combo.currentTextChanged.connect(self._on_task_type_changed)
        task_layout.addRow("Type:", self.task_type_combo)
        
        layout.addWidget(task_group)
        
        # Task parameters
        self.params_group = QGroupBox("Task Parameters")
        self.params_layout = QFormLayout(self.params_group)
        
        layout.addWidget(self.params_group)
        
        # Submit button
        button_layout = QHBoxLayout()
        
        self.submit_button = QPushButton("Submit Task")
        self.submit_button.clicked.connect(self._on_submit_task)
        button_layout.addWidget(self.submit_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Connect agent selection to update task types
        self.agent_combo.currentTextChanged.connect(self._on_agent_changed)
        
        # Initialize task types for first agent
        if self.agent_combo.count() > 0:
            self._on_agent_changed(self.agent_combo.currentText())
    
    def _populate_agents(self) -> None:
        """Populate the agent dropdown with registered agents."""
        agents = self.orchestrator.list_agents()
        
        for agent_info in agents:
            agent_name = agent_info.get("name", "Unknown")
            self.agent_combo.addItem(agent_name)
    
    @Slot(str)
    def _on_agent_changed(self, agent_name: str) -> None:
        """Handle agent selection change.
        
        Args:
            agent_name: Selected agent name.
        """
        self.logger.info(f"Agent changed to: {agent_name}")
        
        # Update task types based on agent role
        self.task_type_combo.clear()
        
        # Get agent info to determine role
        agents = self.orchestrator.list_agents()
        agent_info = next((a for a in agents if a.get("name") == agent_name), None)
        
        if not agent_info:
            return
        
        role = agent_info.get("role", "")
        
        # Add task types based on role
        if role == "game_programmer":
            self.task_type_combo.addItems([
                "create_script",
                "implement_gameplay",
                "implement_physics",
                "implement_ai",
            ])
        elif role == "game_designer":
            self.task_type_combo.addItems([
                "define_mechanics",
                "create_storyboard",
                "design_ux",
                "create_design_document",
            ])
        elif role == "game_artist":
            self.task_type_combo.addItems([
                "create_sprite",
                "create_model",
                "create_animation",
                "design_ui",
            ])
        elif role == "qa_tester":
            self.task_type_combo.addItems([
                "run_tests",
                "report_bug",
                "verify_fix",
            ])
        elif role == "audio_engineer":
            self.task_type_combo.addItems([
                "add_sound_effect",
                "create_music",
            ])
        elif role == "game_producer":
            self.task_type_combo.addItems([
                "assign_task",
                "manage_timeline",
            ])
        else:
            self.task_type_combo.addItem("custom_task")

    @Slot(str)
    def _on_task_type_changed(self, task_type: str) -> None:
        """Handle task type selection change.

        Args:
            task_type: Selected task type.
        """
        self.logger.info(f"Task type changed to: {task_type}")

        # Clear existing parameter inputs
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add parameter inputs based on task type
        if task_type == "create_script":
            script_name = QLineEdit()
            script_name.setPlaceholderText("player.gd")
            script_name.setObjectName("script_name")
            self.params_layout.addRow("Script Name:", script_name)

            description = QPlainTextEdit()
            description.setPlaceholderText("Describe what the script should do...")
            description.setMaximumHeight(100)
            description.setObjectName("description")
            self.params_layout.addRow("Description:", description)

        elif task_type in ["create_sprite", "create_model", "create_animation"]:
            asset_name = QLineEdit()
            asset_name.setPlaceholderText("player_sprite")
            asset_name.setObjectName("asset_name")
            self.params_layout.addRow("Asset Name:", asset_name)

            description = QPlainTextEdit()
            description.setPlaceholderText("Describe the asset...")
            description.setMaximumHeight(100)
            description.setObjectName("description")
            self.params_layout.addRow("Description:", description)

        elif task_type == "report_bug":
            bug_description = QPlainTextEdit()
            bug_description.setPlaceholderText("Describe the bug...")
            bug_description.setMaximumHeight(100)
            bug_description.setObjectName("description")
            self.params_layout.addRow("Bug Description:", bug_description)

        else:
            # Generic description field
            description = QPlainTextEdit()
            description.setPlaceholderText("Task description...")
            description.setMaximumHeight(100)
            description.setObjectName("description")
            self.params_layout.addRow("Description:", description)

    @Slot()
    def _on_submit_task(self) -> None:
        """Handle task submission."""
        agent_name = self.agent_combo.currentText()
        task_type = self.task_type_combo.currentText()

        if not agent_name or not task_type:
            self.status_label.setText("Please select an agent and task type")
            self.status_label.setStyleSheet("color: red;")
            return

        # Collect parameters from form
        payload = {"task_type": task_type}

        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self.params_layout.itemAt(i, QFormLayout.ItemRole.FieldRole)

            if field_item and field_item.widget():
                widget = field_item.widget()
                name = widget.objectName()

                if isinstance(widget, QLineEdit):
                    payload[name] = widget.text()
                elif isinstance(widget, QPlainTextEdit):
                    payload[name] = widget.toPlainText()

        self.logger.info(f"Submitting task: {task_type} to {agent_name} with payload: {payload}")

        # Emit signal
        self.task_submitted.emit(agent_name, task_type, payload)

        self.status_label.setText(f"Task submitted to {agent_name}")
        self.status_label.setStyleSheet("color: green;")

    def refresh_agents(self) -> None:
        """Refresh the list of available agents."""
        current = self.agent_combo.currentText()
        self.agent_combo.clear()
        self._populate_agents()

        # Restore selection if possible
        index = self.agent_combo.findText(current)
        if index >= 0:
            self.agent_combo.setCurrentIndex(index)

