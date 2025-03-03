"""Command storage utilities for EVAI CLI."""

import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

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


def get_editor() -> str:
    """
    Get the user's preferred editor from the EDITOR environment variable.
    
    Returns:
        The editor command to use (defaults to 'vi' if EDITOR is not set)
    """
    return os.environ.get('EDITOR', 'vi')


def edit_command_metadata(command_dir: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Open the command.yaml file in the user's preferred editor and validate it after editing.
    
    Args:
        command_dir: Path to the command directory
        
    Returns:
        A tuple containing:
        - A boolean indicating whether the edit was successful
        - The updated metadata dictionary if successful, None otherwise
        
    Raises:
        FileNotFoundError: If the command.yaml file doesn't exist
        subprocess.SubprocessError: If the editor process fails
    """
    yaml_path = os.path.join(command_dir, "command.yaml")
    
    if not os.path.exists(yaml_path):
        logger.error(f"Command metadata file not found: {yaml_path}")
        raise FileNotFoundError(f"Command metadata file not found: {yaml_path}")
    
    editor = get_editor()
    logger.debug(f"Using editor: {editor}")
    
    try:
        # Open the editor for the user to edit the file
        subprocess.run([editor, yaml_path], check=True)
        logger.debug(f"Editor closed for {yaml_path}")
        
        # Try to load the edited file
        try:
            metadata = load_command_metadata(command_dir)
            return True, metadata
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML after editing: {e}")
            return False, None
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        raise


def edit_command_implementation(command_dir: str) -> bool:
    """
    Open the command.py file in the user's preferred editor.
    
    Args:
        command_dir: Path to the command directory
        
    Returns:
        A boolean indicating whether the edit was successful
        
    Raises:
        FileNotFoundError: If the command.py file doesn't exist
        subprocess.SubprocessError: If the editor process fails
    """
    py_path = os.path.join(command_dir, "command.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Command implementation file not found: {py_path}")
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    
    editor = get_editor()
    logger.debug(f"Using editor: {editor}")
    
    try:
        # Open the editor for the user to edit the file
        subprocess.run([editor, py_path], check=True)
        logger.debug(f"Editor closed for {py_path}")
        return True
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        raise


def run_lint_check(command_dir: str) -> Tuple[bool, Optional[str]]:
    """
    Run flake8 on the command.py file to check for linting errors.
    
    Args:
        command_dir: Path to the command directory
        
    Returns:
        A tuple containing:
        - A boolean indicating whether the lint check passed
        - The lint error output if the check failed, None otherwise
        
    Raises:
        FileNotFoundError: If the command.py file doesn't exist
    """
    py_path = os.path.join(command_dir, "command.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Command implementation file not found: {py_path}")
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    
    try:
        # Run flake8 on the file
        result = subprocess.run(
            ["flake8", py_path],
            capture_output=True,
            text=True,
            check=False  # Don't raise an exception if flake8 finds errors
        )
        
        # Check if flake8 found any errors
        if result.returncode == 0:
            logger.debug(f"Lint check passed for {py_path}")
            return True, None
        else:
            logger.debug(f"Lint check failed for {py_path}: {result.stdout}")
            return False, result.stdout
            
    except FileNotFoundError:
        # flake8 command not found
        logger.error("flake8 command not found. Please install flake8.")
        return False, "flake8 command not found. Please install flake8."
    except Exception as e:
        logger.error(f"Error running lint check: {e}")
        return False, str(e) 