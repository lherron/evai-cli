"""Tests for command listing and execution."""

import os
import sys
import json
import tempfile
import shutil
from unittest import mock
import pytest
from click.testing import CliRunner

from evai.cli import cli
from evai.command_storage import get_command_dir, save_command_metadata


@pytest.fixture
def mock_commands_dir():
    """Create a temporary directory for commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the expanduser function to return our temp directory
        with mock.patch('os.path.expanduser', return_value=temp_dir):
            # Create the commands directory
            commands_dir = os.path.join(temp_dir, '.evai', 'commands')
            os.makedirs(commands_dir, exist_ok=True)
            
            # Create a test command
            test_cmd_dir = os.path.join(commands_dir, 'test-command')
            os.makedirs(test_cmd_dir, exist_ok=True)
            
            # Create command.yaml
            metadata = {
                "name": "test-command",
                "description": "A test command",
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
            
            with open(os.path.join(test_cmd_dir, 'command.yaml'), 'w') as f:
                json.dump(metadata, f)
            
            # Create command.py
            with open(os.path.join(test_cmd_dir, 'command.py'), 'w') as f:
                f.write('''"""Test command implementation."""

def run(message="Hello", count=1):
    """Run the test command."""
    result = []
    for _ in range(count):
        result.append(message)
    return {"messages": result}
''')
            
            # Create a disabled command
            disabled_cmd_dir = os.path.join(commands_dir, 'disabled-command')
            os.makedirs(disabled_cmd_dir, exist_ok=True)
            
            # Create command.yaml for disabled command
            disabled_metadata = {
                "name": "disabled-command",
                "description": "A disabled command",
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
            
            with open(os.path.join(disabled_cmd_dir, 'command.yaml'), 'w') as f:
                json.dump(disabled_metadata, f)
            
            # Create command.py for disabled command
            with open(os.path.join(disabled_cmd_dir, 'command.py'), 'w') as f:
                f.write('''"""Disabled command implementation."""

def run():
    """Run the disabled command."""
    return {"status": "disabled"}
''')
            
            yield temp_dir


def test_list_commands(mock_commands_dir):
    """Test listing commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', 'list'])
    
    assert result.exit_code == 0
    assert "Available commands:" in result.output
    assert "test-command: A test command" in result.output
    assert "disabled-command" not in result.output


def test_run_command(mock_commands_dir):
    """Test running a command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', 'run', 'test-command', '-p', 'message=Hello World', '-p', 'count=3'])
    
    assert result.exit_code == 0
    
    # Parse the JSON output
    output = json.loads(result.output)
    assert output == {"messages": ["Hello World", "Hello World", "Hello World"]}


def test_run_command_with_default_params(mock_commands_dir):
    """Test running a command with default parameters."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', 'run', 'test-command', '-p', 'message=Hello World'])
    
    assert result.exit_code == 0
    
    # Parse the JSON output
    output = json.loads(result.output)
    assert output == {"messages": ["Hello World"]}


def test_run_command_missing_required_param(mock_commands_dir):
    """Test running a command with a missing required parameter."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', 'run', 'test-command'])
    
    assert result.exit_code == 1
    assert "Missing required parameter: message" in result.output


def test_run_nonexistent_command(mock_commands_dir):
    """Test running a nonexistent command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', 'run', 'nonexistent-command'])
    
    assert result.exit_code == 1
    assert "Error running command" in result.output 