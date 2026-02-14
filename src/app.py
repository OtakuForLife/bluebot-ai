"""Application entrypoint for the Bluebot AI desktop application.

This module will gradually wire together the GUI, agent system, and Godot
integration. For now it provides a minimal Qt-based window so the project can
be launched end-to-end.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Start the Bluebot AI desktop application.

    If PySide6 is not installed yet, print a helpful message instead of
    crashing. This keeps the skeleton runnable even before dependencies are
    fully set up.
    """

    try:
        from PySide6.QtWidgets import QApplication, QLabel
    except ImportError:
        print(
            "PySide6 is not installed. Install the 'PySide6' package to run the GUI.",
        )
        return

    app = QApplication(sys.argv)
    window = QLabel("Bluebot AI 5aa multi-agent Godot tool (GUI coming soon)")
    window.setWindowTitle("Bluebot AI")
    window.resize(640, 360)
    window.show()
    sys.exit(app.exec())

