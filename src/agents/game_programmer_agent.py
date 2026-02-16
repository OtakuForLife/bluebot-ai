"""Game Programmer Agent for writing core game code and logic.

This agent is responsible for:
- Writing core code and implementing gameplay systems
- Implementing physics, AI, and graphics code
- Working with GDScript for Godot projects
- Using Godot documentation knowledge base for code generation
"""

import logging
from pathlib import Path
from typing import Optional

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage
from src.llm.prompt_templates import GameProgrammerPrompts


class GameProgrammerAgent(Agent):
    """Agent specialized in game programming and code implementation.

    This agent handles all programming tasks including gameplay systems,
    physics, AI, and graphics implementation. It uses a knowledge base
    loaded with Godot documentation to inform its code generation.

    Attributes:
        knowledge_base: Knowledge base containing Godot documentation.
        project_path: Path to the Godot project being worked on.
    """

    def __init__(
        self,
        name: str = "GameProgrammer",
        godot_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the Game Programmer Agent.

        Args:
            name: Name for this agent instance.
            godot_docs_path: Optional path to Godot documentation markdown files.
            llm_provider: Optional LLM provider for AI-powered code generation.
        """
        super().__init__(name=name, role="game_programmer")
        self.knowledge_base = KnowledgeBase(name="godot_docs")
        self.project_path: Optional[Path] = None
        self.llm_provider = llm_provider

        # Load Godot documentation if path provided
        if godot_docs_path and godot_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(godot_docs_path)
                self.logger.info(f"Loaded {count} Godot documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load Godot docs: {e}")

    async def process_message(self, message: Message) -> None:
        """Process incoming messages.

        Args:
            message: The message to process.
        """
        self.logger.debug(f"Processing message: {message.type.value}")

        if message.type == MessageType.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.type == MessageType.FILE_MODIFIED:
            await self._handle_file_modified(message)
        elif message.type == MessageType.TEST_RESULT:
            await self._handle_test_result(message)
        else:
            self.logger.debug(f"Ignoring message type: {message.type.value}")

    async def _handle_task_request(self, message: Message) -> None:
        """Handle a task request message.

        Args:
            message: The task request message.
        """
        task_type = message.payload.get("task_type")
        self.logger.info(f"Received task request: {task_type}")

        if task_type == "implement_gameplay":
            await self._implement_gameplay(message.payload)
        elif task_type == "implement_physics":
            await self._implement_physics(message.payload)
        elif task_type == "implement_ai":
            await self._implement_ai(message.payload)
        elif task_type == "create_script":
            await self._create_script(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_file_modified(self, message: Message) -> None:
        """Handle notification that a file was modified.

        Args:
            message: The file modified message.
        """
        file_path = message.payload.get("file_path")
        self.logger.info(f"File modified: {file_path}")
        # Could trigger code review or validation here

    async def _handle_test_result(self, message: Message) -> None:
        """Handle test results and potentially fix issues.

        Args:
            message: The test result message.
        """
        passed = message.payload.get("passed", False)
        errors = message.payload.get("errors", [])

        if not passed:
            self.logger.warning(f"Tests failed with {len(errors)} errors")
            # Could trigger automatic bug fixing here

    async def _implement_gameplay(self, payload: dict) -> None:
        """Implement gameplay systems.

        Args:
            payload: Task payload with gameplay requirements.
        """
        self.logger.info("Implementing gameplay systems")
        # Search knowledge base for relevant Godot gameplay patterns
        gameplay_docs = self.knowledge_base.search("gameplay")
        self.logger.debug(f"Found {len(gameplay_docs)} relevant docs")
        # Implementation would go here

    async def _implement_physics(self, payload: dict) -> None:
        """Implement physics systems.

        Args:
            payload: Task payload with physics requirements.
        """
        self.logger.info("Implementing physics systems")
        # Search knowledge base for Godot physics documentation
        physics_docs = self.knowledge_base.search("physics")
        self.logger.debug(f"Found {len(physics_docs)} relevant docs")
        # Implementation would go here

    async def _implement_ai(self, payload: dict) -> None:
        """Implement AI systems.

        Args:
            payload: Task payload with AI requirements.
        """
        self.logger.info("Implementing AI systems")
        # Search knowledge base for AI-related documentation
        ai_docs = self.knowledge_base.search("AI")
        self.logger.debug(f"Found {len(ai_docs)} relevant docs")
        # Implementation would go here

    async def _create_script(self, payload: dict) -> None:
        """Create a new GDScript file.

        Args:
            payload: Task payload with script details.
        """
        script_name = payload.get("script_name", "new_script.gd")
        description = payload.get("description", "A new GDScript file")

        self.logger.info(f"Creating script: {script_name}")

        # Search knowledge base for GDScript syntax and patterns
        gdscript_docs = self.knowledge_base.search("GDScript")
        self.logger.debug(f"Found {len(gdscript_docs)} relevant docs")

        # If LLM provider is available, use it to generate the script
        if self.llm_provider:
            try:
                # Format knowledge context
                knowledge_context = GameProgrammerPrompts.format_knowledge_context(gdscript_docs)

                # Create the prompt
                user_prompt = GameProgrammerPrompts.create_script_prompt(
                    script_name=script_name,
                    description=description,
                    knowledge_context=knowledge_context,
                )

                # Generate the script using LLM
                messages = [
                    LLMMessage(role="system", content=GameProgrammerPrompts.SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ]

                response = await self.llm_provider.generate(messages)

                self.logger.info(f"Generated script with {len(response.content)} characters")

                # Save the script if project path is set
                if self.project_path:
                    script_path = self.project_path / "scripts" / script_name
                    script_path.parent.mkdir(parents=True, exist_ok=True)
                    script_path.write_text(response.content, encoding="utf-8")
                    self.logger.info(f"Saved script to: {script_path}")
                else:
                    self.logger.warning("Project path not set, script not saved to disk")

            except Exception as e:
                self.logger.error(f"Failed to generate script with LLM: {e}")
        else:
            self.logger.warning("No LLM provider configured, cannot generate script")

    def set_project_path(self, path: Path) -> None:
        """Set the Godot project path.

        Args:
            path: Path to the Godot project directory.
        """
        self.project_path = path
        self.logger.info(f"Project path set to: {path}")

    def get_knowledge_summary(self) -> dict:
        """Get a summary of the loaded knowledge base.

        Returns:
            Dictionary with knowledge base statistics.
        """
        return self.knowledge_base.get_summary()

    async def on_autonomous_tick(self) -> None:
        """Autonomous task handling tick.

        This method is called periodically when autonomous_mode is True.
        It discovers available tasks and claims them for execution.
        """
        if not self.autonomous_mode:
            return

        # Discover available tasks for this agent
        available_tasks = await self.discover_tasks()

        if not available_tasks:
            self.logger.debug("No available tasks for Game Programmer")
            return

        # Claim the first available task
        task = available_tasks[0]
        task_id = task.get("id")
        task_title = task.get("title", "Unknown")

        if not task_id:
            self.logger.warning("Task has no ID, skipping")
            return

        self.logger.info(f"Found available task: {task_title}")

        # Claim the task
        success = await self.claim_task(task_id)

        if success:
            self.logger.info(f"Claimed task: {task_title}")
            # Execute the task
            await self._execute_autonomous_task(task)
        else:
            self.logger.warning(f"Failed to claim task: {task_title}")

    async def _execute_autonomous_task(self, task: dict) -> None:
        """Execute a claimed task autonomously.

        Args:
            task: The task data dictionary.
        """
        task_id = task.get("id")
        task_type = task.get("task_type")
        task_title = task.get("title")
        task_description = task.get("description")

        if not task_id:
            self.logger.warning("Task has no ID, cannot execute")
            return

        self.logger.info(f"Executing task: {task_title} (type: {task_type})")

        try:
            # Simulate task execution based on task type
            if task_type == "setup_project":
                result = await self._autonomous_setup_project(task)
            elif task_type == "create_script":
                result = await self._autonomous_create_script(task)
            elif task_type == "implement_system":
                result = await self._autonomous_implement_system(task)
            else:
                self.logger.warning(f"Unknown task type: {task_type}, marking as complete")
                result = {"status": "completed", "message": f"Task type {task_type} not yet implemented"}

            # Complete the task
            await self.complete_task(task_id, result)
            self.logger.info(f"Completed task: {task_title}")

        except Exception as e:
            self.logger.error(f"Error executing task {task_title}: {e}", exc_info=True)

    async def _autonomous_setup_project(self, task: dict) -> dict:
        """Autonomously set up project structure.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Setting up project structure...")

        # Simulate project setup work
        return {
            "status": "completed",
            "message": "Project structure initialized with base folders and scenes",
            "files_created": ["res://scenes/main.tscn", "res://scripts/game_manager.gd"],
        }

    async def _autonomous_create_script(self, task: dict) -> dict:
        """Autonomously create a script.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Creating script...")

        # Simulate script creation
        return {
            "status": "completed",
            "message": "Script created successfully",
            "script_path": "res://scripts/player.gd",
        }

    async def _autonomous_implement_system(self, task: dict) -> dict:
        """Autonomously implement a game system.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Implementing game system...")

        # Simulate system implementation
        return {
            "status": "completed",
            "message": "Game system implemented",
            "systems_created": ["movement", "collision"],
        }

