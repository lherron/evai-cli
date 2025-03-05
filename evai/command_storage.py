"""Command storage utilities for EVAI CLI."""

import os
import yaml
import shutil
from pathlib import Path
import importlib.util
import inspect
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

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
    Run a command with the given arguments, converting them to metadata-specified types.
    
    Args:
        command_path: The path to the command (e.g., "subtract" or "math subtract").
        *args: Positional arguments.
        **kwargs: Named arguments (options).
    
    Returns:
        The result from the command's run function.
    
    Raises:
        ValueError: If argument count or conversion fails.
        FileNotFoundError: If implementation file is missing.
    """
    path_components = parse_command_path(command_path)
    
    # Determine command type and get metadata
    if len(path_components) == 1:
        # This is a top-level command
        command_name = path_components[0]
        cmd_dir = get_command_dir([command_name])
        metadata_path = cmd_dir / f"{command_name}.yaml"
        
        if not metadata_path.exists():
            # Try legacy path
            metadata_path = cmd_dir / "command.yaml"
        
        impl_path = cmd_dir / f"{command_name}.py"
        if not impl_path.exists():
            # Try legacy path
            impl_path = cmd_dir / "command.py"
            if not impl_path.exists():
                raise FileNotFoundError(f"Implementation file not found for command: {command_name}")
    
    elif len(path_components) == 2:
        # This is a subcommand
        group_name = path_components[0]
        command_name = path_components[1]
        group_dir = get_command_dir([group_name])
        metadata_path = group_dir / f"{command_name}.yaml"
        impl_path = group_dir / f"{command_name}.py"
        
        if not metadata_path.exists() or not impl_path.exists():
            raise FileNotFoundError(f"Files not found for subcommand: {group_name} {command_name}")
    
    else:
        raise ValueError(f"Invalid command path: {command_path}")
    
    # Check if this is a group (group cannot be executed)
    if len(path_components) == 1 and is_group(cmd_dir):
        raise ValueError(f"Cannot run a group: {command_path}")
    
    # Load metadata
    with open(metadata_path, "r") as f:
        metadata = yaml.safe_load(f)
    
    # Convert positional arguments based on metadata
    arg_types = [arg["type"] for arg in metadata.get("arguments", [])]
    arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
    
    if len(args) > len(arg_types):
        raise ValueError(f"Too many positional arguments: expected {len(arg_types)}, got {len(args)}")
    if len(args) < len(arg_types):
        raise ValueError(f"Not enough positional arguments: expected {len(arg_types)}, got {len(args)}")
    
    # Convert arguments to their specified types
    try:
        converted_args = [convert_value(arg, arg_type) for arg, arg_type in zip(args, arg_types)]
    except ValueError as e:
        raise ValueError(f"Argument conversion error: {e}")
    
    # Convert keyword options based on metadata
    option_types = {opt["name"]: opt["type"] for opt in metadata.get("options", [])}
    converted_kwargs = {}
    
    try:
        for key, value in kwargs.items():
            if key in option_types:
                opt_type = option_types[key]
                converted_kwargs[key] = convert_value(value, opt_type)
            else:
                # Pass through unknown options as strings
                converted_kwargs[key] = str(value)
    except ValueError as e:
        raise ValueError(f"Option conversion error for '{key}': {e}")
    
    # Load the implementation module
    spec = importlib.util.spec_from_file_location(command_name, impl_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Determine which function to call
    if len(path_components) == 1:
        # Top-level command
        func_name = f"command_{command_name}"
        if hasattr(module, func_name):
            run_func = getattr(module, func_name)
        else:
            raise AttributeError(f"Command '{command_name}' must define 'command_{command_name}' function")
    else:
        # Subcommand
        group_name = path_components[0]
        func_name = f"command_{group_name}_{command_name}"
        if hasattr(module, func_name):
            run_func = getattr(module, func_name)
        else:
            raise AttributeError(f"Subcommand '{group_name} {command_name}' must define 'command_{group_name}_{command_name}' function")
    
    # Combine converted args and kwargs
    kwargs_for_run = dict(zip(arg_names, converted_args))
    kwargs_for_run.update(converted_kwargs)
    
    # Validate type consistency between function type hints and YAML metadata
    try:
        validate_command_types(command_path)
    except ValueError as e:
        logger.warning(f"Type validation warning for command {command_path}: {e}")
    
    # Run the function
    try:
        return run_func(**kwargs_for_run)
    except Exception as e:
        logger.error(f"Error running command {command_path}: {e}")
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

def get_function_type_hints(func: Callable) -> Dict[str, Any]:
    """
    Extract type hints from the command function's parameters.

    Args:
        func: The command function (e.g., command_subtract).

    Returns:
        A dictionary mapping parameter names to their type hints.
    """
    signature = inspect.signature(func)
    type_hints = {}
    for param_name, param in signature.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            type_hints[param_name] = param.annotation
    return type_hints

def get_yaml_types(metadata: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract type information from the YAML metadata for arguments and options.

    Args:
        metadata: The loaded YAML metadata for the command.

    Returns:
        A dictionary mapping parameter names to their YAML-defined types.
    """
    arg_types = {arg['name']: arg['type'] for arg in metadata.get('arguments', [])}
    opt_types = {opt['name']: opt['type'] for opt in metadata.get('options', [])}
    return {**arg_types, **opt_types}

def map_type_to_yaml(type_hint: Any) -> str:
    """
    Map Python type hints to YAML type strings.

    Args:
        type_hint: The Python type hint (e.g., int, str).

    Returns:
        The corresponding YAML type string (e.g., 'integer', 'string').
    """
    if type_hint == str:
        return 'string'
    elif type_hint == int:
        return 'integer'
    elif type_hint == float:
        return 'float'
    elif type_hint == bool:
        return 'boolean'
    else:
        return 'unknown'

def validate_command_types(command_path: str) -> None:
    """
    Validate that the type hints in the command function match the YAML metadata.

    Args:
        command_path (str): The path to the command (e.g., 'subtract').

    Raises:
        ValueError: If there are discrepancies between the function type hints and YAML types.
    """
    # Parse the command path
    path_components = parse_command_path(command_path)
    
    # Load metadata and command function
    if len(path_components) == 1:
        # Top-level command
        command_name = path_components[0]
        cmd_dir = get_command_dir([command_name])
        metadata_path = cmd_dir / f"{command_name}.yaml"
        
        if not metadata_path.exists():
            # Try legacy path
            metadata_path = cmd_dir / "command.yaml"
        
        with open(metadata_path, "r") as f:
            metadata = yaml.safe_load(f)
        
        impl_path = cmd_dir / f"{command_name}.py"
        if not impl_path.exists():
            # Try legacy path
            impl_path = cmd_dir / "command.py"
        
        # Import module and get function
        spec = importlib.util.spec_from_file_location(command_name, impl_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func_name = f"command_{command_name}"
        if hasattr(module, func_name):
            command_func = getattr(module, func_name)
        else:
            raise AttributeError(f"Command '{command_name}' must define 'command_{command_name}' function")
    
    elif len(path_components) == 2:
        # Subcommand
        group_name = path_components[0]
        subcommand_name = path_components[1]
        group_dir = get_command_dir([group_name])
        metadata_path = group_dir / f"{subcommand_name}.yaml"
        
        with open(metadata_path, "r") as f:
            metadata = yaml.safe_load(f)
        
        impl_path = group_dir / f"{subcommand_name}.py"
        
        # Import module and get function
        spec = importlib.util.spec_from_file_location(f"{group_name}_{subcommand_name}", impl_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func_name = f"command_{group_name}_{subcommand_name}"
        if hasattr(module, func_name):
            command_func = getattr(module, func_name)
        else:
            raise AttributeError(f"Subcommand '{group_name} {subcommand_name}' must define 'command_{group_name}_{subcommand_name}' function")
    
    else:
        raise ValueError(f"Invalid command path: {command_path}")

    # Get type hints from the function
    func_type_hints = get_function_type_hints(command_func)

    # Get types from YAML metadata
    yaml_types = get_yaml_types(metadata)

    # Check for discrepancies
    for param_name, type_hint in func_type_hints.items():
        if param_name in yaml_types:
            yaml_type = yaml_types[param_name]
            mapped_type = map_type_to_yaml(type_hint)
            if mapped_type != yaml_type and mapped_type != 'unknown':
                raise ValueError(
                    f"Type mismatch for parameter '{param_name}' in command '{command_path}': "
                    f"function expects '{mapped_type}', YAML specifies '{yaml_type}'"
                )
        else:
            raise ValueError(
                f"Parameter '{param_name}' in command '{command_path}' is not defined in YAML metadata"
            )

    # Check for parameters in YAML but not in the function
    for param_name in yaml_types:
        if param_name not in func_type_hints:
            logger.warning(
                f"Parameter '{param_name}' is defined in YAML metadata but not type-hinted in the function for command '{command_path}'"
            )