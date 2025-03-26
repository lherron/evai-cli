"""Tests for the Anthropic backend."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from evai_llm_lib.backends.anthropic import AnthropicProvider
from evai_llm_lib.backends.base import Message, ToolDefinition, Response
from evai_llm_lib.config import LLMLibConfig
from evai_llm_lib.errors import LLMLibError

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock_client = AsyncMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[{"type": "text", "text": "Mock response"}],
        role="assistant",
        id="msg_12345",
        model="claude-3-sonnet-20240229",
        tool_use=None,
    )
    return mock_client

@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return LLMLibConfig(
        anthropic_api_key="test_key",
        default_model="claude-3-sonnet-20240229"
    )

@pytest.mark.asyncio
async def test_anthropic_initialization():
    """Test AnthropicProvider initialization."""
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        provider = AnthropicProvider(
            config=LLMLibConfig(anthropic_api_key="test_key")
        )
        
        await provider.initialize()
        
        mock_anthropic.assert_called_once_with(api_key="test_key")
        assert provider.client is not None

@pytest.mark.asyncio
async def test_anthropic_generate_response(mock_anthropic_client):
    """Test generating a response from Anthropic."""
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider(
            config=LLMLibConfig(anthropic_api_key="test_key")
        )
        await provider.initialize()
        
        messages = [
            Message(role="user", content="Hello")
        ]
        
        response = await provider.generate_response(messages)
        
        # Verify response
        assert response.content == "Mock response"
        assert response.role == "assistant"
        assert response.tool_calls is None
        
        # Verify client call
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert call_args["messages"] == [{"role": "user", "content": "Hello"}]
        assert call_args["model"] == "claude-3-sonnet-20240229"
        assert call_args["max_tokens"] is None

@pytest.mark.asyncio
async def test_anthropic_with_tools(mock_anthropic_client):
    """Test generating a response with tools from Anthropic."""
    # Create a mock response with tool use
    tool_use_response = MagicMock(
        content=[],
        role="assistant",
        id="msg_12345",
        model="claude-3-sonnet-20240229"
    )
    tool_use_response.content = [
        {
            "type": "tool_use",
            "id": "tool_use_12345",
            "name": "test_tool",
            "input": {"param1": "value1"}
        }
    ]
    
    mock_anthropic_client.messages.create.return_value = tool_use_response
    
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider(
            config=LLMLibConfig(anthropic_api_key="test_key")
        )
        await provider.initialize()
        
        messages = [
            Message(role="user", content="Use the test tool")
        ]
        
        tools = [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                parameters={
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    }
                }
            )
        ]
        
        response = await provider.generate_response(messages, tools=tools)
        
        # Verify tool calls in response
        assert response.content == ""
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "test_tool"
        assert response.tool_calls[0].parameters == {"param1": "value1"}
        
        # Verify client call
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert len(call_args["tools"]) == 1
        assert call_args["tools"][0]["name"] == "test_tool"

@pytest.mark.asyncio
async def test_anthropic_with_multimodal(mock_anthropic_client):
    """Test generating a response with multimodal content."""
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_anthropic.return_value = mock_anthropic_client
        
        provider = AnthropicProvider(
            config=LLMLibConfig(anthropic_api_key="test_key")
        )
        await provider.initialize()
        
        # Message with image content
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "base64data"}}
                ]
            )
        ]
        
        response = await provider.generate_response(messages)
        
        # Verify message conversion
        call_args = mock_anthropic_client.messages.create.call_args[1]
        assert isinstance(call_args["messages"][0]["content"], list)
        assert len(call_args["messages"][0]["content"]) == 2
        assert call_args["messages"][0]["content"][0]["type"] == "text"
        assert call_args["messages"][0]["content"][1]["type"] == "image"

@pytest.mark.asyncio
async def test_anthropic_error_handling():
    """Test error handling in the Anthropic provider."""
    mock_client = AsyncMock()
    error_response = Exception("API Error")
    mock_client.messages.create.side_effect = error_response
    
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_anthropic.return_value = mock_client
        
        provider = AnthropicProvider(
            config=LLMLibConfig(anthropic_api_key="test_key")
        )
        await provider.initialize()
        
        messages = [
            Message(role="user", content="Hello")
        ]
        
        with pytest.raises(LLMLibError) as excinfo:
            await provider.generate_response(messages)
        
        assert "API Error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_anthropic_cleanup():
    """Test cleanup method."""
    provider = AnthropicProvider(
        config=LLMLibConfig(anthropic_api_key="test_key")
    )
    # No client yet
    await provider.cleanup()
    
    # With client
    with patch("evai_llm_lib.backends.anthropic.AsyncAnthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        
        await provider.initialize()
        assert provider.client is not None
        
        await provider.cleanup()
        # Nothing to verify as the client doesn't need explicit cleanup 