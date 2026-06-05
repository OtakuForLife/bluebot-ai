"""Agent workflow state helpers."""

from typing import Optional
from uuid import uuid4

from src.agents.state import AgentMessage


def build_initial_workflow_state(project: dict) -> AgentMessage:
    """Build the startup AgentMessage from a selected project dict."""
    brief = project.get("brief") or (
        f"Project: {project.get('name', 'Unknown')}\n"
        f"{project.get('description', '')}"
    )
    return {
        "task_id": str(uuid4()),
        "task_type": "",
        "task_description": brief,
        "acceptance_criteria": [],
        "capability": "",
        "recommended_artifact": "",
        "rubric": "",
        "gap_report": {},
        "workspace_root": project.get("path", "."),
        "allowed_paths": [project.get("path", ".")],
        "last_agent": None,
        "messages": [],
        "tool_results": [],
        "modified_files": [],
        "created_files": [],
        "deleted_files": [],
        "outcome": None,
        "errors": [],
        "no_more_tasks": False,
        "human_review_approved": None,
        "human_review_comment": None,
        "creative_review_approved": None,
        "creative_review_comment": None,
        "current_task_id": None,
        "current_task_agent": None,
        "task_allocation_mode": "auto_pull",
        "direction": "",
    }


def _iteration_reset_fields() -> dict:
    return {
        "messages": [],
        "tool_results": [],
        "created_files": [],
        "modified_files": [],
        "deleted_files": [],
        "errors": [],
        "outcome": None,
        "human_review_approved": None,
        "human_review_comment": None,
        "creative_review_approved": None,
        "creative_review_comment": None,
        "last_agent": None,
    }


def build_task_state(
    base: AgentMessage,
    *,
    task_id: str,
    task_type: str,
    task_description: str,
    acceptance_criteria: list[str],
    agent_name: str,
    capability: str = "",
    recommended_artifact: str = "",
    rubric: str = "",
) -> AgentMessage:
    """Build state for a specialist task graph run."""
    return {
        **base,
        **_iteration_reset_fields(),
        "task_id": task_id,
        "task_type": task_type,
        "task_description": task_description,
        "acceptance_criteria": acceptance_criteria,
        "capability": capability,
        "recommended_artifact": recommended_artifact,
        "rubric": rubric,
        "current_task_id": task_id,
        "current_task_agent": agent_name,
        "no_more_tasks": False,
        "creative_review_approved": None,
        "creative_review_comment": None,
    }


def build_producer_reset_state(base: AgentMessage) -> AgentMessage:
    """Reset per-iteration fields before a producer graph run."""
    return {
        **base,
        **_iteration_reset_fields(),
        "task_id": str(uuid4()),
        "no_more_tasks": False,
        "current_task_id": None,
        "current_task_agent": None,
        "direction": "",
        "gap_report": {},
    }


def build_polling_reset_state(
    base: AgentMessage, *, original_brief: str
) -> AgentMessage:
    """Reset state between polling-loop iterations."""
    return {
        **base,
        **_iteration_reset_fields(),
        "task_id": str(uuid4()),
        "task_type": "",
        "task_description": original_brief,
        "current_task_id": None,
        "current_task_agent": None,
        "human_review_comment": "",
    }
