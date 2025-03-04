"""Command storage utilities for EVAI CLI."""

import os
import logging
import subprocess
import tempfile
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import inspect

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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_name={command_name}", file=sys.stderr)
    
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
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    
    print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={command_dir}", file=sys.stderr)
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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}", file=sys.stderr)
    
    yaml_path = os.path.join(path, "command.yaml")
    
    try:
        with open(yaml_path, "r") as f:
            metadata = yaml.safe_load(f)
            logger.debug(f"Loaded command metadata from {yaml_path}")
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={metadata}", file=sys.stderr)
            return metadata if metadata else {}
    except FileNotFoundError:
        logger.error(f"Command metadata file not found: {yaml_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in command metadata file: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Error loading command metadata: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}, data={data}", file=sys.stderr)
    
    if not data:
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: ValueError", file=sys.stderr)
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
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except OSError as e:
        logger.error(f"Failed to write command metadata file: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Error saving command metadata: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    
    print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=None", file=sys.stderr)


def get_editor() -> str:
    """
    Get the user's preferred editor from the EDITOR environment variable.
    
    Returns:
        The editor command to use (defaults to 'vi' if EDITOR is not set)
    """
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name}", file=sys.stderr)
    
    editor = os.environ.get('EDITOR', 'vi')
    
    print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={editor}", file=sys.stderr)
    return editor


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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_dir={command_dir}", file=sys.stderr)
    
    yaml_path = os.path.join(command_dir, "command.yaml")
    
    if not os.path.exists(yaml_path):
        logger.error(f"Command metadata file not found: {yaml_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
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
            result = (True, metadata)
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
            return result
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML after editing: {e}")
            result = (False, None)
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
            return result
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_dir={command_dir}", file=sys.stderr)
    
    py_path = os.path.join(command_dir, "command.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Command implementation file not found: {py_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    
    editor = get_editor()
    logger.debug(f"Using editor: {editor}")
    
    try:
        # Open the editor for the user to edit the file
        subprocess.run([editor, py_path], check=True)
        logger.debug(f"Editor closed for {py_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=True", file=sys.stderr)
        return True
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
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
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_dir={command_dir}", file=sys.stderr)
    
    py_path = os.path.join(command_dir, "command.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Command implementation file not found: {py_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
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
            return_value = (True, None)
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={return_value}", file=sys.stderr)
            return return_value
        else:
            logger.debug(f"Lint check failed for {py_path}: {result.stdout}")
            return_value = (False, result.stdout)
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={return_value}", file=sys.stderr)
            return return_value
            
    except FileNotFoundError:
        # flake8 command not found
        logger.error("flake8 command not found. Please install flake8.")
        return_value = (False, "flake8 command not found. Please install flake8.")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={return_value}", file=sys.stderr)
        return return_value
    except Exception as e:
        logger.error(f"Error running lint check: {e}")
        return_value = (False, str(e))
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={return_value}", file=sys.stderr)
        return return_value


def list_commands() -> List[Dict[str, Any]]:
    """
    List all available commands.
    
    Returns:
        A list of dictionaries containing command metadata
    """
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name}", file=sys.stderr)
    
    commands_dir = os.path.expanduser("~/.evai/commands")
    
    # Create the directory if it doesn't exist
    os.makedirs(commands_dir, exist_ok=True)
    
    commands = []
    
    # Scan the commands directory
    for command_name in os.listdir(commands_dir):
        command_dir = os.path.join(commands_dir, command_name)
        
        # Skip if not a directory
        if not os.path.isdir(command_dir):
            continue
        
        try:
            # Load the command metadata
            metadata = load_command_metadata(command_dir)
            
            # Skip disabled commands
            if metadata.get("disabled", False):
                continue
                
            # Add the command to the list
            commands.append({
                "name": metadata.get("name", command_name),
                "description": metadata.get("description", "No description"),
                "path": command_dir
            })
        except Exception as e:
            logger.warning(f"Error loading command '{command_name}': {e}")
    
    print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={commands}", file=sys.stderr)
    return commands


def import_command_module(command_name: str) -> Any:
    """
    Dynamically import a command module.
    
    Args:
        command_name: The name of the command
        
    Returns:
        The imported module
        
    Raises:
        ImportError: If the module cannot be imported
        FileNotFoundError: If the command.py file doesn't exist
    """
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_name={command_name}", file=sys.stderr)
    
    command_dir = get_command_dir(command_name)
    command_py_path = os.path.join(command_dir, "command.py")
    
    if not os.path.exists(command_py_path):
        logger.error(f"Command implementation file not found: {command_py_path}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Command implementation file not found: {command_py_path}")
    
    try:
        # Create a module spec
        spec = importlib.util.spec_from_file_location(
            f"evai.commands.{command_name}", command_py_path
        )
        
        if spec is None or spec.loader is None:
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: ImportError", file=sys.stderr)
            raise ImportError(f"Failed to create module spec for {command_py_path}")
        
        # Create the module
        module = importlib.util.module_from_spec(spec)
        
        # Add the module to sys.modules
        sys.modules[spec.name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={module}", file=sys.stderr)
        return module
    except Exception as e:
        logger.error(f"Error importing command module: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise ImportError(f"Error importing command module: {e}")


def run_command(command_name: str, **kwargs) -> Any:
    """
    Run a command with the given arguments.
    
    Args:
        command_name: The name of the command
        **kwargs: Arguments to pass to the command
        
    Returns:
        The result of the command
        
    Raises:
        ImportError: If the command module cannot be imported
        AttributeError: If the command module doesn't have a run function
        Exception: If the command execution fails
    """
    print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - command_name={command_name}, kwargs={kwargs}", file=sys.stderr)
    
    try:
        # Import the command module
        module = import_command_module(command_name)
        
        # Check if the module has a run function
        if not hasattr(module, "run"):
            logger.error(f"Command module doesn't have a run function: {command_name}")
            print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: AttributeError", file=sys.stderr)
            raise AttributeError(f"Command module doesn't have a run function: {command_name}")
        
        # Run the command
        result = module.run(**kwargs)
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
        return result
    except (ImportError, AttributeError) as e:
        logger.error(f"Error running command: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise 