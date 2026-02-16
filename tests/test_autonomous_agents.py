"""Tests for autonomous agent behavior."""

import pytest
import asyncio
from uuid import uuid4

from src.agents.game_producer_agent import GameProducerAgent
from src.agents.game_programmer_agent import GameProgrammerAgent
from src.agents.game_designer_agent import GameDesignerAgent
from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.task_manager import TaskManager
from src.orchestrator.message_bus import MessageBus


@pytest.fixture
def orchestrator():
    """Create an orchestrator for testing."""
    return Orchestrator()


@pytest.fixture
def task_manager(orchestrator):
    """Get the task manager from orchestrator."""
    return orchestrator.task_manager


@pytest.fixture
def producer_agent():
    """Create a Game Producer agent for testing."""
    return GameProducerAgent(name="Game Producer")


@pytest.fixture
def programmer_agent():
    """Create a Game Programmer agent for testing."""
    return GameProgrammerAgent(name="Game Programmer")


@pytest.fixture
def designer_agent():
    """Create a Game Designer agent for testing."""
    return GameDesignerAgent(name="Game Designer")


@pytest.mark.asyncio
async def test_agent_has_task_manager_after_registration(orchestrator, programmer_agent):
    """Test that agents get task manager when registered."""
    assert programmer_agent.task_manager is None
    
    orchestrator.register_agent(programmer_agent)
    
    assert programmer_agent.task_manager is not None
    assert programmer_agent.task_manager == orchestrator.task_manager


@pytest.mark.asyncio
async def test_agent_discover_tasks(orchestrator, programmer_agent, task_manager):
    """Test agent can discover available tasks."""
    orchestrator.register_agent(programmer_agent)
    
    # Create a task for the programmer
    await task_manager.create_task(
        title="Test Script Task",
        description="Create a test script",
        agent="Game Programmer",
        task_type="create_script"
    )
    
    # Discover tasks
    available_tasks = await programmer_agent.discover_tasks()
    
    assert len(available_tasks) == 1
    assert available_tasks[0]["title"] == "Test Script Task"
    assert available_tasks[0]["agent"] == "Game Programmer"


@pytest.mark.asyncio
async def test_agent_claim_task(orchestrator, programmer_agent, task_manager):
    """Test agent can claim a task."""
    orchestrator.register_agent(programmer_agent)
    
    # Create a task
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )
    
    task_id = task["id"]
    
    # Claim the task
    success = await programmer_agent.claim_task(task_id)
    
    assert success is True
    
    # Verify task was claimed
    claimed_task = await task_manager.get_task(task_id)
    assert claimed_task["claimed_by"] == str(programmer_agent.id)
    assert claimed_task["state"] == "in_progress"


@pytest.mark.asyncio
async def test_agent_complete_task(orchestrator, programmer_agent, task_manager):
    """Test agent can complete a task."""
    orchestrator.register_agent(programmer_agent)
    
    # Create and claim a task
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=False
    )
    
    task_id = task["id"]
    await programmer_agent.claim_task(task_id)
    
    # Complete the task
    result = {"status": "success", "files": ["test.gd"]}
    success = await programmer_agent.complete_task(task_id, result)
    
    assert success is True
    
    # Verify task was completed
    completed_task = await task_manager.get_task(task_id)
    assert completed_task["state"] == "done"
    assert completed_task["metadata"]["result"] == result


@pytest.mark.asyncio
async def test_agent_create_task(orchestrator, producer_agent, task_manager):
    """Test agent can create a task."""
    orchestrator.register_agent(producer_agent)
    
    # Create a task
    task = await producer_agent.create_task(
        title="New Task",
        description="Task created by agent",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=True,
        metadata={"priority": "high"}
    )
    
    assert task is not None
    assert task["title"] == "New Task"
    assert task["created_by"] == str(producer_agent.id)
    assert task["metadata"]["priority"] == "high"
    
    # Verify task exists in task manager
    all_tasks = await task_manager.get_all_tasks()
    assert len(all_tasks) == 1
    assert all_tasks[0]["id"] == task["id"]


@pytest.mark.asyncio
async def test_producer_creates_initial_tasks(orchestrator, producer_agent, task_manager):
    """Test producer creates initial tasks when vision is approved."""
    orchestrator.register_agent(producer_agent)
    
    # Enable autonomous mode and approve vision
    producer_agent.autonomous_mode = True
    producer_agent.vision_approved = True
    
    # Call autonomous tick
    await producer_agent.on_autonomous_tick()
    
    # Verify initial tasks were created
    all_tasks = await task_manager.get_all_tasks()
    assert len(all_tasks) == 5  # Producer creates 5 initial tasks
    
    # Verify task types
    task_titles = [task["title"] for task in all_tasks]
    assert "Define Core Game Mechanics" in task_titles
    assert "Create Art Style Guide" in task_titles
    assert "Set Up Project Structure" in task_titles
    assert "Define Audio Style" in task_titles
    assert "Create Test Plan" in task_titles


@pytest.mark.asyncio
async def test_producer_doesnt_create_duplicate_tasks(orchestrator, producer_agent, task_manager):
    """Test producer doesn't create initial tasks if they already exist."""
    orchestrator.register_agent(producer_agent)

    # Enable autonomous mode and approve vision
    producer_agent.autonomous_mode = True
    producer_agent.vision_approved = True

    # Call autonomous tick first time
    await producer_agent.on_autonomous_tick()

    # Verify tasks were created
    all_tasks = await task_manager.get_all_tasks()
    assert len(all_tasks) == 5

    # Call autonomous tick again
    await producer_agent.on_autonomous_tick()

    # Verify no duplicate tasks were created
    all_tasks = await task_manager.get_all_tasks()
    assert len(all_tasks) == 5


@pytest.mark.asyncio
async def test_programmer_autonomous_tick_discovers_and_claims_task(orchestrator, programmer_agent, task_manager):
    """Test programmer agent discovers and claims tasks autonomously."""
    orchestrator.register_agent(programmer_agent)

    # Create a task for the programmer
    task = await task_manager.create_task(
        title="Setup Project",
        description="Initialize project structure",
        agent="Game Programmer",
        task_type="setup_project",
        requires_review=False
    )

    task_id = task["id"]

    # Enable autonomous mode
    programmer_agent.autonomous_mode = True

    # Call autonomous tick
    await programmer_agent.on_autonomous_tick()

    # Wait a bit for async execution
    await asyncio.sleep(0.1)

    # Verify task was claimed and completed
    completed_task = await task_manager.get_task(task_id)
    assert completed_task["claimed_by"] == str(programmer_agent.id)
    # Task should be completed (state = done)
    assert completed_task["state"] == "done"


@pytest.mark.asyncio
async def test_designer_autonomous_tick_discovers_and_claims_task(orchestrator, designer_agent, task_manager):
    """Test designer agent discovers and claims tasks autonomously."""
    orchestrator.register_agent(designer_agent)

    # Create a task for the designer
    task = await task_manager.create_task(
        title="Define Core Mechanics",
        description="Design the core gameplay mechanics",
        agent="Game Designer",
        task_type="design_mechanics",
        requires_review=False
    )

    task_id = task["id"]

    # Enable autonomous mode
    designer_agent.autonomous_mode = True

    # Call autonomous tick
    await designer_agent.on_autonomous_tick()

    # Wait a bit for async execution
    await asyncio.sleep(0.1)

    # Verify task was claimed and completed
    completed_task = await task_manager.get_task(task_id)
    assert completed_task["claimed_by"] == str(designer_agent.id)
    assert completed_task["state"] == "done"


@pytest.mark.asyncio
async def test_agent_autonomous_tick_when_disabled(orchestrator, programmer_agent, task_manager):
    """Test agent doesn't process tasks when autonomous mode is disabled."""
    orchestrator.register_agent(programmer_agent)

    # Create a task
    task = await task_manager.create_task(
        title="Test Task",
        description="Test description",
        agent="Game Programmer",
        task_type="create_script"
    )

    task_id = task["id"]

    # Autonomous mode is disabled by default
    assert programmer_agent.autonomous_mode is False

    # Call autonomous tick
    await programmer_agent.on_autonomous_tick()

    # Verify task was NOT claimed
    unclaimed_task = await task_manager.get_task(task_id)
    assert unclaimed_task["claimed_by"] is None
    assert unclaimed_task["state"] == "todo"


@pytest.mark.asyncio
async def test_agent_autonomous_tick_with_no_tasks(orchestrator, programmer_agent, task_manager):
    """Test agent handles autonomous tick when no tasks are available."""
    orchestrator.register_agent(programmer_agent)

    # Enable autonomous mode
    programmer_agent.autonomous_mode = True

    # Call autonomous tick with no tasks
    await programmer_agent.on_autonomous_tick()

    # Should not raise any errors
    # Verify no tasks exist
    all_tasks = await task_manager.get_all_tasks()
    assert len(all_tasks) == 0


@pytest.mark.asyncio
async def test_multiple_agents_claim_different_tasks(orchestrator, programmer_agent, designer_agent, task_manager):
    """Test multiple agents can claim different tasks."""
    orchestrator.register_agent(programmer_agent)
    orchestrator.register_agent(designer_agent)

    # Create tasks for different agents
    prog_task = await task_manager.create_task(
        title="Programmer Task",
        description="Programming work",
        agent="Game Programmer",
        task_type="create_script",
        requires_review=False
    )

    design_task = await task_manager.create_task(
        title="Designer Task",
        description="Design work",
        agent="Game Designer",
        task_type="design_mechanics",
        requires_review=False
    )

    # Enable autonomous mode for both
    programmer_agent.autonomous_mode = True
    designer_agent.autonomous_mode = True

    # Call autonomous tick for both
    await programmer_agent.on_autonomous_tick()
    await designer_agent.on_autonomous_tick()

    # Wait for async execution
    await asyncio.sleep(0.1)

    # Verify each agent claimed their respective task
    prog_task_result = await task_manager.get_task(prog_task["id"])
    design_task_result = await task_manager.get_task(design_task["id"])

    assert prog_task_result["claimed_by"] == str(programmer_agent.id)
    assert design_task_result["claimed_by"] == str(designer_agent.id)

    # Both should be completed
    assert prog_task_result["state"] == "done"
    assert design_task_result["state"] == "done"


