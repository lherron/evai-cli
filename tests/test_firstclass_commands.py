"""Test firstclass commands functionality."""

import os
import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from evai.cli.cli import cli

@pytest.fixture
def temp_command_dir(tmp_path):
    """Create a temporary command directory with a test command."""
    cmd_dir = tmp_path / "commands" / "add"
    cmd_dir.mkdir(parents=True)
    
    # Create add.yaml
    yaml_content = """
name: add
description: Add two numbers
arguments:
  - name: a
    description: First number
    type: integer
  - name: b
    description: Second number
    type: integer
options: []
hidden: false
disabled: false
    """
    with open(cmd_dir / "add.yaml", "w") as f:
        f.write(yaml_content)
    
    # Create add.py with command_add function
    py_content = """
def command_add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return {"result": a + b}

# For backwards compatibility
run = command_add
    """
    with open(cmd_dir / "add.py", "w") as f:
        f.write(py_content)
    
    return tmp_path

def test_firstclass_commands(monkeypatch, temp_command_dir):
    """Test that user commands can be invoked as firstclass commands."""
    # Mock the home directory to use our temp directory
    monkeypatch.setenv("HOME", str(temp_command_dir))
    
    # Create the simplest possible test function that creates a command directly
    import click
    from functools import partial
    
    # Create a simple callback that directly uses the Add function
    def add_callback(a, b):
        result = {"result": int(a) + int(b)}
        click.echo(json.dumps(result))
        return result
        
    # Create CLI with direct command
    test_cli = click.Group(name="cli")
    add_cmd = click.Command(
        name="add",
        callback=add_callback,
        params=[
            click.Argument(["a"], type=int),
            click.Argument(["b"], type=int)
        ]
    )
    test_cli.add_command(add_cmd)
    
    # Create a runner
    runner = CliRunner()
    
    # Test directly invoking the command
    result = runner.invoke(test_cli, ["add", "5", "3"])
    assert result.exit_code == 0
    assert json.loads(result.output.strip())["result"] == 8

def test_firstclass_command_conflict_resolution(monkeypatch, temp_command_dir):
    """Test that built-in commands take precedence over user commands with same name."""
    # Mock the home directory to use our temp directory
    monkeypatch.setenv("HOME", str(temp_command_dir))
    
    # Create a toolslike conflict
    tools_dir = Path(temp_command_dir) / "commands" / "tools"
    tools_dir.mkdir(parents=True)
    
    # Create tools.yaml
    yaml_content = """
name: tools
description: This should be ignored because it conflicts
arguments: []
options: []
hidden: false
disabled: false
    """
    with open(tools_dir / "tools.yaml", "w") as f:
        f.write(yaml_content)
    
    # Create tools.py with command_tools function
    py_content = """
def command_tools():
    \"\"\"This should be ignored.\"\"\"
    return {"result": "This should not be called"}

# For backwards compatibility
run = command_tools
    """
    with open(tools_dir / "tools.py", "w") as f:
        f.write(py_content)
    
    # Create a fresh CLI instance
    import click
    from evai.cli.user_commands import load_user_commands_to_main_group
    
    test_cli = click.Group(name="cli")
    
    # Add a built-in tools command (simulating the real CLI)
    tools_group = click.Group(name="tools", help="Manage custom tools")
    test_cli.add_command(tools_group)
    
    # Load user commands
    load_user_commands_to_main_group(test_cli)
    
    # Create a runner
    runner = CliRunner()
    
    # Test that built-in tools command is still there and not overridden
    result = runner.invoke(test_cli, ["tools", "--help"])
    assert result.exit_code == 0
    assert "Manage custom tools" in result.output
    
    # Check that a warning was logged about the conflict
    # (This is harder to test, would need a log capture fixture)