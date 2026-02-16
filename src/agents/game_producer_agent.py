"""Game Producer Agent for managing development timeline and coordination.

This agent is responsible for:
- Managing development timeline and milestones
- Coordinating tasks between other agents
- Tracking project progress and status
- Resource allocation and prioritization
"""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage


class GameProducerAgent(Agent):
    """Agent specialized in project management and coordination.

    This agent handles project management tasks including timeline management,
    agent coordination, progress tracking, and task prioritization. It uses
    a knowledge base loaded with project management best practices.

    Attributes:
        knowledge_base: Knowledge base containing project management documentation.
        project_path: Path to the Godot project being worked on.
        task_assignments: Dictionary tracking task assignments to agents.
        project_timeline: Dictionary storing project milestones and deadlines.
    """

    def __init__(
        self,
        name: str = "GameProducer",
        management_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the Game Producer Agent.

        Args:
            name: Name for this agent instance.
            management_docs_path: Optional path to project management documentation.
            llm_provider: Optional LLM provider for AI-powered project management.
        """
        super().__init__(name=name, role="game_producer")
        self.knowledge_base = KnowledgeBase(name="management_docs")
        self.project_path: Optional[Path] = None
        self.task_assignments: dict[str, dict] = {}
        self.project_timeline: dict[str, dict] = {}
        self.llm_provider = llm_provider
        self.vision_approved: bool = False
        self.autonomous_mode: bool = False
        self.project_info: Optional[dict] = None

        # Load management documentation if path provided
        if management_docs_path and management_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(management_docs_path)
                self.logger.info(f"Loaded {count} management documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load management docs: {e}")

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
        elif message.type == MessageType.TASK_RESPONSE:
            await self._handle_task_response(message)
        elif message.type == MessageType.PROJECT_CREATED:
            await self._handle_project_created(message)
        elif message.type == MessageType.VISION_APPROVED:
            await self._handle_vision_approved(message)
        else:
            self.logger.debug(f"Ignoring message type: {message.type.value}")

    async def _handle_task_request(self, message: Message) -> None:
        """Handle a task request message.

        Args:
            message: The task request message.
        """
        task_type = message.payload.get("task_type")
        self.logger.info(f"Received task request: {task_type}")

        if task_type == "assign_task":
            await self._assign_task(message.payload)
        elif task_type == "track_progress":
            await self._track_progress(message.payload)
        elif task_type == "manage_timeline":
            await self._manage_timeline(message.payload)
        elif task_type == "coordinate_agents":
            await self._coordinate_agents(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status updates from other agents.

        Args:
            message: The status update message.
        """
        agent_id = str(message.sender_id)
        agent_role = message.payload.get("role")
        status = message.payload.get("status")
        
        self.logger.info(f"Status update from {agent_role} ({agent_id}): {status}")
        
        # Update task assignments if this agent has assigned tasks
        for task_id, task_info in self.task_assignments.items():
            if task_info.get("assigned_to") == agent_id:
                task_info["agent_status"] = status

    async def _handle_task_response(self, message: Message) -> None:
        """Handle task completion responses from agents.

        Args:
            message: The task response message.
        """
        task_id = message.payload.get("task_id")
        completed = message.payload.get("completed", False)
        
        if task_id in self.task_assignments:
            self.task_assignments[task_id]["completed"] = completed
            self.logger.info(f"Task {task_id} marked as {'completed' if completed else 'incomplete'}")

    async def _assign_task(self, payload: dict) -> None:
        """Assign a task to an agent.

        Args:
            payload: Task payload with assignment details.
        """
        task_id = payload.get("task_id", "unknown")
        agent_id = payload.get("agent_id")
        task_description = payload.get("description", "")
        
        self.logger.info(f"Assigning task {task_id} to agent {agent_id}")
        
        # Search knowledge base for task management best practices
        mgmt_docs = self.knowledge_base.search("task management")
        self.logger.debug(f"Found {len(mgmt_docs)} relevant docs")
        
        # Store the task assignment
        self.task_assignments[task_id] = {
            "assigned_to": agent_id,
            "description": task_description,
            "status": "assigned",
            "completed": False,
        }

    async def _track_progress(self, payload: dict) -> None:
        """Track project progress.

        Args:
            payload: Task payload with progress tracking details.
        """
        self.logger.info("Tracking project progress")
        
        # Calculate completion statistics
        total_tasks = len(self.task_assignments)
        completed_tasks = sum(1 for task in self.task_assignments.values() if task.get("completed"))
        
        self.logger.info(f"Progress: {completed_tasks}/{total_tasks} tasks completed")

    async def _manage_timeline(self, payload: dict) -> None:
        """Manage project timeline and milestones.

        Args:
            payload: Task payload with timeline details.
        """
        milestone_name = payload.get("milestone", "unnamed")
        deadline = payload.get("deadline")
        
        self.logger.info(f"Managing timeline for milestone: {milestone_name}")
        
        # Search knowledge base for timeline management techniques
        timeline_docs = self.knowledge_base.search("timeline")
        self.logger.debug(f"Found {len(timeline_docs)} relevant docs")
        
        # Store the milestone
        self.project_timeline[milestone_name] = {
            "deadline": deadline,
            "status": "planned",
            "payload": payload,
        }

    async def _coordinate_agents(self, payload: dict) -> None:
        """Coordinate multiple agents for complex tasks.

        Args:
            payload: Task payload with coordination details.
        """
        coordination_type = payload.get("coordination_type", "general")
        self.logger.info(f"Coordinating agents for: {coordination_type}")
        
        # Search knowledge base for coordination strategies
        coord_docs = self.knowledge_base.search("coordination")
        self.logger.debug(f"Found {len(coord_docs)} relevant docs")

    async def _handle_project_created(self, message: Message) -> None:
        """Handle project creation notification.

        Args:
            message: The project created message.
        """
        self.project_info = message.payload
        project_name = self.project_info.get("project_name", "Unknown")
        self.logger.info(f"Project created: {project_name}")
        self.logger.info("Waiting for vision approval to start autonomous coordination...")

    async def _handle_vision_approved(self, message: Message) -> None:
        """Handle vision approval and start autonomous coordination.

        Args:
            message: The vision approved message.
        """
        self.vision_approved = True
        self.autonomous_mode = True

        vision_content = message.payload.get("vision_content", "")
        self.logger.info("Vision approved! Starting autonomous coordination mode...")

        # Start the autonomous coordination loop
        await self._start_autonomous_coordination(vision_content)

    async def _start_autonomous_coordination(self, vision_content: str) -> None:
        """Start autonomous coordination of the development process.

        This method analyzes the vision and creates a development plan,
        then coordinates agents to execute it.

        Args:
            vision_content: The approved vision document content.
        """
        self.logger.info("Analyzing vision and creating development plan...")

        if not self.llm_provider:
            self.logger.error("No LLM provider configured, cannot create development plan")
            return

        try:
            # Use LLM to analyze vision and create task breakdown
            from src.llm import LLMMessage

            user_prompt = f"""# Task: Create Development Plan

You are the Game Producer coordinating a game development project.

## Approved Vision Document
{vision_content}

## Your Task
Based on this vision, create a detailed development plan with specific tasks for each agent:

1. **Game Designer Tasks**
   - Define core mechanics
   - Create level/progression design
   - Design UI/UX flows
   - Balance gameplay systems

2. **Game Programmer Tasks**
   - Set up project structure
   - Implement core mechanics
   - Create game systems
   - Integrate assets

3. **Game Artist Tasks**
   - Create art style guide
   - Design sprites/models
   - Create animations
   - Design UI elements

4. **Audio Engineer Tasks**
   - Define audio style
   - Create sound effects
   - Compose music tracks
   - Implement audio system

5. **QA Tester Tasks**
   - Create test plan
   - Define test cases
   - Set up automated tests
   - Performance testing

For each task, provide:
- Task name
- Description (2-3 sentences)
- Priority (High/Medium/Low)
- Dependencies (which tasks must be done first)
- Estimated complexity (Simple/Medium/Complex)

Format as a structured list. Be specific and actionable."""

            messages = [
                LLMMessage(
                    role="system",
                    content="You are an experienced game producer coordinating a multi-agent development team."
                ),
                LLMMessage(role="user", content=user_prompt),
            ]

            response = await self.llm_provider.generate(messages)

            development_plan = response.content
            self.logger.info(f"Created development plan with {len(development_plan)} characters")

            # Save the development plan
            if self.project_path:
                plan_path = self.project_path / "design" / "DEVELOPMENT_PLAN.md"
                plan_path.parent.mkdir(parents=True, exist_ok=True)
                plan_path.write_text(development_plan, encoding="utf-8")
                self.logger.info(f"Saved development plan to: {plan_path}")

            # TODO: Parse the plan and start assigning tasks to agents
            # For now, just log that we're ready
            self.logger.info("Development plan created. Ready to coordinate agents.")
            self.logger.info("Next step: Implement task parsing and assignment logic")

        except Exception as e:
            self.logger.error(f"Failed to create development plan: {e}", exc_info=True)

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

    def get_task_assignments(self) -> dict[str, dict]:
        """Get all task assignments.

        Returns:
            Dictionary of task assignments.
        """
        return self.task_assignments.copy()

    def get_project_timeline(self) -> dict[str, dict]:
        """Get the project timeline.

        Returns:
            Dictionary of project milestones.
        """
        return self.project_timeline.copy()

    async def on_autonomous_tick(self) -> None:
        """Autonomous coordination tick.

        This method is called periodically when autonomous_mode is True.
        It checks if initial tasks need to be created from the vision.
        """
        if not self.autonomous_mode or not self.vision_approved:
            return

        # Check if we've already created initial tasks
        if not self.task_manager:
            self.logger.warning("Task manager not available")
            return

        # Get all tasks to see if we've already created initial tasks
        all_tasks = await self.task_manager.get_all_tasks()

        # If there are already tasks, don't create more initial tasks
        if len(all_tasks) > 0:
            self.logger.debug(f"Tasks already exist ({len(all_tasks)}), skipping initial task creation")
            return

        # Create initial tasks from vision
        self.logger.info("Creating initial tasks from approved vision...")
        await self._create_initial_tasks()

    async def _create_initial_tasks(self) -> None:
        """Create initial high-level tasks based on the vision.

        This creates a standard set of initial tasks for game development.
        """
        initial_tasks = [
            {
                "title": "Define Core Game Mechanics",
                "description": "Analyze the vision document and define the core gameplay mechanics, rules, and systems that will form the foundation of the game.",
                "agent": "Game Designer",
                "task_type": "design_mechanics",
                "requires_review": True,
            },
            {
                "title": "Create Art Style Guide",
                "description": "Based on the vision, create a comprehensive art style guide including color palette, visual themes, and artistic direction.",
                "agent": "Game Artist",
                "task_type": "create_art_guide",
                "requires_review": True,
            },
            {
                "title": "Set Up Project Structure",
                "description": "Initialize the Godot project structure with proper folder organization, base scenes, and core scripts.",
                "agent": "Game Programmer",
                "task_type": "setup_project",
                "requires_review": False,
            },
            {
                "title": "Define Audio Style",
                "description": "Establish the audio direction including music genre, sound effect style, and overall audio atmosphere.",
                "agent": "Audio Engineer",
                "task_type": "define_audio_style",
                "requires_review": True,
            },
            {
                "title": "Create Test Plan",
                "description": "Develop a comprehensive test plan covering functional testing, performance testing, and quality assurance procedures.",
                "agent": "QA Tester",
                "task_type": "create_test_plan",
                "requires_review": True,
            },
        ]

        for task_data in initial_tasks:
            try:
                task = await self.create_task(
                    title=task_data["title"],
                    description=task_data["description"],
                    agent=task_data["agent"],
                    task_type=task_data["task_type"],
                    requires_review=task_data["requires_review"],
                    metadata={"phase": "initial", "created_by_producer": True},
                )

                if task:
                    self.logger.info(f"Created initial task: {task_data['title']}")
                else:
                    self.logger.error(f"Failed to create task: {task_data['title']}")

            except Exception as e:
                self.logger.error(f"Error creating task {task_data['title']}: {e}", exc_info=True)

