"""Command-line interface for EVAI."""

import sys
import os
import json
import click
import importlib
import pkgutil
from . import __version__
from .command_storage import (
    get_command_dir, 
    save_command_metadata, 
    edit_command_metadata,
    edit_command_implementation,
    run_lint_check,
    list_commands,
    run_command,
    load_command_metadata
)
from .llm_client import (
    generate_default_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
import yaml

# Initialize rich console
console = Console()


@click.group(help="EVAI CLI - Command-line interface for EVAI")
@click.version_option(version=__version__, prog_name="evai")
def cli():
    """EVAI CLI - Command-line interface for EVAI."""
    pass


@cli.group()
def command():
    """Manage custom commands."""
    pass


@command.command()
@click.argument("command_name")
def add(command_name):
    """Add a new custom command."""
    try:
        # Get the command directory
        command_dir = get_command_dir(command_name)
        
        # Create default command.yaml
        default_metadata = {
            "name": command_name,
            "description": "Default description",
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
        
        # Save the metadata
        save_command_metadata(command_dir, default_metadata)
        
        # Create default command.py
        command_py_path = os.path.join(command_dir, "command.py")
        with open(command_py_path, "w") as f:
            f.write('"""Custom command implementation."""\n\n\ndef run(**kwargs):\n    """Run the command with the given arguments."""\n    print("Hello World")\n    return {"status": "success"}\n')
        
        click.echo(f"Command '{command_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(command_dir, 'command.yaml')}")
        click.echo(f"- Implementation: {command_py_path}")
        click.echo(f"\nTo edit this command, run: evai command edit {command_name}")
        
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)


@command.command()
@click.argument("command_name")
@click.option("--metadata/--no-metadata", default=True, help="Edit command metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit command implementation")
def edit(command_name, metadata, implementation):
    """Edit an existing command."""
    try:
        # Get the command directory
        command_dir = get_command_dir(command_name)
        
        # Edit metadata if requested
        if metadata:
            click.echo(f"Opening command.yaml for editing...")
            
            # Loop until the user provides valid YAML or chooses to abort
            while True:
                success, metadata_content = edit_command_metadata(command_dir)
                
                if success:
                    click.echo("Command metadata saved successfully.")
                    break
                else:
                    if not click.confirm("Invalid YAML. Would you like to try again?"):
                        click.echo("Aborting metadata edit.")
                        break
                    click.echo("Opening command.yaml for editing again...")
        
        # Edit implementation if requested
        if implementation:
            click.echo(f"Opening command.py for editing...")
            edit_command_implementation(command_dir)
            
            # Run lint check on the implementation file
            click.echo("Running lint check on command.py...")
            lint_success, lint_output = run_lint_check(command_dir)
            
            # Loop until the lint check passes or the user chooses to abort
            while not lint_success:
                click.echo("Lint check failed. Please fix the following issues:")
                click.echo(lint_output)
                
                if not click.confirm("Would you like to edit the file again?"):
                    click.echo("Aborting. The command implementation may contain lint errors.")
                    break
                    
                click.echo("Opening command.py for editing again...")
                edit_command_implementation(command_dir)
                
                click.echo("Running lint check on command.py...")
                lint_success, lint_output = run_lint_check(command_dir)
            
            if lint_success:
                click.echo("Lint check passed. Command implementation saved successfully.")
        
        click.echo(f"Command '{command_name}' edit complete.")
        
    except Exception as e:
        click.echo(f"Error editing command: {e}", err=True)
        sys.exit(1)


@command.command()
def list():
    """List available commands."""
    try:
        commands = list_commands()
        
        if not commands:
            click.echo("No commands found.")
            return
        
        click.echo("Available commands:")
        for cmd in commands:
            click.echo(f"  {cmd['name']}: {cmd['description']}")
    
    except Exception as e:
        click.echo(f"Error listing commands: {e}", err=True)
        sys.exit(1)


@command.command()
@click.argument("command_name")
@click.option("--param", "-p", multiple=True, help="Command parameters in the format key=value")
def run(command_name, param):
    """Run a command with the given arguments."""
    try:
        # Parse parameters
        kwargs = {}
        for p in param:
            try:
                key, value = p.split("=", 1)
                # Try to parse the value as JSON
                try:
                    kwargs[key] = json.loads(value)
                except json.JSONDecodeError:
                    # If not valid JSON, use the raw string
                    kwargs[key] = value
            except ValueError:
                click.echo(f"Invalid parameter format: {p}. Use key=value format.", err=True)
                sys.exit(1)
        
        # Get command metadata to check parameter requirements
        command_dir = get_command_dir(command_name)
        metadata = load_command_metadata(command_dir)
        
        # Check required parameters
        if "params" in metadata:
            for param_def in metadata.get("params", []):
                param_name = param_def.get("name")
                if param_name and param_def.get("required", True) and param_name not in kwargs:
                    # If parameter has a default value, use it
                    if "default" in param_def and param_def["default"] is not None:
                        kwargs[param_name] = param_def["default"]
                    else:
                        click.echo(f"Missing required parameter: {param_name}", err=True)
                        sys.exit(1)
        
        # Run the command
        result = run_command(command_name, **kwargs)
        
        # Print the result
        if isinstance(result, dict):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error running command: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--name", "-n", default="EVAI Commands", help="Name of the MCP server")
def server(name):
    """Start an MCP server exposing all commands."""
    try:
        # Import here to avoid dependency issues if MCP is not installed
        from .mcp_server import run_server
        
        click.echo(f"Starting MCP server '{name}'...")
        click.echo("Press Ctrl+C to stop the server.")
        
        # Run the server
        run_server(name)
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Please install the MCP Python SDK with: pip install mcp", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting MCP server: {e}", err=True)
        sys.exit(1)


# Automatically add all commands from the commands submodule
def import_commands():
    """Import all commands from the commands submodule and add them to the command group."""
    from . import commands
    
    # Get the package path
    package_path = os.path.dirname(commands.__file__)
    
    # Iterate through all modules in the commands package
    for _, module_name, _ in pkgutil.iter_modules([package_path]):
        # Import the module
        module = importlib.import_module(f".commands.{module_name}", package="evai")
        
        # Find all Click commands in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a Click command
            if isinstance(attr, click.Command):
                # Add the command to the command group
                command.add_command(attr)


# Import commands
import_commands()


def main():
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    return cli()


if __name__ == "__main__":
    sys.exit(main()) 