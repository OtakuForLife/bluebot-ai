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

    Signals:
        vision_creation_requested: Emitted when user requests vision creation.
        vision_approval_requested: Emitted when user approves the vision.
    """

    vision_creation_requested = Signal(dict)  # project_data
    vision_approval_requested = Signal(dict)  # vision_data
    
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

        # Vision section
        vision_group = QGroupBox("Project Vision")
        vision_layout = QVBoxLayout(vision_group)

        self.vision_status_label = QLabel("No vision created yet")
        self.vision_status_label.setStyleSheet("color: #666; font-style: italic;")
        vision_layout.addWidget(self.vision_status_label)

        vision_buttons_layout = QHBoxLayout()

        self.create_vision_button = QPushButton("Create Vision")
        self.create_vision_button.setToolTip("Generate a comprehensive game vision document")
        self.create_vision_button.clicked.connect(self._on_create_vision_clicked)
        vision_buttons_layout.addWidget(self.create_vision_button)

        self.view_vision_button = QPushButton("View Vision")
        self.view_vision_button.setToolTip("View the generated vision document")
        self.view_vision_button.clicked.connect(self._on_view_vision_clicked)
        self.view_vision_button.setEnabled(False)
        vision_buttons_layout.addWidget(self.view_vision_button)

        self.approve_vision_button = QPushButton("Approve Vision")
        self.approve_vision_button.setToolTip("Approve the vision and start autonomous development")
        self.approve_vision_button.clicked.connect(self._on_approve_vision_clicked)
        self.approve_vision_button.setEnabled(False)
        self.approve_vision_button.setStyleSheet("background-color: #4CAF50; color: white;")
        vision_buttons_layout.addWidget(self.approve_vision_button)

        vision_buttons_layout.addStretch()
        vision_layout.addLayout(vision_buttons_layout)

        details_layout.addWidget(vision_group)


        
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
                self.update_vision_status(
                    "✓ Vision created - Ready for review",
                    vision_created=True
                )
            else:
                # Reset vision status for new/different project
                self.vision_status_label.setText("No vision created yet")
                self.vision_status_label.setStyleSheet("color: #666; font-style: italic;")
                self.create_vision_button.setEnabled(True)
                self.view_vision_button.setEnabled(False)
                self.approve_vision_button.setEnabled(False)
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

        # Clear file tree
        self.file_model.setRootPath("")

        # Show placeholder, hide details
        self.details_container.hide()
        self.placeholder.show()



    @Slot()
    def _on_create_vision_clicked(self) -> None:
        """Handle create vision button click."""
        if self.current_project:
            self.logger.info(f"Requesting vision creation for: {self.current_project.get('name')}")

            # Update UI to show vision is being created
            self.vision_status_label.setText("Creating vision document...")
            self.vision_status_label.setStyleSheet("color: #FF9800; font-style: italic;")
            self.create_vision_button.setEnabled(False)

            # Emit signal to main window to send task to Game Designer
            self.vision_creation_requested.emit(self.current_project)

    @Slot()
    def _on_view_vision_clicked(self) -> None:
        """Handle view vision button click."""
        if self.current_project:
            # Check if vision file exists
            project_path = Path(self.current_project.get("path", ""))
            vision_path = project_path / "design" / "VISION.md"

            if vision_path.exists():
                try:
                    vision_content = vision_path.read_text(encoding="utf-8")

                    # Create a dialog to display the vision
                    from PySide6.QtWidgets import QDialog, QTextEdit, QDialogButtonBox

                    dialog = QDialog(self)
                    dialog.setWindowTitle("Game Vision Document")
                    dialog.resize(800, 600)

                    layout = QVBoxLayout(dialog)

                    text_edit = QTextEdit()
                    text_edit.setReadOnly(True)
                    text_edit.setMarkdown(vision_content)
                    layout.addWidget(text_edit)

                    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
                    button_box.rejected.connect(dialog.reject)
                    layout.addWidget(button_box)

                    dialog.exec()

                except Exception as e:
                    self.logger.error(f"Failed to read vision document: {e}")
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Error", f"Failed to read vision document: {e}")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Vision Not Found", "Vision document has not been created yet.")

    @Slot()
    def _on_approve_vision_clicked(self) -> None:
        """Handle approve vision button click."""
        if self.current_project:
            from PySide6.QtWidgets import QMessageBox

            reply = QMessageBox.question(
                self,
                "Approve Vision",
                "Are you sure you want to approve this vision?\n\n"
                "This will start the autonomous development process where agents will "
                "begin working on the game automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info(f"Vision approved for: {self.current_project.get('name')}")

                # Read the vision content
                project_path = Path(self.current_project.get("path", ""))
                vision_path = project_path / "design" / "VISION.md"

                if vision_path.exists():
                    try:
                        vision_content = vision_path.read_text(encoding="utf-8")

                        # Update UI
                        self.vision_status_label.setText("✓ Vision approved - Autonomous development active")
                        self.vision_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                        self.approve_vision_button.setEnabled(False)
                        self.create_vision_button.setEnabled(False)

                        # Emit signal with vision data
                        vision_data = {
                            "project_name": self.current_project.get("name"),
                            "project_path": str(project_path),
                            "vision_content": vision_content,
                        }
                        self.vision_approval_requested.emit(vision_data)

                    except Exception as e:
                        self.logger.error(f"Failed to read vision document: {e}")
                        QMessageBox.warning(self, "Error", f"Failed to read vision document: {e}")
                else:
                    QMessageBox.warning(self, "Error", "Vision document not found. Please create it first.")

    def update_vision_status(self, status: str, vision_created: bool = False) -> None:
        """Update the vision status display.

        Args:
            status: Status message to display.
            vision_created: Whether the vision has been created.
        """
        self.vision_status_label.setText(status)

        if vision_created:
            self.vision_status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            self.create_vision_button.setEnabled(False)
            self.view_vision_button.setEnabled(True)
            self.approve_vision_button.setEnabled(True)
        else:
            self.vision_status_label.setStyleSheet("color: #666; font-style: italic;")

