"""Project selection window for choosing or creating a project."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.commands import CreateProjectCommand
from src.project.files import NewProjectData
from src.project.storage import load_projects_file, save_projects_file
from src.ui.bridge import QtCommandBridge
from src.ui.project_dialog import NewProjectDialog


class ProjectSelectionWindow(QDialog):
    """Window for selecting or creating a project before opening the main window.
    
    This dialog shows a list of existing projects and allows creating new ones.
    The user must select a project before proceeding to the main window.
    
    Signals:
        project_selected: Emitted when a project is selected and confirmed.
    """
    
    on_project_selected = Signal(object)
    create_project_requested = Signal(object)
    
    def __init__(self, qt_command_bridge: QtCommandBridge, parent: Optional[QWidget] = None) -> None:
        """Initialize the project selection window.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.ProjectSelectionWindow")
        self.projects: list[dict] = []
        self.projects_file = Path("projects.json")
        self.selected_project: Optional[dict] = None

        self.create_project_requested.connect(qt_command_bridge.dispatch)
        
        self._setup_ui()
        self._load_projects()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        self.setWindowTitle("Bluebot AI - Select Project")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Select a Project</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Choose an existing project or create a new one to get started.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Project list
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._on_project_double_clicked)
        self.project_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.project_list)
        
        # Buttons
        button_layout = QHBoxLayout()

        new_project_button = QPushButton("+ New Project")
        new_project_button.clicked.connect(self._on_new_project)
        button_layout.addWidget(new_project_button)

        button_layout.addStretch()

        self.delete_button = QPushButton("Delete Project")
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        self.delete_button.clicked.connect(self._on_delete_project)
        button_layout.addWidget(self.delete_button)

        self.open_button = QPushButton("Open Project")
        self.open_button.setEnabled(False)
        self.open_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        self.open_button.clicked.connect(self._on_open_project)
        button_layout.addWidget(self.open_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _load_projects(self) -> None:
        """Load projects from JSON file."""
        self.projects = load_projects_file(self.projects_file, self.logger)
        self._refresh_project_list()
    
    def _refresh_project_list(self) -> None:
        """Refresh the project list display."""
        self.project_list.clear()
        
        for project in self.projects:
            item = QListWidgetItem(project.get("name", "Unnamed Project"))
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.project_list.addItem(item)
    
    def _save_projects(self) -> None:
        """Save projects to JSON file."""
        save_projects_file(self.projects, self.projects_file, self.logger)

    @Slot()
    def _on_new_project(self) -> None:
        """Handle new project button click."""
        dialog = NewProjectDialog(self)
        project_data = dialog.get_project_data()

        if project_data:
            # Create project directory structure via command
            self.create_project_requested.emit(CreateProjectCommand(payload=project_data))

            # Add project to list and save
            # Convert to dict format expected by projects.json
            project_dict = {
                "name": project_data.get("name", "Unnamed Project"),
                "description": project_data.get("description", ""),
                "brief": project_data.get("brief", ""),
                "path": project_data.get("path", ""),
                "genres": project_data.get("genres", []),
                "elements": project_data.get("elements", []),
            }
            self.projects.append(project_dict)
            self._save_projects()
            self._refresh_project_list()

            # Select the newly created project
            self.selected_project = project_dict
            self.logger.info(f"Created new project: {project_data.get('name')}")

            self.accept()


    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle project selection change.

        Args:
            current: Currently selected item.
            previous: Previously selected item.
        """
        if current:
            self.selected_project = current.data(Qt.ItemDataRole.UserRole)
            self.open_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.selected_project = None
            self.open_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    @Slot(QListWidgetItem)
    def _on_project_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on a project item.

        Args:
            item: The clicked item.
        """
        self.selected_project = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    @Slot()
    def _on_open_project(self) -> None:
        """Handle open project button click."""
        if self.selected_project:
            self.accept()

    @Slot()
    def _on_delete_project(self) -> None:
        """Handle delete project button click."""
        if not self.selected_project:
            return

        project_name = self.selected_project.get("name", "Unnamed Project")

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete '{project_name}' from the project list?\n\n"
            "Note: This only removes the project from the list. The project directory and files will not be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Remove project from list
            self.projects.remove(self.selected_project)
            self._save_projects()
            self._refresh_project_list()

            # Clear selection
            self.selected_project = None
            self.open_button.setEnabled(False)
            self.delete_button.setEnabled(False)

            self.logger.info(f"Deleted project from list: {project_name}")

    def get_selected_project(self) -> Optional[dict]:
        """Get the selected project data.

        Returns:
            Selected project data dictionary, or None if no project selected.
        """
        return self.selected_project
