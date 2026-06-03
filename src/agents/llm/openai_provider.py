"""OpenAI LLM provider implementation.

This module provides integration with the OpenAI API for cloud-based LLM inference.
See https://platform.openai.com for more information.
"""

import json
import logging
from typing import Any, AsyncIterator, Optional, List

import aiohttp

from src.agents.llm.base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    ToolCall,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider for cloud-based model inference.

    Supports OpenAI's API with models like gpt-4, gpt-3.5-turbo, etc.
    Requires an API key for authentication.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the OpenAI provider.

        Args:
            config: Configuration for OpenAI (model, temperature, api_key, etc.).
        """
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.api_key = config.api_key
        self.logger = logging.getLogger(f"{__name__}.OpenAIProvider")

        if not self.api_key:
            self.logger.warning("No API key provided for OpenAI provider")

    def _convert_messages_to_openai_format(
        self, messages: list[LLMMessage]
    ) -> list[dict]:
        """Convert our LLMMessage format to OpenAI format.

        Args:
            messages: List of LLMMessage objects.

        Returns:
            List of OpenAI-formatted message dictionaries.
        """
        openai_messages = []
        for msg in messages:
            role = msg.role
            if role == "assistant":
                role = "assistant"
            elif role == "user":
                role = "user"
            elif role == "system":
                role = "system"
            else:
                role = "user"

            openai_messages.append({"role": role, "content": msg.content})

        return openai_messages

    def _convert_tools_to_openai_format(self, tools: List[dict[str, Any]]) -> list[dict]:
        """Convert our tool format to OpenAI format.

        Args:
            tools: List of tool definitions.

        Returns:
            List of OpenAI-formatted tool dictionaries.
        """
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                }
            })
        return openai_tools

    def _parse_tool_calls(self, openai_tool_calls: list) -> List[ToolCall]:
        """Parse OpenAI tool call format to our ToolCall format.

        Args:
            openai_tool_calls: List of OpenAI tool call objects.

        Returns:
            List of ToolCall objects.
        """
        tool_calls = []
        for call in openai_tool_calls:
            function = call.get("function", {})
            tool_calls.append(
                ToolCall(
                    name=function.get("name", ""),
                    arguments=json.loads(function.get("arguments", "{}")),
                    id=call.get("id", ""),
                )
            )
        return tool_calls

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: Optional[List[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response from OpenAI.

        Args:
            messages: List of messages in the conversation.
            tools: Optional list of tools available to the LLM.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.

        Returns:
            LLMResponse containing the generated text.

        Raises:
            LLMProviderError: If the generation fails.
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.config.model,
            "messages": self._convert_messages_to_openai_format(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
        }

        if tools:
            payload["tools"] = self._convert_tools_to_openai_format(tools)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise LLMProviderError(
                            f"HTTP {response.status}: {error_text}",
                            provider="OpenAI",
                        )

                    data = await response.json()
                    choice = data["choices"][0]
                    message = choice["message"]

                    # Parse tool calls if present
                    tool_calls = None
                    if "tool_calls" in message and message["tool_calls"]:
                        tool_calls = self._parse_tool_calls(message["tool_calls"])

                    usage = data.get("usage", {})

                    return LLMResponse(
                        content=message.get("content", ""),
                        model=data.get("model", self.config.model),
                        finish_reason=choice.get("finish_reason"),
                        usage={
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        tool_calls=tool_calls,
                    )
        except aiohttp.ClientError as e:
            raise LLMProviderError(
                f"Failed to connect to OpenAI: {e}",
                provider="OpenAI",
                original_error=e,
            )
        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                provider="OpenAI",
                original_error=e,
            )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[List[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from OpenAI.

        Args:
            messages: List of messages in the conversation.
            tools: Optional list of tools available to the LLM.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.

        Yields:
            Chunks of the generated response as they arrive.

        Raises:
            LLMProviderError: If the generation fails.
        """
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.config.model,
            "messages": self._convert_messages_to_openai_format(messages),
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "top_p": self.config.top_p,
            "stream": True,
        }

        if tools:
            payload["tools"] = self._convert_tools_to_openai_format(tools)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise LLMProviderError(
                            f"HTTP {response.status}: {error_text}",
                            provider="OpenAI",
                        )

                    async for line in response.content:
                        if line:
                            line_text = line.decode("utf-8")
                            if line_text.startswith("data: "):
                                data_str = line_text[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    import json as json_module
                                    data = json_module.loads(data_str)
                                    delta = data["choices"][0]["delta"]
                                    if "content" in delta:
                                        yield delta["content"]
                                except (json_module.JSONDecodeError, KeyError, IndexError) as e:
                                    self.logger.debug(f"Skipping malformed SSE line: {data_str[:100]}, error: {e}")
                                    continue
        except aiohttp.ClientError as e:
            raise LLMProviderError(
                f"Failed to connect to OpenAI: {e}",
                provider="OpenAI",
                original_error=e,
            )

    async def is_available(self) -> bool:
        """Check if OpenAI is available.

        Returns:
            True if OpenAI is available, False otherwise.
        """
        if not self.api_key:
            return False

        url = f"{self.base_url}/models"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current OpenAI model.

        Returns:
            Dictionary with model information.
        """
        return {
            "provider": "OpenAI",
            "model": self.config.model,
            "base_url": self.base_url,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
