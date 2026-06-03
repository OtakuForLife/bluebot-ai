"""Tests for CommandExecutor class."""

from datetime import datetime

import pytest

from src.agents.roles import AgentRole
from src.commands import CreateProjectCommand, CreateTaskCommand
from src.commands.execution import CommandExecutor
from src.project.files import FileManager
from src.project.manager import ProjectManager
from src.events import EventHandler
from src.project.tasks import AgentTask, TaskStatus


def test_command_executor_initialization() -> None:
    """Test that CommandExecutor initializes correctly."""
    event_handler = EventHandler()
    project_manager = ProjectManager(
        event_handler=event_handler
    )
    file_manager = FileManager(event_handler)

    executor = CommandExecutor(project_manager, file_manager)

    assert executor.project_manager == project_manager
    assert executor.file_manager == file_manager


def test_command_executor_handle_create_project(tmp_path) -> None:
    """Test handling a CreateProjectCommand."""
    event_handler = EventHandler()
    project_manager = ProjectManager(
        event_handler=event_handler
    )
    file_manager = FileManager(event_handler)

    executor = CommandExecutor(project_manager, file_manager)

    # Create a project
    project_path = tmp_path / "test_project"
    command = CreateProjectCommand({
        "name": "Test Project",
        "path": str(project_path),
        "brief": "",
        "description": "A test project",
        "elements":[],
        "genres":[]
    })

    executor.handle_create_project(command)

    # Verify project structure was created
    assert project_path.exists()
    assert (project_path / "project.json").exists()


def test_command_executor_handle_create_task(tmp_path) -> None:
    """Test handling a CreateTaskCommand."""
    event_handler = EventHandler()
    project_manager = ProjectManager(
        event_handler=event_handler
    )
    file_manager = FileManager(event_handler)

    executor = CommandExecutor(project_manager, file_manager)

    # Create a task
    task_data: AgentTask = {
        "id": "task-1",
        "title": "Test Task",
        "description": "A test task",
        "status": TaskStatus.OPEN,
        "completed_at":datetime.now(),
        "created_at":datetime.now(),
        "created_by":"",
        "requires_review":True,
        "type":AgentRole.GAME_DESIGNER
    }
    command = CreateTaskCommand(task_data)

    executor.handle_create_task(command)

    # Verify task was added
    tasks = project_manager.get_tasks()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Test Task"
    assert tasks[0]["status"] == TaskStatus.OPEN


def test_command_executor_handles_multiple_tasks(tmp_path) -> None:
    """Test handling multiple CreateTaskCommands."""
    event_handler = EventHandler()
    project_manager = ProjectManager(
        event_handler=event_handler
    )
    file_manager = FileManager(event_handler)

    executor = CommandExecutor(project_manager, file_manager)

    # Create multiple tasks
    for i in range(3):
        task_data: AgentTask = {
            "id": f"task-{i}",
            "title": f"Task {i}",
            "description": f"Test task {i}",
            "status": TaskStatus.OPEN,
            "completed_at":datetime.now(),
            "created_at":datetime.now(),
            "created_by":"",
            "requires_review":True,
            "type":AgentRole.GAME_DESIGNER
        }
        command = CreateTaskCommand(task_data)
        executor.handle_create_task(command)

    # Verify all tasks were added
    tasks = project_manager.get_tasks()
    assert len(tasks) == 3
