"""Baseline tests for the Bluebot AI package and application entrypoint."""

from __future__ import annotations

import builtins

from src import __version__
from src import app


def test_version_is_synced() -> None:
    """Version exposed by the package should match the project metadata.

    This acts as a simple sanity check that the code and packaging are aligned.
    """

    assert __version__ == "0.1.0"


def test_main_handles_missing_pyside6(monkeypatch, capsys) -> None:
    """`app.main` should degrade gracefully when PySide6 is unavailable.

    We simulate an ImportError for PySide6 and assert that a helpful message is
    printed instead of raising.
    """

    # Skip tracing startup — this test is not about Phoenix and starting a real
    # server during pytest causes Windows file-lock errors on teardown.
    monkeypatch.setattr(app, "setup_tracing", lambda: None)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # type: ignore[override]
        if name.startswith("PySide6"):
            raise ImportError("PySide6 not available in test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    app.main()

    captured = capsys.readouterr()
    assert "PySide6 is not installed" in captured.out

