"""Ollama LLM provider implementation.

This module provides integration with Ollama for local LLM inference.
Ollama must be running locally (default: http://localhost:11434).
"""

import json
import logging
import re
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

    def _parse_tool_calls(self, content: str) -> Optional[List[ToolCall]]:
        """Parse tool calls from the response content.

        Args:
            content: The response content from the LLM.

        Returns:
            List of tool calls, or None if no tool calls found.
        """
        # Look for JSON code blocks
        json_block_pattern = r'```json\s*(\[.*?\])\s*```'
        match = re.search(json_block_pattern, content, re.DOTALL)

        if not match:
            # Try to find JSON array without code block
            array_pattern = r'\[\s*\{.*?\}\s*\]'
            match = re.search(array_pattern, content, re.DOTALL)

        if match:
            try:
                tool_calls_data = json.loads(match.group(1) if '```json' in match.group(0) else match.group(0))
                tool_calls = []
                for i, call in enumerate(tool_calls_data):
                    tool_calls.append(
                        ToolCall(
                            name=call.get("name", ""),
                            arguments=call.get("arguments", {}),
                            id=f"call_{i}",
                        )
                    )
                return tool_calls
            except json.JSONDecodeError as e:
                self.logger.debug(f"Failed to parse tool calls: {e}")

        return None

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: Optional[List[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response from Ollama.

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
        url = f"{self.base_url}/api/chat"

        # Build the message list in Ollama's native format.
        # assistant messages that carry tool calls use the "tool_calls" field;
        # tool-result messages use role "tool" with a "tool_call_id".
        ollama_messages: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            ollama_messages.append(entry)

        # Convert tools to Ollama's native function-calling format.
        # Ollama passes these directly to the model's tool-calling layer —
        # no prompt injection needed.
        ollama_tools: Optional[list[dict[str, Any]]] = None
        if tools:
            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    },
                }
                for t in tools
            ]

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }
        if ollama_tools:
            payload["tools"] = ollama_tools

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
                    msg_data = data["message"]
                    content: str = msg_data.get("content", "") or ""

                    # Prefer native tool_calls from the API response; fall back
                    # to text-based JSON parsing for models that don't support
                    # the native tool-calling protocol.
                    tool_calls: Optional[List[ToolCall]] = None
                    native_calls = msg_data.get("tool_calls") or []
                    if native_calls:
                        tool_calls = []
                        for i, tc in enumerate(native_calls):
                            fn = tc.get("function", {})
                            args = fn.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except json.JSONDecodeError:
                                    args = {}
                            tool_calls.append(ToolCall(
                                name=fn.get("name", ""),
                                arguments=args,
                                id=f"call_{i}",
                            ))
                    elif tools and content:
                        # Fallback: model returned JSON tool calls in text form.
                        tool_calls = self._parse_tool_calls(content)

                    return LLMResponse(
                        content=content,
                        model=data.get("model", self.config.model),
                        finish_reason=data.get("done_reason"),
                        usage={
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                        },
                        tool_calls=tool_calls,
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
        tools: Optional[List[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Ollama.

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
        url = f"{self.base_url}/api/chat"

        # Build native-format message list (mirrors generate()).
        ollama_messages: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            ollama_messages.append(entry)

        ollama_tools: Optional[list[dict[str, Any]]] = None
        if tools:
            ollama_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    },
                }
                for t in tools
            ]

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }
        if ollama_tools:
            payload["tools"] = ollama_tools

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
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                # Ollama streaming may include non-JSON lines (empty, control messages)
                                self.logger.debug(f"Skipping non-JSON line in stream: {line!r}")
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

