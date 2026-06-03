"""Tests for base provider classes and dataclasses."""

import pytest

from src.agents.llm.base_provider import (
    ToolCall,
    LLMMessage,
    LLMResponse,
    LLMConfig,
    LLMProviderError,
)


def test_tool_call_initialization() -> None:
    """Test that ToolCall initializes correctly."""
    tool_call = ToolCall(
        name="create_file",
        arguments={"path": "test.txt", "content": "hello"},
        id="call_123"
    )

    assert tool_call.name == "create_file"
    assert tool_call.arguments == {"path": "test.txt", "content": "hello"}
    assert tool_call.id == "call_123"


def test_llm_message_initialization() -> None:
    """Test that LLMMessage initializes correctly."""
    message = LLMMessage(
        role="user",
        content="Hello, how are you?"
    )

    assert message.role == "user"
    assert message.content == "Hello, how are you?"


def test_llm_message_system_role() -> None:
    """Test that LLMMessage supports system role."""
    message = LLMMessage(
        role="system",
        content="You are a helpful assistant."
    )

    assert message.role == "system"
    assert message.content == "You are a helpful assistant."


def test_llm_message_assistant_role() -> None:
    """Test that LLMMessage supports assistant role."""
    message = LLMMessage(
        role="assistant",
        content="I can help you with that."
    )

    assert message.role == "assistant"
    assert message.content == "I can help you with that."


def test_llm_response_initialization() -> None:
    """Test that LLMResponse initializes correctly."""
    response = LLMResponse(
        content="Hello world!",
        model="llama3"
    )

    assert response.content == "Hello world!"
    assert response.model == "llama3"
    assert response.finish_reason is None
    assert response.usage is None
    assert response.tool_calls is None


def test_llm_response_with_all_fields() -> None:
    """Test that LLMResponse supports all fields."""
    response = LLMResponse(
        content="Complete response",
        model="gpt-4",
        finish_reason="stop",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        tool_calls=[
            ToolCall(
                name="search",
                arguments={"query": "test"},
                id="call_1"
            )
        ]
    )

    assert response.content == "Complete response"
    assert response.model == "gpt-4"
    assert response.finish_reason == "stop"
    assert response.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "search"


def test_llm_config_defaults() -> None:
    """Test that LLMConfig has correct defaults."""
    config = LLMConfig()

    assert config.provider == "ollama"
    assert config.model == "llama3"
    assert config.temperature == 0.7
    assert config.max_tokens == 4096
    assert config.top_p == 1.0
    assert config.timeout == 300
    assert config.base_url is None
    assert config.api_key is None


def test_llm_config_custom_values() -> None:
    """Test that LLMConfig accepts custom values."""
    config = LLMConfig(
        provider="openai",
        model="gpt-4",
        temperature=0.5,
        max_tokens=2048,
        top_p=0.9,
        timeout=120,
        base_url="https://api.openai.com",
        api_key="sk-test123"
    )

    assert config.provider == "openai"
    assert config.model == "gpt-4"
    assert config.temperature == 0.5
    assert config.max_tokens == 2048
    assert config.top_p == 0.9
    assert config.timeout == 120
    assert config.base_url == "https://api.openai.com"
    assert config.api_key == "sk-test123"


def test_llm_provider_error_initialization() -> None:
    """Test that LLMProviderError initializes correctly."""
    error = LLMProviderError(
        message="Connection failed",
        provider="OpenAI"
    )

    assert error.provider == "OpenAI"
    assert error.original_error is None
    assert "[OpenAI] Connection failed" in str(error)


def test_llm_provider_error_with_original_exception() -> None:
    """Test that LLMProviderError can wrap original exceptions."""
    original_error = ValueError("Invalid input")
    error = LLMProviderError(
        message="Invalid configuration",
        provider="Ollama",
        original_error=original_error
    )

    assert error.provider == "Ollama"
    assert error.original_error is original_error
    assert "[Ollama] Invalid configuration" in str(error)


def test_llm_config_temperature_bounds() -> None:
    """Test that LLMConfig accepts various temperature values."""
    # Low temperature
    config_low = LLMConfig(temperature=0.0)
    assert config_low.temperature == 0.0

    # High temperature
    config_high = LLMConfig(temperature=2.0)
    assert config_high.temperature == 2.0

    # Mid temperature
    config_mid = LLMConfig(temperature=1.0)
    assert config_mid.temperature == 1.0


def test_tool_call_with_complex_arguments() -> None:
    """Test that ToolCall handles complex argument structures."""
    complex_args = {
        "nested": {
            "key": "value",
            "list": [1, 2, 3]
        },
        "array": ["a", "b", "c"],
        "string": "test"
    }

    tool_call = ToolCall(
        name="complex_tool",
        arguments=complex_args,
        id="call_complex"
    )

    assert tool_call.arguments == complex_args
    assert isinstance(tool_call.arguments, dict)


def test_llm_response_multiple_tool_calls() -> None:
    """Test that LLMResponse supports multiple tool calls."""
    response = LLMResponse(
        content="Making multiple calls",
        model="llama3",
        tool_calls=[
            ToolCall(name="tool1", arguments={}, id="call_1"),
            ToolCall(name="tool2", arguments={}, id="call_2"),
            ToolCall(name="tool3", arguments={}, id="call_3"),
        ]
    )

    assert len(response.tool_calls) == 3
    assert response.tool_calls[0].name == "tool1"
    assert response.tool_calls[1].name == "tool2"
    assert response.tool_calls[2].name == "tool3"
