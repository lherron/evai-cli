"""Migration script to convert commands to tools."""

import os
import sys
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

from evai.command_storage import (
    list_entities, 
    load_command_metadata,
    get_command_dir,
    is_group,
    COMMANDS_DIR
)
from evai.tool_storage import (
    add_tool,
    get_tool_dir,
    TOOLS_BASE_DIR
)

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def migrate_command_to_tool(command_path: str) -> bool:
    """
    Migrate a command to a tool.
    
    Args:
        command_path: Path to the command (e.g., "add" or "math add")
        
    Returns:
        True if the migration was successful, False otherwise
    """
    try:
        # Parse the command path
        path_components = command_path.split()
        
        # Determine tool path - replace spaces with /
        tool_path = command_path.replace(" ", "/")
        
        # Get command directory
        if len(path_components) == 1:
            # Top-level command
            cmd_dir = get_command_dir([path_components[0]])
            is_subcommand = False
        elif len(path_components) == 2:
            # Subcommand
            cmd_dir = get_command_dir([path_components[0]])
            is_subcommand = True
        else:
            logger.error(f"Invalid command path: {command_path}")
            return False
        
        # Check if this is a group
        if is_group(cmd_dir) and not is_subcommand:
            # This is a group, create a tool group
            with open(cmd_dir / "group.yaml", "r") as f:
                group_metadata = yaml.safe_load(f)
                
            # Create the tool group with minimal metadata
            tool_metadata = {
                "name": path_components[0],
                "description": group_metadata.get("description", f"Group for {path_components[0]} tools"),
                "type": "group"
            }
            
            # Add the tool group
            parent_group_dir = get_tool_dir(path_components[0])
            with open(os.path.join(parent_group_dir, "group.yaml"), "w") as f:
                yaml.dump(tool_metadata, f, default_flow_style=False)
                
            logger.info(f"Created tool group: {path_components[0]}")
            
            # Migrate all subcommands in this group
            for item in cmd_dir.iterdir():
                if item.suffix == ".yaml" and item.name != "group.yaml":
                    subcommand_name = item.stem
                    migrate_command_to_tool(f"{path_components[0]} {subcommand_name}")
                    
            return True
        else:
            # This is a command or subcommand
            # Load command metadata
            if is_subcommand:
                yaml_path = cmd_dir / f"{path_components[1]}.yaml"
                py_path = cmd_dir / f"{path_components[1]}.py"
            else:
                yaml_path = cmd_dir / f"{path_components[0]}.yaml"
                if not yaml_path.exists():
                    yaml_path = cmd_dir / "command.yaml"
                    
                py_path = cmd_dir / f"{path_components[0]}.py"
                if not py_path.exists():
                    py_path = cmd_dir / "command.py"
            
            if not yaml_path.exists() or not py_path.exists():
                logger.error(f"Command files not found for: {command_path}")
                return False
                
            # Load metadata and implementation
            with open(yaml_path, "r") as f:
                command_metadata = yaml.safe_load(f)
                
            with open(py_path, "r") as f:
                command_impl = f.read()
                
            # Convert metadata to tool format
            tool_metadata = {
                "name": path_components[-1],
                "description": command_metadata.get("description", ""),
                "arguments": command_metadata.get("arguments", []),
                "options": command_metadata.get("options", []),
                "params": [],  # Empty params list for now
                "hidden": command_metadata.get("hidden", False),
                "disabled": command_metadata.get("disabled", False),
                "mcp_integration": {
                    "enabled": command_metadata.get("mcp_integration", {}).get("enabled", True),
                    "metadata": command_metadata.get("mcp_integration", {}).get("metadata", {
                        "endpoint": "",
                        "method": "POST",
                        "authentication_required": False
                    })
                },
                "llm_interaction": command_metadata.get("llm_interaction", {
                    "enabled": False,
                    "auto_apply": True,
                    "max_llm_turns": 15
                })
            }
            
            # Convert implementation
            # Replace command_X or command_group_X with tool_X
            if is_subcommand:
                command_func_prefix = f"command_{path_components[0]}_{path_components[1]}"
                tool_func_prefix = f"tool_{path_components[1]}"
            else:
                command_func_prefix = f"command_{path_components[0]}"
                tool_func_prefix = f"tool_{path_components[0]}"
                
            tool_impl = command_impl.replace(command_func_prefix, tool_func_prefix)
            
            # Add the tool
            add_tool(tool_path, tool_metadata, tool_impl)
            
            logger.info(f"Migrated command '{command_path}' to tool '{tool_path}'")
            return True
            
    except Exception as e:
        logger.error(f"Error migrating command '{command_path}' to tool: {e}")
        return False


def migrate_all_commands() -> Dict[str, Any]:
    """
    Migrate all commands to tools.
    
    Returns:
        A dictionary with migration stats
    """
    logger.info("Starting migration of commands to tools")
    
    # Create stats dictionary
    stats = {
        "total": 0,
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "groups": 0
    }
    
    # Get all commands and groups
    entities = list_entities()
    stats["total"] = len(entities)
    
    # First migrate groups
    groups = [e for e in entities if e["type"] == "group"]
    for group in groups:
        stats["groups"] += 1
        group_name = group["name"]
        if migrate_command_to_tool(group_name):
            stats["migrated"] += 1
        else:
            stats["failed"] += 1
    
    # Then migrate top-level commands (not in groups)
    commands = [e for e in entities if e["type"] == "command" and "parent" not in e]
    for command in commands:
        command_name = command["name"]
        if migrate_command_to_tool(command_name):
            stats["migrated"] += 1
        else:
            stats["failed"] += 1
    
    logger.info(f"Migration completed. Total: {stats['total']}, "
                f"Migrated: {stats['migrated']}, Failed: {stats['failed']}")
    
    return stats


def main():
    """Run the migration script."""
    try:
        # Check if commands directory exists
        if not COMMANDS_DIR.exists():
            logger.info("No commands directory found. Nothing to migrate.")
            return
            
        # Check if tools directory exists, create if not
        if not os.path.exists(TOOLS_BASE_DIR):
            os.makedirs(TOOLS_BASE_DIR, exist_ok=True)
            
        # Run migration
        stats = migrate_all_commands()
        
        # Print stats
        print("Migration completed:")
        print(f"  Total entities: {stats['total']}")
        print(f"  Groups: {stats['groups']}")
        print(f"  Successfully migrated: {stats['migrated']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        print(f"Error during migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()