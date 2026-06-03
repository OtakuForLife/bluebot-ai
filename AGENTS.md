# AGENTS.md

## Project Overview

Bluebot AI is a **desktop application that uses multiple autonomous agents to assist with Godot game development**.

The application:

* runs locally
* uses **LangGraph-based multi-agent workflows**
* uses **local LLM inference via Ollama**
* communicates internally through an **event-driven architecture**
* provides a **Qt (PySide6) desktop UI**

Agents collaborate to design, implement, and manage game projects.

---
# Important Documents
- [docs/AGENT_WORKFLOW](AGENT_WORKFLOW)
- [docs/ARCHITECTURE](ARCHITECTURE)
- [docs/DECISIONS](DECISIONS)
- [docs/REQUIREMENTS](REQUIREMENTS)
# Running the Application

### Run the desktop app

```bash
uv run main.py
```

### Run tests

```bash
uv run pytest
```

### Run a single test

```bash
uv run pytest tests/test_orchestrator.py
```

### Verbose test output

```bash
uv run pytest -v -s
```

### Run tests with coverage

```bash
uv run pytest --cov=src
```

---

# Repository Structure

```
bluebot-ai/
├── main.py
├── src/
│   ├── app.py
│   ├── events.py
│   ├── commands/
│   ├── agents/
│   ├── project/
│   └── ui/
├── knowledge/
└── tests/
```

### Key directories

| Directory      | Purpose                           |
| -------------- | --------------------------------- |
| `src/agents/`  | Agent system and orchestration    |
| `src/project/` | Project state and file management |
| `src/ui/`      | PySide6 desktop interface         |
| `knowledge/`   | Agent-specific documentation      |
| `tests/`       | Pytest test suite                 |

---

# Core Architecture

The application follows **three primary architectural patterns**.

---

# 1. Event-Driven Communication

All backend components communicate through **events and commands**.

Relevant modules:

```
src/events.py
src/commands/
```

### Events

Events represent **state changes or notifications**.

Examples:

* `TASK_CREATED`
* `PROJECT_FILE_UPDATED`

Events allow components to react without direct coupling.

---

### Commands

Commands represent **explicit actions**.

Examples:

* `CreateProjectCommand`
* `CreateTaskCommand`

Commands are dispatched through the **CommandBus**.

---

### UI Integration

The Qt UI communicates with backend systems through bridges:

* `QtEventBridge`
* `QtCommandBridge`

**Rule:**
UI code must never call backend services directly.

Always use the bridge system.

---

# 2. Multi-Agent Workflow (LangGraph)

Agents are orchestrated using **LangGraph**.

Main implementation:

```
src/agents/graph.py
```

### Shared State

Agents share a central state object:

```
GameState
```

This includes:

* project files
* tasks
* logs
* ...
---

### Agent Workflow

See [docs/AGENT_WORKFLOW](AGENT_WORKFLOW)

---

### LLM Integration

Agents use **LangChain-compatible LLM interfaces**.

LLM providers:

```
src/agents/llm/
```

Current provider:

* `OllamaProvider`

All models run locally via:

```
http://localhost:11434
```

---

### Agent Tools

Agents interact with the project using structured tools:

```
create_file
update_file
delete_file
read_file
list_files
```

Tool implementations:

```
src/agents/tools/
```

---

# 3. Project Structure Management

All project files are managed through:

```
src/project/files.py
```

The **FileManager** is the single source of truth for project file operations.

---

### FileManager Responsibilities

* creating project structures
* reading and writing project files
* enforcing directory layout

---

### Directory Constants

Always use directory constants from `FileManager`.

Examples:

```
SCRIPTS_DIR
SCENES_DIR
ASSETS_DIR
DESIGN_DIR
```

Never hardcode paths.

---

### Project Initialization

New projects are created using:

```
create_project_structure()
```

This creates:

* directory layout
* `project.json`

---

# Major Components

## Agent System

Location:

```
src/agents/
```

Key modules:

| File           | Purpose                        |
| -------------- | ------------------------------ |
| `base.py`      | Agent base class and lifecycle |
| `graph.py`     | LangGraph orchestration        |
| `knowledge.py` | Knowledge base loader          |
| `llm/`         | LLM provider abstraction       |

---

### Agent Base Class

`Agent` provides:

* message queue
* lifecycle management (`start`, `stop`)
* role system (`AgentRole` enum)

---

### Knowledge System

Agents load documentation using:

```
KnowledgeBase
```

Documentation source:

```
knowledge/{agent_role}/
```

The knowledge system loads **markdown documentation relevant to each agent role**.

---

## Project Management

Location:

```
src/project/
```

Modules:

| File         | Purpose                |
| ------------ | ---------------------- |
| `manager.py` | Task and project state |
| `files.py`   | File operations        |

---

### ProjectManager

Responsible for:

* task creation
* task updates
* emitting task-related events

---

## UI Layer

Location:

```
src/ui/
```

Main components:

| File                          | Purpose                    |
| ----------------------------- | -------------------------- |
| `main_window.py`              | Main desktop interface     |
| `bridge.py`                   | Qt ↔ backend communication |
| `logging_handler.py`          | Log forwarding to UI       |
| `project_selection_window.py` | Project selection dialog   |

---

### Main Window Panels

The UI includes:

* agent panel
* task panel
* kanban board
* file explorer
* output/log panel

---

# Knowledge Base

Agent documentation is stored in:

```
knowledge/
```

Structure:

```
knowledge/
├── game_design/
├── programming/
├── art/
├── audio/
├── qa/
└── production/
```

Each directory contains **markdown documentation specific to that agent role**.

These documents are loaded dynamically by `KnowledgeBase`.

---

# Development Rules

### UI Architecture

Do not call backend systems directly from Qt components.

Always use:

```
QtEventBridge
QtCommandBridge
```

---

### File Operations

All project file access must go through:

```
FileManager
```

Never manipulate files directly.

---

### Directory Paths

Always use constants from `FileManager`.

Do not use raw string paths.

---

### Agent Knowledge

Agents must load documentation through:

```
KnowledgeBase
```

Do not access files in `knowledge/` manually.

---