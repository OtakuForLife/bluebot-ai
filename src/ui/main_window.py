"""Main window for Bluebot AI application."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMenuBar,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.agents.base import AgentStatus
from src.orchestrator.agent_factory import AgentFactory
from src.orchestrator.orchestrator import Orchestrator
from src.ui.agent_panel import AgentPanel
from src.ui.async_helper import AsyncHelper
from src.ui.file_explorer_panel import FileExplorerPanel
from src.ui.kanban_board import KanbanBoard
from src.ui.llm_config_panel import LLMConfigPanel
from src.ui.output_panel import OutputPanel


class MainWindow(QMainWindow):
    """Main application window for Bluebot AI.
    
    This window provides the main interface for managing AI agents,
    configuring LLM providers, and monitoring game development tasks.
    
    Signals:
        orchestrator_started: Emitted when the orchestrator starts.
        orchestrator_stopped: Emitted when the orchestrator stops.
    """
    
    orchestrator_started = Signal()
    orchestrator_stopped = Signal()
    
    def __init__(self, orchestrator: Optional[Orchestrator] = None, project_data: Optional[dict] = None) -> None:
        """Initialize the main window.

        Args:
            orchestrator: Optional orchestrator instance. If None, creates a new one.
            project_data: Project data dictionary for the project to work on.
        """
        super().__init__()

        self.logger = logging.getLogger(f"{__name__}.MainWindow")
        self.orchestrator = orchestrator or Orchestrator()
        self.project_data = project_data
        self.project_path: Optional[Path] = None

        # Create async helper for running orchestrator methods
        self.async_helper = AsyncHelper()
        self.async_helper.start()

        # Create agent factory
        self.agent_factory = AgentFactory(self.orchestrator)
        self.agents: dict[str, any] = {} # type: ignore

        self._setup_ui()
        self._create_menus()
        self._create_status_bar()
        self._connect_signals()

        # Initialize orchestrator and agents
        self._initialize_orchestrator()

        # Auto-apply default LLM configuration AFTER agents are created
        self.llm_config_panel.apply_default_config()

        # Set the project if provided
        if self.project_data:
            self._set_current_project(self.project_data)

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

        # Create actual panel widgets (no ProjectPanel - we have a single project)
        from src.ui.project_detail_view import ProjectDetailView
        self.project_detail_view = ProjectDetailView()
        self.file_explorer_panel = FileExplorerPanel()
        self.agent_panel = AgentPanel(self.orchestrator)
        self.kanban_board = KanbanBoard(self.orchestrator)
        self.output_panel = OutputPanel()
        self.llm_config_panel = LLMConfigPanel()

        # Add tabs (Project first, then File Explorer, Agents, Tasks, Output, LLM Settings)
        self.tab_widget.addTab(self.project_detail_view, "Project")
        self.tab_widget.addTab(self.file_explorer_panel, "File Explorer")
        self.tab_widget.addTab(self.agent_panel, "Agents")
        self.tab_widget.addTab(self.kanban_board, "Tasks")
        self.tab_widget.addTab(self.output_panel, "Output")
        self.tab_widget.addTab(self.llm_config_panel, "LLM Settings")
    
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
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Connect Kanban board to output panel
        self.kanban_board.task_submitted.connect(self._on_task_submitted)
        self.kanban_board.task_created.connect(self._on_task_created)
        self.kanban_board.task_state_changed.connect(self._on_task_state_changed)

        # Connect LLM config panel
        self.llm_config_panel.provider_created.connect(self._on_provider_created)

        # Connect project detail view
        self.project_detail_view.vision_creation_requested.connect(self._on_vision_creation_requested)
        self.project_detail_view.vision_approval_requested.connect(self._on_vision_approval_requested)

        # Connect agent panel
        self.agent_panel.agent_start_requested.connect(self._on_agent_start_requested)
        self.agent_panel.agent_stop_requested.connect(self._on_agent_stop_requested)

        # Connect output panel
        self.output_panel.clear_requested.connect(self._on_output_cleared)

    def _initialize_orchestrator(self) -> None:
        """Initialize the orchestrator and create all agents."""
        self.logger.info("Initializing orchestrator...")

        # Start orchestrator
        self.async_helper.run_async(self.orchestrator.start())

        # Create all agents
        self.agents = self.agent_factory.create_all_agents()

        self.logger.info(f"Initialized {len(self.agents)} agents")

        # Log to output panel
        self.output_panel.add_log(
            f"Orchestrator initialized with {len(self.agents)} agents",
            level="INFO",
            agent="System"
        )

    @Slot(dict)
    def _on_task_created(self, task_data: dict) -> None:
        """Handle task creation from Kanban board.

        Args:
            task_data: Task data dictionary.
        """
        self.logger.info(f"Task created: {task_data.get('title')}")
        self.output_panel.add_log(
            f"Task created: {task_data.get('title')} assigned to {task_data.get('agent')}",
            level="INFO",
            agent="System"
        )

        # Create task in task manager
        self.async_helper.run_coroutine(
            self.orchestrator.task_manager.create_task(
                title=task_data.get("title", ""),
                description=task_data.get("description", ""),
                agent=task_data.get("agent", ""),
                task_type=task_data.get("task_type", ""),
                requires_review=task_data.get("requires_review", True),
                created_by=None,  # User-created task
                metadata={}
            )
        )

    @Slot(str, str)
    def _on_task_state_changed(self, task_id: str, new_state: str) -> None:
        """Handle task state change.

        Args:
            task_id: Task ID.
            new_state: New state.
        """
        self.logger.info(f"Task {task_id} moved to {new_state}")
        self.output_panel.add_log(
            f"Task state changed to: {new_state}",
            level="INFO",
            agent="System"
        )

        # Update task state in task manager
        self.async_helper.run_coroutine(
            self.orchestrator.task_manager.update_task_state(task_id, new_state)
        )

    @Slot(str, str, dict)
    def _on_task_submitted(self, agent_name: str, task_type: str, payload: dict) -> None:
        """Handle task submission from Kanban board.

        Args:
            agent_name: Name of the target agent.
            task_type: Type of task.
            payload: Task parameters.
        """
        self.logger.info(f"Task submitted: {task_type} to {agent_name}")
        self.output_panel.add_log(
            f"Task submitted: {task_type} with payload: {payload}",
            level="INFO",
            agent=agent_name
        )

        # Send task to agent via orchestrator
        agent = self.agent_factory.get_agent_by_name(agent_name)
        if agent:
            task_data = {
                "task_type": task_type,
                **payload
            }
            self.async_helper.run_async(
                self.orchestrator.send_task_to_agent(agent.id, task_data)
            )
            self.logger.info(f"Task sent to agent {agent_name}")
        else:
            self.logger.error(f"Agent {agent_name} not found")
            self.output_panel.add_log(
                f"Error: Agent {agent_name} not found",
                level="ERROR",
                agent="System"
            )

    @Slot(object)
    def _on_provider_created(self, provider) -> None:
        """Handle LLM provider creation.

        Args:
            provider: The created LLM provider.
        """
        self.logger.info(f"LLM provider created: {provider}")
        self.output_panel.add_log(
            f"LLM provider configured: {provider.get_model_info()}",
            level="INFO",
            agent="System"
        )

        # Distribute provider to all agents
        self.agent_factory.update_llm_provider(provider)
        self.output_panel.add_log(
            f"LLM provider distributed to all agents",
            level="INFO",
            agent="System"
        )

    @Slot()
    def _on_output_cleared(self) -> None:
        """Handle output panel clear request."""
        self.logger.info("Output cleared by user")
    
    def _set_current_project(self, project_data: dict) -> None:
        """Set the current project and update UI.

        Args:
            project_data: Selected project data.
        """
        project_name = project_data.get("name", "Unknown")
        project_path_str = project_data.get("path")

        self.logger.info(f"Project set: {project_name}")

        # Update window title with project name
        self.setWindowTitle(f"Bluebot AI - {project_name}")

        # Set project in detail view
        self.project_detail_view.set_project(project_data)

        if project_path_str:
            project_path = Path(project_path_str)
            self.set_project_path(project_path)

            # Set project path in file explorer
            self.file_explorer_panel.set_project_path(project_path)

        self.output_panel.add_log(
            f"Project loaded: {project_name}",
            level="INFO",
            agent="System"
        )

    @Slot(dict)
    def _on_vision_creation_requested(self, project_data: dict) -> None:
        """Handle vision creation request.

        Args:
            project_data: Project data dictionary.
        """
        project_name = project_data.get("name", "Unknown")
        self.logger.info(f"Vision creation requested for: {project_name}")

        # Get the Game Designer agent
        designer_agent = self.agent_factory.get_agent_by_name("Game Designer")

        if not designer_agent:
            self.logger.error("Game Designer agent not found")
            self.output_panel.add_log(
                "Error: Game Designer agent not found",
                level="ERROR",
                agent="System"
            )
            return

        # Check if LLM provider is configured
        self.logger.info(f"Designer agent LLM provider: {designer_agent.llm_provider}")
        if not designer_agent.llm_provider:
            self.logger.error("No LLM provider configured")
            self.output_panel.add_log(
                "Error: No LLM provider configured. Please configure an LLM provider in the LLM Settings tab and click 'Apply Configuration'.",
                level="ERROR",
                agent="System"
            )
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "LLM Provider Required",
                "Vision creation requires an LLM provider.\n\n"
                "Please go to the 'LLM Settings' tab, configure your LLM provider, "
                "and click the 'Apply Configuration' button."
            )
            return

        # Set project path for the agent
        from pathlib import Path
        project_path = Path(project_data.get("path", ""))
        designer_agent.set_project_path(project_path)

        # Make sure the agent is started
        if designer_agent.status != AgentStatus.RUNNING:
            self.logger.info("Starting Game Designer agent...")
            self.async_helper.run_async(self.orchestrator.start_agent(designer_agent.id))
            # Give it a moment to start
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._send_vision_creation_task(project_data))
        else:
            self._send_vision_creation_task(project_data)

    def _send_vision_creation_task(self, project_data: dict) -> None:
        """Send the vision creation task to the Game Designer agent.

        Args:
            project_data: Project data dictionary.
        """
        project_name = project_data.get("name", "Unknown")
        designer_agent = self.agent_factory.get_agent_by_name("Game Designer")

        if designer_agent:
            # Prepare task payload
            task_payload = {
                "task_type": "create_vision",
                "project_name": project_name,
                "description": project_data.get("description", ""),
                "genres": project_data.get("genres", []),
                "elements": project_data.get("elements", []),
            }

            # Send task to Game Designer
            self.async_helper.run_async(
                self.orchestrator.send_task_to_agent(designer_agent.id, task_payload)
            )

            self.output_panel.add_log(
                f"Creating vision document for: {project_name}",
                level="INFO",
                agent="Game Designer"
            )
            self.output_panel.add_log(
                f"Note: First request may take longer as the model '{designer_agent.llm_provider.config.model}' loads into memory...",
                level="INFO",
                agent="Game Designer"
            )

            # Schedule a check for vision completion
            from PySide6.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self._check_vision_created(project_data))

    def _check_vision_created(self, project_data: dict) -> None:
        """Check if vision document has been created.

        Args:
            project_data: Project data dictionary.
        """
        from pathlib import Path

        project_path = Path(project_data.get("path", ""))
        vision_path = project_path / "design" / "VISION.md"

        if vision_path.exists():
            self.logger.info("Vision document created successfully")
            self.project_detail_view.update_vision_status(
                "✓ Vision created - Ready for review",
                vision_created=True
            )
            self.output_panel.add_log(
                "Vision document created successfully",
                level="INFO",
                agent="Game Designer"
            )
        else:
            # Check again in 5 seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self._check_vision_created(project_data))

    @Slot(dict)
    def _on_vision_approval_requested(self, vision_data: dict) -> None:
        """Handle vision approval.

        Args:
            vision_data: Vision data including content and project info.
        """
        project_name = vision_data.get("project_name", "Unknown")
        vision_content = vision_data.get("vision_content", "")

        self.logger.info(f"Vision approved for: {project_name}")

        # Broadcast VISION_APPROVED message to all agents
        from src.agents.base import Message, MessageType
        from uuid import UUID

        approval_message = Message(
            id=UUID(int=0),  # UI uses special ID
            type=MessageType.VISION_APPROVED,
            sender_id=UUID(int=0),
            recipient_id=None,  # Broadcast to all agents
            payload={
                "project_name": project_name,
                "vision_content": vision_content,
                "project_path": vision_data.get("project_path", ""),
            }
        )

        # Publish to message bus (will reach all agents)
        self.async_helper.run_async(
            self.orchestrator.message_bus.publish(approval_message)
        )

        self.output_panel.add_log(
            f"Vision approved for {project_name} - Starting autonomous development",
            level="INFO",
            agent="System"
        )

        self.output_panel.add_log(
            "Producer agent is now coordinating autonomous development",
            level="INFO",
            agent="Game Producer"
        )

    @Slot(str)
    def _on_agent_start_requested(self, agent_name: str) -> None:
        """Handle agent start request from agent panel.

        Args:
            agent_name: Name of the agent to start.
        """
        self.logger.info(f"Start requested for agent: {agent_name}")

        agent = self.agent_factory.get_agent_by_name(agent_name)
        if agent:
            self.async_helper.run_async(self.orchestrator.start_agent(agent.id))
            self.output_panel.add_log(
                f"Starting agent: {agent_name}",
                level="INFO",
                agent="System"
            )
        else:
            self.logger.error(f"Agent {agent_name} not found")

    @Slot(str)
    def _on_agent_stop_requested(self, agent_name: str) -> None:
        """Handle agent stop request from agent panel.

        Args:
            agent_name: Name of the agent to stop.
        """
        self.logger.info(f"Stop requested for agent: {agent_name}")

        agent = self.agent_factory.get_agent_by_name(agent_name)
        if agent:
            self.async_helper.run_async(self.orchestrator.stop_agent(agent.id))
            self.output_panel.add_log(
                f"Stopping agent: {agent_name}",
                level="INFO",
                agent="System"
            )
        else:
            self.logger.error(f"Agent {agent_name} not found")

    @Slot()
    def _on_start_all_agents(self) -> None:
        """Handle start all agents action."""
        self.logger.info("Start all agents requested")
        self.status_bar.showMessage("Starting all agents...")

        # Start all agents
        for agent_name, agent in self.agents.items():
            self.async_helper.run_async(self.orchestrator.start_agent(agent.id))

        self.output_panel.add_log(
            f"Starting all {len(self.agents)} agents",
            level="INFO",
            agent="System"
        )

        self.orchestrator_started.emit()

    @Slot()
    def _on_stop_all_agents(self) -> None:
        """Handle stop all agents action."""
        self.logger.info("Stop all agents requested")
        self.status_bar.showMessage("Stopping all agents...")

        # Stop all agents
        for agent_name, agent in self.agents.items():
            self.async_helper.run_async(self.orchestrator.stop_agent(agent.id))

        self.output_panel.add_log(
            f"Stopping all {len(self.agents)} agents",
            level="INFO",
            agent="System"
        )

        self.orchestrator_stopped.emit()



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

    def set_project_path(self, path: Path) -> None:
        """Set the current project path.

        Args:
            path: Path to the Godot project.
        """
        self.project_path = path
        self.logger.info(f"Project path set to: {path}")
        self.status_bar.showMessage(f"Project: {path.name}")

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        self.logger.info("Main window closing")
        # Clean up orchestrator if needed
        event.accept()

