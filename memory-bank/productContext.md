# Product Context

## Why it exists

Game development is a pile of specialized work (vision, mechanics, code, art, QA) that a solo or small team has to do serially. Bluebot AI turns that into a **studio of agents** that continuously ask "what is missing?" and then do the work, with the human able to jump in as teammate, reviewer, or director.

## Problems it solves

- Blank-page start: turn a brief into vision, pillars, and a first task set.
- Context switching: agents keep role-specific knowledge loaded instead of one mega-prompt.
- File chaos: all project writes go through `FileManager`, so the tree stays consistent.
- Opacity: live logs, kanban, agent status, and optional Phoenix tracing show what agents are doing.

## How it should feel

1. Open the app → pick or create a project.
2. Optionally tweak the LLM (Ollama local, or OpenAI if configured).
3. Hit start. Discovery looks at the project vs the brief, reports gaps, creates tasks.
4. Specialists claim matching work, write files, then hit human review.
5. User approves, requests rework, or completes work offline.
6. Loop continues until the user stops the system.

The UI must stay responsive while agents run (workflow lives on a background `QThread` + asyncio loop).

## User participation modes (product intent)

Documented in `docs/AGENT_WORKFLOW.md`; not all are fully wired yet:

| Mode | Intent |
|------|--------|
| Observer | Watch logs, kanban, files |
| Team member | Create/claim tasks |
| Team lead | Assign tasks to agents |
| Creative director | Review work, change vision |

Runtime switching between **automatic task pull** and **manual assignment** is a product goal. Current default path is event-driven auto-dispatch on `TASK_CREATED`.

## UX surfaces that exist

- `ProjectSelectionWindow` — create / open
- `MainWindow` tabs: agents, kanban, files, logs, LLM config, project details
- `HumanReviewDialog` — approve / reject with comment
- Status and log panels for agent thinking and tool actions
