"""Tests for the Task Manager service."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.agents.base import MessageType
from src.orchestrator.message_bus import MessageBus
from src.orchestrator.task_manager import TaskManager


@pytest.fixture
def message_bus():
    """Create a message bus for testing."""
    return MessageBus()


@pytest.fixture
def task_manager(message_bus):
    """Create a task manager for testing."""
    return TaskManager(message_bus=message_bus)


@pytest.mark.asyncio
async def test_task_manager_initialization(task_manager):
    """Test task manager initializes correctly."""
    assert task_manager is not None
    assert task_manager.message_bus is not None
    assert len(task_manager.tasks) == 0


@pytest.mark.asyncio
async def test_create_task(task_manager):
    """Test creating a task."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=True,
        created_by=None,
        metadata={"test": "data"}
    )
    
    assert task is not None
    assert task["title"] == "Test Task"
    assert task["description"] == "Test description"
    assert task["agent"] == "Game Programmer"
    assert task["task_type"] == "create_script"
    assert task["requires_review"] is True
    assert task["state"] == "todo"
    assert task["created_by"] is None
    assert task["claimed_by"] is None
    assert task["metadata"]["test"] == "data"
    assert "id" in task
    assert "created_at" in task


@pytest.mark.asyncio
async def test_get_task(task_manager):
    """Test retrieving a task by ID."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )
    
    task_id = task["id"]
    retrieved_task = await task_manager.get_task(task_id)
    
    assert retrieved_task is not None
    assert retrieved_task["id"] == task_id
    assert retrieved_task["title"] == "Test Task"


@pytest.mark.asyncio
async def test_get_nonexistent_task(task_manager):
    """Test retrieving a task that doesn't exist."""
    task = await task_manager.get_task("nonexistent-id")
    assert task is None


@pytest.mark.asyncio
async def test_get_all_tasks(task_manager):
    """Test retrieving all tasks."""
    # Create multiple tasks
    await task_manager.create_task(
        title="Task 1",
        description="Description 1",
        agent="Game Programmer",
        task_type="create_script"
    )
    await task_manager.create_task(
        title="Task 2",
        description="Description 2",
        agent="Game Designer",
        task_type="design_mechanics"
    )
    
    all_tasks = await task_manager.get_all_tasks()
    
    assert len(all_tasks) == 2
    assert all_tasks[0]["title"] == "Task 1"
    assert all_tasks[1]["title"] == "Task 2"


@pytest.mark.asyncio
async def test_claim_task(task_manager):
    """Test claiming a task."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )
    
    task_id = task["id"]
    agent_id = uuid4()
    
    success = await task_manager.claim_task(task_id, agent_id)
    
    assert success is True
    
    # Verify task was claimed
    claimed_task = await task_manager.get_task(task_id)
    assert claimed_task["claimed_by"] == str(agent_id)
    assert claimed_task["state"] == "in_progress"
    assert claimed_task["claimed_at"] is not None


@pytest.mark.asyncio
async def test_claim_nonexistent_task(task_manager):
    """Test claiming a task that doesn't exist."""
    agent_id = uuid4()
    success = await task_manager.claim_task("nonexistent-id", agent_id)
    assert success is False


@pytest.mark.asyncio
async def test_claim_already_claimed_task(task_manager):
    """Test claiming a task that's already claimed."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )
    
    task_id = task["id"]
    agent1_id = uuid4()
    agent2_id = uuid4()
    
    # First claim should succeed
    success1 = await task_manager.claim_task(task_id, agent1_id)
    assert success1 is True
    
    # Second claim should fail
    success2 = await task_manager.claim_task(task_id, agent2_id)
    assert success2 is False


@pytest.mark.asyncio
async def test_update_task_state(task_manager):
    """Test updating task state."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )

    task_id = task["id"]

    # Update to in_progress
    success = await task_manager.update_task_state(task_id, "in_progress")
    assert success is True

    updated_task = await task_manager.get_task(task_id)
    assert updated_task["state"] == "in_progress"

    # Update to review
    success = await task_manager.update_task_state(task_id, "review")
    assert success is True

    updated_task = await task_manager.get_task(task_id)
    assert updated_task["state"] == "review"


@pytest.mark.asyncio
async def test_complete_task(task_manager):
    """Test completing a task."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=False  # Don't require review for this test
    )

    task_id = task["id"]
    agent_id = uuid4()

    # Claim the task first
    await task_manager.claim_task(task_id, agent_id)

    # Complete the task
    result = {"status": "success", "files_created": ["test.gd"]}
    success = await task_manager.complete_task(task_id, agent_id, result)

    assert success is True

    # Verify task was completed
    completed_task = await task_manager.get_task(task_id)
    assert completed_task["state"] == "done"
    assert completed_task["completed_at"] is not None
    assert completed_task["metadata"]["result"] == result


@pytest.mark.asyncio
async def test_complete_task_with_review(task_manager):
    """Test completing a task that requires review."""
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=True
    )

    task_id = task["id"]
    agent_id = uuid4()

    # Claim and complete the task
    await task_manager.claim_task(task_id, agent_id)
    success = await task_manager.complete_task(task_id, agent_id)

    assert success is True

    # Task should be in review state, not done
    completed_task = await task_manager.get_task(task_id)
    assert completed_task["state"] == "review"


@pytest.mark.asyncio
async def test_get_available_tasks(task_manager):
    """Test getting available tasks."""
    # Create tasks for different agents
    await task_manager.create_task(
        title="Programmer Task 1",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )
    await task_manager.create_task(
        title="Programmer Task 2",
        description="Description",
        agent="Game Programmer",
        task_type="setup_project"
    )
    await task_manager.create_task(
        title="Designer Task",
        description="Description",
        agent="Game Designer",
        task_type="design_mechanics"
    )

    # Get available tasks for Game Programmer
    programmer_tasks = await task_manager.get_available_tasks(agent_role="Game Programmer")
    assert len(programmer_tasks) == 2
    assert all(task["agent"] == "Game Programmer" for task in programmer_tasks)

    # Get available tasks for Game Designer
    designer_tasks = await task_manager.get_available_tasks(agent_role="Game Designer")
    assert len(designer_tasks) == 1
    assert designer_tasks[0]["agent"] == "Game Designer"


@pytest.mark.asyncio
async def test_get_available_tasks_by_type(task_manager):
    """Test getting available tasks filtered by type."""
    await task_manager.create_task(
        title="Script Task",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )
    await task_manager.create_task(
        title="Setup Task",
        description="Description",
        agent="Game Programmer",
        task_type="setup_project"
    )

    # Get tasks by type
    script_tasks = await task_manager.get_available_tasks(task_type="create_script")
    assert len(script_tasks) == 1
    assert script_tasks[0]["task_type"] == "create_script"


@pytest.mark.asyncio
async def test_get_tasks_by_state(task_manager):
    """Test getting tasks by state."""
    task1 = await task_manager.create_task(
        title="Task 1",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )
    task2 = await task_manager.create_task(
        title="Task 2",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )

    # Claim one task
    await task_manager.claim_task(task1["id"], uuid4())

    # Get tasks by state
    todo_tasks = await task_manager.get_tasks_by_state("todo")
    assert len(todo_tasks) == 1
    assert todo_tasks[0]["id"] == task2["id"]

    in_progress_tasks = await task_manager.get_tasks_by_state("in_progress")
    assert len(in_progress_tasks) == 1
    assert in_progress_tasks[0]["id"] == task1["id"]


@pytest.mark.asyncio
async def test_get_agent_tasks(task_manager):
    """Test getting tasks for a specific agent."""
    agent_id = uuid4()

    task1 = await task_manager.create_task(
        title="Task 1",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )
    task2 = await task_manager.create_task(
        title="Task 2",
        description="Description",
        agent="Game Programmer",
        task_type="create_script"
    )

    # Claim one task
    await task_manager.claim_task(task1["id"], agent_id)

    # Get tasks for this agent
    agent_tasks = await task_manager.get_agent_tasks(agent_id)
    assert len(agent_tasks) == 1
    assert agent_tasks[0]["id"] == task1["id"]

