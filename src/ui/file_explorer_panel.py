"""File explorer panel with integrated text editor."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src.ui.bridge import QtEventBridge


class FileExplorerPanel(QWidget):
    """Panel for browsing and editing project files.
    
    Displays a file tree on the left and a text editor on the right.
    Users can click on files to open them in the editor.
    
    Signals:
        file_opened: Emitted when a file is opened.
        file_saved: Emitted when a file is saved.
    """
    
    file_opened = Signal(str)
    file_saved = Signal(str)
    
    def __init__(self, qt_event_bridge: QtEventBridge, parent: Optional[QWidget] = None) -> None:
        """Initialize the file explorer panel.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self.logger = logging.getLogger(f"{__name__}.FileExplorerPanel")
        self.qt_event_bridge = qt_event_bridge
        self.current_file: Optional[Path] = None
        self.project_path: Optional[Path] = None
        self.is_modified = False
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for tree and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: File tree
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(5, 5, 5, 5)
        
        tree_label = QLabel("<b>Project Files</b>")
        tree_layout.addWidget(tree_label)
        
        # File tree view
        self.file_tree = QTreeView()
        self.file_tree.clicked.connect(self._on_file_clicked)
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)
        
        # File system model
        self.file_model = QFileSystemModel()
        self.file_tree.setModel(self.file_model)
        
        # Hide size, type, and date columns
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)
        self.file_tree.setColumnWidth(0, 250)
        
        tree_layout.addWidget(self.file_tree)
        
        splitter.addWidget(tree_widget)
        
        # Right side: Editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(5, 5, 5, 5)
        
        # Editor header with file name and save button
        header_layout = QHBoxLayout()
        
        self.file_name_label = QLabel("<i>No file opened</i>")
        header_layout.addWidget(self.file_name_label)
        
        header_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._on_save)
        header_layout.addWidget(self.save_button)
        
        editor_layout.addLayout(header_layout)
        
        # Text editor
        self.text_editor = QPlainTextEdit()
        self.text_editor.setPlaceholderText("Select a file from the tree to edit...")
        self.text_editor.textChanged.connect(self._on_text_changed)
        
        # Set monospace font for code editing
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.text_editor.setFont(font)
        
        editor_layout.addWidget(self.text_editor)
        
        splitter.addWidget(editor_widget)
        
        # Set splitter sizes (30% tree, 70% editor)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        # Show placeholder message
        self._show_placeholder()
    
    def _show_placeholder(self) -> None:
        """Show placeholder message when no project is loaded."""
        self.text_editor.setPlainText("")
        self.text_editor.setEnabled(False)
        self.file_name_label.setText("<i>No project loaded</i>")
        self.save_button.setEnabled(False)

    def set_project_path(self, path: Path) -> None:
        """Set the project path to browse.

        Args:
            path: Path to the project directory.
        """
        self.project_path = path
        self.logger.info(f"File explorer set to project: {path}")

        # Set up file tree
        if path and path.exists():
            self.file_model.setRootPath(str(path))
            self.file_tree.setRootIndex(self.file_model.index(str(path)))
            self.text_editor.setEnabled(True)
            self.file_name_label.setText("<i>Select a file to edit</i>")
        else:
            self._show_placeholder()

    @Slot()
    def _on_file_clicked(self, index) -> None:
        """Handle file tree item clicked.

        Args:
            index: Model index of clicked item.
        """
        file_path = Path(self.file_model.filePath(index))

        # Only show file info, don't open yet
        if file_path.is_file():
            self.file_name_label.setText(f"<b>{file_path.name}</b> (click to open)")

    @Slot()
    def _on_file_double_clicked(self, index) -> None:
        """Handle file tree item double-clicked.

        Args:
            index: Model index of double-clicked item.
        """
        file_path = Path(self.file_model.filePath(index))

        # Only open files, not directories
        if file_path.is_file():
            self._open_file(file_path)

    def _open_file(self, file_path: Path) -> None:
        """Open a file in the editor.

        Args:
            file_path: Path to the file to open.
        """
        # Check if current file has unsaved changes
        if self.is_modified and self.current_file:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"Save changes to {self.current_file.name}?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Update editor
            self.text_editor.setPlainText(content)
            self.current_file = file_path
            self.is_modified = False

            # Update UI
            self.file_name_label.setText(f"<b>{file_path.name}</b>")
            self.save_button.setEnabled(False)

            self.logger.info(f"Opened file: {file_path}")
            self.file_opened.emit(str(file_path))

        except Exception as e:
            self.logger.error(f"Failed to open file {file_path}: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open file:\n{e}"
            )

    @Slot()
    def _on_text_changed(self) -> None:
        """Handle text editor content changed."""
        if self.current_file:
            self.is_modified = True
            self.save_button.setEnabled(True)
            self.file_name_label.setText(f"<b>{self.current_file.name}</b> *")

    @Slot()
    def _on_save(self) -> None:
        """Handle save button clicked."""
        if self.current_file:
            self._save_file()

    def _save_file(self) -> None:
        """Save the current file."""
        if not self.current_file:
            return

        try:
            # Get content from editor
            content = self.text_editor.toPlainText()

            # Write to temp file first, then atomic rename for safety
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=self.current_file.suffix,
                prefix=self.current_file.stem + '.tmp_',
                dir=self.current_file.parent,
                encoding="utf-8",
                delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
            tmp_path.replace(self.current_file)

            # Update state
            self.is_modified = False
            self.save_button.setEnabled(False)
            self.file_name_label.setText(f"<b>{self.current_file.name}</b>")

            self.logger.info(f"Saved file: {self.current_file}")
            self.file_saved.emit(str(self.current_file))

            QMessageBox.information(
                self,
                "Success",
                f"File saved successfully:\n{self.current_file.name}"
            )

        except Exception as e:
            self.logger.error(f"Failed to save file {self.current_file}: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save file:\n{e}"
            )

    def clear(self) -> None:
        """Clear the editor and reset state."""
        self.current_file = None
        self.project_path = None
        self.is_modified = False
        self._show_placeholder()

