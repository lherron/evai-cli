"""Command management functions for EVAI CLI."""

import sys
import os
import json
import click
import yaml
from evai.command_storage import (
    get_command_dir,
    save_command_metadata,
    load_command_metadata,
    list_commands,
    import_command_module,
    run_command
)
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

# Initialize rich console
console = Console()


@click.command()
@click.argument("command_name")
def add(command_name):
    """Add a new custom command."""
    try:
        # Get the command directory
        cmd_dir = get_command_dir(command_name)
        
        if list(cmd_dir.iterdir()):  # Check if directory is non-empty
            click.echo(f"Command '{command_name}' already exists.", err=True)
            sys.exit(1)
            
        # Load default metadata template
        with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_command.yaml"), "r") as f:
            metadata_content = f.read().replace("{command_name}", command_name)
            default_metadata = yaml.safe_load(metadata_content)
        
        # Save metadata
        save_command_metadata(cmd_dir, default_metadata)
        
        # Create default command.py
        with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_command.py"), "r") as f:
            with open(cmd_dir / "command.py", "w") as py_file:
                py_file.write(f.read())
        
        click.echo(f"Command '{command_name}' created successfully.")
        click.echo(f"- Metadata: {cmd_dir / 'command.yaml'}")
        click.echo(f"- Implementation: {cmd_dir / 'command.py'}")
        click.echo(f"\nTo edit this command, run: evai commands edit {command_name}")
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_name")
def new(command_name):
    """Alias for 'add' - Add a new custom command."""
    add.callback(command_name)


@click.command()
@click.argument("command_name")
@click.option("--metadata/--no-metadata", default=True, help="Edit command metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit command implementation")
def edit(command_name, metadata, implementation):
    """Edit an existing command."""
    try:
        # Get the command directory
        cmd_dir = get_command_dir(command_name)
        
        # Edit metadata if requested
        if metadata:
            click.echo(f"Opening command.yaml for editing...")
            
            # Get path to metadata file
            metadata_path = cmd_dir / "command.yaml"
            if not metadata_path.exists():
                click.echo(f"Metadata file not found: {metadata_path}", err=True)
                sys.exit(1)
                
            # Open editor for user to edit the file
            click.edit(filename=str(metadata_path))
            
            # Validate YAML after editing
            try:
                with open(metadata_path, "r") as f:
                    metadata_content = yaml.safe_load(f)
                click.echo("Command metadata saved successfully.")
            except Exception as e:
                click.echo(f"Invalid YAML: {e}", err=True)
                if click.confirm("Would you like to try again?"):
                    return edit.callback(command_name, True, False)
                click.echo("Skipping metadata edit.")
        
        # Edit implementation if requested
        if implementation:
            click.echo(f"Opening command.py for editing...")
            
            # Get path to implementation file
            impl_path = cmd_dir / "command.py"
            if not impl_path.exists():
                click.echo(f"Implementation file not found: {impl_path}", err=True)
                sys.exit(1)
                
            # Open editor for user to edit the file
            click.edit(filename=str(impl_path))
            click.echo("Command implementation saved.")
        
        click.echo(f"Command '{command_name}' edited successfully.")
        
    except Exception as e:
        click.echo(f"Error editing command: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_name")
@click.option("--metadata/--no-metadata", default=True, help="Edit command metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit command implementation")
def e(command_name, metadata, implementation):
    """Alias for 'edit' - Edit an existing command."""
    edit.callback(command_name, metadata, implementation)


@click.command()
def list():
    """List all available commands."""
    try:
        # Get the list of commands
        commands = list_commands()
        
        if not commands:
            click.echo("No commands found.")
            return
        
        # Print the list of commands
        click.echo("Available commands:")
        for cmd in commands:
            click.echo(f"- {cmd['name']}: {cmd['description']}")
        
    except Exception as e:
        click.echo(f"Error listing commands: {e}", err=True)
        sys.exit(1)


@click.command()
def ls():
    """Alias for 'list' - List all available commands."""
    list.callback()


@click.command()
@click.argument("command_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def remove(command_name, force):
    """Remove a custom command."""
    try:
        # Get the command directory
        cmd_dir = get_command_dir(command_name)
        
        if not cmd_dir.exists():
            click.echo(f"Command '{command_name}' not found.", err=True)
            sys.exit(1)
            
        # Confirm removal unless force flag is set
        if not force and not click.confirm(f"Are you sure you want to remove command '{command_name}'?"):
            click.echo("Operation cancelled.")
            return
        
        # Remove the command directory
        import shutil
        shutil.rmtree(cmd_dir)
        
        click.echo(f"Command '{command_name}' removed successfully.")
        
    except Exception as e:
        click.echo(f"Error removing command: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def rm(command_name, force):
    """Alias for 'remove' - Remove a custom command."""
    remove.callback(command_name, force)


@click.command()
@click.argument("command_name")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Command parameters in the format key=value")
def run(command_name, args, param):
    """Run a command with the given arguments.
    
    Arguments can be provided as positional arguments after the command name,
    or as key=value pairs with the --param/-p option.
    
    Example:
        evai commands run greet John
        evai commands run greet --param name=John --param greeting=Hello
    """
    try:
        # Parse parameters from --param options
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
        cmd_dir = get_command_dir(command_name)
        metadata = load_command_metadata(cmd_dir)
        
        # If using --param options, check required options
        if not args and "options" in metadata:
            for opt_def in metadata.get("options", []):
                opt_name = opt_def.get("name")
                if opt_name and opt_def.get("required", False) and opt_name not in kwargs:
                    # If option has a default value, use it
                    if "default" in opt_def and opt_def["default"] is not None:
                        kwargs[opt_name] = opt_def["default"]
                    else:
                        click.echo(f"Missing required option: {opt_name}", err=True)
                        sys.exit(1)
        
        # Run the command with positional args if provided, otherwise use kwargs
        if args:
            result = run_command(command_name, *args, **kwargs)
        else:
            result = run_command(command_name, **kwargs)
        
        # Print the result
        if isinstance(result, dict):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error running command: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_name")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Command parameters in the format key=value")
def r(command_name, args, param):
    """Alias for 'run' - Run a command with the given arguments."""
    run.callback(command_name, args, param)