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
from evai.command_storage import (
    get_command_dir,
    save_command_metadata,
    list_entities,
    import_command_module,
    import_subcommand_module,
    is_group,
    load_command_metadata,
    load_group_metadata,
    load_subcommand_metadata
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


@click.group(help="EVAI CLI - Command-line interface for EVAI")
@click.version_option(version=__version__, prog_name="evai")
def cli():
    """EVAI CLI - Command-line interface for EVAI."""
    pass


@cli.group(cls=AliasedGroup)
def tools():
    """Manage custom tools."""
    pass

# Tool functions have been moved to evai/cli/commands/tool.py

@cli.group(cls=AliasedGroup)
def commands():
    """Manage user-defined commands."""
    pass

@cli.group(cls=AliasedGroup)
def user():
    """User-defined commands."""
    pass

def create_user_command(metadata: dict, cmd_dir: Path, command_name: str):
    """Create a Click command from command metadata."""
    description = metadata.get("description", "")
    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]

    def callback(*args, **kwargs):
        # Check if this is a subcommand (has a parent directory with group.yaml)
        if is_group(cmd_dir):
            # This is a subcommand
            group_name = cmd_dir.name
            module = import_subcommand_module(group_name, command_name)
        else:
            # This is a top-level command
            module = import_command_module(command_name)
            
        run_func = getattr(module, "run")
        params = dict(zip(arg_names, args))
        params.update(kwargs)
        result = run_func(**params)
        click.echo(json.dumps(result, indent=2))
        return result

    command = click.command(name=command_name, help=description)(callback)

    # Add arguments
    for arg in metadata.get("arguments", []):
        command = click.argument(
            arg["name"],
            type=TYPE_MAP.get(arg.get("type", "string"), click.STRING)
        )(command)

    # Add options
    for opt in metadata.get("options", []):
        command = click.option(
            f"--{opt['name']}",
            type=TYPE_MAP.get(opt.get("type", "string"), click.STRING),
            help=opt.get("description", ""),
            required=opt.get("required", False),
            default=opt.get("default", None)
        )(command)

    return command

def load_user_commands():
    """Load and register user-defined commands from ~/.evai/commands."""
    commands_dir = Path(os.path.expanduser("~/.evai/commands"))
    
    if not commands_dir.exists():
        return
    
    for item in commands_dir.iterdir():
        if item.is_dir():
            group_yaml = item / "group.yaml"
            if group_yaml.exists():
                # This is a group
                with open(group_yaml, "r") as f:
                    metadata = yaml.safe_load(f)
                
                group_name = metadata["name"]
                group = click.Group(name=group_name, help=metadata.get("description", ""))
                user.add_command(group)
                
                # Load subcommands
                for sub_file in item.iterdir():
                    if sub_file.suffix == ".yaml" and sub_file.name != "group.yaml":
                        sub_name = sub_file.stem
                        with open(sub_file, "r") as f:
                            sub_metadata = yaml.safe_load(f)
                        
                        try:
                            command = create_user_command(sub_metadata, item, sub_name)
                            group.add_command(command)
                        except Exception as e:
                            logger.warning(f"Failed to load subcommand {group_name} {sub_name}: {e}")
            else:
                # This is a top-level command
                # Try both naming conventions
                command_name = item.name
                command_yaml = item / f"{command_name}.yaml"
                
                if not command_yaml.exists():
                    # Try legacy path
                    command_yaml = item / "command.yaml"
                    
                if command_yaml.exists():
                    with open(command_yaml, "r") as f:
                        metadata = yaml.safe_load(f)
                    
                    try:
                        command = create_user_command(metadata, item, metadata["name"])
                        user.add_command(command)
                    except Exception as e:
                        logger.warning(f"Failed to load command {metadata['name']}: {e}")

@cli.command()
@click.option("--name", "-n", default="EVAI Tools", help="Name of the MCP server")
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
    
    # Get the package path
    package_path = os.path.dirname(commands_module.__file__)
    
    # Iterate through all modules in the commands package
    for _, module_name, _ in pkgutil.iter_modules([package_path]):
        # Import the module
        module = importlib.import_module(f"evai.cli.commands.{module_name}")
        
        # Find all Click commands in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a Click command
            if isinstance(attr, click.Command):
                # Determine which group to add the command to
                if module_name == "tools" or module_name == "llmadd":
                    # Add tool-related commands to the tools group
                    tools.add_command(attr)
                elif module_name == "commands" or module_name == "cmdllmadd":
                    # Add command-related commands to the commands group
                    commands.add_command(attr)
                else:
                    # Default to tools group for anything else
                    tools.add_command(attr)


# Import commands
import_commands()

# Load user-defined commands
load_user_commands()


def main():
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    return cli()


if __name__ == "__main__":
    sys.exit(main()) 