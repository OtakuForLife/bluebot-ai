"""Tests for the Game Artist Agent."""

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.game_artist_agent import GameArtistAgent


@pytest.mark.asyncio
async def test_game_artist_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = GameArtistAgent()

    assert agent.name == "GameArtist"
    assert agent.role == "game_artist"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None
    assert len(agent.asset_registry) == 0


@pytest.mark.asyncio
async def test_load_art_docs() -> None:
    """Test loading art documentation."""
    # Create temporary docs directory
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)

        # Create some mock art documentation files
        (docs_path / "sprite_guide.md").write_text(
            "# Sprite Creation\n\n2D sprite techniques.", encoding="utf-8"
        )
        (docs_path / "3d_modeling.md").write_text(
            "# 3D Modeling\n\n3D model creation guide.", encoding="utf-8"
        )
        (docs_path / "animation.md").write_text(
            "# Animation\n\nAnimation best practices.", encoding="utf-8"
        )

        # Initialize agent with docs path
        agent = GameArtistAgent(art_docs_path=docs_path)

        # Verify docs were loaded
        summary = agent.get_knowledge_summary()
        assert summary["document_count"] == 3
        assert summary["loaded"] is True


@pytest.mark.asyncio
async def test_set_project_path() -> None:
    """Test setting the project path."""
    agent = GameArtistAgent()
    project_path = Path("/path/to/project")

    agent.set_project_path(project_path)

    assert agent.project_path == project_path


@pytest.mark.asyncio
async def test_create_sprite() -> None:
    """Test creating a sprite asset."""
    agent = GameArtistAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create sprite task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_sprite", "sprite_name": "player_sprite"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the sprite was registered
    assets = agent.get_asset_registry()
    assert "player_sprite" in assets
    assert assets["player_sprite"]["type"] == "sprite"
    assert assets["player_sprite"]["status"] == "created"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_model() -> None:
    """Test creating a 3D model."""
    agent = GameArtistAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create model task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_model", "model_name": "character_model"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the model was registered
    assets = agent.get_asset_registry()
    assert "character_model" in assets
    assert assets["character_model"]["type"] == "model"
    assert assets["character_model"]["status"] == "created"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_animation() -> None:
    """Test creating an animation."""
    agent = GameArtistAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create animation task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_animation", "animation_name": "walk_cycle"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the animation was registered
    assets = agent.get_asset_registry()
    assert "walk_cycle" in assets
    assert assets["walk_cycle"]["type"] == "animation"
    assert assets["walk_cycle"]["status"] == "created"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_design_ui() -> None:
    """Test designing UI elements."""
    agent = GameArtistAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a design UI task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "design_ui", "ui_element": "health_bar"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the UI element was registered
    assets = agent.get_asset_registry()
    assert "health_bar" in assets
    assert assets["health_bar"]["type"] == "ui"
    assert assets["health_bar"]["status"] == "designed"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass

