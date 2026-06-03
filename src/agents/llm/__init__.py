"""LLM provider system for Bluebot AI.

This module provides a flexible abstraction layer for different LLM providers,
allowing easy swapping between Ollama, OpenAI, Anthropic, and other providers.
"""

from src.agents.llm.base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
)
from src.agents.llm.ollama_provider import OllamaProvider
from src.agents.llm.openai_provider import OpenAIProvider
from src.agents.llm.langchain_adapter import LangChainAdapter
from src.agents.llm.factory import ProviderFactory
from src.agents.llm.registry import ProviderRegistry

# Register all available providers
ProviderRegistry.register("ollama", OllamaProvider)
ProviderRegistry.register("openai", OpenAIProvider)

__all__ = [
    "BaseLLMProvider",
    "LLMConfig",
    "LLMMessage",
    "LLMProviderError",
    "LLMResponse",
    "OllamaProvider",
    "OpenAIProvider",
    "LangChainAdapter",
    "ProviderFactory",
    "ProviderRegistry",
]
