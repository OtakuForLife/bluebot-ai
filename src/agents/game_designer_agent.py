"""Game Designer Agent for defining game mechanics and user experience.

This agent is responsible for:
- Defining game mechanics and rules
- Storyboarding and narrative design
- User experience (UX) design
- Game balance and progression systems
"""

import logging
from pathlib import Path
from typing import Optional

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage
from src.llm.prompt_templates import GameDesignerPrompts
from src.utils.project_structure import DESIGN_DIR, VISION_DOCUMENT_FILE, write_project_file


class GameDesignerAgent(Agent):
    """Agent specialized in game design and mechanics.

    This agent handles all game design tasks including mechanics definition,
    storyboarding, UX design, and game balance. It uses a knowledge base
    loaded with game design documentation and best practices.

    Attributes:
        knowledge_base: Knowledge base containing game design documentation.
        project_path: Path to the Godot project being worked on.
        design_documents: Dictionary storing design documents and specifications.
    """

    def __init__(
        self,
        name: str = "GameDesigner",
        design_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the Game Designer Agent.

        Args:
            name: Name for this agent instance.
            design_docs_path: Optional path to game design documentation markdown files.
            llm_provider: Optional LLM provider for AI-powered design document generation.
        """
        super().__init__(name=name, role="game_designer")
        self.knowledge_base = KnowledgeBase(name="game_design_docs")
        self.project_path: Optional[Path] = None
        self.design_documents: dict[str, dict] = {}
        self.llm_provider = llm_provider

        # Load game design documentation if path provided
        if design_docs_path and design_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(design_docs_path)
                self.logger.info(f"Loaded {count} game design documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load design docs: {e}")

    async def process_message(self, message: Message) -> None:
        """Process incoming messages.

        Args:
            message: The message to process.
        """
        self.logger.debug(f"Processing message: {message.type.value}")

        if message.type == MessageType.TASK_REQUEST:
            await self._handle_task_request(message)
        elif message.type == MessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
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

        if task_type == "create_vision":
            await self._create_vision(message.payload)
        elif task_type == "define_mechanics":
            await self._define_mechanics(message.payload)
        elif task_type == "create_storyboard":
            await self._create_storyboard(message.payload)
        elif task_type == "design_ux":
            await self._design_ux(message.payload)
        elif task_type == "balance_gameplay":
            await self._balance_gameplay(message.payload)
        elif task_type == "create_design_doc":
            await self._create_design_document(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status updates from other agents.

        Args:
            message: The status update message.
        """
        agent_role = message.payload.get("role")
        status = message.payload.get("status")
        self.logger.info(f"Status update from {agent_role}: {status}")

    async def _handle_test_result(self, message: Message) -> None:
        """Handle test results and adjust design if needed.

        Args:
            message: The test result message.
        """
        passed = message.payload.get("passed", False)
        balance_issues = message.payload.get("balance_issues", [])

        if balance_issues:
            self.logger.warning(f"Balance issues detected: {len(balance_issues)}")
            # Could trigger automatic rebalancing here

    async def _create_vision(self, payload: dict) -> None:
        """Create a comprehensive game vision document.

        This is the first step after project creation. The vision document
        defines the core concept, target audience, unique selling points,
        and overall direction for the game.

        Args:
            payload: Task payload with project information.
        """
        project_name = payload.get("project_name", "Untitled Game")
        project_description = payload.get("description", "")
        genres = payload.get("genres", [])
        elements = payload.get("elements", [])

        self.logger.info(f"Creating vision document for: {project_name}")

        # Search knowledge base for vision document best practices
        vision_docs = self.knowledge_base.search("vision document")
        self.logger.debug(f"Found {len(vision_docs)} relevant vision documentation")

        # If LLM provider is available, use it to generate the vision
        if self.llm_provider:
            try:
                # Format knowledge context from documentation
                knowledge_context = GameDesignerPrompts.format_knowledge_context(vision_docs)

                # Create the vision prompt using the template
                user_prompt = GameDesignerPrompts.create_vision_prompt(
                    project_name=project_name,
                    project_description=project_description,
                    genres=genres,
                    elements=elements,
                    knowledge_context=knowledge_context
                )

                # Generate the vision document using LLM
                messages = [
                    LLMMessage(role="system", content=GameDesignerPrompts.SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ]

                response = await self.llm_provider.generate(messages)

                self.logger.info(f"Generated vision document with {len(response.content)} characters")

                # Save the vision document if project path is set
                vision_content = response.content
                if self.project_path:
                    success = write_project_file(
                        self.project_path,
                        f"{DESIGN_DIR}/{VISION_DOCUMENT_FILE}",
                        vision_content
                    )
                    if success:
                        self.logger.info(f"Saved vision document to: {self.project_path / DESIGN_DIR / VISION_DOCUMENT_FILE}")
                    else:
                        self.logger.error("Failed to save vision document")

                # Store the vision document
                self.design_documents["vision"] = {
                    "name": project_name,
                    "status": "created",
                    "content": vision_content,
                    "payload": payload,
                }

            except Exception as e:
                self.logger.error(f"Failed to generate vision document with LLM: {e}")
                raise
        else:
            error_msg = "No LLM provider configured, cannot generate vision document"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def _define_mechanics(self, payload: dict) -> None:
        """Define game mechanics and rules.

        Args:
            payload: Task payload with mechanics requirements.
        """
        mechanic_type = payload.get("mechanic_type", "general")
        description = payload.get("description", "")

        self.logger.info(f"Defining game mechanics: {mechanic_type}")

        # Search knowledge base for relevant game design patterns
        mechanics_docs = self.knowledge_base.search("mechanics")
        self.logger.debug(f"Found {len(mechanics_docs)} relevant docs")

        # If LLM provider is available, use it to generate the mechanics definition
        if self.llm_provider:
            try:
                # Format knowledge context
                knowledge_context = GameDesignerPrompts.format_knowledge_context(mechanics_docs)

                # Create the prompt
                user_prompt = GameDesignerPrompts.define_mechanics_prompt(
                    mechanic_type=mechanic_type,
                    description=description,
                    knowledge_context=knowledge_context,
                )

                # Generate the mechanics definition using LLM
                messages = [
                    LLMMessage(role="system", content=GameDesignerPrompts.SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ]

                response = await self.llm_provider.generate(messages)

                self.logger.info(f"Generated mechanics definition with {len(response.content)} characters")

                # Save the design document if project path is set
                if self.project_path:
                    success = write_project_file(
                        self.project_path,
                        f"{DESIGN_DIR}/mechanics_{mechanic_type}.md",
                        response.content
                    )
                    if success:
                        self.logger.info(f"Saved mechanics definition to: {self.project_path / DESIGN_DIR / f'mechanics_{mechanic_type}.md'}")
                    else:
                        self.logger.error("Failed to save mechanics definition")

                # Store the mechanics definition
                self.design_documents[f"mechanics_{mechanic_type}"] = {
                    "type": mechanic_type,
                    "status": "defined",
                    "content": response.content,
                    "payload": payload,
                }

            except Exception as e:
                self.logger.error(f"Failed to generate mechanics definition with LLM: {e}")
        else:
            self.logger.warning("No LLM provider configured, cannot generate mechanics definition")

            # Store basic info without LLM
            self.design_documents[f"mechanics_{mechanic_type}"] = {
                "type": mechanic_type,
                "status": "defined",
                "payload": payload,
            }

    async def _create_storyboard(self, payload: dict) -> None:
        """Create storyboards and narrative design.

        Args:
            payload: Task payload with storyboard requirements.
        """
        scene_name = payload.get("scene_name", "unnamed_scene")
        self.logger.info(f"Creating storyboard for: {scene_name}")
        
        # Search knowledge base for narrative design patterns
        narrative_docs = self.knowledge_base.search("narrative")
        self.logger.debug(f"Found {len(narrative_docs)} relevant docs")
        
        # Store the storyboard
        self.design_documents[f"storyboard_{scene_name}"] = {
            "scene": scene_name,
            "status": "created",
            "payload": payload,
        }

    async def _design_ux(self, payload: dict) -> None:
        """Design user experience and interface flows.

        Args:
            payload: Task payload with UX requirements.
        """
        ux_element = payload.get("element", "general")
        self.logger.info(f"Designing UX for: {ux_element}")
        
        # Search knowledge base for UX best practices
        ux_docs = self.knowledge_base.search("UX")
        self.logger.debug(f"Found {len(ux_docs)} relevant docs")
        
        # Store the UX design
        self.design_documents[f"ux_{ux_element}"] = {
            "element": ux_element,
            "status": "designed",
            "payload": payload,
        }

    async def _balance_gameplay(self, payload: dict) -> None:
        """Balance gameplay systems and progression.

        Args:
            payload: Task payload with balance requirements.
        """
        system_name = payload.get("system", "general")
        self.logger.info(f"Balancing gameplay system: {system_name}")
        
        # Search knowledge base for game balance techniques
        balance_docs = self.knowledge_base.search("balance")
        self.logger.debug(f"Found {len(balance_docs)} relevant docs")

    async def _create_design_document(self, payload: dict) -> None:
        """Create a comprehensive game design document.

        Args:
            payload: Task payload with design document requirements.
        """
        doc_name = payload.get("doc_name", "game_design_doc")
        description = payload.get("description", "")

        self.logger.info(f"Creating design document: {doc_name}")

        # If LLM provider is available, use it to generate the design document
        if self.llm_provider:
            try:
                # Search knowledge base for relevant design patterns
                design_docs = self.knowledge_base.search("design document")
                knowledge_context = GameDesignerPrompts.format_knowledge_context(design_docs)

                # Create a comprehensive prompt
                user_prompt = f"""{knowledge_context}

# Task: Create Game Design Document

Create a comprehensive game design document named `{doc_name}` with the following requirements:

{description}

Provide a detailed design document including:
1. Overview and vision
2. Core mechanics and gameplay
3. Player progression and balance
4. Technical requirements
5. User experience considerations
6. Implementation roadmap

Format as a well-structured markdown document."""

                # Generate the design document using LLM
                messages = [
                    LLMMessage(role="system", content=GameDesignerPrompts.SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ]

                response = await self.llm_provider.generate(messages)

                self.logger.info(f"Generated design document with {len(response.content)} characters")

                # Save the design document if project path is set
                if self.project_path:
                    success = write_project_file(
                        self.project_path,
                        f"{DESIGN_DIR}/{doc_name}.md",
                        response.content
                    )
                    if success:
                        self.logger.info(f"Saved design document to: {self.project_path / DESIGN_DIR / f'{doc_name}.md'}")
                    else:
                        self.logger.error("Failed to save design document")

                # Store the design document
                self.design_documents[doc_name] = {
                    "name": doc_name,
                    "status": "created",
                    "content": response.content,
                    "payload": payload,
                }

            except Exception as e:
                self.logger.error(f"Failed to generate design document with LLM: {e}")
        else:
            self.logger.warning("No LLM provider configured, cannot generate design document")

            # Store basic info without LLM
            self.design_documents[doc_name] = {
                "name": doc_name,
                "status": "created",
                "payload": payload,
            }

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

    def get_design_documents(self) -> dict[str, dict]:
        """Get all design documents created by this agent.

        Returns:
            Dictionary of design documents.
        """
        return self.design_documents.copy()

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
            self.logger.debug("No available tasks for Game Designer")
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

        if not task_id:
            self.logger.warning("Task has no ID, cannot execute")
            return

        self.logger.info(f"Executing task: {task_title} (type: {task_type})")

        try:
            # Simulate task execution based on task type
            if task_type == "design_mechanics":
                result = await self._autonomous_design_mechanics(task)
            elif task_type == "create_level_design":
                result = await self._autonomous_create_level_design(task)
            elif task_type == "design_ui":
                result = await self._autonomous_design_ui(task)
            else:
                self.logger.warning(f"Unknown task type: {task_type}, marking as complete")
                result = {"status": "completed", "message": f"Task type {task_type} not yet implemented"}

            # Complete the task
            await self.complete_task(task_id, result)
            self.logger.info(f"Completed task: {task_title}")

        except Exception as e:
            self.logger.error(f"Error executing task {task_title}: {e}", exc_info=True)

    async def _autonomous_design_mechanics(self, task: dict) -> dict:
        """Autonomously design game mechanics.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Designing core game mechanics...")

        return {
            "status": "completed",
            "message": "Core game mechanics defined",
            "mechanics": ["movement", "combat", "progression"],
        }

    async def _autonomous_create_level_design(self, task: dict) -> dict:
        """Autonomously create level design.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Creating level design...")

        return {
            "status": "completed",
            "message": "Level design created",
            "levels": ["tutorial", "level_1", "level_2"],
        }

    async def _autonomous_design_ui(self, task: dict) -> dict:
        """Autonomously design UI/UX.

        Args:
            task: The task data dictionary.

        Returns:
            Result dictionary with task outcome.
        """
        self.logger.info("Designing UI/UX...")

        return {
            "status": "completed",
            "message": "UI/UX design completed",
            "screens": ["main_menu", "hud", "pause_menu"],
        }

