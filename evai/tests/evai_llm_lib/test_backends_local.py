"""Tests for the local tool executor backend."""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from evai.evai_llm_lib.backends.local import LocalToolExecutor
from evai.evai_llm_lib.backends.base import ToolDefinition
from evai.evai_llm_lib.config import LLMLibConfig, LocalToolsConfig
from evai.evai_llm_lib.errors import LLMLibError, ValidationError, ToolExecutionError

# Sample tools for testing

def sample_sync_tool(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """A test synchronous tool."""
    return {"result": f"{param1}-{param2 or 'default'}"}

async def sample_async_tool(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """A test asynchronous tool."""
    await asyncio.sleep(0.01)  # Small delay to ensure async behavior
    return {"result": f"{param1}-{param2 or 'default'}-async"}

# Test fixtures

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return LLMLibConfig(
        local_tools=LocalToolsConfig(
            module_paths=[],
            function_whitelist=None,
            function_blacklist=None
        )
    )

@pytest.fixture
def local_executor(mock_config):
    """Create a LocalToolExecutor instance with registered tools."""
    executor = LocalToolExecutor(config=mock_config.local_tools)
    
    # Register test tools
    executor.register_tool(sample_sync_tool)
    executor.register_tool(sample_async_tool)
    
    return executor

# Tests

@pytest.mark.asyncio
async def test_local_executor_initialization(mock_config):
    """Test initialization of LocalToolExecutor."""
    executor = LocalToolExecutor(config=mock_config.local_tools)
    await executor.initialize()
    
    tools = await executor.list_tools()
    assert len(tools) == 0
    
    # Register a tool after initialization
    executor.register_tool(sample_sync_tool)
    tools = await executor.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "sample_sync_tool"

@pytest.mark.asyncio
async def test_local_executor_tool_definition(mock_config):
    """Test tool definition generation."""
    executor = LocalToolExecutor(config=mock_config.local_tools)
    executor.register_tool(sample_sync_tool)
    
    await executor.initialize()
    available_tools = await executor.list_tools()
    assert len(available_tools) == 1
    
    tool_def = available_tools[0]
    
    assert tool_def.name == "sample_sync_tool"
    assert tool_def.description == "A test synchronous tool."
    assert tool_def.parameters["type"] == "object"
    assert "param1" in tool_def.parameters["properties"]
    assert "param2" in tool_def.parameters["properties"]
    assert tool_def.parameters["required"] == ["param1"]

@pytest.mark.asyncio
async def test_local_executor_execute_sync_tool(local_executor):
    """Test executing a synchronous tool."""
    await local_executor.initialize()
    
    result = await local_executor.execute_tool(
        tool_name="sample_sync_tool",
        parameters={"param1": "test", "param2": 42}
    )
    
    assert result.success is True
    assert result.result == {"result": "test-42"}

@pytest.mark.asyncio
async def test_local_executor_execute_async_tool(local_executor):
    """Test executing an asynchronous tool."""
    await local_executor.initialize()
    
    result = await local_executor.execute_tool(
        tool_name="sample_async_tool",
        parameters={"param1": "test", "param2": 42}
    )
    
    assert result.success is True
    assert result.result == {"result": "test-42-async"}

@pytest.mark.asyncio
async def test_local_executor_with_missing_parameters(local_executor):
    """Test executing a tool with missing optional parameters."""
    await local_executor.initialize()
    
    result = await local_executor.execute_tool(
        tool_name="sample_sync_tool",
        parameters={"param1": "test"}  # param2 is missing but optional
    )
    
    assert result.success is True
    assert result.result == {"result": "test-default"}

@pytest.mark.asyncio
async def test_local_executor_with_required_parameter_missing(local_executor):
    """Test executing a tool with missing required parameters."""
    await local_executor.initialize()
    
    with pytest.raises(ToolExecutionError) as excinfo:
        await local_executor.execute_tool(
            tool_name="sample_sync_tool",
            parameters={}  # param1 is required but missing
        )
    
    assert "Field required" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_unknown_tool(local_executor):
    """Test executing an unknown tool."""
    await local_executor.initialize()
    
    with pytest.raises(ToolExecutionError) as excinfo:
        await local_executor.execute_tool(
            tool_name="unknown_tool",
            parameters={"param1": "test"}
        )
    
    assert "not found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_tool_error(local_executor):
    """Test error handling when a tool raises an exception."""
    await local_executor.initialize()
    
    # Register a tool that raises an exception
    def error_tool(param1: str) -> Dict[str, Any]:
        raise ValueError("Tool error")
    
    local_executor.register_tool(error_tool)
    
    with pytest.raises(ToolExecutionError) as excinfo:
        await local_executor.execute_tool(
            tool_name="error_tool",
            parameters={"param1": "test"}
        )
    
    assert "Tool error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_local_executor_cleanup(mock_config):
    """Test cleanup method."""
    executor = LocalToolExecutor(config=mock_config.local_tools)
    # Register some tools
    executor.register_tool(sample_sync_tool)
    
    await executor.initialize()
    await executor.cleanup()
    
    # LocalToolExecutor doesn't have specific cleanup logic,
    # but the method should not raise exceptions 