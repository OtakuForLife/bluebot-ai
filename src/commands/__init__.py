from dataclasses import dataclass
from typing import Any, Callable, Type, TypeVar
from src.project.tasks import AgentTask
from src.project.files import NewProjectData


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""
    pass

T = TypeVar("T", bound=Command)


@dataclass(frozen=True)
class CreateProjectCommand(Command):
    payload: NewProjectData

@dataclass(frozen=True)
class CreateTaskCommand(Command):
    payload: AgentTask

@dataclass(frozen=True)
class ApproveTaskCommand(Command):
    task_id: str

@dataclass(frozen=True)
class RejectTaskCommand(Command):
    task_id: str

class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[Type[Command], Callable[[Any], None]] = {}

    def register(self, command_type: Type[T], handler: Callable[[T], None]) -> None:
        self._handlers[command_type] = handler

    def dispatch(self, command: Command) -> None:
        handler = self._handlers.get(type(command))
        if not handler:
            raise RuntimeError(f"No handler registered for command: {type(command).__name__}")
        handler(command)