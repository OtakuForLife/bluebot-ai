"""Tests for the Game Programmer Agent."""

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.game_programmer_agent import GameProgrammerAgent


@pytest.mark.asyncio
async def test_game_programmer_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = GameProgrammerAgent()

    assert agent.name == "GameProgrammer"
    assert agent.role == "game_programmer"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None


@pytest.mark.asyncio
async def test_load_godot_docs() -> None:
    """Test loading Godot documentation."""
    # Create temporary docs directory
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)

        # Create some mock Godot documentation files
        (docs_path / "getting_started.md").write_text(
            "# Getting Started\n\nLearn Godot basics.", encoding="utf-8"
        )
        (docs_path / "gdscript.md").write_text(
            "# GDScript\n\nGDScript is Godot's scripting language.", encoding="utf-8"
        )
        (docs_path / "physics.md").write_text(
            "# Physics\n\nGodot physics engine documentation.", encoding="utf-8"
        )

        # Initialize agent with docs path
        agent = GameProgrammerAgent(godot_docs_path=docs_path)

        # Verify docs were loaded
        summary = agent.get_knowledge_summary()
        assert summary["document_count"] == 3
        assert summary["loaded"] is True


@pytest.mark.asyncio
async def test_set_project_path() -> None:
    """Test setting the project path."""
    agent = GameProgrammerAgent()
    project_path = Path("/path/to/project")

    agent.set_project_path(project_path)

    assert agent.project_path == project_path


@pytest.mark.asyncio
async def test_process_task_request() -> None:
    """Test processing a task request message."""
    agent = GameProgrammerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a task request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_script", "script_name": "player.gd"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Agent should have processed the message (no errors)
    assert agent.status == AgentStatus.RUNNING

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_process_file_modified() -> None:
    """Test processing a file modified notification."""
    agent = GameProgrammerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a file modified message
    message = Message(
        id=uuid4(),
        type=MessageType.FILE_MODIFIED,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"file_path": "scripts/player.gd"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Agent should have processed the message
    assert agent.status == AgentStatus.RUNNING

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_process_test_result() -> None:
    """Test processing test results."""
    agent = GameProgrammerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a test result message
    message = Message(
        id=uuid4(),
        type=MessageType.TEST_RESULT,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"passed": False, "errors": ["Error 1", "Error 2"]},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Agent should have processed the message
    assert agent.status == AgentStatus.RUNNING

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_knowledge_base_search() -> None:
    """Test that the agent can search its knowledge base."""
    # Create temporary docs
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)
        (docs_path / "physics.md").write_text(
            "# Physics\n\nRigidBody2D and physics simulation.", encoding="utf-8"
        )

        agent = GameProgrammerAgent(godot_docs_path=docs_path)

        # Search for physics documentation
        results = agent.knowledge_base.search("physics")
        assert len(results) >= 1
        assert "RigidBody2D" in results[0][1]

