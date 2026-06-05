"""Kanban board for task management."""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional
from uuid import UUID

from PySide6.QtCore import QEvent, Qt, Signal, Slot
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

from src.project.files import FileManager
from src.project.manager import parse_persisted_tasks

_VALID_TASK_TYPES = ("design", "gameplay", "systems", "art")


class TaskCard(QFrame):
    """Individual task card widget."""

    clicked = Signal(str)  # emits task_id when the card is clicked

    def __init__(self, task_data: dict, parent: Optional[QWidget] = None) -> None:
        """Initialize the task card.

        Args:
            task_data: Task data dictionary.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._logger = logging.getLogger(__name__)
        self.task_data = task_data
        self._setup_ui()

        # Install this card as an event filter on every child widget so that
        # mouse clicks anywhere on the card surface (including on labels) are
        # caught here instead of being consumed by the child.
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

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

        # Review pending indicator — shown for tasks in the review column
        if self.task_data.get('state') == 'review':
            review_label = QLabel("🔔 Click to review")
            review_label.setStyleSheet(
                "color: #FF9800; font-size: 10px; font-weight: bold;"
            )
            layout.addWidget(review_label)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        """Intercept mouse presses on child widgets and re-emit as card click."""
        if event.type() == QEvent.Type.MouseButtonPress:
            self._logger.debug(f"TaskCard clicked (via child) — task_id={self.get_task_id()}")
            self.clicked.emit(self.get_task_id())
            return True  # consume — prevents double-fire with mousePressEvent
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Emit clicked signal for clicks directly on the card frame."""
        self._logger.debug(f"TaskCard clicked (direct) — task_id={self.get_task_id()}")
        self.clicked.emit(self.get_task_id())
        super().mousePressEvent(event)

    def get_task_id(self) -> str:
        """Get the task ID."""
        return self.task_data.get('id', '')


class TaskColumn(QWidget):
    """Column for a specific task state."""

    task_moved = Signal(str, str)   # task_id, new_state
    task_clicked = Signal(str)      # task_id — bubbled up from TaskCard.clicked
    
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

        # Create task card and bubble its click signal up to this column
        card = TaskCard(task_data)
        card.clicked.connect(self.task_clicked)
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

    def __init__(
        self,
        agents: Optional[list[str]] = None,
        task_types: Optional[list[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Create New Task")
        self.resize(500, 400)

        self._agent_names = agents or []
        self._task_types = task_types or list(_VALID_TASK_TYPES)
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
        if self._agent_names:
            self.agent_combo.addItems(self._agent_names)
        form_layout.addRow("Assign to:", self.agent_combo)

        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(self._task_types)
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

    task_created = Signal(dict)          # task_data
    task_state_changed = Signal(str, str)  # task_id, new_state
    task_submitted = Signal(str, str, dict)  # agent_name, task_type, payload
    task_review_requested = Signal(str, dict)  # task_id, review_payload

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the Kanban board."""
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.KanbanBoard")
        self.tasks: dict[str, dict] = {}
        self._project_path: Optional[Path] = None
        self._file_manager: Optional[FileManager] = None
        self._agent_names: list[str] = []
        self._pending_reviews: dict[str, dict] = {}

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

        # Review column — clicking a card in this column triggers human review
        self.review_column = TaskColumn("👀 Review", "review")
        self.review_column.task_clicked.connect(self._on_review_card_clicked)
        columns_layout.addWidget(self.review_column)

        # Done column
        self.done_column = TaskColumn("✅ Done", "done")
        columns_layout.addWidget(self.done_column)

        layout.addLayout(columns_layout)

    def set_pending_review(self, task_id: str, payload: dict) -> None:
        """Store a human-review payload for a task awaiting user approval.

        Called by MainWindow when HUMAN_INPUT_REQUESTED arrives. The payload
        is emitted via task_review_requested when the user clicks the card.

        Args:
            task_id: ID of the task awaiting review.
            payload: Full interrupt payload from human_review_node.
        """
        self._pending_reviews[task_id] = payload

    def clear_pending_review(self, task_id: str) -> None:
        """Remove a stored review payload once the user has submitted a decision.

        Args:
            task_id: ID of the task whose review has been submitted.
        """
        self._pending_reviews.pop(task_id, None)

    @Slot(str)
    def _on_review_card_clicked(self, task_id: str) -> None:
        """Emit task_review_requested when the user clicks a card in the Review column.

        If the workflow is currently paused at human_review_node the stored
        pending-review payload is used (contains thread_id so the orchestrator
        can be resumed). Otherwise a minimal payload is built from the persisted
        task data so the user can still approve/reject tasks from a previous run.

        Args:
            task_id: ID of the clicked task card.
        """
        self.logger.debug(
            f"Review card clicked — task_id={task_id}, "
            f"pending_ids={list(self._pending_reviews.keys())}"
        )
        payload = self._pending_reviews.get(task_id)
        if payload is None:
            # No active workflow pause — build payload from stored task data so
            # the user can still review and move the card to Done / back to Todo.
            task_data = self.tasks.get(task_id, {})
            payload = {
                "task_description": task_data.get("description", ""),
                "last_agent": task_data.get("agent", ""),
                "created_files": [],
                "modified_files": [],
                "tool_results": [],
                "current_task_id": task_id,
                # _thread_id intentionally absent — signals no live workflow
            }
            self.logger.info(
                f"No active workflow for task {task_id}; "
                "opening review dialog from persisted task data."
            )
        self.task_review_requested.emit(task_id, payload)

    @Slot()
    def _on_create_task(self) -> None:
        """Handle create task button click."""
        dialog = TaskCreationDialog(
            agents=self._agent_names or None,
            parent=self,
        )

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

    def set_agent_names(self, names: list[str]) -> None:
        self._agent_names = names

    def set_file_manager(self, file_manager: FileManager) -> None:
        self._file_manager = file_manager

    def _column_for_state(self, state: str) -> Optional[TaskColumn]:
        if state == "todo":
            return self.todo_column
        if state == "in_progress":
            return self.in_progress_column
        if state == "review":
            return self.review_column
        if state == "done":
            return self.done_column
        return None

    def set_project_path(self, path: Path) -> None:
        """Load tasks.json for the given project and populate the board."""
        self._project_path = path
        self.tasks.clear()

        tasks = parse_persisted_tasks(path / FileManager.TASKS_FILE)
        if tasks:
            for task in tasks:
                task_id = task.get("id")
                if task_id:
                    self.tasks[task_id] = task
        elif (path / FileManager.TASKS_FILE).exists():
            self.logger.warning(f"Could not parse {FileManager.TASKS_FILE} in {path}")

        self.refresh_board()
        self.logger.info(f"Loaded {len(self.tasks)} task(s) from {path}")

    def _save_tasks(self) -> None:
        """Persist the current task list to tasks.json in the project folder."""
        if not self._project_path:
            return

        data = {"tasks": list(self.tasks.values())}
        if self._file_manager:
            if not self._file_manager.write_json_file(
                self._project_path, FileManager.TASKS_FILE, data
            ):
                self.logger.error(f"Failed to save {FileManager.TASKS_FILE}")
            return

        tasks_file = self._project_path / FileManager.TASKS_FILE
        try:
            tmp = tasks_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(tasks_file)
        except Exception as exc:
            self.logger.error(f"Failed to save {FileManager.TASKS_FILE}: {exc}")

    def add_task(self, task_data: dict) -> None:
        """Add a task to the board and persist the change.

        Args:
            task_data: Task data dictionary.
        """
        task_id = task_data.get("id")
        if not task_id:
            self.logger.error("Task data missing ID")
            return

        # Store task
        self.tasks[task_id] = task_data
        self._save_tasks()

        # Add to appropriate column
        column = self._column_for_state(task_data.get("state", "todo"))
        if column:
            column.add_task(task_data)

    def refresh_board(self) -> None:
        """Refresh the board display."""
        # Clear all columns
        self.todo_column.clear_tasks()
        self.in_progress_column.clear_tasks()
        self.review_column.clear_tasks()
        self.done_column.clear_tasks()

        # Re-add all tasks
        for task_data in self.tasks.values():
            column = self._column_for_state(task_data.get("state", "todo"))
            if column:
                column.add_task(task_data)

    def update_task_state(self, task_id: str, new_state: str) -> None:
        """Update a task's state and persist the change.

        Completed tasks (state == "done") are immutable — this method will
        log a warning and return without making any change.

        Args:
            task_id: Task ID.
            new_state: New state for the task.
        """
        if task_id not in self.tasks:
            return

        current_state = self.tasks[task_id].get("state")
        if current_state == "done":
            self.logger.warning(
                f"Task {task_id} is already done and cannot be moved to '{new_state}'"
            )
            return

        self.tasks[task_id]["state"] = new_state
        self.refresh_board()
        self._save_tasks()
        self.task_state_changed.emit(task_id, new_state)
        self.logger.info(f"Task {task_id} moved to {new_state}")


