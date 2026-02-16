"""Tests for the Kanban board."""

import pytest
from PySide6.QtWidgets import QApplication, QDialog
from src.ui.kanban_board import TaskCard, TaskColumn, TaskCreationDialog, KanbanBoard
from src.orchestrator.orchestrator import Orchestrator


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def orchestrator():
    """Create an Orchestrator instance."""
    return Orchestrator()


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
        """Test that task card displays the title."""
        card = TaskCard(sample_task)

        # Card should be created successfully with the task data
        assert card.task_data["title"] == "Test Task"
    
    def test_task_card_with_review_flag(self, qapp, sample_task):
        """Test that task card shows review indicator when required."""
        sample_task["requires_review"] = True
        card = TaskCard(sample_task)
        
        assert card is not None
        # Review indicator should be present
    
    def test_task_card_without_review_flag(self, qapp, sample_task):
        """Test that task card works without review requirement."""
        sample_task["requires_review"] = False
        card = TaskCard(sample_task)
        
        assert card is not None
    
    def test_task_card_with_empty_description(self, qapp, sample_task):
        """Test that task card handles empty description."""
        sample_task["description"] = ""
        card = TaskCard(sample_task)
        
        assert card is not None


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
    
    def test_add_multiple_tasks(self, qapp, sample_task):
        """Test adding multiple tasks to a column."""
        column = TaskColumn("To Do", "todo")
        
        column.add_task(sample_task)
        
        task2 = sample_task.copy()
        task2["id"] = "test-task-456"
        task2["title"] = "Second Task"
        column.add_task(task2)
        
        assert len(column.tasks) == 2
    
    def test_clear_tasks(self, qapp, sample_task):
        """Test clearing all tasks from a column."""
        column = TaskColumn("To Do", "todo")
        
        column.add_task(sample_task)
        assert len(column.tasks) == 1
        
        column.clear_tasks()
        assert len(column.tasks) == 0
    
    def test_task_count_updates(self, qapp, sample_task):
        """Test that task count label updates correctly."""
        column = TaskColumn("To Do", "todo")
        
        # Initially 0 tasks
        assert "0 task" in column.count_label.text()
        
        # Add one task
        column.add_task(sample_task)
        assert "1 task" in column.count_label.text()
        
        # Add another task
        task2 = sample_task.copy()
        task2["id"] = "test-task-456"
        column.add_task(task2)
        assert "2 tasks" in column.count_label.text()
        
        # Clear tasks
        column.clear_tasks()
        assert "0 task" in column.count_label.text()


class TestTaskCreationDialog:
    """Tests for TaskCreationDialog."""
    
    def test_dialog_initialization(self, qapp, orchestrator):
        """Test that dialog initializes correctly."""
        dialog = TaskCreationDialog(orchestrator)
        
        assert dialog is not None
        assert dialog.windowTitle() == "Create New Task"
    
    def test_dialog_has_required_fields(self, qapp, orchestrator):
        """Test that dialog has all required input fields."""
        dialog = TaskCreationDialog(orchestrator)
        
        assert dialog.title_input is not None
        assert dialog.description_input is not None
        assert dialog.agent_combo is not None
        assert dialog.task_type_combo is not None
        assert dialog.requires_review_checkbox is not None
    
    def test_requires_review_default_checked(self, qapp, orchestrator):
        """Test that requires review checkbox is checked by default."""
        dialog = TaskCreationDialog(orchestrator)

        assert dialog.requires_review_checkbox.isChecked() is True

    def test_get_task_data(self, qapp, orchestrator):
        """Test getting task data from the dialog."""
        dialog = TaskCreationDialog(orchestrator)

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

    def test_get_task_data_with_review_unchecked(self, qapp, orchestrator):
        """Test getting task data with review unchecked."""
        dialog = TaskCreationDialog(orchestrator)

        dialog.title_input.setPlainText("No Review Task")
        dialog.requires_review_checkbox.setChecked(False)

        task_data = dialog.get_task_data()

        assert task_data["requires_review"] is False

    def test_agent_combo_populated(self, qapp, orchestrator):
        """Test that agent combo is populated with agents."""
        # Register some test agents
        from src.agents.game_programmer_agent import GameProgrammerAgent
        from src.agents.game_designer_agent import GameDesignerAgent

        programmer = GameProgrammerAgent()
        designer = GameDesignerAgent()

        orchestrator.register_agent(programmer)
        orchestrator.register_agent(designer)

        dialog = TaskCreationDialog(orchestrator)

        # Should have at least the registered agents
        assert dialog.agent_combo.count() >= 2


class TestKanbanBoard:
    """Tests for KanbanBoard widget."""

    def test_kanban_board_initialization(self, qapp, orchestrator):
        """Test that Kanban board initializes correctly."""
        board = KanbanBoard(orchestrator)

        assert board is not None
        assert board.orchestrator == orchestrator
        assert len(board.tasks) == 0

    def test_kanban_board_has_four_columns(self, qapp, orchestrator):
        """Test that Kanban board has all four columns."""
        board = KanbanBoard(orchestrator)

        assert board.todo_column is not None
        assert board.in_progress_column is not None
        assert board.review_column is not None
        assert board.done_column is not None

        assert board.todo_column.state == "todo"
        assert board.in_progress_column.state == "in_progress"
        assert board.review_column.state == "review"
        assert board.done_column.state == "done"

    def test_add_task_to_board(self, qapp, orchestrator, sample_task):
        """Test adding a task to the board."""
        board = KanbanBoard(orchestrator)

        board.add_task(sample_task)

        assert len(board.tasks) == 1
        assert "test-task-123" in board.tasks
        assert board.tasks["test-task-123"] == sample_task

    def test_add_task_to_correct_column(self, qapp, orchestrator, sample_task):
        """Test that tasks are added to the correct column based on state."""
        board = KanbanBoard(orchestrator)

        # Add task to todo
        sample_task["state"] = "todo"
        board.add_task(sample_task)
        assert len(board.todo_column.tasks) == 1

        # Add task to in_progress
        task2 = sample_task.copy()
        task2["id"] = "task-2"
        task2["state"] = "in_progress"
        board.add_task(task2)
        assert len(board.in_progress_column.tasks) == 1

        # Add task to review
        task3 = sample_task.copy()
        task3["id"] = "task-3"
        task3["state"] = "review"
        board.add_task(task3)
        assert len(board.review_column.tasks) == 1

        # Add task to done
        task4 = sample_task.copy()
        task4["id"] = "task-4"
        task4["state"] = "done"
        board.add_task(task4)
        assert len(board.done_column.tasks) == 1

    def test_update_task_state(self, qapp, orchestrator, sample_task):
        """Test updating a task's state."""
        board = KanbanBoard(orchestrator)

        # Add task to todo
        sample_task["state"] = "todo"
        board.add_task(sample_task)

        # Update to in_progress
        board.update_task_state("test-task-123", "in_progress")

        assert board.tasks["test-task-123"]["state"] == "in_progress"
        assert len(board.in_progress_column.tasks) == 1
        assert len(board.todo_column.tasks) == 0

    def test_refresh_board(self, qapp, orchestrator, sample_task):
        """Test refreshing the board display."""
        board = KanbanBoard(orchestrator)

        # Add multiple tasks
        board.add_task(sample_task)

        task2 = sample_task.copy()
        task2["id"] = "task-2"
        task2["state"] = "in_progress"
        board.add_task(task2)

        # Refresh should maintain all tasks
        board.refresh_board()

        assert len(board.tasks) == 2
        assert len(board.todo_column.tasks) == 1
        assert len(board.in_progress_column.tasks) == 1

    def test_add_task_without_id(self, qapp, orchestrator):
        """Test that adding a task without ID is handled gracefully."""
        board = KanbanBoard(orchestrator)

        invalid_task = {
            "title": "No ID Task",
            "state": "todo"
        }

        board.add_task(invalid_task)

        # Should not be added
        assert len(board.tasks) == 0

    def test_signals_emitted(self, qapp, orchestrator, sample_task):
        """Test that signals are emitted correctly."""
        board = KanbanBoard(orchestrator)

        # Track signal emissions
        task_created_emitted = []
        task_state_changed_emitted = []

        board.task_created.connect(lambda data: task_created_emitted.append(data))
        board.task_state_changed.connect(lambda id, state: task_state_changed_emitted.append((id, state)))

        # Add task (should emit task_created when created via dialog, not directly)
        board.add_task(sample_task)

        # Update state (should emit task_state_changed)
        board.update_task_state("test-task-123", "in_progress")

        assert len(task_state_changed_emitted) == 1
        assert task_state_changed_emitted[0] == ("test-task-123", "in_progress")

