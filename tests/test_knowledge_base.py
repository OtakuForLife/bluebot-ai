"""Tests for knowledge base system."""

import pytest

from src.agents.knowledge import KnowledgeBase


def test_knowledge_base_initialization() -> None:
    """Test that a knowledge base initializes correctly."""
    # Use the actual game_design knowledge directory
    kb = KnowledgeBase(name="game_design")

    assert kb.name == "game_design"
    assert len(kb.get_all_keys()) > 0


def test_knowledge_base_search() -> None:
    """Test that knowledge base search works."""
    kb = KnowledgeBase(name="game_design")

    # Search for "vision"
    results = kb.search("vision")
    assert len(results) > 0

    # Search for "mechanics"
    results = kb.search("mechanics")
    assert len(results) > 0

    # Search for non-existent term
    results = kb.search("nonexistent_term_xyz123")
    assert len(results) == 0


def test_knowledge_base_get_all_keys() -> None:
    """Test getting all document keys."""
    kb = KnowledgeBase(name="game_design")

    keys = kb.get_all_keys()
    assert len(keys) > 0

    # Verify some expected files exist
    assert any("vision" in key.lower() for key in keys)
