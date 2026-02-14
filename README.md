# Bluebot AI 5aa Multi-Agent Godot Game Development Tool

Bluebot AI is a **desktop application** that uses **multiple autonomous agents**
to help design, implement, and test video games built with the **Godot game
engine**. The goal is to automate and accelerate common game development
workflows while remaining **offline-first** and **100% open source**.

This repository currently contains an initial project skeleton; core
functionality will be added iteratively.

---

## 1. Features (Planned)

Based on the project requirements:

- Orchestrate multiple specialized agents (design, programming, testing, etc.).
- Generate and modify Godot-compatible game assets and code.
- Run automated tests within a Godot project and present the results.
- Provide a cross-platform desktop UI for controlling agents and viewing logs.
- Operate entirely offline using only open-source technologies.

---

## 2. Technologies

See [`TECHNOLOGIES.md`](./TECHNOLOGIES.md) for full details. In short, the
stack is:

- **Language:** Python 3.12
- **Desktop UI:** Qt for Python (**PySide6**)
- **Game engine:** Godot 4.x (MIT-licensed)
- **Testing:** Godot tests (e.g., GUT) + `pytest` for this tool
- **Packaging:** PyInstaller or equivalent for Windows/Linux executables

---

## 3. Project Structure

Current layout after initial project setup:

- `README.md` 4d6 &mdash; Project overview and setup instructions.
- `REQUIREMENTS.md` 4dd &mdash; Functional and non-functional requirements.
- `TECHNOLOGIES.md` 4da &mdash; Technology choices and rationale.
- `main.py` 680 &mdash; Convenience entrypoint to launch the desktop app.
- `bluebot_ai/` 4e6 &mdash; Main Python package for the application:
  - `__init__.py` &mdash; Package metadata.
  - `app.py` &mdash; Top-level application entrypoint and GUI bootstrap.
  - `agents/` &mdash; Placeholder package for agent implementations.
  - `orchestrator/` &mdash; Placeholder package for the agent orchestrator.
  - `godot_integration/` &mdash; Placeholder package for Godot integration helpers.
  - `ui/` &mdash; Placeholder package for UI components and windows.

As the project evolves, additional packages (e.g., configuration, logging,
plugins) can be added under `bluebot_ai/`.

---

## 4. Getting Started

### 4.1 Prerequisites

- **Python**: 3.12 or newer installed and available on your `PATH`.
- **Godot**: A compatible Godot 4.x build installed locally.
- **PySide6**: Required to run the Qt-based desktop UI.

To install PySide6 into your environment (example using `pip`):

```bash
pip install PySide6
```

> Note: This command is provided as documentation only; it is not executed by
> this project automatically.

### 4.2 Running the Skeleton Application

From the repository root:

```bash
python main.py
```

If `PySide6` is available, this will open a minimal window titled
**"Bluebot AI"**. The real multi-agent orchestration and Godot integration will
be wired into this entrypoint over time.

If PySide6 is **not** installed, the script will print a clear message
explaining that the `PySide6` dependency is missing.

---

## 5. Roadmap (High Level)

Planned high-level steps for future iterations include:

1. Implement a basic orchestrator service and internal message bus.
2. Add initial agent types (e.g., project setup agent, test agent).
3. Integrate with a local Godot installation via its CLI.
4. Add Godot-side automated testing support and result parsing.
5. Expand the Qt UI to monitor agents, show logs, and configure projects.

Contributions and feedback on the architecture and requirements are welcome.

