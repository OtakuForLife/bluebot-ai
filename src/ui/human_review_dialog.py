"""Human review dialog for approving or rejecting agent work."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class HumanReviewDialog(QDialog):
    """Modal dialog asking the user to approve or reject an agent's output.

    The dialog receives the interrupt payload emitted by human_review_node and
    displays the task description, the agent that completed the work, and the
    files touched. The user then writes an optional comment and clicks
    Approve or Reject.

    The result is retrieved via :meth:`get_result` after exec() returns.
    """

    def __init__(self, payload: dict, parent: Optional[QWidget] = None) -> None:
        """Initialise the dialog.

        Args:
            payload: Interrupt payload from human_review_node.  Keys:
                task_description, last_agent, created_files,
                modified_files, tool_results.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Human Review Required")
        self.setMinimumWidth(600)
        self.setMinimumHeight(480)
        self.setModal(True)

        self._approved = False
        self._payload = payload

        self._setup_ui(payload)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self, payload: dict) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        header = QLabel("<h2>👤 Human Review Required</h2>")
        layout.addWidget(header)

        subtitle = QLabel(
            "An agent has completed a task. Please review the work below "
            "and approve or reject it. Your comment will be visible to the "
            "Game Producer."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addWidget(self._make_separator())

        # Scrollable context area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        context_widget = QWidget()
        context_layout = QVBoxLayout(context_widget)
        context_layout.setSpacing(8)

        context_layout.addWidget(self._make_field(
            "Agent",
            payload.get("last_agent") or "—"
        ))
        context_layout.addWidget(self._make_field(
            "Task",
            payload.get("task_description") or "—",
            multiline=True
        ))
        context_layout.addWidget(self._make_field(
            "Files created",
            "\n".join(payload.get("created_files", [])) or "none"
        ))
        context_layout.addWidget(self._make_field(
            "Files modified",
            "\n".join(payload.get("modified_files", [])) or "none"
        ))

        tool_results = payload.get("tool_results", [])
        if tool_results:
            context_layout.addWidget(self._make_field(
                "Tool results",
                "\n".join(tool_results[-5:]),  # last 5 to keep UI compact
                multiline=True
            ))

        context_layout.addStretch()
        scroll.setWidget(context_widget)
        layout.addWidget(scroll, stretch=1)

        layout.addWidget(self._make_separator())

        # Comment box
        layout.addWidget(QLabel("<b>Your comment (visible to the producer):</b>"))
        self._comment_edit = QPlainTextEdit()
        self._comment_edit.setPlaceholderText("Optional — describe what to fix or why you approved…")
        self._comment_edit.setFixedHeight(80)
        layout.addWidget(self._comment_edit)

        # Approve / Reject buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reject_btn = QPushButton("✗  Reject")
        reject_btn.setStyleSheet("QPushButton { color: #e05555; font-weight: bold; }")
        reject_btn.clicked.connect(self._on_reject)
        btn_layout.addWidget(reject_btn)

        approve_btn = QPushButton("✓  Approve")
        approve_btn.setStyleSheet("QPushButton { color: #4ec9b0; font-weight: bold; }")
        approve_btn.setDefault(True)
        approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

    def _make_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _make_field(self, label: str, value: str, multiline: bool = False) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)

        vbox.addWidget(QLabel(f"<b>{label}:</b>"))

        value_label = QLabel(value)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if multiline:
            value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        vbox.addWidget(value_label)
        return widget

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_approve(self) -> None:
        self._approved = True
        self.accept()

    def _on_reject(self) -> None:
        self._approved = False
        self.accept()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_result(self) -> tuple[bool, str]:
        """Return the reviewer's decision and comment.

        Returns:
            Tuple of (approved, comment).
        """
        return self._approved, self._comment_edit.toPlainText().strip()
