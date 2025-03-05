"""Tests for tool listing and execution."""

import os
import sys
import json
import tempfile
import shutil
from unittest import mock
import pytest
from click.testing import CliRunner

from evai.cli import cli
from evai.tool_storage import get_tool_dir, save_tool_metadata


@pytest.fixture
def mock_tools_dir():
    """Create a temporary directory for tools."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the expanduser function to return our temp directory
        with mock.patch('os.path.expanduser', return_value=temp_dir):
            # Create the tools directory
            tools_dir = os.path.join(temp_dir, '.evai', 'tools')
            os.makedirs(tools_dir, exist_ok=True)
            
            # Create a test tool
            test_tool_dir = os.path.join(tools_dir, 'test-tool')
            os.makedirs(test_tool_dir, exist_ok=True)
            
            # Create tool.yaml
            metadata = {
                "name": "test-tool",
                "description": "A test tool",
                "params": [
                    {
                        "name": "message",
                        "description": "A message to echo",
                        "required": True
                    },
                    {
                        "name": "count",
                        "description": "Number of times to echo",
                        "required": False,
                        "default": 1
                    }
                ],
                "hidden": False,
                "disabled": False,
                "mcp_integration": {
                    "enabled": True,
                    "metadata": {
                        "endpoint": "",
                        "method": "POST",
                        "authentication_required": False
                    }
                },
                "llm_interaction": {
                    "enabled": False,
                    "auto_apply": True,
                    "max_llm_turns": 15
                }
            }
            
            with open(os.path.join(test_tool_dir, 'tool.yaml'), 'w') as f:
                json.dump(metadata, f)
            
            # Create tool.py
            with open(os.path.join(test_tool_dir, 'tool.py'), 'w') as f:
                f.write('''"""Test tool implementation."""

def run(message="Hello", count=1):
    """Run the test tool."""
    result = []
    for _ in range(count):
        result.append(message)
    return {"messages": result}
''')
            
            # Create a disabled tool
            disabled_tool_dir = os.path.join(tools_dir, 'disabled-tool')
            os.makedirs(disabled_tool_dir, exist_ok=True)
            
            # Create tool.yaml for disabled tool
            disabled_metadata = {
                "name": "disabled-tool",
                "description": "A disabled tool",
                "params": [],
                "hidden": False,
                "disabled": True,
                "mcp_integration": {
                    "enabled": True,
                    "metadata": {
                        "endpoint": "",
                        "method": "POST",
                        "authentication_required": False
                    }
                },
                "llm_interaction": {
                    "enabled": False,
                    "auto_apply": True,
                    "max_llm_turns": 15
                }
            }
            
            with open(os.path.join(disabled_tool_dir, 'tool.yaml'), 'w') as f:
                json.dump(disabled_metadata, f)
            
            # Create tool.py for disabled tool
            with open(os.path.join(disabled_tool_dir, 'tool.py'), 'w') as f:
                f.write('''"""Disabled tool implementation."""

def run():
    """Run the disabled tool."""
    return {"status": "disabled"}
''')
            
            yield temp_dir


def test_list_tools(mock_tools_dir):
    """Test listing tools."""
    runner = CliRunner()
    result = runner.invoke(cli, ['tool', 'list'])
    
    assert result.exit_code == 0
    assert "Available tools:" in result.output
    assert "test-tool: A test tool" in result.output
    assert "disabled-tool" not in result.output


def test_run_tool(mock_tools_dir):
    """Test running a tool."""
    runner = CliRunner()
    result = runner.invoke(cli, ['tool', 'run', 'test-tool', '-p', 'message=Hello World', '-p', 'count=3'])
    
    assert result.exit_code == 0
    
    # Parse the JSON output
    output = json.loads(result.output)
    assert output == {"messages": ["Hello World", "Hello World", "Hello World"]}


def test_run_tool_with_default_params(mock_tools_dir):
    """Test running a tool with default parameters."""
    runner = CliRunner()
    result = runner.invoke(cli, ['tool', 'run', 'test-tool', '-p', 'message=Hello World'])
    
    assert result.exit_code == 0
    
    # Parse the JSON output
    output = json.loads(result.output)
    assert output == {"messages": ["Hello World"]}


def test_run_tool_missing_required_param(mock_tools_dir):
    """Test running a tool with a missing required parameter."""
    runner = CliRunner()
    result = runner.invoke(cli, ['tool', 'run', 'test-tool'])
    
    assert result.exit_code == 1
    assert "Missing required parameter: message" in result.output


def test_run_nonexistent_tool(mock_tools_dir):
    """Test running a nonexistent tool."""
    runner = CliRunner()
    result = runner.invoke(cli, ['tool', 'run', 'nonexistent-tool'])
    
    assert result.exit_code == 1
    assert "Error running tool" in result.output 