

from src.commands import CreateProjectCommand, CreateTaskCommand
from src.project.files import FileManager
from src.project.manager import ProjectManager


class CommandExecutor:
    def __init__(self, project_manager: ProjectManager, file_manager: FileManager):
        self.project_manager = project_manager
        self.file_manager = file_manager

    def handle_create_project(self, command: CreateProjectCommand) -> None:
        self.file_manager.create_project_structure(command.payload)

    def handle_create_task(self, command: CreateTaskCommand) -> None:
        self.project_manager.add_task(command.payload)