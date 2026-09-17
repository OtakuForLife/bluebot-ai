# Active Context

## Current focus

Memory bank initialized (2026-09-17) so future sessions have a durable map of the repo.

Latest git work on `main` (`ce7d979`): tests plus improved gap reporting and injecting knowledge documents into agent context.

Open editor file at init time: `src/agents/llm/tools.py` (agent tools, duplicate-task guard, protected files).

## What the app actually does today

Working loop:

1. Select/create project via Qt dialog.
2. Pre-load `tasks.json` into `ProjectManager` (duplicate guard needs prior tasks).
3. User starts orchestrator from `MainWindow`.
4. `start_event_driven` → agents WORKING → seed **discovery** producer run.
5. Discovery `report_gap` / `create_task` → `TASK_CREATED`.
6. `TaskDispatchService` claims and runs the specialist graph.
7. Director creative review → LangGraph interrupt → `HumanReviewDialog`.
8. `TASK_COMPLETED` retriggers discovery (`ProducerService`).

Default LLM: local Ollama, model `qwen3-vl:8b`.

## Active architectural shape

Event-driven dispatch is the live path (`event_driven=True` in `app.py`). Polling workflow + `create_task_dispatcher` still exist for tests / fallback.

Producer is **discovery**, not a separate producer agent. Project director sits on specialist graphs for creative review, not as the marketplace pump.

## Decisions that must not be "cleaned up" casually

- Command/event split and Qt bridges (DECISION 001–002).
- FileManager + directory constants (005, 008).
- Structured `AgentTool`s, no arbitrary exec (006).
- KnowledgeBase isolation (007).
- Ollama-default / offline-first (004).
- LangGraph for orchestration (003).

## Open product gaps (do not pretend they exist)

- No Godot CLI / headless test runner.
- QA, audio, producer agents are roles + knowledge folders only.
- No AUTO_PULL vs MANUAL_ASSIGNMENT UI switch (event type exists).
- No deadlock recovery / project FSM as specified in AGENT_WORKFLOW.
- No SQLite / durable graph checkpoints.
- `ApproveTaskCommand` / `RejectTaskCommand` defined; review currently goes through orchestrator bridge slots.
- `MainWindow` still receives `FileManager` directly for the explorer — slight leak vs the bridge rule.

## Next likely work (not committed; for orientation)

- Wire remaining AGENT_WORKFLOW pieces (allocation mode, QA agent, Godot invoke).
- Keep desloppifying (repo is AI-generated and actively cleaned).
- Harden discovery so it does not spam duplicate tasks (partially done in `tools.py`).

## How to run

```bash
uv run main.py
uv run pytest
```

Needs: Python 3.12, Ollama with the configured model if you want agents to think, Godot only when engine integration lands.
