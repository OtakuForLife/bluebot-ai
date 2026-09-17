# Tech Context

## Runtime

- **Language:** Python 3.12
- **Package/runner:** `uv` (`uv run main.py`, `uv run pytest`)
- **Build:** hatchling; package is `src`
- **Version:** 0.1.0

## Dependencies (runtime)

From `pyproject.toml`:

| Package | Why |
|---------|-----|
| PySide6 | Desktop UI |
| langgraph | Agent graphs, interrupts, MemorySaver checkpointer |
| langchain-core | Messages, StructuredTool |
| aiohttp | HTTP for LLM providers |
| markdown | Knowledge / UI rendering |
| arize-phoenix + OpenTelemetry | Optional local LLM tracing |

Dev: `pytest`, `pytest-asyncio`.

## LLM

- **Default:** Ollama at `http://localhost:11434`
- **App default model:** `qwen3-vl:8b`
- **Optional:** OpenAI-compatible provider (NFR-4: proprietary APIs allowed as expansion, not required)
- Tool calling: native when the model supports it; `base.py` also parses JSON / loose text tool calls for local models

## Persistence (current)

- Project folders on disk
- `project.json`, `tasks.json`
- `projects.json` / `settings.json` at repo root are gitignored (local app state)
- LangGraph `MemorySaver` is **in-memory** (not durable across process restarts)
- SQLite is documented as a future option in ARCHITECTURE / AGENT_WORKFLOW — **not implemented**

## UI

- PySide6 widgets (not QML)
- Background work: `QThread` + dedicated asyncio loop
- Logging: stdlib `logging` + `LoggingBridge` / `QtLogHandler` into the output panel

## Godot

- Target: Godot 4.x, GDScript
- User-installed engine (SC-2)
- **Not implemented yet:** CLI launch, headless tests, GUT integration, parse of Godot test output

## Tests

- Location: `tests/`
- Run: `uv run pytest` (pythonpath includes `.`)
- Coverage of: command executor, FileManager, ProjectManager, graphs, ReAct loop, knowledge, providers, kanban, bridges, discovery tools, human review dialog

## Dev conventions that are load-bearing

1. UI → bridges only (`QtEventBridge`, `QtCommandBridge`).
2. Files → `FileManager` + its directory constants.
3. Agent docs → `KnowledgeBase`, not raw `knowledge/` paths.
4. New agent tools → instantiate `AgentTool` in `src/agents/llm/tool.py` / `tools.py`.
5. New events → add to `EventType` and wire the Qt bridge map if the UI should see them.
6. Prefer deletion and stdlib (ponytail / lazy senior rule). No new deps unless required.

## Packaging

PyInstaller (or equivalent) is planned for Windows/Linux user-space installs. Not in the current toolchain.

## Tooling not yet in pyproject

ARCHITECTURE mentions black, ruff, mypy as intended quality tools. They are **not** listed as project dependencies today.
