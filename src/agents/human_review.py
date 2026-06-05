"""Human review LangGraph node and async/UI coordination."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from langgraph.types import Command, interrupt

from src.agents.state import AgentMessage
from src.events import Event, EventHandler, EventType


def human_review_node(state: AgentMessage) -> AgentMessage:
    """Pause the workflow for user approval via LangGraph interrupt."""
    review_response: dict = interrupt({
        "task_description": state.get("task_description", ""),
        "acceptance_criteria": state.get("acceptance_criteria", []),
        "recommended_artifact": state.get("recommended_artifact", ""),
        "rubric": state.get("rubric", ""),
        "creative_review_approved": state.get("creative_review_approved"),
        "creative_review_comment": state.get("creative_review_comment", ""),
        "last_agent": state.get("last_agent"),
        "created_files": state.get("created_files", []),
        "modified_files": state.get("modified_files", []),
        "tool_results": state.get("tool_results", []),
        "current_task_id": state.get("current_task_id"),
    })

    return {
        **state,
        "human_review_approved": review_response.get("approved", False),
        "human_review_comment": review_response.get("comment", ""),
        "last_agent": "human_review",
    }


class HumanReviewCoordinator:
    """Coordinates human-review interrupts between asyncio and the Qt UI."""

    def __init__(self, event_handler: EventHandler, logger: logging.Logger) -> None:
        self._event_handler = event_handler
        self._logger = logger
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._review_events: dict[str, asyncio.Event] = {}
        self._pending_reviews: dict[str, dict] = {}

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def wait_for_decision(
        self, thread_id: str, interrupt_value: dict
    ) -> Command:
        """Emit HUMAN_INPUT_REQUESTED and block until the UI submits a decision."""
        self._logger.info(f"Workflow paused for human review (thread={thread_id})")
        self._event_handler.emit_event(Event(
            type=EventType.HUMAN_INPUT_REQUESTED,
            payload={"thread_id": thread_id, **interrupt_value},
            timestamp=datetime.now().isoformat(),
        ))

        review_event = asyncio.Event()
        self._review_events[thread_id] = review_event
        await review_event.wait()
        self._review_events.pop(thread_id, None)

        return Command(resume=self._pending_reviews.pop(thread_id, {}))

    def submit_decision(self, thread_id: str, approved: bool, comment: str) -> None:
        """Submit a review decision from the UI thread."""
        self._pending_reviews[thread_id] = {"approved": approved, "comment": comment}

        if self._loop and thread_id in self._review_events:
            self._loop.call_soon_threadsafe(self._review_events[thread_id].set)

        self._event_handler.emit_event(Event(
            type=EventType.HUMAN_INPUT_RECEIVED,
            payload={"thread_id": thread_id, "approved": approved, "comment": comment},
            timestamp=datetime.now().isoformat(),
        ))
