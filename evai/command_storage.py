"""Command storage utilities for EVAI CLI."""

import os
import yaml
import shutil
from pathlib import Path
import importlib.util
import inspect
import logging

logger = logging.getLogger(__name__)

COMMANDS_DIR = Path.home() / ".evai" / "commands"

def parse_command_path(command_path: str) -> list[str]:
    """
    Parse a command path into components.
    
    For example, "projects add" becomes ["projects", "add"].
    """
    return command_path.split()

def get_command_dir(path_components: list[str]) -> Path:
    """
    Get the directory path for a command or group and create it if it doesn't exist.
    
    Args:
        path_components: List of path components (e.g., ["projects"] or ["projects", "add"])
        
    Returns:
        Path to the command or group directory
    """
    if not path_components:
        return COMMANDS_DIR
    
    command_dir = COMMANDS_DIR / path_components[0]
    command_dir.mkdir(parents=True, exist_ok=True)
    return command_dir

def is_group(directory: Path) -> bool:
    """
    Check if a directory is a command group.
    
    Args:
        directory: Path to the directory
        
    Returns:
        True if the directory contains a group.yaml file, False otherwise
    """
    return (directory / "group.yaml").exists()

def load_command_metadata(path: Path) -> dict:
    """Load command metadata from <command_name>.yaml or command.yaml (legacy)."""
    # Get the command name from the directory name
    command_name = path.name
    yaml_path = path / f"{command_name}.yaml"
    
    if not yaml_path.exists():
        # Try legacy path for backward compatibility
        legacy_path = path / "command.yaml"
        if legacy_path.exists():
            yaml_path = legacy_path
        else:
            raise FileNotFoundError(f"Command metadata file not found: {yaml_path}")
            
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def load_group_metadata(path: Path) -> dict:
    """Load group metadata from group.yaml."""
    yaml_path = path / "group.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Group metadata file not found: {yaml_path}")
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def load_subcommand_metadata(group_dir: Path, subcommand_name: str) -> dict:
    """Load subcommand metadata from <subcommand_name>.yaml."""
    yaml_path = group_dir / f"{subcommand_name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Subcommand metadata file not found: {yaml_path}")
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def save_command_metadata(path: Path, data: dict) -> None:
    """Save command metadata to <command_name>.yaml."""
    # Get the command name from the metadata
    command_name = data.get("name", path.name)
    yaml_path = path / f"{command_name}.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def save_group_metadata(path: Path, data: dict) -> None:
    """Save group metadata to group.yaml."""
    yaml_path = path / "group.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def save_subcommand_metadata(group_dir: Path, subcommand_name: str, data: dict) -> None:
    """Save subcommand metadata to <subcommand_name>.yaml."""
    yaml_path = group_dir / f"{subcommand_name}.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def list_entities() -> list[dict]:
    """
    List all available commands and groups.
    
    Returns:
        A list of dictionaries containing entity information
    """
    if not COMMANDS_DIR.exists():
        return []
    
    entities = []
    
    for item in COMMANDS_DIR.iterdir():
        if not item.is_dir():
            continue
            
        # Check if this is a group
        group_yaml = item / "group.yaml"
        if group_yaml.exists():
            # This is a group
            with open(group_yaml, "r") as f:
                metadata = yaml.safe_load(f)
                
            group_name = metadata["name"]
            entities.append({
                "type": "group",
                "name": group_name,
                "description": metadata.get("description", ""),
                "path": str(item)
            })
            
            # List all subcommands in this group
            for sub_file in item.iterdir():
                if sub_file.suffix == ".yaml" and sub_file.name != "group.yaml":
                    sub_name = sub_file.stem
                    with open(sub_file, "r") as f:
                        sub_metadata = yaml.safe_load(f)
                    
                    entities.append({
                        "type": "command",
                        "name": f"{group_name} {sub_name}",
                        "description": sub_metadata.get("description", ""),
                        "parent": group_name,
                        "path": str(item)
                    })
        else:
            # Check if this is a top-level command
            # Try both naming conventions
            command_name = item.name
            command_yaml = item / f"{command_name}.yaml"
            
            if not command_yaml.exists():
                # Try legacy path
                command_yaml = item / "command.yaml"
                
            if command_yaml.exists():
                with open(command_yaml, "r") as f:
                    metadata = yaml.safe_load(f)
                
                entities.append({
                    "type": "command",
                    "name": metadata["name"],
                    "description": metadata.get("description", ""),
                    "path": str(item)
                })
    
    return entities

def list_commands() -> list[dict]:
    """List all available commands (for backwards compatibility)."""
    entities = list_entities()
    commands = []
    
    for entity in entities:
        if entity["type"] == "command" and not entity.get("disabled", False):
            commands.append({
                "name": entity["name"],
                "description": entity["description"],
                "path": Path(entity["path"])
            })
    
    return commands

def import_command_module(command_name: str):
    """Dynamically import a command module (for top-level commands)."""
    cmd_dir = get_command_dir([command_name])
    py_path = cmd_dir / f"{command_name}.py"
    if not py_path.exists():
        # Try legacy path for backward compatibility
        legacy_path = cmd_dir / "command.py"
        if legacy_path.exists():
            py_path = legacy_path
        else:
            raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    spec = importlib.util.spec_from_file_location(f"evai.commands.{command_name}", py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def import_module_from_path(module_name: str, file_path: Path):
    """
    Dynamically import a module from a file path.
    
    Args:
        module_name: Name to give the imported module
        file_path: Path to the module file
        
    Returns:
        The imported module
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Module file not found: {file_path}")
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def import_subcommand_module(group_name: str, subcommand_name: str):
    """
    Dynamically import a subcommand module.
    
    Args:
        group_name: Name of the group
        subcommand_name: Name of the subcommand
        
    Returns:
        The imported module
    """
    group_dir = get_command_dir([group_name])
    py_path = group_dir / f"{subcommand_name}.py"
    
    return import_module_from_path(f"evai.commands.{group_name}.{subcommand_name}", py_path)

def run_command(command_path: str, *args, **kwargs):
    """
    Run a command with the given arguments.
    
    Args:
        command_path: Path to the command (e.g., "projects add")
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        The result of the command
    """
    try:
        path_components = parse_command_path(command_path)
        
        if len(path_components) == 1:
            # This is a top-level command
            command_name = path_components[0]
            module = import_command_module(command_name)
            
            # Check if module has the command_* function first
            function_name = f"command_{command_name}"
            if hasattr(module, function_name):
                command_func = getattr(module, function_name)
                
                # Convert positional args to kwargs based on metadata if needed
                if args and len(args) > 0:
                    cmd_dir = get_command_dir([command_name])
                    metadata = load_command_metadata(cmd_dir)
                    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
                    
                    # Map positional args to named args
                    if len(args) > len(arg_names):
                        raise ValueError(f"Too many arguments provided. Expected: {len(arg_names)}, Got: {len(args)}")
                        
                    # Create kwargs from positional args with type conversion
                    arguments_metadata = metadata.get("arguments", [])
                    for i, arg in enumerate(args):
                        if i < len(arg_names):
                            arg_name = arg_names[i]
                            arg_type = next((a.get("type") for a in arguments_metadata if a["name"] == arg_name), None)
                            
                            # Convert argument to the correct type
                            if arg_type == "int":
                                kwargs[arg_name] = int(arg)
                            elif arg_type == "float":
                                kwargs[arg_name] = float(arg)
                            elif arg_type == "bool" and arg.lower() in ("true", "false"):
                                kwargs[arg_name] = arg.lower() == "true"
                            else:
                                kwargs[arg_name] = arg
                
                # Run the command_* function with kwargs only
                return command_func(**kwargs)
            
            # Fallback to legacy run function if command_* not found
            elif hasattr(module, "run"):
                run_func = getattr(module, "run")
                
                # Convert positional args to kwargs based on metadata
                if args and len(args) > 0:
                    cmd_dir = get_command_dir([command_name])
                    metadata = load_command_metadata(cmd_dir)
                    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
                    
                    # Map positional args to named args
                    if len(args) > len(arg_names):
                        raise ValueError(f"Too many arguments provided. Expected: {len(arg_names)}, Got: {len(args)}")
                        
                    # Create kwargs from positional args with type conversion
                    arguments_metadata = metadata.get("arguments", [])
                    for i, arg in enumerate(args):
                        if i < len(arg_names):
                            arg_name = arg_names[i]
                            arg_type = next((a.get("type") for a in arguments_metadata if a["name"] == arg_name), None)
                            
                            # Convert argument to the correct type
                            if arg_type == "int":
                                kwargs[arg_name] = int(arg)
                            elif arg_type == "float":
                                kwargs[arg_name] = float(arg)
                            elif arg_type == "bool" and arg.lower() in ("true", "false"):
                                kwargs[arg_name] = arg.lower() == "true"
                            else:
                                kwargs[arg_name] = arg
                
                # Run with kwargs
                return run_func(**kwargs)
            else:
                raise AttributeError(f"Command '{command_name}' must define either 'command_{command_name}' or 'run' function")
                
        elif len(path_components) == 2:
            # This is a subcommand
            group_name = path_components[0]
            subcommand_name = path_components[1]
            
            module = import_subcommand_module(group_name, subcommand_name)
            
            # Check if module has the command_*_* function first
            function_name = f"command_{group_name}_{subcommand_name}"
            if hasattr(module, function_name):
                command_func = getattr(module, function_name)
                
                # Convert positional args to kwargs based on metadata if needed
                if args and len(args) > 0:
                    group_dir = get_command_dir([group_name])
                    metadata = load_subcommand_metadata(group_dir, subcommand_name)
                    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
                    
                    # Map positional args to named args
                    if len(args) > len(arg_names):
                        raise ValueError(f"Too many arguments provided. Expected: {len(arg_names)}, Got: {len(args)}")
                        
                    # Create kwargs from positional args with type conversion
                    arguments_metadata = metadata.get("arguments", [])
                    for i, arg in enumerate(args):
                        if i < len(arg_names):
                            arg_name = arg_names[i]
                            arg_type = next((a.get("type") for a in arguments_metadata if a["name"] == arg_name), None)
                            
                            # Convert argument to the correct type
                            if arg_type == "int":
                                kwargs[arg_name] = int(arg)
                            elif arg_type == "float":
                                kwargs[arg_name] = float(arg)
                            elif arg_type == "bool" and arg.lower() in ("true", "false"):
                                kwargs[arg_name] = arg.lower() == "true"
                            else:
                                kwargs[arg_name] = arg
                
                # Run the command_*_* function with kwargs only
                return command_func(**kwargs)
            
            # Fallback to legacy run function if command_*_* not found
            elif hasattr(module, "run"):
                run_func = getattr(module, "run")
                
                # Convert positional args to kwargs based on metadata
                if args and len(args) > 0:
                    group_dir = get_command_dir([group_name])
                    metadata = load_subcommand_metadata(group_dir, subcommand_name)
                    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
                    
                    # Map positional args to named args
                    if len(args) > len(arg_names):
                        raise ValueError(f"Too many arguments provided. Expected: {len(arg_names)}, Got: {len(args)}")
                        
                    # Create kwargs from positional args with type conversion
                    arguments_metadata = metadata.get("arguments", [])
                    for i, arg in enumerate(args):
                        if i < len(arg_names):
                            arg_name = arg_names[i]
                            arg_type = next((a.get("type") for a in arguments_metadata if a["name"] == arg_name), None)
                            
                            # Convert argument to the correct type
                            if arg_type == "int":
                                kwargs[arg_name] = int(arg)
                            elif arg_type == "float":
                                kwargs[arg_name] = float(arg)
                            elif arg_type == "bool" and arg.lower() in ("true", "false"):
                                kwargs[arg_name] = arg.lower() == "true"
                            else:
                                kwargs[arg_name] = arg
                
                # Run with kwargs
                return run_func(**kwargs)
            else:
                raise AttributeError(f"Subcommand '{group_name} {subcommand_name}' must define either 'command_{group_name}_{subcommand_name}' or 'run' function")
        else:
            raise ValueError(f"Invalid command path: {command_path}")
    
    except Exception as e:
        logger.error(f"Error running command: {e}")
        raise

def remove_entity(command_path: str) -> None:
    """
    Remove a command or group.
    
    Args:
        command_path: Path to the command or group (e.g., "projects" or "projects add")
    """
    path_components = parse_command_path(command_path)
    
    if len(path_components) == 1:
        # This is a top-level command or group
        entity_dir = get_command_dir([path_components[0]])
        
        if not entity_dir.exists():
            raise FileNotFoundError(f"Entity '{command_path}' not found")
            
        shutil.rmtree(entity_dir)
    elif len(path_components) == 2:
        # This is a subcommand
        group_name = path_components[0]
        subcommand_name = path_components[1]
        
        group_dir = get_command_dir([group_name])
        subcommand_yaml = group_dir / f"{subcommand_name}.yaml"
        subcommand_py = group_dir / f"{subcommand_name}.py"
        
        if not subcommand_yaml.exists():
            raise FileNotFoundError(f"Subcommand '{command_path}' not found")
            
        # Remove the subcommand files
        subcommand_yaml.unlink()
        if subcommand_py.exists():
            subcommand_py.unlink()
    else:
        raise ValueError(f"Invalid command path: {command_path}")

# For backward compatibility
remove_command = remove_entity