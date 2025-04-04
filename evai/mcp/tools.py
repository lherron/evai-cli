"""MCP tools for EVAI CLI."""

import os
import sys
import logging
import inspect
import traceback
from typing import Dict, Any, List, Optional, Awaitable, Tuple, Union, cast, Callable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Provide a helpful error message if MCP is not installed
    raise ImportError(
        "The MCP Python SDK is required for MCP server integration. "
        "Please install it with: pip install mcp"
    )

from evai.tool_storage import (
    list_tools, 
    run_tool,  # Do not remove, used in register_tool
    load_tool_metadata
)

# Set up logging
logger = logging.getLogger(__name__)



def register_tools(mcp: FastMCP) -> None:
    """
    Register all available tools.
    
    Args:
        mcp: The MCP server instance
    """
    logger.debug("Registering custom tools")
    
    try:
        # Get all available tools and groups
        entities = list_tools()
        
        # Filter for tools only (not groups)
        tools = [entity for entity in entities if entity["type"] == "tool"]
        
        # Register each tool
        for tool in tools:
            tool_path = tool["path"]
            
            try:
                # Load the tool metadata
                metadata = load_tool_metadata(tool_path)
                
                # Skip disabled tools
                if metadata.get("disabled", False):
                    logger.debug(f"Skipping disabled tool: {tool_path}")
                    continue
                
                # Skip tools that have MCP integration disabled
                if not metadata.get("mcp_integration", {}).get("enabled", True):
                    logger.debug(f"Skipping tool with MCP integration disabled: {tool_path}")
                    continue
                
                # Register the tool with a unique name based on its path
                # Replace / and - with _ for MCP naming
                mcp_tool_name = tool_path.replace("/", "_").replace("-", "_")
                register_tool(mcp, tool_path, mcp_tool_name, metadata)
                
            except Exception as e:
                # Print the error stack trace
                logger.error(traceback.format_exc())
                logger.error(f"Error registering tool '{tool_path}': {e}")
        
        logger.debug(f"Registered {len(tools)} custom tools")
        
    except Exception as e:
        logger.error(f"Error registering tools: {e}")
    

def register_tool(mcp: FastMCP, tool_path: str, mcp_tool_name: str, metadata: Dict[str, Any]) -> None:
    """
    Register a tool as an MCP tool.
    
    Args:
        mcp: The MCP server instance
        tool_path: The path to the tool
        mcp_tool_name: The name to use for the MCP tool
        metadata: The tool metadata
    """
    logger.debug(f"Registering tool: {tool_path} as {mcp_tool_name}")
    
    try:
        # Import the tool module to get the actual function signature
        from evai.tool_storage import import_tool_module, run_tool
        
        # Get the tool name from the path
        path_components = tool_path.replace('/', os.sep).split(os.sep)
        name = path_components[-1]
        
        # Import the module
        module = import_tool_module(tool_path)
        
        # Find the appropriate function (tool_<name>)
        func_name = f"tool_{name}"
        if not hasattr(module, func_name):
            # Try to find any tool_* function
            tool_functions = [
                name for name, obj in inspect.getmembers(module)
                if inspect.isfunction(obj) and name.startswith('tool_')
            ]
            if not tool_functions:
                raise AttributeError(f"Tool module doesn't have any tool_* functions: {tool_path}")
            func_name = tool_functions[0]
        
        # Get the actual tool function
        tool_func = getattr(module, func_name)
        
        # Get the function signature
        sig = inspect.signature(tool_func)
        
        # Build parameter string with type annotations and default values
        param_str = []
        for param_name, param in sig.parameters.items():
            param_def = param_name
            if param.annotation is not inspect.Parameter.empty:
                # Handle different types of annotations
                if hasattr(param.annotation, "__name__"):
                    param_def += f": {param.annotation.__name__}"
                else:
                    # For complex types like Union, List, etc.
                    param_def += f": '{param.annotation}'"
            if param.default is not inspect.Parameter.empty:
                param_def += f" = {repr(param.default)}"
            param_str.append(param_def)
        
        # Build the return type annotation
        return_annotation = ""
        if sig.return_annotation is not inspect.Parameter.empty and sig.return_annotation is not None:
            if hasattr(sig.return_annotation, "__name__"):
                return_annotation = f" -> {sig.return_annotation.__name__}"
            else:
                # Handle more complex return annotations
                return_annotation = f" -> '{sig.return_annotation}'"
        
        # Check if the tool function has a 'ctx' parameter for MCP context
        has_ctx_param = 'ctx' in sig.parameters
        
        # Create the wrapper function code
        wrapper_code = f"""
def {mcp_tool_name}({', '.join(param_str)}){return_annotation}:
    \"\"\"
    {metadata.get('description', f'Run the {tool_path} tool')}
    \"\"\"
    logger.debug(f"Running tool {tool_path}")
    try:
        # Convert all arguments to a kwargs dict
        kwargs = locals().copy()
        # Remove the function reference from kwargs
        kwargs.pop('{mcp_tool_name}', None)
        
        # If the original function expects a ctx parameter but it's not provided,
        # we'll pass the MCP context from the wrapper's context
        {'# Pass ctx if needed' if has_ctx_param else '# No ctx parameter needed'}
        
        result = run_tool('{tool_path}', kwargs=kwargs)
        return result
    except Exception as e:
        logger.error(f"Error running tool {tool_path}: {{e}}")
        return {{"status": "error", "message": str(e)}}
"""
        
        # Create a local namespace for the exec
        local_namespace = {
            'logger': logger,
            'run_tool': run_tool
        }
        print(wrapper_code)
        # Execute the wrapper code to create the function
        exec(wrapper_code, globals(), local_namespace)
        
        # Get the created wrapper function
        wrapper_func = local_namespace[mcp_tool_name]
        
        # Copy the docstring from the original function if available
        if tool_func.__doc__:
            wrapper_func.__doc__ = tool_func.__doc__
        else:
            wrapper_func.__doc__ = metadata.get("description", f"Run the {tool_path} tool")
        
        # Register the tool with MCP
        # Pass the function directly as a callable
        func_tool = mcp.tool(
            name=mcp_tool_name,
            description=metadata.get("description", "")
        )
        func_tool(wrapper_func) # type: ignore
        
        logger.debug(f"Successfully registered tool: {tool_path} as {mcp_tool_name}")
    except Exception as e:
        logger.error(f"Error registering tool '{tool_path}': {e}")
        raise