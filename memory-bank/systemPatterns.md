# System Patterns

## Three primary patterns

1. **Event-driven communication** — `EventHandler` + `CommandBus`
2. **Qt bridge isolation** — UI never calls backend services directly
3. **LangGraph orchestration** — workflows as compiled graphs over shared `AgentMessage` state

Canonical ADRs: `docs/DECISIONS.md`. Agent rules: `AGENTS.md`.

---

## Event + command bus

**Events** (`src/events.py`) are notifications. Sync subscribers run inline; async subscribers are scheduled on the workflow asyncio loop via `run_coroutine_threadsafe`.

Important event types: `TASK_CREATED`, `TASK_COMPLETED`, `PROJECT_FILE_*`, `HUMAN_INPUT_*`, `AGENT_*`, `AGENTIC_SYSTEM_*`.

**Commands** (`src/commands/`) are explicit actions: `CreateProjectCommand`, `CreateTaskCommand`, `ApproveTaskCommand`, `RejectTaskCommand`. Dispatched through `CommandBus` to `CommandExecutor`.

Rule: actors never call each other. They emit events or dispatch commands.

---

## Qt bridges

| Bridge | Job |
|--------|-----|
| `QtEventBridge` | backend events → Qt signals |
| `QtCommandBridge` | Qt slots → `CommandBus` + orchestrator start/stop |
| `OrchestratorBridge` | thin facade for lifecycle, review, provider swap |

UI widgets subscribe to signals / dispatch commands only. Do not import `ProjectManager`, `AgentOrchestrator`, or `FileManager` into widgets except where `MainWindow` is given `FileManager` for the file explorer (existing exception — prefer not to grow it).

Workflow runs in `WorkflowThread` (`src/ui/main_window.py`) so the Qt main thread stays free.

---

## Agent orchestration (current runtime)

`app.py` builds agents, then `AgentOrchestrator(..., event_driven=True)`.

**Producer graph:** `discovery_agent` (entry). On system start and after task completion, `ProducerService` re-runs discovery.

**Task graphs:** one compiled graph per specialist capability (`design`, `gameplay`, `systems`, `art`):

```
specialist → project_director (creative review) → human_review (interrupt) or END
```

`TaskDispatchService` listens for `TASK_CREATED`, claims the task, runs the matching graph.

`GraphRegistry` holds compiled producer + per-capability graphs. `GraphBuilder` is a pure, testable compiler of `WorkflowSpec` (direct / conditional / capability edges).

There is also a **polling** path (`run_polling_workflow`, `create_workflow_spec` with a task dispatcher node). The shipped app uses the event-driven path, not polling.

---

## Agents

Created in `src/app.py` `_create_agents`:

| Node | Role | Capabilities | Typical tools |
|------|------|--------------|---------------|
| `project_director` | governance / creative review | none | list/read files, `submit_creative_review` |
| `discovery_agent` | gap analysis + task creation | none | list/read, list/create tasks, `report_gap`, `read_rubric` |
| `game_designer` | design docs | `design` | file read/write/list |
| `game_developer` | GDScript / systems | `gameplay`, `systems` | file read/write/list |
| `game_artist` | visual direction | `art` | file read/write/list |

Roles exist in `AgentRole` but are **not instantiated**: `QA_TESTER`, `AUDIO_ENGINEER`, `GAME_PRODUCER`.

Each `Agent` runs a ReAct-style tool loop (`src/agents/base.py`) with a `finish` tool. Local models often emit bare tool names; parsers in `base.py` recover those.

---

## File and project access

- All project file I/O: `FileManager` (`src/project/files.py`).
- Directory names: `FileManager` constants (`SCRIPTS_DIR` = `game`, `DESIGN_DIR`, `ASSETS_DIR`, …). Never raw path strings for those dirs.
- Tasks: `ProjectManager` + `tasks.json`. Duplicate-guard on create (active task for same artifact/capability).
- Protected files agents must not overwrite: `tasks.json`, `project.json`.
- Knowledge: `KnowledgeBase` over `knowledge/{role}/`. Never read `knowledge/` ad hoc from agents.

Standard project tree:

```
design/          VISION.md, MECHANICS.md, …
assets/graphics, assets/audio
game/            project.godot, scripts
project.json
tasks.json
```

---

## LLM layer

- Interface: `BaseLLMProvider` + `LLMConfig`.
- Registry/factory: `ProviderRegistry` / `ProviderFactory`.
- Registered: `ollama` (default), `openai`.
- Agents wrap providers in `LangChainAdapter`.
- Tools are `AgentTool` instances (`src/agents/llm/tool.py`), assembled in `build_agent_tools`.

Default app config in `app.py`: model `qwen3-vl:8b`, temperature 0.7, max_tokens 4096. (`LLMConfig` dataclass default model is still `llama3` — the app override wins at runtime.)

Optional **Arize Phoenix** tracing at `http://localhost:6006` (offline). Missing package is a warning, not a crash.

---

## Human review

`human_review_node` uses LangGraph `interrupt`. `HumanReviewCoordinator` emits `HUMAN_INPUT_REQUESTED`, blocks on an asyncio Event, and resumes when the UI calls `submit_human_review`. Reject can trigger `request_task_rework`.

---

## Component map

```
main.py → app.main()
  EventHandler, CommandBus
  ProjectManager, FileManager
  OllamaProvider
  Agents + AgentOrchestrator
  TaskDispatchService, ProducerService
  Qt bridges → ProjectSelectionWindow → MainWindow
```
