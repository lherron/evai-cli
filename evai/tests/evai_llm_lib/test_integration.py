"""Integration tests for the LLM library."""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from evai.evai_llm_lib.api import ask, ChatSession
from evai.evai_llm_lib.backends.anthropic import AnthropicBackend
from evai.evai_llm_lib.backends.local import LocalToolExecutor
from evai.evai_llm_lib.backends.base import LLMResponse, ToolDefinition, ToolResult
from evai.evai_llm_lib.config import LLMLibConfig, AnthropicConfig, LocalToolsConfig
from evai.evai_llm_lib.errors import LLMLibError

# Mock tool for testing
async def calculator(operation: str, a: float, b: float) -> Dict[str, Any]:
    """Calculator tool for testing.
    
    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        
    Returns:
        Result of the calculation
    """
    result = None
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
        
    return {"result": result}

# Mock response fixtures

@pytest.fixture
def mock_anthropic_response():
    """Create a mock response from Anthropic's chat completion API."""
    return MagicMock(
        content=[{"type": "text", "text": "Hello! How can I help you today?"}],
        role="assistant",
        id="msg_1",
        model="claude-3-sonnet-20240229",
        tool_use=None,
    )

@pytest.fixture
def mock_anthropic_tool_response():
    """Create a mock response with a tool call."""
    response = MagicMock(
        content=[],
        role="assistant",
        id="msg_2",
        model="claude-3-sonnet-20240229"
    )
    response.content = [
        {
            "type": "tool_use",
            "id": "tool_use_1",
            "name": "calculator",
            "input": {"operation": "add", "a": 40, "b": 2}
        }
    ]
    return response

@pytest.fixture
def mock_anthropic_final_response():
    """Create a mock final response after tool execution."""
    return MagicMock(
        content=[{"type": "text", "text": "The result is 42"}],
        role="assistant",
        id="msg_3",
        model="claude-3-sonnet-20240229",
        tool_use=None,
    )
    
# Tests

@pytest.mark.asyncio
async def test_integration_ask(mock_anthropic_response):
    """Test the integration of ask() with Anthropic provider."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.return_value = mock_client
        
        # Create a configuration
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic"
        )
        
        # Test the ask function
        response = await ask(
            "Hello, how are you?",
            config=config
        )
        
        # Verify the result
        assert response.text == "Hello! How can I help you today?"
        
        # Verify the function was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["messages"][0]["content"] == "Hello, how are you?"
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["model"] == "claude-3-sonnet-20240229"

@pytest.mark.asyncio
async def test_integration_chat_session_with_tools(
    mock_anthropic_response,
    mock_anthropic_tool_response,
    mock_anthropic_final_response
):
    """Test the integration of ChatSession with tools."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        # Set up the mock client with a sequence of responses
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [
            mock_anthropic_response,           # Initial greeting
            mock_anthropic_tool_response,      # Tool call
            mock_anthropic_final_response      # Final response after tool execution
        ]
        mock_anthropic.return_value = mock_client
        
        # Create a local tool executor with a calculator tool
        tool_executor = LocalToolExecutor(config=LocalToolsConfig(
            module_paths=[],
            function_whitelist=None,
            function_blacklist=None
        ))
        tool_executor.register_tool(calculator)
        
        # Create a chat session
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic"
        )
        
        session = ChatSession(config=config, tool_executor=tool_executor)
        
        # Initialize the session
        await session.initialize()
        
        # Start the conversation
        response = await session.send_message("Hello!")
        assert response.text == "Hello! How can I help you today?"
        
        # Send a message that triggers a tool call
        response = await session.send_message("Can you calculate 40 + 2?")
        
        # Verify the result
        assert response.text == "The result is 42"
        
        # Verify the correct number of calls
        assert mock_client.messages.create.call_count == 3

@pytest.mark.asyncio
async def test_integration_error_handling():
    """Test error handling in the integration."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        # Set up the mock client to raise an exception
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client
        
        # Create a configuration
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic"
        )
        
        # Test error handling in ask
        with pytest.raises(LLMLibError) as excinfo:
            await ask("Hello", config=config)
            
        assert "API Error" in str(excinfo.value)
        
        # Test error handling in ChatSession
        with pytest.raises(LLMLibError) as excinfo:
            session = ChatSession(config=config)
            await session.initialize()
            await session.send_message("Hello")
            
        assert "API Error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_integration_sync_wrapper():
    """Test the synchronous wrapper."""
    with patch("evai.evai_llm_lib.api.ask") as mock_ask:
        # Set up the mock to return a future
        response = LLMResponse(
            text="Hello from the sync wrapper test",
            raw_response={},
            tools_calls=[]
        )
        future = asyncio.Future()
        future.set_result(response)
        mock_ask.return_value = future
        
        # Import sync wrapper
        from evai.evai_llm_lib.api import ask_sync
        
        # Test the sync wrapper
        result = ask_sync("Hello")
        
        # Verify the result
        assert result.text == "Hello from the sync wrapper test"
        mock_ask.assert_called_once()

@pytest.mark.asyncio
async def test_integration_end_to_end_flow():
    """Test the end-to-end flow of the library."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        # Set up responses for different stages
        first_response = MagicMock(
            content=[{"type": "text", "text": "What would you like to calculate?"}],
            role="assistant",
            id="msg_1",
            model="claude-3-sonnet-20240229",
            tool_use=None,
        )
        
        tool_response = MagicMock(
            content=[],
            role="assistant",
            id="msg_2",
            model="claude-3-sonnet-20240229"
        )
        tool_response.content = [
            {
                "type": "tool_use",
                "id": "tool_use_1",
                "name": "calculator",
                "input": {"operation": "multiply", "a": 12, "b": 34}
            }
        ]
        
        final_response = MagicMock(
            content=[{"type": "text", "text": "12 × 34 = 408"}],
            role="assistant",
            id="msg_3",
            model="claude-3-sonnet-20240229",
            tool_use=None,
        )
        
        # Set up the mock client
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [
            first_response,
            tool_response,
            final_response
        ]
        mock_anthropic.return_value = mock_client
        
        # Create a local tool executor
        tool_executor = LocalToolExecutor(config=LocalToolsConfig(
            module_paths=[],
            function_whitelist=None,
            function_blacklist=None
        ))
        tool_executor.register_tool(calculator)
        
        # Create a chat session
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic"
        )
        
        # Initialize session
        session = ChatSession(config=config, tool_executor=tool_executor)
        await session.initialize()
        
        # First message to start the conversation
        response = await session.send_message("I need to do a calculation")
        assert response.text == "What would you like to calculate?"
        
        # Second message triggering a tool call
        response = await session.send_message("What is 12 times 34?")
        assert response.text == "12 × 34 = 408"
        
        # Verify tool was called
        assert mock_client.messages.create.call_count == 3 