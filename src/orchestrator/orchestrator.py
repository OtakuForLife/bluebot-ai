"""Orchestrator service for managing agents and coordinating workflows.

The orchestrator is responsible for:
- Creating and managing agent instances
- Starting and stopping agents
- Coordinating the message bus
- Assigning tasks to agents
- Managing the overall workflow
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from src.agents.base import Agent, AgentStatus, Message, MessageType
from src.orchestrator.message_bus import MessageBus
from src.orchestrator.task_manager import TaskManager


class Orchestrator:
    """Central orchestrator for managing the multi-agent system.

    The orchestrator manages the lifecycle of all agents, coordinates
    communication through the message bus, and handles task assignment
    and workflow coordination.

    Attributes:
        message_bus: The message bus for inter-agent communication.
        _agents: Dictionary mapping agent IDs to agent instances.
        _running: Flag indicating if the orchestrator is running.
    """

    def __init__(self) -> None:
        """Initialize a new orchestrator."""
        self.logger = logging.getLogger("orchestrator")
        self.message_bus = MessageBus()
        self.task_manager = TaskManager(message_bus=self.message_bus)
        self._agents: dict[UUID, Agent] = {}
        self._agent_tasks: dict[UUID, asyncio.Task] = {}
        self._running: bool = False
        self._bus_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the orchestrator and message bus.

        This initializes the message bus and prepares the orchestrator
        to manage agents.
        """
        if self._running:
            self.logger.warning("Orchestrator is already running")
            return

        self._running = True
        self.logger.info("Orchestrator starting")

        # Start the message bus
        self._bus_task = asyncio.create_task(self.message_bus.start())
        await asyncio.sleep(0.1)  # Give the bus time to start

        self.logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Stop the orchestrator and all managed agents.

        This gracefully shuts down all agents and the message bus.
        """
        self.logger.info("Orchestrator stopping")
        self._running = False

        # Stop all agents
        for agent_id in list(self._agents.keys()):
            await self.stop_agent(agent_id)

        # Stop the message bus
        await self.message_bus.stop()
        if self._bus_task:
            self._bus_task.cancel()
            try:
                await self._bus_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Orchestrator stopped")

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: The agent instance to register.
        """
        if agent.id in self._agents:
            self.logger.warning(f"Agent {agent.id} is already registered")
            return

        self._agents[agent.id] = agent

        # Set the task manager on the agent
        agent.task_manager = self.task_manager

        # Subscribe the agent to the message bus
        self.message_bus.subscribe(agent.id, agent.receive_message)

        self.logger.info(f"Registered agent: {agent.name} ({agent.role}) - ID: {agent.id}")

    def unregister_agent(self, agent_id: UUID) -> None:
        """Unregister an agent from the orchestrator.

        Args:
            agent_id: The ID of the agent to unregister.
        """
        if agent_id not in self._agents:
            self.logger.warning(f"Agent {agent_id} is not registered")
            return

        agent = self._agents[agent_id]

        # Unsubscribe from message bus
        self.message_bus.unsubscribe(agent_id)

        # Remove from agents dict
        del self._agents[agent_id]

        self.logger.info(f"Unregistered agent: {agent.name} ({agent.role})")

    async def start_agent(self, agent_id: UUID) -> None:
        """Start a registered agent.

        Args:
            agent_id: The ID of the agent to start.

        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} is not registered")

        if agent_id in self._agent_tasks:
            self.logger.warning(f"Agent {agent_id} is already running")
            return

        agent = self._agents[agent_id]
        self.logger.info(f"Starting agent: {agent.name} ({agent.role})")

        # Start the agent in a task
        task = asyncio.create_task(agent.start())
        self._agent_tasks[agent_id] = task

        # Send agent ready message
        ready_message = Message(
            id=agent.id,
            type=MessageType.AGENT_READY,
            sender_id=agent.id,
            recipient_id=None,  # Broadcast
            payload={"name": agent.name, "role": agent.role},
        )
        await self.message_bus.publish(ready_message)

    async def stop_agent(self, agent_id: UUID) -> None:
        """Stop a running agent.

        Args:
            agent_id: The ID of the agent to stop.
        """
        if agent_id not in self._agents:
            self.logger.warning(f"Agent {agent_id} is not registered")
            return

        agent = self._agents[agent_id]
        self.logger.info(f"Stopping agent: {agent.name} ({agent.role})")

        # Stop the agent
        await agent.stop()

        # Cancel and clean up the task
        if agent_id in self._agent_tasks:
            task = self._agent_tasks[agent_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._agent_tasks[agent_id]

        # Send agent shutdown message
        shutdown_message = Message(
            id=agent.id,
            type=MessageType.AGENT_SHUTDOWN,
            sender_id=agent.id,
            recipient_id=None,  # Broadcast
            payload={"name": agent.name, "role": agent.role},
        )
        await self.message_bus.publish(shutdown_message)

    async def send_task_to_agent(
        self, agent_id: UUID, task_data: dict
    ) -> None:
        """Send a task request to a specific agent.

        Args:
            agent_id: The ID of the agent to receive the task.
            task_data: Dictionary containing task information.

        Raises:
            ValueError: If the agent is not registered.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} is not registered")

        # Create a task request message
        task_message = Message(
            id=UUID(int=0),  # Orchestrator uses a special ID
            type=MessageType.TASK_REQUEST,
            sender_id=UUID(int=0),
            recipient_id=agent_id,
            payload=task_data,
        )

        await self.message_bus.publish(task_message)
        self.logger.info(f"Sent task to agent {agent_id}: {task_data}")

    def get_agent_status(self, agent_id: UUID) -> Optional[AgentStatus]:
        """Get the current status of an agent.

        Args:
            agent_id: The ID of the agent.

        Returns:
            The agent's status, or None if not registered.
        """
        if agent_id not in self._agents:
            return None
        return self._agents[agent_id].status

    def list_agents(self) -> list[dict]:
        """List all registered agents and their status.

        Returns:
            List of dictionaries containing agent information.
        """
        return [
            {
                "id": str(agent.id),
                "name": agent.name,
                "role": agent.role,
                "status": agent.status.value,
            }
            for agent in self._agents.values()
        ]

    def get_message_bus_stats(self) -> dict[str, int]:
        """Get statistics from the message bus.

        Returns:
            Dictionary containing message bus statistics.
        """
        return self.message_bus.get_stats()

