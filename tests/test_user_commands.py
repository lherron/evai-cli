"""Tests for user command loading and running."""

import os
import sys
import json
import tempfile
import shutil
from unittest import mock
import pytest
from click.testing import CliRunner
from pathlib import Path

from evai.cli.cli import cli
from evai.command_storage import get_command_dir, save_command_metadata


@pytest.fixture
def mock_commands_dir():
    """Create a temporary directory for commands with test command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the expanduser function to return our temp directory
        with mock.patch('os.path.expanduser') as mock_expanduser:
            # When expanduser is called with ~/.evai, return our temp .evai dir
            mock_expanduser.side_effect = lambda path: path.replace('~', temp_dir)
            
            # Create the commands directory
            commands_dir = os.path.join(temp_dir, '.evai', 'commands')
            os.makedirs(commands_dir, exist_ok=True)
            
            # Create a test command
            test_command_dir = os.path.join(commands_dir, 'hello')
            os.makedirs(test_command_dir, exist_ok=True)
            
            # Create command.yaml
            metadata = {
                "name": "hello",
                "description": "A test hello command",
                "arguments": [
                    {
                        "name": "name",
                        "description": "Name to greet",
                        "type": "string"
                    }
                ],
                "options": [
                    {
                        "name": "greeting",
                        "description": "Greeting to use",
                        "type": "string",
                        "required": False,
                        "default": "Hello"
                    }
                ],
                "hidden": False,
                "disabled": False
            }
            
            with open(os.path.join(test_command_dir, 'hello.yaml'), 'w') as f:
                json.dump(metadata, f)
            
            # Create hello.py
            with open(os.path.join(test_command_dir, 'hello.py'), 'w') as f:
                f.write('''"""Test command implementation."""

def command_hello(name: str, greeting: str = "Hello"):
    """Greet the user."""
    message = f"{greeting}, {name}!"
    return {"message": message}

# Legacy support
def run(**kwargs):
    """Legacy run function for backward compatibility."""
    return command_hello(**kwargs)
''')
            
            yield temp_dir


def test_user_command_in_help(mock_commands_dir):
    """Test that user commands appear in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    assert "user" in result.output
    
    result = runner.invoke(cli, ['user', '--help'])
    assert result.exit_code == 0
    assert "hello" in result.output


def test_run_user_command(mock_commands_dir):
    """Test running a user command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['user', 'hello', 'World', '--greeting', 'Hi'])
    
    assert result.exit_code == 0
    
    # Parse the JSON output
    output = json.loads(result.output)
    assert output == {"message": "Hi, World!"}