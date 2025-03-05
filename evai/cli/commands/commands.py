"""Command management functions for EVAI CLI."""

import sys
import os
import json
import click
import yaml
import shutil
from pathlib import Path
from evai.command_storage import (
    get_command_dir,
    save_command_metadata,
    save_group_metadata,
    save_subcommand_metadata,
    load_command_metadata,
    load_group_metadata,
    load_subcommand_metadata,
    list_entities,
    parse_command_path,
    is_group,
    run_command,
    remove_entity
)
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

# Initialize rich console
console = Console()


@click.command()
@click.option("--type", type=click.Choice(["command", "group"]), required=True, help="Type of entity to create")
@click.option("--name", required=True, help="Name of the entity")
@click.option("--parent", default=None, help="Parent group for subcommands")
def add(type, name, parent):
    """Add a new command or group."""
    try:
        if parent:
            # This is a subcommand
            cmd_dir = get_command_dir([parent])
            if not (cmd_dir / "group.yaml").exists():
                click.echo(f"Parent group '{parent}' does not exist.", err=True)
                sys.exit(1)
            
            if type != "command":
                click.echo(f"Cannot create a {type} under a group. Only commands can be added as subcommands.", err=True)
                sys.exit(1)
            
            # Check if subcommand already exists
            sub_yaml = cmd_dir / f"{name}.yaml"
            if sub_yaml.exists():
                click.echo(f"Subcommand '{name}' already exists in group '{parent}'.", err=True)
                sys.exit(1)
            
            # Create subcommand
            with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_subcommand.yaml"), "r") as f:
                metadata_content = f.read().replace("{command_name}", name)
                metadata = yaml.safe_load(metadata_content)
            
            # Save metadata
            save_subcommand_metadata(cmd_dir, name, metadata)
            
            # Create implementation file
            with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_command.py"), "r") as f:
                with open(cmd_dir / f"{name}.py", "w") as py_file:
                    py_file.write(f.read())
            
            click.echo(f"Subcommand '{name}' created successfully under group '{parent}'.")
            click.echo(f"- Metadata: {sub_yaml}")
            click.echo(f"- Implementation: {cmd_dir / f'{name}.py'}")
            click.echo(f"\nTo edit this command, run: evai commands edit {parent} {name}")
        else:
            # This is a top-level entity (command or group)
            cmd_dir = get_command_dir([name])
            
            if cmd_dir.exists() and list(cmd_dir.iterdir()):
                click.echo(f"Entity '{name}' already exists.", err=True)
                sys.exit(1)
            
            if type == "group":
                # Create a group
                with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_group.yaml"), "r") as f:
                    metadata_content = f.read().replace("{group_name}", name)
                    metadata = yaml.safe_load(metadata_content)
                
                # Save metadata
                save_group_metadata(cmd_dir, metadata)
                
                click.echo(f"Group '{name}' created successfully.")
                click.echo(f"- Metadata: {cmd_dir / 'group.yaml'}")
                click.echo(f"\nTo add a subcommand, run: evai commands add --type command --parent {name} --name <subcommand>")
            else:
                # Create a command
                with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_command.yaml"), "r") as f:
                    metadata_content = f.read().replace("{command_name}", name)
                    metadata = yaml.safe_load(metadata_content)
                
                # Save metadata
                save_command_metadata(cmd_dir, metadata)
                
                # Create implementation file
                with open(os.path.join(os.path.dirname(__file__), "../../templates/sample_command.py"), "r") as f:
                    with open(cmd_dir / f"{name}.py", "w") as py_file:
                        py_file.write(f.read())
                
                click.echo(f"Command '{name}' created successfully.")
                click.echo(f"- Metadata: {cmd_dir / f'{name}.yaml'}")
                click.echo(f"- Implementation: {cmd_dir / f'{name}.py'}")
                click.echo(f"\nTo edit this command, run: evai commands edit {name}")
    except Exception as e:
        click.echo(f"Error creating {type}: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_path")
@click.option("--metadata/--no-metadata", default=True, help="Edit entity metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit entity implementation")
def edit(command_path, metadata, implementation):
    """Edit an existing command or group."""
    try:
        path_components = parse_command_path(command_path)
        
        if len(path_components) == 1:
            # This is a top-level entity (command or group)
            entity_name = path_components[0]
            entity_dir = get_command_dir([entity_name])
            
            if not entity_dir.exists():
                click.echo(f"Entity '{entity_name}' not found.", err=True)
                sys.exit(1)
            
            if is_group(entity_dir):
                # This is a group
                if metadata:
                    click.echo(f"Opening group.yaml for editing...")
                    
                    # Get path to metadata file
                    metadata_path = entity_dir / "group.yaml"
                    if not metadata_path.exists():
                        click.echo(f"Group metadata file not found: {metadata_path}", err=True)
                        sys.exit(1)
                    
                    # Open editor for user to edit the file
                    click.edit(filename=str(metadata_path))
                    
                    # Validate YAML after editing
                    try:
                        with open(metadata_path, "r") as f:
                            metadata_content = yaml.safe_load(f)
                        click.echo("Group metadata saved successfully.")
                    except Exception as e:
                        click.echo(f"Invalid YAML: {e}", err=True)
                        if click.confirm("Would you like to try again?"):
                            return edit.callback(command_path, True, False)
                        click.echo("Skipping metadata edit.")
                
                if implementation:
                    click.echo("Groups do not have implementation files.")
                
                click.echo(f"Group '{entity_name}' edited successfully.")
            else:
                # This is a command
                if metadata:
                    # Try both naming conventions
                    command_name = entity_name
                    metadata_path = entity_dir / f"{command_name}.yaml"
                    
                    if not metadata_path.exists():
                        # Try legacy path
                        metadata_path = entity_dir / "command.yaml"
                    
                    if not metadata_path.exists():
                        click.echo(f"Command metadata file not found: {metadata_path}", err=True)
                        sys.exit(1)
                    
                    click.echo(f"Opening {metadata_path.name} for editing...")
                    
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
                            return edit.callback(command_path, True, False)
                        click.echo("Skipping metadata edit.")
                
                if implementation:
                    # Try both naming conventions
                    command_name = entity_name
                    impl_path = entity_dir / f"{command_name}.py"
                    
                    if not impl_path.exists():
                        # Try legacy path
                        impl_path = entity_dir / "command.py"
                    
                    if not impl_path.exists():
                        click.echo(f"Implementation file not found: {impl_path}", err=True)
                        sys.exit(1)
                    
                    click.echo(f"Opening {impl_path.name} for editing...")
                    
                    # Open editor for user to edit the file
                    click.edit(filename=str(impl_path))
                    click.echo("Command implementation saved.")
                
                click.echo(f"Command '{entity_name}' edited successfully.")
        elif len(path_components) == 2:
            # This is a subcommand
            group_name = path_components[0]
            subcommand_name = path_components[1]
            
            group_dir = get_command_dir([group_name])
            
            if not group_dir.exists() or not is_group(group_dir):
                click.echo(f"Group '{group_name}' not found.", err=True)
                sys.exit(1)
            
            if metadata:
                click.echo(f"Opening {subcommand_name}.yaml for editing...")
                
                # Get path to metadata file
                metadata_path = group_dir / f"{subcommand_name}.yaml"
                if not metadata_path.exists():
                    click.echo(f"Subcommand metadata file not found: {metadata_path}", err=True)
                    sys.exit(1)
                
                # Open editor for user to edit the file
                click.edit(filename=str(metadata_path))
                
                # Validate YAML after editing
                try:
                    with open(metadata_path, "r") as f:
                        metadata_content = yaml.safe_load(f)
                    click.echo("Subcommand metadata saved successfully.")
                except Exception as e:
                    click.echo(f"Invalid YAML: {e}", err=True)
                    if click.confirm("Would you like to try again?"):
                        return edit.callback(command_path, True, False)
                    click.echo("Skipping metadata edit.")
            
            if implementation:
                click.echo(f"Opening {subcommand_name}.py for editing...")
                
                # Get path to implementation file
                impl_path = group_dir / f"{subcommand_name}.py"
                if not impl_path.exists():
                    click.echo(f"Implementation file not found: {impl_path}", err=True)
                    sys.exit(1)
                
                # Open editor for user to edit the file
                click.edit(filename=str(impl_path))
                click.echo("Subcommand implementation saved.")
            
            click.echo(f"Subcommand '{group_name} {subcommand_name}' edited successfully.")
        else:
            click.echo(f"Invalid command path: {command_path}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error editing entity: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_path")
@click.option("--metadata/--no-metadata", default=True, help="Edit entity metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit entity implementation")
def e(command_path, metadata, implementation):
    """Alias for 'edit' - Edit an existing command or group."""
    edit.callback(command_path, metadata, implementation)


@click.command()
def list():
    """List all available commands and groups."""
    try:
        # Get the list of entities
        entities = list_entities()
        
        if not entities:
            click.echo("No entities found.")
            return
        
        # Print the list of entities
        click.echo("Available entities:")
        
        # First print groups
        groups = [e for e in entities if e["type"] == "group"]
        for group in groups:
            click.echo(f"- {group['name']} (group): {group['description']}")
            
            # Print subcommands under this group
            subcommands = [e for e in entities if e["type"] == "command" and e.get("parent") == group["name"]]
            for cmd in subcommands:
                click.echo(f"  - {cmd['name']}: {cmd['description']}")
        
        # Then print top-level commands
        commands = [e for e in entities if e["type"] == "command" and "parent" not in e]
        if commands:
            if groups:
                click.echo("\nTop-level commands:")
            for cmd in commands:
                click.echo(f"- {cmd['name']}: {cmd['description']}")
        
    except Exception as e:
        click.echo(f"Error listing entities: {e}", err=True)
        sys.exit(1)


@click.command()
def ls():
    """Alias for 'list' - List all available commands and groups."""
    list.callback()


@click.command()
@click.argument("command_path")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def remove(command_path, force):
    """Remove a command, group, or subcommand."""
    try:
        path_components = parse_command_path(command_path)
        
        if len(path_components) == 1:
            # This is a top-level entity (command or group)
            entity_name = path_components[0]
            entity_dir = get_command_dir([entity_name])
            
            if not entity_dir.exists():
                click.echo(f"Entity '{entity_name}' not found.", err=True)
                sys.exit(1)
            
            if is_group(entity_dir):
                # This is a group
                # Check if the group has subcommands
                has_subcommands = False
                for item in entity_dir.iterdir():
                    if item.suffix == ".yaml" and item.name != "group.yaml":
                        has_subcommands = True
                        break
                
                if has_subcommands and not force:
                    click.echo(f"Group '{entity_name}' contains subcommands.")
                    if not click.confirm(f"Are you sure you want to remove group '{entity_name}' and all its subcommands?"):
                        click.echo("Operation cancelled.")
                        return
            else:
                # This is a command
                if not force and not click.confirm(f"Are you sure you want to remove command '{entity_name}'?"):
                    click.echo("Operation cancelled.")
                    return
            
            # Remove the entity
            remove_entity(command_path)
            
            if is_group(entity_dir):
                click.echo(f"Group '{entity_name}' and all its subcommands removed successfully.")
            else:
                click.echo(f"Command '{entity_name}' removed successfully.")
        elif len(path_components) == 2:
            # This is a subcommand
            group_name = path_components[0]
            subcommand_name = path_components[1]
            
            group_dir = get_command_dir([group_name])
            
            if not group_dir.exists() or not is_group(group_dir):
                click.echo(f"Group '{group_name}' not found.", err=True)
                sys.exit(1)
            
            subcommand_yaml = group_dir / f"{subcommand_name}.yaml"
            if not subcommand_yaml.exists():
                click.echo(f"Subcommand '{group_name} {subcommand_name}' not found.", err=True)
                sys.exit(1)
            
            if not force and not click.confirm(f"Are you sure you want to remove subcommand '{group_name} {subcommand_name}'?"):
                click.echo("Operation cancelled.")
                return
            
            # Remove the subcommand
            remove_entity(command_path)
            
            click.echo(f"Subcommand '{group_name} {subcommand_name}' removed successfully.")
        else:
            click.echo(f"Invalid command path: {command_path}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error removing entity: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_path")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def rm(command_path, force):
    """Alias for 'remove' - Remove a command, group, or subcommand."""
    remove.callback(command_path, force)


@click.command()
@click.argument("command_path")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Command parameters in the format key=value")
def run(command_path, args, param):
    """Run a command with the given arguments.
    
    Arguments can be provided as positional arguments after the command path,
    or as key=value pairs with the --param/-p option.
    
    Example:
        evai commands run greet John
        evai commands run projects add --param name=MyProject
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
        
        # Run the command with positional args if provided, otherwise use kwargs
        if args:
            result = run_command(command_path, *args, **kwargs)
        else:
            result = run_command(command_path, **kwargs)
        
        # Print the result
        if isinstance(result, dict):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error running command: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("command_path")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Command parameters in the format key=value")
def r(command_path, args, param):
    """Alias for 'run' - Run a command with the given arguments."""
    run.callback(command_path, args, param)