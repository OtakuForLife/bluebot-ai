"""Application entrypoint for the Bluebot AI desktop application.

This module wires together the GUI, agent system, and Godot integration.
"""

from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    """Set up application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main() -> None:
    """Start the Bluebot AI desktop application.

    If PySide6 is not installed yet, print a helpful message instead of
    crashing. This keeps the skeleton runnable even before dependencies are
    fully set up.
    """

    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is not installed. Install the 'PySide6' package to run the GUI.",
        )
        return

    try:
        from PySide6.QtWidgets import QDialog
        from src.orchestrator.orchestrator import Orchestrator
        from src.ui.main_window import MainWindow
        from src.ui.project_selection_window import ProjectSelectionWindow

        logger.info("Starting Bluebot AI application...")

        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Bluebot AI")
        app.setOrganizationName("Bluebot")

        # Show project selection window first
        project_selection = ProjectSelectionWindow()
        if project_selection.exec() != QDialog.DialogCode.Accepted:
            logger.info("No project selected, exiting application")
            return

        # Get selected project
        selected_project = project_selection.get_selected_project()
        if not selected_project:
            logger.info("No project selected, exiting application")
            return

        logger.info(f"Project selected: {selected_project.get('name')}")

        # Create orchestrator
        orchestrator = Orchestrator()

        # Create and show main window with selected project
        window = MainWindow(orchestrator, selected_project)
        window.show()

        logger.info("Application started successfully")

        # Run event loop
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)
