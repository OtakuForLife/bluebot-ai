"""Centralized project structure management utilities.

This module provides a single source of truth for creating and managing
project directory structures and metadata files.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Standard project directory structure
PROJECT_DIRECTORIES = [
    "scripts",
    "scenes",
    "assets",
    "assets/sprites",
    "assets/models",
    "assets/audio",
    "design",
    "docs",
]


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
        
        metadata_path = project_path / "project.json"
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
    validation_results["project.json"] = (project_path / "project.json").exists()
    
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

