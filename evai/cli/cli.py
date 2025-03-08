"""Command-line interface for EVAI."""

import sys
import os
import json
import click
import importlib
import pkgutil
from pathlib import Path
from evai import __version__
from evai.tool_storage import (
    get_tool_dir, 
    save_tool_metadata, 
    edit_tool_metadata,
    edit_tool_implementation,
    run_lint_check,
    list_tools,
    run_tool,
    load_tool_metadata
)
from evai.llm_client import (
    generate_default_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
import yaml
import logging

def get_click_type(type_str: str):
    """
    Map metadata type strings to Click parameter types.
    
    Args:
        type_str: The type string from metadata (e.g., "string", "integer").
    
    Returns:
        The corresponding Click type object.
    """
    type_map = {
        "string": click.STRING,
        "integer": click.INT,
        "float": click.FLOAT,
        "boolean": click.BOOL,
    }
    return type_map.get(type_str.lower(), click.STRING)  # Default to STRING if unknown

def convert_value(value: str, type_str: str):
    """
    Convert a string value to the specified type based on metadata.
    
    Args:
        value: The string value to convert (e.g., "8").
        type_str: The target type from metadata (e.g., "integer").
    
    Returns:
        The converted value.
    
    Raises:
        ValueError: If conversion fails.
    """
    type_str = type_str.lower()
    try:
        if type_str == "string":
            return str(value)
        elif type_str == "integer":
            return int(value)
        elif type_str == "float":
            return float(value)
        elif type_str == "boolean":
            return value.lower() in ("true", "1", "yes", "on") if isinstance(value, str) else bool(value)
        else:
            return str(value)  # Default to string for unknown types
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert '{value}' to {type_str}: {str(e)}")

def create_command(command_name: str, metadata: dict, module):
    """
    Create a Click command with typed arguments and options from metadata.
    
    Args:
        command_name: The name of the command.
        metadata: The command's metadata dictionary.
        module: The imported module containing the command's run function.
    
    Returns:
        A configured click.Command object.
    """
    command = click.Command(name=command_name, help=metadata.get("description", ""))
    
    # Add positional arguments with types
    for arg in metadata.get("arguments", []):
        arg_type = get_click_type(arg["type"])
        param = click.Argument([arg["name"]], type=arg_type)
        command.params.append(param)
    
    # Add options with types
    for opt in metadata.get("options", []):
        opt_type = get_click_type(opt["type"])
        param = click.Option(
            [f"--{opt['name']}"],
            type=opt_type,
            help=opt.get("description", ""),
            required=opt.get("required", False),
            default=opt.get("default", None)
        )
        command.params.append(param)
    
    def command_callback(*args, **kwargs):
        # Map positional args to their names from metadata
        arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
        if len(args) > len(arg_names):
            raise click.UsageError(f"Too many positional arguments: expected {len(arg_names)}, got {len(args)}")
        kwargs.update(dict(zip(arg_names, args)))
        # Execute the command function
        command_name = command_name.replace('-', '_')
        command_func = getattr(module, f"command_{command_name}")
        result = command_func(**kwargs)
        click.echo(json.dumps(result))
    
    command.callback = command_callback
    return command

# Initialize rich console
console = Console()
logger = logging.getLogger(__name__)

# Type mapping for Click parameter types
TYPE_MAP = {
    "string": click.STRING,
    "integer": click.INT,
    "float": click.FLOAT,
    "boolean": click.BOOL,
}

# Create an AliasedGroup class to support command aliases
class AliasedGroup(click.Group):
    def __init__(self, *args, **kwargs):
        self.section = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
    
    def get_command(self, ctx, cmd_name):
        # Try to get command by name
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        
        # Try to match aliases
        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")
    
    def format_commands(self, ctx, formatter):
        """Custom command formatter that displays section headers."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        # Group commands by section
        sections = {}
        for subcommand, cmd in commands:
            # Get section from command or use default section
            section = getattr(cmd, 'section', self.section or 'Commands')
            if section not in sections:
                sections[section] = []
            sections[section].append((subcommand, cmd))
        
        # Calculate limit for short help text
        limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)
        
        # Display each section with its commands
        for section, section_commands in sorted(sections.items()):
            rows = []
            for subcommand, cmd in sorted(section_commands, key=lambda x: x[0]):
                help_text = cmd.get_short_help_str(limit)
                rows.append((subcommand, help_text))
            
            if rows:
                with formatter.section(section):
                    formatter.write_dl(rows)


@click.group(cls=AliasedGroup, help="EVAI CLI - Command-line interface for EVAI")
@click.version_option(version=__version__, prog_name="evai")
def cli():
    """EVAI CLI - Command-line interface for EVAI."""
    pass


@cli.group(cls=AliasedGroup, section="Core Commands")
def tools():
    """Manage custom tools."""
    pass

# Tool functions have been moved to evai/cli/commands/tool.py

@cli.group(cls=AliasedGroup, section="User Commands")
def user():
    """User-defined commands."""
    pass

# Create command with section
def create_command_with_section(section="Core Commands"):
    """Decorator to set section on a command."""
    def decorator(command):
        command.section = section
        return command
    return decorator

@cli.command()
@click.option("--name", "-n", default="EVAI Tools", help="Name of the MCP server")
@create_command_with_section(section="Core Commands")
def server(name):
    """Start an MCP server exposing all tools."""
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
    """Import all commands from the commands submodule and add them to the appropriate groups."""
    from evai.cli import commands as commands_module
    
    # Define categories for commands
    CORE_COMMANDS = ["llm", "server", "deploy_artifact"]
    TOOL_MANAGEMENT = ["tools", "llmadd"]
    SAMPLE_COMMANDS = ["sample-add", "sample-mismatch", "sample-missing", "subtract"]
    USER_COMMANDS = ["user"]
    
    # Get the package path
    package_path = os.path.dirname(commands_module.__file__)
    
    # Set of commands already added to avoid duplicates
    added_commands = set()
    
    # Iterate through all modules in the commands package
    for _, module_name, _ in pkgutil.iter_modules([package_path]):
        # Skip command and cmdllmadd modules
        if module_name in ["commands", "cmdllmadd"]:
            continue
            
        # Import the module
        module = importlib.import_module(f"evai.cli.commands.{module_name}")
        
        # Find all Click commands in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a Click command
            if isinstance(attr, click.Command):
                # Skip if already added
                if attr.name in added_commands:
                    continue
                    
                # Categorize commands into sections
                if attr.name in CORE_COMMANDS:
                    # Core EVAI functionality
                    attr.section = "Core Commands"
                elif attr.name in SAMPLE_COMMANDS or attr.name.startswith("sample-"):
                    # Sample commands for testing
                    attr.section = "Sample Commands"
                elif module_name in TOOL_MANAGEMENT or attr.name.startswith("tool"):
                    # Tool management
                    attr.section = "Tool Management"
                else:
                    # Default for uncategorized commands
                    attr.section = "Other Commands"
                
                # Manually set certain command sections
                if attr.name == "deploy_artifact":
                    attr.section = "Core Commands"
                elif attr.name in ["sample-add", "sample-mismatch", "sample-missing", "subtract"]:
                    attr.section = "Sample Commands"

                # Determine which group to add the command to
                if module_name == "tools" or module_name == "llmadd":
                    # Add tool-related commands to the tools group
                    tools.add_command(attr)
                elif module_name == "llm" and attr_name == "llm":
                    # Add llm command directly to the main CLI group
                    cli.add_command(attr)
                    added_commands.add(attr.name)
                else:
                    # Standalone commands go to main CLI
                    cli.add_command(attr)
                    added_commands.add(attr.name)


# Import commands
import_commands()

# Load tools to the main CLI group with section
from evai.cli.user_commands import load_tools_to_main_group
load_tools_to_main_group(cli, section="Tool Commands")

# Organize command sections after all commands are loaded
for cmd_name in cli.commands:
    cmd = cli.commands[cmd_name]
    # Core and management commands
    if cmd_name in ["deploy_artifact", "server", "llm", "tools"]:
        cmd.section = "Core Commands"
    # All other commands are considered "User Commands" (including samples in dev)
    else:
        cmd.section = "User Commands"


def main():
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    return cli()


if __name__ == "__main__":
    sys.exit(main())