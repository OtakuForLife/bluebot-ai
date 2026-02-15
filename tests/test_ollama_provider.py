"""Tests for the Ollama LLM provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm import LLMConfig, LLMMessage, OllamaProvider, LLMProviderError


@pytest.fixture
def ollama_config() -> LLMConfig:
    """Create a test Ollama configuration."""
    return LLMConfig(
        model="llama2",
        temperature=0.7,
        max_tokens=1024,
        base_url="http://localhost:11434",
    )


@pytest.fixture
def ollama_provider(ollama_config: LLMConfig) -> OllamaProvider:
    """Create a test Ollama provider."""
    return OllamaProvider(ollama_config)


def test_ollama_provider_initialization(ollama_provider: OllamaProvider) -> None:
    """Test that the Ollama provider initializes correctly."""
    assert ollama_provider.config.model == "llama2"
    assert ollama_provider.base_url == "http://localhost:11434"
    assert ollama_provider.config.temperature == 0.7


def test_get_model_info(ollama_provider: OllamaProvider) -> None:
    """Test getting model information."""
    info = ollama_provider.get_model_info()
    
    assert info["provider"] == "Ollama"
    assert info["model"] == "llama2"
    assert info["base_url"] == "http://localhost:11434"
    assert info["temperature"] == 0.7


@pytest.mark.asyncio
async def test_generate_success(ollama_provider: OllamaProvider) -> None:
    """Test successful generation."""
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello!"),
    ]
    
    # Mock the aiohttp response
    mock_response_data = {
        "model": "llama2",
        "message": {"content": "Hello! How can I help you?"},
        "done_reason": "stop",
        "prompt_eval_count": 10,
        "eval_count": 8,
    }
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_post = AsyncMock()
        mock_post.status = 200
        mock_post.json = AsyncMock(return_value=mock_response_data)
        mock_post.__aenter__ = AsyncMock(return_value=mock_post)
        mock_post.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_post
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        response = await ollama_provider.generate(messages)
        
        assert response.content == "Hello! How can I help you?"
        assert response.model == "llama2"
        assert response.finish_reason == "stop"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 8


@pytest.mark.asyncio
async def test_generate_http_error(ollama_provider: OllamaProvider) -> None:
    """Test generation with HTTP error."""
    messages = [LLMMessage(role="user", content="Hello!")]
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_post = AsyncMock()
        mock_post.status = 500
        mock_post.text = AsyncMock(return_value="Internal Server Error")
        mock_post.__aenter__ = AsyncMock(return_value=mock_post)
        mock_post.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_post
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        with pytest.raises(LLMProviderError) as exc_info:
            await ollama_provider.generate(messages)
        
        assert "HTTP 500" in str(exc_info.value)
        assert exc_info.value.provider == "Ollama"


@pytest.mark.asyncio
async def test_is_available_success(ollama_provider: OllamaProvider) -> None:
    """Test checking if Ollama is available (success)."""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_get = AsyncMock()
        mock_get.status = 200
        mock_get.__aenter__ = AsyncMock(return_value=mock_get)
        mock_get.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_get
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        available = await ollama_provider.is_available()
        assert available is True


@pytest.mark.asyncio
async def test_is_available_failure(ollama_provider: OllamaProvider) -> None:
    """Test checking if Ollama is available (failure)."""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.side_effect = Exception("Connection refused")
        
        available = await ollama_provider.is_available()
        assert available is False


@pytest.mark.asyncio
async def test_generate_with_custom_params(ollama_provider: OllamaProvider) -> None:
    """Test generation with custom temperature and max_tokens."""
    messages = [LLMMessage(role="user", content="Test")]
    
    mock_response_data = {
        "model": "llama2",
        "message": {"content": "Response"},
        "done_reason": "stop",
        "prompt_eval_count": 5,
        "eval_count": 3,
    }
    
    with patch("aiohttp.ClientSession") as mock_session:
        mock_post = AsyncMock()
        mock_post.status = 200
        mock_post.json = AsyncMock(return_value=mock_response_data)
        mock_post.__aenter__ = AsyncMock(return_value=mock_post)
        mock_post.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_post
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        response = await ollama_provider.generate(
            messages,
            temperature=0.9,
            max_tokens=2048,
        )
        
        assert response.content == "Response"
        
        # Verify the custom parameters were passed
        call_args = mock_session_instance.post.call_args
        payload = call_args[1]["json"]
        assert payload["options"]["temperature"] == 0.9
        assert payload["options"]["num_predict"] == 2048

