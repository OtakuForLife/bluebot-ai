from pathlib import Path as _Path
from pydantic import BaseModel, model_validator, ValidationError
from typing import TypeVar as _TypeVar

_T = _TypeVar("_T", bound=BaseModel)

from src.agents.llm.tool import AgentTool
from src.project.files import FileManager
from src.project.manager import ProjectManager

_VALID_TASK_TYPES = {"design", "gameplay", "systems", "art"}

# Files that must never be overwritten by specialist agents.
_PROTECTED_FILES = {"tasks.json", "project.json"}

_FINISH_TOOL_NAME = "finish"


def _normalize_artifact_path(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def _active_work_exists_message(capability: str, artifact: str, states: list[str]) -> str:
    target = artifact or capability or "this deliverable"
    state_label = ", ".join(states) if states else "active"
    return (
        f"Active work exists for '{target}' (state: {state_label}). "
        "Do NOT report_gap or create_task for this capability. "
        "Call create_task with no_more_tasks=true, then finish."
    )


_INACTIVE_TASK_STATES: set[str] = set()


def _get_inactive_task_states() -> set[str]:
    from src.project.tasks import TaskStatus

    global _INACTIVE_TASK_STATES
    if not _INACTIVE_TASK_STATES:
        _INACTIVE_TASK_STATES = {
            TaskStatus.COMPLETED.value,
            TaskStatus.CANCELLED.value,
        }
    return _INACTIVE_TASK_STATES


def _active_duplicate(
    project_manager: ProjectManager,
    task_type: str,
    artifact: str,
    capability: str,
) -> tuple[bool, list[str]]:
    inactive = _get_inactive_task_states()
    active_states: list[str] = []
    for t in project_manager.get_tasks():
        if t.get("state") in inactive:
            continue
        if artifact and _normalize_artifact_path(
            t.get("recommended_artifact", "")
        ) == _normalize_artifact_path(artifact):
            active_states.append(t.get("state", "unknown"))
        elif capability and t.get("capability") == capability:
            active_states.append(t.get("state", "unknown"))
        elif (
            not artifact
            and not capability
            and t.get("task_type") == task_type
        ):
            active_states.append(t.get("state", "unknown"))
    return bool(active_states), active_states

class CreateTaskParams(BaseModel):
    task_type: str = ""
    task_description: str = ""
    acceptance_criteria: list[str] = []
    capability: str = ""
    recommended_artifact: str = ""
    rubric: str = ""
    no_more_tasks: bool = False

    @model_validator(mode="after")
    def _check_required_fields(self) -> "CreateTaskParams":
        if not self.no_more_tasks:
            if self.task_type not in _VALID_TASK_TYPES:
                raise ValueError(
                    f"task_type must be one of {sorted(_VALID_TASK_TYPES)}, "
                    f"got '{self.task_type}'. "
                    "Call create_task with the correct field names."
                )
            if not self.task_description.strip():
                raise ValueError(
                    "task_description is required and must not be empty "
                    "when no_more_tasks is False."
                )
        return self


class CreateFileParams(BaseModel):
    path: str
    content: str
    project_root: str = "."

    @model_validator(mode="after")
    def _block_protected_files(self) -> "CreateFileParams":
        if _Path(self.path).name in _PROTECTED_FILES:
            raise ValueError(
                f"'{self.path}' is a protected system file. "
                "Specialists must not overwrite it. Choose a different path."
            )
        return self


class ReadFileParams(BaseModel):
    path: str
    project_root: str = "."


class ListFilesParams(BaseModel):
    directory: str = ""
    project_root: str = "."


class ListTasksParams(BaseModel):
    project_root: str = "."


class SetDirectionParams(BaseModel):
    directive: str


class SubmitCreativeReviewParams(BaseModel):
    approved: bool
    comment: str = ""

    @model_validator(mode="after")
    def _require_comment_on_reject(self) -> "SubmitCreativeReviewParams":
        if not self.approved and not self.comment.strip():
            raise ValueError(
                "comment is required when approved is false — "
                "explain what misaligns with the vision or design."
            )
        return self


class ReportGapParams(BaseModel):
    capability: str
    recommended_artifact: str
    rubric: str
    missing_capabilities: list[str] = []
    summary: str = ""

    @model_validator(mode="after")
    def _check_fields(self) -> "ReportGapParams":
        if not self.capability.strip():
            raise ValueError("capability is required")
        if not self.recommended_artifact.strip():
            raise ValueError("recommended_artifact is required")
        if not self.rubric.strip():
            raise ValueError("rubric is required")
        return self


class ReadRubricParams(BaseModel):
    rubric_id: str


def _validate(model_cls: type[_T], params: dict) -> tuple[_T | None, str | None]:
    """Validate *params* against *model_cls*.

    Returns ``(instance, None)`` on success or ``(None, error_message)`` on
    failure. The error message is suitable to return directly as a tool result
    so the LLM receives actionable feedback.
    """
    try:
        return model_cls.model_validate(params), None
    except ValidationError as exc:
        # Summarise all errors in one readable string
        messages = "; ".join(
            f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        return None, f"Tool call validation error: {messages}"

def _create_file_tool(file_manager: FileManager) -> AgentTool:
    """Create the file creation tool for worker agents."""
    def _callback(params: dict) -> str:
        p, err = _validate(CreateFileParams, params)
        if err:
            return _tool_error(err)
        assert p is not None
        result = file_manager.create_file(
            path=p.path,
            content=p.content,
            project_root=p.project_root,
        )
        if result.startswith("Error"):
            return _tool_error(result)
        return result

    return AgentTool(
        name="create_file",
        description=(
            "Create or overwrite a project file with the given content.\n"
            "Use this for new deliverables and for revising existing files after rework.\n"
            "Args:\n"
            "  path: Relative path to the file (e.g. 'design/VISION.md').\n"
            "  content: Full text content to write.\n"
            "  project_root: Absolute path to the project root directory.\n"
            "NOTE: tasks.json and project.json are protected — do not use this path.\n"
            "Returns: success or error message."
        ),
        callback=_callback,
        parameters_schema=CreateFileParams.model_json_schema(),
    )


def _tool_error(message: str) -> str:
    return f"ERROR: {message}"


def _state_tool_error(message: str, **extra: object) -> dict:
    return {"ok": False, "error": message, **extra}


def _create_list_files_tool(file_manager: FileManager) -> AgentTool:
    """Create the list-files tool so agents can inspect the project tree."""
    def _callback(params: dict) -> str:
        p, err = _validate(ListFilesParams, params)
        if err:
            return _tool_error(err)
        assert p is not None
        root = _Path(p.project_root)
        files = file_manager.list_project_files(root, p.directory)
        if not files and p.directory and not (root / p.directory).exists():
            return _tool_error(f"Directory does not exist: {root / p.directory}")
        return "\n".join(files) if files else "(no files found)"

    return AgentTool(
        name="list_files",
        description=(
            "List all files inside a project directory.\n"
            "Args:\n"
            "  project_root: Absolute path to the project root directory.\n"
            "  directory: Sub-directory to list relative to project_root "
            "(e.g. 'design'). Leave empty to list the whole project.\n"
            "Returns: newline-separated relative file paths."
        ),
        callback=_callback,
        parameters_schema=ListFilesParams.model_json_schema(),
    )


def _create_read_file_tool(file_manager: FileManager) -> AgentTool:
    """Create the read-file tool so agents can inspect existing content."""
    def _callback(params: dict) -> str:
        p, err = _validate(ReadFileParams, params)
        if err:
            return _tool_error(err)
        assert p is not None
        content = file_manager.read_project_file(_Path(p.project_root), p.path)
        if content is None:
            return _tool_error(f"File does not exist or could not be read: {p.path}")
        return content if content.strip() else "File is empty."

    return AgentTool(
        name="read_file",
        description=(
            "Read the contents of a project file.\n"
            "Args:\n"
            "  project_root: Absolute path to the project root directory.\n"
            "  path: Relative path to the file (e.g. 'design/VISION.md').\n"
            "Returns: file contents as text, or an error message."
        ),
        callback=_callback,
        parameters_schema=ReadFileParams.model_json_schema(),
    )


def _create_list_tasks_tool(project_manager: ProjectManager) -> AgentTool:
    """Create a tool that returns all current tasks from the in-memory store.

    Reads from ProjectManager (which mirrors task events) — never from disk.
    tasks.json is a persistence file owned by the UI, not by agents.
    """
    def _callback(params: dict) -> str:
        p, err = _validate(ListTasksParams, params)
        if err:
            return _tool_error(err)
        tasks = project_manager.get_tasks()
        if not tasks:
            return "No tasks found."
        lines = [
            "All tasks (includes completed/done — a done task does NOT mean content is adequate; "
            "always read_file and judge against the rubric):"
        ]
        for t in tasks:
            state = t.get("state", "unknown")
            title = t.get("title", "(no title)")
            task_type = t.get("task_type", "")
            agent = t.get("agent", "unassigned")
            artifact = t.get("recommended_artifact", "")
            capability = t.get("capability", "")
            extra = ""
            if artifact or capability:
                extra = f" — capability={capability or '?'}, artifact={artifact or '?'}"
            lines.append(
                f"[{state}] ({task_type}) {title} — assigned to: {agent}{extra}"
            )
        return "\n".join(lines)

    return AgentTool(
        name="list_tasks",
        description=(
            "List every task in the project — open, in-progress, review, AND completed (done).\n"
            "Use this to see active work — skip report_gap/create_task only when an ACTIVE "
            "(todo/in_progress/review) task already targets the same capability/artifact.\n"
            "Args:\n"
            "  project_root: Absolute path to the project root directory.\n"
            "Returns: A formatted list of tasks, or 'No tasks found.' if none exist yet."
        ),
        callback=_callback,
        parameters_schema=ListTasksParams.model_json_schema(),
    )


def _create_task_tool(
    project_manager: ProjectManager,
) -> AgentTool:
    """Create the create_task tool used by the Discovery Agent.

    Discovery calls this tool to place work into the open task marketplace.
    Assignment to a specialist is handled separately by TaskDispatchService
    on TASK_CREATED — this tool does not assign work directly.

    The only value written back into LangGraph state is ``no_more_tasks``,
    which the Director uses to signal "nothing left to create this iteration".

    Duplicate detection uses the in-memory ProjectManager — never reads disk.
    """
    import uuid
    from src.project.tasks import TaskStatus

    def _no_dup_error(
        task_type: str,
        states: list[str],
        *,
        artifact: str = "",
        capability: str = "",
    ) -> dict:
        return _state_tool_error(
            _active_work_exists_message(
                capability or task_type, artifact, states
            ),
            no_more_tasks=False,
        )

    def _callback(params: dict) -> dict:
        p, err = _validate(CreateTaskParams, params)
        if err:
            return _state_tool_error(err, no_more_tasks=False)
        assert p is not None

        if p.no_more_tasks:
            return {"ok": True, "no_more_tasks": True, "message": "Director signalled: no more tasks."}

        task_type = p.task_type
        task_description = p.task_description
        acceptance_criteria = p.acceptance_criteria
        capability = p.capability.strip()
        recommended_artifact = p.recommended_artifact.strip()
        rubric = p.rubric.strip()

        dup, active = _active_duplicate(
            project_manager, task_type, recommended_artifact, capability
        )
        if dup:
            return _no_dup_error(
                task_type,
                active,
                artifact=recommended_artifact,
                capability=capability,
            )

        task_id = str(uuid.uuid4())

        task_payload: dict = {
            "id": task_id,
            "title": task_description[:80],
            "description": task_description,
            "task_type": task_type,
            "acceptance_criteria": acceptance_criteria,
            "state": TaskStatus.OPEN.value,
        }
        if capability:
            task_payload["capability"] = capability
        if recommended_artifact:
            task_payload["recommended_artifact"] = recommended_artifact
        if rubric:
            task_payload["rubric"] = rubric

        project_manager.add_task(task_payload)

        return {
            "ok": True,
            "no_more_tasks": False,
            "message": (
                f"Task '{task_type}' placed in the marketplace (id={task_id}). "
                "The task_dispatcher will assign it to the appropriate specialist."
            ),
        }

    return AgentTool(
        name="create_task",
        description=(
            "Create a new open task in the task marketplace (does not assign it).\n"
            "Args:\n"
            "  task_type: One of 'design' | 'gameplay' | 'systems' | 'art'.\n"
            "  task_description: Full description of what the specialist must do, "
            "including context from the game brief and any review feedback.\n"
            "  acceptance_criteria: List of strings — objective checks that verify "
            "the task is done (derive from read_rubric when possible).\n"
            "  capability: Studio capability id (e.g. 'game_vision').\n"
            "  recommended_artifact: Target file path (e.g. 'design/VISION.md').\n"
            "  rubric: Quality spec id from the catalog (e.g. 'vision_document_guide').\n"
            "  no_more_tasks: Set to true when all required work exists in the "
            "marketplace or is already done.\n"
            "Returns: confirmation that the task was added to the marketplace."
        ),
        callback=_callback,
        # Only no_more_tasks needs to flow back into graph state.
        # Routing is handled by task_dispatcher + CapabilityEdge, not by state keys.
        state_keys=["no_more_tasks"],
        parameters_schema=CreateTaskParams.model_json_schema(),
    )


def _create_set_direction_tool() -> AgentTool:
    """Create the set-direction tool used exclusively by the Project Director.

    The Director calls this tool after analysing the project to record a
    short strategic directive in the shared LangGraph state.  The Discovery
    Agent reads ``state["direction"]`` via its prompt so it knows which gap
    to focus on when creating the next task.

    This tool is terminal — calling it ends the Director's ReAct loop.
    """

    def _callback(params: dict) -> dict:
        p, err = _validate(SetDirectionParams, params)
        if err:
            return _state_tool_error(err, direction="")
        assert p is not None
        return {
            "ok": True,
            "direction": p.directive,
            "message": f"Direction set: {p.directive}",
        }

    return AgentTool(
        name="set_direction",
        description=(
            "Record the Project Director's strategic directive for this iteration.\n"
            "Call this ONCE after reviewing files and tasks.\n"
            "Args:\n"
            "  directive: A short, clear statement of what work is most needed next.\n"
            "    Examples:\n"
            "      'Create the game vision document (design/VISION.md)'\n"
            "      'Implement the first playable feature based on existing design docs'\n"
            "      'PROJECT COMPLETE — all required work is done'\n"
            "Returns: confirmation that the directive was recorded."
        ),
        callback=_callback,
        state_keys=["direction"],
        parameters_schema=SetDirectionParams.model_json_schema(),
    )


def _create_submit_creative_review_tool() -> AgentTool:
    """Creative Director verdict after a specialist completes a deliverable."""

    def _callback(params: dict) -> dict:
        p, err = _validate(SubmitCreativeReviewParams, params)
        if err:
            return _state_tool_error(
                err,
                creative_review_approved=None,
                creative_review_comment="",
            )
        assert p is not None
        verdict = "approved" if p.approved else "rejected"
        return {
            "ok": True,
            "creative_review_approved": p.approved,
            "creative_review_comment": p.comment.strip(),
            "message": f"Creative review {verdict}. {p.comment}".strip(),
        }

    return AgentTool(
        name="submit_creative_review",
        description=(
            "Submit the Creative Director's alignment verdict on a deliverable.\n"
            "Call after reading the deliverable and relevant design docs.\n"
            "Args:\n"
            "  approved: true if the work aligns with the game vision and design; "
            "false if it misaligns, contradicts other docs, or misses creative intent.\n"
            "  comment: Actionable feedback — required when rejecting; optional praise "
            "or notes when approving.\n"
            "Returns: confirmation that the verdict was recorded."
        ),
        callback=_callback,
        state_keys=["creative_review_approved", "creative_review_comment"],
        parameters_schema=SubmitCreativeReviewParams.model_json_schema(),
    )


def _create_report_gap_tool(project_manager: ProjectManager) -> AgentTool:
    """Record structured gap analysis in LangGraph state for tracing."""

    def _callback(params: dict) -> dict:
        p, err = _validate(ReportGapParams, params)
        if err:
            return _state_tool_error(err, gap_report={})
        assert p is not None

        _dup, active_states = _active_duplicate(
            project_manager, "", p.recommended_artifact, p.capability
        )
        if _dup:
            return _state_tool_error(
                _active_work_exists_message(
                    p.capability, p.recommended_artifact, active_states
                ),
                gap_report={},
            )

        missing = p.missing_capabilities or [p.capability]
        gap_report = {
            "capability": p.capability,
            "recommended_artifact": p.recommended_artifact,
            "rubric": p.rubric,
            "missing_capabilities": missing,
            "summary": p.summary or f"Missing capability: {p.capability}",
        }
        return {
            "ok": True,
            "gap_report": gap_report,
            "message": gap_report["summary"],
        }

    return AgentTool(
        name="report_gap",
        description=(
            "Record a structured gap finding after inspecting project files.\n"
            "Call this once you have identified the highest-priority missing capability.\n"
            "Args:\n"
            "  capability: Capability id from the Studio Deliverables Catalog.\n"
            "  recommended_artifact: Target file to produce (e.g. 'design/VISION.md').\n"
            "  rubric: Rubric id for quality criteria (e.g. 'vision_document_guide').\n"
            "  missing_capabilities: Optional list of related gaps; defaults to [capability].\n"
            "  summary: One-sentence explanation of why this gap exists.\n"
            "Returns: confirmation and the structured gap report."
        ),
        callback=_callback,
        state_keys=["gap_report"],
        parameters_schema=ReportGapParams.model_json_schema(),
    )


def _create_read_rubric_tool() -> AgentTool:
    """Load a quality rubric from knowledge/ by id."""

    from src.agents.rubrics import list_rubric_ids, load_rubric

    def _callback(params: dict) -> str:
        p, err = _validate(ReadRubricParams, params)
        if err:
            return _tool_error(err)
        assert p is not None
        content = load_rubric(p.rubric_id)
        if content is None:
            known = ", ".join(list_rubric_ids())
            return _tool_error(
                f"Unknown rubric_id '{p.rubric_id}'. Known ids: {known}"
            )
        return content

    return AgentTool(
        name="read_rubric",
        description=(
            "Load the full quality rubric for a deliverable from knowledge/.\n"
            "Use this after report_gap to derive objective acceptance_criteria.\n"
            "Args:\n"
            "  rubric_id: Rubric id from the catalog (e.g. 'vision_document_guide').\n"
            "Returns: full markdown rubric text."
        ),
        callback=_callback,
        parameters_schema=ReadRubricParams.model_json_schema(),
    )


def _create_finish_tool() -> AgentTool:
    """Return the finish tool that every agent receives automatically.

    Calling finish() is the only way to exit the ReAct loop.  The agent
    must call it once its work is complete.
    """
    def _callback(params: dict) -> str:
        summary = params.get("summary", "")
        return f"Work complete. {summary}".strip()

    return AgentTool(
        name=_FINISH_TOOL_NAME,
        description=(
            "Signal that your work for this turn is complete.\n"
            "Call this ONCE when you have nothing more to do.\n"
            "Args:\n"
            "  summary: Optional one-sentence summary of what was accomplished.\n"
            "Returns: confirmation."
        ),
        callback=_callback,
        parameters_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "What was accomplished."},
            },
        },
    )


def build_agent_tools(
    file_manager: FileManager,
    project_manager: ProjectManager,
) -> dict[str, AgentTool]:
    """Create the shared agent tool set for application wiring."""
    return {
        "file": _create_file_tool(file_manager),
        "list_files": _create_list_files_tool(file_manager),
        "read_file": _create_read_file_tool(file_manager),
        "list_tasks": _create_list_tasks_tool(project_manager),
        "create_task": _create_task_tool(project_manager),
        "set_direction": _create_set_direction_tool(),
        "submit_creative_review": _create_submit_creative_review_tool(),
        "report_gap": _create_report_gap_tool(project_manager),
        "read_rubric": _create_read_rubric_tool(),
    }


