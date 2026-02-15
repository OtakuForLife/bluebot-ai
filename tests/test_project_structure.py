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
    write_project_file,
    read_project_file,
    delete_project_file,
    file_exists,
    PROJECT_DIRECTORIES,
    DESIGN_DIR,
    VISION_DOCUMENT_FILE,
    PROJECT_METADATA_FILE,
    GRAPHICS_DIR,
    AUDIO_DIR,
    SCRIPTS_DIR,
    SCENES_DIR,
    ASSETS_DIR,
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
    metadata_path = project_path / PROJECT_METADATA_FILE
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
    
    metadata_path = project_path / PROJECT_METADATA_FILE
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
    
    metadata_path = project_path / PROJECT_METADATA_FILE
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
    assert results[PROJECT_METADATA_FILE] is True


def test_validate_project_structure_incomplete(temp_project_dir):
    """Test validation of an incomplete project structure."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create only some directories
    (project_path / SCRIPTS_DIR).mkdir(exist_ok=True)
    (project_path / SCENES_DIR).mkdir(exist_ok=True)

    results = validate_project_structure(project_path)

    # Only created directories should exist
    assert results[SCRIPTS_DIR] is True
    assert results[SCENES_DIR] is True

    # Missing directories should not exist
    assert results[DESIGN_DIR] is False
    assert results[PROJECT_METADATA_FILE] is False


def test_validate_project_structure_empty(temp_project_dir):
    """Test validation of an empty project directory."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    results = validate_project_structure(project_path)

    # All directories should not exist
    for directory in PROJECT_DIRECTORIES:
        assert results[directory] is False

    assert results[PROJECT_METADATA_FILE] is False


def test_repair_project_structure_success(temp_project_dir):
    """Test successful repair of missing project directories."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create only some directories
    (project_path / SCRIPTS_DIR).mkdir(exist_ok=True)
    (project_path / SCENES_DIR).mkdir(exist_ok=True)

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
    metadata_path = project_path / PROJECT_METADATA_FILE
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

    assert results[PROJECT_METADATA_FILE] is False


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


# ============================================================================
# File Writing Utilities Tests
# ============================================================================


def test_write_project_file_success(temp_project_dir):
    """Test successful file writing to project directory."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    content = "# Test Document\n\nThis is a test."
    success = write_project_file(project_path, "design/test.md", content)

    assert success is True

    # Verify file was created
    file_path = project_path / "design" / "test.md"
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == content


def test_write_project_file_creates_parent_dirs(temp_project_dir):
    """Test that write_project_file creates parent directories."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Write to nested path that doesn't exist yet
    content = "Test content"
    success = write_project_file(
        project_path,
        "design/mechanics/combat.md",
        content
    )

    assert success is True

    # Verify nested directories were created
    file_path = project_path / "design" / "mechanics" / "combat.md"
    assert file_path.exists()
    assert file_path.parent.exists()


def test_write_project_file_unicode_content(temp_project_dir):
    """Test writing Unicode content to project file."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    content = "# 游戏设计\n\n这是一个测试。\n\nアクション: Приключения"
    success = write_project_file(project_path, "design/unicode.md", content)

    assert success is True

    # Verify Unicode was preserved
    file_path = project_path / "design" / "unicode.md"
    assert file_path.read_text(encoding="utf-8") == content


def test_read_project_file_success(temp_project_dir):
    """Test successful file reading from project directory."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create a file first
    content = "# Test Content\n\nReading test."
    file_path = project_path / "design" / "test.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    # Read it back
    read_content = read_project_file(project_path, "design/test.md")

    assert read_content == content


def test_read_project_file_nonexistent(temp_project_dir):
    """Test reading a non-existent file returns None."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    content = read_project_file(project_path, "design/nonexistent.md")

    assert content is None


def test_delete_project_file_success(temp_project_dir):
    """Test successful file deletion from project directory."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create a file first
    file_path = project_path / "design" / "to_delete.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Delete me", encoding="utf-8")

    assert file_path.exists()

    # Delete it
    success = delete_project_file(project_path, "design/to_delete.md")

    assert success is True
    assert not file_path.exists()


def test_delete_project_file_nonexistent(temp_project_dir):
    """Test deleting a non-existent file returns True."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Should succeed even if file doesn't exist
    success = delete_project_file(project_path, "design/nonexistent.md")

    assert success is True


def test_file_exists_true(temp_project_dir):
    """Test file_exists returns True for existing file."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create a file
    file_path = project_path / "design" / "exists.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("I exist", encoding="utf-8")

    assert file_exists(project_path, "design/exists.md") is True


def test_file_exists_false(temp_project_dir):
    """Test file_exists returns False for non-existent file."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    assert file_exists(project_path, "design/nonexistent.md") is False


def test_file_exists_directory(temp_project_dir):
    """Test file_exists returns False for directories."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    # Create a directory
    dir_path = project_path / "design"
    dir_path.mkdir(parents=True, exist_ok=True)

    # Should return False because it's a directory, not a file
    assert file_exists(project_path, "design") is False


def test_write_and_read_roundtrip(temp_project_dir):
    """Test writing and reading a file in a roundtrip."""
    project_path = temp_project_dir
    project_path.mkdir(parents=True, exist_ok=True)

    original_content = "# Vision Document\n\n## Overview\n\nThis is the game vision."

    # Write
    write_success = write_project_file(
        project_path,
        f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}",
        original_content
    )
    assert write_success is True

    # Read
    read_content = read_project_file(project_path, f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}")
    assert read_content == original_content

    # Check existence
    assert file_exists(project_path, f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}") is True

    # Delete
    delete_success = delete_project_file(project_path, f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}")
    assert delete_success is True

    # Verify deleted
    assert file_exists(project_path, f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}") is False

