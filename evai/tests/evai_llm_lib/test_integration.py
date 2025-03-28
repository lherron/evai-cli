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
        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello! I'm doing well.")]
        mock_response.stop_reason = "end_turn"
        mock_response.tool_calls = None

        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
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

        assert response.content == "Hello! I'm doing well."
        assert response.stop_reason == "end_turn"
        assert response.tool_calls is None

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

        # Send messages and verify responses
        response = await session.send_message("Let's do some math!")
        assert response.content == "What would you like to calculate?"

        response = await session.send_message("What is 12 times 34?")
        assert response.content == "12 × 34 = 408"

@pytest.mark.asyncio
async def test_integration_error_handling():
    """Test error handling in the integration."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        # Set up the mock client to raise an exception
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = anthropic.APIError("API Error")
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

@pytest.mark.asyncio
async def test_integration_sync_wrapper():
    """Test the synchronous wrapper."""
    with patch("evai.evai_llm_lib.api.ask") as mock_ask:
        # Set up the mock to return a future
        response = LLMResponse(
            content="Hello from the sync wrapper test",
            stop_reason="end_turn",
            tool_calls=None
        )
        mock_ask.return_value = response

        # Test the sync wrapper
        sync_response = ask_sync("Hello", config=None)
        assert sync_response.content == "Hello from the sync wrapper test"

@pytest.mark.asyncio
async def test_integration_end_to_end_flow():
    """Test the end-to-end flow of the library."""
    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic:
        # Set up responses for different stages
        first_response = MagicMock()
        first_response.content = [MagicMock(text="What would you like to calculate?")]
        first_response.stop_reason = "end_turn"
        first_response.tool_calls = None

        tool_response = MagicMock()
        tool_response.content = [MagicMock(text="")]
        tool_response.stop_reason = "tool_calls"
        tool_response.tool_calls = [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "arguments": {"operation": "multiply", "a": 12, "b": 34}
                }
            }
        ]

        final_response = MagicMock()
        final_response.content = [MagicMock(text="12 × 34 = 408")]
        final_response.stop_reason = "end_turn"
        final_response.tool_calls = None

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

        session = ChatSession(config=config, tool_executor=tool_executor)

        # Send messages and verify responses
        response = await session.send_message("Let's do some math!")
        assert response.content == "What would you like to calculate?"

        response = await session.send_message("What is 12 times 34?")
        assert response.content == "12 × 34 = 408" 