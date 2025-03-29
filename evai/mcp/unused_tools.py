"""
Unused tools for MCP server.
"""

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP

import logging
from evai.tool_storage import (
    list_tools, 
    load_tool_metadata, 
    get_tool_dir
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
    async def call_llm(prompt: str, ctx: Any) -> Any:
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
                types.SamplingMessage(
                    role="user",
                    content=types.TextContent(type="text", text=prompt)
                )
            ],
            modelPreferences=types.ModelPreferences(hints=[types.ModelHint(name="claude-3-sonnet")]),
            includeContext="none",
            maxTokens=1000
        )
        # Send the sampling request to the client
        response = await ctx.send_request("sampling/createMessage", message)
        if hasattr(response, 'content') and hasattr(response.content, 'text'):
            return response.content.text
        # Ensure we always return a string
        return str(response) if response is not None else ""
    
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
            # Import is done here to avoid circular imports
            from evai.tool_storage import edit_tool
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
