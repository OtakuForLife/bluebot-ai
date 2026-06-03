"""Tests for FileManager class."""

import json
import pytest
from pathlib import Path

from src.events import EventHandler
from src.project.files import FileManager, NewProjectData


@pytest.fixture
def file_manager():
    """Create a FileManager instance."""
    return FileManager(event_handler=EventHandler())  # No event handler needed for tests


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary directory for project testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    yield project_dir


def test_file_manager_initialization(file_manager) -> None:
    """Test that FileManager initializes correctly."""
    assert file_manager is not None



def test_create_project_structure(file_manager, temp_project_dir) -> None:
    """Test creating a project structure."""
    project_data: NewProjectData = {
        "path": str(temp_project_dir),
        "name": "Test Project",
        "description": "A test project",
        "brief": "",
        "genres": ["Action"],
        "elements": ["Single Player"],
    }

    result = file_manager.create_project_structure(project_data)

    assert result is True

    # Verify directories were created
    for directory in FileManager.PROJECT_DIRECTORIES:
        dir_path = temp_project_dir / directory
        assert dir_path.exists()
        assert dir_path.is_dir()

    # Verify project.json was created
    metadata_file = temp_project_dir / FileManager.PROJECT_METADATA_FILE
    assert metadata_file.exists()


def test_write_and_read_project_file(file_manager, temp_project_dir) -> None:
    """Test writing and reading a project file."""
    content = "# Test File\n\nThis is test content."
    relative_path = "design/test.md"

    # Write file
    write_result = file_manager.write_project_file(temp_project_dir, relative_path, content)
    assert write_result is True

    # Verify file exists
    file_path = temp_project_dir / relative_path
    assert file_path.exists()

    # Read file
    read_content = file_manager.read_project_file(temp_project_dir, relative_path)
    assert read_content == content


def test_file_exists(file_manager, temp_project_dir) -> None:
    """Test checking if a file exists."""
    # Create a file
    test_file = temp_project_dir / "test.txt"
    test_file.write_text("test content")

    # Test file exists
    assert file_manager.file_exists(temp_project_dir, "test.txt") is True
    # Test non-existent file
    assert file_manager.file_exists(temp_project_dir, "nonexistent.txt") is False


def test_read_nonexistent_file(file_manager, temp_project_dir) -> None:
    """Test reading a non-existent file returns None."""
    content = file_manager.read_project_file(temp_project_dir, "nonexistent.md")
    assert content is None


def test_create_project_metadata(file_manager, temp_project_dir) -> None:
    """Test creating project metadata."""
    project_data: NewProjectData = {
        "path": str(temp_project_dir),
        "name": "Test Project",
        "description": "A test project",
        "brief": "",
        "genres": ["Action", "RPG"],
        "elements": ["Single Player", "Open World"],
    }

    result = file_manager.create_project_metadata(project_data)

    assert result is True

    # Verify metadata file was created
    metadata_file = temp_project_dir / FileManager.PROJECT_METADATA_FILE
    assert metadata_file.exists()

    # Verify content
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    assert metadata["name"] == "Test Project"
    assert metadata["description"] == "A test project"
    assert metadata["genres"] == ["Action", "RPG"]
    assert metadata["elements"] == ["Single Player", "Open World"]


def test_validate_project_structure(file_manager, temp_project_dir) -> None:
    """Test validating a project structure."""
    # Create a minimal project structure
    (temp_project_dir / FileManager.DESIGN_DIR).mkdir()
    (temp_project_dir / FileManager.SCRIPTS_DIR).mkdir()
    (temp_project_dir / "project.json").write_text("{}")

    results = file_manager.validate_project_structure(temp_project_dir)

    # Check that design and scripts directories exist
    assert results[FileManager.DESIGN_DIR] is True
    assert results[FileManager.SCRIPTS_DIR] is True

    # Check that other directories don't exist
    assert results[FileManager.ASSETS_DIR] is False
