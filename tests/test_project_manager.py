"""Tests for ProjectManager class."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.agents.base import AgentRole
from src.commands import CommandBus
from src.events import EventHandler, EventType, Event
from src.project.manager import ProjectManager
from src.project.tasks import TaskStatus


@pytest.fixture
def project_manager():
    """Create a ProjectManager instance with a real EventHandler.

    ProjectManager subscribes to TASK_CREATED / TASK_UPDATED / TASK_ASSIGNED
    to keep its in-memory store current, so a real EventHandler is required —
    a Mock would swallow emit_event calls and the subscriptions would never fire.
    """
    return ProjectManager(event_handler=EventHandler())


class TestProjectManager:
    """Tests for ProjectManager class."""

    def test_initialization(self, project_manager) -> None:
        """Test that ProjectManager initializes correctly."""
        assert project_manager is not None
        assert project_manager.event_handler is not None
        assert len(project_manager.get_tasks()) == 0

    def test_add_task(self, project_manager) -> None:
        """Test adding a task."""
        task = {
            "id": "task-1",
            "type": AgentRole.GAME_PRODUCER,
            "title": "Create game vision",
            "description": "Create game vision document",
            "status": "todo",
            "requires_review": False,
            "created_at": datetime.now(),
            "created_by": None,
            "completed_at": None,
        }
        project_manager.add_task(task)

        # Verify task was added — the task being present proves the
        # TASK_CREATED event was both emitted and handled by the subscription.
        tasks = project_manager.get_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "task-1"

    def test_get_task_existing(self, project_manager) -> None:
        """Test getting an existing task."""
        task = {
            "id": "task-1",
            "type": AgentRole.GAME_PRODUCER,
            "title": "Create game vision",
            "description": "Create game vision document",
            "status": "todo",
            "requires_review": False,
            "created_at": datetime.now(),
            "created_by": None,
            "completed_at": None,
        }
        project_manager.add_task(task)

        retrieved = project_manager.get_task("task-1")
        assert retrieved is not None
        assert retrieved["id"] == "task-1"

    def test_get_task_nonexistent(self, project_manager) -> None:
        """Test getting a non-existent task returns None."""
        retrieved = project_manager.get_task("nonexistent")
        assert retrieved is None

    def test_update_task_existing(self, project_manager) -> None:
        """Test updating an existing task."""
        task = {
            "id": "task-1",
            "type": AgentRole.GAME_PRODUCER,
            "title": "Create game vision",
            "description": "Create game vision document",
            "status": "todo",
            "requires_review": False,
            "created_at": datetime.now(),
            "created_by": None,
            "completed_at": None,
        }
        project_manager.add_task(task)

        updates = {"status": "in_progress"}
        project_manager.update_task("task-1", updates)

        # Verify task was updated (status changed, other fields preserved)
        task = project_manager.get_task("task-1")
        assert task["status"] == "in_progress"
        assert task["title"] == "Create game vision"

    def test_update_task_nonexistent(self, project_manager) -> None:
        """Test updating a non-existent task doesn't error."""
        updates = {"status": "completed"}
        project_manager.update_task("nonexistent", updates)

        # Should not raise error and should not add task
        tasks = project_manager.get_tasks()
        assert len(tasks) == 0

    def test_get_tasks_empty(self, project_manager) -> None:
        """Test getting tasks when empty."""
        tasks = project_manager.get_tasks()
        assert tasks == []

    def test_get_tasks_multiple(self, project_manager) -> None:
        """Test getting multiple tasks."""
        base_task = {
            "type": AgentRole.GAME_PRODUCER,
            "title": "Create game vision",
            "description": "Create game vision document",
            "status": "todo",
            "requires_review": False,
            "created_at": datetime.now(),
            "created_by": None,
            "completed_at": None,
        }
        task1 = {**base_task, "id": "task-1"}
        task2 = {**base_task, "id": "task-2"}
        task3 = {**base_task, "id": "task-3"}

        project_manager.add_task(task1)
        project_manager.add_task(task2)
        project_manager.add_task(task3)

        tasks = project_manager.get_tasks()
        assert len(tasks) == 3
        task_ids = [t["id"] for t in tasks]
        assert set(task_ids) == {"task-1", "task-2", "task-3"}


class TestTaskMarketplace:
    """Tests for the task-pull marketplace: get_next_open_task and claim_task."""

    def _open_task(self, task_id: str, task_type: str) -> dict:
        """Return a minimal marketplace task dict."""
        return {
            "id": task_id,
            "title": f"Task {task_id}",
            "description": f"Description for {task_id}",
            "task_type": task_type,
            "state": TaskStatus.OPEN.value,
            "acceptance_criteria": [],
        }

    # ── get_next_open_task ────────────────────────────────────────────────────

    def test_get_next_open_task_returns_none_when_empty(self, project_manager) -> None:
        """Empty marketplace returns None for any capability list."""
        result = project_manager.get_next_open_task(["design", "art"])
        assert result is None

    def test_get_next_open_task_returns_matching_task(self, project_manager) -> None:
        """Returns the first task whose task_type is in the capabilities list."""
        project_manager.add_task(self._open_task("t1", "design"))
        result = project_manager.get_next_open_task(["design"])
        assert result is not None
        assert result["id"] == "t1"
        assert result["task_type"] == "design"

    def test_get_next_open_task_ignores_non_matching_type(self, project_manager) -> None:
        """Tasks whose task_type is not in capabilities are skipped."""
        project_manager.add_task(self._open_task("t1", "art"))
        result = project_manager.get_next_open_task(["design"])
        assert result is None

    def test_get_next_open_task_skips_in_progress_tasks(self, project_manager) -> None:
        """Tasks already IN_PROGRESS are not returned."""
        project_manager.add_task(self._open_task("t1", "design"))
        # Claim it to move it to IN_PROGRESS.
        project_manager.claim_task("t1", "game_designer")
        result = project_manager.get_next_open_task(["design"])
        assert result is None

    def test_get_next_open_task_returns_oldest_when_multiple(self, project_manager) -> None:
        """Insertion order is preserved — oldest task is returned first."""
        project_manager.add_task(self._open_task("t1", "design"))
        project_manager.add_task(self._open_task("t2", "design"))
        result = project_manager.get_next_open_task(["design"])
        assert result is not None
        assert result["id"] == "t1"

    def test_get_next_open_task_returns_copy(self, project_manager) -> None:
        """Returned dict is a copy; mutating it does not affect the store."""
        project_manager.add_task(self._open_task("t1", "design"))
        result = project_manager.get_next_open_task(["design"])
        assert result is not None
        result["state"] = "mutated"
        stored = project_manager.get_task("t1")
        assert stored is not None
        assert stored["state"] == TaskStatus.OPEN.value

    # ── claim_task ────────────────────────────────────────────────────────────

    def test_claim_task_returns_true_for_open_task(self, project_manager) -> None:
        """claim_task returns True when the task is OPEN."""
        project_manager.add_task(self._open_task("t1", "design"))
        assert project_manager.claim_task("t1", "game_designer") is True

    def test_claim_task_moves_task_to_in_progress(self, project_manager) -> None:
        """After claiming, the task state must be IN_PROGRESS."""
        project_manager.add_task(self._open_task("t1", "design"))
        project_manager.claim_task("t1", "game_designer")
        task = project_manager.get_task("t1")
        assert task is not None
        assert task["state"] == TaskStatus.IN_PROGRESS.value

    def test_claim_task_records_agent_name(self, project_manager) -> None:
        """After claiming, the task 'agent' field is set to the claimant."""
        project_manager.add_task(self._open_task("t1", "design"))
        project_manager.claim_task("t1", "game_designer")
        task = project_manager.get_task("t1")
        assert task is not None
        assert task["agent"] == "game_designer"

    def test_claim_task_returns_false_for_nonexistent_task(self, project_manager) -> None:
        """Claiming an unknown task ID returns False."""
        assert project_manager.claim_task("no-such-id", "agent") is False

    def test_claim_task_returns_false_when_already_claimed(self, project_manager) -> None:
        """A task already IN_PROGRESS cannot be claimed again."""
        project_manager.add_task(self._open_task("t1", "design"))
        project_manager.claim_task("t1", "game_designer")
        assert project_manager.claim_task("t1", "game_designer_2") is False

    def test_claim_task_emits_task_assigned_event(self, project_manager) -> None:
        """claim_task emits a TASK_ASSIGNED event."""
        received: list[Event] = []
        project_manager.event_handler.subscribe(
            EventType.TASK_ASSIGNED, received.append
        )
        project_manager.add_task(self._open_task("t1", "design"))
        project_manager.claim_task("t1", "game_designer")
        assert len(received) == 1
        assert received[0]["payload"]["task_id"] == "t1"
        assert received[0]["payload"]["agent_name"] == "game_designer"

    # ── allocation_mode ───────────────────────────────────────────────────────

    def test_allocation_mode_default_is_auto_pull(self, project_manager) -> None:
        """Default allocation mode is 'auto_pull'."""
        assert project_manager.allocation_mode == "auto_pull"

    def test_set_allocation_mode_changes_mode(self, project_manager) -> None:
        """set_allocation_mode updates the allocation_mode property."""
        project_manager.set_allocation_mode("manual_assignment")
        assert project_manager.allocation_mode == "manual_assignment"

    def test_set_allocation_mode_emits_event(self, project_manager) -> None:
        """set_allocation_mode emits TASK_ALLOCATION_MODE_CHANGED."""
        received: list[Event] = []
        project_manager.event_handler.subscribe(
            EventType.TASK_ALLOCATION_MODE_CHANGED, received.append
        )
        project_manager.set_allocation_mode("manual_assignment")
        assert len(received) == 1
        assert received[0]["payload"]["mode"] == "manual_assignment"

    def test_set_allocation_mode_raises_on_invalid_mode(self, project_manager) -> None:
        """set_allocation_mode raises ValueError for unknown modes."""
        with pytest.raises(ValueError, match="Unknown allocation mode"):
            project_manager.set_allocation_mode("invalid_mode")
