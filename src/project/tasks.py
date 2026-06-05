from enum import Enum
from typing import Optional, TypedDict


class TaskStatus(str, Enum):
    """Lifecycle states for tasks in the marketplace.

    String values are chosen to match the kanban board's column identifiers
    so tasks flow through the UI without extra mapping logic.

    States
    ------
    OPEN        — available in the marketplace; any capable agent may claim it.
    IN_PROGRESS — claimed by an agent and actively being worked on.
    REVIEW      — work complete; awaiting human or automated review.
    COMPLETED   — accepted; no further action needed.
    CANCELLED   — rejected or abandoned.
    """
    OPEN = "todo"           # maps to "To Do" kanban column
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "done"      # maps to "Done" kanban column
    CANCELLED = "cancelled"


class AgentTask(TypedDict, total=False):
    """In-memory and persisted task shape used by ProjectManager and the UI."""
    id: str
    title: str
    description: str
    task_type: str
    state: str
    agent: str
    requires_review: bool
    acceptance_criteria: list[str]
    capability: str
    recommended_artifact: str
    rubric: str
    created_at: str
    created_by: Optional[str]
    completed_at: Optional[str]