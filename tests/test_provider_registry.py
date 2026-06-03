"""Tests for ProviderRegistry class."""

import pytest

from src.agents.llm.base_provider import LLMConfig
from src.agents.llm.registry import ProviderRegistry


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config


class MockProvider2:
    """Another mock provider for testing."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config


def test_provider_registry_register() -> None:
    """Test that a provider can be registered."""
    # Register a provider
    ProviderRegistry.register("mock", MockProvider)

    # Get the provider
    provider_class = ProviderRegistry.get("mock")
    assert provider_class == MockProvider

    # Cleanup
    ProviderRegistry.unregister("mock")


def test_provider_registry_register_case_insensitive() -> None:
    """Test that provider registration is case-insensitive."""
    ProviderRegistry.register("MockProvider", MockProvider)

    # Should be able to retrieve with different cases
    assert ProviderRegistry.get("mockprovider") == MockProvider
    assert ProviderRegistry.get("MOCKPROVIDER") == MockProvider
    assert ProviderRegistry.get("MockProvider") == MockProvider

    ProviderRegistry.unregister("MockProvider")


def test_provider_registry_list_providers() -> None:
    """Test listing all registered providers."""
    # Clear any existing providers
    ProviderRegistry.clear()

    # Register multiple providers
    ProviderRegistry.register("provider1", MockProvider)
    ProviderRegistry.register("provider2", MockProvider2)

    # List providers
    providers = ProviderRegistry.list_providers()

    assert len(providers) >= 2
    assert "provider1" in providers
    assert "provider2" in providers
    assert isinstance(providers, list)

    # Cleanup
    ProviderRegistry.clear()


def test_provider_registry_create() -> None:
    """Test creating a provider instance."""
    ProviderRegistry.register("mock", MockProvider)

    config = LLMConfig(model="test-model")
    provider = ProviderRegistry.create("mock", config)

    assert isinstance(provider, MockProvider)
    assert provider.config == config

    ProviderRegistry.unregister("mock")


def test_provider_registry_create_nonexistent() -> None:
    """Test creating a non-existent provider returns None."""
    config = LLMConfig()
    provider = ProviderRegistry.create("nonexistent_provider", config)

    assert provider is None


def test_provider_registry_unregister() -> None:
    """Test unregistering a provider."""
    ProviderRegistry.register("mock", MockProvider)

    # Verify it's registered
    assert ProviderRegistry.get("mock") == MockProvider

    # Unregister it
    result = ProviderRegistry.unregister("mock")
    assert result is True

    # Verify it's gone
    assert ProviderRegistry.get("mock") is None


def test_provider_registry_unregister_nonexistent() -> None:
    """Test unregistering a non-existent provider returns False."""
    result = ProviderRegistry.unregister("nonexistent_provider")
    assert result is False


def test_provider_registry_clear() -> None:
    """Test clearing all providers."""
    # Register some providers
    ProviderRegistry.register("mock1", MockProvider)
    ProviderRegistry.register("mock2", MockProvider2)

    assert len(ProviderRegistry.list_providers()) >= 2

    # Clear all
    ProviderRegistry.clear()

    # Verify all are gone
    # Note: This may still have ollama_provider and openai_provider registered
    # So we just verify the ones we added are gone
    assert ProviderRegistry.get("mock1") is None
    assert ProviderRegistry.get("mock2") is None


def test_provider_registry_multiple_registrations() -> None:
    """Test that multiple providers can coexist."""
    ProviderRegistry.register("mock1", MockProvider)
    ProviderRegistry.register("mock2", MockProvider2)

    config = LLMConfig()

    provider1 = ProviderRegistry.create("mock1", config)
    provider2 = ProviderRegistry.create("mock2", config)

    assert isinstance(provider1, MockProvider)
    assert isinstance(provider2, MockProvider2)
    assert provider1 is not provider2  # Different instances

    # Cleanup
    ProviderRegistry.unregister("mock1")
    ProviderRegistry.unregister("mock2")
