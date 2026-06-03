"""Centralized project structure management utilities.

This module provides a single source of truth for creating and managing
project directory structures and metadata files.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, TypedDict

from src.events import EventHandler

logger = logging.getLogger(__name__)

class NewProjectData(TypedDict):
    path: str
    name: str
    description: str
    brief: str
    genres: list[str]
    elements: list[str]

class FileManager:

    """ideal project folder structure 
    design
        VISION.md
        MECHANICS.md
        STORY.md
        UX.md
        GRAPHICS.md
        AUDIO.md
    assets
        graphics
        audio
        texts
    game
        project.godot
    project.json
    tasks.json
    """

    # Standard project directory constants
    SCRIPTS_DIR = "game"
    ASSETS_DIR = "assets"
    GRAPHICS_DIR = "assets/graphics"
    AUDIO_DIR = "assets/audio"
    DESIGN_DIR = "design"

    PROJECT_DIRECTORIES = [
        SCRIPTS_DIR,
        ASSETS_DIR,
        GRAPHICS_DIR,
        AUDIO_DIR,
        DESIGN_DIR,
    ]

    # Standard project file constants
    PROJECT_METADATA_FILE = "project.json"
    TASKS_FILE = "tasks.json"
    AGENTS_CONFIG = "agents.config"

    def __init__(self, event_handler: EventHandler) -> None:
        self.event_handler = event_handler

    def create_project_structure(self, project_data: NewProjectData) -> bool:
        try:
            project_path = Path(project_data["path"])
            
            # Create main project directory
            project_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created project directory: {project_path}")
            
            # Create all subdirectories
            for directory in FileManager.PROJECT_DIRECTORIES:
                dir_path = project_path / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created subdirectory: {dir_path}")
            
            # Create project metadata file
            self.create_project_metadata(project_data)
            
            logger.info(f"Successfully created project structure at: {project_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create project structure: {e}", exc_info=True)
            return False


    def create_project_metadata(self, project_data: NewProjectData) -> bool:
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
                "brief": project_data.get("brief", ""),
                "genres": project_data.get("genres", []),
                "elements": project_data.get("elements", []),
            }
            
            metadata_path = project_path / self.PROJECT_METADATA_FILE
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created project metadata: {metadata_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create project metadata: {e}", exc_info=True)
            return False



    def validate_project_structure(self, project_path: Path) -> dict[str, bool]:
        """Validate that a project has the expected directory structure.
        
        Args:
            project_path: Path to the project directory.
        
        Returns:
            Dictionary mapping directory names to existence status.
        """
        validation_results = {}
        
        for directory in FileManager.PROJECT_DIRECTORIES:
            dir_path = project_path / directory
            validation_results[directory] = dir_path.exists()
        
        # Check for project.json
        validation_results[FileManager.PROJECT_METADATA_FILE] = (
            project_path / FileManager.PROJECT_METADATA_FILE
        ).exists()
        
        return validation_results

    def create_file(self, path: str, content: str, project_root: Optional[str] = None) -> str:
        """Create a new file with the given content.

        Args:
            path: Relative path to the file to create.
            content: Content to write to the file.
            project_root: Optional project root directory.

        Returns:
            Success message or error description.
        """
        try:
            file_path = Path(project_root) / path if project_root else Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then atomic rename for safety
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=file_path.suffix,
                prefix=file_path.stem + '.tmp_',
                dir=file_path.parent,
                encoding="utf-8",
                delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
            tmp_path.replace(file_path)
            return f"Successfully created file: {path}"
        except Exception as e:
            return f"Error creating file {path}: {str(e)}"

    def write_project_file(self, project_path: Path, relative_path: str, content: str, encoding: str = "utf-8") -> bool:
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

            # Write to temp file first, then atomic rename for safety
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=file_path.suffix,
                prefix=file_path.stem + '.tmp_',
                dir=file_path.parent,
                encoding=encoding,
                delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
            tmp_path.replace(file_path)

            logger.info(f"Wrote file to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file {relative_path}: {e}", exc_info=True)
            return False


    def read_project_file(self, project_path: Path, relative_path: str, encoding: str = "utf-8") -> Optional[str]:
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

    def file_exists(self, project_path: Path, relative_path: str) -> bool:
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