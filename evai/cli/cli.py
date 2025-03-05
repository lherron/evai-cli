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
        
        # Get command function 
        if is_group(cmd_dir):
            # This is a subcommand - use command_<group>_<command> naming
            group_name = cmd_dir.name
            func_name = f"command_{group_name}_{command_name}"
        else:
            # This is a top-level command - use command_<command> naming
            func_name = f"command_{command_name}"
            
        run_func = getattr(module, func_name)
            
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
    """Load and register user-defined commands from ~/.evai/commands with type conversion."""
    user_commands_dir = Path.home() / ".evai" / "commands"
    
    if not user_commands_dir.exists():
        return
        
    for entity_dir in user_commands_dir.iterdir():
        if entity_dir.is_dir():
            group_yaml = entity_dir / "group.yaml"
            if group_yaml.exists():
                # Load group
                with open(group_yaml, "r") as f:
                    group_metadata = yaml.safe_load(f)
                group_name = group_metadata["name"]
                group = click.Group(name=group_name, help=group_metadata.get("description", ""))
                
                # Add subcommands to the group
                for subcmd_yaml in entity_dir.glob("*.yaml"):
                    if subcmd_yaml.name != "group.yaml":
                        subcmd_name = subcmd_yaml.stem
                        with open(subcmd_yaml, "r") as f:
                            subcmd_metadata = yaml.safe_load(f)
                        impl_path = entity_dir / f"{subcmd_name}.py"
                        if impl_path.exists():
                            try:
                                spec = importlib.util.spec_from_file_location(subcmd_name, impl_path)
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                subcmd = create_command(subcmd_name, subcmd_metadata, module)
                                group.add_command(subcmd)
                            except Exception as e:
                                logger.warning(f"Failed to load subcommand {group_name} {subcmd_name}: {e}")
                user.add_command(group)
            else:
                # Load top-level command
                metadata_path = entity_dir / f"{entity_dir.name}.yaml"
                if not metadata_path.exists():
                    # Try legacy path
                    metadata_path = entity_dir / "command.yaml"
                    
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = yaml.safe_load(f)
                    command_name = metadata["name"]
                    impl_path = entity_dir / f"{entity_dir.name}.py"
                    if not impl_path.exists():
                        # Try legacy path
                        impl_path = entity_dir / "command.py"
                        
                    if impl_path.exists():
                        try:
                            spec = importlib.util.spec_from_file_location(command_name, impl_path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            command = create_command(command_name, metadata, module)
                            user.add_command(command)
                        except Exception as e:
                            logger.warning(f"Failed to load command {command_name}: {e}")

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

# Load user-defined commands to the user group
load_user_commands()

# Also load user-defined commands to the main CLI group
from evai.cli.user_commands import load_user_commands_to_main_group
load_user_commands_to_main_group(cli)


def main():
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    return cli()


if __name__ == "__main__":
    sys.exit(main())