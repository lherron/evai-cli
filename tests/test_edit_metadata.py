"""Tests for the tool metadata editing functionality."""

import os
import sys
import shutil
import tempfile
import yaml
from unittest import mock
import subprocess

from evai_cli.tool_storage import edit_tool_metadata, get_editor


class TestEditMetadata:
    """Tests for the tool metadata editing functionality."""

    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test tool directory
        self.tool_dir = os.path.join(self.temp_dir, 'test-tool')
        os.makedirs(self.tool_dir, exist_ok=True)
        
        # Create a test tool.yaml file
        self.yaml_path = os.path.join(self.tool_dir, 'tool.yaml')
        self.test_metadata = {
            "name": "test-tool",
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
        # We need to also mock the subprocess.run call for the 'which' command
        # that might be called to find an editor
        with mock.patch.dict('os.environ', clear=True):
            with mock.patch('subprocess.run', side_effect=subprocess.SubprocessError):
                # Default editor when none found on system
                if sys.platform == 'win32':
                    assert get_editor() == 'notepad.exe'
                else:
                    assert get_editor() == 'nano'

    @mock.patch('subprocess.run')
    def test_edit_tool_metadata_success(self, mock_run):
        """Test editing tool metadata successfully."""
        # Mock the subprocess.run call to simulate the editor
        mock_run.return_value = subprocess.CompletedProcess(args=['vi', self.yaml_path], returncode=0)
        
        # Mock load_tool_metadata to return our test metadata
        with mock.patch('evai.tool_storage.load_tool_metadata', return_value=self.test_metadata):
            # Mock the os.environ to avoid 'which' calls 
            with mock.patch.dict('os.environ', {'EDITOR': 'vi'}):
                # Call the function
                success, metadata = edit_tool_metadata(self.tool_dir)
        
        # Check that the function returned success
        assert success is True
        assert metadata == self.test_metadata
        
        # Verify that subprocess.run was called with the correct arguments
        # Get the last call since there might be multiple calls 
        assert len(mock_run.call_args_list) >= 1
        
        # Get the last call arguments
        args, kwargs = mock_run.call_args
        assert args[0][1].endswith('tool.yaml')
        assert kwargs['check'] is True

    @mock.patch('subprocess.run')
    def test_edit_tool_metadata_invalid_yaml(self, mock_run):
        """Test editing tool metadata with invalid YAML."""
        # Mock the subprocess.run call to simulate the editor
        mock_run.return_value = subprocess.CompletedProcess(args=['vi', self.yaml_path], returncode=0)
        
        # Mock load_tool_metadata to raise a YAML error
        yaml_error = yaml.YAMLError("Invalid YAML")
        with mock.patch('evai.tool_storage.load_tool_metadata', side_effect=yaml_error):
            # Mock the os.environ to avoid 'which' calls 
            with mock.patch.dict('os.environ', {'EDITOR': 'vi'}):
                # Call the function
                success, metadata = edit_tool_metadata(self.tool_dir)
        
        # Check that the function returned failure
        assert success is False
        assert metadata is None
        
        # Verify that subprocess.run was called at least once
        assert mock_run.called

    def test_edit_tool_metadata_file_not_found(self):
        """Test editing tool metadata when the file doesn't exist."""
        # Remove the YAML file
        os.remove(self.yaml_path)
        
        # Call the function and check that it raises FileNotFoundError
        try:
            edit_tool_metadata(self.tool_dir)
            assert False, "Expected FileNotFoundError but no exception was raised"
        except FileNotFoundError:
            pass

    @mock.patch('subprocess.run')
    def test_edit_tool_metadata_subprocess_error(self, mock_run):
        """Test editing tool metadata when the subprocess fails."""
        # Mock the subprocess.run call to simulate an error
        mock_run.side_effect = subprocess.SubprocessError("Editor process failed")
        
        # Call the function and check that it raises SubprocessError
        try:
            edit_tool_metadata(self.tool_dir)
            assert False, "Expected SubprocessError but no exception was raised"
        except subprocess.SubprocessError:
            pass 