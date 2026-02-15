"""Tests for the knowledge base system."""

import tempfile
from pathlib import Path

import pytest

from src.agents.knowledge_base import KnowledgeBase


def test_knowledge_base_initialization() -> None:
    """Test that a knowledge base initializes correctly."""
    kb = KnowledgeBase(name="test_kb")

    assert kb.name == "test_kb"
    assert kb.get_document_count() == 0
    assert not kb.is_loaded()


def test_load_from_string() -> None:
    """Test loading markdown content from a string."""
    kb = KnowledgeBase(name="test_kb")

    content = "# Test Document\n\nThis is a test."
    kb.load_from_string(content, "test.md")

    assert kb.get_document_count() == 1
    assert kb.get_document("test.md") == content


def test_load_from_file() -> None:
    """Test loading a markdown file."""
    kb = KnowledgeBase(name="test_kb")

    # Create a temporary markdown file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Godot Documentation\n\nGodot is a game engine.")
        temp_path = Path(f.name)

    try:
        kb.load_from_file(temp_path)

        assert kb.get_document_count() == 1
        doc = kb.get_document(temp_path.name)
        assert doc is not None
        assert "Godot is a game engine" in doc
    finally:
        temp_path.unlink()


def test_load_from_directory() -> None:
    """Test loading multiple markdown files from a directory."""
    kb = KnowledgeBase(name="test_kb")

    # Create a temporary directory with markdown files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create some markdown files
        (temp_path / "doc1.md").write_text("# Document 1\n\nContent 1", encoding="utf-8")
        (temp_path / "doc2.md").write_text("# Document 2\n\nContent 2", encoding="utf-8")
        (temp_path / "readme.txt").write_text("Not a markdown file", encoding="utf-8")

        # Create a subdirectory with another markdown file
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "doc3.md").write_text("# Document 3\n\nContent 3", encoding="utf-8")

        count = kb.load_from_directory(temp_path)

        assert count == 3  # Should load 3 .md files
        assert kb.get_document_count() == 3
        assert kb.is_loaded()

        # Check that all documents were loaded
        assert kb.get_document("doc1.md") is not None
        assert kb.get_document("doc2.md") is not None
        assert kb.get_document("subdir/doc3.md") is not None or kb.get_document("subdir\\doc3.md") is not None


def test_search() -> None:
    """Test searching for documents."""
    kb = KnowledgeBase(name="test_kb")

    kb.load_from_string("# GDScript Tutorial\n\nLearn GDScript basics.", "gdscript.md")
    kb.load_from_string("# Python Tutorial\n\nLearn Python basics.", "python.md")
    kb.load_from_string("# Godot Engine\n\nGodot uses GDScript.", "godot.md")

    # Search for "GDScript" (case-insensitive by default)
    results = kb.search("GDScript")
    assert len(results) == 2  # Should find gdscript.md and godot.md

    # Case-sensitive search for "GDScript" (exact match)
    results = kb.search("GDScript", case_sensitive=True)
    assert len(results) == 2  # Should find both documents with "GDScript"

    # Case-insensitive search
    results = kb.search("gdscript", case_sensitive=False)
    assert len(results) == 2  # Should find both

    # Search for something that doesn't exist
    results = kb.search("JavaScript")
    assert len(results) == 0


def test_get_all_keys() -> None:
    """Test getting all document keys."""
    kb = KnowledgeBase(name="test_kb")

    kb.load_from_string("Content 1", "doc1.md")
    kb.load_from_string("Content 2", "doc2.md")
    kb.load_from_string("Content 3", "doc3.md")

    keys = kb.get_all_keys()
    assert len(keys) == 3
    assert "doc1.md" in keys
    assert "doc2.md" in keys
    assert "doc3.md" in keys


def test_clear() -> None:
    """Test clearing the knowledge base."""
    kb = KnowledgeBase(name="test_kb")

    kb.load_from_string("Content", "doc.md")
    assert kb.get_document_count() == 1

    kb.clear()
    assert kb.get_document_count() == 0
    assert not kb.is_loaded()


def test_get_summary() -> None:
    """Test getting knowledge base summary."""
    base_path = Path("/docs")
    kb = KnowledgeBase(name="godot_docs", base_path=base_path)

    kb.load_from_string("Content 1", "doc1.md")
    kb.load_from_string("Content 2", "doc2.md")

    summary = kb.get_summary()

    assert summary["name"] == "godot_docs"
    assert summary["document_count"] == 2
    assert summary["loaded"] is True
    assert summary["base_path"] == str(base_path)


def test_load_from_nonexistent_directory() -> None:
    """Test that loading from a nonexistent directory raises an error."""
    kb = KnowledgeBase(name="test_kb")

    with pytest.raises(ValueError, match="Directory does not exist"):
        kb.load_from_directory(Path("/nonexistent/path"))


def test_load_from_nonexistent_file() -> None:
    """Test that loading a nonexistent file raises an error."""
    kb = KnowledgeBase(name="test_kb")

    with pytest.raises(ValueError, match="File does not exist"):
        kb.load_from_file(Path("/nonexistent/file.md"))


def test_get_nonexistent_document() -> None:
    """Test that getting a nonexistent document returns None."""
    kb = KnowledgeBase(name="test_kb")

    assert kb.get_document("nonexistent.md") is None

