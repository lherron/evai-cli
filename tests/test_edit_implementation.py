"""Tests for the tool implementation editing and lint checking functionality."""

import os
import shutil
import tempfile
from unittest import mock
import subprocess

from evai.tool_storage import edit_tool_implementation, run_lint_check


class TestEditImplementation:
    """Tests for the tool implementation editing and lint checking functionality."""

    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for the tests
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test tool directory
        self.tool_dir = os.path.join(self.temp_dir, 'test-tool')
        os.makedirs(self.tool_dir, exist_ok=True)
        
        # Create a test tool.py file with valid Python code
        self.py_path = os.path.join(self.tool_dir, 'tool.py')
        with open(self.py_path, 'w') as f:
            f.write('"""Custom tool implementation."""\n\n\ndef tool_echo(echo_string: str) -> str:\n    """Echo the input string."""\n    return echo_string\n')

    def teardown_method(self):
        """Clean up after the tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    @mock.patch('subprocess.run')
    def test_edit_tool_implementation_success(self, mock_run):
        """Test editing tool implementation successfully."""
        # Mock the subprocess.run call to simulate the editor
        mock_run.return_value = subprocess.CompletedProcess(args=['vi', self.py_path], returncode=0)
        
        # Mock the os.environ to avoid 'which' calls 
        with mock.patch.dict('os.environ', {'EDITOR': 'vi'}):
            # Call the function
            success = edit_tool_implementation(self.tool_dir)
        
        # Check that the function returned success
        assert success is True
        
        # Verify that subprocess.run was called with the correct arguments
        # Get the second call since the first one might be to check for editors
        assert len(mock_run.call_args_list) >= 1
        
        # Get the last call arguments
        args, kwargs = mock_run.call_args
        assert args[0][1] == self.py_path
        assert kwargs['check'] is True

    def test_edit_tool_implementation_file_not_found(self):
        """Test editing tool implementation when the file doesn't exist."""
        # Remove the Python file
        os.remove(self.py_path)
        
        # Call the function and check that it raises FileNotFoundError
        try:
            edit_tool_implementation(self.tool_dir)
            assert False, "Expected FileNotFoundError but no exception was raised"
        except FileNotFoundError:
            pass

    @mock.patch('subprocess.run')
    def test_edit_tool_implementation_subprocess_error(self, mock_run):
        """Test editing tool implementation when the subprocess fails."""
        # Mock the subprocess.run call to simulate an error
        mock_run.side_effect = subprocess.SubprocessError("Editor process failed")
        
        # Call the function and check that it raises SubprocessError
        try:
            edit_tool_implementation(self.tool_dir)
            assert False, "Expected SubprocessError but no exception was raised"
        except subprocess.SubprocessError:
            pass

    @mock.patch('subprocess.run')
    def test_run_lint_check_success(self, mock_run):
        """Test running lint check on a valid Python file."""
        # Mock the subprocess.run call to simulate flake8 passing
        mock_run.return_value = subprocess.CompletedProcess(
            args=['flake8', self.py_path],
            returncode=0,
            stdout='',
            stderr=''
        )
        
        # Call the function
        success, output = run_lint_check(self.tool_dir)
        
        # Check that the function returned success
        assert success is True
        assert output is None
        
        # Verify that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0][0] == 'flake8'
        assert args[0][1] == self.py_path
        assert kwargs['check'] is False
        assert kwargs['stdout'] == subprocess.PIPE
        assert kwargs['stderr'] == subprocess.PIPE
        assert kwargs['text'] is True

    @mock.patch('subprocess.run')
    def test_run_lint_check_failure(self, mock_run):
        """Test running lint check on a Python file with lint errors."""
        # Create a Python file with lint errors
        with open(self.py_path, 'w') as f:
            f.write('"""Custom tool implementation."""\n\nimport os\n\ndef tool_echo(echo_string: str) -> str:\n    x = 1\n    y = 2  # unused variable\n    return echo_string\n')
        
        # Mock the subprocess.run call to simulate flake8 failing
        mock_run.return_value = subprocess.CompletedProcess(
            args=['flake8', self.py_path],
            returncode=1,
            stdout=f'{self.py_path}:7:5: F841 local variable \'y\' is assigned to but never used',
            stderr=''
        )
        
        # Call the function
        success, output = run_lint_check(self.tool_dir)
        
        # Check that the function returned failure
        assert success is False
        assert 'F841 local variable \'y\' is assigned to but never used' in output
        
        # Verify that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()

    @mock.patch('subprocess.run')
    def test_run_lint_check_flake8_not_found(self, mock_run):
        """Test running lint check when flake8 is not installed."""
        # Mock the subprocess.run call to simulate flake8 not being found
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'flake8'")
        
        # Call the function
        success, output = run_lint_check(self.tool_dir)
        
        # Check that the function returned success and skipped
        assert success is True
        assert output is None
        
        # Verify that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()

    def test_run_lint_check_file_not_found(self):
        """Test running lint check when the file doesn't exist."""
        # Remove the Python file
        os.remove(self.py_path)
        
        # Call the function and check that it raises FileNotFoundError
        try:
            run_lint_check(self.tool_dir)
            assert False, "Expected FileNotFoundError but no exception was raised"
        except FileNotFoundError:
            pass 