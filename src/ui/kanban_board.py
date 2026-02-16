"""Kanban board for task management."""

import logging
import uuid
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.orchestrator.orchestrator import Orchestrator


class TaskCard(QFrame):
    """Individual task card widget."""
    
    def __init__(self, task_data: dict, parent: Optional[QWidget] = None) -> None:
        """Initialize the task card.
        
        Args:
            task_data: Task data dictionary.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.task_data = task_data
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Task title
        title = QLabel(f"<b>{self.task_data.get('title', 'Untitled Task')}</b>")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Task description
        description = self.task_data.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 10px;")
            layout.addWidget(desc_label)
        
        # Agent assignment
        agent = self.task_data.get('agent', 'Unassigned')
        agent_label = QLabel(f"👤 {agent}")
        agent_label.setStyleSheet("color: #2196F3; font-size: 10px;")
        layout.addWidget(agent_label)
        
        # Review required indicator
        if self.task_data.get('requires_review', False):
            review_label = QLabel("⚠️ Requires Review")
            review_label.setStyleSheet("color: #FF9800; font-size: 10px; font-weight: bold;")
            layout.addWidget(review_label)
    
    def get_task_id(self) -> str:
        """Get the task ID.
        
        Returns:
            Task ID.
        """
        return self.task_data.get('id', '')


class TaskColumn(QWidget):
    """Column for a specific task state."""
    
    task_moved = Signal(str, str)  # task_id, new_state
    
    def __init__(self, title: str, state: str, parent: Optional[QWidget] = None) -> None:
        """Initialize the task column.
        
        Args:
            title: Column title.
            state: Task state this column represents.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.title = title
        self.state = state
        self.tasks: list[dict] = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Column header
        header = QLabel(f"<h3>{self.title}</h3>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Task count
        self.count_label = QLabel("0 tasks")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.count_label)
        
        # Scroll area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for task cards
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.task_container)
        layout.addWidget(scroll)
    
    def add_task(self, task_data: dict) -> None:
        """Add a task to this column.

        Args:
            task_data: Task data dictionary.
        """
        self.tasks.append(task_data)

        # Create task card
        card = TaskCard(task_data)
        self.task_layout.addWidget(card)

        # Update count
        self._update_count()

    def clear_tasks(self) -> None:
        """Clear all tasks from this column."""
        self.tasks.clear()

        # Remove all task cards
        while self.task_layout.count():
            item = self.task_layout.takeAt(0)
            if item.widget(): # type: ignore
                item.widget().deleteLater() # type: ignore

        self._update_count()

    def _update_count(self) -> None:
        """Update the task count label."""
        count = len(self.tasks)
        self.count_label.setText(f"{count} task{'s' if count != 1 else ''}")


class TaskCreationDialog(QDialog):
    """Dialog for creating new tasks."""

    def __init__(self, orchestrator: Orchestrator, parent: Optional[QWidget] = None) -> None:
        """Initialize the task creation dialog.

        Args:
            orchestrator: The orchestrator managing the agents.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.orchestrator = orchestrator
        self.setWindowTitle("Create New Task")
        self.resize(500, 400)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)

        # Form layout
        form_group = QGroupBox("Task Details")
        form_layout = QFormLayout(form_group)

        # Title
        self.title_input = QPlainTextEdit()
        self.title_input.setPlaceholderText("Enter task title...")
        self.title_input.setMaximumHeight(60)
        form_layout.addRow("Title:", self.title_input)

        # Description
        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText("Enter task description...")
        self.description_input.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_input)

        # Agent selection
        self.agent_combo = QComboBox()
        self._populate_agents()
        form_layout.addRow("Assign to:", self.agent_combo)

        # Task type selection
        self.task_type_combo = QComboBox()
        self.agent_combo.currentTextChanged.connect(self._on_agent_changed)
        form_layout.addRow("Task Type:", self.task_type_combo)

        # Requires review checkbox
        self.requires_review_checkbox = QCheckBox("Require user review before completion")
        self.requires_review_checkbox.setChecked(True)
        form_layout.addRow("", self.requires_review_checkbox)

        layout.addWidget(form_group)

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

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

    def get_task_data(self) -> dict:
        """Get the task data from the form.

        Returns:
            Task data dictionary.
        """
        return {
            "id": str(uuid.uuid4()),
            "title": self.title_input.toPlainText().strip(),
            "description": self.description_input.toPlainText().strip(),
            "agent": self.agent_combo.currentText(),
            "task_type": self.task_type_combo.currentText(),
            "requires_review": self.requires_review_checkbox.isChecked(),
            "state": "todo",
        }


class KanbanBoard(QWidget):
    """Kanban board for task management."""

    task_created = Signal(dict)  # task_data
    task_state_changed = Signal(str, str)  # task_id, new_state
    task_submitted = Signal(str, str, dict)  # agent_name, task_type, payload

    def __init__(self, orchestrator: Orchestrator, parent: Optional[QWidget] = None) -> None:
        """Initialize the Kanban board.

        Args:
            orchestrator: The orchestrator managing the agents.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.KanbanBoard")
        self.orchestrator = orchestrator
        self.tasks: dict[str, dict] = {}  # task_id -> task_data

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)

        # Header with title and create button
        header_layout = QHBoxLayout()

        title = QLabel("<h2>Task Board</h2>")
        header_layout.addWidget(title)

        header_layout.addStretch()

        create_button = QPushButton("+ Create Task")
        create_button.clicked.connect(self._on_create_task)
        header_layout.addWidget(create_button)

        layout.addLayout(header_layout)

        # Kanban columns
        columns_layout = QHBoxLayout()

        # To Do column
        self.todo_column = TaskColumn("📋 To Do", "todo")
        columns_layout.addWidget(self.todo_column)

        # In Progress column
        self.in_progress_column = TaskColumn("🔄 In Progress", "in_progress")
        columns_layout.addWidget(self.in_progress_column)

        # Review column
        self.review_column = TaskColumn("👀 Review", "review")
        columns_layout.addWidget(self.review_column)

        # Done column
        self.done_column = TaskColumn("✅ Done", "done")
        columns_layout.addWidget(self.done_column)

        layout.addLayout(columns_layout)

    @Slot()
    def _on_create_task(self) -> None:
        """Handle create task button click."""
        dialog = TaskCreationDialog(self.orchestrator, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()

            # Validate task data
            if not task_data.get("title"):
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Task", "Please enter a task title.")
                return

            # Add task to board
            self.add_task(task_data)

            # Emit signal
            self.task_created.emit(task_data)

            # Submit task to orchestrator
            agent_name = task_data.get("agent")
            task_type = task_data.get("task_type")
            payload = {
                "task_type": task_type,
                "description": task_data.get("description", ""),
                "task_id": task_data.get("id"),
            }

            self.logger.info(f"Created task: {task_data.get('title')} for {agent_name}")
            self.task_submitted.emit(agent_name, task_type, payload)

    def add_task(self, task_data: dict) -> None:
        """Add a task to the board.

        Args:
            task_data: Task data dictionary.
        """
        task_id = task_data.get("id")
        if not task_id:
            self.logger.error("Task data missing ID")
            return

        # Store task
        self.tasks[task_id] = task_data

        # Add to appropriate column
        state = task_data.get("state", "todo")

        if state == "todo":
            self.todo_column.add_task(task_data)
        elif state == "in_progress":
            self.in_progress_column.add_task(task_data)
        elif state == "review":
            self.review_column.add_task(task_data)
        elif state == "done":
            self.done_column.add_task(task_data)

    def refresh_board(self) -> None:
        """Refresh the board display."""
        # Clear all columns
        self.todo_column.clear_tasks()
        self.in_progress_column.clear_tasks()
        self.review_column.clear_tasks()
        self.done_column.clear_tasks()

        # Re-add all tasks
        for task_data in self.tasks.values():
            state = task_data.get("state", "todo")

            if state == "todo":
                self.todo_column.add_task(task_data)
            elif state == "in_progress":
                self.in_progress_column.add_task(task_data)
            elif state == "review":
                self.review_column.add_task(task_data)
            elif state == "done":
                self.done_column.add_task(task_data)

    def update_task_state(self, task_id: str, new_state: str) -> None:
        """Update a task's state.

        Args:
            task_id: Task ID.
            new_state: New state for the task.
        """
        if task_id in self.tasks:
            self.tasks[task_id]["state"] = new_state
            self.refresh_board()
            self.task_state_changed.emit(task_id, new_state)
            self.logger.info(f"Task {task_id} moved to {new_state}")


