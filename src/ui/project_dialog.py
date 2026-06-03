"""Project creation dialog for creating new game projects."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.project.files import NewProjectData


class NewProjectDialog(QDialog):
    """Dialog for creating a new game project.
    
    Allows users to specify project name, description, location,
    genres, and game elements.
    
    Signals:
        project_created: Emitted when a project is created with project data.
    """
    
    project_created = Signal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the new project dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.NewProjectDialog")
        self.setWindowTitle("Create New Game Project")
        self.setMinimumWidth(600)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Create New Game Project</h2>")
        layout.addWidget(title)
        
        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Awesome Game")
        basic_layout.addRow("Project Name*:", self.name_input)
        
        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText("Short one-line summary of the game...")
        self.description_input.setMaximumHeight(60)
        basic_layout.addRow("Description:", self.description_input)

        self.brief_input = QPlainTextEdit()
        self.brief_input.setPlaceholderText(
            "Describe the game in detail — genre feel, core loop, art style, "
            "target audience, inspirations, anything you care about.\n\n"
            "Agents will use this as their creative brief."
        )
        self.brief_input.setMinimumHeight(120)
        basic_layout.addRow("Game Brief*:", self.brief_input)

        # Project location (parent directory)
        location_layout = QHBoxLayout()
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Select parent directory (e.g., C:/Users/User/Desktop)")
        location_layout.addWidget(self.location_input)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_location)
        location_layout.addWidget(browse_button)

        basic_layout.addRow("Parent Directory*:", location_layout)
        
        layout.addWidget(basic_group)
        
        # Game genres
        genre_group = QGroupBox("Game Genres (Select all that apply)")
        genre_layout = QVBoxLayout(genre_group)
        
        self.genre_checkboxes = {}
        genres = [
            "Action", "Adventure", "RPG", "Strategy", "Simulation",
            "Puzzle", "Platformer", "Racing", "Sports", "Horror",
            "Survival", "Sandbox", "Fighting", "Stealth", "Rhythm"
        ]
        
        # Create grid of checkboxes
        row_layout = None
        for i, genre in enumerate(genres):
            if i % 3 == 0:
                row_layout = QHBoxLayout()
                genre_layout.addLayout(row_layout)
            
            checkbox = QCheckBox(genre)
            self.genre_checkboxes[genre] = checkbox
            if(row_layout):
                row_layout.addWidget(checkbox)
        
        layout.addWidget(genre_group)
        
        # Game elements
        elements_group = QGroupBox("Game Elements (Select all that apply)")
        elements_layout = QVBoxLayout(elements_group)
        
        self.element_checkboxes = {}
        elements = [
            "Single Player", "Multiplayer", "Co-op", "PvP",
            "Story-driven", "Open World", "Linear Levels", "Procedural Generation",
            "Character Customization", "Skill Trees", "Inventory System", "Crafting",
            "Dialogue System", "Quest System", "Day/Night Cycle", "Weather System",
            "AI Enemies", "Boss Battles", "Achievements", "Leaderboards"
        ]
        
        # Create grid of checkboxes
        row_layout = None
        for i, element in enumerate(elements):
            if i % 3 == 0:
                row_layout = QHBoxLayout()
                elements_layout.addLayout(row_layout)
            
            checkbox = QCheckBox(element)
            self.element_checkboxes[element] = checkbox
            if(row_layout):
                row_layout.addWidget(checkbox)
        
        layout.addWidget(elements_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    @Slot()
    def _on_browse_location(self) -> None:
        """Handle browse location button click."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Parent Directory for Project",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            self.location_input.setText(directory)

    @Slot()
    def _on_accept(self) -> None:
        """Handle OK button click."""
        # Validate inputs
        name = self.name_input.text().strip()
        location = self.location_input.text().strip()
        brief = self.brief_input.toPlainText().strip()

        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Project name is required.")
            return

        if not location:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Parent directory is required.")
            return

        if not brief:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Game brief is required.")
            return

        # Collect selected genres
        selected_genres = [
            genre for genre, checkbox in self.genre_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Collect selected elements
        selected_elements = [
            element for element, checkbox in self.element_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Create project data
        project_data = {
            "name": name,
            "description": self.description_input.toPlainText().strip(),
            "brief": brief,
            "path": str(Path(location) / name),
            "genres": selected_genres,
            "elements": selected_elements,
        }

        self.logger.info(f"Creating project: {name}")
        self.project_created.emit(project_data)
        self.accept()

    def get_project_data(self) -> Optional[NewProjectData]:
        """Get the project data if dialog was accepted.

        Returns:
            Project data dictionary or None if cancelled.
        """
        if self.exec() == QDialog.DialogCode.Accepted:
            name = self.name_input.text().strip()
            location = self.location_input.text().strip()

            # Calculate full project path
            project_path = str(Path(location) / name)

            return NewProjectData(
                name=name,
                description=self.description_input.toPlainText().strip(),
                brief=self.brief_input.toPlainText().strip(),
                path=project_path,
                genres=[
                    genre for genre, checkbox in self.genre_checkboxes.items()
                    if checkbox.isChecked()
                ],
                elements=[
                    element for element, checkbox in self.element_checkboxes.items()
                    if checkbox.isChecked()
                ],
            )
        return None

