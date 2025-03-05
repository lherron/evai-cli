"""Tests for the command add functionality."""

import os
import shutil
import tempfile
import yaml
from click.testing import CliRunner
from unittest import mock

from evai.cli.cli import cli


class TestAddCommand:
    """Tests for the command add functionality."""

    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Create the .evai directory structure
        self.evai_dir = os.path.join(self.temp_dir, '.evai')
        os.makedirs(self.evai_dir, exist_ok=True)
        
        # Mock the expanduser function to use our temporary directory
        self.patcher = mock.patch('os.path.expanduser')
        self.mock_expanduser = self.patcher.start()
        # When expanduser is called with ~/.evai, return our temp .evai dir
        self.mock_expanduser.side_effect = lambda path: path.replace('~', self.temp_dir)

    def teardown_method(self):
        """Clean up after the tests."""
        # Stop the patcher
        self.patcher.stop()
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_add_command(self):
        """Test adding a new command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['tools', 'add', 'test-command'])
        
        # Check that the command was successful
        assert result.exit_code == 0
        assert "Tool 'test-command' created successfully." in result.output
        
        # Check that the command directory was created
        command_dir = os.path.join(self.temp_dir, '.evai', 'tools', 'test-command')
        assert os.path.exists(command_dir)
        
        # Check that the command.yaml file was created with the correct content
        yaml_path = os.path.join(command_dir, 'tool.yaml')
        assert os.path.exists(yaml_path)
        
        with open(yaml_path, 'r') as f:
            metadata = yaml.safe_load(f)
        
        assert metadata['name'] == 'test-command'
        assert metadata['description'] == 'Default description'
        assert metadata['params'] == []
        assert metadata['hidden'] is False
        assert metadata['disabled'] is False
        assert metadata['mcp_integration']['enabled'] is True
        assert metadata['mcp_integration']['metadata']['method'] == 'POST'
        assert metadata['mcp_integration']['metadata']['authentication_required'] is False
        assert metadata['llm_interaction']['enabled'] is False
        assert metadata['llm_interaction']['auto_apply'] is True
        assert metadata['llm_interaction']['max_llm_turns'] == 15
        
        # Check that the command.py file was created with the correct content
        py_path = os.path.join(command_dir, 'tool.py')
        assert os.path.exists(py_path)
        
        with open(py_path, 'r') as f:
            content = f.read()
        
        assert '"""Custom tool implementation."""' in content
        assert 'def tool_echo(' in content
        assert 'return echo_string' in content

    def test_add_command_invalid_name(self):
        """Test adding a command with an invalid name."""
        runner = CliRunner()
        result = runner.invoke(cli, ['tools', 'add', 'test command'])  # Space in name
        
        # Check that the command failed
        assert result.exit_code == 1
        assert "Error creating tool" in result.output
        
        # Check that the command directory was not created
        command_dir = os.path.join(self.temp_dir, '.evai', 'tools', 'test command')
        assert not os.path.exists(command_dir)