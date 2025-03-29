# evai/cli/user_commands.py
import click
import importlib.util
import logging
import json
import sys
from functools import partial
from typing import Dict, Any, List, Optional, Tuple, Union, cast
from evai.tool_storage import (
    list_tools,
    load_tool_metadata,
    run_tool
)

logger = logging.getLogger(__name__)

def get_click_type(type_str: str) -> Any:
    """Map metadata type strings to Click parameter types."""
    type_map = {
        "string": str,
        "integer": int,
        "float": float,
        "number": float,  # Handle "number" as float
        "boolean": bool
    }
    return type_map.get(type_str, str)


def load_tools_to_main_group(main_group: click.Group, section: str = "Tool Commands") -> None:
    """Load user-created tools into the main Click group.
    
    This function makes tools available as first-class commands in the CLI,
    so they can be called directly as 'evai <tool>' instead of 'evai tools run <tool>'.
    
    Built-in commands have precedence over tools with the same name.
    
    Args:
        main_group: The click group to add commands to
        section: The section label to use in help display
    """
    # Get all tools and groups
    entities = list_tools()
    
    # Handle groups and their subtools
    groups = [e for e in entities if e["type"] == "group"]
    for group in groups:
        group_path = group["path"]
        group_name = group["name"]
        
        # Skip if a command with this name already exists
        if group_name in main_group.commands:
            logger.warning(f"Skipping tool group '{group_name}' because a command with that name already exists.")
            continue
        
        # Create a new Click group with section information
        # Use AliasedGroup if available to support sections
        from evai.cli.cli import AliasedGroup
        if AliasedGroup is not None:
            new_group = AliasedGroup(name=group_name, 
                                help=group["description"],
                                section=section)
        else:
            # This code is unreachable but kept for completeness
            if False:  # type: ignore
                new_group = click.Group(name=group_name, help=group["description"])
            
        main_group.add_command(new_group)
        
        # Find all tools in this group
        group_tools = [e for e in entities if e["type"] == "tool" and e["path"].startswith(f"{group_path}/")]
        
        # Add each tool to the group
        for tool in group_tools:
            tool_path = tool["path"]
            # Get the tool name (last part of the path)
            tool_name = tool_path.split("/")[-1]
            
            # Skip if a command with this name already exists in the group
            if tool_name in new_group.commands:
                logger.warning(f"Skipping tool '{tool_path}' because a command with that name already exists in the group.")
                continue
            
            try:
                # Load the tool metadata
                metadata = load_tool_metadata(tool_path)
                
                # Skip disabled tools
                if metadata.get("disabled", False) or metadata.get("hidden", False):
                    continue
                
                # Create a Click command for this tool
                cmd = create_tool_command(tool_path, metadata, tool_name)
                # Set section if the command has this attribute
                if hasattr(cmd, 'section'):
                    cmd.section = section
                new_group.add_command(cmd)
            except Exception as e:
                logger.error(f"Error loading tool '{tool_path}': {e}")
                continue
    
    # Handle individual tools (not in groups)
    tools = [e for e in entities if e["type"] == "tool" and "/" not in e["path"]]
    for tool in tools:
        tool_path = tool["path"]
        tool_name = tool["name"]
        
        # Skip if a command with this name already exists
        if tool_name in main_group.commands:
            logger.warning(f"Skipping tool '{tool_name}' because a command with that name already exists.")
            continue
        
        try:
            # Load the tool metadata
            metadata = load_tool_metadata(tool_path)
            
            # Skip disabled or hidden tools
            if metadata.get("disabled", False) or metadata.get("hidden", False):
                continue
            
            # Create a Click command for this tool
            cmd = create_tool_command(tool_path, metadata, tool_name)
            # Set section if the command has this attribute
            if hasattr(cmd, 'section'):
                cmd.section = section
            main_group.add_command(cmd)
        except Exception as e:
            logger.error(f"Error loading tool '{tool_name}': {e}")
            continue

def create_tool_command(tool_path: str, metadata: Dict[str, Any], tool_name: str) -> click.Command:
    """Create a Click command for a tool."""
    description = metadata.get("description", "")
    
    # Get the arguments, options, and params from metadata
    arguments = metadata.get("arguments", [])
    options = metadata.get("options", [])
    params = metadata.get("params", [])
    
    # Function to run when the command is invoked
    def command_callback(*args: Any, **kwargs: Any) -> None:
        try:
            # Run the tool
            result = run_tool(tool_path, args=list(args), kwargs=kwargs)
            
            # Print the result
            if isinstance(result, dict):
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(result)
                
        except Exception as e:
            click.echo(f"Error running tool: {e}", err=True)
            sys.exit(1)
    
    # Create a Click command
    cmd = click.Command(name=tool_name, callback=command_callback, help=description)
    
    # Add arguments from 'arguments' field
    for i, arg in enumerate(arguments):
        arg_name = arg["name"]
        arg_type = get_click_type(arg.get("type", "string"))
        cmd.params.append(click.Argument([arg_name], type=arg_type))
    
    # Add options from 'options' field
    for opt in options:
        opt_name = opt["name"]
        opt_type = get_click_type(opt.get("type", "string"))
        opt_required = opt.get("required", False)
        opt_default = opt.get("default", None)
        cmd.params.append(click.Option(
            ["--" + opt_name], 
            type=opt_type, 
            required=opt_required, 
            default=opt_default, 
            help=opt.get("description", "")
        ))
    
    # If there are no arguments but we have params, convert first two required params to positional arguments
    # This is for backward compatibility with tools that only define params
    if not arguments and params:
        # Sort required params first
        required_params = sorted(
            [p for p in params if p.get("required", True)],
            key=lambda p: p.get("name", "")
        )
        
        # Use the first two required params as positional arguments
        for i, param in enumerate(required_params[:2]):
            param_name = param["name"]
            # Map 'number' type to 'float' for Click
            param_type = param.get("type", "string")
            if param_type == "number":
                param_type = "float"
            arg_type = get_click_type(param_type)
            cmd.params.append(click.Argument([param_name], type=arg_type))
        
        # Add remaining params as options
        for param in params:
            # Skip params that were already added as arguments
            if param in required_params[:2]:
                continue
                
            param_name = param["name"]
            # Map 'number' type to 'float' for Click
            param_type = param.get("type", "string")
            if param_type == "number":
                param_type = "float"
            opt_type = get_click_type(param_type)
            opt_required = param.get("required", True)
            opt_default = param.get("default", None)
            cmd.params.append(click.Option(
                ["--" + param_name], 
                type=opt_type, 
                required=opt_required, 
                default=opt_default, 
                help=param.get("description", "")
            ))
    
    return cmd