# evai/cli/user_commands.py
import click
import importlib.util
import logging
import json
from evai.command_storage import (
    list_entities,
    get_command_dir,
    load_command_metadata,
    load_subcommand_metadata
)

logger = logging.getLogger(__name__)

def get_click_type(type_str):
    """Map metadata type strings to Click parameter types."""
    type_map = {
        "string": str,
        "integer": int,
        "float": float,
        "boolean": bool
    }
    if type_str not in type_map:
        raise ValueError(f"Unsupported type: {type_str}")
    return type_map[type_str]

def load_user_commands_to_main_group(main_group):
    """Load user-created commands and groups into the main Click group.
    
    This function is used to make user-created commands available as first-class
    commands in the CLI, alongside the built-in commands. It adds user commands
    directly to the main CLI group (evai), so they can be called directly as
    'evai <command>' instead of just 'evai commands run <command>'.
    
    Built-in commands have precedence over user-created commands with the same name.
    """
    entities = list_entities()
    
    # Handle groups and their subcommands
    for entity in entities:
        if entity["type"] == "group":
            group_name = entity["name"]
            if group_name in main_group.commands:
                logger.warning(f"Skipping group '{group_name}' because a command with that name already exists.")
                continue
            
            # Create a new Click group
            group_dir = get_command_dir([group_name])
            group_metadata = load_group_metadata(group_dir)
            group = click.Group(name=group_name, help=group_metadata.get("description", ""))
            main_group.add_command(group)
            
            # Add subcommands
            subcommands = [e for e in entities if e["type"] == "command" and e.get("parent") == group_name]
            for subcmd in subcommands:
                subcmd_name = subcmd["name"]
                if subcmd_name in group.commands:
                    logger.warning(f"Skipping subcommand '{group_name} {subcmd_name}' because a command with that name already exists in the group.")
                    continue
                
                try:
                    metadata = load_subcommand_metadata(group_dir, subcmd_name)
                    if metadata.get("disabled", False):
                        continue
                    
                    # Create a command using the existing create_user_command function
                    from evai.cli.cli import create_user_command
                    command = create_user_command(metadata, group_dir, subcmd_name)
                    group.add_command(command)
                except Exception as e:
                    logger.error(f"Error loading subcommand '{group_name} {subcmd_name}': {e}")
                    continue
    
    # Handle individual commands
    for entity in entities:
        if entity["type"] == "command" and "parent" not in entity:
            cmd_name = entity["name"]
            if cmd_name in main_group.commands:
                logger.warning(f"Skipping command '{cmd_name}' because a command with that name already exists.")
                continue
            
            try:
                cmd_dir = get_command_dir([cmd_name])
                metadata = load_command_metadata(cmd_dir)
                if metadata.get("disabled", False):
                    continue
                
                # Create a command using the existing create_user_command function
                from evai.cli.cli import create_user_command
                command = create_user_command(metadata, cmd_dir, cmd_name)
                main_group.add_command(command)
            except Exception as e:
                logger.error(f"Error loading command '{cmd_name}': {e}")
                continue