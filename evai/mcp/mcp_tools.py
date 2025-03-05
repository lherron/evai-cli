"""MCP tools for EVAI CLI."""

import os
import sys
import logging
import inspect
from typing import Dict, Any, List, Optional, Awaitable

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
    run_tool, 
    load_tool_metadata, 
    get_tool_dir,
    save_tool_metadata,
    edit_tool_metadata,
    edit_tool_implementation,
    run_lint_check,
    import_tool_module
)

# Set up logging
logger = logging.getLogger(__name__)


def register_built_in_tools(mcp: FastMCP) -> None:
    """
    Register built-in tools like tool creation.
    
    Args:
        mcp: The MCP server instance
    """
    logger.debug("Registering built-in tools")
    
    @mcp.tool(name="call_llm")
    async def call_llm(prompt: str, ctx: Any) -> str:
        """Call the LLM with the given prompt via MCP sampling.
        
        Args:
            prompt: The text prompt to send to the LLM.
            ctx: The MCP context for sending requests.
        
        Returns:
            The text response from the LLM.
        """
        from mcp import types
        
        logger.debug("Calling LLM with prompt via MCP sampling")
        message = types.CreateMessageRequestParams(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt)
                )
            ],
            modelPreferences={"hints": [{"name": "claude-3-sonnet"}]},
            includeContext="none",
            maxTokens=1000
        )
        # Send the sampling request to the client
        response = await ctx.send_request("sampling/createMessage", message)
        return response.content.text
    
    @mcp.tool(name="list_tools")
    def list_available_tools() -> Dict[str, Any]:
        """
        List all available tools.
        
        Returns:
            A dictionary with the list of available tools
        """
        logger.debug("Listing available tools")
        try:
            tools_list = list_tools()
            logger.debug(f"Found {len(tools_list)} tools")
            return {
                "status": "success",
                "tools": tools_list
            }
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return {"status": "error", "message": str(e)}
    
    @mcp.tool(name="edit_tool_implementation")
    def edit_tool_implementation_tool(tool_name: str, implementation: str) -> Dict[str, Any]:
        """
        Edit the implementation of an existing tool.
        
        Args:
            tool_name: The name of the tool to edit
            implementation: The new implementation code
            
        Returns:
            A dictionary with the status of the edit
        """
        logger.debug(f"Editing implementation for tool: {tool_name}")
        try:
            # Get the tool directory
            tool_dir = get_tool_dir(tool_name)
            
            # Check if tool exists
            tool_py_path = os.path.join(tool_dir, "tool.py")
            if not os.path.exists(tool_py_path):
                logger.error(f"Tool '{tool_name}' does not exist")
                return {"status": "error", "message": f"Tool '{tool_name}' does not exist"}
            
            # Write the new implementation
            with open(tool_py_path, "w") as f:
                f.write(implementation)
            
            # Check if the tool is already registered
            try:
                # Re-import the module to update the implementation
                from importlib import reload
                import sys
                
                # Get the module name
                module_name = f"evai.tools.{tool_name}"
                
                # If the module is already loaded, reload it
                if module_name in sys.modules:
                    reload(sys.modules[module_name])
                    
                logger.info(f"Reloaded implementation for tool '{tool_name}'")
            except Exception as e:
                logger.warning(f"Failed to reload implementation for tool '{tool_name}': {e}")
            
            result = {
                "status": "success",
                "message": f"Implementation for tool '{tool_name}' updated successfully",
                "implementation_path": tool_py_path
            }
            logger.debug(f"Successfully edited implementation for tool: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error editing tool implementation: {e}")
            return {"status": "error", "message": str(e)}
            
    @mcp.tool(name="edit_tool_metadata")
    def edit_tool_metadata_tool(tool_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit the metadata of an existing tool.
        
        Args:
            tool_name: The name of the tool to edit
            metadata: The new metadata
            
        Returns:
            A dictionary with the status of the edit
        """
        logger.debug(f"Editing metadata for tool: {tool_name}")
        try:
            # Get the tool directory
            tool_dir = get_tool_dir(tool_name)
            
            # Check if tool exists
            tool_yaml_path = os.path.join(tool_dir, "tool.yaml")
            if not os.path.exists(tool_yaml_path):
                logger.error(f"Tool '{tool_name}' does not exist")
                return {"status": "error", "message": f"Tool '{tool_name}' does not exist"}
            
            # Ensure the name field matches the tool_name
            metadata["name"] = tool_name
            
            # Save the metadata
            save_tool_metadata(tool_dir, metadata)
            
            result = {
                "status": "success",
                "message": f"Metadata for tool '{tool_name}' updated successfully",
                "metadata_path": tool_yaml_path
            }
            logger.debug(f"Successfully edited metadata for tool: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error editing tool metadata: {e}")
            return {"status": "error", "message": str(e)}
    
    logger.debug("Built-in tools registered successfully")


def register_tools(mcp: FastMCP) -> None:
    """
    Register all available tools.
    
    Args:
        mcp: The MCP server instance
    """
    logger.debug("Registering custom tools")
    
    try:
        # Get all available tools
        tools = list_tools()
        
        # Register each tool
        for tool in tools:
            tool_name = tool["name"]
            tool_dir = tool["path"]
            
            try:
                # Load the tool metadata
                metadata = load_tool_metadata(tool_dir)
                
                # Register the tool
                register_tool(mcp, tool_name, metadata)
                
            except Exception as e:
                logger.error(f"Error registering tool '{tool_name}': {e}")
        
        logger.debug(f"Registered {len(tools)} custom tools")
        
    except Exception as e:
        logger.error(f"Error registering tools: {e}")
    

def register_tool(mcp: FastMCP, tool_name: str, metadata: Dict[str, Any]) -> None:
    """
    Register a tool as an MCP tool.
    
    Args:
        mcp: The MCP server instance
        tool_name: The name of the tool
        metadata: The tool metadata
    """
    logger.debug(f"Registering tool: {tool_name}")
    
    try:
        # Import the tool module using the existing function
        module = import_tool_module(tool_name)
        
        # Find any function that starts with 'tool_'
        tool_functions = [
            name for name, obj in inspect.getmembers(module)
            if inspect.isfunction(obj) and name.startswith('tool_')
        ]
        
        if not tool_functions:
            raise AttributeError(f"Tool module doesn't have any tool_* functions")
        
        # Use the first tool function found
        tool_function_name = tool_functions[0]
        logger.debug(f"Found tool function: {tool_function_name}")
        
        # Get the tool function and register it with MCP
        tool_function = getattr(module, tool_function_name)
        mcp.tool(name=tool_name)(tool_function)
        
        logger.debug(f"Successfully registered tool: {tool_name}")
    except Exception as e:
        logger.error(f"Error registering tool '{tool_name}': {e}")
        raise 