"""Helper for running async code from Qt UI thread."""

import asyncio
import logging
from concurrent.futures import Future
from threading import Thread
from typing import Any, Awaitable, Callable, Optional

from PySide6.QtCore import QObject, Signal


class AsyncHelper(QObject):
    """Helper class to run async code from Qt UI thread.
    
    This class manages an asyncio event loop in a separate thread
    and provides methods to run async functions from the Qt UI thread.
    
    Signals:
        task_completed: Emitted when an async task completes successfully.
        task_failed: Emitted when an async task fails with an error.
    """
    
    task_completed = Signal(object)  # result
    task_failed = Signal(str)  # error message
    
    def __init__(self) -> None:
        """Initialize the async helper."""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._running = False
    
    def start(self) -> None:
        """Start the asyncio event loop in a separate thread."""
        if self._running:
            self.logger.warning("AsyncHelper is already running")
            return
        
        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self.logger.info("AsyncHelper started")
    
    def stop(self) -> None:
        """Stop the asyncio event loop."""
        if not self._running:
            return
        
        self._running = False
        
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=2.0)
        
        self.logger.info("AsyncHelper stopped")
    
    def _run_loop(self) -> None:
        """Run the asyncio event loop (runs in separate thread)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            self._loop = None
    
    def run_coroutine(
        self,
        coro: Awaitable[Any],
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> Future:
        """Run a coroutine in the async event loop.
        
        Args:
            coro: The coroutine to run.
            on_success: Optional callback for successful completion.
            on_error: Optional callback for errors.
            
        Returns:
            Future that will contain the result.
        """
        if not self._loop:
            raise RuntimeError("AsyncHelper not started")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        
        def _handle_result(fut: Future) -> None:
            try:
                result = fut.result()
                if on_success:
                    on_success(result)
                self.task_completed.emit(result)
            except Exception as e:
                self.logger.error(f"Async task failed: {e}", exc_info=True)
                if on_error:
                    on_error(e)
                self.task_failed.emit(str(e))
        
        future.add_done_callback(_handle_result)
        
        return future
    
    def run_async(self, coro: Awaitable[Any]) -> None:
        """Run a coroutine without waiting for result.
        
        Args:
            coro: The coroutine to run.
        """
        if not self._loop:
            raise RuntimeError("AsyncHelper not started")
        
        asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def call_soon(self, callback: Callable[[], None]) -> None:
        """Schedule a callback to run in the async loop.
        
        Args:
            callback: The callback to run.
        """
        if not self._loop:
            raise RuntimeError("AsyncHelper not started")
        
        self._loop.call_soon_threadsafe(callback)

