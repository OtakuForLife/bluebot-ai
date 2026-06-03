from datetime import datetime
from typing import Optional

from src.events import Event, EventHandler, EventType
from src.project.tasks import AgentTask, TaskStatus

_AUTO_PULL = "auto_pull"
_MANUAL_ASSIGNMENT = "manual_assignment"


class ProjectManager:
    """In-memory task store and task marketplace, kept current by events.

    tasks.json on disk is only a persistence file: written by the UI
    (KanbanBoard) and read back at startup. Agents must never touch it
    directly — they query this class instead.

    Task Pull
    ---------
    In AUTO_PULL mode, agents call get_next_open_task() to find work that
    matches their capabilities, then claim_task() to atomically take
    ownership. The task_dispatcher graph node handles this on their behalf.
    """

    def __init__(self, event_handler: EventHandler) -> None:
        self.event_handler = event_handler
        self._tasks: dict[str, dict] = {}
        self._allocation_mode: str = _AUTO_PULL

        # Mirror every task event into _tasks so agents always read
        # from memory, not from the filesystem.
        event_handler.subscribe(EventType.TASK_CREATED, self._on_task_created)
        event_handler.subscribe(EventType.TASK_UPDATED, self._on_task_updated)
        event_handler.subscribe(EventType.TASK_ASSIGNED, self._on_task_assigned)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_task_created(self, event: Event) -> None:
        payload = event["payload"]
        task_id = payload.get("id")
        if task_id:
            task_data = dict(payload)
            # Ensure every stored task has a 'state' key so marketplace
            # queries work regardless of which code path created the task.
            if "state" not in task_data:
                task_data["state"] = TaskStatus.OPEN.value
            self._tasks[task_id] = task_data

    def _on_task_updated(self, event: Event) -> None:
        payload = event["payload"]
        task_id = payload.get("task_id")
        new_state = payload.get("new_state")
        if task_id and new_state and task_id in self._tasks:
            self._tasks[task_id]["state"] = new_state

    def _on_task_assigned(self, event: Event) -> None:
        payload = event["payload"]
        task_id = payload.get("task_id")
        if task_id and task_id in self._tasks:
            if new_state := payload.get("new_state"):
                self._tasks[task_id]["state"] = new_state
            if agent_name := payload.get("agent_name"):
                self._tasks[task_id]["agent"] = agent_name

    # ── Public API — task CRUD ────────────────────────────────────────────────

    def add_task(self, task: AgentTask) -> None:
        """Register a new task by emitting TASK_CREATED.

        _on_task_created (subscribed above) handles the actual dict write,
        so there is exactly one code path for task storage regardless of
        whether the task came from a command or from the assign_task tool.
        """
        self.event_handler.emit_event(Event(
            type=EventType.TASK_CREATED,
            payload=dict(task),
            timestamp=datetime.now().isoformat()
        ))

    def update_task(self, task_id: str, updates: dict) -> None:
        """Directly update fields on an existing in-memory task."""
        if task_id in self._tasks:
            self._tasks[task_id].update(updates)

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def get_tasks(self) -> list[dict]:
        return list(self._tasks.values())

    def load_tasks(self, tasks: list[dict]) -> None:
        """Pre-populate _tasks from a persisted task list (e.g. tasks.json).

        Must be called before any agent runs so the duplicate guard has
        visibility of tasks created in previous sessions.  Only tasks that
        carry an 'id' field are imported; already-known IDs are skipped so
        calling this more than once is safe.

        Args:
            tasks: List of task dicts as stored in tasks.json.
        """
        for task in tasks:
            task_id = task.get("id")
            if task_id and task_id not in self._tasks:
                task_data = dict(task)
                if "state" not in task_data:
                    task_data["state"] = TaskStatus.OPEN.value
                self._tasks[task_id] = task_data

    # ── Public API — task marketplace ─────────────────────────────────────────

    def get_next_open_task(self, capabilities: list[str]) -> Optional[dict]:
        """Return the first OPEN task whose task_type matches a given capability.

        Tasks are considered open when their state equals TaskStatus.OPEN
        ("todo"). Insertion order is preserved so the oldest task wins.

        Args:
            capabilities: List of task_type strings the caller can handle
                          (e.g. ["design", "art"]).

        Returns:
            A copy of the task dict, or None if no matching open task exists.
        """
        for task in self._tasks.values():
            if (task.get("state") == TaskStatus.OPEN.value
                    and task.get("task_type") in capabilities):
                return dict(task)
        return None

    def claim_task(self, task_id: str, agent_name: str) -> bool:
        """Atomically claim an open task for an agent.

        Emits TASK_ASSIGNED so the ProjectManager's own subscription moves
        the task to IN_PROGRESS and the kanban board moves the card to the
        "In Progress" column — reusing the existing event flow with no new
        event types required.

        Args:
            task_id:    ID of the task to claim.
            agent_name: Name of the agent claiming the task.

        Returns:
            True if the task was successfully claimed, False if it was not
            found or was already taken.
        """
        task = self._tasks.get(task_id)
        if not task or task.get("state") != TaskStatus.OPEN.value:
            return False

        self.event_handler.emit_event(Event(
            type=EventType.TASK_ASSIGNED,
            payload={
                "task_id": task_id,
                "agent_name": agent_name,
                "new_state": TaskStatus.IN_PROGRESS.value,
            },
            timestamp=datetime.now().isoformat(),
        ))
        return True

    # ── Public API — allocation mode ──────────────────────────────────────────

    @property
    def allocation_mode(self) -> str:
        """Current task allocation mode: "auto_pull" or "manual_assignment"."""
        return self._allocation_mode

    def set_allocation_mode(self, mode: str) -> None:
        """Switch between AUTO_PULL and MANUAL_ASSIGNMENT modes.

        Emits TASK_ALLOCATION_MODE_CHANGED so the UI and any interested
        components can react without polling.

        Args:
            mode: "auto_pull" or "manual_assignment".
        """
        if mode not in (_AUTO_PULL, _MANUAL_ASSIGNMENT):
            raise ValueError(
                f"Unknown allocation mode '{mode}'. "
                f"Use '{_AUTO_PULL}' or '{_MANUAL_ASSIGNMENT}'."
            )
        self._allocation_mode = mode
        self.event_handler.emit_event(Event(
            type=EventType.TASK_ALLOCATION_MODE_CHANGED,
            payload={"mode": mode},
            timestamp=datetime.now().isoformat(),
        ))
