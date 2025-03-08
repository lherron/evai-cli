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
    def edit_tool_implementation_tool(path: str, implementation: str) -> Dict[str, Any]:
        """
        Edit the implementation of an existing tool.
        
        Args:
            path: The path to the tool to edit (e.g., "group/subtool")
            implementation: The new implementation code
            
        Returns:
            A dictionary with the status of the edit
        """
        logger.debug(f"Editing implementation for tool: {path}")
        try:
            # Get the name component from the path
            name = path.split('/')[-1]
            
            # Get the tool directory
            dir_path = get_tool_dir(path)
            
            # Check if tool exists by trying to load metadata
            try:
                metadata = load_tool_metadata(path)
            except FileNotFoundError:
                logger.error(f"Tool '{path}' does not exist")
                return {"status": "error", "message": f"Tool '{path}' does not exist"}
            
            # Determine the correct python file path
            py_path = os.path.join(dir_path, f"{name}.py")
            if not os.path.exists(py_path):
                py_path = os.path.join(dir_path, "tool.py")
                if not os.path.exists(py_path):
                    # Create a new implementation file
                    py_path = os.path.join(dir_path, f"{name}.py")
            
            # Write the new implementation
            with open(py_path, "w") as f:
                f.write(implementation)
            
            # Try to reload the module if it's already loaded
            try:
                from importlib import reload
                import sys
                
                # Get the module name
                module_name = f"evai.tools.{path.replace('/', '_')}"
                
                # If the module is already loaded, reload it
                if module_name in sys.modules:
                    reload(sys.modules[module_name])
                    
                logger.info(f"Reloaded implementation for tool '{path}'")
            except Exception as e:
                logger.warning(f"Failed to reload implementation for tool '{path}': {e}")
            
            result = {
                "status": "success",
                "message": f"Implementation for tool '{path}' updated successfully",
                "implementation_path": py_path
            }
            logger.debug(f"Successfully edited implementation for tool: {path}")
            return result
            
        except Exception as e:
            logger.error(f"Error editing tool implementation: {e}")
            return {"status": "error", "message": str(e)}
            
    @mcp.tool(name="edit_tool_metadata")
    def edit_tool_metadata_tool(path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit the metadata of an existing tool.
        
        Args:
            path: The path to the tool or group to edit (e.g., "group/subtool")
            metadata: The new metadata
            
        Returns:
            A dictionary with the status of the edit
        """
        logger.debug(f"Editing metadata for: {path}")
        try:
            # Get the name component from the path
            name = path.split('/')[-1]
            
            # Check if the tool or group exists
            try:
                existing_metadata = load_tool_metadata(path)
            except FileNotFoundError:
                logger.error(f"Tool or group '{path}' does not exist")
                return {"status": "error", "message": f"Tool or group '{path}' does not exist"}
            
            # Ensure the name field matches the tool name
            metadata["name"] = name
            
            # Update the metadata
            edit_tool(path, metadata=metadata)
            
            result = {
                "status": "success",
                "message": f"Metadata for '{path}' updated successfully"
            }
            logger.debug(f"Successfully edited metadata for: {path}")
            return result
            
        except Exception as e:
            logger.error(f"Error editing metadata: {e}")
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
                # Replace / with _ for MCP naming
                mcp_tool_name = tool_path.replace("/", "_")
                register_tool(mcp, tool_path, mcp_tool_name, metadata)
                
            except Exception as e:
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
        # Get the expected function parameters from the metadata
        params = []
        
        # First check for CLI arguments
        for arg in metadata.get("arguments", []):
            params.append({
                "name": arg["name"],
                "type": arg.get("type", "string"),
                "description": arg.get("description", ""),
                "required": True,
                "default": None
            })
        
        # Then check for CLI options
        for opt in metadata.get("options", []):
            params.append({
                "name": opt["name"],
                "type": opt.get("type", "string"),
                "description": opt.get("description", ""),
                "required": opt.get("required", False),
                "default": opt.get("default", None)
            })
        
        # Then check for MCP parameters
        for param in metadata.get("params", []):
            # Skip if this parameter is already defined as an argument or option
            if any(p["name"] == param["name"] for p in params):
                continue
                
            params.append({
                "name": param["name"],
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
                "required": param.get("required", True),
                "default": param.get("default", None)
            })
        
        # Define the tool wrapper function that will call our run_tool
        def tool_wrapper(**kwargs):
            logger.debug(f"Running tool {tool_path} with kwargs: {kwargs}")
            try:
                result = run_tool(tool_path, kwargs=kwargs)
                return result
            except Exception as e:
                logger.error(f"Error running tool {tool_path}: {e}")
                return {"status": "error", "message": str(e)}
        
        # Add metadata to the wrapper
        tool_wrapper.__name__ = mcp_tool_name
        tool_wrapper.__doc__ = metadata.get("description", f"Run the {tool_path} tool")
        
        # Register the tool with MCP
        mcp.tool(
            name=mcp_tool_name,
            description=metadata.get("description", ""),
            params=[
                {
                    "name": param["name"],
                    "type": param["type"],
                    "description": param.get("description", ""),
                    "required": param.get("required", True)
                }
                for param in params
            ]
        )(tool_wrapper)
        
        logger.debug(f"Successfully registered tool: {tool_path} as {mcp_tool_name}")
    except Exception as e:
        logger.error(f"Error registering tool '{tool_path}': {e}")
        raise