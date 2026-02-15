"""Audio Engineer Agent for managing sound and music.

This agent is responsible for:
- Creating and managing sound effects
- Composing and integrating music
- Managing audio assets and mixing
- Ensuring audio quality and performance
"""

import logging
from pathlib import Path
from typing import Optional

from src.agents.base import Agent, Message, MessageType
from src.agents.knowledge_base import KnowledgeBase
from src.llm import BaseLLMProvider, LLMMessage


class AudioEngineerAgent(Agent):
    """Agent specialized in audio engineering and sound design.

    This agent handles all audio tasks including sound effects, music,
    audio asset management, and mixing. It uses a knowledge base loaded
    with audio design documentation and best practices.

    Attributes:
        knowledge_base: Knowledge base containing audio design documentation.
        project_path: Path to the Godot project being worked on.
        audio_assets: Dictionary tracking audio assets.
    """

    def __init__(
        self,
        name: str = "AudioEngineer",
        audio_docs_path: Optional[Path] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialize the Audio Engineer Agent.

        Args:
            name: Name for this agent instance.
            audio_docs_path: Optional path to audio documentation markdown files.
            llm_provider: Optional LLM provider for AI-powered audio specification generation.
        """
        super().__init__(name=name, role="audio_engineer")
        self.knowledge_base = KnowledgeBase(name="audio_docs")
        self.project_path: Optional[Path] = None
        self.audio_assets: dict[str, dict] = {}
        self.llm_provider = llm_provider

        # Load audio documentation if path provided
        if audio_docs_path and audio_docs_path.exists():
            try:
                count = self.knowledge_base.load_from_directory(audio_docs_path)
                self.logger.info(f"Loaded {count} audio documentation files")
            except Exception as e:
                self.logger.error(f"Failed to load audio docs: {e}")

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

        if task_type == "add_sound_effect":
            await self._add_sound_effect(message.payload)
        elif task_type == "create_music":
            await self._create_music(message.payload)
        elif task_type == "manage_audio_assets":
            await self._manage_audio_assets(message.payload)
        elif task_type == "mix_audio":
            await self._mix_audio(message.payload)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")

    async def _handle_file_modified(self, message: Message) -> None:
        """Handle notification that an audio file was modified.

        Args:
            message: The file modified message.
        """
        file_path = message.payload.get("file_path")
        self.logger.info(f"Audio file modified: {file_path}")
        # Could trigger audio re-import or validation here

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status updates from other agents.

        Args:
            message: The status update message.
        """
        agent_role = message.payload.get("role")
        status = message.payload.get("status")
        self.logger.info(f"Status update from {agent_role}: {status}")

    async def _add_sound_effect(self, payload: dict) -> None:
        """Add a sound effect to the game.

        Args:
            payload: Task payload with sound effect details.
        """
        sound_name = payload.get("sound_name", "new_sound")
        sound_type = payload.get("sound_type", "general")
        
        self.logger.info(f"Adding sound effect: {sound_name} (type: {sound_type})")
        
        # Search knowledge base for sound design techniques
        sound_docs = self.knowledge_base.search("sound effect")
        self.logger.debug(f"Found {len(sound_docs)} relevant docs")
        
        # Register the audio asset
        self.audio_assets[sound_name] = {
            "type": "sound_effect",
            "sound_type": sound_type,
            "status": "created",
            "payload": payload,
        }

    async def _create_music(self, payload: dict) -> None:
        """Create music for the game.

        Args:
            payload: Task payload with music details.
        """
        music_name = payload.get("music_name", "new_music")
        music_style = payload.get("style", "ambient")
        
        self.logger.info(f"Creating music: {music_name} (style: {music_style})")
        
        # Search knowledge base for music composition techniques
        music_docs = self.knowledge_base.search("music composition")
        self.logger.debug(f"Found {len(music_docs)} relevant docs")
        
        # Register the audio asset
        self.audio_assets[music_name] = {
            "type": "music",
            "style": music_style,
            "status": "created",
            "payload": payload,
        }

    async def _manage_audio_assets(self, payload: dict) -> None:
        """Manage audio assets and organization.

        Args:
            payload: Task payload with asset management details.
        """
        operation = payload.get("operation", "organize")
        self.logger.info(f"Managing audio assets: {operation}")
        
        # Search knowledge base for asset management best practices
        asset_docs = self.knowledge_base.search("audio asset")
        self.logger.debug(f"Found {len(asset_docs)} relevant docs")

    async def _mix_audio(self, payload: dict) -> None:
        """Mix and balance audio levels.

        Args:
            payload: Task payload with mixing details.
        """
        mix_name = payload.get("mix_name", "master_mix")
        self.logger.info(f"Mixing audio: {mix_name}")
        
        # Search knowledge base for audio mixing techniques
        mix_docs = self.knowledge_base.search("audio mixing")
        self.logger.debug(f"Found {len(mix_docs)} relevant docs")

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

    def get_audio_assets(self) -> dict[str, dict]:
        """Get all audio assets.

        Returns:
            Dictionary of audio assets.
        """
        return self.audio_assets.copy()

