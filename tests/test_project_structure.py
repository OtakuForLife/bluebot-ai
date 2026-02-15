"""Tests for project structure utility module."""

import json
import pytest
from pathlib import Path
from src.utils.project_structure import (
    create_project_structure,
    create_project_metadata,
    get_project_directories,
    validate_project_structure,
    repair_project_structure,
    PROJECT_DIRECTORIES,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary directory for project testing."""
    return tmp_path / "test_project"


@pytest.fixture
def sample_project_data(temp_project_dir):
    """Create sample project data for testing."""
    return {
        "name": "Test Game",
        "path": str(temp_project_dir),
        "description": "A test game project",
        "genres": ["Action", "Adventure"],
        "elements": ["Combat", "Exploration"],
    }


def test_project_directories_constant():
    """Test that PROJECT_DIRECTORIES constant is defined correctly."""
    assert isinstance(PROJECT_DIRECTORIES, list)
    assert len(PROJECT_DIRECTORIES) > 0
    assert "scripts" in PROJECT_DIRECTORIES
    assert "scenes" in PROJECT_DIRECTORIES
    assert "assets" in PROJECT_DIRECTORIES
    assert "design" in PROJECT_DIRECTORIES
    assert "docs" in PROJECT_DIRECTORIES


def test_get_project_directories():
    """Test getting the list of project directories."""
    directories = get_project_directories()
    
    assert isinstance(directories, list)
    assert directories == PROJECT_DIRECTORIES
    # Verify it returns a copy, not the original
    directories.append("test")
    assert "test" not in PROJECT_DIRECTORIES


def test_create_project_structure_success(sample_project_data):
    """Test successful project structure creation."""
    success = create_project_structure(sample_project_data)
    
    assert success is True
    
    project_path = Path(sample_project_data["path"])
    assert project_path.exists()
    
    # Verify all directories were created
    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        assert dir_path.exists(), f"Directory {directory} was not created"
        assert dir_path.is_dir(), f"{directory} is not a directory"
    
    # Verify project.json was created
    metadata_path = project_path / "project.json"
    assert metadata_path.exists()
    assert metadata_path.is_file()


def test_create_project_structure_missing_path():
    """Test that create_project_structure raises error when path is missing."""
    project_data = {
        "name": "Test Game",
        "description": "A test game",
    }
    
    with pytest.raises(ValueError, match="project_data must contain 'path' field"):
        create_project_structure(project_data)


def test_create_project_structure_missing_name(temp_project_dir):
    """Test that create_project_structure raises error when name is missing."""
    project_data = {
        "path": str(temp_project_dir),
        "description": "A test game",
    }
    
    with pytest.raises(ValueError, match="project_data must contain 'name' field"):
        create_project_structure(project_data)


def test_create_project_metadata_success(sample_project_data):
    """Test successful project metadata creation."""
    project_path = Path(sample_project_data["path"])
    project_path.mkdir(parents=True, exist_ok=True)
    
    success = create_project_metadata(sample_project_data)
    
    assert success is True
    
    metadata_path = project_path / "project.json"
    assert metadata_path.exists()
    
    # Verify metadata content
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    assert metadata["name"] == "Test Game"
    assert metadata["description"] == "A test game project"
    assert metadata["genres"] == ["Action", "Adventure"]
    assert metadata["elements"] == ["Combat", "Exploration"]


def test_create_project_metadata_with_defaults(temp_project_dir):
    """Test project metadata creation with default values."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)
    
    project_data = {
        "path": str(project_path),
    }
    
    success = create_project_metadata(project_data)
    
    assert success is True
    
    metadata_path = project_path / "project.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    assert metadata["name"] == "Unnamed Project"
    assert metadata["description"] == ""
    assert metadata["genres"] == []
    assert metadata["elements"] == []


def test_validate_project_structure_complete(sample_project_data):
    """Test validation of a complete project structure."""
    # Create the project structure
    create_project_structure(sample_project_data)

    project_path = Path(sample_project_data["path"])
    results = validate_project_structure(project_path)

    # All directories should exist
    for directory in PROJECT_DIRECTORIES:
        assert results[directory] is True, f"Directory {directory} validation failed"

    # project.json should exist
    assert results["project.json"] is True


def test_validate_project_structure_incomplete(temp_project_dir):
    """Test validation of an incomplete project structure."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create only some directories
    (project_path / "scripts").mkdir(exist_ok=True)
    (project_path / "scenes").mkdir(exist_ok=True)

    results = validate_project_structure(project_path)

    # Only created directories should exist
    assert results["scripts"] is True
    assert results["scenes"] is True

    # Missing directories should not exist
    assert results["design"] is False
    assert results["docs"] is False
    assert results["project.json"] is False


def test_validate_project_structure_empty(temp_project_dir):
    """Test validation of an empty project directory."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    results = validate_project_structure(project_path)

    # All directories should not exist
    for directory in PROJECT_DIRECTORIES:
        assert results[directory] is False

    assert results["project.json"] is False


def test_repair_project_structure_success(temp_project_dir):
    """Test successful repair of missing project directories."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create only some directories
    (project_path / "scripts").mkdir(exist_ok=True)
    (project_path / "scenes").mkdir(exist_ok=True)

    # Repair the structure
    success = repair_project_structure(project_path)

    assert success is True

    # All directories should now exist
    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        assert dir_path.exists(), f"Directory {directory} was not repaired"


def test_repair_project_structure_complete(sample_project_data):
    """Test repair of an already complete project structure."""
    # Create complete structure
    create_project_structure(sample_project_data)

    project_path = Path(sample_project_data["path"])

    # Repair should still succeed
    success = repair_project_structure(project_path)

    assert success is True

    # All directories should still exist
    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        assert dir_path.exists()


def test_create_project_structure_with_nested_paths(tmp_path):
    """Test creating project structure with deeply nested paths."""
    nested_path = tmp_path / "level1" / "level2" / "level3" / "project"

    project_data = {
        "name": "Nested Project",
        "path": str(nested_path),
        "description": "A deeply nested project",
        "genres": [],
        "elements": [],
    }

    success = create_project_structure(project_data)

    assert success is True
    assert nested_path.exists()

    # Verify all directories were created
    for directory in PROJECT_DIRECTORIES:
        dir_path = nested_path / directory
        assert dir_path.exists()


def test_create_project_structure_idempotent(sample_project_data):
    """Test that creating project structure multiple times is safe."""
    # Create structure first time
    success1 = create_project_structure(sample_project_data)
    assert success1 is True

    # Create structure second time (should not fail)
    success2 = create_project_structure(sample_project_data)
    assert success2 is True

    # Verify structure is still intact
    project_path = Path(sample_project_data["path"])
    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        assert dir_path.exists()


def test_create_project_metadata_unicode_support(temp_project_dir):
    """Test that project metadata supports Unicode characters."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    project_data = {
        "name": "游戏项目",  # Chinese characters
        "path": str(project_path),
        "description": "Un jeu vidéo génial",  # French with accents
        "genres": ["アクション"],  # Japanese
        "elements": ["Приключения"],  # Russian
    }

    success = create_project_metadata(project_data)
    assert success is True

    # Verify Unicode was preserved
    metadata_path = project_path / "project.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    assert metadata["name"] == "游戏项目"
    assert metadata["description"] == "Un jeu vidéo génial"
    assert metadata["genres"] == ["アクション"]
    assert metadata["elements"] == ["Приключения"]


def test_validate_project_structure_nonexistent_path(tmp_path):
    """Test validation of a non-existent project path."""
    nonexistent_path = tmp_path / "does_not_exist"

    results = validate_project_structure(nonexistent_path)

    # All should be False
    for directory in PROJECT_DIRECTORIES:
        assert results[directory] is False

    assert results["project.json"] is False


def test_repair_project_structure_creates_parent_dirs(tmp_path):
    """Test that repair creates parent directories if needed."""
    project_path = tmp_path / "parent" / "child" / "project"

    # Don't create the directory first
    success = repair_project_structure(project_path)

    # Should still succeed and create all necessary directories
    assert success is True
    assert project_path.exists()

    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        assert dir_path.exists()

