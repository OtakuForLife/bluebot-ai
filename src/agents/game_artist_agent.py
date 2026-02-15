"""Game Artist Agent for creating visual assets and animations.

This agent is responsible for:
- Creating 2D/3D models and assets
- Designing animations and visual effects
- Managing textures and materials
- Designing user interface (UI) elements
"""

import logging
from pathlib import Path
from typing import Optional

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage
from src.llm.prompt_templates import GameArtistPrompts


class GameArtistAgent(Agent):
    """Agent specialized in game art and visual asset creation.

    This agent handles all art-related tasks including 2D/3D modeling,
    animations, textures, and UI design. It uses a knowledge base
    loaded with art and asset creation documentation.

    Attributes:
        knowledge_base: Knowledge base containing art and asset documentation.
        project_path: Path to the Godot project being worked on.
        asset_registry: Dictionary tracking created assets.
    """

    def __init__(
        self,
        name: str = "GameArtist",
        art_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the Game Artist Agent.

        Args:
            name: Name for this agent instance.
            art_docs_path: Optional path to art documentation markdown files.
            llm_provider: Optional LLM provider for AI-powered asset specification generation.
        """
        super().__init__(name=name, role="game_artist")
        self.knowledge_base = KnowledgeBase(name="art_docs")
        self.project_path: Optional[Path] = None
        self.asset_registry: dict[str, dict] = {}
        self.llm_provider = llm_provider

        # Load art documentation if path provided
        if art_docs_path and art_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(art_docs_path)
                self.logger.info(f"Loaded {count} art documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load art docs: {e}")

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
        elif message.type == MessageType.STATUS_UPDATE:
            await self._handle_status_update(message)
        else:
            self.logger.debug(f"Ignoring message type: {message.type.value}")

    async def _handle_task_request(self, message: Message) -> None:
        """Handle a task request message.

        Args:
            message: The task request message.
        """
        task_type = message.payload.get("task_type")
        self.logger.info(f"Received task request: {task_type}")

        if task_type == "create_sprite":
            await self._create_sprite(message.payload)
        elif task_type == "create_model":
            await self._create_model(message.payload)
        elif task_type == "create_animation":
            await self._create_animation(message.payload)
        elif task_type == "design_ui":
            await self._design_ui(message.payload)
        elif task_type == "manage_textures":
            await self._manage_textures(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_file_modified(self, message: Message) -> None:
        """Handle notification that an asset file was modified.

        Args:
            message: The file modified message.
        """
        file_path = message.payload.get("file_path")
        self.logger.info(f"Asset file modified: {file_path}")
        # Could trigger asset validation or re-import here

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status updates from other agents.

        Args:
            message: The status update message.
        """
        agent_role = message.payload.get("role")
        status = message.payload.get("status")
        self.logger.info(f"Status update from {agent_role}: {status}")

    async def _create_sprite(self, payload: dict) -> None:
        """Create a 2D sprite asset.

        Args:
            payload: Task payload with sprite requirements.
        """
        sprite_name = payload.get("sprite_name", "new_sprite")
        description = payload.get("description", "")

        self.logger.info(f"Creating sprite: {sprite_name}")

        # Search knowledge base for sprite creation techniques
        sprite_docs = self.knowledge_base.search("sprite")
        self.logger.debug(f"Found {len(sprite_docs)} relevant docs")

        # If LLM provider is available, use it to generate asset specification
        if self.llm_provider:
            try:
                # Format knowledge context
                knowledge_context = GameArtistPrompts.format_knowledge_context(sprite_docs)

                # Create the prompt
                user_prompt = GameArtistPrompts.create_asset_prompt(
                    asset_type="2D Sprite",
                    description=description,
                    knowledge_context=knowledge_context,
                )

                # Generate the asset specification using LLM
                messages = [
                    LLMMessage(role="system", content=GameArtistPrompts.SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ]

                response = await self.llm_provider.generate(messages)

                self.logger.info(f"Generated sprite specification with {len(response.content)} characters")

                # Save the specification if project path is set
                if self.project_path:
                    spec_path = self.project_path / "art" / "specs" / f"{sprite_name}_spec.md"
                    spec_path.parent.mkdir(parents=True, exist_ok=True)
                    spec_path.write_text(response.content, encoding="utf-8")
                    self.logger.info(f"Saved sprite specification to: {spec_path}")

                # Register the asset
                self.asset_registry[sprite_name] = {
                    "type": "sprite",
                    "status": "created",
                    "content": response.content,
                    "payload": payload,
                }

            except Exception as e:
                self.logger.error(f"Failed to generate sprite specification with LLM: {e}")
        else:
            self.logger.warning("No LLM provider configured, cannot generate sprite specification")

            # Register basic info without LLM
            self.asset_registry[sprite_name] = {
                "type": "sprite",
                "status": "created",
                "payload": payload,
            }

    async def _create_model(self, payload: dict) -> None:
        """Create a 3D model asset.

        Args:
            payload: Task payload with model requirements.
        """
        model_name = payload.get("model_name", "new_model")
        self.logger.info(f"Creating 3D model: {model_name}")
        
        # Search knowledge base for 3D modeling techniques
        model_docs = self.knowledge_base.search("3D model")
        self.logger.debug(f"Found {len(model_docs)} relevant docs")
        
        # Register the asset
        self.asset_registry[model_name] = {
            "type": "model",
            "status": "created",
            "payload": payload,
        }

    async def _create_animation(self, payload: dict) -> None:
        """Create an animation asset.

        Args:
            payload: Task payload with animation requirements.
        """
        animation_name = payload.get("animation_name", "new_animation")
        self.logger.info(f"Creating animation: {animation_name}")
        
        # Search knowledge base for animation techniques
        anim_docs = self.knowledge_base.search("animation")
        self.logger.debug(f"Found {len(anim_docs)} relevant docs")
        
        # Register the asset
        self.asset_registry[animation_name] = {
            "type": "animation",
            "status": "created",
            "payload": payload,
        }

    async def _design_ui(self, payload: dict) -> None:
        """Design UI elements and layouts.

        Args:
            payload: Task payload with UI design requirements.
        """
        ui_element = payload.get("ui_element", "new_ui")
        self.logger.info(f"Designing UI element: {ui_element}")
        
        # Search knowledge base for UI design patterns
        ui_docs = self.knowledge_base.search("UI design")
        self.logger.debug(f"Found {len(ui_docs)} relevant docs")
        
        # Register the asset
        self.asset_registry[ui_element] = {
            "type": "ui",
            "status": "designed",
            "payload": payload,
        }

    async def _manage_textures(self, payload: dict) -> None:
        """Manage textures and materials.

        Args:
            payload: Task payload with texture requirements.
        """
        texture_name = payload.get("texture_name", "new_texture")
        self.logger.info(f"Managing texture: {texture_name}")
        
        # Search knowledge base for texture techniques
        texture_docs = self.knowledge_base.search("texture")
        self.logger.debug(f"Found {len(texture_docs)} relevant docs")

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

    def get_asset_registry(self) -> dict[str, dict]:
        """Get all assets created by this agent.

        Returns:
            Dictionary of created assets.
        """
        return self.asset_registry.copy()

