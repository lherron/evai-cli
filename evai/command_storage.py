"""Command storage utilities for EVAI CLI."""

import os
import yaml
from pathlib import Path
import importlib.util
import inspect
import logging

logger = logging.getLogger(__name__)

COMMANDS_DIR = Path.home() / ".evai" / "commands"

def get_command_dir(command_name: str) -> Path:
    """Get the directory path for a command and create it if it doesn't exist."""
    command_dir = COMMANDS_DIR / command_name
    command_dir.mkdir(parents=True, exist_ok=True)
    return command_dir

def load_command_metadata(path: Path) -> dict:
    """Load command metadata from command.yaml."""
    yaml_path = path / "command.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Command metadata file not found: {yaml_path}")
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def save_command_metadata(path: Path, data: dict) -> None:
    """Save command metadata to command.yaml."""
    yaml_path = path / "command.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def list_commands() -> list[dict]:
    """List all available commands."""
    if not COMMANDS_DIR.exists():
        return []
    commands = []
    for cmd_dir in COMMANDS_DIR.iterdir():
        if cmd_dir.is_dir():
            try:
                metadata = load_command_metadata(cmd_dir)
                if not metadata.get("disabled", False):
                    commands.append({
                        "name": metadata.get("name", cmd_dir.name),
                        "description": metadata.get("description", "No description"),
                        "path": cmd_dir
                    })
            except Exception as e:
                logger.warning(f"Error loading command {cmd_dir.name}: {e}")
    return commands

def import_command_module(command_name: str):
    """Dynamically import a command module."""
    cmd_dir = get_command_dir(command_name)
    py_path = cmd_dir / "command.py"
    if not py_path.exists():
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    spec = importlib.util.spec_from_file_location(f"evai.commands.{command_name}", py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_command(command_name: str, *args, **kwargs):
    """Run a command with the given arguments."""
    try:
        # Import the command module
        module = import_command_module(command_name)
        
        # Check if the module has a run function
        if not hasattr(module, "run"):
            raise AttributeError(f"Command '{command_name}' does not have a run function")
        
        run_func = getattr(module, "run")
        
        # Get the function signature
        sig = inspect.signature(run_func)
        
        # Check if we're using args or kwargs
        if args and len(args) > 0:
            # Convert positional args to kwargs based on metadata
            cmd_dir = get_command_dir(command_name)
            metadata = load_command_metadata(cmd_dir)
            arg_names = [arg["name"] for arg in metadata.get("arguments", [])]
            
            # Map positional args to named args
            if len(args) > len(arg_names):
                raise ValueError(f"Too many arguments provided. Expected: {len(arg_names)}, Got: {len(args)}")
                
            # Create kwargs from positional args
            for i, arg in enumerate(args):
                if i < len(arg_names):
                    kwargs[arg_names[i]] = arg
            
            # Run with kwargs
            return run_func(**kwargs)
        else:
            # Run with kwargs
            return run_func(**kwargs)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        raise

def remove_command(command_name: str) -> None:
    """Remove a command directory and its files."""
    import shutil
    cmd_dir = get_command_dir(command_name)
    if not cmd_dir.exists():
        raise FileNotFoundError(f"Command '{command_name}' not found")
    shutil.rmtree(cmd_dir)