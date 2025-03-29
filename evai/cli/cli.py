"""Command-line interface for EVAI."""

import sys
import os
import json
import click
import importlib
import pkgutil
from typing import Any, Dict, List, Optional, Tuple
from evai import __version__
from rich.console import Console
import logging

def get_click_type(type_str: str) -> click.ParamType:
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

def convert_value(value: str, type_str: str) -> Any:
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

def create_command(command_name: str, metadata: Dict[str, Any], module: Any) -> click.Command:
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
        option_param = click.Option(
            [f"--{opt['name']}"],
            type=opt_type,
            help=opt.get("description", ""),
            required=opt.get("required", False),
            default=opt.get("default", None)
        )
        command.params.append(option_param)
    
    def command_callback(*args: Any, **kwargs: Any) -> None:
        # Map positional args to their names from metadata
        arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
        if len(args) > len(arg_names):
            raise click.UsageError(f"Too many positional arguments: expected {len(arg_names)}, got {len(args)}")
        kwargs.update(dict(zip(arg_names, args)))
        # Execute the command function
        cmd_name = command_name.replace('-', '_')
        command_func = getattr(module, f"command_{cmd_name}")
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
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.section: Optional[str] = kwargs.pop('section', None)
        super().__init__(*args, **kwargs)
    
    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
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
        if False:  # type: ignore
            return None
    
    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Custom command formatter that displays section headers."""
        commands: List[Tuple[str, click.Command]] = []
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
        sections: Dict[str, List[Tuple[str, click.Command]]] = {}
        for subcommand, cmd in commands:
            # Get section from command or use default section
            section_name = getattr(cmd, 'section', self.section or 'Commands')
            if section_name is None:
                section_name = 'Commands'  # Default if none specified
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append((subcommand, cmd))
        
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
def cli() -> None:
    """EVAI CLI - Command-line interface for EVAI."""
    pass


@cli.group(cls=AliasedGroup, section="Core Commands", invoke_without_command=True)
@click.pass_context
def tools(ctx: click.Context) -> None:
    """Manage custom tools."""
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, show both help and the list of tools
        from evai.cli.commands.tools import list as list_cmd
        
        # Print the help text first
        click.echo(ctx.get_help())
        click.echo("\n")  # Add some spacing
        
        # Then show the list of tools
        if hasattr(list_cmd, "callback") and callable(list_cmd.callback):
            list_cmd.callback()
        click.echo("\n")  # Add some spacing

# Create command with section
def create_command_with_section(section: str = "Core Commands") -> Any:
    """Decorator to set section on a command."""
    def decorator(command: click.Command) -> click.Command:
        # Use setattr to avoid mypy errors about missing attribute
        setattr(command, "section", section)
        return command
    return decorator

# Automatically add all commands from the commands submodule
def import_commands() -> None:
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
                    setattr(attr, "section", "Core Commands")
                elif attr.name in SAMPLE_COMMANDS or (hasattr(attr, 'name') and isinstance(attr.name, str) and attr.name.startswith("sample-")):
                    # Sample commands for testing
                    setattr(attr, "section", "Sample Commands")
                elif module_name in TOOL_MANAGEMENT or (hasattr(attr, 'name') and isinstance(attr.name, str) and attr.name.startswith("tool")):
                    # Tool management
                    setattr(attr, "section", "Tool Management")
                else:
                    # Default for uncategorized commands
                    setattr(attr, "section", "Other Commands")
                
                # Manually set certain command sections
                if attr.name == "deploy_artifact":
                    setattr(attr, "section", "Core Commands")
                elif attr.name in ["sample-add", "sample-mismatch", "sample-missing", "subtract"]:
                    setattr(attr, "section", "Sample Commands")

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
    if cmd_name in ["server", "llm", "tools"]:
        # Use setattr to avoid mypy errors with the section attribute
        setattr(cmd, "section", "Core Commands")  
    # All other commands are considered "User Commands" (including samples in dev)
    else:
        # Use setattr to avoid mypy errors with the section attribute
        setattr(cmd, "section", "User Commands")


def main() -> int:
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    result = cli()
    # Ensure we return an integer exit code
    return 0 if result is None else int(result)


if __name__ == "__main__":
    sys.exit(main())