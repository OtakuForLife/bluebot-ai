"""Agent control panel for managing AI agents."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.agents.base import AgentStatus
from src.llm import BaseLLMProvider, LLMConfig, OllamaProvider
from src.orchestrator.orchestrator import Orchestrator


class AgentCard(QWidget):
    """Widget representing a single agent with controls.
    
    Signals:
        start_requested: Emitted when start button is clicked.
        stop_requested: Emitted when stop button is clicked.
    """
    
    start_requested = Signal(str)  # agent_name
    stop_requested = Signal(str)   # agent_name
    
    def __init__(self, agent_name: str, agent_role: str, parent: Optional[QWidget] = None) -> None:
        """Initialize the agent card.
        
        Args:
            agent_name: Name of the agent.
            agent_role: Role of the agent.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.status = AgentStatus.IDLE
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Agent info
        info_layout = QHBoxLayout()
        
        self.name_label = QLabel(f"<b>{self.agent_name}</b>")
        self.role_label = QLabel(f"({self.agent_role})")
        self.role_label.setStyleSheet("color: gray;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.role_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Status indicator
        status_layout = QHBoxLayout()
        
        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel(self.status.value)
        self._update_status_style()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Style the card
        self.setStyleSheet("""
            AgentCard {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
    
    def _update_status_style(self) -> None:
        """Update the status label style based on current status."""
        colors = {
            AgentStatus.IDLE: "gray",
            AgentStatus.RUNNING: "green",
            AgentStatus.PAUSED: "orange",
            AgentStatus.STOPPED: "red",
            AgentStatus.ERROR: "darkred",
        }
        
        color = colors.get(self.status, "black")
        self.status_label.setText(self.status.value.upper())
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def set_status(self, status: AgentStatus) -> None:
        """Update the agent status.
        
        Args:
            status: New agent status.
        """
        self.status = status
        self._update_status_style()
        
        # Update button states
        if status == AgentStatus.RUNNING:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
    @Slot()
    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        self.start_requested.emit(self.agent_name)
    
    @Slot()
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.stop_requested.emit(self.agent_name)


class AgentPanel(QWidget):
    """Panel for managing all AI agents.

    This panel displays all registered agents and provides controls
    for starting, stopping, and monitoring them.

    Signals:
        agent_start_requested: Emitted when an agent start is requested.
        agent_stop_requested: Emitted when an agent stop is requested.
    """

    agent_start_requested = Signal(str)  # agent_name
    agent_stop_requested = Signal(str)   # agent_name

    def __init__(self, orchestrator: Orchestrator, parent: Optional[QWidget] = None) -> None:
        """Initialize the agent panel.
        
        Args:
            orchestrator: The orchestrator managing the agents.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.AgentPanel")
        self.orchestrator = orchestrator
        self.agent_cards: dict[str, AgentCard] = {}

        self._setup_ui()
        self._populate_agents()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>AI Agents</h2>")
        layout.addWidget(title)

        # Scroll area for agent cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for agent cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

    def _populate_agents(self) -> None:
        """Populate the panel with registered agents."""
        # Get all registered agents from orchestrator
        agents = self.orchestrator.list_agents()

        for agent_info in agents:
            agent_name = agent_info.get("name", "Unknown")
            agent_role = agent_info.get("role", "unknown")
            self.add_agent(agent_name, agent_role)

    def add_agent(self, agent_name: str, agent_role: str) -> None:
        """Add an agent card to the panel.

        Args:
            agent_name: Name of the agent.
            agent_role: Role of the agent.
        """
        if agent_name in self.agent_cards:
            self.logger.warning(f"Agent {agent_name} already exists in panel")
            return

        # Create agent card
        card = AgentCard(agent_name, agent_role)
        card.start_requested.connect(self._on_agent_start_requested)
        card.stop_requested.connect(self._on_agent_stop_requested)

        # Add to layout and tracking
        self.cards_layout.addWidget(card)
        self.agent_cards[agent_name] = card

        self.logger.info(f"Added agent card for {agent_name}")

    def remove_agent(self, agent_name: str) -> None:
        """Remove an agent card from the panel.

        Args:
            agent_name: Name of the agent to remove.
        """
        if agent_name not in self.agent_cards:
            self.logger.warning(f"Agent {agent_name} not found in panel")
            return

        card = self.agent_cards.pop(agent_name)
        self.cards_layout.removeWidget(card)
        card.deleteLater()

        self.logger.info(f"Removed agent card for {agent_name}")

    def update_agent_status(self, agent_name: str, status: AgentStatus) -> None:
        """Update the status of an agent.

        Args:
            agent_name: Name of the agent.
            status: New status.
        """
        if agent_name not in self.agent_cards:
            self.logger.warning(f"Agent {agent_name} not found in panel")
            return

        self.agent_cards[agent_name].set_status(status)
        self.logger.debug(f"Updated {agent_name} status to {status}")

    @Slot(str)
    def _on_agent_start_requested(self, agent_name: str) -> None:
        """Handle agent start request.

        Args:
            agent_name: Name of the agent to start.
        """
        self.logger.info(f"Start requested for agent: {agent_name}")
        # Emit signal to main window to actually start the agent
        self.agent_start_requested.emit(agent_name)
        # Update UI status
        self.update_agent_status(agent_name, AgentStatus.RUNNING)

    @Slot(str)
    def _on_agent_stop_requested(self, agent_name: str) -> None:
        """Handle agent stop request.

        Args:
            agent_name: Name of the agent to stop.
        """
        self.logger.info(f"Stop requested for agent: {agent_name}")
        # Emit signal to main window to actually stop the agent
        self.agent_stop_requested.emit(agent_name)
        # Update UI status
        self.update_agent_status(agent_name, AgentStatus.STOPPED)

