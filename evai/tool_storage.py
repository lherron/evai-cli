"""Tool storage utilities for EVAI CLI."""

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
import json

# Set up logging
logger = logging.getLogger(__name__)

# Get the path to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def get_tool_dir(tool_name: str) -> str:
    """
    Get the directory path for a tool and create it if it doesn't exist.
    
    Args:
        tool_name: The name of the tool
        
    Returns:
        The absolute path to the tool directory
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_name={tool_name}", file=sys.stderr)
    
    if not tool_name:
        raise ValueError("Tool name cannot be empty")
    
    # Validate tool name (alphanumeric, hyphens, and underscores only)
    if not all(c.isalnum() or c in "-_" for c in tool_name):
        raise ValueError(
            "Tool name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    # Get the tool directory path
    tool_dir = os.path.expanduser(f"~/.evai/tools/{tool_name}")
    
    # Create the directory if it doesn't exist
    try:
        os.makedirs(tool_dir, exist_ok=True)
        logger.debug(f"Tool directory created or already exists: {tool_dir}")
    except OSError as e:
        logger.error(f"Failed to create tool directory: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    
    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={tool_dir}", file=sys.stderr)
    return tool_dir


def load_tool_metadata(path: str) -> Dict[str, Any]:
    """
    Load tool metadata from a YAML file.
    
    Args:
        path: Path to the directory containing the tool.yaml file
        
    Returns:
        Dictionary containing the tool metadata
        
    Raises:
        FileNotFoundError: If the tool.yaml file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}", file=sys.stderr)
    
    yaml_path = os.path.join(path, "tool.yaml")
    
    try:
        with open(yaml_path, "r") as f:
            metadata = yaml.safe_load(f)
            logger.debug(f"Loaded tool metadata from {yaml_path}")
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={metadata}", file=sys.stderr)
            return metadata if metadata else {}
    except FileNotFoundError:
        logger.error(f"Tool metadata file not found: {yaml_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in tool metadata file: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Error loading tool metadata: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise


def save_tool_metadata(path: str, data: Dict[str, Any]) -> None:
    """
    Save tool metadata to a YAML file.
    
    Args:
        path: Path to the directory where tool.yaml will be saved
        data: Dictionary containing the tool metadata
        
    Raises:
        OSError: If the file cannot be written
        yaml.YAMLError: If the data cannot be serialized to YAML
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}, data={data}", file=sys.stderr)
    
    if not data:
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: ValueError", file=sys.stderr)
        raise ValueError("Tool metadata cannot be empty")
    
    yaml_path = os.path.join(path, "tool.yaml")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    
    try:
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Saved tool metadata to {yaml_path}")
    except yaml.YAMLError as e:
        logger.error(f"Failed to serialize tool metadata to YAML: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except OSError as e:
        logger.error(f"Failed to write tool metadata file: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Error saving tool metadata: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    
    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=None", file=sys.stderr)


def get_editor() -> str:
    """
    Get the user's preferred editor.
    
    Returns:
        The path to the editor executable
    """
    # Try to get the editor from the EDITOR environment variable
    editor = os.environ.get("EDITOR")
    
    # If not set, use a default editor
    if not editor:
        if sys.platform == "win32":
            editor = "notepad.exe"
        else:
            # Try to find a common editor
            for e in ["nano", "vim", "vi", "emacs"]:
                try:
                    subprocess.run(["which", e], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    editor = e
                    break
                except subprocess.SubprocessError:
                    continue
            
            # If no editor found, use nano as a last resort
            if not editor:
                editor = "nano"
    
    return editor


def load_sample_tool_py() -> str:
    """
    Load the sample tool.py template.
    
    Returns:
        The contents of the sample tool.py file
        
    Raises:
        FileNotFoundError: If the sample file doesn't exist
    """
    sample_path = os.path.join(TEMPLATES_DIR, "sample_tool.py")
    
    try:
        with open(sample_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Sample tool.py file not found: {sample_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading sample tool.py: {e}")
        raise


def load_sample_tool_yaml(tool_name: str) -> Dict[str, Any]:
    """
    Load the sample tool.yaml template and substitute the tool name.
    
    Args:
        tool_name: The name of the tool
        
    Returns:
        Dictionary containing the tool metadata
        
    Raises:
        FileNotFoundError: If the sample file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    sample_path = os.path.join(TEMPLATES_DIR, "sample_tool.yaml")
    
    try:
        with open(sample_path, "r") as f:
            template = f.read()
            # Replace the placeholder with the actual tool name
            template = template.replace("{tool_name}", tool_name)
            # Parse the YAML
            metadata = yaml.safe_load(template)
            return metadata if metadata else {}
    except FileNotFoundError:
        logger.error(f"Sample tool.yaml file not found: {sample_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in sample tool.yaml file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading sample tool.yaml: {e}")
        raise


def edit_tool_metadata(tool_dir: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Open the tool.yaml file in the user's preferred editor and validate it after editing.
    
    Args:
        tool_dir: Path to the tool directory
        
    Returns:
        A tuple containing:
        - A boolean indicating whether the edit was successful
        - The updated metadata dictionary if successful, None otherwise
        
    Raises:
        FileNotFoundError: If the tool.yaml file doesn't exist
        subprocess.SubprocessError: If the editor process fails
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_dir={tool_dir}", file=sys.stderr)
    
    yaml_path = os.path.join(tool_dir, "tool.yaml")
    
    if not os.path.exists(yaml_path):
        logger.error(f"Tool metadata file not found: {yaml_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Tool metadata file not found: {yaml_path}")
    
    editor = get_editor()
    logger.debug(f"Using editor: {editor}")
    
    try:
        # Open the editor for the user to edit the file
        subprocess.run([editor, yaml_path], check=True)
        logger.debug(f"Editor closed for {yaml_path}")
        
        # Try to load the edited file
        try:
            metadata = load_tool_metadata(tool_dir)
            result = (True, metadata)
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
            return result
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML after editing: {e}")
            result = (False, None)
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
            return result
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise


def edit_tool_implementation(tool_dir: str) -> bool:
    """
    Open the tool.py file in the user's preferred editor.
    
    Args:
        tool_dir: Path to the tool directory
        
    Returns:
        A boolean indicating whether the edit was successful
        
    Raises:
        FileNotFoundError: If the tool.py file doesn't exist
        subprocess.SubprocessError: If the editor process fails
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_dir={tool_dir}", file=sys.stderr)
    
    py_path = os.path.join(tool_dir, "tool.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Tool implementation file not found: {py_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Tool implementation file not found: {py_path}")
    
    editor = get_editor()
    logger.debug(f"Using editor: {editor}")
    
    try:
        # Open the editor for the user to edit the file
        subprocess.run([editor, py_path], check=True)
        logger.debug(f"Editor closed for {py_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=True", file=sys.stderr)
        return True
            
    except subprocess.SubprocessError as e:
        logger.error(f"Error running editor: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise


def run_lint_check(tool_dir: str) -> Tuple[bool, Optional[str]]:
    """
    Run flake8 on the tool.py file to check for linting errors.
    
    Args:
        tool_dir: Path to the tool directory
        
    Returns:
        A tuple containing:
        - A boolean indicating whether the lint check passed
        - The lint error output if the check failed, None otherwise
        
    Raises:
        FileNotFoundError: If the tool.py file doesn't exist
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_dir={tool_dir}", file=sys.stderr)
    
    py_path = os.path.join(tool_dir, "tool.py")
    
    if not os.path.exists(py_path):
        logger.error(f"Tool implementation file not found: {py_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Tool implementation file not found: {py_path}")
    
    try:
        # Run flake8 on the file
        result = subprocess.run(
            ["flake8", py_path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check if flake8 found any errors
        if result.returncode == 0:
            logger.debug(f"Lint check passed for {py_path}")
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=(True, None)", file=sys.stderr)
            return (True, None)
        else:
            logger.warning(f"Lint check failed for {py_path}")
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=(False, {result.stdout})", file=sys.stderr)
            return (False, result.stdout)
    except FileNotFoundError:
        # flake8 is not installed
        logger.warning("flake8 is not installed, skipping lint check")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=(True, None)", file=sys.stderr)
        return (True, None)
    except Exception as e:
        logger.error(f"Error running lint check: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return=(False, {str(e)})", file=sys.stderr)
        return (False, str(e))


def list_tools() -> List[Dict[str, Any]]:
    """
    List all available tools.
    
    Returns:
        A list of dictionaries containing tool metadata
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name}", file=sys.stderr)
    
    tools_dir = os.path.expanduser("~/.evai/tools")
    
    # Create the directory if it doesn't exist
    os.makedirs(tools_dir, exist_ok=True)
    
    tools = []
    
    # Scan the tools directory
    for tool_name in os.listdir(tools_dir):
        tool_dir = os.path.join(tools_dir, tool_name)
        
        # Skip if not a directory
        if not os.path.isdir(tool_dir):
            continue
        
        try:
            # Load the tool metadata
            metadata = load_tool_metadata(tool_dir)
            
            # Skip disabled tools
            if metadata.get("disabled", False):
                continue
                
            # Add the tool to the list
            tools.append({
                "name": metadata.get("name", tool_name),
                "description": metadata.get("description", "No description"),
                "path": tool_dir
            })
        except Exception as e:
            logger.warning(f"Error loading tool '{tool_name}': {e}")
    
    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={tools}", file=sys.stderr)
    return tools


def import_tool_module(tool_name: str) -> Any:
    """
    Dynamically import a tool module.
    
    Args:
        tool_name: The name of the tool
        
    Returns:
        The imported module
        
    Raises:
        ImportError: If the module cannot be imported
        FileNotFoundError: If the tool.py file doesn't exist
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_name={tool_name}", file=sys.stderr)
    
    tool_dir = get_tool_dir(tool_name)
    tool_py_path = os.path.join(tool_dir, "tool.py")
    
    if not os.path.exists(tool_py_path):
        logger.error(f"Tool implementation file not found: {tool_py_path}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
        raise FileNotFoundError(f"Tool implementation file not found: {tool_py_path}")
    
    try:
        # Create a module spec
        spec = importlib.util.spec_from_file_location(
            f"evai.tools.{tool_name}", tool_py_path
        )
        
        if spec is None or spec.loader is None:
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: ImportError", file=sys.stderr)
            raise ImportError(f"Failed to create module spec for {tool_py_path}")
        
        # Create the module
        module = importlib.util.module_from_spec(spec)
        
        # Add the module to sys.modules
        sys.modules[spec.name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={module}", file=sys.stderr)
        return module
    except Exception as e:
        logger.error(f"Error importing tool module: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise ImportError(f"Error importing tool module: {e}")


def run_tool(tool_name: str, *args, **kwargs) -> Any:
    """
    Run a tool with the given arguments.
    
    Args:
        tool_name: The name of the tool
        *args: Positional arguments to pass to the tool function
        **kwargs: Keyword arguments to pass to the tool
        
    Returns:
        The result of the tool
        
    Raises:
        ImportError: If the tool module cannot be imported
        AttributeError: If the tool module doesn't have any tool_* functions
        Exception: If the tool execution fails
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - tool_name={tool_name}, args={args}, kwargs={kwargs}", file=sys.stderr)
    
    try:
        # Import the tool module
        module = import_tool_module(tool_name)
        
        # Find callable functions in the module that start with "tool_"
        tool_functions = [
            name for name, obj in inspect.getmembers(module)
            if inspect.isfunction(obj) and name.startswith('tool_')
        ]
        
        if not tool_functions:
            logger.error(f"Tool module doesn't have any tool_* functions: {tool_name}")
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: AttributeError", file=sys.stderr)
            raise AttributeError(f"Tool module doesn't have any tool_* functions: {tool_name}")
        
        # Use the first tool function found
        function_name = tool_functions[0]
        function = getattr(module, function_name)
        
        # Get the function signature
        sig = inspect.signature(function)
        
        # If we have positional arguments, use them
        if args:
            # Convert args to appropriate types based on function signature
            converted_args = []
            for i, (param_name, param) in enumerate(sig.parameters.items()):
                if i < len(args):
                    # Get the parameter type annotation
                    param_type = param.annotation
                    if param_type is inspect.Parameter.empty:
                        # No type annotation, use the arg as is
                        converted_args.append(args[i])
                    else:
                        # Try to convert the arg to the annotated type
                        try:
                            # Handle special cases for common types
                            if param_type is float or param_type is int:
                                converted_args.append(param_type(args[i]))
                            elif param_type is bool:
                                # Convert string to bool
                                value = str(args[i]).lower()
                                converted_args.append(value in ('true', 't', 'yes', 'y', '1'))
                            else:
                                # For other types, try direct conversion
                                converted_args.append(param_type(args[i]))
                        except (ValueError, TypeError):
                            # If conversion fails, use the original value
                            logger.warning(f"Could not convert argument {args[i]} to {param_type.__name__}")
                            converted_args.append(args[i])
            
            # Call the function with the converted positional arguments
            result = function(*converted_args)
        else:
            # Filter kwargs to only include parameters that the function accepts
            filtered_kwargs = {
                k: v for k, v in kwargs.items() 
                if k in sig.parameters
            }
            
            # Call the function with the filtered kwargs
            result = function(**filtered_kwargs)
        
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
        return result
    except (ImportError, AttributeError) as e:
        logger.error(f"Error running tool: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise


def remove_tool(tool_name: str) -> bool:
    """
    Remove a tool by deleting its directory.
    
    Args:
        tool_name: The name of the tool to remove
        
    Returns:
        True if the tool was successfully removed, False otherwise
        
    Raises:
        ValueError: If the tool name is invalid
        FileNotFoundError: If the tool directory doesn't exist
    """
    if not tool_name:
        raise ValueError("Tool name cannot be empty")
    
    # Validate tool name (alphanumeric, hyphens, and underscores only)
    if not all(c.isalnum() or c in "-_" for c in tool_name):
        raise ValueError(
            "Tool name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    # Get the tool directory path
    tool_dir = os.path.expanduser(f"~/.evai/tools/{tool_name}")
    
    # Check if the directory exists
    if not os.path.exists(tool_dir):
        raise FileNotFoundError(f"Tool '{tool_name}' not found")
    
    # Remove the directory and all its contents
    try:
        import shutil
        shutil.rmtree(tool_dir)
        logger.debug(f"Tool directory removed: {tool_dir}")
        return True
    except OSError as e:
        logger.error(f"Failed to remove tool directory: {e}")
        raise