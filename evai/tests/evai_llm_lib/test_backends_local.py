"""Tests for the local tool executor backend."""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from evai_llm_lib.backends.local import LocalToolExecutor
from evai_llm_lib.backends.base import ToolDefinition, ToolCall
from evai_llm_lib.config import LLMLibConfig
from evai_llm_lib.errors import LLMLibError

# Test tools

def test_sync_tool(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """A test synchronous tool."""
    return {"result": f"{param1}-{param2 or 'default'}"}

async def test_async_tool(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """A test asynchronous tool."""
    await asyncio.sleep(0.01)  # Small delay to ensure async behavior
    return {"result": f"{param1}-{param2 or 'default'}-async"}

# Test fixtures

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return LLMLibConfig()

@pytest.fixture
def local_executor():
    """Create a LocalToolExecutor instance with registered tools."""
    executor = LocalToolExecutor()
    
    # Register test tools
    executor.register_tool("test_sync_tool", test_sync_tool)
    executor.register_tool("test_async_tool", test_async_tool)
    
    return executor

# Tests

@pytest.mark.asyncio
async def test_local_executor_initialization():
    """Test initialization of LocalToolExecutor."""
    executor = LocalToolExecutor()
    await executor.initialize()
    
    assert executor.available_tools == []
    
    # Register a tool after initialization
    executor.register_tool("test_tool", test_sync_tool)
    assert len(executor.available_tools) == 1
    assert executor.available_tools[0].name == "test_tool"

@pytest.mark.asyncio
async def test_local_executor_tool_definition():
    """Test tool definition generation."""
    executor = LocalToolExecutor()
    executor.register_tool("test_sync_tool", test_sync_tool)
    
    tool_def = executor.available_tools[0]
    
    assert tool_def.name == "test_sync_tool"
    assert tool_def.description == "A test synchronous tool."
    assert tool_def.parameters["type"] == "object"
    assert "param1" in tool_def.parameters["properties"]
    assert "param2" in tool_def.parameters["properties"]
    assert tool_def.parameters["required"] == ["param1"]

@pytest.mark.asyncio
async def test_local_executor_execute_sync_tool(local_executor):
    """Test executing a synchronous tool."""
    await local_executor.initialize()
    
    tool_call = ToolCall(
        id="call_1",
        name="test_sync_tool",
        parameters={"param1": "test", "param2": 42}
    )
    
    result = await local_executor.execute_tool(tool_call)
    
    assert result.tool_call_id == "call_1"
    assert result.result == {"result": "test-42"}

@pytest.mark.asyncio
async def test_local_executor_execute_async_tool(local_executor):
    """Test executing an asynchronous tool."""
    await local_executor.initialize()
    
    tool_call = ToolCall(
        id="call_2",
        name="test_async_tool",
        parameters={"param1": "test", "param2": 42}
    )
    
    result = await local_executor.execute_tool(tool_call)
    
    assert result.tool_call_id == "call_2"
    assert result.result == {"result": "test-42-async"}

@pytest.mark.asyncio
async def test_local_executor_with_missing_parameters(local_executor):
    """Test executing a tool with missing optional parameters."""
    await local_executor.initialize()
    
    tool_call = ToolCall(
        id="call_3",
        name="test_sync_tool",
        parameters={"param1": "test"}  # param2 is missing but optional
    )
    
    result = await local_executor.execute_tool(tool_call)
    
    assert result.tool_call_id == "call_3"
    assert result.result == {"result": "test-default"}

@pytest.mark.asyncio
async def test_local_executor_with_required_parameter_missing(local_executor):
    """Test executing a tool with missing required parameters."""
    await local_executor.initialize()
    
    tool_call = ToolCall(
        id="call_4",
        name="test_sync_tool",
        parameters={}  # param1 is required but missing
    )
    
    with pytest.raises(LLMLibError) as excinfo:
        await local_executor.execute_tool(tool_call)
    
    assert "Missing required parameter" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_unknown_tool(local_executor):
    """Test executing an unknown tool."""
    await local_executor.initialize()
    
    tool_call = ToolCall(
        id="call_5",
        name="unknown_tool",
        parameters={"param1": "test"}
    )
    
    with pytest.raises(LLMLibError) as excinfo:
        await local_executor.execute_tool(tool_call)
    
    assert "Unknown tool" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_tool_error(local_executor):
    """Test error handling when a tool raises an exception."""
    await local_executor.initialize()
    
    # Register a tool that raises an exception
    def error_tool(param1: str) -> Dict[str, Any]:
        raise ValueError("Tool error")
    
    local_executor.register_tool("error_tool", error_tool)
    
    tool_call = ToolCall(
        id="call_6",
        name="error_tool",
        parameters={"param1": "test"}
    )
    
    with pytest.raises(LLMLibError) as excinfo:
        await local_executor.execute_tool(tool_call)
    
    assert "Tool error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_cleanup():
    """Test cleanup method."""
    executor = LocalToolExecutor()
    # Register some tools
    executor.register_tool("test_tool", test_sync_tool)
    
    await executor.initialize()
    await executor.cleanup()
    
    # LocalToolExecutor doesn't have specific cleanup logic,
    # but the method should not raise exceptions 