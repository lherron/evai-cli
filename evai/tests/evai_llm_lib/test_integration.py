"""Integration tests for the LLM library."""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic # Ensure anthropic is imported

from evai.evai_llm_lib.api import ask, ChatSession, ask_sync
from evai.evai_llm_lib.backends.anthropic import AnthropicBackend
from evai.evai_llm_lib.backends.local import LocalToolExecutor
from evai.evai_llm_lib.backends.base import LLMResponse, ToolDefinition, ToolResult
from evai.evai_llm_lib.config import LLMLibConfig, AnthropicConfig, LocalToolsConfig
from evai.evai_llm_lib.errors import LLMLibError
from evai.evai_llm_lib.backends.base import LLMResponse

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
    # Create a mock tool executor instance first
    mock_executor = LocalToolExecutor(config=LocalToolsConfig(
        module_paths=[],
        function_whitelist=None,
        function_blacklist=None
    ))
    mock_executor.register_tool(calculator)

    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic, \
         patch("evai.evai_llm_lib.api.create_session_backends") as mock_create_backends:

        # Set up the mock Anthropic client
        mock_anthropic_client = AsyncMock()
        responses = [
            mock_anthropic_response,
            mock_anthropic_tool_response,
            mock_anthropic_final_response
        ]
        futures = [asyncio.Future() for _ in responses]
        for future, response in zip(futures, responses):
            future.set_result(response)
        mock_anthropic_client.messages.create.side_effect = futures
        mock_anthropic.return_value = mock_anthropic_client

        # Mock create_session_backends to return mock provider and executor
        mock_provider = AnthropicBackend(config=AnthropicConfig(api_key="test_key"))
        mock_provider._client = mock_anthropic_client # Inject the mock client
        mock_provider._initialized = True # Mark as initialized
        mock_create_backends.return_value = (mock_provider, mock_executor)

        # Create a chat session, passing executor name
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic",
            # Specify local executor by name
            default_tool_executor="local" 
        )

        # Pass the executor *name* instead of the instance
        async with ChatSession(config=config, tool_executor="local") as session:
            # Verify backends were created with correct names
            mock_create_backends.assert_called_once_with(
                provider_name=None, # Uses default from config
                executor_name="local",
                config=config
            )

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
        # Use anthropic.APIError
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

        # Check for the specific LLMProviderError message from the backend
        assert "Anthropic API error: API Error" in str(excinfo.value)

# Mock function to replace asyncio.run
def mock_asyncio_run(coro, *args, **kwargs):
    # If the coroutine is awaitable, return its result directly
    if asyncio.iscoroutine(coro):
        # This is a simplified approach for testing; might need adjustments
        # if the coroutine relies on a running loop for other tasks.
        # We assume the patched ask function already returns a completed future.
        try:
            coro.send(None)
        except StopIteration as e:
            return e.value
    return coro # Or handle non-coroutines if necessary

@pytest.mark.asyncio
async def test_integration_sync_wrapper():
    """Test the synchronous wrapper."""
    # Define the mock response outside the patches
    expected_response = LLMResponse(
        content="Hello from the sync wrapper test",
        stop_reason="end_turn",
        tool_calls=None
    )

    # Patch api.ask and asyncio.run
    with patch("evai.evai_llm_lib.api.ask", new_callable=AsyncMock) as mock_ask, \
         patch("asyncio.run", new=mock_asyncio_run):

        # Configure the mock_ask to return the expected response
        mock_ask.return_value = expected_response

        # Test the sync wrapper
        sync_response = ask_sync("Hello", config=None)

        # Assertions
        assert sync_response.content == "Hello from the sync wrapper test"
        # Verify that the mocked api.ask was called
        mock_ask.assert_called_once_with("Hello", provider=None, config=None, max_tokens=None)


@pytest.mark.asyncio
async def test_integration_end_to_end_flow():
    """Test the end-to-end flow of the library."""
    # Create a mock tool executor instance first
    mock_executor = LocalToolExecutor(config=LocalToolsConfig(
        module_paths=[],
        function_whitelist=None,
        function_blacklist=None
    ))
    mock_executor.register_tool(calculator)

    with patch("evai.evai_llm_lib.backends.anthropic.anthropic.Anthropic") as mock_anthropic, \
         patch("evai.evai_llm_lib.api.create_session_backends") as mock_create_backends:

        # Set up responses for different stages
        first_response = MagicMock()
        first_response.content = [MagicMock(text="What would you like to calculate?")]
        first_response.stop_reason = "end_turn"
        first_response.tool_calls = None

        tool_response = MagicMock()
        tool_response.content = [MagicMock(text="")]
        tool_response.stop_reason = "tool_calls"
        # Correct tool_calls format for Anthropic
        tool_response.tool_calls = [
             MagicMock(id="tool_use_1", type="tool_use", name="calculator", input={"operation": "multiply", "a": 12, "b": 34})
        ]

        final_response = MagicMock()
        final_response.content = [MagicMock(text="12 × 34 = 408")]
        final_response.stop_reason = "end_turn"
        final_response.tool_calls = None

        # Set up the mock Anthropic client
        mock_anthropic_client = AsyncMock()
        responses = [first_response, tool_response, final_response]
        futures = [asyncio.Future() for _ in responses]
        for future, response in zip(futures, responses):
            future.set_result(response)
        mock_anthropic_client.messages.create.side_effect = futures
        mock_anthropic.return_value = mock_anthropic_client

        # Mock create_session_backends
        mock_provider = AnthropicBackend(config=AnthropicConfig(api_key="test_key"))
        mock_provider._client = mock_anthropic_client
        mock_provider._initialized = True
        mock_create_backends.return_value = (mock_provider, mock_executor)

        # Create a chat session config
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-sonnet-20240229"
            ),
            default_provider="anthropic",
            default_tool_executor="local"
        )

        # Use context manager, passing executor name
        async with ChatSession(config=config, tool_executor="local") as session:
             # Verify backends were created
            mock_create_backends.assert_called_once_with(
                provider_name=None, 
                executor_name="local",
                config=config
            )
            # Send messages and verify responses
            response = await session.send_message("Let's do some math!")
            assert response.content == "What would you like to calculate?"

            response = await session.send_message("What is 12 times 34?")
            assert response.content == "12 × 34 = 408" 