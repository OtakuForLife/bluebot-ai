"""Message bus for inter-agent communication.

This module implements an asyncio-based message bus that routes messages
between agents and the orchestrator. It supports both direct messaging
(agent-to-agent) and broadcast messaging (one-to-many).
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional
from uuid import UUID

from src.agents.base import Message, MessageType


class MessageBus:
    """Asynchronous message bus for routing messages between agents.

    The message bus maintains subscriptions for agents and routes messages
    based on recipient IDs. It supports:
    - Direct messaging: Messages sent to a specific agent ID
    - Broadcast messaging: Messages with no recipient ID go to all subscribers
    - Type-based filtering: Agents can subscribe to specific message types

    Attributes:
        _subscribers: Mapping of agent IDs to their message handlers.
        _running: Flag indicating if the bus is actively processing messages.
        _message_queue: Internal queue for messages to be routed.
    """

    def __init__(self) -> None:
        """Initialize a new message bus."""
        self.logger = logging.getLogger("message_bus")
        self._subscribers: dict[UUID, Callable[[Message], Awaitable[None]]] = {}
        self._type_subscribers: dict[MessageType, set[UUID]] = {}
        self._running: bool = False
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_dropped": 0,
        }

    def subscribe(
        self,
        agent_id: UUID,
        handler: Callable[[Message], Awaitable[None]],
        message_types: Optional[list[MessageType]] = None,
    ) -> None:
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Unique identifier of the subscribing agent.
            handler: Async callable that will receive messages.
            message_types: Optional list of message types to filter.
                          If None, receives all messages.
        """
        self._subscribers[agent_id] = handler
        self.logger.info(f"Agent {agent_id} subscribed to message bus")

        if message_types:
            for msg_type in message_types:
                if msg_type not in self._type_subscribers:
                    self._type_subscribers[msg_type] = set()
                self._type_subscribers[msg_type].add(agent_id)
            self.logger.debug(
                f"Agent {agent_id} subscribed to types: {[t.value for t in message_types]}"
            )

    def unsubscribe(self, agent_id: UUID) -> None:
        """Unsubscribe an agent from the message bus.

        Args:
            agent_id: Unique identifier of the agent to unsubscribe.
        """
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
            self.logger.info(f"Agent {agent_id} unsubscribed from message bus")

        # Remove from type-specific subscriptions
        for subscribers in self._type_subscribers.values():
            subscribers.discard(agent_id)

    async def publish(self, message: Message) -> None:
        """Publish a message to the bus for routing.

        Args:
            message: The message to publish.
        """
        await self._message_queue.put(message)
        self._stats["messages_sent"] += 1
        self.logger.debug(
            f"Message {message.id} published: {message.type.value} "
            f"from {message.sender_id} to {message.recipient_id or 'broadcast'}"
        )

    async def start(self) -> None:
        """Start the message bus processing loop.

        This method runs continuously, routing messages from the queue
        to their intended recipients.
        """
        if self._running:
            self.logger.warning("Message bus is already running")
            return

        self._running = True
        self.logger.info("Message bus started")

        try:
            await self._process_messages()
        except Exception as e:
            self.logger.error(f"Message bus error: {e}", exc_info=True)
            raise
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the message bus gracefully."""
        self.logger.info("Message bus stopping")
        self._running = False

    async def _process_messages(self) -> None:
        """Internal loop that processes messages from the queue."""
        while self._running:
            try:
                # Wait for a message with timeout to allow checking _running flag
                message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=0.5
                )
                await self._route_message(message)
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)

    async def _route_message(self, message: Message) -> None:
        """Route a message to its intended recipient(s).

        Args:
            message: The message to route.
        """
        delivered = False

        if message.recipient_id:
            # Direct message to specific agent
            if message.recipient_id in self._subscribers:
                handler = self._subscribers[message.recipient_id]
                try:
                    await handler(message)
                    self._stats["messages_delivered"] += 1
                    delivered = True
                    self.logger.debug(
                        f"Message {message.id} delivered to {message.recipient_id}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error delivering message {message.id} to "
                        f"{message.recipient_id}: {e}",
                        exc_info=True,
                    )
            else:
                self.logger.warning(
                    f"No subscriber found for recipient {message.recipient_id}"
                )
                self._stats["messages_dropped"] += 1
        else:
            # Broadcast message
            recipients = self._get_broadcast_recipients(message)
            for agent_id in recipients:
                handler = self._subscribers[agent_id]
                try:
                    await handler(message)
                    self._stats["messages_delivered"] += 1
                    delivered = True
                except Exception as e:
                    self.logger.error(
                        f"Error broadcasting message {message.id} to {agent_id}: {e}",
                        exc_info=True,
                    )

            if delivered:
                self.logger.debug(
                    f"Message {message.id} broadcast to {len(recipients)} recipients"
                )
            else:
                self._stats["messages_dropped"] += 1

    def _get_broadcast_recipients(self, message: Message) -> set[UUID]:
        """Get the set of agent IDs that should receive a broadcast message.

        Args:
            message: The broadcast message.

        Returns:
            Set of agent IDs that should receive the message.
        """
        # If there are type-specific subscribers, use those
        if message.type in self._type_subscribers:
            return self._type_subscribers[message.type].copy()

        # Otherwise, broadcast to all subscribers except the sender
        return {
            agent_id
            for agent_id in self._subscribers.keys()
            if agent_id != message.sender_id
        }

    def get_stats(self) -> dict[str, int]:
        """Get message bus statistics.

        Returns:
            Dictionary containing message statistics.
        """
        return self._stats.copy()

