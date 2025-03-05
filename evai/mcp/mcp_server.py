"""MCP server integration for EVAI CLI."""

import os
import sys
import logging
import json
import subprocess
import importlib.util
from typing import Dict, Any, List, Optional, Tuple

try:
    from mcp.server.fastmcp import FastMCP, Context
    import mcp.types as types
    from mcp.types import PromptMessage

    # Define available prompts
    PROMPTS = {
        "git-commit": types.Prompt(
            name="git-commit",
            description="Generate a Git commit message",
            arguments=[
                types.PromptArgument(
                    name="changes",
                    description="Git diff or description of changes",
                    required=True
                )
            ],
        ),
        "explain-code": types.Prompt(
            name="explain-code",
            description="Explain how code works",
            arguments=[
                types.PromptArgument(
                    name="code",
                    description="Code to explain",
                    required=True
                ),
                types.PromptArgument(
                    name="language",
                    description="Programming language",
                    required=False
                )
            ],
        )
    }
except ImportError:
    # Provide a helpful error message if MCP is not installed
    raise ImportError(
        "The MCP Python SDK is required for MCP server integration. "
        "Please install it with: pip install mcp"
    )

# Add the parent directory to sys.path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from evai.tool_storage import (
    list_tools, 
    run_tool, 
    load_tool_metadata, 
    get_tool_dir,
    save_tool_metadata,
    edit_tool_metadata,
    edit_tool_implementation,
    run_lint_check
)

# Set up logging
logger = logging.getLogger(__name__)
mcp = FastMCP("evai")


class EVAIServer:
    """MCP server for EVAI CLI custom tools."""
    
    def __init__(self, mcp: FastMCP):
        """
        Initialize the MCP server.
        
        Args:
            name: The name of the server
        """
        print(f"[DEBUG] Entering EVAIServer.__init__ with name=evai", file=sys.stderr)
        self.name = "evai"
        self.mcp = mcp
        self.tools = {}
        self._register_built_in_tools()
        self._register_prompts()
        self._register_tools()
        print(f"[DEBUG] Exiting EVAIServer.__init__", file=sys.stderr)
    
    def _register_built_in_tools(self) -> None:
        """Register built-in tools like tool creation."""
        print(f"[DEBUG] Entering EVAIServer._register_built_in_tools", file=sys.stderr)
        

        @self.mcp.tool(name="list_tools")
        def list_available_tools() -> Dict[str, Any]:
            """
            List all available tools.
            
            Returns:
                A dictionary with the list of available tools
            """
            print(f"[DEBUG] Entering list_available_tools", file=sys.stderr)
            try:
                tools_list = list_tools()
                print(f"[DEBUG] Exiting list_available_tools with {len(tools_list)} tools", file=sys.stderr)
                return {
                    "status": "success",
                    "tools": tools_list
                }
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                print(f"[DEBUG] Exiting list_available_tools with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
        
        @self.mcp.tool(name="edit_tool_implementation")
        def edit_tool_implementation_tool(tool_name: str, implementation: str) -> Dict[str, Any]:
            """
            Edit the implementation of an existing tool.
            
            Args:
                tool_name: The name of the tool to edit
                implementation: The new implementation code
                
            Returns:
                A dictionary with the status of the edit
            """
            print(f"[DEBUG] Entering edit_tool_implementation_tool with tool_name={tool_name}", file=sys.stderr)
            try:
                # Get the tool directory
                tool_dir = get_tool_dir(tool_name)
                
                # Check if tool exists
                tool_py_path = os.path.join(tool_dir, "tool.py")
                if not os.path.exists(tool_py_path):
                    print(f"[DEBUG] Exiting edit_tool_implementation_tool with error: Tool does not exist", file=sys.stderr)
                    return {"status": "error", "message": f"Tool '{tool_name}' does not exist"}
                
                # Write the new implementation
                with open(tool_py_path, "w") as f:
                    f.write(implementation)
                
                # Check if the tool is already registered
                if tool_name in self.tools:
                    # Reload the tool module
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
                        print(f"[DEBUG] Warning: Failed to reload implementation: {e}", file=sys.stderr)
                
                result = {
                    "status": "success",
                    "message": f"Implementation for tool '{tool_name}' updated successfully",
                    "implementation_path": tool_py_path
                }
                print(f"[DEBUG] Exiting edit_tool_implementation_tool with success", file=sys.stderr)
                return result
                
            except Exception as e:
                logger.error(f"Error editing tool implementation: {e}")
                print(f"[DEBUG] Exiting edit_tool_implementation_tool with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
                
        @self.mcp.tool(name="edit_tool_metadata")
        def edit_tool_metadata_tool(tool_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            """
            Edit the metadata of an existing tool.
            
            Args:
                tool_name: The name of the tool to edit
                metadata: The new metadata
                
            Returns:
                A dictionary with the status of the edit
            """
            print(f"[DEBUG] Entering edit_tool_metadata_tool with tool_name={tool_name}", file=sys.stderr)
            try:
                # Get the tool directory
                tool_dir = get_tool_dir(tool_name)
                
                # Check if tool exists
                tool_yaml_path = os.path.join(tool_dir, "tool.yaml")
                if not os.path.exists(tool_yaml_path):
                    print(f"[DEBUG] Exiting edit_tool_metadata_tool with error: Tool does not exist", file=sys.stderr)
                    return {"status": "error", "message": f"Tool '{tool_name}' does not exist"}
                
                # Ensure the name field matches the tool_name
                metadata["name"] = tool_name
                
                # Save the metadata
                save_tool_metadata(tool_dir, metadata)
                
                # Check if the tool is already registered
                if tool_name in self.tools:
                    # Update the tool metadata
                    try:
                        # Update the tool metadata in the server
                        self._register_tool_tool(tool_name, metadata)
                        logger.info(f"Updated metadata for tool '{tool_name}'")
                    except Exception as e:
                        logger.warning(f"Failed to update metadata for tool '{tool_name}': {e}")
                        print(f"[DEBUG] Warning: Failed to update metadata: {e}", file=sys.stderr)
                
                result = {
                    "status": "success",
                    "message": f"Metadata for tool '{tool_name}' updated successfully",
                    "metadata_path": tool_yaml_path
                }
                print(f"[DEBUG] Exiting edit_tool_metadata_tool with success", file=sys.stderr)
                return result
                
            except Exception as e:
                logger.error(f"Error editing tool metadata: {e}")
                print(f"[DEBUG] Exiting edit_tool_metadata_tool with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
        
        print(f"[DEBUG] Exiting EVAIServer._register_built_in_tools", file=sys.stderr)
    
    def _register_tools(self) -> None:
        """Register all available tools."""
        print(f"[DEBUG] Entering EVAIServer._register_tools", file=sys.stderr)
        
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
                    self._register_tool_tool(tool_name, metadata)
                    
                except Exception as e:
                    logger.error(f"Error registering tool '{tool_name}': {e}")
                    print(f"[DEBUG] Error registering tool '{tool_name}': {e}", file=sys.stderr)
            
            print(f"[DEBUG] Registered {len(tools)} tools", file=sys.stderr)
            
        except Exception as e:
            logger.error(f"Error registering tools: {e}")
            print(f"[DEBUG] Error registering tools: {e}", file=sys.stderr)
        
        print(f"[DEBUG] Exiting EVAIServer._register_tools", file=sys.stderr)
    
    def _register_tool_tool(self, tool_name: str, metadata: Dict[str, Any]) -> None:
        """
        Register a tool as an MCP tool.
        
        Args:
            tool_name: The name of the tool
            metadata: The tool metadata
        """
        print(f"[DEBUG] Entering EVAIServer._register_tool_tool with tool_name={tool_name}", file=sys.stderr)
        
        # Get the tool directory
        tool_dir = get_tool_dir(tool_name)
        
        # Define the tool function
        @self.mcp.tool(name=tool_name)
        def tool_function(**kwargs) -> Dict[str, Any]:
            """
            Run the tool with the given arguments.
            
            Args:
                **kwargs: Arguments to pass to the tool
                
            Returns:
                The result of the tool
            """
            print(f"[DEBUG] Entering tool_function for tool '{tool_name}' with kwargs={kwargs}", file=sys.stderr)
            try:
                # Run the tool
                result = run_tool(tool_name, **kwargs)
                print(f"[DEBUG] Exiting tool_function for tool '{tool_name}' with result={result}", file=sys.stderr)
                return result
            except Exception as e:
                logger.error(f"Error running tool '{tool_name}': {e}")
                print(f"[DEBUG] Exiting tool_function for tool '{tool_name}' with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
        
        # Store the tool function
        self.tools[tool_name] = tool_function
        
        print(f"[DEBUG] Exiting EVAIServer._register_tool_tool", file=sys.stderr)
    
    def _register_prompts(self) -> None:
        """Register all available prompts."""
        print(f"[DEBUG] Entering EVAIServer._register_prompts", file=sys.stderr)
        
        # Register the analyze-file prompt
        @self.mcp.prompt(name="analyze-file", description="Analyze a file")
        async def analyze_file(path: str) -> list[PromptMessage]:
            """
            Analyze a file and provide insights.
            
            Args:
                path: Path to the file to analyze
                
            Returns:
                A list of prompt messages
            """
            print(f"[DEBUG] Entering analyze_file with path={path}", file=sys.stderr)
            try:
                # Read the file
                content = self.read_file(path)
                
                # Return the file content as a prompt message
                return [PromptMessage(role="user", content=f"Please analyze this file:\n\n```\n{content}\n```")]
            except Exception as e:
                logger.error(f"Error analyzing file: {e}")
                print(f"[DEBUG] Exiting analyze_file with exception: {e}", file=sys.stderr)
                return [PromptMessage(role="user", content=f"Error analyzing file: {e}")]
        
        print(f"[DEBUG] Exiting EVAIServer._register_prompts", file=sys.stderr)
    
    def read_file(self, path: str) -> str:
        """Read a file and return its contents."""
        with open(path, "r") as f:
            return f.read()
    
    def run(self) -> None:
        """Run the MCP server."""
        print(f"[DEBUG] Entering EVAIServer.run", file=sys.stderr)
        try:
            # Start the server
            self.mcp.run()
        except KeyboardInterrupt:
            print("Server stopped by user.")
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            print(f"Error running MCP server: {e}", file=sys.stderr)
        print(f"[DEBUG] Exiting EVAIServer.run", file=sys.stderr)


def create_server(name: str = "EVAI Tools") -> EVAIServer:
    """
    Create an MCP server for EVAI CLI custom tools.
    
    Args:
        name: The name of the server
        
    Returns:
        The MCP server
    """
    print(f"[DEBUG] Entering create_server with name={name}", file=sys.stderr)
    server = EVAIServer(mcp)
    print(f"[DEBUG] Exiting create_server", file=sys.stderr)
    return server


def run_server(name: str = "EVAI Tools") -> None:
    """
    Run an MCP server for EVAI CLI custom tools.
    
    Args:
        name: The name of the server
    """
    print(f"[DEBUG] Entering run_server with name={name}", file=sys.stderr)
    server = create_server(name)
    server.run()
    print(f"[DEBUG] Exiting run_server", file=sys.stderr)