"""Shared workflow state for the LangGraph agent pipeline.

AgentMessage is the single TypedDict that flows through every node in the graph.
Keeping it in its own file prevents circular imports between base.py and graph.py.
"""

from typing import Optional, TypedDict


class AgentMessage(TypedDict):
    """State passed between every node in the LangGraph workflow.

    Sections are organised by who writes them and who reads them.
    """

    # ── Task context ─────────────────────────────────────────────────────────
    # Written by Discovery (via create_task), read by Specialist agents.
    task_id: str
    task_type: str                  # "design" | "gameplay" | "systems" | "art"
    task_description: str           # Full brief the specialist must act on
    acceptance_criteria: list[str]  # Objective checks for human review
    capability: str                 # Studio capability id (e.g. game_vision)
    recommended_artifact: str       # Target file path (e.g. design/VISION.md)
    rubric: str                     # Knowledge rubric id used for quality criteria

    # ── Filesystem contract ──────────────────────────────────────────────────
    # Set at startup and never mutated during the workflow.
    workspace_root: str             # Absolute path to the project root
    allowed_paths: list[str]        # Sandbox — agents may only touch these paths

    # ── Execution trace ──────────────────────────────────────────────────────
    # Updated after every agent turn.
    last_agent: str | None          # Name of the last agent that ran
    messages: list                  # LLM conversation (reset each turn)
    tool_results: list[str]         # Human-readable log of tool calls + results

    # ── File outputs ─────────────────────────────────────────────────────────
    # Appended by Specialists when they call create_file, etc.
    modified_files: list[str]
    created_files: list[str]
    deleted_files: list[str]

    # ── Terminal flags ───────────────────────────────────────────────────────
    outcome: str | None             # "done" | "blocked" | "needs_review"
    errors: list[str]
    no_more_tasks: bool             # True → Producer signals nothing left to do

    # ── Human review ─────────────────────────────────────────────────────────
    # Written by human_review_node, read by the Producer on the next iteration.
    human_review_approved: Optional[bool]   # None until the reviewer acts
    human_review_comment: Optional[str]

    # ── Creative Director review ───────────────────────────────────────────────
    # Written by Project Director (submit_creative_review) before human review.
    creative_review_approved: Optional[bool]
    creative_review_comment: Optional[str]

    # ── Kanban tracking ──────────────────────────────────────────────────────
    # Written by task_dispatcher, consumed by Agent.run to move kanban cards.
    current_task_id: Optional[str]
    current_task_agent: Optional[str]

    # ── Task allocation mode ──────────────────────────────────────────────────
    # "auto_pull" — task_dispatcher claims tasks automatically.
    # "manual_assignment" — tasks wait for human assignment via the UI.
    task_allocation_mode: str

    # ── Project Director output (optional legacy) ─────────────────────────────
    direction: str

    # ── Discovery gap analysis ───────────────────────────────────────────────
    gap_report: dict
