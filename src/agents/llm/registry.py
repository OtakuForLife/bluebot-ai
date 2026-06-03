"""Provider registry for LLM providers.

This module provides a centralized registry for registering and retrieving
LLM providers by name. This allows for easy addition of new providers and
runtime provider selection.
"""

from typing import Callable, Dict, Optional, Type

from src.agents.llm.base_provider import BaseLLMProvider, LLMConfig


class ProviderRegistry:
    """Registry for LLM providers.

    This class maintains a mapping of provider names to provider classes,
    allowing for easy instantiation of providers by name.
    """

    _providers: Dict[str, Type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[BaseLLMProvider]) -> None:
        """Register an LLM provider.

        Args:
            name: The name to register the provider under (e.g., "ollama", "openai").
            provider_class: The provider class to register.
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseLLMProvider]]:
        """Get a registered provider by name.

        Args:
            name: The name of the provider to retrieve.

        Returns:
            The provider class if found, None otherwise.
        """
        return cls._providers.get(name.lower())

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            List of registered provider names.
        """
        return sorted(cls._providers.keys())

    @classmethod
    def create(cls, name: str, config: LLMConfig) -> Optional[BaseLLMProvider]:
        """Create an instance of a registered provider.

        Args:
            name: The name of the provider to create.
            config: Configuration for the provider.

        Returns:
            A provider instance if the provider is registered, None otherwise.
        """
        provider_class = cls.get(name)
        if provider_class is None:
            return None
        return provider_class(config)

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a provider.

        Args:
            name: The name of the provider to unregister.

        Returns:
            True if the provider was unregistered, False if it wasn't registered.
        """
        name = name.lower()
        if name in cls._providers:
            del cls._providers[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers."""
        cls._providers.clear()
