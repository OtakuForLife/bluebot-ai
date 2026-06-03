# DECISIONS.md

This document records important **architectural and design decisions** for the Bluebot AI project.

Each decision includes:

* context
* chosen solution
* reasoning
* implications

This helps agents and contributors understand **why certain patterns must be preserved**.

---

# DECISION 001 — Event-Driven Backend Architecture

## Status

Accepted

## Context

The application consists of multiple independent subsystems:

* UI layer
* agent orchestration
* project management
* task system
* file management

Direct coupling between these components would make the system difficult to extend and maintain.

In particular, the Qt UI must not tightly depend on backend implementations.

## Decision

The backend uses an **event-driven architecture** with a **CommandBus + EventHandler pattern**.

Two message types exist:

### Commands

Commands represent **explicit requests to perform an action**.

Examples:

* `CreateProjectCommand`
* `CreateTaskCommand`

Commands are dispatched via the **CommandBus**.

### Events

Events represent **state changes or notifications**.

Examples:

* `TASK_CREATED`
* `PROJECT_FILE_UPDATED`

Events are broadcast to any interested subscribers.

## Consequences

Advantages:

* components remain loosely coupled
* new features can subscribe to existing events
* UI integration becomes simple
* system behavior becomes observable

Tradeoffs:

* debugging can be more complex
* tracing control flow requires following event chains

---

# DECISION 002 — Qt Bridge Pattern

## Status

Accepted

## Context

Qt UI components should remain **presentation-layer only**.

If UI widgets directly call backend logic:

* business logic leaks into UI
* testing becomes difficult
* architecture becomes tightly coupled

## Decision

All Qt communication with backend systems must go through bridge classes:

* `QtEventBridge`
* `QtCommandBridge`

These bridges translate:

* Qt signals → backend commands
* backend events → Qt signals

## Consequences

Advantages:

* clean separation of UI and application logic
* easier testing of backend
* UI components remain lightweight

Rules:

* UI must never directly call backend services
* bridges are the only allowed communication path

---

# DECISION 003 — LangGraph for Agent Orchestration

## Status

Accepted

## Context

Bluebot AI requires multiple specialized agents collaborating to build a game.

A simple sequential system would limit extensibility.

The architecture needs:

* composable workflows
* shared state
* future parallelism
* clear agent roles

## Decision

The system uses **LangGraph** for multi-agent orchestration.

The orchestrator builds a workflow graph.

Agents communicate through a shared state object.

## Consequences

Advantages:

* modular workflows
* extensible graph structure
* easy to insert additional agents
* clear reasoning flow

Future extensions could include:

* QA agent
* artist agent
* audio agent

---

# DECISION 004 — Local LLM Inference (Offline-First)

## Status

Accepted

## Context

Bluebot AI is intended to run as a **local desktop tool for developers**.

External APIs introduce problems:

* latency
* cost
* privacy concerns
* internet dependency

## Decision

By default, LLM inference is performed locally using **Ollama**, but other providers can be configured

Default endpoint:

```
http://localhost:11434
```

LLM access is abstracted via provider interfaces.

## Consequences

Advantages:

* fully offline operation
* predictable cost (none)
* faster iteration during development
* improved privacy

Tradeoffs:

* model capability depends on local hardware
* may require GPU for best performance

---

# DECISION 005 — FileManager as Single Source of Truth

## Status

Accepted

## Context

Agents interact heavily with project files.

Allowing unrestricted file access could lead to:

* inconsistent directory structures
* accidental overwrites
* broken project layouts

## Decision

All project file operations must go through:

```
FileManager
```

Located in:

```
src/project/files.py
```

FileManager provides controlled methods:

* `write_project_file`
* `read_project_file`
* `create_project_structure`

## Consequences

Advantages:

* consistent project structure
* centralized file logic
* easier validation
* safer agent operations

Rules:

* do not access project files directly
* always use FileManager

---

# DECISION 006 — Structured Agent Tools

## Status

Accepted

## Context

LLM agents require structured ways to interact with the system.

Allowing arbitrary Python execution would be unsafe and unpredictable.

## Decision

Agents interact with the project using **explicit tools**.

Example tools:

* `create_file`
* `update_file`
* `delete_file`
* `read_file`
* `list_files`

Tools are created by instanciating the `Tool` class in `agents/llm/tool.py`

## Consequences

Advantages:

* predictable agent behavior
* controlled filesystem access
* easier debugging
* better prompt reliability


---

# DECISION 007 — Knowledge Base for Agent Expertise

## Status

Accepted

## Context

Different agents require **specialized domain knowledge**:

* game design
* programming
* art
* QA
* production

Embedding all knowledge in prompts would be inefficient.

## Decision

Agents load role-specific knowledge from markdown documentation.

Location:

```
knowledge/{agent_role}/
```

Loaded through:

```
KnowledgeBase
```

## Consequences

Advantages:

* modular documentation
* scalable knowledge system
* agents receive only relevant information

This also allows contributors to expand agent expertise by simply adding markdown files.

---

# DECISION 008 — Directory Constants for Project Structure

## Status

Accepted

## Context

Hardcoding directory names across the codebase leads to fragile systems.

## Decision

Directory paths are defined as constants inside `FileManager`.

Examples:

```
SCRIPTS_DIR
SCENES_DIR
ASSETS_DIR
DESIGN_DIR
```

## Consequences

Advantages:

* consistent directory usage
* easier refactoring
* fewer path errors

Rule:

Never use raw path strings for project directories.

---

# Future Architectural Decisions

The following areas may require additional ADRs:

* agent memory system
* multi-agent concurrency
* persistent agent state
* plugin architecture
* Godot editor integration

When major architecture changes occur, add a new entry to this document.