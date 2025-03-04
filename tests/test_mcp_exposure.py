"""Tests for MCP server integration."""

import os
import sys
import json
import tempfile
from unittest import mock
import pytest

# Create a proper mock for FastMCP
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tool = MockToolRegistry()
    
    def run(self):
        """Mock run method."""
        pass

class MockToolRegistry:
    def __init__(self):
        self.registry = {}
    
    def __call__(self, name=None):
        def decorator(func):
            self.registry[name] = func
            return func
        return decorator

class MockContext:
    def __init__(self):
        pass

# Mock the MCP SDK
mcp_mock = mock.MagicMock()
mcp_mock.server.fastmcp.FastMCP = MockFastMCP
mcp_mock.server.fastmcp.Context = MockContext
sys.modules['mcp'] = mcp_mock
sys.modules['mcp.server'] = mcp_mock.server
sys.modules['mcp.server.fastmcp'] = mcp_mock.server.fastmcp

# Import after mocking
from evai.mcp_server import EVAIServer, create_server
from evai.command_storage import get_command_dir, save_command_metadata, list_commands


@pytest.fixture
def mock_commands_dir():
    """Create a temporary directory for commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the expanduser function to return our temp directory
        with mock.patch('os.path.expanduser', return_value=temp_dir):
            # Create the commands directory
            commands_dir = os.path.join(temp_dir, '.evai', 'commands')
            os.makedirs(commands_dir, exist_ok=True)
            
            # Create a test command
            test_cmd_dir = os.path.join(commands_dir, 'test-command')
            os.makedirs(test_cmd_dir, exist_ok=True)
            
            # Create command.yaml
            metadata = {
                "name": "test-command",
                "description": "A test command",
                "params": [
                    {
                        "name": "message",
                        "description": "A message to echo",
                        "required": True
                    },
                    {
                        "name": "count",
                        "description": "Number of times to echo",
                        "required": False,
                        "default": 1
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
            
            with open(os.path.join(test_cmd_dir, 'command.yaml'), 'w') as f:
                json.dump(metadata, f)
            
            # Create command.py
            with open(os.path.join(test_cmd_dir, 'command.py'), 'w') as f:
                f.write('''"""Test command implementation."""

def run(message="Hello", count=1):
    """Run the test command."""
    result = []
    for _ in range(count):
        result.append(message)
    return {"messages": result}
''')
            
            # Create a command with MCP integration disabled
            disabled_mcp_dir = os.path.join(commands_dir, 'disabled-mcp')
            os.makedirs(disabled_mcp_dir, exist_ok=True)
            
            # Create command.yaml for disabled MCP command
            disabled_metadata = {
                "name": "disabled-mcp",
                "description": "A command with MCP integration disabled",
                "params": [],
                "hidden": False,
                "disabled": False,
                "mcp_integration": {
                    "enabled": False,
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
            
            with open(os.path.join(disabled_mcp_dir, 'command.yaml'), 'w') as f:
                json.dump(disabled_metadata, f)
            
            # Create command.py for disabled MCP command
            with open(os.path.join(disabled_mcp_dir, 'command.py'), 'w') as f:
                f.write('''"""Disabled MCP command implementation."""

def run():
    """Run the disabled MCP command."""
    return {"status": "disabled"}
''')
            
            # Mock list_commands to return our test commands
            with mock.patch('evai.mcp_server.list_commands', return_value=[
                {
                    "name": "test-command",
                    "description": "A test command",
                    "path": test_cmd_dir
                },
                {
                    "name": "disabled-mcp",
                    "description": "A command with MCP integration disabled",
                    "path": disabled_mcp_dir
                }
            ]):
                # Mock load_command_metadata to return our test metadata
                with mock.patch('evai.mcp_server.load_command_metadata', side_effect=lambda path: 
                    metadata if "test-command" in path else disabled_metadata):
                    yield temp_dir


@mock.patch('evai.mcp_server.run_command')
def test_server_initialization(mock_run_command, mock_commands_dir):
    """Test MCP server initialization."""
    # Create a server
    server = create_server("Test Server")
    
    # Check that the server was initialized correctly
    assert server.name == "Test Server"
    assert isinstance(server.mcp, MockFastMCP)
    assert "test-command" in server.commands
    assert "disabled-mcp" not in server.commands
    
    # Check that built-in tools are registered
    assert "add_command" in server.mcp.tool.registry
    assert "list_commands" in server.mcp.tool.registry
    assert "edit_command_implementation" in server.mcp.tool.registry
    assert "edit_command_metadata" in server.mcp.tool.registry
    assert "test-command" in server.mcp.tool.registry


@mock.patch('evai.mcp_server.run_command')
def test_command_execution(mock_run_command, mock_commands_dir):
    """Test command execution through MCP."""
    # Mock the run_command function
    mock_run_command.return_value = {"messages": ["Hello World", "Hello World", "Hello World"]}
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "test-command":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    result = tool_func(message="Hello World", count=3)
    
    # Check that run_command was called with the correct arguments
    mock_run_command.assert_called_once_with("test-command", message="Hello World", count=3)
    
    # Check the result
    assert result == {"messages": ["Hello World", "Hello World", "Hello World"]}


@mock.patch('evai.mcp_server.run_command')
def test_command_execution_error(mock_run_command, mock_commands_dir):
    """Test command execution error handling."""
    # Mock the run_command function to raise an exception
    mock_run_command.side_effect = Exception("Test error")
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "test-command":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    result = tool_func(message="Hello World", count=3)
    
    # Check that run_command was called with the correct arguments
    mock_run_command.assert_called_once_with("test-command", message="Hello World", count=3)
    
    # Check the result
    assert result == {"error": "Test error"}


@mock.patch('evai.mcp_server.list_commands')
def test_list_commands_tool(mock_list_commands, mock_commands_dir):
    """Test the list_commands built-in tool."""
    # Mock the list_commands function
    mock_list_commands.return_value = [
        {
            "name": "test-command",
            "description": "A test command",
            "path": "/path/to/test-command"
        }
    ]
    
    # Create a server
    server = create_server("Test Server")
    
    # Reset the mock to clear previous calls
    mock_list_commands.reset_mock()
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "list_commands":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    result = tool_func()
    
    # Check that list_commands was called
    mock_list_commands.assert_called_once()
    
    # Check the result
    assert result == {
        "status": "success",
        "commands": [
            {
                "name": "test-command",
                "description": "A test command",
                "path": "/path/to/test-command"
            }
        ]
    }


@mock.patch('evai.mcp_server.get_command_dir')
@mock.patch('evai.mcp_server.save_command_metadata')
def test_add_command_tool(mock_save_metadata, mock_get_command_dir, mock_commands_dir):
    """Test the add_command built-in tool."""
    # Mock the get_command_dir function
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'new-command')
    mock_get_command_dir.return_value = command_dir
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "add_command":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    with mock.patch('os.path.exists', return_value=False):  # Mock that the command doesn't exist yet
        with mock.patch('builtins.open', mock.mock_open()) as mock_file:
            result = tool_func(
                command_name="new-command",
                description="A new command",
                params=[
                    {
                        "name": "message",
                        "description": "A message to echo",
                        "required": True
                    }
                ]
            )
    
    # Check that get_command_dir was called with the correct arguments
    mock_get_command_dir.assert_called_once_with("new-command")
    
    # Check that save_command_metadata was called with the correct arguments
    mock_save_metadata.assert_called_once()
    args, kwargs = mock_save_metadata.call_args
    assert args[0] == command_dir
    assert args[1]["name"] == "new-command"
    assert args[1]["description"] == "A new command"
    assert args[1]["params"] == [{"name": "message", "description": "A message to echo", "required": True}]
    
    # Check the result
    assert result["status"] == "success"
    assert "new-command" in result["message"]
    assert command_dir == result["command_dir"]


def test_add_command_tool_validation(mock_commands_dir):
    """Test validation in the add_command built-in tool."""
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "add_command":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Test empty command name
    result = tool_func(command_name="")
    assert result["status"] == "error"
    assert "Command name cannot be empty" in result["message"]
    
    # Test invalid command name
    result = tool_func(command_name="invalid command name")
    assert result["status"] == "error"
    assert "Command name must contain only alphanumeric characters" in result["message"]
    
    # Test command already exists
    with mock.patch('os.path.exists', return_value=True):  # Mock that the command already exists
        result = tool_func(command_name="existing-command")
        assert result["status"] == "error"
        assert "already exists" in result["message"]


@mock.patch('evai.mcp_server.get_command_dir')
@mock.patch('builtins.open', new_callable=mock.mock_open)
def test_edit_command_implementation_tool(mock_open, mock_get_command_dir, mock_commands_dir):
    """Test the edit_command_implementation built-in tool."""
    # Mock the get_command_dir function
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'test-command')
    mock_get_command_dir.return_value = command_dir
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "edit_command_implementation":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Reset the mock to clear previous calls
    mock_open.reset_mock()
    
    # Call the tool function
    with mock.patch('os.path.exists', return_value=True):  # Mock that the command exists
        with mock.patch('importlib.reload') as mock_reload:
            result = tool_func(
                command_name="test-command",
                implementation='''"""Updated test command implementation."""

def run(message="Hello", count=1):
    """Run the updated test command."""
    result = []
    for _ in range(count):
        result.append(f"Updated: {message}")
    return {"messages": result}
'''
            )
    
    # Check that get_command_dir was called with the correct arguments
    mock_get_command_dir.assert_called_once_with("test-command")
    
    # Check that the file was written with the correct content
    mock_open.assert_any_call(os.path.join(command_dir, "command.py"), "w")
    
    # Check the result
    assert result["status"] == "success"
    assert "test-command" in result["message"]
    assert "updated successfully" in result["message"]


@mock.patch('evai.mcp_server.get_command_dir')
def test_edit_command_implementation_nonexistent(mock_get_command_dir, mock_commands_dir):
    """Test editing implementation of a nonexistent command."""
    # Mock the get_command_dir function
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'nonexistent')
    mock_get_command_dir.return_value = command_dir
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "edit_command_implementation":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    with mock.patch('os.path.exists', return_value=False):  # Mock that the command doesn't exist
        result = tool_func(
            command_name="nonexistent",
            implementation="def run(): pass"
        )
    
    # Check the result
    assert result["status"] == "error"
    assert "does not exist" in result["message"]


@mock.patch('evai.mcp_server.get_command_dir')
@mock.patch('evai.mcp_server.save_command_metadata')
def test_edit_command_metadata_tool(mock_save_metadata, mock_get_command_dir, mock_commands_dir):
    """Test the edit_command_metadata built-in tool."""
    # Mock the get_command_dir function
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'test-command')
    mock_get_command_dir.return_value = command_dir
    
    # Create a server
    server = create_server("Test Server")
    
    # Add a command to the server's commands dict
    server.commands["test-command"] = {
        "name": "test-command",
        "description": "Original description",
        "params": []
    }
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "edit_command_metadata":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    with mock.patch('os.path.exists', return_value=True):  # Mock that the command exists
        with mock.patch.dict(server.mcp.tool.registry, {"test-command": lambda: None}):
            result = tool_func(
                command_name="test-command",
                metadata={
                    "name": "test-command",
                    "description": "Updated description",
                    "params": [
                        {
                            "name": "new_param",
                            "description": "A new parameter",
                            "required": True
                        }
                    ],
                    "hidden": False,
                    "disabled": False,
                    "mcp_integration": {
                        "enabled": True
                    },
                    "llm_interaction": {
                        "enabled": False
                    }
                }
            )
    
    # Check that get_command_dir was called with the correct arguments
    mock_get_command_dir.assert_called_once_with("test-command")
    
    # Check that save_command_metadata was called with the correct arguments
    mock_save_metadata.assert_called_once()
    args, kwargs = mock_save_metadata.call_args
    assert args[0] == command_dir
    assert args[1]["name"] == "test-command"
    assert args[1]["description"] == "Updated description"
    assert len(args[1]["params"]) == 1
    assert args[1]["params"][0]["name"] == "new_param"
    
    # Check the result
    assert result["status"] == "success"
    assert "test-command" in result["message"]
    assert "updated successfully" in result["message"]
    
    # Check that the server's commands dict was updated
    assert server.commands["test-command"]["description"] == "Updated description"
    assert len(server.commands["test-command"]["params"]) == 1
    assert server.commands["test-command"]["params"][0]["name"] == "new_param"


@mock.patch('evai.mcp_server.get_command_dir')
def test_edit_command_metadata_nonexistent(mock_get_command_dir, mock_commands_dir):
    """Test editing metadata of a nonexistent command."""
    # Mock the get_command_dir function
    command_dir = os.path.join(mock_commands_dir, '.evai', 'commands', 'nonexistent')
    mock_get_command_dir.return_value = command_dir
    
    # Create a server
    server = create_server("Test Server")
    
    # Get the tool function
    tool_func = None
    for name, func in server.mcp.tool.registry.items():
        if name == "edit_command_metadata":
            tool_func = func
            break
    
    assert tool_func is not None
    
    # Call the tool function
    with mock.patch('os.path.exists', return_value=False):  # Mock that the command doesn't exist
        result = tool_func(
            command_name="nonexistent",
            metadata={"name": "nonexistent", "description": "Nonexistent command"}
        )
    
    # Check the result
    assert result["status"] == "error"
    assert "does not exist" in result["message"] 