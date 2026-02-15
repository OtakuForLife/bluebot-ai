"""Project detail view showing project information and file tree."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class ProjectDetailView(QWidget):
    """Widget showing detailed project information and file tree.
    
    Displays project metadata, genres, elements, and a file tree
    of the project directory structure.
    
    Signals:
        file_selected: Emitted when a file is selected in the tree.
        vision_creation_requested: Emitted when user requests vision creation.
        vision_approval_requested: Emitted when user approves the vision.
    """

    file_selected = Signal(str)
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

        # File tree section
        file_tree_group = QGroupBox("Project Files")
        file_tree_layout = QVBoxLayout(file_tree_group)
        
        # Toolbar for file operations
        toolbar_layout = QHBoxLayout()
        
        add_file_button = QPushButton("+ Add File")
        add_file_button.clicked.connect(self._on_add_file)
        toolbar_layout.addWidget(add_file_button)
        
        add_folder_button = QPushButton("+ Add Folder")
        add_folder_button.clicked.connect(self._on_add_folder)
        toolbar_layout.addWidget(add_folder_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._on_refresh)
        toolbar_layout.addWidget(refresh_button)
        
        toolbar_layout.addStretch()
        
        file_tree_layout.addLayout(toolbar_layout)
        
        # File tree view
        self.file_tree = QTreeView()
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_context_menu)
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)
        
        # File system model
        self.file_model = QFileSystemModel()
        self.file_tree.setModel(self.file_model)
        
        # Hide size, type, and date columns for cleaner view
        self.file_tree.setColumnWidth(0, 300)
        
        file_tree_layout.addWidget(self.file_tree)
        
        details_layout.addWidget(file_tree_group)
        
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

        # Set up file tree
        project_path = project_data.get("path")
        if not project_path:
            # Try to construct path from location and name
            location = project_data.get("location", "")
            name = project_data.get("name", "")
            if location and name:
                project_path = str(Path(location) / name)

        if project_path and Path(project_path).exists():
            self.file_model.setRootPath(project_path)
            self.file_tree.setRootIndex(self.file_model.index(project_path))
            self.logger.info(f"Loaded project files from: {project_path}")
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
    def _on_add_file(self) -> None:
        """Handle add file button click."""
        if not self.current_project:
            return

        project_path = self.current_project.get("path")
        if not project_path:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Add",
            str(Path.home()),
            "All Files (*.*)"
        )

        if file_path:
            try:
                import shutil
                source = Path(file_path)
                destination = Path(project_path) / source.name

                shutil.copy2(source, destination)
                self.logger.info(f"Added file: {source.name}")

                # Refresh tree
                self._on_refresh()

            except Exception as e:
                self.logger.error(f"Failed to add file: {e}")

    @Slot()
    def _on_add_folder(self) -> None:
        """Handle add folder button click."""
        if not self.current_project:
            return

        project_path = self.current_project.get("path")
        if not project_path:
            return

        from PySide6.QtWidgets import QInputDialog

        folder_name, ok = QInputDialog.getText(
            self,
            "Create Folder",
            "Folder name:"
        )

        if ok and folder_name:
            try:
                new_folder = Path(project_path) / folder_name
                new_folder.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created folder: {folder_name}")

                # Refresh tree
                self._on_refresh()

            except Exception as e:
                self.logger.error(f"Failed to create folder: {e}")

    @Slot()
    def _on_refresh(self) -> None:
        """Refresh the file tree."""
        if self.current_project:
            project_path = self.current_project.get("path")
            if project_path:
                # Force model refresh
                self.file_model.setRootPath("")
                self.file_model.setRootPath(project_path)
                self.file_tree.setRootIndex(self.file_model.index(project_path))
                self.logger.info("Refreshed file tree")

    @Slot()
    def _on_context_menu(self, position) -> None:
        """Show context menu for file operations.

        Args:
            position: Position where context menu was requested.
        """
        index = self.file_tree.indexAt(position)
        if not index.isValid():
            return

        file_path = self.file_model.filePath(index)

        menu = QMenu(self)

        open_action = menu.addAction("Open")
        delete_action = menu.addAction("Delete")
        rename_action = menu.addAction("Rename")

        action = menu.exec(self.file_tree.viewport().mapToGlobal(position))

        if action == open_action:
            self._open_file(file_path)
        elif action == delete_action:
            self._delete_file(file_path)
        elif action == rename_action:
            self._rename_file(file_path)

    @Slot()
    def _on_file_double_clicked(self, index) -> None:
        """Handle file double-click.

        Args:
            index: Model index of the clicked item.
        """
        file_path = self.file_model.filePath(index)

        if Path(file_path).is_file():
            self._open_file(file_path)

    def _open_file(self, file_path: str) -> None:
        """Open a file with the default system application.

        Args:
            file_path: Path to the file to open.
        """
        try:
            import os
            import platform

            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{file_path}"')

            self.logger.info(f"Opened file: {file_path}")
            self.file_selected.emit(file_path)

        except Exception as e:
            self.logger.error(f"Failed to open file: {e}")

    def _delete_file(self, file_path: str) -> None:
        """Delete a file or folder.

        Args:
            file_path: Path to the file or folder to delete.
        """
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n{Path(file_path).name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                path = Path(file_path)
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)

                self.logger.info(f"Deleted: {file_path}")
                self._on_refresh()

            except Exception as e:
                self.logger.error(f"Failed to delete: {e}")
                QMessageBox.warning(self, "Error", f"Failed to delete: {e}")

    def _rename_file(self, file_path: str) -> None:
        """Rename a file or folder.

        Args:
            file_path: Path to the file or folder to rename.
        """
        from PySide6.QtWidgets import QInputDialog

        old_path = Path(file_path)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename",
            "New name:",
            text=old_path.name
        )

        if ok and new_name and new_name != old_path.name:
            try:
                new_path = old_path.parent / new_name
                old_path.rename(new_path)

                self.logger.info(f"Renamed: {old_path.name} -> {new_name}")
                self._on_refresh()

            except Exception as e:
                self.logger.error(f"Failed to rename: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", f"Failed to rename: {e}")

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
            project_path = Path(self.current_project.get("location", ""))
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
                project_path = Path(self.current_project.get("location", ""))
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

