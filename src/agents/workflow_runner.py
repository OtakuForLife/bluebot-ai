"""LangGraph workflow execution with human-review interrupt handling."""

import asyncio
import logging
from typing import Any, Optional, cast

from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphInterrupt

from src.agents.human_review import HumanReviewCoordinator
from src.agents.state import AgentMessage
from src.agents.state_factory import build_polling_reset_state


class WorkflowRunner:
    """Runs compiled graphs and handles human-review interrupt/resume cycles."""

    def __init__(
        self,
        default_compiled: Any,
        review: HumanReviewCoordinator,
        logger: logging.Logger,
    ) -> None:
        self._default_compiled = default_compiled
        self._review = review
        self._logger = logger

    async def run(
        self,
        initial_state: AgentMessage,
        thread_id: str = "default",
        compiled: Any = None,
    ) -> AgentMessage:
        _compiled = compiled if compiled is not None else self._default_compiled
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        current_input: Any = initial_state

        while True:
            try:
                result = await _compiled.ainvoke(current_input, config)
            except GraphInterrupt as exc:
                interrupts = exc.args[0] if exc.args else []
                interrupt_value: dict = interrupts[0].value if interrupts else {}
                current_input = await self._review.wait_for_decision(
                    thread_id, interrupt_value
                )
                continue

            if isinstance(result, dict) and result.get("__interrupt__"):
                interrupts = result["__interrupt__"]
                interrupt_value = interrupts[0].value if interrupts else {}
                current_input = await self._review.wait_for_decision(
                    thread_id, interrupt_value
                )
                continue

            if isinstance(result, dict):
                result = {
                    k: v for k, v in result.items() if k != "__interrupt__"
                }
            return cast(AgentMessage, result)

    async def stream(
        self, initial_state: AgentMessage, thread_id: str = "default"
    ):
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        async for state in self._default_compiled.astream(initial_state, config):
            yield state

    def get_state(self, thread_id: str = "default") -> Optional[AgentMessage]:
        try:
            config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
            state = self._default_compiled.get_state(config)
            return cast(AgentMessage, state.values) if state else None
        except Exception as exc:
            self._logger.warning(
                f"Could not get workflow state for thread {thread_id}: {exc}"
            )
            return None

    async def run_polling_loop(
        self,
        run_once: Any,
        initial_state: AgentMessage,
        thread_id: str,
        interval: int,
        stop_event: asyncio.Event,
    ) -> None:
        """Run a workflow repeatedly until *stop_event* is set."""
        original_brief: str = initial_state.get("task_description", "")
        state: AgentMessage = initial_state
        iteration = 0

        while not stop_event.is_set():
            iteration += 1
            self._logger.info(
                f"Producer polling loop — iteration {iteration} "
                f"(next check in {interval}s after this one finishes)"
            )

            try:
                state = await run_once(state, thread_id)
            except asyncio.CancelledError:
                self._logger.info("Polling loop cancelled — exiting")
                break
            except Exception as exc:
                self._logger.error(
                    f"Polling iteration {iteration} raised an error: {exc}"
                )

            if stop_event.is_set():
                break

            state = build_polling_reset_state(state, original_brief=original_brief)

            self._logger.info(
                f"Producer polling loop — waiting {interval}s before next check"
            )

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=float(interval))
                break
            except asyncio.TimeoutError:
                self._logger.debug("Polling interval elapsed — continuing loop")

        self._logger.info("Producer polling loop finished")
