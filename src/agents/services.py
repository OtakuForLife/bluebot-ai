"""Event-driven services that connect the orchestrator to project events."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from src.agents.orchestrator import AgentOrchestrator
from src.agents.state import AgentMessage
from src.events import Event, EventType
from src.project.manager import ProjectManager
from src.project.tasks import TaskStatus


class TaskDispatchService:
    """Reacts to TASK_CREATED events: claims the task and runs its specialist graph.

    Subscribe this service's ``on_task_created`` coroutine via::

        event_handler.subscribe_async(EventType.TASK_CREATED, service.on_task_created)

    The orchestrator must have been constructed with specialist agents that have
    capabilities, so that ``_task_graphs`` is populated before events arrive.
    """

    def __init__(
        self,
        project_manager: ProjectManager,
        orchestrator: AgentOrchestrator,
    ) -> None:
        self._pm = project_manager
        self._orch = orchestrator
        self._logger = logging.getLogger(f"{__name__}.TaskDispatchService")

    async def on_task_created(self, event: Event) -> None:
        """Called for every TASK_CREATED event — claims and runs the task graph."""
        payload = event["payload"]
        task_id: Optional[str] = payload.get("id")
        task_type: str = str(payload.get("task_type", "")).lower()

        if not task_id:
            return

        entry = self._orch._task_graphs.get(task_type)
        if entry is None:
            self._logger.warning(
                f"No task graph for task_type='{task_type}' — skipping {task_id}"
            )
            return

        agent_name, compiled = entry

        if not self._pm.claim_task(task_id, agent_name):
            self._logger.warning(f"Could not claim task {task_id} (already taken?)")
            return

        self._logger.info(
            f"Dispatching task {task_id} (type='{task_type}') → {agent_name}"
        )

        base = self._orch._base_state
        if base is None:
            self._logger.error("No base state set — was start_event_driven() called?")
            return

        task_state: AgentMessage = {
            **base,
            "task_id": task_id,
            "task_type": task_type,
            "task_description": payload.get("description", ""),
            "acceptance_criteria": payload.get("acceptance_criteria", []),
            "current_task_id": task_id,
            "current_task_agent": agent_name,
            "no_more_tasks": False,
            "messages": [],
            "tool_results": [],
            "created_files": [],
            "modified_files": [],
            "deleted_files": [],
            "errors": [],
            "outcome": None,
            "human_review_approved": None,
            "human_review_comment": None,
            "last_agent": None,
        }

        try:
            result = await self._orch.run_workflow(
                task_state, thread_id=task_id, compiled=compiled
            )
        except asyncio.CancelledError:
            self._logger.info(f"Task graph for {task_id} was cancelled")
            return
        except Exception as exc:
            self._logger.error(f"Task graph for {task_id} raised: {exc}")
            self._orch.event_handler.emit_event(Event(
                type=EventType.TASK_FAILED,
                payload={"task_id": task_id, "error": str(exc)},
                timestamp=datetime.now().isoformat(),
            ))
            return

        approved = result.get("human_review_approved", False)
        if approved:
            self._pm.update_task(task_id, {"state": TaskStatus.COMPLETED.value})
            self._orch.event_handler.emit_event(Event(
                type=EventType.TASK_COMPLETED,
                payload={
                    "task_id": task_id,
                    "approved": True,
                    "comment": result.get("human_review_comment", ""),
                },
                timestamp=datetime.now().isoformat(),
            ))
        else:
            self._pm.update_task(task_id, {"state": TaskStatus.OPEN.value})
            self._orch.event_handler.emit_event(Event(
                type=EventType.TASK_UPDATED,
                payload={
                    "task_id": task_id,
                    "new_state": TaskStatus.OPEN.value,
                    "comment": result.get("human_review_comment", ""),
                },
                timestamp=datetime.now().isoformat(),
            ))


class ProducerService:
    """Reacts to TASK_COMPLETED events by re-running the Producer graph.

    After each task finishes (approved or rejected-and-reset), the Producer
    analyses the project again and places any new tasks it finds.  This keeps
    the marketplace populated without a polling timer.

    Subscribe via::

        event_handler.subscribe_async(EventType.TASK_COMPLETED, service.on_task_completed)
    """

    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self._orch = orchestrator
        self._logger = logging.getLogger(f"{__name__}.ProducerService")

    async def on_task_completed(self, event: Event) -> None:
        """Re-run the Producer so it can create new tasks or decide the project is done."""
        if self._orch._base_state is None:
            return

        task_id = event["payload"].get("task_id", "unknown")
        self._logger.info(f"Task {task_id} completed — re-running Producer")

        producer_state: AgentMessage = {
            **self._orch._base_state,
            "task_id": str(uuid.uuid4()),
            "messages": [],
            "tool_results": [],
            "created_files": [],
            "modified_files": [],
            "deleted_files": [],
            "errors": [],
            "outcome": None,
            "no_more_tasks": False,
            "human_review_approved": None,
            "human_review_comment": None,
            "current_task_id": None,
            "current_task_agent": None,
            "last_agent": None,
            "direction": "",
        }
        try:
            await self._orch._run_producer(producer_state)
        except asyncio.CancelledError:
            self._logger.info("Producer run cancelled (system stopping)")
