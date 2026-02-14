# Technologies for the Multi-Agent Godot Game Development Tool

This document describes the concrete technologies and tooling that will be used to implement the requirements in `REQUIREMENTS.md`, while respecting the constraints of being **offline-first** and **100% open source**.

## 1. Core Language and Runtime

- **Primary language:** Python 3.12
  - Mature ecosystem for automation, tooling, and desktop integration.
  - Excellent support for concurrency (`asyncio`, `threading`, `multiprocessing`) to run multiple agents without blocking the UI.
  - Widely available on Windows and Linux.

## 2. Desktop Application and UI

- **GUI framework:** Qt for Python (**PySide6**) – LGPL-licensed, cross-platform, open source.
  - Used to build the main desktop application window.
  - Provides widgets for project selection, agent control, logs, and test results.
  - Supports responsive UIs that remain usable while agents run in the background.
- **UI architecture:** Model–View–ViewModel (MVVM) / Model–View–Presenter style separation.
  - View layer: Qt widgets and dialogs.
  - View-model/presenter: Python classes that expose state and actions to the UI.
  - Keeps UI independent from agent/orchestrator internals (supports NFR-9 Maintainability).

## 3. Agent System and Orchestrator

- **Agent implementation:** Python classes/modules, each encapsulating a specific role (design, programming, testing, etc.).
- **Orchestrator:** A central Python service responsible for:
  - Creating, configuring, and running agents.
  - Managing workflows and task assignments between agents.
  - Coordinating access to the shared Godot project.
- **Concurrency model:**
  - **`asyncio`** event loop for non-blocking agent tasks (file I/O, orchestration logic, message passing).
  - Optional worker threads or processes (`concurrent.futures`, `multiprocessing`) for CPU-intensive tasks.
- **Internal communication:**
  - In-memory message bus built on `asyncio.Queue` or equivalent.
  - Agents exchange structured messages/events rather than calling each other directly (FR-4, FR-5).

### 3.1 Optional AI / LLM Integration (Open Source Only)

Although not strictly required by the current requirements, the agent design will allow AI-assisted behaviors while staying fully open source and offline:

- **Local-only inference:** If language models are used, they will run via locally hosted, open-source runtimes (e.g., bindings to `llama.cpp` or similar), never via proprietary cloud APIs (NFR-1, NFR-3, SC-1).
- **Pluggable strategy layer:** Agents can be rule-based, heuristic, or model-based, as long as implementations remain open source and locally executable.

## 4. Godot Engine Integration

- **Game engine:** Godot Engine (version 4.x, open source under MIT license).
  - Installed and maintained by the user (SC-2).
- **Invocation method:**
  - The application will launch Godot via its **command-line interface** using Python’s `subprocess` module.
  - Example use cases:
    - Opening a Godot project for manual inspection.
    - Running automated tests or headless scenes.
    - Building/exporting the game where needed.
- **Supported scripting:**
  - Focus on **GDScript** for generated/modified scripts (FR-7).
- **Project file handling:**
  - The tool treats a Godot project as a file tree (`project.godot`, `.tscn`, `.tres`, `.gd`, assets, etc.).
  - Uses Python file I/O and parsing helpers to generate and modify these files (FR-6).
  - Validity is checked by invoking Godot in validation/test modes and parsing its output (FR-9).

## 5. Automated Testing and QA

- **Godot-side testing:**
  - Use Godot’s own test capabilities or an open-source testing framework such as **GUT (Godot Unit Test)**.
  - Tests are run **headless** where possible via the Godot CLI to satisfy FR-10 and FR-11.
  - The application parses test output (logs, exit codes) and presents structured results to the user (FR-12).
- **Tool-side testing:**
  - **`pytest`** for unit and integration tests of the orchestrator, agents, and UI logic (NFR-10).
  - Mocks and fakes for Godot invocations to allow fast, offline testing without always launching the engine.

## 6. Configuration, Logging, and Persistence

- **Configuration:**
  - Project and agent configuration stored in human-readable **TOML** files (e.g., `config.toml`).
  - Parsed using Python’s standard library (`tomllib` in 3.11+) or a compatible open-source parser.
  - Configuration kept external to the codebase (NFR-11).
- **Logging:**
  - Use Python’s built-in **`logging`** module.
  - Logs written both to the UI (live view) and to rotating log files on disk.
  - Logs can be exported as text or JSON files to support NFR-7 and NFR-8.
- **Persistence:**
  - Primary storage via project folders and configuration/log files.
  - Optional use of **SQLite** (via Python’s `sqlite3` module) for structured data such as run history or test reports; SQLite is open source and embedded.

## 7. Packaging and Distribution

- **Application bundling:**
  - Use **PyInstaller** (or an equivalent open-source packager) to create standalone executables for Windows and Linux (FR-16, SC-3).
  - Bundles Python runtime, application code, and required libraries.
- **Installation:**
  - Target user-space installation paths that do **not** require administrative privileges when possible (SC-3).
  - All dependencies are shipped with the application to support offline operation (SC-1).

## 8. Development Tooling and Process

- **Version control:** Git (with optional future integration into the app UI, per REQ 8. Future Enhancements).
- **Code quality:**
  - Formatters and linters such as **black** and **ruff** (or similar open-source tools) to keep the codebase consistent and maintainable.
  - Type hints and optional use of **mypy** for static type checking.
- **CI (future, optional):**
  - Open-source CI solutions (e.g., GitHub Actions, GitLab CI) can be used for automated testing and packaging as part of project evolution.

## 9. Open Source and Licensing Alignment

- All third-party components (Python, PySide6, Godot, testing libraries, packagers) are **open source** under OSI-approved licenses (NFR-1).
- Selected licenses (MIT, LGPL, Apache-2.0, etc.) are compatible with redistribution of this tool (NFR-2).
- No proprietary APIs, SDKs, game engines, or hosted model providers are required to use or build the application (NFR-3, SC-1, SC-2).

These technology choices directly support the functional and non-functional requirements in `REQUIREMENTS.md` while leaving room for future enhancements such as plugin systems, visual workflow editors, and version-control-aware workflows.
