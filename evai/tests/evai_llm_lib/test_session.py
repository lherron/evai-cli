"""Tests for the LLMChatSession class."""

import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from evai.evai_llm_lib.session import LLMChatSession
from evai.evai_llm_lib.backends.base import (
    LLMProviderBackend,
    ToolExecutorBackend,
    Message,
    ToolDefinition,
    ToolResult,
    LLMResponse
)
from evai.evai_llm_lib.config import LLMLibConfig
from evai.evai_llm_lib.errors import LLMLibError

# Fixtures

@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMProviderBackend)
    provider.generate_response.return_value = LLMResponse(
        content="Test response",
        stop_reason="end_turn",
        tool_calls=None
    )
    return provider

@pytest.fixture
def mock_tool_executor():
    """Create a mock tool executor."""
    executor = AsyncMock(spec=ToolExecutorBackend)
    executor.list_tools.return_value = [
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
    return LLMLibConfig()

@pytest.fixture
def chat_session(mock_llm_provider, mock_tool_executor, mock_config):
    """Create a chat session with mocked components."""
    session = LLMChatSession(
        llm_provider=mock_llm_provider,
        tool_executor=mock_tool_executor,
        config=mock_config
    )
    return session

# Basic functionality tests

@pytest.mark.asyncio
async def test_session_initialization(chat_session):
    """Test session initialization."""
    assert chat_session.messages == []
    assert chat_session.llm_provider is not None
    assert chat_session.tool_executor is not None
    
    # Test initialization
    await chat_session.initialize()
    chat_session.llm_provider.initialize.assert_called_once()
    chat_session.tool_executor.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_add_message(chat_session):
    """Test adding messages to the session."""
    # Add a user message
    await chat_session.add_user_message("Hello")
    assert len(chat_session.messages) == 1
    assert chat_session.messages[0].role == "user"
    assert chat_session.messages[0].content == "Hello"
    
    # Add an assistant message
    await chat_session.add_assistant_message("Hi there")
    assert len(chat_session.messages) == 2
    assert chat_session.messages[1].role == "assistant"
    assert chat_session.messages[1].content == "Hi there"
    
    # Add a message with custom content
    custom_content = [{"type": "text", "text": "With image"}]
    await chat_session.add_message(Message(role="user", content=custom_content))
    assert len(chat_session.messages) == 3
    assert chat_session.messages[2].role == "user"
    assert chat_session.messages[2].content == custom_content

@pytest.mark.asyncio
async def test_run_turn_simple(chat_session, mock_llm_provider):
    """Test running a simple turn without tools."""
    await chat_session.initialize()
    
    # Add a user message
    await chat_session.add_user_message("Hello")
    
    # Run the turn
    response = await chat_session.run_turn()
    
    # Verify the response
    assert response == "Test response"
    
    # Verify LLM was called
    mock_llm_provider.generate_response.assert_called_once()
    
    # Verify message was added to history
    assert len(chat_session.messages) == 2
    assert chat_session.messages[1].role == "assistant"
    assert chat_session.messages[1].content == "Test response"

@pytest.mark.asyncio
async def test_run_turn_with_tools(chat_session, mock_llm_provider, mock_tool_executor):
    """Test running a turn with tool calls."""
    await chat_session.initialize()
    
    # Set up the LLM to return a tool call
    tool_call = {
        "name": "test_tool",
        "arguments": {}
    }
    mock_llm_provider.generate_response.return_value = LLMResponse(
        content="",
        stop_reason="tool_calls",
        tool_calls=[tool_call]
    )
    
    # Set up the tool executor to return a result
    tool_result = ToolResult(
        success=True,
        result={"result": "success"}
    )
    mock_tool_executor.execute_tool.return_value = tool_result
    
    # Set up the LLM to return a final response after the tool call
    final_response = LLMResponse(
        content="Tool execution complete",
        stop_reason="end_turn",
        tool_calls=None
    )
    mock_llm_provider.generate_response.side_effect = [
        LLMResponse(content="", stop_reason="tool_calls", tool_calls=[tool_call]),
        final_response
    ]
    
    # Add a user message
    await chat_session.add_user_message("Use the test tool")
    
    # Run the turn
    response = await chat_session.run_turn()
    
    # Verify the response
    assert response == "Tool execution complete"
    
    # Verify LLM was called twice (once for tool call, once for final response)
    assert mock_llm_provider.generate_response.call_count == 2
    
    # Verify tool executor was called
    mock_tool_executor.execute_tool.assert_called_once_with("test_tool", {})
    
    # Verify messages added to history
    assert len(chat_session.messages) >= 2
    assert chat_session.messages[0].role == "user"
    assert chat_session.messages[-1].role == "assistant"
    assert chat_session.messages[-1].content == "Tool execution complete"

@pytest.mark.asyncio
async def test_session_without_tool_executor(mock_llm_provider, mock_config):
    """Test session without a tool executor."""
    session = LLMChatSession(
        llm_provider=mock_llm_provider,
        tool_executor=None,
        config=mock_config
    )
    
    await session.initialize()
    
    # Should work without a tool executor for basic messages
    await session.add_user_message("Hello")
    response = await session.run_turn()
    
    assert response == "Test response"
    assert session.available_tools is None

@pytest.mark.asyncio
async def test_session_cleanup(chat_session):
    """Test session cleanup."""
    await chat_session.initialize()
    await chat_session.cleanup()
    
    chat_session.llm_provider.cleanup.assert_called_once()
    chat_session.tool_executor.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_available_tools(chat_session, mock_tool_executor):
    """Test getting available tools."""
    tool_def = ToolDefinition(
        name="another_tool",
        description="Another test tool",
        parameters={"type": "object", "properties": {}}
    )
    mock_tool_executor.list_tools.return_value = [tool_def]
    
    await chat_session.initialize()
    assert chat_session.available_tools == [tool_def]

@pytest.mark.asyncio
async def test_error_handling(chat_session, mock_llm_provider):
    """Test error handling during LLM calls."""
    await chat_session.initialize()
    
    # Make the LLM provider raise an exception
    mock_llm_provider.generate_response.side_effect = Exception("LLM error")
    
    await chat_session.add_user_message("Hello")
    
    with pytest.raises(LLMLibError) as excinfo:
        await chat_session.run_turn()
    
    assert "LLM error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_tool_execution_error(chat_session, mock_llm_provider, mock_tool_executor):
    """Test handling of tool execution errors."""
    await chat_session.initialize()
    
    # Set up the LLM to return a tool call
    tool_call = {
        "name": "test_tool",
        "arguments": {}
    }
    mock_llm_provider.generate_response.return_value = LLMResponse(
        content="",
        stop_reason="tool_calls",
        tool_calls=[tool_call]
    )
    
    # Make the tool executor raise an exception
    mock_tool_executor.execute_tool.side_effect = LLMLibError("Tool execution failed")
    
    # Set up the LLM to return a response after the tool error
    second_response = LLMResponse(
        content="Tool execution failed",
        stop_reason="end_turn",
        tool_calls=None
    )
    mock_llm_provider.generate_response.side_effect = [
        LLMResponse(content="", stop_reason="tool_calls", tool_calls=[tool_call]), 
        second_response
    ]
    
    await chat_session.add_user_message("Use the test tool")
    
    # Should report the error but continue
    response = await chat_session.run_turn()
    
    assert response == "Tool execution failed"
    
    # Verify final response was added to message history
    assert len(chat_session.messages) >= 2
    assert chat_session.messages[-1].role == "assistant" 
    assert chat_session.messages[-1].content == "Tool execution failed" 