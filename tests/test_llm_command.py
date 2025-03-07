"""Tests for the LLM command."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from click.testing import CliRunner
from evai.cli.commands.llm import llm


@pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, 
                    reason="ANTHROPIC_API_KEY not set")
def test_llm_command_missing_api_key():
    """Test that the LLM command fails gracefully without API key."""
    runner = CliRunner()
    
    # Run with mock environment without API key
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        result = runner.invoke(llm, ["Test prompt"])
        assert result.exit_code != 0
        assert "ANTHROPIC_API_KEY" in result.output


@pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, 
                    reason="ANTHROPIC_API_KEY not set")
def test_llm_command_direct_call():
    """Test the LLM command with direct Claude API call."""
    runner = CliRunner()
    
    # Create mock for Anthropic client
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is a direct response from Claude.")]
    
    # Create patch for Anthropic client
    with patch("anthropic.Anthropic") as mock_anthropic:
        # Set up the mock
        mock_client = mock_anthropic.return_value
        mock_client.messages.create = MagicMock(return_value=mock_response)
        
        # Run the command (without --use-mcp)
        result = runner.invoke(llm, ["Test prompt"])
        
        # Check the result
        assert result.exit_code == 0
        assert "This is a direct response from Claude." in result.output
        
        # Verify the call
        mock_client.messages.create.assert_called_once()
        args, kwargs = mock_client.messages.create.call_args
        assert kwargs["model"] == "claude-3-7-sonnet-20250219"
        assert kwargs["messages"][0]["role"] == "user"
        assert kwargs["messages"][0]["content"] == "Test prompt"


@pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, 
                    reason="ANTHROPIC_API_KEY not set")
def test_llm_command_with_mcp():
    """Test the LLM command using MCP integration."""
    runner = CliRunner()
    
    # Create mock for Popen
    mock_popen = MagicMock()
    mock_popen_instance = MagicMock()
    mock_popen.return_value.__enter__.return_value = mock_popen_instance
    
    # Mock Claude response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is a response via MCP.")]
    
    # Create patches
    with patch("subprocess.Popen", mock_popen), \
         patch("time.sleep"), \
         patch("anthropic.Anthropic") as mock_anthropic:
        
        # Set up the anthropic mock
        mock_client = mock_anthropic.return_value
        mock_client.messages.create = MagicMock(return_value=mock_response)
        
        # Run the command with --use-mcp flag
        result = runner.invoke(llm, ["Test prompt", "--use-mcp"])
        
        # Check the result
        assert result.exit_code == 0
        assert "This is a response via MCP." in result.output
        
        # Verify the subprocess was created with correct args
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0][0] == "python"
        assert args[0][1] == "-m"
        assert args[0][2] == "evai.mcp.mcp_server"
        
        # Verify the termination
        mock_popen_instance.terminate.assert_called_once()