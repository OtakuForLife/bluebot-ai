"""Project management panel for listing and managing game projects."""

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.ui.project_detail_view import ProjectDetailView
from src.ui.project_dialog import NewProjectDialog


class ProjectPanel(QWidget):
    """Panel for managing game projects.
    
    Displays a list of projects and allows creating new ones.
    Shows project details when a project is selected.
    
    Signals:
        project_selected: Emitted when a project is selected.
    """
    
    project_selected = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the project panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.ProjectPanel")
        self.projects: list[dict] = []
        self.projects_file = Path("projects.json")
        
        self._setup_ui()
        self._load_projects()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for list and detail view
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Project list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        
        # Header with title and new project button
        header_layout = QHBoxLayout()
        
        title = QLabel("<h2>Projects</h2>")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        new_project_button = QPushButton("+ New Project")
        new_project_button.clicked.connect(self._on_new_project)
        header_layout.addWidget(new_project_button)
        
        list_layout.addLayout(header_layout)
        
        # Project list
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        list_layout.addWidget(self.project_list)
        
        splitter.addWidget(list_widget)
        
        # Right side: Project detail view
        self.detail_view = ProjectDetailView()
        splitter.addWidget(self.detail_view)
        
        # Set splitter sizes (30% list, 70% detail)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
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
    
    def _save_projects(self) -> None:
        """Save projects to JSON file."""
        try:
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(self.projects)} projects")
            
        except Exception as e:
            self.logger.error(f"Failed to save projects: {e}")
    
    def _refresh_project_list(self) -> None:
        """Refresh the project list widget."""
        self.project_list.clear()
        
        for project in self.projects:
            item = QListWidgetItem(project["name"])
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.project_list.addItem(item)
    
    @Slot()
    def _on_new_project(self) -> None:
        """Handle new project button click."""
        dialog = NewProjectDialog(self)
        
        if dialog.exec() == NewProjectDialog.DialogCode.Accepted:
            project_data = dialog.get_project_data()
            
            if project_data:
                # Create project directory structure
                self._create_project_structure(project_data)
                
                # Add to projects list
                self.projects.append(project_data)
                self._save_projects()
                self._refresh_project_list()

                self.logger.info(f"Created new project: {project_data['name']}")

    def _create_project_structure(self, project_data: dict) -> None:
        """Create the project directory structure.

        Args:
            project_data: Project data dictionary.
        """
        try:
            project_path = Path(project_data["path"])
            project_path.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (project_path / "scripts").mkdir(exist_ok=True)
            (project_path / "scenes").mkdir(exist_ok=True)
            (project_path / "assets").mkdir(exist_ok=True)
            (project_path / "assets" / "sprites").mkdir(exist_ok=True)
            (project_path / "assets" / "models").mkdir(exist_ok=True)
            (project_path / "assets" / "audio").mkdir(exist_ok=True)
            (project_path / "design").mkdir(exist_ok=True)
            (project_path / "docs").mkdir(exist_ok=True)

            # Create project info file
            project_info = {
                "name": project_data["name"],
                "description": project_data["description"],
                "genres": project_data["genres"],
                "elements": project_data["elements"],
            }

            with open(project_path / "project.json", 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Created project structure at: {project_path}")

        except Exception as e:
            self.logger.error(f"Failed to create project structure: {e}")

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_project_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle project selection change.

        Args:
            current: Currently selected item.
            previous: Previously selected item.
        """
        if current:
            project_data = current.data(Qt.ItemDataRole.UserRole)
            self.logger.info(f"Selected project: {project_data['name']}")

            # Update detail view
            self.detail_view.set_project(project_data)

            # Emit signal
            self.project_selected.emit(project_data)
        else:
            self.detail_view.clear()

    def get_selected_project(self) -> Optional[dict]:
        """Get the currently selected project.

        Returns:
            Project data dictionary or None if no selection.
        """
        current_item = self.project_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

