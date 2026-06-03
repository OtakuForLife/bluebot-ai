"""Project detail view showing project information and file tree."""

import logging
from pathlib import Path
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


class ProjectDetailView(QWidget):
    """Widget showing detailed project information.

    Displays project metadata, genres, elements, and vision management.

    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the project detail view.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.ProjectDetailView")
        self.current_project: Optional[dict] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Placeholder when no project is selected
        self.placeholder = QLabel(
            "<h3>No Project Selected</h3>"
            "<p>Select a project from the list or create a new one.</p>"
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: gray;")
        layout.addWidget(self.placeholder)
        
        # Project details container (hidden initially)
        self.details_container = QWidget()
        details_layout = QVBoxLayout(self.details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Project info section
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setMaximumHeight(250)
        
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Project name
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        info_layout.addWidget(self.name_label)
        
        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.description_label)
        
        # Genres
        genres_group = QGroupBox("Genres")
        genres_layout = QVBoxLayout(genres_group)
        self.genres_label = QLabel()
        self.genres_label.setWordWrap(True)
        genres_layout.addWidget(self.genres_label)
        info_layout.addWidget(genres_group)
        
        # Elements
        elements_group = QGroupBox("Game Elements")
        elements_layout = QVBoxLayout(elements_group)
        self.elements_label = QLabel()
        self.elements_label.setWordWrap(True)
        elements_layout.addWidget(self.elements_label)
        info_layout.addWidget(elements_group)
        
        info_scroll.setWidget(info_widget)
        details_layout.addWidget(info_scroll)


        layout.addWidget(self.details_container)

        # Initially hide details and show placeholder
        self.details_container.hide()

    def set_project(self, project_data: dict) -> None:
        """Set the current project and display its details.

        Args:
            project_data: Project data dictionary.
        """
        self.current_project = project_data

        # Update UI
        self.name_label.setText(project_data.get("name", "Unnamed Project"))

        description = project_data.get("description", "No description provided.")
        self.description_label.setText(description if description else "No description provided.")

        # Display genres
        genres = project_data.get("genres", [])
        if genres:
            self.genres_label.setText(", ".join(genres))
        else:
            self.genres_label.setText("No genres selected")

        # Display elements
        elements = project_data.get("elements", [])
        if elements:
            self.elements_label.setText(", ".join(elements))
        else:
            self.elements_label.setText("No game elements selected")

        # Check if vision document already exists
        project_path = project_data.get("path")

        if project_path and Path(project_path).exists():
            self.logger.info(f"Loaded project from: {project_path}")

            # Check if vision document already exists
            vision_path = Path(project_path) / "design" / "VISION.md"
            if vision_path.exists():
                self.logger.info(f"Found existing vision document at: {vision_path}")
                # Vision UI removed - vision is just another file now
        else:
            self.logger.warning(f"Project path not found: {project_path}")

        # Show details, hide placeholder
        self.placeholder.hide()
        self.details_container.show()

    def clear(self) -> None:
        """Clear the current project and show placeholder."""
        self.current_project = None

        # Clear labels
        self.name_label.setText("")
        self.description_label.setText("")
        self.genres_label.setText("")
        self.elements_label.setText("")

        # Show placeholder, hide details
        self.details_container.hide()
        self.placeholder.show()
