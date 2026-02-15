"""Factory for creating and initializing all specialized agents."""

import logging
from pathlib import Path
from typing import Optional

from src.agents.audio_engineer_agent import AudioEngineerAgent
from src.agents.game_artist_agent import GameArtistAgent
from src.agents.game_designer_agent import GameDesignerAgent
from src.agents.game_producer_agent import GameProducerAgent
from src.agents.game_programmer_agent import GameProgrammerAgent
from src.agents.qa_tester_agent import QATesterAgent
from src.llm.base_provider import BaseLLMProvider
from src.orchestrator.orchestrator import Orchestrator


class AgentFactory:
    """Factory for creating and registering all specialized agents.

    This factory creates instances of all 6 specialized agents and
    registers them with the orchestrator.
    """

    def __init__(self, orchestrator: Orchestrator) -> None:
        """Initialize the agent factory.

        Args:
            orchestrator: The orchestrator to register agents with.
        """
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self._agents: dict[str, any] = {}

        # Set up documentation paths
        self.docs_root = Path(__file__).parent.parent.parent / "docs"
        self.game_design_docs = self.docs_root / "game_design"
        self.programming_docs = self.docs_root / "programming"
        self.art_docs = self.docs_root / "art"
        self.audio_docs = self.docs_root / "audio"
        self.qa_docs = self.docs_root / "qa"
        self.production_docs = self.docs_root / "production"
    
    def create_all_agents(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        godot_docs_path: Optional[Path] = None
    ) -> dict[str, any]:
        """Create and register all specialized agents.

        Args:
            llm_provider: Optional LLM provider to use for all agents.
            godot_docs_path: Optional path to Godot documentation.

        Returns:
            Dictionary mapping agent names to agent instances.
        """
        self.logger.info("Creating all specialized agents...")

        # Create Game Programmer Agent with programming documentation
        programmer = GameProgrammerAgent(
            llm_provider=llm_provider,
            godot_docs_path=godot_docs_path
        )
        # Load programming documentation into knowledge base
        if self.programming_docs.exists():
            count = programmer.knowledge_base.load_from_directory(self.programming_docs)
            self.logger.info(f"Loaded {count} programming documentation files from {self.programming_docs}")

        self.orchestrator.register_agent(programmer)
        self._agents["Game Programmer"] = programmer

        # Create Game Designer Agent with game design documentation
        designer = GameDesignerAgent(llm_provider=llm_provider)
        # Load game design documentation into knowledge base
        if self.game_design_docs.exists():
            count = designer.knowledge_base.load_from_directory(self.game_design_docs)
            self.logger.info(f"Loaded {count} game design documentation files from {self.game_design_docs}")

        self.orchestrator.register_agent(designer)
        self._agents["Game Designer"] = designer

        # Create Game Artist Agent with art documentation
        artist = GameArtistAgent(llm_provider=llm_provider)
        # Load art documentation into knowledge base
        if self.art_docs.exists():
            count = artist.knowledge_base.load_from_directory(self.art_docs)
            self.logger.info(f"Loaded {count} art documentation files from {self.art_docs}")

        self.orchestrator.register_agent(artist)
        self._agents["Game Artist"] = artist

        # Create Game Producer Agent with production documentation
        producer = GameProducerAgent(llm_provider=llm_provider)
        # Load production documentation into knowledge base
        if self.production_docs.exists():
            count = producer.knowledge_base.load_from_directory(self.production_docs)
            self.logger.info(f"Loaded {count} production documentation files from {self.production_docs}")

        self.orchestrator.register_agent(producer)
        self._agents["Game Producer"] = producer

        # Create QA Tester Agent with QA documentation
        qa_tester = QATesterAgent(llm_provider=llm_provider)
        # Load QA documentation into knowledge base
        if self.qa_docs.exists():
            count = qa_tester.knowledge_base.load_from_directory(self.qa_docs)
            self.logger.info(f"Loaded {count} QA documentation files from {self.qa_docs}")

        self.orchestrator.register_agent(qa_tester)
        self._agents["QA Tester"] = qa_tester

        # Create Audio Engineer Agent with audio documentation
        audio_engineer = AudioEngineerAgent(llm_provider=llm_provider)
        # Load audio documentation into knowledge base
        if self.audio_docs.exists():
            count = audio_engineer.knowledge_base.load_from_directory(self.audio_docs)
            self.logger.info(f"Loaded {count} audio documentation files from {self.audio_docs}")

        self.orchestrator.register_agent(audio_engineer)
        self._agents["Audio Engineer"] = audio_engineer

        self.logger.info(f"Created and registered {len(self._agents)} agents")

        return self._agents
    
    def get_agent_by_name(self, name: str) -> Optional[any]:
        """Get an agent by its name.
        
        Args:
            name: The agent's name.
            
        Returns:
            The agent instance or None if not found.
        """
        return self._agents.get(name)
    
    def get_all_agents(self) -> dict[str, any]:
        """Get all created agents.
        
        Returns:
            Dictionary mapping agent names to agent instances.
        """
        return self._agents.copy()
    
    def update_llm_provider(self, llm_provider: BaseLLMProvider) -> None:
        """Update the LLM provider for all agents.

        Args:
            llm_provider: The new LLM provider.
        """
        self.logger.info(f"Updating LLM provider for all agents... Provider: {llm_provider}")
        self.logger.info(f"Number of agents: {len(self._agents)}")

        for name, agent in self._agents.items():
            self.logger.info(f"Checking agent '{name}': has llm_provider attr = {hasattr(agent, 'llm_provider')}")
            if hasattr(agent, 'llm_provider'):
                old_provider = getattr(agent, 'llm_provider', None)
                self.logger.info(f"  Old provider for {name}: {old_provider}")
                agent.llm_provider = llm_provider
                self.logger.info(f"  New provider for {name}: {agent.llm_provider}")
                self.logger.info(f"Updated LLM provider for {name}")

        self.logger.info("LLM provider updated for all agents")

