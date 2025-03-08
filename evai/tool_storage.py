"""Tool storage utilities for EVAI CLI."""

import os
import logging
import subprocess
import tempfile
import importlib.util
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import inspect

import yaml
import json

# Set up logging
logger = logging.getLogger(__name__)

# Get the path to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Tool directory constants
TOOLS_BASE_DIR = os.path.expanduser("~/.evai/tools")


def get_tool_dir(path: str) -> str:
    """
    Get the directory path for a tool or tool group and create it if it doesn't exist.
    
    Args:
        path: Tool path, which can include groups (e.g., "group/subtool")
        
    Returns:
        The absolute path to the tool or group directory
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}", file=sys.stderr)
    
    if not path:
        raise ValueError("Tool path cannot be empty")
    
    # Replace / with os.sep to handle the path correctly
    path_components = path.replace('/', os.sep).split(os.sep)
    
    # Validate each component of the path
    for component in path_components:
        if not all(c.isalnum() or c in "-_" for c in component):
            raise ValueError(
                "Tool path components must contain only alphanumeric characters, hyphens, and underscores"
            )
    
    # Get the full directory path
    tool_dir = os.path.join(TOOLS_BASE_DIR, *path_components)
    
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
    Load tool or group metadata from a YAML file.
    
    Args:
        path: Path to the tool or group, which can include nested paths (e.g., "group/subtool")
        
    Returns:
        Dictionary containing the metadata
        
    Raises:
        FileNotFoundError: If the metadata YAML file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}", file=sys.stderr)
    
    # Get the directory for this path
    dir_path = get_tool_dir(path)
    
    # Get the last component of the path (tool or group name)
    path_components = path.replace('/', os.sep).split(os.sep)
    name = path_components[-1]
    
    # Check for different yaml file formats in order of priority
    yaml_paths = [
        os.path.join(dir_path, f"{name}.yaml"),  # <name>.yaml (preferred for tools)
        os.path.join(dir_path, "tool.yaml"),     # tool.yaml (legacy for tools)
        os.path.join(dir_path, "group.yaml")     # group.yaml (for groups)
    ]
    
    for yaml_path in yaml_paths:
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r") as f:
                    metadata = yaml.safe_load(f)
                    logger.debug(f"Loaded metadata from {yaml_path}")
                    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={metadata}", file=sys.stderr)
                    return metadata if metadata else {}
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in metadata file: {e}")
                # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
                raise
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
                raise
    
    # If we get here, no metadata file was found
    logger.error(f"Metadata file not found for: {path}")
    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
    raise FileNotFoundError(f"Metadata file not found for: {path}")


def save_tool_metadata(path: str, data: Dict[str, Any]) -> None:
    """
    Save tool or group metadata to a YAML file.
    
    Args:
        path: Path to the tool or group, which can include nested paths (e.g., "group/subtool")
        data: Dictionary containing the metadata
        
    Raises:
        ValueError: If the metadata is empty
        OSError: If the file cannot be written
        yaml.YAMLError: If the data cannot be serialized to YAML
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}, data={data}", file=sys.stderr)
    
    if not data:
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: ValueError", file=sys.stderr)
        raise ValueError("Metadata cannot be empty")
    
    # Get the directory for this path
    dir_path = get_tool_dir(path)
    
    # Get the last component of the path (tool or group name)
    path_components = path.replace('/', os.sep).split(os.sep)
    name = path_components[-1]
    
    # Determine what type of entity this is and choose the appropriate file name
    if "arguments" in data or "options" in data or "params" in data:
        # This is a tool, save as <name>.yaml
        yaml_path = os.path.join(dir_path, f"{name}.yaml")
    elif len(path_components) > 1 or data.get("type") == "group":
        # This is a group, save as group.yaml
        yaml_path = os.path.join(dir_path, "group.yaml")
    else:
        # Default case, save as <name>.yaml
        yaml_path = os.path.join(dir_path, f"{name}.yaml")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    
    try:
        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Saved metadata to {yaml_path}")
    except yaml.YAMLError as e:
        logger.error(f"Failed to serialize metadata to YAML: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except OSError as e:
        logger.error(f"Failed to write metadata file: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")
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
    List all available tools and groups, supporting hierarchical organization.
    
    Returns:
        A list of dictionaries containing tool and group metadata:
        - name: Tool or group name
        - path: Relative path (e.g., group/subtool)
        - type: "tool" or "group"
        - description: Description from metadata
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name}", file=sys.stderr)
    
    # Create the base directory if it doesn't exist
    os.makedirs(TOOLS_BASE_DIR, exist_ok=True)
    
    entities = []
    
    def scan_directory(dir_path, rel_path=''):
        """Recursively scan a directory for tools and groups."""
        for item_name in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item_name)
            
            # Skip if not a directory
            if not os.path.isdir(item_path):
                continue
            
            # Determine the relative path for this item
            if rel_path:
                item_rel_path = f"{rel_path}/{item_name}"
            else:
                item_rel_path = item_name
            
            # Check for group.yaml to identify groups
            group_yaml = os.path.join(item_path, "group.yaml")
            
            if os.path.exists(group_yaml):
                # This is a group
                try:
                    with open(group_yaml, "r") as f:
                        metadata = yaml.safe_load(f) or {}
                    
                    # Skip disabled groups
                    if metadata.get("disabled", False):
                        continue
                    
                    # Add the group to the list
                    entities.append({
                        "name": metadata.get("name", item_name),
                        "path": item_rel_path,
                        "type": "group",
                        "description": metadata.get("description", "No description")
                    })
                    
                    # Recursively scan the group's contents
                    scan_directory(item_path, item_rel_path)
                    
                except Exception as e:
                    logger.warning(f"Error loading group '{item_rel_path}': {e}")
            else:
                # Check for tool yaml files
                tool_yaml = os.path.join(item_path, "tool.yaml")
                tool_name_yaml = os.path.join(item_path, f"{item_name}.yaml")
                yaml_path = tool_yaml if os.path.exists(tool_yaml) else tool_name_yaml
                py_path = os.path.join(item_path, "tool.py")
                alt_py_path = os.path.join(item_path, f"{item_name}.py")
                
                if os.path.exists(yaml_path) and (os.path.exists(py_path) or os.path.exists(alt_py_path)):
                    # This is a tool
                    try:
                        with open(yaml_path, "r") as f:
                            metadata = yaml.safe_load(f) or {}
                        
                        # Skip disabled tools
                        if metadata.get("disabled", False):
                            continue
                        
                        # Add the tool to the list
                        entities.append({
                            "name": metadata.get("name", item_name),
                            "path": item_rel_path,
                            "type": "tool",
                            "description": metadata.get("description", "No description")
                        })
                    except Exception as e:
                        logger.warning(f"Error loading tool '{item_rel_path}': {e}")
                else:
                    # This might be a directory for nested tools, scan it
                    scan_directory(item_path, item_rel_path)
    
    # Start the recursive scan
    scan_directory(TOOLS_BASE_DIR)
    
    # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={entities}", file=sys.stderr)
    return entities


def import_tool_module(path: str) -> Any:
    """
    Dynamically import a tool module.
    
    Args:
        path: Path to the tool, which can include nested paths (e.g., "group/subtool")
        
    Returns:
        The imported module
        
    Raises:
        ImportError: If the module cannot be imported
        FileNotFoundError: If the implementation file doesn't exist
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}", file=sys.stderr)
    
    # Get the directory and name for this path
    dir_path = get_tool_dir(path)
    path_components = path.replace('/', os.sep).split(os.sep)
    name = path_components[-1]
    
    # Check for the implementation file first with the name, then legacy path
    tool_py_path = os.path.join(dir_path, f"{name}.py")
    if not os.path.exists(tool_py_path):
        tool_py_path = os.path.join(dir_path, "tool.py")
        if not os.path.exists(tool_py_path):
            logger.error(f"Tool implementation file not found for: {path}")
            # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: FileNotFoundError", file=sys.stderr)
            raise FileNotFoundError(f"Tool implementation file not found for: {path}")
    
    try:
        # Create a unique module name based on the path
        module_name = f"evai.tools.{path.replace('/', '_')}"
        
        # Create a module spec
        spec = importlib.util.spec_from_file_location(module_name, tool_py_path)
        
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


def run_tool(path: str, args=None, kwargs=None) -> Any:
    """
    Run a tool with the given arguments.
    
    Args:
        path: Path to the tool, which can include nested paths (e.g., "group/subtool")
        args: List of positional arguments (optional)
        kwargs: Dictionary of keyword arguments (optional)
        
    Returns:
        The result of the tool function
        
    Raises:
        ImportError: If the tool module cannot be imported
        AttributeError: If the tool function cannot be found
        ValueError: If the tool doesn't exist
        Exception: If the tool execution fails
    """
    # print(f"DEBUG: ENTER {inspect.currentframe().f_code.co_name} - path={path}, args={args}, kwargs={kwargs}", file=sys.stderr)
    
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    
    try:
        # Get the tool directory
        dir_path = get_tool_dir(path)
        
        # Load the metadata to verify this is a tool (not a group)
        metadata = load_tool_metadata(path)
        
        # Get the tool name from the path
        path_components = path.replace('/', os.sep).split(os.sep)
        name = path_components[-1]
        
        # Check if this is a group
        group_yaml = os.path.join(dir_path, "group.yaml")
        if os.path.exists(group_yaml):
            logger.error(f"Cannot run a group: {path}")
            raise ValueError(f"Cannot run a group: {path}")
        
        # Get the implementation file path
        py_path = os.path.join(dir_path, f"{name}.py")
        if not os.path.exists(py_path):
            # Try legacy path
            py_path = os.path.join(dir_path, "tool.py")
            if not os.path.exists(py_path):
                raise FileNotFoundError(f"Tool implementation not found for: {path}")
        
        # Import the module
        module_name = f"tool_{path.replace('/', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, py_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to create module spec for {py_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the appropriate function (tool_<name>)
        func_name = f"tool_{name}"
        if not hasattr(module, func_name):
            # Try to find any tool_* function
            tool_functions = [
                name for name, obj in inspect.getmembers(module)
                if inspect.isfunction(obj) and name.startswith('tool_')
            ]
            if not tool_functions:
                raise AttributeError(f"Tool module doesn't have any tool_* functions: {path}")
            func_name = tool_functions[0]
        
        func = getattr(module, func_name)
        
        # Get the function signature
        sig = inspect.signature(func)
        
        # Match arguments based on function signature
        # First by positional parameters
        bound_args = []
        if args:
            # Convert args to appropriate types based on function signature
            for i, (param_name, param) in enumerate(sig.parameters.items()):
                if i < len(args):
                    # Get the parameter type annotation
                    param_type = param.annotation
                    if param_type is inspect.Parameter.empty:
                        # No type annotation, use the arg as is
                        bound_args.append(args[i])
                    else:
                        # Try to convert the arg to the annotated type
                        try:
                            # Handle special cases for common types
                            if param_type is float or param_type is int:
                                bound_args.append(param_type(args[i]))
                            elif param_type is bool:
                                # Convert string to bool
                                value = str(args[i]).lower()
                                bound_args.append(value in ('true', 't', 'yes', 'y', '1'))
                            else:
                                # For other types, try direct conversion
                                bound_args.append(param_type(args[i]))
                        except (ValueError, TypeError):
                            # If conversion fails, use the original value
                            logger.warning(f"Could not convert argument {args[i]} to {param_type.__name__}")
                            bound_args.append(args[i])
        
        # Then by keyword parameters (if they match the function signature)
        filtered_kwargs = {}
        if kwargs:
            filtered_kwargs = {
                k: v for k, v in kwargs.items() 
                if k in sig.parameters
            }
        
        # Call the function
        if bound_args:
            result = func(*bound_args, **filtered_kwargs)
        else:
            result = func(**filtered_kwargs)
        
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - return={result}", file=sys.stderr)
        return result
    except (ImportError, AttributeError, FileNotFoundError, ValueError) as e:
        logger.error(f"Error running tool: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        # print(f"DEBUG: EXIT {inspect.currentframe().f_code.co_name} - EXCEPTION: {e}", file=sys.stderr)
        raise


def add_tool(path: str, metadata: Dict[str, Any], implementation: str) -> None:
    """
    Add a new tool or group.
    
    Args:
        path: Path to the tool or group, which can include nested paths (e.g., "group/subtool")
        metadata: Dictionary containing the metadata for the tool
        implementation: String containing the tool implementation code
    
    Raises:
        ValueError: If the metadata is invalid
        ValueError: If implementation is provided for a group
        OSError: If files cannot be written
    """
    # Get the directory for this path
    dir_path = get_tool_dir(path)
    
    # Get the path components
    path_components = path.replace('/', os.sep).split(os.sep)
    name = path_components[-1]
    
    # Validate metadata
    if not metadata:
        raise ValueError("Metadata cannot be empty")
    
    if metadata.get("name") != name:
        raise ValueError(f"Metadata name '{metadata.get('name')}' must match tool name '{name}'")
    
    # If this is a subtool, ensure parent directory has a group.yaml
    if len(path_components) > 1:
        parent_path = os.path.join(TOOLS_BASE_DIR, *path_components[:-1])
        parent_group_yaml = os.path.join(parent_path, "group.yaml")
        
        if not os.path.exists(parent_group_yaml):
            # Create minimal group metadata
            group_name = path_components[-2]
            group_metadata = {
                "name": group_name,
                "description": f"Group for {group_name} tools",
                "type": "group"
            }
            
            with open(parent_group_yaml, "w") as f:
                yaml.dump(group_metadata, f, default_flow_style=False, sort_keys=False)
            logger.debug(f"Created parent group metadata at {parent_group_yaml}")
    
    # Save the metadata
    save_tool_metadata(path, metadata)
    
    # If this is not a group, save the implementation
    if "arguments" in metadata or "options" in metadata or "params" in metadata:
        # This is a tool, save the implementation
        py_path = os.path.join(dir_path, f"{name}.py")
        with open(py_path, "w") as f:
            f.write(implementation)
        logger.debug(f"Saved tool implementation to {py_path}")
    elif implementation:
        # This is a group, shouldn't have implementation
        logger.warning(f"Implementation provided for group '{path}' will be ignored")


def edit_tool(path: str, metadata: Dict[str, Any] = None, implementation: str = None) -> None:
    """
    Edit an existing tool or group.
    
    Args:
        path: Path to the tool or group, which can include nested paths (e.g., "group/subtool")
        metadata: Dictionary containing the updated metadata (optional)
        implementation: String containing the updated implementation code (optional)
    
    Raises:
        FileNotFoundError: If the tool or group doesn't exist
        ValueError: If both metadata and implementation are None
        OSError: If files cannot be written
    """
    if metadata is None and implementation is None:
        raise ValueError("Either metadata or implementation must be provided")
    
    # Get the directory for this path
    dir_path = get_tool_dir(path)
    
    # Get the path components
    path_components = path.replace('/', os.sep).split(os.sep)
    name = path_components[-1]
    
    # Check if the tool or group exists
    try:
        existing_metadata = load_tool_metadata(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Tool or group '{path}' not found")
    
    # Update metadata if provided
    if metadata:
        # Merge with existing metadata, preserving fields not in the update
        updated_metadata = {**existing_metadata, **metadata}
        save_tool_metadata(path, updated_metadata)
        logger.debug(f"Updated metadata for '{path}'")
    
    # Update implementation if provided
    if implementation:
        is_group = False
        # Check if this is a group
        group_yaml = os.path.join(dir_path, "group.yaml")
        if os.path.exists(group_yaml):
            is_group = True
        
        if is_group:
            logger.warning(f"Implementation provided for group '{path}' will be ignored")
        else:
            py_path = os.path.join(dir_path, f"{name}.py")
            with open(py_path, "w") as f:
                f.write(implementation)
            logger.debug(f"Updated implementation for '{path}'")


def remove_tool(path: str) -> bool:
    """
    Remove a tool or group.
    
    Args:
        path: Path to the tool or group, which can include nested paths (e.g., "group/subtool")
        
    Returns:
        True if the tool or group was successfully removed
        
    Raises:
        ValueError: If the path is invalid
        FileNotFoundError: If the tool or group doesn't exist
    """
    if not path:
        raise ValueError("Path cannot be empty")
    
    # Get the directory for this path
    dir_path = get_tool_dir(path)
    
    # Check if the directory exists
    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Tool or group '{path}' not found")
    
    # Check if this is a group or a tool
    group_yaml = os.path.join(dir_path, "group.yaml")
    
    try:
        if os.path.exists(group_yaml):
            # This is a group, remove the entire directory
            shutil.rmtree(dir_path)
            logger.debug(f"Group directory removed: {dir_path}")
        else:
            # This is a tool, get the name
            path_components = path.replace('/', os.sep).split(os.sep)
            name = path_components[-1]
            
            # Remove the tool files
            yaml_path = os.path.join(dir_path, f"{name}.yaml")
            if not os.path.exists(yaml_path):
                # Try legacy path
                yaml_path = os.path.join(dir_path, "tool.yaml")
            py_path = os.path.join(dir_path, f"{name}.py")
            if not os.path.exists(py_path):
                # Try legacy path
                py_path = os.path.join(dir_path, "tool.py")
            
            if os.path.exists(yaml_path):
                os.remove(yaml_path)
                logger.debug(f"Tool metadata removed: {yaml_path}")
            if os.path.exists(py_path):
                os.remove(py_path)
                logger.debug(f"Tool implementation removed: {py_path}")
                
            # Check if the directory is now empty
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                logger.debug(f"Empty tool directory removed: {dir_path}")
        
        return True
    except OSError as e:
        logger.error(f"Failed to remove tool or group: {e}")
        raise