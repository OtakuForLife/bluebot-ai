"""Main window for Bluebot AI application."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.agents.orchestrator import AgentOrchestrator
from src.ui.agent_panel import AgentPanel
from src.ui.file_explorer_panel import FileExplorerPanel
from src.ui.human_review_dialog import HumanReviewDialog
from src.ui.kanban_board import KanbanBoard
from src.ui.llm_config_panel import LLMConfigPanel
from src.ui.logging_handler import QtLogHandler
from src.ui.output_panel import OutputPanel
from src.ui.bridge import QtEventBridge, QtCommandBridge
from src.ui.project_detail_view import ProjectDetailView


class WorkflowThread(QThread):
    """Runs the agent workflow in a background asyncio event loop.

    Keeps the Qt main thread free so dialogs and signals continue to work
    while the event-driven agent system is executing.
    """

    workflow_done = Signal()   # fires only on clean stop
    error = Signal(str)        # fires only on unexpected exception

    def __init__(
        self,
        orchestrator,
        initial_state: dict,
        thread_id: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.initial_state = initial_state
        self.thread_id = thread_id

    def run(self) -> None:
        """Entry point for the QThread — starts the event-driven workflow."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self.orchestrator.start_event_driven(
                    self.initial_state, self.thread_id
                )
            )
            self.workflow_done.emit()
        except asyncio.CancelledError:
            # Cancelled by signal_stop() — clean exit, no error signal
            self.workflow_done.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            loop.close()

class MainWindow(QMainWindow):
    """Main application window for Bluebot AI.
    
    This window provides the main interface for managing AI agents,
    configuring LLM providers, and monitoring game development tasks.
    """
    
    
    def __init__(
        self,
        qt_event_bridge: QtEventBridge,
        qt_command_bridge: QtCommandBridge,
        qt_log_handler: QtLogHandler,
        agent_orchestrator: Optional[AgentOrchestrator] = None,
        selected_project: Optional[dict] = None,
    ) -> None:
        """Initialize the main window.

        Args:
            qt_event_bridge: Qt event bridge for backend events.
            qt_command_bridge: Qt command bridge for backend commands.
            qt_log_handler: Qt log handler for logging.
            agent_orchestrator: Optional agent orchestrator instance.
            selected_project: Selected project data dictionary.
        """
        super().__init__()

        self.logger = logging.getLogger(f"{__name__}.MainWindow")

        self.qt_event_bridge = qt_event_bridge
        self.qt_command_bridge = qt_command_bridge
        self.qt_log_handler = qt_log_handler
        self.agent_orchestrator = agent_orchestrator
        self.selected_project = selected_project

        self._setup_ui()
        self._create_menus()
        self._create_status_bar()

        # Auto-apply default LLM configuration
        self.llm_config_panel.apply_default_config()

        self.logger.info("Main window initialized")
    
    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        self.setWindowTitle("Bluebot AI - Multi-Agent Game Development")
        self.setMinimumSize(1200, 800)

        # Create central widget with tab layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.project_detail_view = ProjectDetailView()
        self.file_explorer_panel = FileExplorerPanel(self.qt_event_bridge)
        self.agent_panel = AgentPanel()

        # Set project data on detail view if available
        if self.selected_project:
            self.project_detail_view.set_project(self.selected_project)
            project_path = self.selected_project.get('path')
            if project_path:
                self.file_explorer_panel.set_project_path(Path(project_path))
        self.kanban_board = KanbanBoard()
        if self.selected_project:
            project_path = self.selected_project.get('path')
            if project_path:
                self.kanban_board.set_project_path(Path(project_path))
        self.output_panel = OutputPanel()
        self.llm_config_panel = LLMConfigPanel()

        # Add tabs (Project first, then File Explorer, Agents, Tasks, Output, LLM Settings)
        self.tab_widget.addTab(self.project_detail_view, "Project")
        self.tab_widget.addTab(self.file_explorer_panel, "File Explorer")
        self.tab_widget.addTab(self.agent_panel, "Agents")
        self.tab_widget.addTab(self.kanban_board, "Tasks")
        self.tab_widget.addTab(self.output_panel, "History")
        self.tab_widget.addTab(self.llm_config_panel, "LLM Settings")

        # Add agents to the panel if orchestrator has registered agents
        if self.agent_orchestrator:
            from src.agents.base import AgentRole
            agents = self.agent_orchestrator.get_agents()
            for agent in agents:
                self.agent_panel.add_agent(agent.name, agent.role.value)
            self.logger.info(f"Added {len(agents)} agents to the panel")

        # Connect agent panel signals to orchestrator
        self.agent_panel.system_start_requested.connect(self._on_start_system)
        self.agent_panel.system_stop_requested.connect(self._on_stop_system)

        # Propagate LLM provider changes to all agents
        if self.agent_orchestrator:
            self.llm_config_panel.provider_created.connect(
                self.agent_orchestrator.update_provider
            )

        # Connect Qt event bridge signals to panel updates
        self.qt_event_bridge.agent_status_changed.connect(self._on_agent_status_changed)
        self.qt_event_bridge.agent_current_task_changed.connect(self._on_agent_current_task_changed)
        self.qt_event_bridge.agent_thinking.connect(self._on_agent_thinking)
        self.qt_event_bridge.agent_action.connect(self._on_agent_action)
        self.qt_event_bridge.agentic_system_started.connect(self._on_system_started)
        self.qt_event_bridge.agentic_system_stopped.connect(self._on_system_stopped)

        # Human review: store payload when workflow pauses; dialog opens on card click
        self.qt_event_bridge.human_input_requested.connect(self._on_human_input_requested)
        self.kanban_board.task_review_requested.connect(self._on_task_review_requested)

        # Show agent-created tasks on the kanban board and track their state
        self.qt_event_bridge.task_created.connect(self._on_task_created)
        self.qt_event_bridge.task_assigned.connect(self._on_task_assigned)
        self.qt_event_bridge.task_updated.connect(self._on_task_updated)

        # Route all Python log records to the History panel
        self.qt_log_handler.log_message.connect(self.output_panel.add_log)
    
    def _create_menus(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Agents menu
        agents_menu = menubar.addMenu("&Agents")
        
        start_all_action = QAction("&Start All Agents", self)
        start_all_action.triggered.connect(self._on_start_all_agents)
        agents_menu.addAction(start_all_action)
        
        stop_all_action = QAction("S&top All Agents", self)
        stop_all_action.triggered.connect(self._on_stop_all_agents)
        agents_menu.addAction(stop_all_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    @Slot(object)
    def _on_agent_status_changed(self, event: dict) -> None:
        """Handle agent status changed event.

        Args:
            event: Event dict with agent_id, agent_name, agent_role, old_status, new_status.
        """
        payload = event.get("payload", {})
        agent_name = payload.get("agent_name")
        new_status = payload.get("new_status")
        if agent_name and new_status:
            from src.agents.base import AgentStatus
            status = AgentStatus(new_status)
            self.agent_panel.update_agent_status(agent_name, status)

    @Slot(object)
    def _on_agent_current_task_changed(self, event: dict) -> None:
        """Handle agent current task changed event.

        Args:
            event: Event dict with agent_id, agent_name, task.
        """
        payload = event.get("payload", {})
        agent_name = payload.get("agent_name")
        task = payload.get("task")
        if agent_name:
            self.agent_panel.update_agent_task(agent_name, task)

    @Slot(object)
    def _on_agent_thinking(self, event: dict) -> None:
        """Handle agent thinking event.

        Args:
            event: Event dict with agent_id, agent_name, thought.
        """
        payload = event.get("payload", {})
        agent_name = payload.get("agent_name")
        thought = payload.get("thought")
        if agent_name and thought:
            self.output_panel.add_log(f"[{agent_name}] Thinking: {thought}", "INFO", agent_name)

    @Slot(object)
    def _on_agent_action(self, event: dict) -> None:
        """Handle agent action event.

        Args:
            event: Event dict with agent_id, agent_name, action, results.
        """
        payload = event.get("payload", {})
        agent_name = payload.get("agent_name")
        action = payload.get("action")
        results = payload.get("results", [])
        if agent_name and action:
            log_message = f"[{agent_name}] Action: {action}"
            if results:
                log_message += f" | Results: {results}"
            self.output_panel.add_log(log_message, "INFO", agent_name)

    # ------------------------------------------------------------------
    # Project JSON helpers (brief + thread_id persistence)
    # ------------------------------------------------------------------

    def _read_project_json(self) -> dict:
        """Read project.json from the selected project's directory.

        Returns an empty dict if the file is missing or unreadable.
        """
        project_path = Path(self.selected_project.get("path", "")) if self.selected_project else None
        if not project_path:
            return {}
        meta_file = project_path / "project.json"
        if not meta_file.exists():
            return {}
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self.logger.warning(f"Could not read project.json: {exc}")
            return {}

    def _write_project_json(self, data: dict) -> None:
        """Write *data* back to project.json in the selected project's directory."""
        project_path = Path(self.selected_project.get("path", "")) if self.selected_project else None
        if not project_path:
            return
        meta_file = project_path / "project.json"
        try:
            meta_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"Failed to write project.json: {exc}")

    # ------------------------------------------------------------------
    # Workflow start / stop
    # ------------------------------------------------------------------

    @Slot()
    def _on_start_system(self) -> None:
        """Start the agent system and launch the workflow in a background thread."""
        if not self.agent_orchestrator:
            return

        if not self.selected_project:
            self.logger.warning("No project selected — workflow not started")
            return

        # Ensure the project has a stable thread_id (persisted across restarts).
        # The brief is always set at project creation time and comes from project.json.
        meta = self._read_project_json()
        if not meta.get("thread_id"):
            meta["thread_id"] = f"workflow-{uuid4().hex[:8]}"
            self._write_project_json(meta)
        self.selected_project["thread_id"] = meta["thread_id"]

        # start_system() is called inside start_event_driven() — no separate call needed
        initial_state = self._build_initial_workflow_state()
        thread_id = self.selected_project["thread_id"]

        self._workflow_thread = WorkflowThread(
            self.agent_orchestrator, initial_state, thread_id, parent=self
        )
        self._workflow_thread.workflow_done.connect(self._on_workflow_finished)
        self._workflow_thread.error.connect(self._on_workflow_error)
        self._workflow_thread.start()
        self.logger.info(f"Workflow thread started (thread_id={thread_id})")

    def _build_initial_workflow_state(self) -> dict:
        """Build the initial AgentMessage state from the selected project.

        Uses the persisted game brief as the top-level task description so the
        Producer has real creative direction from the very first iteration.
        """
        project = self.selected_project or {}
        brief = project.get("brief") or (
            f"Project: {project.get('name', 'Unknown')}\n"
            f"{project.get('description', '')}"
        )
        return {
            "task_id": str(uuid4()),
            "task_type": "",
            "task_description": brief,
            "acceptance_criteria": [],
            "workspace_root": project.get("path", "."),
            "allowed_paths": [project.get("path", ".")],
            "last_agent": None,
            "messages": [],
            "tool_results": [],
            "modified_files": [],
            "created_files": [],
            "deleted_files": [],
            "outcome": None,
            "errors": [],
            "no_more_tasks": False,
            "human_review_approved": None,
            "human_review_comment": None,
            "current_task_id": None,
            "current_task_agent": None,
            "task_allocation_mode": "auto_pull",
        }

    @Slot()
    def _on_workflow_finished(self) -> None:
        """Called when the background workflow thread completes normally."""
        self.logger.info("Workflow finished")
        self.status_bar.showMessage("Workflow completed")
        self.agent_panel.set_system_status(False)

    @Slot(str)
    def _on_workflow_error(self, message: str) -> None:
        """Called when the background workflow thread raises an exception."""
        self.logger.error(f"Workflow error: {message}")
        self.status_bar.showMessage(f"Workflow error: {message}")
        self.agent_panel.set_system_status(False)
        QMessageBox.critical(self, "Workflow Error", message)

    @Slot(object)
    def _on_human_input_requested(self, event: dict) -> None:
        """Store the review payload and wait for the user to click the task card.

        Instead of popping up a dialog immediately, the payload is stored in the
        kanban board keyed by task_id. The task is already in the Review column
        (moved there by TASK_UPDATED). The user clicks the card to open the dialog.

        Args:
            event: Event dict whose payload mirrors the human_review_node
                   interrupt payload plus ``thread_id`` and ``current_task_id``.
        """
        payload = event.get("payload", {})
        task_id = payload.get("current_task_id")
        thread_id = payload.get("thread_id", "default")

        self.logger.info(
            f"Human review requested — thread_id={thread_id}, current_task_id={task_id!r}"
        )

        if not task_id:
            # current_task_id missing from interrupt payload — open dialog immediately
            self.logger.warning(
                "current_task_id not in interrupt payload; opening review dialog immediately. "
                "Check that assign_task was called and current_task_id is in LangGraph state."
            )
            self._show_review_dialog(payload, thread_id)
            return

        # Store payload keyed by task_id; dialog opens when the user clicks the card
        payload["_thread_id"] = thread_id
        self.kanban_board.set_pending_review(task_id, payload)
        self.logger.info(
            f"Review pending for task {task_id} — click the card in the Review column"
        )

    @Slot(str, dict)
    def _on_task_review_requested(self, task_id: str, payload: dict) -> None:
        """Open the review dialog when the user clicks a Review-column task card.

        Handles two cases:
        - Active workflow: payload contains ``_thread_id`` → resume the orchestrator.
        - No active workflow: task loaded from tasks.json → update task state directly.

        Args:
            task_id: ID of the task being reviewed.
            payload: Review payload (from human_review_node or built from task data).
        """
        thread_id = payload.get("_thread_id")  # None when no live workflow

        dialog = HumanReviewDialog(payload, parent=self)
        dialog.exec()
        approved, comment = dialog.get_result()

        if thread_id and self.agent_orchestrator:
            # Live workflow paused at human_review_node — resume it
            self.agent_orchestrator.submit_human_review(thread_id, approved, comment)
            self.logger.info(
                f"Human review submitted to workflow: approved={approved}, "
                f"thread_id={thread_id}"
            )
        else:
            # No active workflow — update the task card state directly
            new_state = "done" if approved else "todo"
            self.kanban_board.update_task_state(task_id, new_state)
            self.logger.info(
                f"Human review (offline): approved={approved} → task {task_id} "
                f"moved to '{new_state}'"
            )

        self.kanban_board.clear_pending_review(task_id)

    def _show_review_dialog(self, payload: dict, thread_id: str) -> None:
        """Open the HumanReviewDialog for the automatic fallback path.

        Called when HUMAN_INPUT_REQUESTED fires but current_task_id is absent
        from the interrupt payload, so there is no task card to click.

        Args:
            payload: Review payload to display in the dialog.
            thread_id: Workflow thread_id to resume after the decision.
        """
        if not self.agent_orchestrator:
            return

        dialog = HumanReviewDialog(payload, parent=self)
        dialog.exec()
        approved, comment = dialog.get_result()

        self.agent_orchestrator.submit_human_review(thread_id, approved, comment)
        self.logger.info(
            f"Human review submitted (fallback): approved={approved}, "
            f"thread_id={thread_id}"
        )

    @Slot()
    def _on_stop_system(self) -> None:
        """Handle stop system request.

        Sets the stop event so start_event_driven() exits cleanly.
        stop_system() is called automatically inside start_event_driven() after
        the stop event fires — do NOT call it here to avoid a double-stop.
        Falls back to a hard quit after 5 s if the thread doesn't exit cleanly.
        """
        if self.agent_orchestrator:
            self.agent_orchestrator.signal_stop()

        if hasattr(self, "_workflow_thread") and self._workflow_thread.isRunning():
            self._workflow_thread.quit()
            self._workflow_thread.wait(5000)

    @Slot(object)
    def _on_system_started(self, event: dict) -> None:
        """Handle system started event.

        Args:
            event: Event dict with agents list.
        """
        payload = event.get("payload", {})
        agents = payload.get("agents", [])
        self.status_bar.showMessage(f"System started with {len(agents)} agents")
        self.agent_panel.set_system_status(True)

    @Slot(object)
    def _on_system_stopped(self, event: dict) -> None:
        """Handle system stopped event.

        Args:
            event: Event dict (empty payload).
        """
        self.status_bar.showMessage("System stopped")
        self.agent_panel.set_system_status(False)

    @Slot(object)
    def _on_task_created(self, event: dict) -> None:
        """Add a Producer-created task to the kanban board."""
        payload = event.get("payload", {})
        self.kanban_board.add_task(payload)

    @Slot(object)
    def _on_task_assigned(self, event: dict) -> None:
        """Move a task to 'in_progress' when a specialist picks it up."""
        payload = event.get("payload", {})
        task_id = payload.get("task_id")
        if task_id:
            self.kanban_board.update_task_state(task_id, "in_progress")

    @Slot(object)
    def _on_task_updated(self, event: dict) -> None:
        """Update a task's state on the kanban board (e.g. to 'review' or 'done')."""
        payload = event.get("payload", {})
        task_id = payload.get("task_id")
        new_state = payload.get("new_state")
        if task_id and new_state:
            self.kanban_board.update_task_state(task_id, new_state)

    @Slot()
    def _on_start_all_agents(self) -> None:
        """Handle start all agents action."""
        self._on_start_system()

    @Slot()
    def _on_stop_all_agents(self) -> None:
        """Handle stop all agents action."""
        self._on_stop_system()



    @Slot()
    def _on_about(self) -> None:
        """Handle about action."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About Bluebot AI",
            "<h2>Bluebot AI</h2>"
            "<p>Multi-Agent Game Development System</p>"
            "<p>Version 0.1.0</p>"
            "<p>Built with PySide6 and Python</p>",
        )


    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        self.logger.info("Main window closing")
        # Clean up orchestrator if needed
        event.accept()

