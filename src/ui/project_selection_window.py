"""Project selection window for choosing or creating a project."""

import json
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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.project_dialog import NewProjectDialog
from src.utils.project_structure import create_project_structure


class ProjectSelectionWindow(QDialog):
    """Window for selecting or creating a project before opening the main window.
    
    This dialog shows a list of existing projects and allows creating new ones.
    The user must select a project before proceeding to the main window.
    
    Signals:
        project_selected: Emitted when a project is selected and confirmed.
    """
    
    project_selected = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the project selection window.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.ProjectSelectionWindow")
        self.projects: list[dict] = []
        self.projects_file = Path("projects.json")
        self.selected_project: Optional[dict] = None
        
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
        if self.projects_file.exists():
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    self.projects = json.load(f)
                
                self.logger.info(f"Loaded {len(self.projects)} projects")
                self._refresh_project_list()
                
            except Exception as e:
                self.logger.error(f"Failed to load projects: {e}")
                self.projects = []
        else:
            self.logger.info("No projects file found, starting with empty list")
            self.projects = []
    
    def _refresh_project_list(self) -> None:
        """Refresh the project list display."""
        self.project_list.clear()
        
        for project in self.projects:
            item = QListWidgetItem(project.get("name", "Unnamed Project"))
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.project_list.addItem(item)
    
    def _save_projects(self) -> None:
        """Save projects to JSON file."""
        try:
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved {len(self.projects)} projects")

        except Exception as e:
            self.logger.error(f"Failed to save projects: {e}")

    @Slot()
    def _on_new_project(self) -> None:
        """Handle new project button click."""
        dialog = NewProjectDialog(self)
        project_data = dialog.get_project_data()

        if project_data:
            # Create project directory structure
            self._create_project_structure(project_data)

            # Add to projects list
            self.projects.append(project_data)
            self._save_projects()
            self._refresh_project_list()

            # Select the newly created project
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == project_data:
                    self.project_list.setCurrentItem(item)
                    break

            self.logger.info(f"Created new project: {project_data['name']}")

    def _create_project_structure(self, project_data: dict) -> None:
        """Create the project directory structure.

        Args:
            project_data: Project data dictionary.
        """
        # Use centralized utility for project structure creation
        success = create_project_structure(project_data)

        if success:
            self.logger.info(f"Created project structure for: {project_data['name']}")
        else:
            self.logger.error(f"Failed to create project structure for: {project_data['name']}")

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
        else:
            self.selected_project = None
            self.open_button.setEnabled(False)

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

    def get_selected_project(self) -> Optional[dict]:
        """Get the selected project data.

        Returns:
            Selected project data dictionary, or None if no project selected.
        """
        return self.selected_project

