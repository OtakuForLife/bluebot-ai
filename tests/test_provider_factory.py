"""Tests for ProviderFactory class."""

import pytest

from src.agents.llm.base_provider import LLMConfig, LLMProviderError
from src.agents.llm.factory import ProviderFactory
from src.agents.llm.registry import ProviderRegistry
from src.agents.llm.ollama_provider import OllamaProvider
from src.agents.llm.openai_provider import OpenAIProvider


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config


@pytest.fixture(autouse=True)
def register_providers():
    """Register providers before all tests."""
    ProviderRegistry.register("ollama", OllamaProvider)
    ProviderRegistry.register("openai", OpenAIProvider)
    yield
    # Cleanup
    ProviderRegistry.unregister("ollama")
    ProviderRegistry.unregister("openai")


def test_provider_factory_create_with_mock_provider() -> None:
    """Test creating a mock provider."""
    # Register a mock provider
    ProviderRegistry.register("mock", MockProvider)

    config = LLMConfig(provider="mock", model="test-model")
    provider = ProviderFactory.create(config)

    assert provider is not None
    assert isinstance(provider, MockProvider)
    assert provider.config == config

    # Cleanup
    ProviderRegistry.unregister("mock")


def test_provider_factory_create_with_registered_provider() -> None:
    """Test creating a provider that's registered."""
    ProviderRegistry.register("test_provider", MockProvider)

    config = LLMConfig(provider="test_provider", model="custom")
    provider = ProviderFactory.create(config)

    assert isinstance(provider, MockProvider)
    assert provider.config.model == "custom"

    # Cleanup
    ProviderRegistry.unregister("test_provider")


def test_provider_factory_create_with_unknown_provider() -> None:
    """Test that creating an unknown provider raises an error."""
    # Clear registry to ensure our test is isolated
    ProviderRegistry.clear()

    config = LLMConfig(provider="unknown_provider")

    with pytest.raises(LLMProviderError) as exc_info:
        ProviderFactory.create(config)

    assert "Unknown provider" in str(exc_info.value)
    assert "unknown_provider" in str(exc_info.value)


def test_provider_factory_error_message_includes_available_providers() -> None:
    """Test that error message includes available providers."""
    # Register a mock provider
    ProviderRegistry.register("mock_provider", MockProvider)

    # Try to create a non-existent provider
    config = LLMConfig(provider="nonexistent")
    with pytest.raises(LLMProviderError) as exc_info:
        ProviderFactory.create(config)

    error_msg = str(exc_info.value)
    assert "Available providers" in error_msg

    # Cleanup
    ProviderRegistry.unregister("mock_provider")


def test_provider_factory_uses_mock_as_default() -> None:
    """Test that factory defaults to registered provider."""
    # Clear and register a mock as the only option
    ProviderRegistry.clear()
    ProviderRegistry.register("mock", MockProvider)

    config = LLMConfig(provider="mock")
    provider = ProviderFactory.create(config)

    assert isinstance(provider, MockProvider)

    # Cleanup
    ProviderRegistry.clear()


def test_provider_factory_preserves_config() -> None:
    """Test that factory preserves all config settings."""
    ProviderRegistry.register("test", MockProvider)

    config = LLMConfig(
        provider="test",
        model="custom-model",
        temperature=0.5,
        max_tokens=2048,
        top_p=0.9,
        timeout=120,
        base_url="http://localhost:11434",
        api_key="test-key"
    )

    provider = ProviderFactory.create(config)

    assert isinstance(provider, MockProvider)
    assert provider.config.model == "custom-model"
    assert provider.config.temperature == 0.5
    assert provider.config.max_tokens == 2048
    assert provider.config.top_p == 0.9
    assert provider.config.timeout == 120
    assert provider.config.base_url == "http://localhost:11434"
    assert provider.config.api_key == "test-key"

    # Cleanup
    ProviderRegistry.unregister("test")
