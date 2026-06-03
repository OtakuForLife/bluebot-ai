"""Tests for Kanban board UI components."""

import pytest
from PySide6.QtWidgets import QApplication

from src.ui.kanban_board import TaskCard, TaskColumn, TaskCreationDialog


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_task():
    """Create a sample task data dictionary."""
    return {
        "id": "test-task-123",
        "title": "Test Task",
        "description": "This is a test task",
        "agent": "Game Programmer",
        "task_type": "create_script",
        "requires_review": True,
        "state": "todo",
    }


class TestTaskCard:
    """Tests for TaskCard widget."""

    def test_task_card_initialization(self, qapp, sample_task):
        """Test that task card initializes correctly."""
        card = TaskCard(sample_task)

        assert card is not None
        assert card.task_data == sample_task
        assert card.get_task_id() == "test-task-123"

    def test_task_card_displays_title(self, qapp, sample_task):
        """Test that task card displays title."""
        card = TaskCard(sample_task)

        assert card.task_data["title"] == "Test Task"


class TestTaskColumn:
    """Tests for TaskColumn widget."""

    def test_task_column_initialization(self, qapp):
        """Test that task column initializes correctly."""
        column = TaskColumn("To Do", "todo")

        assert column is not None
        assert column.title == "To Do"
        assert column.state == "todo"
        assert len(column.tasks) == 0

    def test_add_task_to_column(self, qapp, sample_task):
        """Test adding a task to a column."""
        column = TaskColumn("To Do", "todo")

        column.add_task(sample_task)

        assert len(column.tasks) == 1
        assert column.tasks[0] == sample_task

    def test_clear_tasks(self, qapp, sample_task):
        """Test clearing all tasks from a column."""
        column = TaskColumn("To Do", "todo")

        column.add_task(sample_task)
        assert len(column.tasks) == 1

        column.clear_tasks()
        assert len(column.tasks) == 0


class TestTaskCreationDialog:
    """Tests for TaskCreationDialog."""

    def test_dialog_initialization(self, qapp):
        """Test that dialog initializes correctly."""
        dialog = TaskCreationDialog()

        assert dialog is not None
        assert dialog.windowTitle() == "Create New Task"

    def test_dialog_has_required_fields(self, qapp):
        """Test that dialog has all required input fields."""
        dialog = TaskCreationDialog()

        assert dialog.title_input is not None
        assert dialog.description_input is not None
        assert dialog.agent_combo is not None
        assert dialog.task_type_combo is not None
        assert dialog.requires_review_checkbox is not None

    def test_requires_review_default_checked(self, qapp):
        """Test that requires review checkbox is checked by default."""
        dialog = TaskCreationDialog()

        assert dialog.requires_review_checkbox.isChecked() is True

    def test_get_task_data(self, qapp):
        """Test getting task data from dialog."""
        dialog = TaskCreationDialog()

        # Set some values
        dialog.title_input.setPlainText("Test Task Title")
        dialog.description_input.setPlainText("Test Description")
        dialog.requires_review_checkbox.setChecked(True)

        task_data = dialog.get_task_data()

        assert task_data["title"] == "Test Task Title"
        assert task_data["description"] == "Test Description"
        assert task_data["requires_review"] is True
        assert task_data["state"] == "todo"
        assert "id" in task_data
        assert len(task_data["id"]) > 0
