"""User interface components for the Bluebot AI desktop application.

High-level windows and widgets will be kept separate from the core
agent/orchestrator logic to maintain a modular architecture.
"""

from src.ui.agent_panel import AgentCard, AgentPanel
from src.ui.llm_config_panel import LLMConfigPanel
from src.ui.main_window import MainWindow
from src.ui.output_panel import OutputPanel
from src.ui.project_detail_view import ProjectDetailView
from src.ui.project_dialog import NewProjectDialog
from src.ui.project_panel import ProjectPanel
from src.ui.task_panel import TaskPanel

__all__ = [
    "AgentCard",
    "AgentPanel",
    "LLMConfigPanel",
    "MainWindow",
    "OutputPanel",
    "ProjectDetailView",
    "NewProjectDialog",
    "ProjectPanel",
    "TaskPanel",
]

