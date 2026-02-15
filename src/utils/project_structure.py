"""Centralized project structure management utilities.

This module provides a single source of truth for creating and managing
project directory structures and metadata files.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Standard project directory constants
SCRIPTS_DIR = "scripts"
SCENES_DIR = "scenes"
ASSETS_DIR = "assets"
GRAPHICS_DIR = "assets/graphics"
AUDIO_DIR = "assets/audio"
DESIGN_DIR = "design"

PROJECT_DIRECTORIES = [
    SCRIPTS_DIR,
    SCENES_DIR,
    ASSETS_DIR,
    GRAPHICS_DIR,
    AUDIO_DIR,
    DESIGN_DIR,
]

# Standard project file constants
PROJECT_METADATA_FILE = "project.json"
VISION_DOCUMENT_FILE = "VISION.md"


def create_project_structure(project_data: dict) -> bool:
    """Create the standard project directory structure.
    
    This is the central function for creating project directories.
    All project creation should use this function to ensure consistency.
    
    Args:
        project_data: Project data dictionary containing:
            - path: Full path to the project directory
            - name: Project name
            - description: Project description
            - genres: List of game genres
            - elements: List of game elements
    
    Returns:
        True if successful, False otherwise.
    
    Raises:
        ValueError: If project_data is missing required fields.
    """
    # Validate required fields
    if "path" not in project_data:
        raise ValueError("project_data must contain 'path' field")
    
    if "name" not in project_data:
        raise ValueError("project_data must contain 'name' field")
    
    try:
        project_path = Path(project_data["path"])
        
        # Create main project directory
        project_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project directory: {project_path}")
        
        # Create all subdirectories
        for directory in PROJECT_DIRECTORIES:
            dir_path = project_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created subdirectory: {dir_path}")
        
        # Create project metadata file
        create_project_metadata(project_data)
        
        logger.info(f"Successfully created project structure at: {project_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create project structure: {e}", exc_info=True)
        return False


def create_project_metadata(project_data: dict) -> bool:
    """Create the project.json metadata file.
    
    Args:
        project_data: Project data dictionary.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        project_path = Path(project_data["path"])
        
        # Create project metadata
        project_info = {
            "name": project_data.get("name", "Unnamed Project"),
            "description": project_data.get("description", ""),
            "genres": project_data.get("genres", []),
            "elements": project_data.get("elements", []),
        }
        
        metadata_path = project_path / PROJECT_METADATA_FILE
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created project metadata: {metadata_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create project metadata: {e}", exc_info=True)
        return False


def get_project_directories() -> list[str]:
    """Get the list of standard project directories.
    
    Returns:
        List of directory paths relative to project root.
    """
    return PROJECT_DIRECTORIES.copy()


def validate_project_structure(project_path: Path) -> dict[str, bool]:
    """Validate that a project has the expected directory structure.
    
    Args:
        project_path: Path to the project directory.
    
    Returns:
        Dictionary mapping directory names to existence status.
    """
    validation_results = {}
    
    for directory in PROJECT_DIRECTORIES:
        dir_path = project_path / directory
        validation_results[directory] = dir_path.exists()
    
    # Check for project.json
    validation_results[PROJECT_METADATA_FILE] = (project_path / PROJECT_METADATA_FILE).exists()
    
    return validation_results


def repair_project_structure(project_path: Path) -> bool:
    """Repair missing directories in a project structure.

    Args:
        project_path: Path to the project directory.

    Returns:
        True if repair was successful, False otherwise.
    """
    try:
        for directory in PROJECT_DIRECTORIES:
            dir_path = project_path / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Repaired missing directory: {dir_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to repair project structure: {e}", exc_info=True)
        return False


def write_project_file(
    project_path: Path,
    relative_path: str,
    content: str,
    encoding: str = "utf-8",
) -> bool:
    """Write a file to a project directory with automatic parent directory creation.

    This is the centralized function for writing files to project directories.
    It automatically creates parent directories if they don't exist.

    Args:
        project_path: Path to the project root directory.
        relative_path: Relative path from project root (e.g., "design/VISION.md").
        content: Content to write to the file.
        encoding: File encoding (default: "utf-8").

    Returns:
        True if successful, False otherwise.

    Example:
        >>> write_project_file(
        ...     Path("/projects/my_game"),
        ...     "design/mechanics.md",
        ...     "# Game Mechanics\\n\\nContent here..."
        ... )
        True
    """
    try:
        file_path = project_path / relative_path

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        file_path.write_text(content, encoding=encoding)

        logger.info(f"Wrote file to: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to write file {relative_path}: {e}", exc_info=True)
        return False


def read_project_file(
    project_path: Path,
    relative_path: str,
    encoding: str = "utf-8",
) -> Optional[str]:
    """Read a file from a project directory.

    Args:
        project_path: Path to the project root directory.
        relative_path: Relative path from project root (e.g., "design/VISION.md").
        encoding: File encoding (default: "utf-8").

    Returns:
        File content as string, or None if file doesn't exist or error occurs.

    Example:
        >>> content = read_project_file(
        ...     Path("/projects/my_game"),
        ...     "design/VISION.md"
        ... )
    """
    try:
        file_path = project_path / relative_path

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None

        content = file_path.read_text(encoding=encoding)
        logger.debug(f"Read file from: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to read file {relative_path}: {e}", exc_info=True)
        return None


def delete_project_file(
    project_path: Path,
    relative_path: str,
) -> bool:
    """Delete a file from a project directory.

    Args:
        project_path: Path to the project root directory.
        relative_path: Relative path from project root (e.g., "design/old_doc.md").

    Returns:
        True if successful or file doesn't exist, False on error.

    Example:
        >>> delete_project_file(
        ...     Path("/projects/my_game"),
        ...     "design/old_doc.md"
        ... )
        True
    """
    try:
        file_path = project_path / relative_path

        if not file_path.exists():
            logger.debug(f"File does not exist (already deleted): {file_path}")
            return True

        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete file {relative_path}: {e}", exc_info=True)
        return False


def file_exists(
    project_path: Path,
    relative_path: str,
) -> bool:
    """Check if a file exists in a project directory.

    Args:
        project_path: Path to the project root directory.
        relative_path: Relative path from project root (e.g., "design/VISION.md").

    Returns:
        True if file exists, False otherwise.

    Example:
        >>> if file_exists(Path("/projects/my_game"), "design/VISION.md"):
        ...     print("Vision file exists!")
    """
    file_path = project_path / relative_path
    return file_path.exists() and file_path.is_file()