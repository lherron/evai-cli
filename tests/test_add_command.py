"""Tests for the command add functionality."""

import os
import shutil
import tempfile
import yaml
from click.testing import CliRunner
from unittest import mock

from evai.cli import cli


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
        result = runner.invoke(cli, ['command', 'add', 'test-command', '--test-mode'], catch_exceptions=False)
        
        # Check that the command was successful
        assert result.exit_code == 0
        assert "Command 'test-command' created successfully." in result.output
        assert "Test mode: Skipping editor." in result.output
        
        # Check that the command directory was created
        command_dir = os.path.join(self.temp_dir, '.evai', 'commands', 'test-command')
        assert os.path.exists(command_dir)
        
        # Check that the command.yaml file was created with the correct content
        yaml_path = os.path.join(command_dir, 'command.yaml')
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
        py_path = os.path.join(command_dir, 'command.py')
        assert os.path.exists(py_path)
        
        with open(py_path, 'r') as f:
            content = f.read()
        
        assert '"""Custom command implementation."""' in content
        assert 'def run(**kwargs):' in content
        assert 'print("Hello World")' in content
        assert 'return {"status": "success"}' in content

    def test_add_command_invalid_name(self):
        """Test adding a command with an invalid name."""
        runner = CliRunner()
        result = runner.invoke(cli, ['command', 'add', 'test command', '--test-mode'], catch_exceptions=False)  # Space in name
        
        # Check that the command failed
        assert result.exit_code == 1
        assert "Error creating command" in result.output
        
        # Check that the command directory was not created
        command_dir = os.path.join(self.temp_dir, '.evai', 'commands', 'test command')
        assert not os.path.exists(command_dir)
        
    @mock.patch('evai.command_storage.edit_command_metadata')
    @mock.patch('evai.command_storage.edit_command_implementation')
    @mock.patch('evai.command_storage.run_lint_check')
    def test_add_command_with_editing_and_lint_check(self, mock_lint, mock_edit_impl, mock_edit_meta):
        """Test adding a command with editing and lint checking."""
        # Mock the edit_command_metadata function to return success
        mock_edit_meta.return_value = (True, {
            "name": "test-command",
            "description": "Edited description",
            "params": [],
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
        })
        
        # Mock the edit_command_implementation function to return success
        mock_edit_impl.return_value = True
        
        # Mock the run_lint_check function to return success
        mock_lint.return_value = (True, None)
        
        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ['command', 'add', 'test-command'], catch_exceptions=False, input='y\n')
        
        # Check that the command was successful
        assert result.exit_code == 0
        assert "Command 'test-command' created successfully." in result.output
        assert "Opening command.yaml for editing" in result.output
        assert "Command metadata saved successfully." in result.output
        assert "Opening command.py for editing" in result.output
        assert "Running lint check on command.py" in result.output
        assert "Lint check passed. Command implementation saved successfully." in result.output
        assert "Command 'test-command' setup complete." in result.output
        
        # Verify that the mock functions were called
        mock_edit_meta.assert_called_once()
        mock_edit_impl.assert_called_once()
        mock_lint.assert_called_once()
        
    @mock.patch('evai.command_storage.edit_command_metadata')
    @mock.patch('evai.command_storage.edit_command_implementation')
    @mock.patch('evai.command_storage.run_lint_check')
    def test_add_command_with_lint_failure_then_success(self, mock_lint, mock_edit_impl, mock_edit_meta):
        """Test adding a command with lint failure followed by success."""
        # Mock the edit_command_metadata function to return success
        mock_edit_meta.return_value = (True, {
            "name": "test-command",
            "description": "Edited description",
            "params": [],
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
        })
        
        # Mock the edit_command_implementation function to return success
        mock_edit_impl.return_value = True
        
        # Mock the run_lint_check function to return failure then success
        mock_lint.side_effect = [
            (False, "test-command/command.py:7:5: F841 local variable 'y' is assigned to but never used"),
            (True, None)
        ]
        
        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ['command', 'add', 'test-command'], catch_exceptions=False, input='y\ny\n')
        
        # Check that the command was successful
        assert result.exit_code == 0
        assert "Command 'test-command' created successfully." in result.output
        assert "Opening command.yaml for editing" in result.output
        assert "Command metadata saved successfully." in result.output
        assert "Opening command.py for editing" in result.output
        assert "Running lint check on command.py" in result.output
        assert "Lint check failed. Please fix the following issues:" in result.output
        assert "local variable 'y' is assigned to but never used" in result.output
        assert "Would you like to edit the file again?" in result.output
        assert "Opening command.py for editing again" in result.output
        assert "Lint check passed. Command implementation saved successfully." in result.output
        assert "Command 'test-command' setup complete." in result.output
        
        # Verify that the mock functions were called
        mock_edit_meta.assert_called_once()
        assert mock_edit_impl.call_count == 2
        assert mock_lint.call_count == 2
        
    @mock.patch('evai.command_storage.edit_command_metadata')
    @mock.patch('evai.command_storage.edit_command_implementation')
    @mock.patch('evai.command_storage.run_lint_check')
    def test_add_command_with_lint_failure_and_abort(self, mock_lint, mock_edit_impl, mock_edit_meta):
        """Test adding a command with lint failure and user choosing to abort."""
        # Mock the edit_command_metadata function to return success
        mock_edit_meta.return_value = (True, {
            "name": "test-command",
            "description": "Edited description",
            "params": [],
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
        })
        
        # Mock the edit_command_implementation function to return success
        mock_edit_impl.return_value = True
        
        # Mock the run_lint_check function to return failure
        mock_lint.return_value = (False, "test-command/command.py:7:5: F841 local variable 'y' is assigned to but never used")
        
        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ['command', 'add', 'test-command'], catch_exceptions=False, input='y\nn\n')
        
        # Check that the command was successful but with a warning
        assert result.exit_code == 0
        assert "Command 'test-command' created successfully." in result.output
        assert "Opening command.yaml for editing" in result.output
        assert "Command metadata saved successfully." in result.output
        assert "Opening command.py for editing" in result.output
        assert "Running lint check on command.py" in result.output
        assert "Lint check failed. Please fix the following issues:" in result.output
        assert "local variable 'y' is assigned to but never used" in result.output
        assert "Would you like to edit the file again?" in result.output
        assert "Aborting. The command has been created but may contain lint errors." in result.output
        assert "Command 'test-command' setup complete." in result.output
        
        # Verify that the mock functions were called
        mock_edit_meta.assert_called_once()
        mock_edit_impl.assert_called_once()
        mock_lint.assert_called_once() 