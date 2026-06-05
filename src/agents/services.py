"""Event-driven services that connect the orchestrator to project events."""

import asyncio
import logging
from datetime import datetime

from src.agents.orchestrator import AgentOrchestrator
from src.agents.state import AgentMessage
from src.agents.state_factory import build_producer_reset_state, build_task_state
from src.events import Event, EventType
from src.project.manager import ProjectManager
from src.project.tasks import TaskStatus


class TaskDispatchService:
    """Reacts to TASK_CREATED events: claims the task and runs its specialist graph."""

    def __init__(
        self,
        project_manager: ProjectManager,
        orchestrator: AgentOrchestrator,
    ) -> None:
        self._pm = project_manager
        self._orch = orchestrator
        self._logger = logging.getLogger(f"{__name__}.TaskDispatchService")

    async def on_system_start(self) -> None:
        """Recover stale tasks and re-dispatch open marketplace work."""
        reset = self._pm.reconcile_orphaned_tasks()
        if reset:
            self._logger.info(
                f"Reset {len(reset)} orphaned in-progress task(s) to todo: {reset}"
            )

        open_tasks = [
            t for t in self._pm.get_tasks()
            if t.get("state") == TaskStatus.OPEN.value
        ]
        for task in open_tasks:
            task_id = task.get("id", "?")
            self._logger.info(f"Re-dispatching open task {task_id}")
            await self.on_task_created(Event(
                type=EventType.TASK_CREATED,
                payload=dict(task),
                timestamp=datetime.now().isoformat(),
            ))

    async def on_task_created(self, event: Event) -> None:
        payload = event["payload"]
        task_id = payload.get("id")
        task_type = str(payload.get("task_type", "")).lower()

        if not task_id:
            return

        entry = self._orch.get_task_graph(task_type)
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

        base = self._orch.get_base_state()
        if base is None:
            self._logger.error("No base state set — was start_event_driven() called?")
            return

        task_state = build_task_state(
            base,
            task_id=task_id,
            task_type=task_type,
            task_description=payload.get("description", ""),
            acceptance_criteria=payload.get("acceptance_criteria", []),
            agent_name=agent_name,
            capability=payload.get("capability", ""),
            recommended_artifact=payload.get("recommended_artifact", ""),
            rubric=payload.get("rubric", ""),
        )

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

        human_approved = result.get("human_review_approved")
        creative_ok = result.get("creative_review_approved")

        if creative_ok is False:
            await self.reopen_for_rework(
                task_id,
                result.get("creative_review_comment", ""),
                rejected_by="Creative Director",
            )
            return

        if human_approved is None:
            self._logger.warning(
                f"Task {task_id} workflow ended without a human review verdict — "
                "leaving in review"
            )
            self._pm.update_task(task_id, {"state": TaskStatus.REVIEW.value})
            return

        if human_approved:
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
            self._orch.event_handler.emit_event(Event(
                type=EventType.TASK_UPDATED,
                payload={
                    "task_id": task_id,
                    "new_state": TaskStatus.COMPLETED.value,
                },
                timestamp=datetime.now().isoformat(),
            ))
        else:
            await self.reopen_for_rework(
                task_id,
                result.get("human_review_comment", ""),
                rejected_by="Human review",
            )

    async def reopen_for_rework(
        self,
        task_id: str,
        rework_comment: str = "",
        *,
        rejected_by: str = "review",
    ) -> None:
        """Return a task to the marketplace and re-run its specialist graph."""
        task = self._pm.get_task(task_id)
        if not task:
            self._logger.warning(f"Cannot reopen unknown task {task_id}")
            return

        updates: dict = {
            "state": TaskStatus.OPEN.value,
            "agent": "",
        }
        if rework_comment.strip():
            section = (
                f"\n\n--- REWORK ({rejected_by}) ---\n{rework_comment.strip()}"
            )
            updates["description"] = task.get("description", "") + section

        self._pm.update_task(task_id, updates)
        self._orch.event_handler.emit_event(Event(
            type=EventType.TASK_UPDATED,
            payload={
                "task_id": task_id,
                "new_state": TaskStatus.OPEN.value,
                "comment": rework_comment,
                "rejected_by": rejected_by,
            },
            timestamp=datetime.now().isoformat(),
        ))

        refreshed = self._pm.get_task(task_id)
        if refreshed is None:
            return

        self._logger.info(
            f"Re-dispatching task {task_id} after {rejected_by} rejection"
        )
        await self.on_task_created(Event(
            type=EventType.TASK_CREATED,
            payload=dict(refreshed),
            timestamp=datetime.now().isoformat(),
        ))

    async def complete_task_offline(
        self, task_id: str, comment: str = ""
    ) -> None:
        """Mark a task done when no workflow is active (e.g. stale review card)."""
        task = self._pm.get_task(task_id)
        if not task:
            self._logger.warning(f"Cannot complete unknown task {task_id}")
            return

        self._pm.update_task(task_id, {"state": TaskStatus.COMPLETED.value})
        self._orch.event_handler.emit_event(Event(
            type=EventType.TASK_COMPLETED,
            payload={
                "task_id": task_id,
                "approved": True,
                "comment": comment,
            },
            timestamp=datetime.now().isoformat(),
        ))
        self._orch.event_handler.emit_event(Event(
            type=EventType.TASK_UPDATED,
            payload={
                "task_id": task_id,
                "new_state": TaskStatus.COMPLETED.value,
            },
            timestamp=datetime.now().isoformat(),
        ))


class ProducerService:
    """Reacts to TASK_COMPLETED events by re-running the Producer graph."""

    def __init__(self, orchestrator: AgentOrchestrator) -> None:
        self._orch = orchestrator
        self._logger = logging.getLogger(f"{__name__}.ProducerService")

    async def on_task_completed(self, event: Event) -> None:
        base = self._orch.get_base_state()
        if base is None:
            return

        task_id = event["payload"].get("task_id", "unknown")
        self._logger.info(f"Task {task_id} completed — re-running Producer")

        try:
            await self._orch.run_producer(build_producer_reset_state(base))
        except asyncio.CancelledError:
            self._logger.info("Producer run cancelled (system stopping)")
