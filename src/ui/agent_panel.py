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
from src.agents.llm import BaseLLMProvider, LLMConfig, OllamaProvider
from src.agents.orchestrator import AgentOrchestrator


class AgentCard(QWidget):
    """Widget representing a single agent.

    The agent card shows the agent's name, role, status,
    and optionally the task the agent is currently working on.
    """

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
        self.status_label = QLabel(self.status.value.upper())
        self._update_status_style()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addLayout(status_layout)

        # Task display (hidden by default)
        self.task_group = QGroupBox("Current Task")
        self.task_group.setVisible(False)
        task_layout = QVBoxLayout()

        self.task_title_label = QLabel("No task")
        self.task_title_label.setWordWrap(True)
        self.task_title_label.setStyleSheet("font-weight: bold;")

        self.task_desc_label = QLabel("")
        self.task_desc_label.setWordWrap(True)
        self.task_desc_label.setStyleSheet("color: gray; font-size: 10px;")

        task_layout.addWidget(self.task_title_label)
        task_layout.addWidget(self.task_desc_label)
        self.task_group.setLayout(task_layout)

        layout.addWidget(self.task_group)

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
            AgentStatus.WORKING: "green",
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

    def set_current_task(self, task: Optional[dict]) -> None:
        """Update the current task display.

        Args:
            task: Task dict with 'title' and 'description' keys, or None.
        """
        if task:
            self.task_title_label.setText(task.get('title', 'No title'))
            self.task_desc_label.setText(task.get('description', ''))
            self.task_group.setVisible(True)
        else:
            self.task_group.setVisible(False)


class AgentPanel(QWidget):
    """Panel for managing all AI agents.

    This panel displays all registered agents and provides system-level
    controls for starting and stopping the autonomous agent system.

    Signals:
        system_start_requested: Emitted when the system should be started.
        system_stop_requested: Emitted when the system should be stopped.
    """

    system_start_requested = Signal()
    system_stop_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the agent panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self.logger = logging.getLogger(f"{__name__}.AgentPanel")
        self.agent_cards: dict[str, AgentCard] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>AI Agents</h2>")
        layout.addWidget(title)

        # System control buttons
        control_layout = QHBoxLayout()

        self.start_system_button = QPushButton("Start System")
        self.start_system_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        self.start_system_button.clicked.connect(self._on_start_system)
        control_layout.addWidget(self.start_system_button)

        self.stop_system_button = QPushButton("Stop System")
        self.stop_system_button.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        self.stop_system_button.clicked.connect(self._on_stop_system)
        control_layout.addWidget(self.stop_system_button)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # System status indicator
        self.system_status_label = QLabel("System: STOPPED")
        self.system_status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        layout.addWidget(self.system_status_label)

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

    def update_agent_task(self, agent_name: str, task: Optional[dict]) -> None:
        """Update the current task for an agent.

        Args:
            agent_name: Name of the agent.
            task: Task dict with 'title' and 'description' keys, or None.
        """
        if agent_name not in self.agent_cards:
            self.logger.warning(f"Agent {agent_name} not found in panel")
            return

        self.agent_cards[agent_name].set_current_task(task)

    @Slot()
    def _on_start_system(self) -> None:
        """Handle start system button click."""
        self.logger.info("Start system requested")
        self.system_start_requested.emit()

    @Slot()
    def _on_stop_system(self) -> None:
        """Handle stop system button click."""
        self.logger.info("Stop system requested")
        self.system_stop_requested.emit()

    def set_system_status(self, running: bool) -> None:
        """Update the system status indicator and button states.

        Args:
            running: Whether the system is running.
        """
        if running:
            self.system_status_label.setText("System: RUNNING")
            self.system_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
            self.start_system_button.setEnabled(False)
            self.stop_system_button.setEnabled(True)
        else:
            self.system_status_label.setText("System: STOPPED")
            self.system_status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
            self.start_system_button.setEnabled(True)
            self.stop_system_button.setEnabled(False)

