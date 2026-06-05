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
uv run pytest tests/test_app.py
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