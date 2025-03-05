"""Tests for the command metadata editing functionality."""

import os
import shutil
import tempfile
import yaml
from unittest import mock
import subprocess

from evai.tool_storage import edit_command_metadata, get_editor


class TestEditMetadata:
    """Tests for the command metadata editing functionality."""

    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test command directory
        self.command_dir = os.path.join(self.temp_dir, 'test-command')
        os.makedirs(self.command_dir, exist_ok=True)
        
        # Create a test command.yaml file
        self.yaml_path = os.path.join(self.command_dir, 'command.yaml')
        self.test_metadata = {
            "name": "test-command",
            "description": "Test description",
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
        }
        with open(self.yaml_path, 'w') as f:
            yaml.dump(self.test_metadata, f, default_flow_style=False, sort_keys=False)

    def teardown_method(self):
        """Clean up after the tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_get_editor(self):
        """Test getting the editor command."""
        # Test with EDITOR environment variable set
        with mock.patch.dict('os.environ', {'EDITOR': 'nano'}):
            assert get_editor() == 'nano'
        
        # Test with EDITOR environment variable not set
        with mock.patch.dict('os.environ', clear=True):
            assert get_editor() == 'vi'

    @mock.patch('subprocess.run')
    def test_edit_command_metadata_success(self, mock_run):
        """Test editing command metadata successfully."""
        # Mock the subprocess.run call to simulate the editor
        mock_run.return_value = subprocess.CompletedProcess(args=['vi', self.yaml_path], returncode=0)
        
        # Call the function
        success, metadata = edit_command_metadata(self.command_dir)
        
        # Check that the function returned success
        assert success is True
        assert metadata == self.test_metadata
        
        # Verify that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] in ['vi', os.environ.get('EDITOR', 'vi')]
        assert args[0][1] == self.yaml_path
        assert kwargs['check'] is True

    @mock.patch('subprocess.run')
    def test_edit_command_metadata_invalid_yaml(self, mock_run):
        """Test editing command metadata with invalid YAML."""
        # Mock the subprocess.run call to simulate the editor
        mock_run.return_value = subprocess.CompletedProcess(args=['vi', self.yaml_path], returncode=0)
        
        # Write invalid YAML to the file after the mock is set up
        with open(self.yaml_path, 'w') as f:
            f.write('invalid: yaml:\n  - missing: colon\n  indentation error\n')
        
        # Call the function
        success, metadata = edit_command_metadata(self.command_dir)
        
        # Check that the function returned failure
        assert success is False
        assert metadata is None
        
        # Verify that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()

    def test_edit_command_metadata_file_not_found(self):
        """Test editing command metadata when the file doesn't exist."""
        # Remove the YAML file
        os.remove(self.yaml_path)
        
        # Call the function and check that it raises FileNotFoundError
        try:
            edit_command_metadata(self.command_dir)
            assert False, "Expected FileNotFoundError but no exception was raised"
        except FileNotFoundError:
            pass

    @mock.patch('subprocess.run')
    def test_edit_command_metadata_subprocess_error(self, mock_run):
        """Test editing command metadata when the subprocess fails."""
        # Mock the subprocess.run call to simulate an error
        mock_run.side_effect = subprocess.SubprocessError("Editor process failed")
        
        # Call the function and check that it raises SubprocessError
        try:
            edit_command_metadata(self.command_dir)
            assert False, "Expected SubprocessError but no exception was raised"
        except subprocess.SubprocessError:
            pass 