"""Tests for the Game Producer Agent."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.base import AgentStatus, Message, MessageType
from src.agents.game_producer_agent import GameProducerAgent
from src.llm import LLMMessage, LLMResponse


@pytest.mark.asyncio
async def test_game_producer_agent_initialization() -> None:
    """Test that the agent initializes correctly."""
    agent = GameProducerAgent()

    assert agent.name == "GameProducer"
    assert agent.role == "game_producer"
    assert agent.status == AgentStatus.IDLE
    assert agent.knowledge_base is not None
    assert agent.project_path is None
    assert len(agent.task_assignments) == 0
    assert len(agent.project_timeline) == 0


@pytest.mark.asyncio
async def test_assign_task() -> None:
    """Test assigning a task to an agent."""
    agent = GameProducerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send an assign task request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "assign_task",
            "task_id": "task_001",
            "agent_id": str(uuid4()),
            "description": "Implement player movement",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the task was assigned
    assignments = agent.get_task_assignments()
    assert "task_001" in assignments
    assert assignments["task_001"]["description"] == "Implement player movement"
    assert assignments["task_001"]["status"] == "assigned"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_manage_timeline() -> None:
    """Test managing project timeline."""
    agent = GameProducerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a manage timeline request
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={
            "task_type": "manage_timeline",
            "milestone": "alpha_release",
            "deadline": "2024-12-31",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that the milestone was added
    timeline = agent.get_project_timeline()
    assert "alpha_release" in timeline
    assert timeline["alpha_release"]["deadline"] == "2024-12-31"
    assert timeline["alpha_release"]["status"] == "planned"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_handle_status_update() -> None:
    """Test handling status updates from other agents."""
    agent = GameProducerAgent()

    # First assign a task
    agent_id = str(uuid4())
    agent.task_assignments["task_001"] = {
        "assigned_to": agent_id,
        "description": "Test task",
        "status": "assigned",
        "completed": False,
    }

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a status update
    message = Message(
        id=uuid4(),
        type=MessageType.STATUS_UPDATE,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"role": "game_programmer", "status": "running"},
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Agent should have processed the status update
    assert agent.status == AgentStatus.RUNNING

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_handle_project_created() -> None:
    """Test handling PROJECT_CREATED message."""
    agent = GameProducerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a PROJECT_CREATED message
    message = Message(
        id=uuid4(),
        type=MessageType.PROJECT_CREATED,
        sender_id=uuid4(),
        recipient_id=None,  # Broadcast
        payload={
            "project_name": "Test Game",
            "description": "A test game",
            "genres": ["Action"],
            "elements": ["Single Player"],
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Check that project info was stored
    assert agent.project_info is not None
    assert agent.project_info["project_name"] == "Test Game"
    assert agent.vision_approved is False
    assert agent.autonomous_mode is False

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_handle_vision_approved_without_llm() -> None:
    """Test that vision approval without LLM provider doesn't crash."""
    agent = GameProducerAgent()

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a VISION_APPROVED message without LLM provider
    message = Message(
        id=uuid4(),
        type=MessageType.VISION_APPROVED,
        sender_id=uuid4(),
        recipient_id=None,  # Broadcast
        payload={
            "project_name": "Test Game",
            "vision_content": "# Vision\nTest vision content",
            "project_path": "/tmp/test",
        },
    )

    await agent.receive_message(message)
    await asyncio.sleep(0.2)

    # Agent should have set flags but not created plan
    assert agent.vision_approved is True
    assert agent.autonomous_mode is True

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_handle_vision_approved_with_llm() -> None:
    """Test handling VISION_APPROVED message and creating development plan."""
    # Create a mock LLM provider
    mock_llm = MagicMock()
    mock_response = LLMResponse(
        content="""# Development Plan

## Game Designer Tasks
1. **Define Core Mechanics** - High Priority
   - Description: Define the core gameplay mechanics
   - Dependencies: None
   - Complexity: Medium

2. **Create Level Design** - Medium Priority
   - Description: Design the game levels
   - Dependencies: Define Core Mechanics
   - Complexity: Complex

## Game Programmer Tasks
1. **Set Up Project Structure** - High Priority
   - Description: Initialize Godot project
   - Dependencies: None
   - Complexity: Simple

2. **Implement Core Mechanics** - High Priority
   - Description: Code the core gameplay systems
   - Dependencies: Define Core Mechanics
   - Complexity: Complex

## Game Artist Tasks
1. **Create Art Style Guide** - High Priority
   - Description: Define visual style
   - Dependencies: None
   - Complexity: Medium

## Audio Engineer Tasks
1. **Define Audio Style** - Medium Priority
   - Description: Establish audio direction
   - Dependencies: None
   - Complexity: Simple

## QA Tester Tasks
1. **Create Test Plan** - Medium Priority
   - Description: Define testing strategy
   - Dependencies: None
   - Complexity: Medium
""",
        model="test-model",
        usage={"prompt_tokens": 150, "completion_tokens": 300},
    )
    mock_llm.generate = AsyncMock(return_value=mock_response)

    # Create temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Initialize agent with LLM provider
        agent = GameProducerAgent(llm_provider=mock_llm)
        agent.set_project_path(project_path)

        # Start the agent
        agent_task = asyncio.create_task(agent.start())
        await asyncio.sleep(0.1)

        # Send a VISION_APPROVED message
        vision_content = """# Game Vision

## Executive Summary
This is a test game vision.

## Game Overview
Action-adventure game with innovative mechanics.
"""

        message = Message(
            id=uuid4(),
            type=MessageType.VISION_APPROVED,
            sender_id=uuid4(),
            recipient_id=None,  # Broadcast
            payload={
                "project_name": "Test Game",
                "vision_content": vision_content,
                "project_path": str(project_path),
            },
        )

        await agent.receive_message(message)
        await asyncio.sleep(0.3)

        # Check that autonomous mode was activated
        assert agent.vision_approved is True
        assert agent.autonomous_mode is True

        # Check that development plan was created
        plan_file = project_path / "design" / "DEVELOPMENT_PLAN.md"
        assert plan_file.exists()
        plan_content = plan_file.read_text(encoding="utf-8")
        assert "Development Plan" in plan_content
        assert "Game Designer Tasks" in plan_content
        assert "Game Programmer Tasks" in plan_content

        # Verify LLM was called
        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args[0][0]
        assert len(call_args) == 2  # system + user message
        assert "vision" in call_args[1].content.lower()

        # Clean up
        await agent.stop()
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass

