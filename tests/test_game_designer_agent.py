"""Tests for the Game Designer Agent."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.game_designer_agent import GameDesignerAgent
from src.llm import LLMMessage, LLMResponse


@pytest.mark.asyncio
async def test_game_designer_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = GameDesignerAgent()

    assert agent.name == "GameDesigner"
    assert agent.role == "game_designer"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None
    assert len(agent.design_documents) == 0


@pytest.mark.asyncio
async def test_load_design_docs() -> None:
    """Test loading game design documentation."""
    # Create temporary docs directory
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_path = Path(temp_dir)

        # Create some mock design documentation files
        (docs_path / "mechanics.md").write_text(
            "# Game Mechanics\n\nCore gameplay mechanics.", encoding="utf-8"
        )
        (docs_path / "narrative.md").write_text(
            "# Narrative Design\n\nStoryboarding and narrative patterns.", encoding="utf-8"
        )
        (docs_path / "ux_patterns.md").write_text(
            "# UX Patterns\n\nUser experience best practices.", encoding="utf-8"
        )

        # Initialize agent with docs path
        agent = GameDesignerAgent(design_docs_path=docs_path)

        # Verify docs were loaded
        summary = agent.get_knowledge_summary()
        assert summary["document_count"] == 3
        assert summary["loaded"] is True


@pytest.mark.asyncio
async def test_set_project_path() -> None:
    """Test setting the project path."""
    agent = GameDesignerAgent()
    project_path = Path("/path/to/project")

    agent.set_project_path(project_path)

    assert agent.project_path == project_path


@pytest.mark.asyncio
async def test_define_mechanics() -> None:
    """Test defining game mechanics."""
    agent = GameDesignerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a define mechanics task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "define_mechanics", "mechanic_type": "combat"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the mechanics were stored
    design_docs = agent.get_design_documents()
    assert "mechanics_combat" in design_docs
    assert design_docs["mechanics_combat"]["type"] == "combat"
    assert design_docs["mechanics_combat"]["status"] == "defined"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_storyboard() -> None:
    """Test creating a storyboard."""
    agent = GameDesignerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create storyboard task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_storyboard", "scene_name": "intro_scene"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the storyboard was stored
    design_docs = agent.get_design_documents()
    assert "storyboard_intro_scene" in design_docs
    assert design_docs["storyboard_intro_scene"]["scene"] == "intro_scene"
    assert design_docs["storyboard_intro_scene"]["status"] == "created"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_design_ux() -> None:
    """Test designing UX elements."""
    agent = GameDesignerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a design UX task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "design_ux", "element": "main_menu"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the UX design was stored
    design_docs = agent.get_design_documents()
    assert "ux_main_menu" in design_docs
    assert design_docs["ux_main_menu"]["element"] == "main_menu"
    assert design_docs["ux_main_menu"]["status"] == "designed"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_design_document() -> None:
    """Test creating a design document."""
    agent = GameDesignerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create design doc task
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task_type": "create_design_doc", "doc_name": "core_gameplay"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the design document was stored
    design_docs = agent.get_design_documents()
    assert "core_gameplay" in design_docs
    assert design_docs["core_gameplay"]["name"] == "core_gameplay"
    assert design_docs["core_gameplay"]["status"] == "created"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_vision_without_llm() -> None:
    """Test that vision creation fails without LLM provider."""
    agent = GameDesignerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a create vision task without LLM provider
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "create_vision",
            "project_name": "Test Game",
            "description": "A test game",
            "genres": ["Action", "Adventure"],
            "elements": ["Single Player", "Story-driven"],
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Vision should not be created without LLM
    design_docs = agent.get_design_documents()
    assert "vision" not in design_docs

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_create_vision_with_llm() -> None:
    """Test creating a vision document with LLM provider."""
    # Create a mock LLM provider
    mock_llm = MagicMock()
    mock_response = LLMResponse(
        content="""# Game Vision Document

## Executive Summary
This is a test game vision document.

## Game Overview
- Genre: Action, Adventure
- Platform: PC
- Core Loop: Explore, fight, progress

## Vision Statement
Create an engaging experience.

## Unique Selling Points
1. Innovative mechanics
2. Compelling story
3. Beautiful art

## Target Audience
Casual and hardcore gamers

## Scope and Constraints
- Timeline: 6 months
- Team: 5 people

## Success Criteria
- Complete core features
- Positive player feedback
""",
        model="test-model",
        usage={"prompt_tokens": 100, "completion_tokens": 200},
    )
    mock_llm.generate = AsyncMock(return_value=mock_response)

    # Create temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Initialize agent with LLM provider
        agent = GameDesignerAgent(llm_provider=mock_llm)
        agent.set_project_path(project_path)

        # Start the agent
        agent_task = asyncio.create_task(agent.start())
        await asyncio.sleep(0.1)

        # Send a create vision task
        message = Message(
            id=uuid4(),
            type=MessageType.TASK_REQUEST,
            sender_id=uuid4(),
            recipient_id=agent.id,
            payload={
                "task_type": "create_vision",
                "project_name": "Test Game",
                "description": "A test game for vision creation",
                "genres": ["Action", "Adventure"],
                "elements": ["Single Player", "Story-driven"],
            },
        )

        await agent.receive_message(message)
        await asyncio.sleep(0.3)

        # Check that the vision was created
        design_docs = agent.get_design_documents()
        assert "vision" in design_docs
        assert design_docs["vision"]["name"] == "Test Game"
        assert design_docs["vision"]["status"] == "created"
        assert "Game Vision Document" in design_docs["vision"]["content"]

        # Check that the vision file was saved
        vision_file = project_path / "design" / "VISION.md"
        assert vision_file.exists()
        vision_content = vision_file.read_text(encoding="utf-8")
        assert "Game Vision Document" in vision_content
        assert "Executive Summary" in vision_content

        # Verify LLM was called with correct parameters
        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args[0][0]
        assert len(call_args) == 2  # system + user message
        assert call_args[0].role == "system"
        assert call_args[1].role == "user"
        assert "Test Game" in call_args[1].content
        assert "Action" in call_args[1].content

        # Clean up
        await agent.stop()
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass

