"""Tests for LangChainAdapter."""

from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from src.agents.llm.base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMResponse,
    ToolCall,
)
from src.agents.llm.langchain_adapter import LangChainAdapter
from src.agents.llm.tool import AgentTool


class MockProvider(BaseLLMProvider):
    """Minimal provider stub for adapter tests."""

    def __init__(self, response: Optional[LLMResponse] = None) -> None:
        super().__init__(LLMConfig(model="test-model"))
        self.response = response or LLMResponse(content="hello", model="test-model")
        self.last_messages: Optional[list[LLMMessage]] = None
        self.last_tools: Optional[list[dict[str, Any]]] = None
        self.last_temperature: Optional[float] = None
        self.last_max_tokens: Optional[int] = None

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        self.last_messages = messages
        self.last_tools = tools
        self.last_temperature = temperature
        self.last_max_tokens = max_tokens
        return self.response

    async def generate_stream(self, messages: list[LLMMessage], **kwargs: Any):
        yield self.response.content

    async def is_available(self) -> bool:
        return True

    def get_model_info(self) -> dict[str, Any]:
        return {"provider": "Mock", "model": self.config.model}


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def adapter(provider: MockProvider) -> LangChainAdapter:
    return LangChainAdapter(provider)


def test_llm_type_property(adapter: LangChainAdapter) -> None:
    assert adapter._llm_type == "langchain_adapter_MockProvider"


def test_convert_messages_all_roles(adapter: LangChainAdapter) -> None:
    messages = adapter._convert_messages_to_provider_format([
        SystemMessage(content="sys"),
        HumanMessage(content="user"),
        AIMessage(content="assistant", tool_calls=[
            {"name": "search", "args": {"q": "x"}, "id": "call_1"},
        ]),
        ToolMessage(content="result", tool_call_id="call_1"),
    ])

    assert [m.role for m in messages] == ["system", "user", "assistant", "tool"]
    assert messages[2].tool_calls == [
        {"function": {"name": "search", "arguments": {"q": "x"}}},
    ]
    assert messages[3].tool_call_id == "call_1"
    assert messages[3].content == "result"


def test_convert_messages_unknown_type_falls_back_to_user(adapter: LangChainAdapter) -> None:
    unknown = MagicMock()
    unknown.content = "fallback"
    messages = adapter._convert_messages_to_provider_format([unknown])
    assert messages[0].role == "user"
    assert messages[0].content == "fallback"


def test_convert_tools_returns_none_when_unbound(adapter: LangChainAdapter) -> None:
    assert adapter._convert_tools_to_provider_format() is None


def test_bind_tools_uses_agent_tool_schema(adapter: LangChainAdapter) -> None:
    def noop(**kwargs: Any) -> str:
        return "ok"

    lc_tool = StructuredTool.from_function(
        func=noop,
        name="create_file",
        description="Create a file",
    )
    agent_tool = AgentTool(
        name="create_file",
        description="Create a file",
        callback=lambda _: None,
        parameters_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )

    bound = adapter.bind_tools([lc_tool], agent_tools=[agent_tool])
    tools = bound._convert_tools_to_provider_format()

    assert tools is not None
    assert tools[0]["parameters"] == agent_tool.parameters_schema


def test_convert_provider_tool_calls_to_langchain(adapter: LangChainAdapter) -> None:
    converted = adapter._convert_provider_tool_calls_to_langchain([
        ToolCall(name="read_file", arguments={"path": "a.txt"}, id="id-1"),
    ])
    assert converted == [{"name": "read_file", "args": {"path": "a.txt"}, "id": "id-1"}]


@pytest.mark.asyncio
async def test_ainvoke_returns_text_response(provider: MockProvider) -> None:
    lc_adapter = LangChainAdapter(provider)
    result = await lc_adapter.ainvoke([HumanMessage(content="hi")])

    assert isinstance(result, AIMessage)
    assert result.content == "hello"
    assert not result.tool_calls
    assert provider.last_messages == [LLMMessage(role="user", content="hi")]


@pytest.mark.asyncio
async def test_ainvoke_returns_tool_calls(provider: MockProvider) -> None:
    provider.response = LLMResponse(
        content="",
        model="test-model",
        tool_calls=[ToolCall(name="list_files", arguments={}, id="tc-1")],
    )
    lc_adapter = LangChainAdapter(provider)
    result = await lc_adapter.ainvoke([HumanMessage(content="list files")])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "list_files"
    assert result.tool_calls[0]["args"] == {}
    assert result.tool_calls[0]["id"] == "tc-1"


@pytest.mark.asyncio
async def test_ainvoke_wraps_provider_error(provider: MockProvider) -> None:
    async def failing_generate(*args: Any, **kwargs: Any) -> LLMResponse:
        raise LLMProviderError("boom", provider="Mock")

    provider.generate = failing_generate  # type: ignore[method-assign]
    lc_adapter = LangChainAdapter(provider)

    with pytest.raises(RuntimeError, match="LLM generation failed"):
        await lc_adapter.ainvoke([HumanMessage(content="fail")])


@pytest.mark.asyncio
async def test_agenerate_returns_chat_result(provider: MockProvider) -> None:
    lc_adapter = LangChainAdapter(provider)
    result = await lc_adapter.agenerate([HumanMessage(content="hi")])

    assert result.generations[0].message.content == "hello"
    assert result.llm_output == {"model": "test-model"}


def test_invoke_sync_wrapper(provider: MockProvider) -> None:
    lc_adapter = LangChainAdapter(provider)
    result = lc_adapter.invoke([HumanMessage(content="sync")])

    assert isinstance(result, AIMessage)
    assert result.content == "hello"


def test_generate_sync_wrapper(provider: MockProvider) -> None:
    lc_adapter = LangChainAdapter(provider)
    result = lc_adapter.generate([HumanMessage(content="sync")])

    assert result.generations[0].message.content == "hello"
