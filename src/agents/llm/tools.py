from pathlib import Path as _Path
from pydantic import BaseModel, model_validator, ValidationError
from typing import TypeVar as _TypeVar

_T = _TypeVar("_T", bound=BaseModel)

from src.agents.llm.tool import AgentTool
from src.events import EventHandler
from src.project.files import FileManager
from src.project.manager import ProjectManager

_VALID_TASK_TYPES = {"design", "gameplay", "systems", "art"}

# Files that must never be overwritten by specialist agents.
_PROTECTED_FILES = {"tasks.json", "project.json"}

_FINISH_TOOL_NAME = "finish"

class AssignTaskParams(BaseModel):
    task_type: str = ""
    task_description: str = ""
    acceptance_criteria: list[str] = []
    no_more_tasks: bool = False

    @model_validator(mode="after")
    def _check_required_fields(self) -> "AssignTaskParams":
        if not self.no_more_tasks:
            if self.task_type not in _VALID_TASK_TYPES:
                raise ValueError(
                    f"task_type must be one of {sorted(_VALID_TASK_TYPES)}, "
                    f"got '{self.task_type}'. "
                    "Call assign_task with the correct field names."
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
            return err
        assert p is not None
        return file_manager.create_file(
            path=p.path,
            content=p.content,
            project_root=p.project_root,
        )

    return AgentTool(
        name="create_file",
        description=(
            "Create a new file with the given content.\n"
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


def _create_list_files_tool() -> AgentTool:
    """Create the list-files tool so agents can inspect the project tree."""
    def _callback(params: dict) -> str:
        p, err = _validate(ListFilesParams, params)
        if err:
            return err
        assert p is not None
        base = _Path(p.project_root) / p.directory
        if not base.exists():
            return f"Directory does not exist: {base}"
        files = sorted(
            str(f.relative_to(_Path(p.project_root)))
            for f in base.rglob("*")
            if f.is_file() and not f.name.startswith(".")
        )
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


def _create_read_file_tool() -> AgentTool:
    """Create the read-file tool so agents can inspect existing content."""
    def _callback(params: dict) -> str:
        p, err = _validate(ReadFileParams, params)
        if err:
            return err
        assert p is not None
        full = _Path(p.project_root) / p.path
        if not full.exists():
            return f"File does not exist: {p.path}"
        try:
            content = full.read_text(encoding="utf-8")
            return content if content.strip() else "File is empty."
        except Exception as exc:
            return f"Error reading {p.path}: {exc}"

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
            return err
        tasks = project_manager.get_tasks()
        if not tasks:
            return "No tasks found."
        lines = []
        for t in tasks:
            state = t.get("state", "unknown")
            title = t.get("title", "(no title)")
            task_type = t.get("task_type", "")
            agent = t.get("agent", "unassigned")
            lines.append(f"[{state}] ({task_type}) {title} — assigned to: {agent}")
        return "\n".join(lines)

    return AgentTool(
        name="list_tasks",
        description=(
            "List all current tasks with their state, type, title, and assigned agent.\n"
            "Use this before assigning any new task to avoid creating duplicates.\n"
            "Args:\n"
            "  project_root: Absolute path to the project root directory.\n"
            "Returns: A formatted list of tasks, or 'No tasks found.' if none exist yet."
        ),
        callback=_callback,
        parameters_schema=ListTasksParams.model_json_schema(),
    )


def _create_assign_task_tool(
    event_handler: EventHandler,
    project_manager: ProjectManager,
) -> AgentTool:
    """Create the assign-task tool used exclusively by the Project Director.

    The Director calls this tool to place work into the task marketplace.
    Routing to the correct specialist is handled by the task_dispatcher graph
    node + CapabilityEdge router — this tool no longer drives routing directly.

    The only value written back into LangGraph state is ``no_more_tasks``,
    which the Director uses to signal "nothing left to create this iteration".

    Duplicate detection uses the in-memory ProjectManager — never reads disk.
    """
    from datetime import datetime
    from src.events import Event, EventType
    import uuid
    from src.project.tasks import TaskStatus

    # Active states: any task that is not yet completed or cancelled blocks a
    # duplicate.  Using the set complement so new TaskStatus values are safe.
    _INACTIVE_STATES = {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}

    def _no_dup_error(task_type: str, states: list[str]) -> dict:
        return {
            "no_more_tasks": False,
            "error": (
                f"Duplicate prevented: a '{task_type}' task already exists "
                f"in state(s) {states}. Do NOT create another one. "
                "Either call assign_task with a different task_type, "
                "or call assign_task with no_more_tasks=true if nothing else is needed."
            ),
        }

    def _callback(params: dict) -> dict:
        p, err = _validate(AssignTaskParams, params)
        if err:
            # The LLM sees this dict as the tool result and can retry.
            return {"no_more_tasks": False, "error": err}
        assert p is not None

        if p.no_more_tasks:
            return {"no_more_tasks": True, "message": "Director signalled: no more tasks."}

        task_type = p.task_type
        task_description = p.task_description
        acceptance_criteria = p.acceptance_criteria

        # Server-side duplicate guard — no disk I/O.
        active = [
            t.get("state", "")
            for t in project_manager.get_tasks()
            if t.get("task_type") == task_type
            and t.get("state") not in _INACTIVE_STATES
        ]
        if active:
            return _no_dup_error(task_type, active)

        task_id = str(uuid.uuid4())

        # Place task in the marketplace with OPEN status.
        # The task_dispatcher node will claim it and route to the right agent.
        event_handler.emit_event(Event(
            type=EventType.TASK_CREATED,
            payload={
                "id": task_id,
                "title": task_description[:80],
                "description": task_description,
                "task_type": task_type,
                "acceptance_criteria": acceptance_criteria,
                "state": TaskStatus.OPEN.value,  # "todo" — open in marketplace
            },
            timestamp=datetime.now().isoformat(),
        ))

        return {
            "no_more_tasks": False,
            "message": (
                f"Task '{task_type}' placed in the marketplace (id={task_id}). "
                "The task_dispatcher will assign it to the appropriate specialist."
            ),
        }

    return AgentTool(
        name="assign_task",
        description=(
            "Place a new task in the task marketplace for a specialist to pick up.\n"
            "Args:\n"
            "  task_type: One of 'design' | 'gameplay' | 'systems' | 'art'.\n"
            "  task_description: Full description of what the specialist must do, "
            "including context from the game brief and any review feedback.\n"
            "  acceptance_criteria: List of strings — objective checks that verify "
            "the task is done.\n"
            "  no_more_tasks: Set to true when all required work exists in the "
            "marketplace or is already done.\n"
            "Returns: confirmation that the task was added to the marketplace."
        ),
        callback=_callback,
        # Only no_more_tasks needs to flow back into graph state.
        # Routing is handled by task_dispatcher + CapabilityEdge, not by state keys.
        state_keys=["no_more_tasks"],
        parameters_schema=AssignTaskParams.model_json_schema(),
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
            return {"direction": "", "message": err}
        assert p is not None
        return {
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