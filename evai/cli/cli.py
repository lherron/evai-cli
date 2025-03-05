"""Command-line interface for EVAI."""

import sys
import os
import json
import click
import importlib
import pkgutil
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

# Initialize rich console
console = Console()


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
    """Import all commands from the commands submodule and add them to the tools group."""
    from evai.cli import commands
    
    # Get the package path
    package_path = os.path.dirname(commands.__file__)
    
    # Iterate through all modules in the commands package
    for _, module_name, _ in pkgutil.iter_modules([package_path]):
        # Import the module
        module = importlib.import_module(f"evai.cli.commands.{module_name}")
        
        # Find all Click commands in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a Click command
            if isinstance(attr, click.Command):
                # Add the command to the tools group
                tools.add_command(attr)


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