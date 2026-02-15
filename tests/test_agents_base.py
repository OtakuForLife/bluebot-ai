"""Tests for the base agent class and message types."""

import asyncio
from uuid import uuid4

import pytest

from src.agents.base import Agent, AgentStatus, Message, MessageType


class TestAgent(Agent):
    """Concrete test implementation of Agent for testing purposes."""

    def __init__(self, name: str, role: str) -> None:
        super().__init__(name, role)
        self.processed_messages: list[Message] = []

    async def process_message(self, message: Message) -> None:
        """Store processed messages for test verification."""
        self.processed_messages.append(message)


@pytest.mark.asyncio
async def test_agent_initialization() -> None:
    """Test that an agent initializes with correct default values."""
    agent = TestAgent(name="TestAgent1", role="tester")

    assert agent.name == "TestAgent1"
    assert agent.role == "tester"
    assert agent.status == AgentStatus.IDLE
    assert agent.id is not None
    assert not agent._running


@pytest.mark.asyncio
async def test_agent_start_and_stop() -> None:
    """Test that an agent can start and stop gracefully."""
    agent = TestAgent(name="TestAgent2", role="developer")

    # Start the agent in a task
    agent_task = asyncio.create_task(agent.start())

    # Give it a moment to start
    await asyncio.sleep(0.1)

    assert agent._running
    assert agent.status == AgentStatus.RUNNING

    # Stop the agent
    await agent.stop()
    await asyncio.sleep(0.1)

    assert not agent._running
    assert agent.status == AgentStatus.STOPPED

    # Clean up the task
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_agent_receive_and_process_message() -> None:
    """Test that an agent can receive and process messages."""
    agent = TestAgent(name="TestAgent3", role="tester")

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send a message to the agent
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=agent.id,
        payload={"task": "run_tests"},
    )

    await agent.receive_message(message)

    # Give the agent time to process
    await asyncio.sleep(0.2)

    # Verify the message was processed
    assert len(agent.processed_messages) == 1
    assert agent.processed_messages[0].type == MessageType.TASK_REQUEST
    assert agent.processed_messages[0].payload["task"] == "run_tests"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_message_validation() -> None:
    """Test that Message validates its type field."""
    sender_id = uuid4()
    recipient_id = uuid4()

    # Valid message should work
    valid_message = Message(
        id=uuid4(),
        type=MessageType.STATUS_UPDATE,
        sender_id=sender_id,
        recipient_id=recipient_id,
        payload={"status": "running"},
    )
    assert valid_message.type == MessageType.STATUS_UPDATE

    # Invalid message type should raise ValueError
    with pytest.raises(ValueError, match="Invalid message type"):
        Message(
            id=uuid4(),
            type="invalid_type",  # type: ignore
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload={},
        )


@pytest.mark.asyncio
async def test_agent_processes_multiple_messages() -> None:
    """Test that an agent can process multiple messages in sequence."""
    agent = TestAgent(name="TestAgent4", role="developer")

    # Start the agent
    agent_task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.1)

    # Send multiple messages
    messages = [
        Message(
            id=uuid4(),
            type=MessageType.TASK_REQUEST,
            sender_id=uuid4(),
            recipient_id=agent.id,
            payload={"task": f"task_{i}"},
        )
        for i in range(5)
    ]

    for msg in messages:
        await agent.receive_message(msg)

    # Give the agent time to process all messages
    await asyncio.sleep(0.5)

    # Verify all messages were processed
    assert len(agent.processed_messages) == 5
    for i, processed_msg in enumerate(agent.processed_messages):
        assert processed_msg.payload["task"] == f"task_{i}"

    # Clean up
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass


def test_agent_status_enum() -> None:
    """Test that AgentStatus enum has expected values."""
    assert AgentStatus.IDLE.value == "idle"
    assert AgentStatus.RUNNING.value == "running"
    assert AgentStatus.PAUSED.value == "paused"
    assert AgentStatus.STOPPED.value == "stopped"
    assert AgentStatus.ERROR.value == "error"


def test_message_type_enum() -> None:
    """Test that MessageType enum has expected values."""
    assert MessageType.TASK_REQUEST.value == "task_request"
    assert MessageType.TASK_RESPONSE.value == "task_response"
    assert MessageType.STATUS_UPDATE.value == "status_update"
    assert MessageType.ERROR_REPORT.value == "error_report"
    assert MessageType.FILE_MODIFIED.value == "file_modified"
    assert MessageType.TEST_RESULT.value == "test_result"
    assert MessageType.AGENT_READY.value == "agent_ready"
    assert MessageType.AGENT_SHUTDOWN.value == "agent_shutdown"
    # New vision workflow message types
    assert MessageType.PROJECT_CREATED.value == "project_created"
    assert MessageType.VISION_CREATED.value == "vision_created"
    assert MessageType.VISION_APPROVED.value == "vision_approved"
    assert MessageType.VISION_REJECTED.value == "vision_rejected"

