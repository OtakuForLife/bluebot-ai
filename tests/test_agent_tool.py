"""Tests for AgentTool class."""

import pytest

from src.agents.llm.tool import AgentTool


def test_agent_tool_initialization() -> None:
    """Test that an agent tool initializes correctly."""
    def dummy_callback(params: dict) -> str:
        return f"Executed with {params}"

    tool = AgentTool(
        name="test_tool",
        description="A test tool",
        callback=dummy_callback
    )

    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.callback == dummy_callback


def test_agent_tool_execution() -> None:
    """Test that an agent tool executes correctly."""
    def dummy_callback(params: dict) -> str:
        return f"Executed with {params}"

    tool = AgentTool(
        name="test_tool",
        description="A test tool",
        callback=dummy_callback
    )

    result = tool.execute({"key": "value"})
    assert result == "Executed with {'key': 'value'}"


def test_agent_tool_execution_with_multiple_params() -> None:
    """Test that an agent tool handles multiple parameters."""
    def concat_callback(params: dict) -> str:
        return f"{params.get('first')} {params.get('second')}"

    tool = AgentTool(
        name="concat_tool",
        description="Concatenates two strings",
        callback=concat_callback
    )

    result = tool.execute({"first": "Hello", "second": "World"})
    assert result == "Hello World"


def test_agent_tool_with_complex_callback() -> None:
    """Test that an agent tool works with complex callback logic."""
    def complex_callback(params: dict) -> dict:
        numbers = params.get("numbers", [])
        return {
            "sum": sum(numbers),
            "count": len(numbers),
            "average": sum(numbers) / len(numbers) if numbers else 0
        }

    tool = AgentTool(
        name="stats_tool",
        description="Calculates statistics",
        callback=complex_callback
    )

    result = tool.execute({"numbers": [1, 2, 3, 4, 5]})
    assert result == {"sum": 15, "count": 5, "average": 3.0}


def test_agent_tool_with_empty_params() -> None:
    """Test that an agent tool handles empty parameters."""
    def empty_callback(params: dict) -> bool:
        return len(params) == 0

    tool = AgentTool(
        name="check_empty",
        description="Checks if params are empty",
        callback=empty_callback
    )

    result = tool.execute({})
    assert result is True
