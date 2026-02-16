"""Base agent class and core agent abstractions.

This module defines the foundational Agent class that all specialized agents
inherit from, along with the core interfaces for agent lifecycle and communication.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.orchestrator.task_manager import TaskManager


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
    # Autonomous task management message types
    TASK_CREATED = "task_created"
    TASK_CLAIMED = "task_claimed"
    TASK_COMPLETED = "task_completed"
    TASK_STATE_CHANGED = "task_state_changed"
    TASK_QUERY = "task_query"
    TASK_QUERY_RESPONSE = "task_query_response"


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
        self.task_manager: Optional[TaskManager] = None  # Will be set by orchestrator
        self.autonomous_mode: bool = False  # Enable/disable autonomous behavior

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
        Also calls autonomous tick when in autonomous mode.
        """
        autonomous_tick_interval = 5.0  # seconds between autonomous ticks
        last_autonomous_tick = 0.0

        while self._running:
            try:
                # Wait for a message with a timeout to allow checking _running flag
                message = await asyncio.wait_for(self._task_queue.get(), timeout=0.5)
                await self.process_message(message)
            except asyncio.TimeoutError:
                # No message received, check if we should do autonomous tick
                if self.autonomous_mode:
                    import time
                    current_time = time.time()
                    if current_time - last_autonomous_tick >= autonomous_tick_interval:
                        try:
                            await self.on_autonomous_tick()
                            last_autonomous_tick = current_time
                        except Exception as e:
                            self.logger.error(f"Error in autonomous tick: {e}", exc_info=True)
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
                self.status = AgentStatus.ERROR

    # Task management methods for autonomous behavior

    async def discover_tasks(self, task_type: Optional[str] = None) -> list[dict]:
        """Discover available tasks that this agent can handle.

        Args:
            task_type: Optional filter by specific task type.

        Returns:
            List of available task data dictionaries.
        """
        if not self.task_manager:
            self.logger.warning("Task manager not available")
            return []

        return await self.task_manager.get_available_tasks(
            agent_role=self.name,
            task_type=task_type
        )

    async def claim_task(self, task_id: str) -> bool:
        """Claim a task for this agent to work on.

        Args:
            task_id: ID of the task to claim.

        Returns:
            True if task was successfully claimed, False otherwise.
        """
        if not self.task_manager:
            self.logger.warning("Task manager not available")
            return False

        success = await self.task_manager.claim_task(task_id, self.id)

        if success:
            self.logger.info(f"Successfully claimed task: {task_id}")

        return success

    async def complete_task(self, task_id: str, result: Optional[dict] = None) -> bool:
        """Mark a task as completed.

        Args:
            task_id: ID of the task to complete.
            result: Optional result data from task completion.

        Returns:
            True if task was successfully completed, False otherwise.
        """
        if not self.task_manager:
            self.logger.warning("Task manager not available")
            return False

        success = await self.task_manager.complete_task(task_id, self.id, result)

        if success:
            self.logger.info(f"Successfully completed task: {task_id}")

        return success

    async def create_task(
        self,
        title: str,
        description: str,
        agent: str,
        task_type: str,
        requires_review: bool = True,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Create a new task.

        Args:
            title: Task title.
            description: Task description.
            agent: Agent name to assign the task to.
            task_type: Type of task.
            requires_review: Whether task requires user review.
            metadata: Optional additional metadata.

        Returns:
            The created task data or None if creation failed.
        """
        if not self.task_manager:
            self.logger.warning("Task manager not available")
            return None

        task = await self.task_manager.create_task(
            title=title,
            description=description,
            agent=agent,
            task_type=task_type,
            requires_review=requires_review,
            created_by=self.id,
            metadata=metadata,
        )

        self.logger.info(f"Created task: {task['id']} - {title}")

        return task

    async def on_autonomous_tick(self) -> None:
        """Called periodically when in autonomous mode.

        Agents can override this to implement autonomous behavior like:
        - Discovering and claiming tasks
        - Creating new tasks based on analysis
        - Monitoring project state

        This is called from the agent's main loop when autonomous_mode is True.
        """
        pass  # Default implementation does nothing

