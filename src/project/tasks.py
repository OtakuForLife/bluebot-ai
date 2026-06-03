

from datetime import datetime
from enum import Enum
from typing import Optional, TypedDict

from src.agents.roles import AgentRole



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


class AgentTask(TypedDict):
    id: str
    type: AgentRole
    title: str
    description: str
    status: TaskStatus
    requires_review: bool
    created_at: datetime
    created_by: Optional[str]
    completed_at: Optional[datetime]