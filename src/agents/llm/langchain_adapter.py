"""LangChain adapter for BaseLLMProvider.

This module provides a wrapper that makes our BaseLLMProvider compatible with LangChain's
message types and output formats, allowing it to be used with LangChain agents and tools.
"""

import asyncio
import json
from typing import Any, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from opentelemetry import trace as _otel_trace
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues

from src.agents.llm.base_provider import BaseLLMProvider, LLMMessage, LLMProviderError, ToolCall

_tracer = _otel_trace.get_tracer(__name__)


class LangChainAdapter:
    """Adapter that wraps BaseLLMProvider to work with LangChain.

    This allows our custom LLM providers (Ollama, OpenAI, etc.) to be used with
    LangChain's agent framework and tools.
    """

    def __init__(self, provider: BaseLLMProvider):
        """Initialize the adapter.

        Args:
            provider: The BaseLLMProvider instance to wrap.
        """
        self.provider = provider
        self.bound_tools: Optional[list[BaseTool]] = None
        # Maps tool name → JSON Schema dict for the native tool-calling API.
        # Populated by bind_tools when AgentTool objects are supplied alongside
        # the LangChain StructuredTool wrappers.
        self._agent_tool_schemas: dict[str, dict] = {}

    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return f"langchain_adapter_{self.provider.__class__.__name__}"

    def bind_tools(
        self,
        tools: list[BaseTool],
        agent_tools: "Optional[list]" = None,
    ) -> "LangChainAdapter":
        """Bind tools to this model for tool calling.

        Args:
            tools: List of LangChain BaseTool wrappers to bind.
            agent_tools: Optional list of AgentTool objects whose
                ``parameters_schema`` dicts will be used as the authoritative
                JSON Schema for the native tool-calling API, overriding the
                schema inferred from the StructuredTool's function signature.

        Returns:
            A new LangChainAdapter instance with tools bound.
        """
        adapter = LangChainAdapter(self.provider)
        adapter.bound_tools = tools
        if agent_tools:
            adapter._agent_tool_schemas = {
                t.name: t.parameters_schema
                for t in agent_tools
                if t.parameters_schema is not None
            }
        return adapter

    def _convert_messages_to_provider_format(
        self, messages: list[BaseMessage]
    ) -> list[LLMMessage]:
        """Convert LangChain messages to our provider's format.

        Handles four message types correctly:
        - SystemMessage  → role "system"
        - HumanMessage   → role "user"
        - AIMessage      → role "assistant", with tool_calls preserved when present
        - ToolMessage    → role "tool", with tool_call_id linking it to the call

        Args:
            messages: List of LangChain BaseMessage objects.

        Returns:
            List of LLMMessage objects for our provider.
        """
        provider_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                provider_messages.append(LLMMessage(role="system", content=msg.content))

            elif isinstance(msg, HumanMessage):
                provider_messages.append(LLMMessage(role="user", content=msg.content))

            elif isinstance(msg, AIMessage):
                if msg.tool_calls:
                    # Preserve structured tool calls so the provider can forward
                    # them to the model in the correct native format.
                    native_tool_calls = [
                        {"function": {"name": tc["name"], "arguments": tc["args"]}}
                        for tc in msg.tool_calls
                    ]
                    provider_messages.append(LLMMessage(
                        role="assistant",
                        content=msg.content or "",
                        tool_calls=native_tool_calls,
                    ))
                else:
                    provider_messages.append(LLMMessage(
                        role="assistant",
                        content=msg.content or "",
                    ))

            elif isinstance(msg, ToolMessage):
                # Tool results must use role "tool" (not "user") so the model
                # understands them as responses to its own tool calls.
                provider_messages.append(LLMMessage(
                    role="tool",
                    content=str(msg.content),
                    tool_call_id=msg.tool_call_id,
                ))

            else:
                provider_messages.append(LLMMessage(role="user", content=str(msg.content)))

        return provider_messages

    def _convert_tools_to_provider_format(self) -> Optional[list[dict[str, Any]]]:
        """Convert bound tools to provider format.

        Parameter schemas are resolved in priority order:
        1. ``_agent_tool_schemas[name]`` — the Pydantic-derived schema supplied
           via ``bind_tools(agent_tools=...)``.  This is the most accurate source
           because it reflects the actual validation model used by the callback.
        2. ``tool.args_schema.schema()`` — the schema inferred from the
           StructuredTool's function signature.  This is often wrong for tools
           whose callbacks accept a plain ``dict``, yielding a useless
           ``{"params": {"type": "object"}}`` schema.
        3. ``{}`` — empty fallback; the model must rely on the description alone.

        Returns:
            List of tool definitions in provider format, or None if no tools bound.
        """
        if not self.bound_tools:
            return None

        tools = []
        for tool in self.bound_tools:
            # Prefer the explicit Pydantic schema when available.
            schema = self._agent_tool_schemas.get(tool.name)
            if schema is None and tool.args_schema:
                schema = tool.args_schema.schema()

            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": schema or {},
            }
            tools.append(tool_def)

        return tools

    def _convert_provider_tool_calls_to_langchain(
        self, tool_calls: Optional[list[ToolCall]]
    ) -> list[dict[str, Any]]:
        """Convert provider tool calls to LangChain format.

        Args:
            tool_calls: List of ToolCall objects from provider.

        Returns:
            List of LangChain-formatted tool call dictionaries.
        """
        if not tool_calls:
            return []

        langchain_tool_calls = []
        for call in tool_calls:
            langchain_tool_calls.append({
                "name": call.name,
                "args": call.arguments,
                "id": call.id,
            })
        return langchain_tool_calls

    def invoke(self, messages: list[BaseMessage], **kwargs: Any) -> AIMessage:
        """Invoke the model with messages (synchronous wrapper).

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional generation parameters.

        Returns:
            AIMessage with the generated response.
        """
        # Run the async version in a new event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.ainvoke(messages, **kwargs))

    async def ainvoke(self, messages: list[BaseMessage], **kwargs: Any) -> AIMessage:
        """Invoke the model with messages asynchronously.

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional generation parameters.

        Returns:
            AIMessage with the generated response.
        """
        result = await self._generate_with_tools(messages, **kwargs)
        return result

    async def _generate_with_tools(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> AIMessage:
        """Generate a response with tool calling support.

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional generation parameters.

        Returns:
            AIMessage with the generated response and tool calls if any.
        """
        with _tracer.start_as_current_span("llm.generate") as span:
            span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.LLM.value,
            )
            span.set_attribute(SpanAttributes.LLM_MODEL_NAME, self.provider.config.model)

            # Record the full conversation going IN to the LLM.
            input_parts: list[str] = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    role = "system"
                elif isinstance(msg, HumanMessage):
                    role = "user"
                elif isinstance(msg, AIMessage):
                    role = "assistant"
                elif isinstance(msg, ToolMessage):
                    role = f"tool({msg.tool_call_id})"
                else:
                    role = type(msg).__name__
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                input_parts.append(f"[{role}]\n{content}")
            span.set_attribute(SpanAttributes.INPUT_VALUE, "\n\n---\n\n".join(input_parts))

            if self.bound_tools:
                span.set_attribute(
                    "llm.tools",
                    ", ".join(t.name for t in self.bound_tools),
                )

            provider_messages = self._convert_messages_to_provider_format(messages)
            tools = self._convert_tools_to_provider_format()
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")

            try:
                response = await self.provider.generate(
                    messages=provider_messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                tool_calls = self._convert_provider_tool_calls_to_langchain(response.tool_calls)

                # Record what the LLM returned.
                if tool_calls:
                    tc_lines = "\n".join(
                        f"→ {tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"
                        for tc in tool_calls
                    )
                    span.set_attribute(SpanAttributes.OUTPUT_VALUE, f"[TOOL CALLS]\n{tc_lines}")
                    return AIMessage(content=response.content, tool_calls=tool_calls)
                else:
                    span.set_attribute(SpanAttributes.OUTPUT_VALUE, response.content or "(empty)")
                    return AIMessage(content=response.content)

            except LLMProviderError as e:
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, f"[ERROR] {e}")
                span.record_exception(e)
                raise RuntimeError(f"LLM generation failed: {e}") from e

    def generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        """Generate a response (synchronous version).

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional generation parameters.

        Returns:
            ChatResult with the generated response.
        """
        # Run the async version in a new event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.agenerate(messages, **kwargs))

    async def agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        """Generate a response asynchronously.

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional generation parameters.

        Returns:
            ChatResult with the generated response.
        """
        message = await self._generate_with_tools(messages, **kwargs)
        generation = ChatGeneration(message=message)

        return ChatResult(
            generations=[generation],
            llm_output={
                "model": self.provider.config.model,
            },
        )
