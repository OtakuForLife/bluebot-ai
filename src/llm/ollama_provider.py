"""Ollama LLM provider implementation.

This module provides integration with Ollama for local LLM inference.
Ollama must be running locally (default: http://localhost:11434).
"""

import logging
from typing import Any, AsyncIterator, Optional

import aiohttp

from src.llm.base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
)


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider for local model inference.
    
    Ollama provides local LLM inference with models like llama2, codellama, mistral, etc.
    See https://ollama.ai for more information.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the Ollama provider.
        
        Args:
            config: Configuration for Ollama (model, temperature, etc.).
        """
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.logger = logging.getLogger(f"{__name__}.OllamaProvider")

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response from Ollama.
        
        Args:
            messages: List of messages in the conversation.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            
        Returns:
            LLMResponse containing the generated text.
            
        Raises:
            LLMProviderError: If the generation fails.
        """
        url = f"{self.base_url}/api/chat"
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise LLMProviderError(
                            f"HTTP {response.status}: {error_text}",
                            provider="Ollama",
                        )
                    
                    data = await response.json()
                    
                    return LLMResponse(
                        content=data["message"]["content"],
                        model=data.get("model", self.config.model),
                        finish_reason=data.get("done_reason"),
                        usage={
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                        },
                    )
        except aiohttp.ClientError as e:
            raise LLMProviderError(
                f"Failed to connect to Ollama: {e}",
                provider="Ollama",
                original_error=e,
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                provider="Ollama",
                original_error=e,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Ollama.
        
        Args:
            messages: List of messages in the conversation.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            
        Yields:
            Chunks of the generated response as they arrive.
            
        Raises:
            LLMProviderError: If the generation fails.
        """
        url = f"{self.base_url}/api/chat"
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise LLMProviderError(
                            f"HTTP {response.status}: {error_text}",
                            provider="Ollama",
                        )
                    
                    async for line in response.content:
                        if line:
                            import json
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                continue
        except aiohttp.ClientError as e:
            raise LLMProviderError(
                f"Failed to connect to Ollama: {e}",
                provider="Ollama",
                original_error=e,
            )

    async def preload_model(self) -> bool:
        """Pre-load the model into memory to avoid delays on first request.

        This sends a minimal request to Ollama to trigger model loading.
        Subsequent requests will be much faster since the model is already loaded.

        Returns:
            True if model was loaded successfully, False otherwise.
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.config.model,
            "prompt": "Hello",  # Minimal prompt to trigger model loading
            "stream": False,
            "options": {
                "num_predict": 1,  # Only generate 1 token
            },
        }

        try:
            self.logger.info(f"Pre-loading model '{self.config.model}'...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Model '{self.config.model}' loaded successfully")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"Failed to pre-load model: HTTP {response.status}: {error_text}")
                        return False
        except Exception as e:
            self.logger.warning(f"Failed to pre-load model: {e}")
            return False

    async def is_available(self) -> bool:
        """Check if Ollama is running and available.

        Returns:
            True if Ollama is available, False otherwise.
        """
        url = f"{self.base_url}/api/tags"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current Ollama model.
        
        Returns:
            Dictionary with model information.
        """
        return {
            "provider": "Ollama",
            "model": self.config.model,
            "base_url": self.base_url,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

