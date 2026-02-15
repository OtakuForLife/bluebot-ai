"""Tests for the Audio Engineer Agent."""

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.audio_engineer_agent import AudioEngineerAgent


@pytest.mark.asyncio
async def test_audio_engineer_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = AudioEngineerAgent()

    assert agent.name == "AudioEngineer"
    assert agent.role == "audio_engineer"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None
    assert len(agent.audio_assets) == 0


@pytest.mark.asyncio
async def test_add_sound_effect() -> None:
    """Test adding a sound effect."""
    agent = AudioEngineerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send an add sound effect request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "add_sound_effect",
            "sound_name": "jump_sound",
            "sound_type": "player_action",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the sound effect was added
    assets = agent.get_audio_assets()
    assert "jump_sound" in assets
    assert assets["jump_sound"]["type"] == "sound_effect"
    assert assets["jump_sound"]["sound_type"] == "player_action"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_music() -> None:
    """Test creating music."""
    agent = AudioEngineerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create music request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "create_music",
            "music_name": "main_theme",
            "style": "orchestral",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the music was created
    assets = agent.get_audio_assets()
    assert "main_theme" in assets
    assert assets["main_theme"]["type"] == "music"
    assert assets["main_theme"]["style"] == "orchestral"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_load_audio_docs() -> None:
    """Test loading audio documentation."""
    # Create temporary docs directory
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)

        # Create some mock audio documentation files
        (docs_path / "sound_design.md").write_text(
            "# Sound Design\n\nSound effect creation techniques.", encoding="utf-8"
        )
        (docs_path / "music_composition.md").write_text(
            "# Music Composition\n\nMusic composition guide.", encoding="utf-8"
        )

        # Initialize agent with docs path
        agent = AudioEngineerAgent(audio_docs_path=docs_path)

        # Verify docs were loaded
        summary = agent.get_knowledge_summary()
        assert summary["document_count"] == 2
        assert summary["loaded"] is True


@pytest.mark.asyncio
async def test_set_project_path() -> None:
    """Test setting the project path."""
    agent = AudioEngineerAgent()
    project_path = Path("/path/to/project")

    agent.set_project_path(project_path)

    assert agent.project_path == project_path

