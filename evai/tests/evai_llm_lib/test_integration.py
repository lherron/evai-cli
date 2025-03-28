"""Integration tests for the LLM library."""

import os
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch

from evai.evai_llm_lib.api import ask, ChatSession, ask_sync
from evai.evai_llm_lib.backends.anthropic import AnthropicBackend
from evai.evai_llm_lib.backends.local import LocalToolExecutor
from evai.evai_llm_lib.backends.base import Message, ToolDefinition, LLMProviderBackend, LLMResponse
from evai.evai_llm_lib.config import LLMLibConfig, AnthropicConfig, LocalToolsConfig
from evai.evai_llm_lib.errors import LLMProviderError, AuthenticationError, ToolExecutionError

# Real tool for testing
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

# Use a mock provider but a real tool executor
class TestIntegration:
    
    @pytest.fixture
    def llm_config(self):
        """Create a test LLM configuration."""
        return LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key="test_key",
                model="claude-3-7-sonnet-latest"
            ),
            default_provider="anthropic",
            default_tool_executor="local"
        )
    
    @pytest.fixture
    def tool_executor(self):
        """Create a real local tool executor with a calculator tool."""
        executor = LocalToolExecutor(config=LocalToolsConfig(
            module_paths=[],
            function_whitelist=None,
            function_blacklist=None
        ))
        executor.register_tool(calculator)
        return executor
    
    @pytest.mark.asyncio
    async def test_chat_session_backend_integration(self, tool_executor):
        """Test integration between tool executor and LLM backend using minimal mocking."""
        # We create an implementation of LLMProviderBackend that simulates tool calls
        # but doesn't use external services
        
        class TestLLMBackend(LLMProviderBackend):
            """Test LLM backend that simulates tool calls without external dependencies."""
            
            def __init__(self):
                self.tools = []
                self._initialized = False
                self.call_count = 0
                
            async def initialize(self) -> None:
                self._initialized = True
                
            async def generate_response(
                self,
                messages: List[Message],
                tools: Optional[List[ToolDefinition]] = None,
                max_tokens: Optional[int] = None
            ) -> LLMResponse:
                """Generate responses that simulate tool use based on message content."""
                self.call_count += 1
                
                # Store tools for later use
                if tools:
                    self.tools = tools
                
                # The function gets called with our LLM implmentation and should always return a tool call
                # for the calculator on the first call, and a result on the second call for this test
                if self.call_count == 1:
                    # First call - always return a tool call for the calculator
                    return LLMResponse(
                        content="",
                        stop_reason="tool_calls",
                        tool_calls=[{
                            "name": "calculator",
                            "arguments": {
                                "operation": "multiply",
                                "a": 6,
                                "b": 7
                            }
                        }]
                    )
                elif self.call_count == 2:
                    # Second call - return a nice response
                    return LLMResponse(
                        content="The result of 6 multiplied by 7 is 42",
                        stop_reason="end_turn",
                        tool_calls=None
                    )
                
                # Default response - shouldn't happen in our test
                return LLMResponse(
                    content="Default response - test should not reach here",
                    stop_reason="end_turn",
                    tool_calls=None
                )
            
            async def cleanup(self) -> None:
                pass
        
        # Create our test backend
        test_llm = TestLLMBackend()
        
        # Set up a session with our test LLM backend and real tool executor
        from evai.evai_llm_lib.session import LLMChatSession
        
        session = LLMChatSession(
            llm_provider=test_llm,
            tool_executor=tool_executor,
            config=LLMLibConfig()
        )
        
        # Initialize the session
        await session.initialize()
        
        # Send a user message asking for a calculation
        await session.add_user_message("What is 6 times 7?")
        
        # Run a turn
        response = await session.run_turn()
        
        # Verify the response
        assert "result" in response.lower()
        assert "42" in response
        
        # Verify the LLM was called twice (once for the tool call, once for the final response)
        assert test_llm.call_count == 2
        
        # Clean up
        await session.cleanup()
    
    @pytest.mark.asyncio
    async def test_real_local_tool_calculator(self):
        """Test that the calculator tool actually works as expected."""
        # Test all operations to ensure the tool itself works correctly
        assert (await calculator("add", 5, 3))["result"] == 8
        assert (await calculator("subtract", 10, 4))["result"] == 6
        assert (await calculator("multiply", 7, 8))["result"] == 56
        assert (await calculator("divide", 20, 5))["result"] == 4
        
        # Test error case
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            await calculator("divide", 10, 0)
            
        with pytest.raises(ValueError, match="Unknown operation"):
            await calculator("power", 2, 3)
    
    @pytest.mark.asyncio
    async def test_executor_integration(self, tool_executor):
        """Test the integration between tool_executor and the calculator tool."""
        # Initialize the executor
        await tool_executor.initialize()
        
        # List available tools
        tools = await tool_executor.list_tools()
        assert len(tools) > 0
        
        # Find our calculator tool
        calculator_tool = next((t for t in tools if t.name == "calculator"), None)
        assert calculator_tool is not None
        assert calculator_tool.name == "calculator"
        assert "Calculator tool for testing" in calculator_tool.description
        
        # Execute the tool
        result = await tool_executor.execute_tool(
            "calculator",
            {"operation": "add", "a": 40, "b": 2}
        )
        
        # Verify results
        assert result.success is True
        assert result.result["result"] == 42
        
    @pytest.mark.asyncio
    async def test_full_toolchain_integration(self, tool_executor):
        """Test the complete tool execution chain with various operations."""
        # Initialize the executor
        await tool_executor.initialize()
        
        # Execute multiple operations in sequence
        operations = [
            {"operation": "add", "a": 10, "b": 5},
            {"operation": "subtract", "a": 20, "b": 8},
            {"operation": "multiply", "a": 6, "b": 7},
            {"operation": "divide", "a": 100, "b": 4}
        ]
        
        expected_results = [15, 12, 42, 25]
        
        # Execute each operation and verify
        for i, op in enumerate(operations):
            result = await tool_executor.execute_tool("calculator", op)
            assert result.success is True
            assert result.result["result"] == expected_results[i]
            
        # Test error handling
        with pytest.raises(ToolExecutionError) as excinfo:
            await tool_executor.execute_tool(
                "calculator", 
                {"operation": "divide", "a": 10, "b": 0}
            )
            
        # Verify error message
        assert "Cannot divide by zero" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_end_to_end_with_anthropic_env(self):
        """
        Test the full integration with Anthropic if API key is available.
        This test is skipped if no API key is available.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY environment variable not set")
            
        # Create a real config with the real API key
        config = LLMLibConfig(
            anthropic=AnthropicConfig(
                api_key=api_key,
                model="claude-3-7-sonnet-latest"
            ),
            default_provider="anthropic"
        )
        
        try:
            # This test will actually call the Anthropic API
            response = await ask(
                "Say 'Integration test successful' and nothing else",
                config=config
            )
            
            assert "Integration test successful" in response
        except Exception as e:
            # Only fail test if error isn't related to auth/credentials
            if not isinstance(e, AuthenticationError):
                raise

# Sync wrapper test using patching to avoid needing real asyncio.run
def test_sync_wrapper():
    """Test the synchronous wrapper."""
    with patch("asyncio.run") as mock_run:
        mock_run.return_value = "Hello from the sync wrapper test"
        
        # Test the sync wrapper
        sync_response = ask_sync("Hello", config=None)
        
        # Verify
        assert mock_run.called
        assert sync_response == "Hello from the sync wrapper test"