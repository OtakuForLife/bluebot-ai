"""Tests for Discovery tools and rubric loading."""

import pytest

from src.agents.llm.tools import (
    _create_read_rubric_tool,
    _create_report_gap_tool,
    _create_task_tool,
)
from src.agents.rubrics import load_rubric, list_rubric_ids
from src.events import EventHandler
from src.project.manager import ProjectManager
from src.project.tasks import TaskStatus


def test_load_rubric_known_id() -> None:
    content = load_rubric("vision_document_guide")
    assert content is not None
    assert "Game Vision" in content or "vision" in content.lower()


def test_load_rubric_unknown_id() -> None:
    assert load_rubric("not_a_real_rubric") is None


def test_list_rubric_ids_includes_vision() -> None:
    assert "vision_document_guide" in list_rubric_ids()


def test_report_gap_writes_state() -> None:
    tool = _create_report_gap_tool(ProjectManager(EventHandler()))
    result = tool.execute({
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
        "summary": "No vision document with required sections.",
    })
    assert result["ok"] is True
    state_update = tool.consume_state_update()
    assert state_update["gap_report"]["capability"] == "game_vision"
    assert state_update["gap_report"]["recommended_artifact"] == "design/VISION.md"


def test_read_rubric_tool_returns_content() -> None:
    tool = _create_read_rubric_tool()
    content = tool.execute({"rubric_id": "vision_document_guide"})
    assert "ERROR" not in content
    assert len(content) > 100


def test_read_rubric_tool_unknown_id() -> None:
    tool = _create_read_rubric_tool()
    content = tool.execute({"rubric_id": "missing_rubric"})
    assert content.startswith("ERROR:")


def test_create_task_stores_capability_fields() -> None:
    handler = EventHandler()
    pm = ProjectManager(handler)
    created: list[dict] = []
    from src.events import EventType
    handler.subscribe(EventType.TASK_CREATED, lambda e: created.append(e["payload"]))

    tool = _create_task_tool(pm)
    result = tool.execute({
        "task_type": "design",
        "task_description": "Write the game vision document at design/VISION.md",
        "acceptance_criteria": ["Includes executive summary", "Defines core loop"],
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
    })
    assert result["ok"] is True
    assert len(created) == 1
    payload = created[0]
    assert payload["capability"] == "game_vision"
    assert payload["recommended_artifact"] == "design/VISION.md"
    assert payload["rubric"] == "vision_document_guide"


def test_create_task_duplicate_by_artifact() -> None:
    handler = EventHandler()
    pm = ProjectManager(handler)
    tool = _create_task_tool(pm)

    base = {
        "task_type": "design",
        "task_description": "Write vision",
        "acceptance_criteria": ["Has hook"],
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
    }
    assert tool.execute(base)["ok"] is True

    dup = tool.execute({
        **base,
        "task_description": "Write vision again",
    })
    assert dup["ok"] is False
    assert "Active work exists" in dup["error"]


def test_create_task_allows_same_type_different_artifact() -> None:
    handler = EventHandler()
    pm = ProjectManager(handler)
    tool = _create_task_tool(pm)

    first = tool.execute({
        "task_type": "design",
        "task_description": "Vision doc",
        "acceptance_criteria": ["Hook"],
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
    })
    assert first["ok"] is True

    second = tool.execute({
        "task_type": "design",
        "task_description": "Mechanics doc",
        "acceptance_criteria": ["Core verbs"],
        "capability": "core_mechanics",
        "recommended_artifact": "design/MECHANICS.md",
        "rubric": "mechanics_design",
    })
    assert second["ok"] is True


def test_create_task_allows_improvement_after_done() -> None:
    """A done task must not block rework when content is still inadequate."""
    handler = EventHandler()
    pm = ProjectManager(handler)
    tool = _create_task_tool(pm)

    pm.add_task({
        "id": "done-1",
        "title": "Old vision",
        "description": "Done",
        "task_type": "design",
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "state": TaskStatus.COMPLETED.value,
    })

    result = tool.execute({
        "task_type": "design",
        "task_description": "Revise vision — add core loop and success criteria",
        "acceptance_criteria": ["Defines core loop", "Lists success criteria"],
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
    })
    assert result["ok"] is True


def test_report_gap_rejects_active_work() -> None:
    handler = EventHandler()
    pm = ProjectManager(handler)
    pm.add_task({
        "id": "active-1",
        "title": "Vision in progress",
        "description": "Working",
        "task_type": "design",
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "state": TaskStatus.IN_PROGRESS.value,
    })
    tool = _create_report_gap_tool(pm)
    result = tool.execute({
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
        "summary": "Missing vision",
    })
    assert result["ok"] is False
    assert "Active work exists" in result["error"]


def test_report_gap_allows_gap_when_done_but_content_inadequate() -> None:
    """report_gap must not be blocked by a completed task alone."""
    handler = EventHandler()
    pm = ProjectManager(handler)
    pm.add_task({
        "id": "done-1",
        "title": "Vision done",
        "description": "Done",
        "task_type": "design",
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "state": TaskStatus.COMPLETED.value,
    })
    tool = _create_report_gap_tool(pm)
    result = tool.execute({
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "rubric": "vision_document_guide",
        "summary": "VISION.md missing core loop despite prior approval",
    })
    assert result["ok"] is True
    assert "core loop" in result["message"].lower()


def test_list_tasks_includes_completed() -> None:
    from src.agents.llm.tools import _create_list_tasks_tool

    handler = EventHandler()
    pm = ProjectManager(handler)
    pm.add_task({
        "id": "done-1",
        "title": "Vision",
        "description": "Done",
        "task_type": "design",
        "capability": "game_vision",
        "recommended_artifact": "design/VISION.md",
        "state": TaskStatus.COMPLETED.value,
    })
    tool = _create_list_tasks_tool(pm)
    listing = tool.execute({})
    assert "done" in listing
    assert "game_vision" in listing
    assert "completed" in listing.lower() or "done" in listing
