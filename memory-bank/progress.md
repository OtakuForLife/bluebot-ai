# Progress

## Status

**Early but runnable desktop studio.** Core UI, event bus, project files, event-driven multi-agent loop, human review, and a solid pytest suite exist. Godot engine integration and several planned actor types do not.

Version: `0.1.0` on branch `main` (tracks `origin/main`).

## What works

- App bootstrap: logging, optional Phoenix, component wiring in `src/app.py`
- Project create/open and on-disk structure via `FileManager`
- Task marketplace in `ProjectManager` (open / in_progress / review / done / cancelled)
- Persist and reload tasks from `tasks.json`
- Event-driven orchestrator start/stop from the UI
- Discovery → task create → specialist dispatch → director review → human interrupt
- File tools with protected `project.json` / `tasks.json`
- Duplicate/active-work guard on `create_task` / `report_gap`
- Knowledge loading per role + discovery knowledge (`knowledge/discovery/studio_deliverables.md`)
- Kanban board, agent panel, file explorer, log panel, LLM config panel, human review dialog
- LLM providers: Ollama + OpenAI, registry/factory, LangChain adapter
- ReAct loop with finish tool and text-tool-call recovery for local models
- pytest coverage across backend and several UI pieces

## What is left (requirements vs code)

| Area | Requirement | Code |
|------|-------------|------|
| Godot generate/modify files | FR-6, FR-7 | File tools exist; no Godot-aware validation |
| Launch Godot | FR-8 | Missing |
| Godot errors / tests | FR-9–FR-13 | Missing |
| Concurrent agents | FR-1, NFR-5 | Graphs can run; no real parallelism policy |
| Manual vs auto assignment | AGENT_WORKFLOW §4 | Event type only |
| QA / audio / producer agents | FR-2, knowledge folders | Roles unused |
| Packaging | FR-16, SC-3 | Not started |
| SQLite history | ARCHITECTURE §6 | Not started |
| Deadlock recovery / release FSM | AGENT_WORKFLOW | Not started |

## Known issues / sharp edges

- `LLMConfig.model` default (`llama3`) ≠ app override (`qwen3-vl:8b`). Easy to confuse in tests vs runtime.
- `KnowledgeBase.KNOWLEGDE_PATH` typo is the real attribute name.
- `knowledge/README.md` still says `docs/` layout; actual root is `knowledge/`.
- REQUIREMENTS.md duplicates FR-6/FR-7 numbers (agent system vs Godot).
- In-memory LangGraph checkpoints: restart loses in-flight graph state (tasks on disk survive).
- UI `FileManager` injection in `MainWindow` bypasses the strict bridge rule for the explorer.
- Local-model tool-call parsing is heuristic; flaky models still need the finish-tool escape hatch.

## Recent commits (newest first)

- `ce7d979` add tests and improve gap and inject knowledge documents
- `36ff3e6` adding tests and improve error handling
- `180c04a` Workflow adjustments
- `b5b790a` add extensive in-app logging
- `1e1fbd5` add autonomous mode
- `a24cd3a` added kanban board and moved file explorer

## Test command

```bash
uv run pytest
uv run pytest tests/test_app.py
uv run pytest --cov=src
```
