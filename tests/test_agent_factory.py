"""Tests for the AgentFactory."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.agent_factory import AgentFactory


class TestAgentFactory:
    """Test suite for AgentFactory."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance."""
        return Orchestrator()

    @pytest.fixture
    def agent_factory(self, orchestrator):
        """Create an agent factory instance."""
        return AgentFactory(orchestrator)

    def test_initialization(self, agent_factory):
        """Test that AgentFactory initializes correctly."""
        assert agent_factory.orchestrator is not None
        assert agent_factory._agents == {}
        
        # Check documentation paths are set
        assert agent_factory.docs_root is not None
        assert agent_factory.game_design_docs is not None
        assert agent_factory.programming_docs is not None
        assert agent_factory.art_docs is not None
        assert agent_factory.audio_docs is not None
        assert agent_factory.qa_docs is not None
        assert agent_factory.production_docs is not None

    def test_create_all_agents(self, agent_factory):
        """Test that all agents are created and registered."""
        agents = agent_factory.create_all_agents()
        
        # Verify all 6 agents are created
        assert len(agents) == 6
        assert "Game Programmer" in agents
        assert "Game Designer" in agents
        assert "Game Artist" in agents
        assert "Game Producer" in agents
        assert "QA Tester" in agents
        assert "Audio Engineer" in agents
        
        # Verify agents have knowledge bases
        for agent_name, agent in agents.items():
            assert hasattr(agent, 'knowledge_base')
            assert agent.knowledge_base is not None

    def test_knowledge_base_loading(self, agent_factory):
        """Test that agents load their documentation if it exists."""
        agents = agent_factory.create_all_agents()
        
        # Check if documentation directories exist
        docs_exist = agent_factory.game_design_docs.exists()
        
        if docs_exist:
            # If docs exist, verify they are loaded
            designer = agents["Game Designer"]
            assert designer.knowledge_base.is_loaded()
            assert designer.knowledge_base.get_document_count() > 0
            
            # Verify search functionality works
            results = designer.knowledge_base.search("vision")
            # Should find results if vision_document_guide.md exists
            assert isinstance(results, list)

    def test_get_agent_by_name(self, agent_factory):
        """Test retrieving agents by name."""
        agents = agent_factory.create_all_agents()
        
        designer = agent_factory.get_agent_by_name("Game Designer")
        assert designer is not None
        assert designer == agents["Game Designer"]
        
        # Test non-existent agent
        non_existent = agent_factory.get_agent_by_name("Non Existent")
        assert non_existent is None

    def test_get_all_agents(self, agent_factory):
        """Test getting all agents."""
        created_agents = agent_factory.create_all_agents()
        all_agents = agent_factory.get_all_agents()
        
        assert len(all_agents) == len(created_agents)
        assert all_agents == created_agents
        
        # Verify it returns a copy
        all_agents["Test"] = "value"
        assert "Test" not in agent_factory.get_all_agents()

    def test_update_llm_provider(self, agent_factory):
        """Test updating LLM provider for all agents."""
        agents = agent_factory.create_all_agents()
        
        # Create a mock LLM provider
        mock_provider = MagicMock()
        
        # Update provider
        agent_factory.update_llm_provider(mock_provider)
        
        # Verify all agents have the new provider
        for agent_name, agent in agents.items():
            if hasattr(agent, 'llm_provider'):
                assert agent.llm_provider == mock_provider

    def test_agents_registered_with_orchestrator(self, agent_factory, orchestrator):
        """Test that agents are registered with the orchestrator."""
        agents = agent_factory.create_all_agents()

        # Verify agents are registered
        for agent_name, agent in agents.items():
            # Check agent is in orchestrator's agents dict
            assert agent.id in orchestrator._agents

    def test_documentation_paths_are_correct(self, agent_factory):
        """Test that documentation paths point to correct directories."""
        # Get the project root
        project_root = Path(__file__).parent.parent
        expected_docs_root = project_root / "docs"
        
        assert agent_factory.docs_root == expected_docs_root
        assert agent_factory.game_design_docs == expected_docs_root / "game_design"
        assert agent_factory.programming_docs == expected_docs_root / "programming"
        assert agent_factory.art_docs == expected_docs_root / "art"
        assert agent_factory.audio_docs == expected_docs_root / "audio"
        assert agent_factory.qa_docs == expected_docs_root / "qa"
        assert agent_factory.production_docs == expected_docs_root / "production"

    def test_agents_have_unique_ids(self, agent_factory):
        """Test that all agents have unique IDs."""
        agents = agent_factory.create_all_agents()

        agent_ids = [agent.id for agent in agents.values()]

        # All IDs should be unique
        assert len(agent_ids) == len(set(agent_ids))

    def test_create_agents_with_llm_provider(self, agent_factory):
        """Test creating agents with an LLM provider."""
        mock_provider = MagicMock()
        
        agents = agent_factory.create_all_agents(llm_provider=mock_provider)
        
        # Verify all agents have the provider
        for agent_name, agent in agents.items():
            if hasattr(agent, 'llm_provider'):
                assert agent.llm_provider == mock_provider

