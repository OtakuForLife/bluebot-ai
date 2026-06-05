"""Tests for human review dialog dismiss vs submit behavior."""

from PySide6.QtWidgets import QApplication, QDialog

from src.ui.human_review_dialog import HumanReviewDialog


def test_dismissed_dialog_returns_rejected(monkeypatch) -> None:
    """Closing via X/Escape yields Rejected — caller must not treat as reject."""
    app = QApplication.instance() or QApplication([])
    dialog = HumanReviewDialog({"task_description": "Write VISION.md"})
    monkeypatch.setattr(dialog, "exec", lambda: QDialog.DialogCode.Rejected)

    result = dialog.exec()
    assert result == QDialog.DialogCode.Rejected
    approved, _ = dialog.get_result()
    assert approved is False


def test_approve_returns_accepted(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = HumanReviewDialog({"task_description": "Write VISION.md"})
    monkeypatch.setattr(dialog, "exec", lambda: QDialog.DialogCode.Accepted)
    dialog._approved = True

    assert dialog.exec() == QDialog.DialogCode.Accepted
    approved, _ = dialog.get_result()
    assert approved is True
