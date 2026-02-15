"""Base LLM provider interface.

This module defines the abstract interface that all LLM providers must implement.
This allows easy swapping between different AI providers (Ollama, OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMMessage:
    """A message in a conversation with an LLM.
    
    Attributes:
        role: The role of the message sender (system, user, assistant).
        content: The text content of the message.
    """
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider.
    
    Attributes:
        content: The generated text content.
        model: The model that generated the response.
        finish_reason: Why the generation stopped (e.g., "stop", "length").
        usage: Token usage information (if available).
    """
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, int]] = None


@dataclass
class LLMConfig:
    """Configuration for an LLM provider.
    
    Attributes:
        model: The model name/identifier to use.
        temperature: Sampling temperature (0.0 to 2.0, higher = more random).
        max_tokens: Maximum tokens to generate.
        top_p: Nucleus sampling parameter.
        timeout: Request timeout in seconds.
        base_url: Base URL for the API (provider-specific).
        api_key: API key for authentication (if required).
    """
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    timeout: int = 60
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    All LLM providers (Ollama, OpenAI, Anthropic, etc.) must implement this interface.
    This ensures a consistent API regardless of the underlying provider.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the LLM provider.
        
        Args:
            config: Configuration for the LLM provider.
        """
        self.config = config

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            messages: List of messages in the conversation.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            
        Returns:
            LLMResponse containing the generated text and metadata.
            
        Raises:
            LLMProviderError: If the generation fails.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """Generate a streaming response from the LLM.
        
        Args:
            messages: List of messages in the conversation.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            
        Yields:
            Chunks of the generated response as they arrive.
            
        Raises:
            LLMProviderError: If the generation fails.
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available and responding.
        
        Returns:
            True if the provider is available, False otherwise.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary with model information (name, context length, etc.).
        """
        pass


class LLMProviderError(Exception):
    """Exception raised when an LLM provider encounters an error."""
    
    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        """Initialize the error.
        
        Args:
            message: Error message.
            provider: Name of the provider that raised the error.
            original_error: The original exception (if any).
        """
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")

