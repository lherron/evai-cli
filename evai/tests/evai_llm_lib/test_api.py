"""Tests for the high-level API functions and classes."""

import asyncio
import pytest
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from evai.evai_llm_lib.api import (
    ask, ask_sync,
    chat, chat_sync,
    ChatSession, SyncChatSession
)
from evai.evai_llm_lib.backends.base import (
    LLMProviderBackend as LLMProvider,
    ToolExecutorBackend as ToolExecutor,
    Message,
    ToolDefinition,
    ToolResult,
    LLMResponse as Response
)
from evai.evai_llm_lib.config import LLMLibConfig
from evai.evai_llm_lib.errors import LLMLibError

# Test fixtures

@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMProvider)
    provider.generate_response.return_value = Response(
        content="Test response",
        role="assistant",
        tool_calls=None
    )
    return provider

@pytest.fixture
def mock_tool_executor():
    """Create a mock tool executor."""
    executor = AsyncMock(spec=ToolExecutor)
    executor.available_tools = [
        ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}}
        )
    ]
    return executor

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return LLMLibConfig(
        anthropic_api_key="test_key",
        default_provider="anthropic",
        default_tool_executor=None
    )

# Test one-shot queries

@pytest.mark.asyncio
async def test_ask(mock_llm_provider):
    """Test the ask() function."""
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        response = await ask("Test prompt")
        
        assert response == "Test response"
        mock_create.assert_called_once_with(None, None)
        mock_llm_provider.initialize.assert_called_once()
        mock_llm_provider.generate_response.assert_called_once_with(
            messages=[Message(role="user", content="Test prompt")],
            max_tokens=None
        )

def test_ask_sync(mock_llm_provider):
    """Test the ask_sync() function."""
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        response = ask_sync("Test prompt")
        
        assert response == "Test response"
        mock_create.assert_called_once_with(None, None)
        mock_llm_provider.initialize.assert_called_once()
        mock_llm_provider.generate_response.assert_called_once()

# Test multi-turn chat

@pytest.mark.asyncio
async def test_chat_with_string_messages(mock_llm_provider):
    """Test chat() with string messages."""
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        messages = ["Hello", "How are you?"]
        response = await chat(messages)
        
        assert response == "Test response"
        mock_create.assert_called_once_with(None, None)
        mock_llm_provider.initialize.assert_called_once()
        mock_llm_provider.generate_response.assert_called_once()
        
        # Verify message conversion
        called_messages = mock_llm_provider.generate_response.call_args[1]["messages"]
        assert len(called_messages) == 2
        assert all(isinstance(m, Message) for m in called_messages)
        assert all(m.role == "user" for m in called_messages)

@pytest.mark.asyncio
async def test_chat_with_dict_messages(mock_llm_provider):
    """Test chat() with dict messages."""
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"}
        ]
        response = await chat(messages)
        
        assert response == "Test response"
        mock_create.assert_called_once_with(None, None)
        
        # Verify message conversion
        called_messages = mock_llm_provider.generate_response.call_args[1]["messages"]
        assert len(called_messages) == 3
        assert all(isinstance(m, Message) for m in called_messages)
        assert [m.role for m in called_messages] == ["user", "assistant", "user"]

def test_chat_sync(mock_llm_provider):
    """Test the chat_sync() function."""
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        messages = ["Hello", "How are you?"]
        response = chat_sync(messages)
        
        assert response == "Test response"
        mock_create.assert_called_once_with(None, None)
        mock_llm_provider.initialize.assert_called_once()
        mock_llm_provider.generate_response.assert_called_once()

# Test chat sessions

@pytest.mark.asyncio
async def test_chat_session(mock_llm_provider, mock_tool_executor):
    """Test the ChatSession class."""
    with patch("evai.evai_llm_lib.api.create_session_backends") as mock_create:
        mock_create.return_value = (mock_llm_provider, mock_tool_executor)
        
        async with ChatSession() as session:
            # Test sending a message
            response = await session.send_message("Hello")
            assert response == "Test response"
            
            # Test available tools
            tools = session.available_tools
            assert len(tools) == 1
            assert tools[0].name == "test_tool"
        
        # Verify cleanup
        mock_llm_provider.cleanup.assert_called_once()
        mock_tool_executor.cleanup.assert_called_once()

def test_sync_chat_session(mock_llm_provider, mock_tool_executor):
    """Test the SyncChatSession class."""
    with patch("evai.evai_llm_lib.api.create_session_backends") as mock_create:
        mock_create.return_value = (mock_llm_provider, mock_tool_executor)
        
        with SyncChatSession() as session:
            # Test sending a message
            response = session.send_message("Hello")
            assert response == "Test response"
            
            # Test available tools
            tools = session.available_tools
            assert len(tools) == 1
            assert tools[0].name == "test_tool"
        
        # Verify cleanup
        mock_llm_provider.cleanup.assert_called_once()
        mock_tool_executor.cleanup.assert_called_once()

# Test error cases

@pytest.mark.asyncio
async def test_chat_session_without_context():
    """Test using ChatSession without context manager."""
    session = ChatSession()
    
    with pytest.raises(LLMLibError):
        await session.send_message("Hello")
    
    assert session.available_tools is None

def test_sync_chat_session_without_context():
    """Test using SyncChatSession without context manager."""
    session = SyncChatSession()
    
    with pytest.raises(LLMLibError):
        session.send_message("Hello")
    
    assert session.available_tools is None

@pytest.mark.asyncio
async def test_provider_error(mock_llm_provider):
    """Test handling of provider errors."""
    mock_llm_provider.generate_response.side_effect = Exception("Provider error")
    
    with patch("evai.evai_llm_lib.api.create_llm_provider") as mock_create:
        mock_create.return_value = mock_llm_provider
        
        with pytest.raises(LLMLibError):
            await ask("Test prompt") 