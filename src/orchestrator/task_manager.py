"""Task Manager for autonomous agent task management.

This module provides centralized task storage, lifecycle management, and querying
capabilities for autonomous agents to create, discover, claim, and complete tasks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from src.agents.base import Message, MessageType


class TaskState:
    """Task state constants."""
    
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class TaskManager:
    """Manages tasks for autonomous agent coordination.
    
    The TaskManager provides:
    - Centralized task storage
    - Task lifecycle management (create, claim, update, complete)
    - Task querying and filtering
    - Integration with message bus for real-time updates
    
    Attributes:
        tasks: Dictionary mapping task IDs to task data.
        message_bus: Message bus for publishing task events.
    """
    
    def __init__(self, message_bus=None):
        """Initialize the Task Manager.
        
        Args:
            message_bus: Optional message bus for publishing task events.
        """
        self.tasks: dict[str, dict] = {}
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
    
    async def create_task(
        self,
        title: str,
        description: str,
        agent: str,
        task_type: str,
        requires_review: bool = True,
        created_by: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new task.
        
        Args:
            title: Task title.
            description: Task description.
            agent: Agent name to assign the task to.
            task_type: Type of task (e.g., "create_script", "define_mechanics").
            requires_review: Whether task requires user review before completion.
            created_by: UUID of the agent/user who created the task.
            metadata: Optional additional metadata.
        
        Returns:
            The created task data.
        """
        async with self._lock:
            task_id = str(uuid4())
            
            task_data = {
                "id": task_id,
                "title": title,
                "description": description,
                "agent": agent,
                "task_type": task_type,
                "requires_review": requires_review,
                "state": TaskState.TODO,
                "created_at": datetime.now().isoformat(),
                "created_by": str(created_by) if created_by else None,
                "claimed_by": None,
                "claimed_at": None,
                "completed_at": None,
                "metadata": metadata or {},
            }
            
            self.tasks[task_id] = task_data
            self.logger.info(f"Created task: {task_id} - {title} (assigned to {agent})")
            
            # Publish task created event
            if self.message_bus:
                await self._publish_task_event(MessageType.TASK_CREATED, task_data)
            
            return task_data
    
    async def claim_task(self, task_id: str, agent_id: UUID) -> bool:
        """Claim a task for an agent.
        
        Args:
            task_id: ID of the task to claim.
            agent_id: UUID of the agent claiming the task.
        
        Returns:
            True if task was successfully claimed, False otherwise.
        """
        async with self._lock:
            if task_id not in self.tasks:
                self.logger.warning(f"Task {task_id} not found")
                return False
            
            task = self.tasks[task_id]
            
            # Only allow claiming tasks in TODO state
            if task["state"] != TaskState.TODO:
                self.logger.warning(f"Task {task_id} is not in TODO state (current: {task['state']})")
                return False
            
            # Update task state
            task["state"] = TaskState.IN_PROGRESS
            task["claimed_by"] = str(agent_id)
            task["claimed_at"] = datetime.now().isoformat()
            
            self.logger.info(f"Task {task_id} claimed by agent {agent_id}")
            
            # Publish task claimed event
            if self.message_bus:
                await self._publish_task_event(MessageType.TASK_CLAIMED, task)
            
            return True

    async def update_task_state(self, task_id: str, new_state: str, agent_id: Optional[UUID] = None) -> bool:
        """Update a task's state.

        Args:
            task_id: ID of the task to update.
            new_state: New state for the task.
            agent_id: Optional UUID of the agent updating the task.

        Returns:
            True if task was successfully updated, False otherwise.
        """
        async with self._lock:
            if task_id not in self.tasks:
                self.logger.warning(f"Task {task_id} not found")
                return False

            task = self.tasks[task_id]
            old_state = task["state"]
            task["state"] = new_state

            # Mark completion time if moving to DONE
            if new_state == TaskState.DONE and old_state != TaskState.DONE:
                task["completed_at"] = datetime.now().isoformat()

            self.logger.info(f"Task {task_id} state changed: {old_state} -> {new_state}")

            # Publish task state changed event
            if self.message_bus:
                await self._publish_task_event(MessageType.TASK_STATE_CHANGED, task)

            return True

    async def complete_task(self, task_id: str, agent_id: UUID, result: Optional[dict] = None) -> bool:
        """Mark a task as completed.

        Args:
            task_id: ID of the task to complete.
            agent_id: UUID of the agent completing the task.
            result: Optional result data from task completion.

        Returns:
            True if task was successfully completed, False otherwise.
        """
        async with self._lock:
            if task_id not in self.tasks:
                self.logger.warning(f"Task {task_id} not found")
                return False

            task = self.tasks[task_id]

            # If task requires review, move to REVIEW state, otherwise DONE
            if task["requires_review"]:
                new_state = TaskState.REVIEW
            else:
                new_state = TaskState.DONE
                task["completed_at"] = datetime.now().isoformat()

            task["state"] = new_state

            if result:
                task["metadata"]["result"] = result

            self.logger.info(f"Task {task_id} completed by agent {agent_id} (state: {new_state})")

            # Publish task completed event
            if self.message_bus:
                await self._publish_task_event(MessageType.TASK_COMPLETED, task)

            return True

    async def get_available_tasks(self, agent_role: Optional[str] = None, task_type: Optional[str] = None) -> list[dict]:
        """Get available tasks that can be claimed.

        Args:
            agent_role: Optional filter by agent role.
            task_type: Optional filter by task type.

        Returns:
            List of available task data dictionaries.
        """
        async with self._lock:
            available = []

            for task in self.tasks.values():
                # Only return tasks in TODO state
                if task["state"] != TaskState.TODO:
                    continue

                # Filter by agent role if specified
                if agent_role and task["agent"] != agent_role:
                    continue

                # Filter by task type if specified
                if task_type and task["task_type"] != task_type:
                    continue

                available.append(task.copy())

            return available

    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get a specific task by ID.

        Args:
            task_id: ID of the task to retrieve.

        Returns:
            Task data dictionary or None if not found.
        """
        async with self._lock:
            return self.tasks.get(task_id, None)

    async def get_all_tasks(self) -> list[dict]:
        """Get all tasks.

        Returns:
            List of all task data dictionaries.
        """
        async with self._lock:
            return [task.copy() for task in self.tasks.values()]

    async def get_tasks_by_state(self, state: str) -> list[dict]:
        """Get all tasks in a specific state.

        Args:
            state: Task state to filter by.

        Returns:
            List of task data dictionaries in the specified state.
        """
        async with self._lock:
            return [task.copy() for task in self.tasks.values() if task["state"] == state]

    async def get_agent_tasks(self, agent_id: UUID) -> list[dict]:
        """Get all tasks claimed by a specific agent.

        Args:
            agent_id: UUID of the agent.

        Returns:
            List of task data dictionaries claimed by the agent.
        """
        async with self._lock:
            agent_id_str = str(agent_id)
            return [task.copy() for task in self.tasks.values() if task["claimed_by"] == agent_id_str]

    async def _publish_task_event(self, message_type: MessageType, task_data: dict) -> None:
        """Publish a task event to the message bus.

        Args:
            message_type: Type of message to publish.
            task_data: Task data to include in the message.
        """
        if not self.message_bus:
            return

        message = Message(
            id=uuid4(),
            type=message_type,
            sender_id=UUID(int=0),  # Task manager uses special ID
            recipient_id=None,  # Broadcast to all agents
            payload={"task": task_data},
        )

        await self.message_bus.publish(message)

