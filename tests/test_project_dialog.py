"""Tests for NewProjectDialog."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from src.ui.project_dialog import NewProjectDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestNewProjectDialog:
    def test_dialog_initialization(self, qapp) -> None:
        dialog = NewProjectDialog()
        assert dialog.windowTitle() == "Create New Game Project"
        assert dialog.name_input.text() == ""
        assert len(dialog.genre_checkboxes) == 15
        assert len(dialog.element_checkboxes) == 20

    def test_on_accept_requires_name(self, qapp, monkeypatch) -> None:
        dialog = NewProjectDialog()
        dialog.location_input.setText("/tmp/projects")
        dialog.brief_input.setPlainText("A roguelike dungeon crawler.")

        warned = False

        def fake_warning(*args, **kwargs):
            nonlocal warned
            warned = True

        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            fake_warning,
        )
        dialog._on_accept()
        assert warned is True

    def test_on_accept_emits_project_data(self, qapp) -> None:
        dialog = NewProjectDialog()
        dialog.name_input.setText("My Game")
        dialog.description_input.setPlainText("Short summary")
        dialog.brief_input.setPlainText("Full creative brief for agents.")
        dialog.location_input.setText("/tmp/projects")
        dialog.genre_checkboxes["RPG"].setChecked(True)
        dialog.element_checkboxes["Single Player"].setChecked(True)

        emitted: list[dict] = []
        dialog.project_created.connect(emitted.append)

        dialog._on_accept()

        assert len(emitted) == 1
        data = emitted[0]
        assert data["name"] == "My Game"
        assert data["brief"] == "Full creative brief for agents."
        assert data["path"].endswith("My Game")
        assert data["genres"] == ["RPG"]
        assert data["elements"] == ["Single Player"]

    def test_get_project_data_returns_none_when_rejected(self, qapp, monkeypatch) -> None:
        dialog = NewProjectDialog()
        monkeypatch.setattr(dialog, "exec", lambda: QDialog.DialogCode.Rejected)
        assert dialog.get_project_data() is None

    def test_get_project_data_when_accepted(self, qapp, monkeypatch) -> None:
        dialog = NewProjectDialog()
        dialog.name_input.setText("Accepted Game")
        dialog.brief_input.setPlainText("Brief text")
        dialog.location_input.setText("/tmp/parent")
        dialog.genre_checkboxes["Action"].setChecked(True)

        monkeypatch.setattr(dialog, "exec", lambda: QDialog.DialogCode.Accepted)
        data = dialog.get_project_data()

        assert data is not None
        assert data["name"] == "Accepted Game"
        assert Path(data["path"]) == Path("/tmp/parent/Accepted Game")
        assert data["genres"] == ["Action"]
