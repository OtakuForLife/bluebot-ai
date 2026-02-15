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

from src.orchestrator.agent_factory import AgentFactory
from src.orchestrator.orchestrator import Orchestrator
from src.ui.agent_panel import AgentPanel
from src.ui.async_helper import AsyncHelper
from src.ui.llm_config_panel import LLMConfigPanel
from src.ui.output_panel import OutputPanel
from src.ui.project_panel import ProjectPanel
from src.ui.task_panel import TaskPanel


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
    
    def __init__(self, orchestrator: Optional[Orchestrator] = None) -> None:
        """Initialize the main window.
        
        Args:
            orchestrator: Optional orchestrator instance. If None, creates a new one.
        """
        super().__init__()
        
        self.logger = logging.getLogger(f"{__name__}.MainWindow")
        self.orchestrator = orchestrator or Orchestrator()
        self.project_path: Optional[Path] = None

        # Create async helper for running orchestrator methods
        self.async_helper = AsyncHelper()
        self.async_helper.start()

        # Create agent factory
        self.agent_factory = AgentFactory(self.orchestrator)
        self.agents: dict[str, any] = {}

        self._setup_ui()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()
        self._connect_signals()

        # Initialize orchestrator and agents
        self._initialize_orchestrator()

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

        # Create actual panel widgets
        self.project_panel = ProjectPanel()
        self.agent_panel = AgentPanel(self.orchestrator)
        self.task_panel = TaskPanel(self.orchestrator)
        self.output_panel = OutputPanel()
        self.llm_config_panel = LLMConfigPanel()

        # Add tabs with actual panels (Projects first)
        self.tab_widget.addTab(self.project_panel, "Projects")
        self.tab_widget.addTab(self.agent_panel, "Agents")
        self.tab_widget.addTab(self.task_panel, "Tasks")
        self.tab_widget.addTab(self.output_panel, "Output")
        self.tab_widget.addTab(self.llm_config_panel, "LLM Settings")
    
    def _create_menus(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_project_action = QAction("&New Project...", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_project_action)
        
        open_project_action = QAction("&Open Project...", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
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
    
    def _create_toolbars(self) -> None:
        """Create toolbars."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        start_action = QAction("Start Orchestrator", self)
        start_action.triggered.connect(self._on_start_orchestrator)
        toolbar.addAction(start_action)
        
        stop_action = QAction("Stop Orchestrator", self)
        stop_action.triggered.connect(self._on_stop_orchestrator)
        toolbar.addAction(stop_action)
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Connect task panel to output panel
        self.task_panel.task_submitted.connect(self._on_task_submitted)

        # Connect LLM config panel
        self.llm_config_panel.provider_created.connect(self._on_provider_created)

        # Connect project panel
        self.project_panel.project_selected.connect(self._on_project_selected)

        # Connect project detail view (inside project panel)
        self.project_panel.detail_view.vision_creation_requested.connect(self._on_vision_creation_requested)
        self.project_panel.detail_view.vision_approval_requested.connect(self._on_vision_approval_requested)

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

    @Slot(str, str, dict)
    def _on_task_submitted(self, agent_name: str, task_type: str, payload: dict) -> None:
        """Handle task submission from task panel.

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
    
    @Slot()
    def _on_new_project(self) -> None:
        """Handle new project action."""
        self.logger.info("New project requested")
        # Switch to projects tab and trigger new project dialog
        self.tab_widget.setCurrentWidget(self.project_panel)
        self.project_panel._on_new_project()

    @Slot()
    def _on_open_project(self) -> None:
        """Handle open project action."""
        self.logger.info("Open project requested")
        # Switch to projects tab
        self.tab_widget.setCurrentWidget(self.project_panel)

    @Slot(dict)
    def _on_project_selected(self, project_data: dict) -> None:
        """Handle project selection.

        Args:
            project_data: Selected project data.
        """
        project_name = project_data.get("name", "Unknown")
        project_path_str = project_data.get("path")

        self.logger.info(f"Project selected: {project_name}")

        if project_path_str:
            self.set_project_path(Path(project_path_str))

        self.output_panel.add_log(
            f"Project selected: {project_name}",
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

            # Schedule a check for vision completion
            from PySide6.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self._check_vision_created(project_data))
        else:
            self.logger.error("Game Designer agent not found")
            self.output_panel.add_log(
                "Error: Game Designer agent not found",
                level="ERROR",
                agent="System"
            )

    def _check_vision_created(self, project_data: dict) -> None:
        """Check if vision document has been created.

        Args:
            project_data: Project data dictionary.
        """
        from pathlib import Path

        project_path = Path(project_data.get("location", ""))
        vision_path = project_path / "design" / "VISION.md"

        if vision_path.exists():
            self.logger.info("Vision document created successfully")
            self.project_panel.detail_view.update_vision_status(
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
    def _on_start_orchestrator(self) -> None:
        """Handle start orchestrator action."""
        self.logger.info("Starting orchestrator...")
        self.status_bar.showMessage("Orchestrator started")
        self.orchestrator_started.emit()

    @Slot()
    def _on_stop_orchestrator(self) -> None:
        """Handle stop orchestrator action."""
        self.logger.info("Stopping orchestrator...")
        self.status_bar.showMessage("Orchestrator stopped")
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

