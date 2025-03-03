"""Command storage utilities for EVAI CLI."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

# Set up logging
logger = logging.getLogger(__name__)


def get_command_dir(command_name: str) -> str:
    """
    Get the directory path for a command and create it if it doesn't exist.
    
    Args:
        command_name: The name of the command
        
    Returns:
        The absolute path to the command directory
    """
    if not command_name:
        raise ValueError("Command name cannot be empty")
    
    # Validate command name (alphanumeric, hyphens, and underscores only)
    if not all(c.isalnum() or c in "-_" for c in command_name):
        raise ValueError(
            "Command name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    # Get the command directory path
    command_dir = os.path.expanduser(f"~/.evai/commands/{command_name}")
    
    # Create the directory if it doesn't exist
    try:
        os.makedirs(command_dir, exist_ok=True)
        logger.debug(f"Command directory created or already exists: {command_dir}")
    except OSError as e:
        logger.error(f"Failed to create command directory: {e}")
        raise
    
    return command_dir


def load_command_metadata(path: str) -> Dict[str, Any]:
    """
    Load command metadata from a YAML file.
    
    Args:
        path: Path to the directory containing the command.yaml file
        
    Returns:
        Dictionary containing the command metadata
        
    Raises:
        FileNotFoundError: If the command.yaml file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    yaml_path = os.path.join(path, "command.yaml")
    
    try:
        with open(yaml_path, "r") as f:
            metadata = yaml.safe_load(f)
            logger.debug(f"Loaded command metadata from {yaml_path}")
            return metadata if metadata else {}
    except FileNotFoundError:
        logger.error(f"Command metadata file not found: {yaml_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in command metadata file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading command metadata: {e}")
        raise


def save_command_metadata(path: str, data: Dict[str, Any]) -> None:
    """
    Save command metadata to a YAML file.
    
    Args:
        path: Path to the directory where command.yaml will be saved
        data: Dictionary containing the command metadata
        
    Raises:
        OSError: If the file cannot be written
        yaml.YAMLError: If the data cannot be serialized to YAML
    """
    if not data:
        raise ValueError("Command metadata cannot be empty")
    
    yaml_path = os.path.join(path, "command.yaml")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    
    try:
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Saved command metadata to {yaml_path}")
    except yaml.YAMLError as e:
        logger.error(f"Failed to serialize command metadata to YAML: {e}")
        raise
    except OSError as e:
        logger.error(f"Failed to write command metadata file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving command metadata: {e}")
        raise 