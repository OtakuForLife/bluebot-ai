"""Base agent class and core agent abstractions.

This module defines the foundational Agent class that all specialized agents
inherit from, along with the core interfaces for agent lifecycle and communication.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class AgentStatus(Enum):
    """Enumeration of possible agent states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    FILE_MODIFIED = "file_modified"
    TEST_RESULT = "test_result"
    AGENT_READY = "agent_ready"
    AGENT_SHUTDOWN = "agent_shutdown"
    PROJECT_CREATED = "project_created"
    VISION_CREATED = "vision_created"
    VISION_APPROVED = "vision_approved"
    VISION_REJECTED = "vision_rejected"


@dataclass
class Message:
    """A message exchanged between agents or between agent and orchestrator.

    Attributes:
        id: Unique identifier for this message.
        type: The type of message being sent.
        sender_id: UUID of the agent sending the message.
        recipient_id: UUID of the intended recipient (None for broadcast).
        payload: The actual message data (structure depends on message type).
        timestamp: When the message was created (set automatically).
    """

    id: UUID
    type: MessageType
    sender_id: UUID
    recipient_id: Optional[UUID]
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        if not isinstance(self.type, MessageType):
            raise ValueError(f"Invalid message type: {self.type}")


class Agent(ABC):
    """Abstract base class for all agents in the system.

    Each agent runs asynchronously and communicates via messages through
    a shared message bus. Agents have a specific role and can process
    tasks independently.

    Attributes:
        id: Unique identifier for this agent instance.
        name: Human-readable name for this agent.
        role: The agent's specialized role (e.g., "developer", "tester").
        status: Current operational status of the agent.
    """

    def __init__(self, name: str, role: str) -> None:
        """Initialize a new agent.

        Args:
            name: Human-readable name for this agent.
            role: The agent's specialized role.
        """
        self.id: UUID = uuid4()
        self.name: str = name
        self.role: str = role
        self.status: AgentStatus = AgentStatus.IDLE
        self.logger: logging.Logger = logging.getLogger(
            f"agent.{role}.{self.id.hex[:8]}"
        )
        self._running: bool = False
        self._task_queue: asyncio.Queue[Message] = asyncio.Queue()

    async def start(self) -> None:
        """Start the agent's main processing loop.

        This method should be called to begin agent operation. It will
        run until stop() is called or an unrecoverable error occurs.
        """
        if self._running:
            self.logger.warning(f"Agent {self.name} is already running")
            return

        self._running = True
        self.status = AgentStatus.RUNNING
        self.logger.info(f"Agent {self.name} ({self.role}) starting")

        try:
            await self._run()
        except Exception as e:
            self.logger.error(f"Agent {self.name} encountered error: {e}", exc_info=True)
            self.status = AgentStatus.ERROR
            raise
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the agent gracefully.

        Signals the agent to stop processing and clean up resources.
        """
        self.logger.info(f"Agent {self.name} stopping")
        self._running = False
        self.status = AgentStatus.STOPPED

    async def send_message(self, message: Message) -> None:
        """Send a message to another agent or the orchestrator.

        This method should be overridden by subclasses to integrate with
        the actual message bus.

        Args:
            message: The message to send.
        """
        # Default implementation logs the message
        # Subclasses will override to use the actual message bus
        self.logger.debug(f"Sending message: {message.type.value} to {message.recipient_id}")

    async def receive_message(self, message: Message) -> None:
        """Receive a message from another agent or the orchestrator.

        Args:
            message: The received message.
        """
        await self._task_queue.put(message)

    @abstractmethod
    async def process_message(self, message: Message) -> None:
        """Process a received message.

        This method must be implemented by concrete agent classes to define
        how they handle different message types.

        Args:
            message: The message to process.
        """
        pass

    async def _run(self) -> None:
        """Internal main loop for the agent.

        Continuously processes messages from the task queue while running.
        """
        while self._running:
            try:
                # Wait for a message with a timeout to allow checking _running flag
                message = await asyncio.wait_for(self._task_queue.get(), timeout=0.5)
                await self.process_message(message)
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
                self.status = AgentStatus.ERROR

