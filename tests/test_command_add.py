"""Tests for command adding functionality."""

import os
import sys
import json
import tempfile
import shutil
from unittest import mock
import pytest
from click.testing import CliRunner

from evai.cli.cli import cli
from evai.command_storage import get_command_dir, save_command_metadata


@pytest.fixture
def mock_commands_dir():
    """Create a temporary directory for commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the expanduser function to return our temp directory
        with mock.patch('os.path.expanduser') as mock_expanduser:
            # When expanduser is called with ~/.evai, return our temp .evai dir
            mock_expanduser.side_effect = lambda path: path.replace('~', temp_dir)
            
            # Create the commands directory
            commands_dir = os.path.join(temp_dir, '.evai', 'commands')
            os.makedirs(commands_dir, exist_ok=True)
            
            yield temp_dir


def test_add_command(mock_commands_dir):
    """Test adding a command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['commands', 'add', 'test-command'])
    
    assert result.exit_code == 0
    assert "Command 'test-command' created successfully." in result.output
    
    # Verify files were created
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'test-command')
    assert os.path.exists(command_dir)
    assert os.path.exists(os.path.join(command_dir, 'command.yaml'))
    assert os.path.exists(os.path.join(command_dir, 'command.py'))
    
    # Verify content of command.yaml
    with open(os.path.join(command_dir, 'command.yaml'), 'r') as f:
        metadata = json.load(f)
        assert metadata["name"] == "test-command"