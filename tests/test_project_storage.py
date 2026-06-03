"""Tests for project storage utilities."""

import json
import logging
from pathlib import Path

import pytest

from src.project.storage import load_projects_file, save_projects_file


@pytest.fixture
def temp_projects_file(tmp_path):
    """Create a temporary projects.json file."""
    projects_file = tmp_path / "projects.json"
    yield projects_file
    if projects_file.exists():
        projects_file.unlink()


@pytest.fixture
def sample_projects():
    """Create sample projects data."""
    return [
        {
            "name": "Project A",
            "description": "First project",
            "path": "/projects/a",
            "genres": ["RPG"],
            "elements": ["Single Player"],
        },
        {
            "name": "Project B",
            "description": "Second project",
            "path": "/projects/b",
            "genres": ["Action"],
            "elements": ["Multiplayer"],
        },
    ]


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return logging.getLogger("test_logger")


class TestLoadProjectsFile:
    """Tests for load_projects_file function."""

    def test_load_nonexistent_file(self, temp_projects_file, mock_logger) -> None:
        """Test loading from non-existent file returns empty list."""
        result = load_projects_file(temp_projects_file, mock_logger)
        assert result == []

    def test_load_existing_file(self, temp_projects_file, sample_projects, mock_logger) -> None:
        """Test loading from existing file."""
        # Write sample data
        with open(temp_projects_file, 'w', encoding='utf-8') as f:
            json.dump(sample_projects, f)

        result = load_projects_file(temp_projects_file, mock_logger)
        assert result == sample_projects

    def test_load_malformed_json(self, temp_projects_file, mock_logger) -> None:
        """Test loading malformed JSON returns empty list."""
        # Write malformed JSON
        temp_projects_file.write_text("invalid json")

        result = load_projects_file(temp_projects_file, mock_logger)
        assert result == []


class TestSaveProjectsFile:
    """Tests for save_projects_file function."""

    def test_save_projects(self, temp_projects_file, sample_projects, mock_logger) -> None:
        """Test saving projects to file."""
        result = save_projects_file(sample_projects, temp_projects_file, mock_logger)
        assert result is True

        # Verify file was created and content is correct
        assert temp_projects_file.exists()
        with open(temp_projects_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert saved == sample_projects

    def test_save_empty_list(self, temp_projects_file, mock_logger) -> None:
        """Test saving empty projects list."""
        result = save_projects_file([], temp_projects_file, mock_logger)
        assert result is True

        with open(temp_projects_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert saved == []

    def test_save_creates_parent_directory(self, tmp_path, mock_logger) -> None:
        """Test that save creates parent directory if it doesn't exist."""
        nested_dir = tmp_path / "nested" / "path" / "projects.json"
        parent_dir = nested_dir.parent

        assert not parent_dir.exists()

        save_projects_file([], nested_dir, mock_logger)

        assert parent_dir.exists()
        assert nested_dir.exists()
