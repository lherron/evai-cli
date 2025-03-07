"""Tests for the LLM command."""

import os
import pytest
from unittest.mock import patch, MagicMock
from evai.cli.commands.llm import run_llm_command_with_mcp, call_claude_sync, llm

# Sample response for mocking
SAMPLE_RESPONSE = "This is a sample response from Claude."

@pytest.fixture
def mock_anthropic():
    """Mock the Anthropic client."""
    with patch('anthropic.Anthropic') as mock_client:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=SAMPLE_RESPONSE)]
        
        # Set up the mock client
        mock_instance = mock_client.return_value
        mock_instance.messages.create.return_value = mock_response
        
        yield mock_client

@pytest.fixture
def mock_mcp_session():
    """Mock the MCP ClientSession."""
    with patch('evai.cli.commands.llm.ClientSession') as mock_session:
        # Create mock objects
        mock_instance = mock_session.return_value.__aenter__.return_value
        mock_instance.initialize = MagicMock()
        mock_instance.list_prompts = MagicMock(return_value=[MagicMock(name="default")])
        mock_instance.get_prompt = MagicMock(return_value=MagicMock(
            messages=[MagicMock(role="assistant", content=MagicMock(text=SAMPLE_RESPONSE))]
        ))
        
        yield mock_session

@pytest.fixture
def mock_stdio_client():
    """Mock the stdio_client."""
    with patch('evai.cli.commands.llm.stdio_client') as mock_client:
        # Set up the mock client
        mock_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
        
        yield mock_client

@pytest.fixture
def mock_env():
    """Set up environment variables for testing."""
    original_env = os.environ.copy()
    os.environ['ANTHROPIC_API_KEY'] = 'test_key'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

def test_call_claude_sync(mock_anthropic, mock_env):
    """Test the call_claude_sync function."""
    # Call the function
    result = call_claude_sync("Test prompt")
    
    # Verify the result
    assert result == SAMPLE_RESPONSE
    
    # Verify the API call
    mock_anthropic.return_value.messages.create.assert_called_once()
    args, kwargs = mock_anthropic.return_value.messages.create.call_args
    assert kwargs['model'] == "claude-3-7-sonnet-20250219"
    assert kwargs['messages'][0]['content'] == "Test prompt"

@pytest.mark.asyncio
async def test_run_llm_command_with_mcp(mock_mcp_session, mock_stdio_client, mock_env):
    """Test the run_llm_command_with_mcp function."""
    # Call the function
    result = run_llm_command_with_mcp("Test prompt")
    
    # Verify the result
    assert result == SAMPLE_RESPONSE
    
    # Verify the MCP session was initialized
    mock_mcp_session.return_value.__aenter__.return_value.initialize.assert_called_once()
    mock_mcp_session.return_value.__aenter__.return_value.list_prompts.assert_called_once()
    mock_mcp_session.return_value.__aenter__.return_value.get_prompt.assert_called_once()

@pytest.mark.parametrize("use_mcp", [True, False])
def test_llm_command(use_mcp, mock_anthropic, mock_mcp_session, mock_stdio_client, mock_env, monkeypatch):
    """Test the llm command with both direct and MCP modes."""
    # Mock click.echo
    mock_echo = MagicMock()
    monkeypatch.setattr('click.echo', mock_echo)
    
    # Call the command
    llm("Test prompt", use_mcp)
    
    # Verify the result was echoed
    mock_echo.assert_called_once_with(SAMPLE_RESPONSE)
    
    # Verify the appropriate function was called
    if use_mcp:
        mock_mcp_session.return_value.__aenter__.return_value.get_prompt.assert_called_once()
    else:
        mock_anthropic.return_value.messages.create.assert_called_once() 