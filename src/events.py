import asyncio
import logging
from collections import defaultdict
from concurrent.futures import Future
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypedDict

_log = logging.getLogger(__name__)

class EventType(str, Enum):

    # Add new events here

    PROJECT_CREATED = "project_created"

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"

    PROJECT_FILE_CREATED = "file_created"
    PROJECT_FILE_UPDATED = "file_updated"
    PROJECT_FILE_DELETED = "file_deleted"

    HUMAN_INPUT_REQUESTED = "human_input_requested"
    HUMAN_INPUT_RECEIVED = "human_input_received"

    # Agent coordination events
    TASK_ASSIGNED = "task_assigned"
    TASK_FAILED = "task_failed"

    # Agent state and lifecycle events
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_CURRENT_TASK_CHANGED = "agent_current_task_changed"
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTION = "agent_action"

    # Task marketplace events
    TASK_ALLOCATION_MODE_CHANGED = "task_allocation_mode_changed"

    # System control events
    AGENTIC_SYSTEM_STARTED = "agentic_system_started"
    AGENTIC_SYSTEM_STOPPED = "agentic_system_stopped"

class Event(TypedDict):
    type: EventType
    payload: Any
    timestamp: str

EventHandlerCallback = Callable[[Event], None]
AsyncEventHandlerCallback = Callable[[Event], Coroutine[Any, Any, None]]


class EventHandler:
    """Synchronous event bus with optional async subscriber support.

    Sync subscribers (subscribe / subscribe_all) are called inline from
    emit_event — same behaviour as before, zero overhead.

    Async subscribers (subscribe_async) are scheduled on the asyncio event
    loop registered via set_event_loop().  They are dispatched using
    run_coroutine_threadsafe so that emit_event remains non-blocking and
    thread-safe even when called from the Qt main thread.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[EventHandlerCallback]] = defaultdict(list)
        self._async_subscribers: Dict[EventType, List[AsyncEventHandlerCallback]] = defaultdict(list)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Track live async-dispatch futures so they can be cancelled on shutdown
        self._pending_futures: set[Future] = set()

    # ── Event loop registration ───────────────────────────────────────────────

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the running asyncio event loop for async subscriber dispatch.

        Must be called from inside the event loop thread (e.g. at the start of
        WorkflowThread.run) so that run_coroutine_threadsafe has a live loop
        to schedule work on.
        """
        self._loop = loop

    # ── Subscription ─────────────────────────────────────────────────────────

    def subscribe(self, event_type: EventType, function: EventHandlerCallback) -> None:
        """Register a synchronous subscriber for an event type."""
        self._subscribers[event_type].append(function)

    def subscribe_async(
        self, event_type: EventType, function: AsyncEventHandlerCallback
    ) -> None:
        """Register an async coroutine subscriber for an event type.

        The coroutine is scheduled on the registered event loop each time the
        event fires.  Requires set_event_loop() to have been called first.
        """
        self._async_subscribers[event_type].append(function)

    def subscribe_all(self, function: EventHandlerCallback) -> None:
        """Register a synchronous subscriber for every event type."""
        for event_type in EventType:
            self.subscribe(event_type, function)

    # ── Emission ─────────────────────────────────────────────────────────────

    def emit_event(self, event: Event) -> None:
        """Emit an event to all registered subscribers.

        Sync subscribers are called immediately (inline).
        Async subscribers are scheduled on the event loop without blocking.
        Exceptions raised by async handlers are logged rather than silently dropped.
        """
        # Sync path — unchanged, always runs
        for handler in self._subscribers.get(event["type"], []):
            handler(event)

        # Async path — only runs when a live loop has been registered
        if self._loop and self._loop.is_running():
            for handler in self._async_subscribers.get(event["type"], []):
                future = asyncio.run_coroutine_threadsafe(handler(event), self._loop)
                self._pending_futures.add(future)

                # Log any exception the handler raises; remove future when done
                def _on_done(f: Future, name: str = handler.__qualname__) -> None:
                    self._pending_futures.discard(f)
                    if not f.cancelled() and f.exception() is not None:
                        _log.error(
                            "Async event handler '%s' raised an exception: %r",
                            name, f.exception(),
                        )

                future.add_done_callback(_on_done)

    def cancel_pending(self) -> None:
        """Cancel all in-flight async-subscriber futures.

        Call this from signal_stop() or shutdown logic to interrupt long-running
        handlers (e.g. an LLM inference inside TaskDispatchService.on_task_created).
        """
        for f in list(self._pending_futures):
            if not f.done():
                f.cancel()
        self._pending_futures.clear()
