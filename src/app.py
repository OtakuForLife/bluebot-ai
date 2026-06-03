"""Application entrypoint for Bluebot AI desktop application.

This module wires together GUI, agent system, and Godot integration.
"""

from __future__ import annotations

import logging
import sys

from src.agents.config import AgentConfig
from src.agents.graph import (
    WorkflowSpec, DirectEdge, build_capabilities_map,
    create_task_dispatcher, create_workflow_spec,
)
from src.agents.orchestrator import AgentOrchestrator, human_review_node
from src.agents.services import TaskDispatchService, ProducerService
from src.agents.llm import LLMConfig, OllamaProvider
from src.agents.llm.tool import AgentTool
from src.commands import CommandBus, CreateProjectCommand, CreateTaskCommand
from src.commands.execution import CommandExecutor
from src.events import EventHandler, EventType
from src.project.files import FileManager
from src.project.manager import ProjectManager
from src.ui.logging_handler import LoggingBridge
from src.ui.bridge import QtCommandBridge, QtEventBridge
from src.agents.llm.prompt_templates import (
    GAME_ARTIST_SYSTEM_PROMPT,
    GAME_DESIGNER_SYSTEM_PROMPT,
    GAME_PROGRAMMER_SYSTEM_PROMPT,
    PROJECT_DIRECTOR_SYSTEM_PROMPT,
    DISCOVERY_SYSTEM_PROMPT,
)
from src.agents.llm.tools import (
    _create_assign_task_tool,
    _create_file_tool,
    _create_list_files_tool,
    _create_list_tasks_tool,
    _create_read_file_tool,
    _create_set_direction_tool,
)



def setup_logging() -> None:
    """Set up application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def setup_tracing() -> None:
    """Start Arize Phoenix local tracing UI and configure the OTel exporter.

    Phoenix runs entirely on-device at http://localhost:6006.
    No API key or internet connection required.
    Safe to call even if arize-phoenix is not installed — tracing is simply skipped.
    """
    # Phoenix uses Strawberry for its internal GraphQL API. During startup it can
    # emit a benign "Cannot return null for non-nullable field Project.name" error
    # while its own DB initialises. Silence that logger so it doesn't pollute ours.
    logging.getLogger("strawberry.execution").setLevel(logging.CRITICAL)

    try:
        import phoenix as px
        from phoenix.otel import register
        px.launch_app()
        register(project_name="bluebot-ai")
        logging.getLogger(__name__).info(
            "Phoenix tracing started — open http://localhost:6006 to inspect LLM calls"
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "arize-phoenix not installed — LLM tracing disabled"
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(
            f"Phoenix tracing could not start ({exc}) — LLM tracing disabled"
        )



def _create_agents(
    event_handler: EventHandler,
    llm_config: LLMConfig,
    file_tool: AgentTool,
    list_files_tool: AgentTool,
    read_file_tool: AgentTool,
    assign_task_tool: AgentTool,
    list_tasks_tool: AgentTool,
    set_direction_tool: AgentTool,
) -> dict:
    """Create all agents for the application."""
    from src.agents.base import Agent, AgentRole

    # Workers can create and read files.
    worker_tools = [file_tool, read_file_tool, list_files_tool]

    return {
        "project_director": Agent(
            name="project_director",
            role=AgentRole.PROJECT_DIRECTOR,
            config=AgentConfig(
                event_handler=event_handler,
                llm_config=llm_config,
                knowledge_path="production/",
                # Director reads the project and sets strategic direction via
                # set_direction — it never creates tasks directly.
                tools=[list_files_tool, read_file_tool, list_tasks_tool, set_direction_tool],
                system_prompt=PROJECT_DIRECTOR_SYSTEM_PROMPT,
                capabilities=[],
            ),
        ),
        "discovery_agent": Agent(
            name="discovery_agent",
            role=AgentRole.DISCOVERY,
            config=AgentConfig(
                event_handler=event_handler,
                llm_config=llm_config,
                knowledge_path="production/",
                # Discovery reads the Director's directive and creates the task.
                tools=[list_files_tool, read_file_tool, list_tasks_tool, assign_task_tool],
                system_prompt=DISCOVERY_SYSTEM_PROMPT,
                capabilities=[],
            ),
        ),
        "game_designer": Agent(
            name="game_designer",
            role=AgentRole.GAME_DESIGNER,
            config=AgentConfig(
                event_handler=event_handler,
                llm_config=llm_config,
                knowledge_path="game_design/",
                tools=worker_tools,
                system_prompt=GAME_DESIGNER_SYSTEM_PROMPT,
                capabilities=["design"],
            ),
        ),
        "game_developer": Agent(
            name="game_developer",
            role=AgentRole.GAME_PROGRAMMER,
            config=AgentConfig(
                event_handler=event_handler,
                llm_config=llm_config,
                knowledge_path="programming/",
                tools=worker_tools,
                system_prompt=GAME_PROGRAMMER_SYSTEM_PROMPT,
                capabilities=["gameplay", "systems"],
            ),
        ),
        "game_artist": Agent(
            name="game_artist",
            role=AgentRole.GAME_ARTIST,
            config=AgentConfig(
                event_handler=event_handler,
                llm_config=llm_config,
                knowledge_path="art/",
                tools=worker_tools,
                system_prompt=GAME_ARTIST_SYSTEM_PROMPT,
                capabilities=["art"],
            ),
        ),
    }




def _load_persisted_tasks(
    project_manager: ProjectManager,
    selected_project: dict,
    logger: "logging.Logger",
) -> None:
    """Read tasks.json from the selected project and pre-populate ProjectManager.

    This must run before any agent starts so the duplicate guard in assign_task
    has visibility of tasks created in previous sessions.  Errors are logged
    as warnings; a missing or malformed tasks.json is treated as an empty list.
    """
    import json
    from pathlib import Path

    tasks_file = Path(selected_project.get("path", ".")) / "tasks.json"
    if not tasks_file.exists():
        return

    try:
        data = json.loads(tasks_file.read_text(encoding="utf-8"))
        tasks: list[dict] = data.get("tasks", data) if isinstance(data, dict) else data
        if isinstance(tasks, list):
            project_manager.load_tasks(tasks)
            logger.info(f"Pre-loaded {len(tasks)} persisted task(s) from {tasks_file}")
        else:
            logger.warning(f"Unexpected tasks.json format in {tasks_file} — skipping pre-load")
    except Exception as exc:
        logger.warning(f"Could not pre-load tasks from {tasks_file}: {exc}")


def _setup_components() -> tuple:
    """Set up core application components.

    Returns:
        Tuple of (event_handler, command_bus, project_manager, file_manager,
                 llm_provider, command_executor).
    """
    event_handler = EventHandler()
    command_bus = CommandBus()

    project_manager = ProjectManager(event_handler)
    file_manager = FileManager(event_handler)

    llm_config = LLMConfig(model="qwen3-vl:8b",
                          temperature=0.7, max_tokens=4096)
    llm_provider = OllamaProvider(llm_config)

    command_executor = CommandExecutor(project_manager, file_manager)
    

    return (event_handler, command_bus, project_manager,
            file_manager, llm_provider, command_executor)


def _setup_bridges(event_handler: EventHandler, command_bus: CommandBus) -> tuple:
    """Set up Qt bridges for UI-backend communication.

    Args:
        event_handler: Event handler to bridge to Qt.
        command_bus: Command bus to bridge to Qt.

    Returns:
        Tuple of (qt_event_bridge, qt_command_bridge, qt_log_handler).
    """
    qt_event_bridge = QtEventBridge(event_handler)
    qt_command_bridge = QtCommandBridge(command_bus)
    logging_bridge = LoggingBridge()
    qt_log_handler = logging_bridge.create_handler(level=logging.DEBUG)
    logging_bridge.attach_to_root()

    return qt_event_bridge, qt_command_bridge, qt_log_handler


def _select_project(qt_command_bridge, logger):
    """Show project selection dialog and get selected project.

    Args:
        qt_command_bridge: Command bridge for the selection window.
        logger: Logger instance.

    Returns:
        Selected project dict or None.
    """
    from PySide6.QtWidgets import QDialog
    from src.ui.project_selection_window import ProjectSelectionWindow

    project_selection = ProjectSelectionWindow(qt_command_bridge)
    if project_selection.exec() != QDialog.DialogCode.Accepted:
        logger.info("No project selected, exiting application")
        return None

    selected_project = project_selection.get_selected_project()
    if not selected_project:
        logger.info("No project selected, exiting application")
        return None

    logger.info(f"Project selected: {selected_project.get('name')}")
    return selected_project


def main() -> int:
    """Start Bluebot AI desktop application.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    setup_logging()
    setup_tracing()
    logger = logging.getLogger(__name__)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is not installed. Install 'PySide6' package to run the GUI.",
        )
        return 1

    try:
        from src.ui.main_window import MainWindow

        logger.info("Starting Bluebot AI application...")

        # Set up core components
        (event_handler, command_bus, project_manager,
         file_manager, llm_provider, command_executor) = _setup_components()
        
        command_bus.register(CreateTaskCommand, command_executor.handle_create_task)
        command_bus.register(CreateProjectCommand,
                        command_executor.handle_create_project)

        # Create agents and orchestrator
        file_tool = _create_file_tool(file_manager)
        list_files_tool = _create_list_files_tool()
        read_file_tool = _create_read_file_tool()
        list_tasks_tool = _create_list_tasks_tool(project_manager)
        set_direction_tool = _create_set_direction_tool()
        assign_task_tool = _create_assign_task_tool(event_handler, project_manager)
        agents = _create_agents(
            event_handler,
            llm_provider.config,
            file_tool,
            list_files_tool,
            read_file_tool,
            assign_task_tool,
            list_tasks_tool,
            set_direction_tool,
        )

        # Build capability map from agent metadata — no hardcoded route dict.
        capabilities_map = build_capabilities_map(agents)

        # task_dispatcher is a plain callable node; it queries the marketplace
        # and claims the next open task before the CapabilityEdge routes it.
        task_dispatcher = create_task_dispatcher(project_manager, capabilities_map)

        spec = create_workflow_spec(
            producer_name=agents["project_director"].name,
            dispatcher_name="task_dispatcher",
            capabilities_map=capabilities_map,
        )

        # Explicit producer chain: Project Director analyses the project and
        # sets strategic direction; Discovery Agent reads that direction and
        # creates the specific task in the marketplace.
        producer_spec = WorkflowSpec(
            entry_point="project_director",
            edges=[DirectEdge(source="project_director", target="discovery_agent")],
        )

        nodes = {
            **agents,
            "task_dispatcher": task_dispatcher,
            "human_review": human_review_node,
        }
        agent_orchestrator = AgentOrchestrator(
            event_handler, nodes=nodes, spec=spec, producer_spec=producer_spec)

        # Wire event-driven services
        # TaskDispatchService reacts to TASK_CREATED → runs specialist + review graph
        # ProducerService reacts to TASK_COMPLETED → re-runs Producer for more tasks
        task_dispatch_service = TaskDispatchService(project_manager, agent_orchestrator)
        producer_service = ProducerService(agent_orchestrator)
        event_handler.subscribe_async(
            EventType.TASK_CREATED, task_dispatch_service.on_task_created
        )
        event_handler.subscribe_async(
            EventType.TASK_COMPLETED, producer_service.on_task_completed
        )

        # Set up bridges
        qt_event_bridge, qt_command_bridge, qt_log_handler = _setup_bridges(
            event_handler, command_bus)

        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Bluebot AI")
        app.setOrganizationName("Bluebot")

        # Select project
        selected_project = _select_project(qt_command_bridge, logger)
        if not selected_project:
            return 0

        # Pre-load persisted tasks so the duplicate guard in assign_task sees
        # tasks created in previous sessions before any agent runs.
        _load_persisted_tasks(project_manager, selected_project, logger)

        # Create and show main window
        window = MainWindow(
            qt_event_bridge, qt_command_bridge,
            qt_log_handler, agent_orchestrator, selected_project
        )
        window.show()

        logger.info("Application started successfully")

        # Run event loop
        return app.exec()

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1
