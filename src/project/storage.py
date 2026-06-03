"""Utilities for loading and saving the project registry (projects.json)."""

import json
import logging
from pathlib import Path
from typing import Any


def load_projects_file(projects_file: Path, logger: logging.Logger) -> list[dict[str, Any]]:
    """Load projects from the projects.json file.

    Args:
        projects_file: Path to the projects.json file.
        logger: Logger instance for error/info messages.

    Returns:
        List of project dictionaries. Empty list if file doesn't exist or error occurs.
    """
    if projects_file.exists():
        try:
            with open(projects_file, 'r', encoding='utf-8') as f:
                projects = json.load(f)
            logger.info(f"Loaded {len(projects)} projects")
            return projects
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            return []
    else:
        logger.info("No projects file found, starting with empty list")
        return []


def save_projects_file(projects: list[dict[str, Any]], projects_file: Path, logger: logging.Logger) -> bool:
    """Save projects to the projects.json file.

    Args:
        projects: List of project dictionaries.
        projects_file: Path to the projects.json file.
        logger: Logger instance for error/info messages.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Create parent directory if it doesn't exist
        projects_file.parent.mkdir(parents=True, exist_ok=True)
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(projects)} projects")
        return True
    except Exception as e:
        logger.error(f"Failed to save projects: {e}")
        return False
