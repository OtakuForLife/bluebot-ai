"""Tests for the orchestrator service."""

import asyncio
from uuid import uuid4

import pytest

from src.agents.base import Agent, AgentStatus, Message, MessageType
from src.orchestrator.orchestrator import Orchestrator


class MockAgent(Agent):
    """Mock agent for testing purposes."""

    def __init__(self, name: str, role: str) -> None:
        super().__init__(name, role)
        self.processed_messages: list[Message] = []

    async def process_message(self, message: Message) -> None:
        """Store processed messages for verification."""
        self.processed_messages.append(message)


@pytest.mark.asyncio
async def test_orchestrator_initialization() -> None:
    """Test that an orchestrator initializes correctly."""
    orchestrator = Orchestrator()

    assert orchestrator.message_bus is not None
    assert len(orchestrator._agents) == 0
    assert orchestrator._running is False


@pytest.mark.asyncio
async def test_orchestrator_start_and_stop() -> None:
    """Test starting and stopping the orchestrator."""
    orchestrator = Orchestrator()

    await orchestrator.start()
    assert orchestrator._running is True

    await orchestrator.stop()
    assert orchestrator._running is False


@pytest.mark.asyncio
async def test_register_and_unregister_agent() -> None:
    """Test registering and unregistering agents."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent = MockAgent(name="TestAgent", role="tester")

    # Register agent
    orchestrator.register_agent(agent)
    assert agent.id in orchestrator._agents
    assert agent.id in orchestrator.message_bus._subscribers

    # Unregister agent
    orchestrator.unregister_agent(agent.id)
    assert agent.id not in orchestrator._agents
    assert agent.id not in orchestrator.message_bus._subscribers

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_start_and_stop_agent() -> None:
    """Test starting and stopping an agent through the orchestrator."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent = MockAgent(name="TestAgent", role="developer")
    orchestrator.register_agent(agent)

    # Start the agent
    await orchestrator.start_agent(agent.id)
    await asyncio.sleep(0.2)

    assert agent.status == AgentStatus.RUNNING
    assert agent.id in orchestrator._agent_tasks

    # Stop the agent
    await orchestrator.stop_agent(agent.id)
    await asyncio.sleep(0.1)

    assert agent.status == AgentStatus.STOPPED
    assert agent.id not in orchestrator._agent_tasks

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_send_task_to_agent() -> None:
    """Test sending a task to an agent through the orchestrator."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent = MockAgent(name="TestAgent", role="developer")
    orchestrator.register_agent(agent)
    await orchestrator.start_agent(agent.id)
    await asyncio.sleep(0.2)

    # Send a task to the agent
    task_data = {"action": "create_file", "filename": "test.gd"}
    await orchestrator.send_task_to_agent(agent.id, task_data)
    await asyncio.sleep(0.3)

    # Verify the agent received the task
    task_messages = [
        msg for msg in agent.processed_messages
        if msg.type == MessageType.TASK_REQUEST
    ]
    assert len(task_messages) == 1
    assert task_messages[0].payload["action"] == "create_file"

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_get_agent_status() -> None:
    """Test getting agent status through the orchestrator."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent = MockAgent(name="TestAgent", role="tester")
    orchestrator.register_agent(agent)

    # Check initial status
    status = orchestrator.get_agent_status(agent.id)
    assert status == AgentStatus.IDLE

    # Start agent and check status
    await orchestrator.start_agent(agent.id)
    await asyncio.sleep(0.2)

    status = orchestrator.get_agent_status(agent.id)
    assert status == AgentStatus.RUNNING

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_list_agents() -> None:
    """Test listing all registered agents."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent1 = MockAgent(name="Agent1", role="developer")
    agent2 = MockAgent(name="Agent2", role="tester")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    agents_list = orchestrator.list_agents()

    assert len(agents_list) == 2
    assert any(a["name"] == "Agent1" and a["role"] == "developer" for a in agents_list)
    assert any(a["name"] == "Agent2" and a["role"] == "tester" for a in agents_list)

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_orchestrator_broadcasts_agent_ready() -> None:
    """Test that orchestrator broadcasts AGENT_READY when starting an agent."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent1 = MockAgent(name="Agent1", role="developer")
    agent2 = MockAgent(name="Agent2", role="tester")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    await orchestrator.start_agent(agent1.id)
    await orchestrator.start_agent(agent2.id)
    await asyncio.sleep(0.3)

    # Agent2 should have received AGENT_READY from Agent1
    ready_messages = [
        msg for msg in agent2.processed_messages
        if msg.type == MessageType.AGENT_READY
    ]
    assert len(ready_messages) >= 1

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_get_message_bus_stats() -> None:
    """Test getting message bus statistics through the orchestrator."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent = MockAgent(name="TestAgent", role="developer")
    orchestrator.register_agent(agent)
    await orchestrator.start_agent(agent.id)
    await asyncio.sleep(0.2)

    # Send a task
    await orchestrator.send_task_to_agent(agent.id, {"task": "test"})
    await asyncio.sleep(0.2)

    # Get stats
    stats = orchestrator.get_message_bus_stats()
    assert stats["messages_sent"] >= 1
    assert stats["messages_delivered"] >= 1

    await orchestrator.stop()


@pytest.mark.asyncio
async def test_orchestrator_stops_all_agents() -> None:
    """Test that stopping the orchestrator stops all agents."""
    orchestrator = Orchestrator()
    await orchestrator.start()

    agent1 = MockAgent(name="Agent1", role="developer")
    agent2 = MockAgent(name="Agent2", role="tester")

    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    await orchestrator.start_agent(agent1.id)
    await orchestrator.start_agent(agent2.id)
    await asyncio.sleep(0.2)

    # Stop orchestrator
    await orchestrator.stop()
    await asyncio.sleep(0.1)

    # Verify all agents are stopped
    assert agent1.status == AgentStatus.STOPPED
    assert agent2.status == AgentStatus.STOPPED
    assert len(orchestrator._agent_tasks) == 0

