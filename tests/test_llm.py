"""Tests for the LLM interaction functionality."""

import os
import shutil
import tempfile
import yaml
from click.testing import CliRunner
from unittest import mock

from evai.cli import cli
from evai.llm_client import (
    generate_default_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)


class TestLLMInteraction:
    """Tests for the LLM interaction functionality."""

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

    @mock.patch('evai.llm_client.get_openai_client')
    def test_generate_metadata_with_llm(self, mock_get_client):
        """Test generating metadata with LLM."""
        # Mock the OpenAI client
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response from the OpenAI API
        mock_response = mock.MagicMock()
        mock_message = mock.MagicMock()
        mock_message.content = """```yaml
name: test-command
description: A test command
params:
  - name: param1
    type: string
    description: A test parameter
    required: true
hidden: false
disabled: false
mcp_integration:
  enabled: true
  metadata:
    endpoint: ""
    method: POST
    authentication_required: false
llm_interaction:
  enabled: false
  auto_apply: true
  max_llm_turns: 15
```"""
        mock_choice = mock.MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call the function
        metadata = generate_default_metadata_with_llm("test-command", "A test command")
        
        # Check that the client was called with the correct arguments
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert len(kwargs["messages"]) == 2
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"
        assert "test-command" in kwargs["messages"][1]["content"]
        assert "A test command" in kwargs["messages"][1]["content"]
        
        # Check the returned metadata
        assert metadata["name"] == "test-command"
        assert metadata["description"] == "A test command"
        assert len(metadata["params"]) == 1
        assert metadata["params"][0]["name"] == "param1"
        assert metadata["params"][0]["type"] == "string"
        assert metadata["params"][0]["description"] == "A test parameter"
        assert metadata["params"][0]["required"] is True
        assert metadata["hidden"] is False
        assert metadata["disabled"] is False
        assert metadata["mcp_integration"]["enabled"] is True
        assert metadata["mcp_integration"]["metadata"]["method"] == "POST"
        assert metadata["mcp_integration"]["metadata"]["authentication_required"] is False
        assert metadata["llm_interaction"]["enabled"] is False
        assert metadata["llm_interaction"]["auto_apply"] is True
        assert metadata["llm_interaction"]["max_llm_turns"] == 15

    @mock.patch('evai.llm_client.get_openai_client')
    def test_generate_implementation_with_llm(self, mock_get_client):
        """Test generating implementation with LLM."""
        # Mock the OpenAI client
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response from the OpenAI API
        mock_response = mock.MagicMock()
        mock_message = mock.MagicMock()
        mock_message.content = """```python
\"\"\"Custom command implementation.\"\"\"


def tool_echo(echo_string: str) -> str:
    \"\"\"Echo the input string.\"\"\"
    # Validate parameters
    if not echo_string:
        raise ValueError("Missing required parameter: echo_string")
    
    # Process the input
    result = echo_string.upper()
    
    # Return the result
    return result
```"""
        mock_choice = mock.MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create test metadata
        metadata = {
            "name": "test-command",
            "description": "A test command",
            "params": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "A test parameter",
                    "required": True
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
        
        # Call the function
        implementation = generate_implementation_with_llm("test-command", metadata)
        
        # Check that the client was called with the correct arguments
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert len(kwargs["messages"]) == 2
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"
        assert "test-command" in kwargs["messages"][1]["content"]
        
        # Check the returned implementation
        assert '"""Custom command implementation."""' in implementation
        assert 'def tool_echo(echo_string: str) -> str:' in implementation
        assert 'if not echo_string:' in implementation
        assert 'return result' in implementation

    @mock.patch('evai.llm_client.get_openai_client')
    def test_check_additional_info_needed(self, mock_get_client):
        """Test checking if additional information is needed."""
        # Mock the OpenAI client
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response from the OpenAI API
        mock_response = mock.MagicMock()
        mock_message = mock.MagicMock()
        mock_message.content = "Yes, I need more information. What specific task should this command perform?"
        mock_choice = mock.MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call the function
        result = check_additional_info_needed("test-command", "A test command")
        
        # Check that the client was called with the correct arguments
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert len(kwargs["messages"]) == 2
        assert kwargs["messages"][0]["role"] == "system"
        assert kwargs["messages"][1]["role"] == "user"
        assert "test-command" in kwargs["messages"][1]["content"]
        assert "A test command" in kwargs["messages"][1]["content"]
        
        # Check the returned result
        assert result == "Yes, I need more information. What specific task should this command perform?"

    @mock.patch('evai.llm_client.get_openai_client')
    def test_check_additional_info_not_needed(self, mock_get_client):
        """Test checking if additional information is not needed."""
        # Mock the OpenAI client
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock the response from the OpenAI API
        mock_response = mock.MagicMock()
        mock_message = mock.MagicMock()
        mock_message.content = "No additional information needed."
        mock_choice = mock.MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call the function
        result = check_additional_info_needed("test-command", "A detailed test command that does something specific")
        
        # Check that the client was called with the correct arguments
        mock_client.chat.completions.create.assert_called_once()
        
        # Check the returned result
        assert result is None

    @mock.patch('evai.llm_client.get_openai_client', side_effect=LLMClientError("Test error"))
    def test_generate_default_metadata_with_llm_fallback(self, mock_get_client):
        """Test fallback to default metadata when LLM fails."""
        # Call the function
        metadata = generate_default_metadata_with_llm("test-command", "A test command")
        
        # Check the returned metadata
        assert metadata["name"] == "test-command"
        assert metadata["description"] == "A test command"
        assert metadata["params"] == []
        assert metadata["hidden"] is False
        assert metadata["disabled"] is False
        assert metadata["mcp_integration"]["enabled"] is True
        assert metadata["llm_interaction"]["enabled"] is False

    @mock.patch('evai.cli.check_additional_info_needed')
    @mock.patch('evai.cli.generate_default_metadata_with_llm')
    @mock.patch('evai.cli.generate_implementation_with_llm')
    @mock.patch('evai.command_storage.edit_command_metadata')
    @mock.patch('evai.command_storage.edit_command_implementation')
    @mock.patch('evai.command_storage.run_lint_check')
    @mock.patch('evai.command_storage.get_editor')
    @mock.patch('subprocess.run')
    def test_llmadd_command(self, mock_subprocess_run, mock_get_editor, mock_lint_check, 
                           mock_edit_impl, mock_edit_meta, mock_gen_impl, 
                           mock_gen_meta, mock_check_info):
        """Test the llmadd command."""
        # Mock the editor
        mock_get_editor.return_value = "vi"
        mock_subprocess_run.return_value = mock.MagicMock(returncode=0)
        
        # Mock the LLM functions
        mock_check_info.return_value = "Additional information needed"
        mock_gen_meta.return_value = {
            "name": "test-command",
            "description": "A test command",
            "params": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "A test parameter",
                    "required": True
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
        mock_gen_impl.return_value = '"""Custom command implementation."""\n\ndef tool_echo(echo_string: str) -> str:\n    """Echo the input string."""\n    return echo_string\n'
        
        # Mock the edit functions
        mock_edit_meta.return_value = (True, mock_gen_meta.return_value)
        mock_edit_impl.return_value = True
        mock_lint_check.return_value = (True, None)
        
        # Run the command
        runner = CliRunner()
        result = runner.invoke(
            cli, ['command', 'llmadd', 'test-command'], 
            input='A test command\n\nn\nn\n',
            catch_exceptions=False
        )
        
        # Print the output for debugging
        print(f"Command output: {result.output}")
        
        # Check that the command was successful
        assert result.exit_code == 0
        assert "Command 'test-command' created successfully." in result.output
        
        # Check that the command directory was created
        command_dir = os.path.join(self.temp_dir, '.evai', 'commands', 'test-command')
        assert os.path.exists(command_dir)
        
        # Check that the LLM functions were called
        mock_check_info.assert_called_once_with("test-command", "A test command")
        mock_gen_meta.assert_called_once_with("test-command", "A test command")
        mock_gen_impl.assert_called_once_with("test-command", mock_gen_meta.return_value) 