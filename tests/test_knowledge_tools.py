"""Tests for role-scoped knowledge tools."""

from src.agents.base import Agent
from src.agents.config import AgentConfig
from src.agents.knowledge import KnowledgeBase
from src.agents.knowledge_tools import create_knowledge_tools
from src.agents.roles import AgentRole


def test_create_knowledge_tools_list_and_read() -> None:
    """list_knowledge and read_knowledge return role documentation."""
    kb = KnowledgeBase(name="game_design")
    tools = {t.name: t for t in create_knowledge_tools(kb)}

    listing = tools["list_knowledge"].execute({})
    assert "vision_document_guide.md" in listing

    content = tools["read_knowledge"].execute(
        {"document_key": "vision_document_guide.md"}
    )
    assert not content.startswith("ERROR:")
    assert len(content) > 100


def test_read_knowledge_unknown_key_returns_error() -> None:
    kb = KnowledgeBase(name="game_design")
    tools = {t.name: t for t in create_knowledge_tools(kb)}

    result = tools["read_knowledge"].execute({"document_key": "missing.md"})
    assert result.startswith("ERROR:")


def test_agent_with_knowledge_path_gets_knowledge_tools() -> None:
    """Agents with knowledge_path receive list_knowledge and read_knowledge."""
    agent = Agent(
        "game_designer",
        AgentRole.GAME_DESIGNER,
        AgentConfig(
            knowledge_path="game_design/",
            system_prompt="Designer",
            capabilities=["design"],
        ),
    )
    names = {t.name for t in agent.tools}
    assert "list_knowledge" in names
    assert "read_knowledge" in names


def test_build_prompt_injects_full_rubric() -> None:
    """Specialist prompt must include full rubric markdown, not just the id."""
    from langchain_core.messages import HumanMessage

    from src.agents.state_factory import build_initial_workflow_state
    from src.agents.state_factory import build_task_state

    agent = Agent(
        "game_designer",
        AgentRole.GAME_DESIGNER,
        AgentConfig(
            knowledge_path="game_design/",
            system_prompt="Designer",
            capabilities=["design"],
        ),
    )
    base = build_initial_workflow_state({"name": "Test", "brief": "A cozy game"})
    state = build_task_state(
        base,
        task_id="t1",
        task_type="design",
        task_description="Write VISION.md",
        acceptance_criteria=["Has genre"],
        agent_name="game_designer",
        rubric="vision_document_guide",
        recommended_artifact="design/VISION.md",
    )
    prompt = agent._build_prompt(state)
    human = next(m for m in prompt if isinstance(m, HumanMessage))
    assert "Quality Rubric (vision_document_guide):" in human.content
    assert "vision_document_guide" in human.content.lower() or "vision" in human.content.lower()
    # Rubric body should be substantial, not just the id line.
    assert len(human.content) > 500
