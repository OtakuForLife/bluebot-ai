"""Tests for the message bus."""

import asyncio
from uuid import uuid4

import pytest

from src.agents.base import Message, MessageType
from src.orchestrator.message_bus import MessageBus


@pytest.mark.asyncio
async def test_message_bus_initialization() -> None:
    """Test that a message bus initializes correctly."""
    bus = MessageBus()

    assert bus._running is False
    assert len(bus._subscribers) == 0
    assert bus.get_stats()["messages_sent"] == 0


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe() -> None:
    """Test subscribing and unsubscribing agents."""
    bus = MessageBus()
    agent_id = uuid4()
    received_messages: list[Message] = []

    async def handler(message: Message) -> None:
        received_messages.append(message)

    # Subscribe
    bus.subscribe(agent_id, handler)
    assert agent_id in bus._subscribers

    # Unsubscribe
    bus.unsubscribe(agent_id)
    assert agent_id not in bus._subscribers


@pytest.mark.asyncio
async def test_direct_message_delivery() -> None:
    """Test that direct messages are delivered to the correct recipient."""
    bus = MessageBus()
    agent1_id = uuid4()
    agent2_id = uuid4()
    received_messages: list[Message] = []

    async def handler(message: Message) -> None:
        received_messages.append(message)

    # Subscribe both agents
    bus.subscribe(agent1_id, handler)
    bus.subscribe(agent2_id, handler)

    # Start the bus
    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.1)

    # Send a direct message from agent1 to agent2
    message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=agent1_id,
        recipient_id=agent2_id,
        payload={"task": "test_task"},
    )

    await bus.publish(message)
    await asyncio.sleep(0.2)

    # Verify the message was delivered
    assert len(received_messages) == 1
    assert received_messages[0].recipient_id == agent2_id
    assert received_messages[0].payload["task"] == "test_task"

    # Clean up
    await bus.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_broadcast_message_delivery() -> None:
    """Test that broadcast messages are delivered to all subscribers."""
    bus = MessageBus()
    agent1_id = uuid4()
    agent2_id = uuid4()
    agent3_id = uuid4()

    agent1_messages: list[Message] = []
    agent2_messages: list[Message] = []
    agent3_messages: list[Message] = []

    async def handler1(message: Message) -> None:
        agent1_messages.append(message)

    async def handler2(message: Message) -> None:
        agent2_messages.append(message)

    async def handler3(message: Message) -> None:
        agent3_messages.append(message)

    # Subscribe all agents
    bus.subscribe(agent1_id, handler1)
    bus.subscribe(agent2_id, handler2)
    bus.subscribe(agent3_id, handler3)

    # Start the bus
    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.1)

    # Send a broadcast message (no recipient_id)
    message = Message(
        id=uuid4(),
        type=MessageType.STATUS_UPDATE,
        sender_id=agent1_id,
        recipient_id=None,  # Broadcast
        payload={"status": "ready"},
    )

    await bus.publish(message)
    await asyncio.sleep(0.2)

    # Verify the message was broadcast to all except sender
    assert len(agent1_messages) == 0  # Sender doesn't receive own broadcast
    assert len(agent2_messages) == 1
    assert len(agent3_messages) == 1

    # Clean up
    await bus.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_type_filtered_subscription() -> None:
    """Test that agents can subscribe to specific message types."""
    bus = MessageBus()
    agent1_id = uuid4()
    agent2_id = uuid4()

    agent1_messages: list[Message] = []
    agent2_messages: list[Message] = []

    async def handler1(message: Message) -> None:
        agent1_messages.append(message)

    async def handler2(message: Message) -> None:
        agent2_messages.append(message)

    # Agent1 subscribes to TASK_REQUEST only
    bus.subscribe(agent1_id, handler1, [MessageType.TASK_REQUEST])
    # Agent2 subscribes to STATUS_UPDATE only
    bus.subscribe(agent2_id, handler2, [MessageType.STATUS_UPDATE])

    # Start the bus
    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.1)

    # Send a TASK_REQUEST broadcast
    task_message = Message(
        id=uuid4(),
        type=MessageType.TASK_REQUEST,
        sender_id=uuid4(),
        recipient_id=None,
        payload={"task": "test"},
    )
    await bus.publish(task_message)
    await asyncio.sleep(0.2)

    # Send a STATUS_UPDATE broadcast
    status_message = Message(
        id=uuid4(),
        type=MessageType.STATUS_UPDATE,
        sender_id=uuid4(),
        recipient_id=None,
        payload={"status": "running"},
    )
    await bus.publish(status_message)
    await asyncio.sleep(0.2)

    # Verify filtering worked
    assert len(agent1_messages) == 1
    assert agent1_messages[0].type == MessageType.TASK_REQUEST

    assert len(agent2_messages) == 1
    assert agent2_messages[0].type == MessageType.STATUS_UPDATE

    # Clean up
    await bus.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_message_bus_statistics() -> None:
    """Test that message bus tracks statistics correctly."""
    bus = MessageBus()
    agent_id = uuid4()

    async def handler(message: Message) -> None:
        pass

    bus.subscribe(agent_id, handler)

    # Start the bus
    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(0.1)

    # Send some messages
    for i in range(3):
        message = Message(
            id=uuid4(),
            type=MessageType.TASK_REQUEST,
            sender_id=uuid4(),
            recipient_id=agent_id,
            payload={"index": i},
        )
        await bus.publish(message)

    await asyncio.sleep(0.3)

    # Check statistics
    stats = bus.get_stats()
    assert stats["messages_sent"] == 3
    assert stats["messages_delivered"] == 3

    # Clean up
    await bus.stop()
    bus_task.cancel()
    try:
        await bus_task
    except asyncio.CancelledError:
        pass

