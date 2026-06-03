"""Provider factory for LLM providers.

This module provides a factory for creating LLM provider instances based on
configuration. It uses the ProviderRegistry to find and instantiate providers.
"""

from src.agents.llm.base_provider import BaseLLMProvider, LLMConfig, LLMProviderError
from src.agents.llm.registry import ProviderRegistry


class ProviderFactory:
    """Factory for creating LLM provider instances.

    This class uses the ProviderRegistry to find and instantiate providers
    based on the provider name in the LLMConfig.
    """

    @staticmethod
    def create(config: LLMConfig) -> BaseLLMProvider:
        """Create an LLM provider instance based on the configuration.

        Args:
            config: Configuration for the LLM provider.

        Returns:
            An instance of the requested LLM provider.

        Raises:
            LLMProviderError: If the provider is not registered or cannot be created.
        """
        provider_name = config.provider or "ollama"

        provider_class = ProviderRegistry.get(provider_name)
        if provider_class is None:
            available = ProviderRegistry.list_providers()
            raise LLMProviderError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {', '.join(available)}",
                provider="ProviderFactory",
            )

        return provider_class(config)

    @staticmethod
    def create_default() -> BaseLLMProvider:
        """Create an LLM provider with default configuration.

        Returns:
            An instance of the default LLM provider.
        """
        config = LLMConfig()
        return ProviderFactory.create(config)
