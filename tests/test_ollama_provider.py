"""Tests for Ollama LLM provider."""

import pytest

from src.agents.llm import LLMConfig, OllamaProvider


@pytest.fixture
def ollama_config() -> LLMConfig:
    """Create a test Ollama configuration."""
    return LLMConfig(
        model="llama2",
        temperature=0.7,
        max_tokens=1024,
        base_url="http://localhost:11434",
    )


@pytest.fixture
def ollama_provider(ollama_config: LLMConfig) -> OllamaProvider:
    """Create a test Ollama provider."""
    return OllamaProvider(ollama_config)


def test_ollama_provider_initialization(ollama_provider: OllamaProvider) -> None:
    """Test that Ollama provider initializes correctly."""
    assert ollama_provider.config.model == "llama2"
    assert ollama_provider.base_url == "http://localhost:11434"
    assert ollama_provider.config.temperature == 0.7
    assert ollama_provider.config.max_tokens == 1024


def test_get_model_info(ollama_provider: OllamaProvider) -> None:
    """Test getting model information."""
    info = ollama_provider.get_model_info()

    assert info["provider"] == "Ollama"
    assert info["model"] == "llama2"
    assert info["base_url"] == "http://localhost:11434"
    assert info["temperature"] == 0.7
    assert info["max_tokens"] == 1024


def test_llm_config_defaults() -> None:
    """Test that LLMConfig has sensible defaults."""
    config = LLMConfig(model="test-model")

    assert config.model == "test-model"
    assert config.temperature == 0.7  # Default temperature
    assert config.max_tokens == 4096  # Default max_tokens
    assert config.top_p == 1.0  # Default top_p
    assert config.timeout == 300  # Default timeout (5 minutes)
