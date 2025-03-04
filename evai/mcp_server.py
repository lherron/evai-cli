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
except ImportError:
    # Provide a helpful error message if MCP is not installed
    raise ImportError(
        "The MCP Python SDK is required for MCP server integration. "
        "Please install it with: pip install mcp"
    )

# Add the parent directory to sys.path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from evai.command_storage import (
    list_commands, 
    run_command, 
    load_command_metadata, 
    get_command_dir,
    save_command_metadata,
    edit_command_metadata,
    edit_command_implementation,
    run_lint_check
)

# Set up logging
logger = logging.getLogger(__name__)
mcp = FastMCP("evai")


class EVAIServer:
    """MCP server for EVAI CLI custom commands."""
    
    def __init__(self, mcp: FastMCP):
        """
        Initialize the MCP server.
        
        Args:
            name: The name of the server
        """
        print(f"[DEBUG] Entering EVAIServer.__init__ with name=evai", file=sys.stderr)
        self.name = "evai"
        self.mcp = mcp
        self.commands = {}
        self._register_built_in_tools()
        self._register_commands()
        print(f"[DEBUG] Exiting EVAIServer.__init__", file=sys.stderr)
    
    def _register_built_in_tools(self) -> None:
        """Register built-in tools like command creation."""
        print(f"[DEBUG] Entering EVAIServer._register_built_in_tools", file=sys.stderr)
        

        @self.mcp.tool(name="list_commands")
        def list_available_commands() -> Dict[str, Any]:
            """
            List all available commands.
            
            Returns:
                A dictionary with the list of available commands
            """
            print(f"[DEBUG] Entering list_available_commands", file=sys.stderr)
            try:
                commands_list = list_commands()
                print(f"[DEBUG] Exiting list_available_commands with {len(commands_list)} commands", file=sys.stderr)
                return {
                    "status": "success",
                    "commands": commands_list
                }
            except Exception as e:
                logger.error(f"Error listing commands: {e}")
                print(f"[DEBUG] Exiting list_available_commands with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
        
        @self.mcp.tool(name="edit_command_implementation")
        def edit_command_implementation_tool(command_name: str, implementation: str) -> Dict[str, Any]:
            """
            Edit the implementation of an existing command.
            
            Args:
                command_name: The name of the command to edit
                implementation: The new implementation code
                
            Returns:
                A dictionary with the status of the edit
            """
            print(f"[DEBUG] Entering edit_command_implementation_tool with command_name={command_name}", file=sys.stderr)
            try:
                # Get the command directory
                command_dir = get_command_dir(command_name)
                
                # Check if command exists
                command_py_path = os.path.join(command_dir, "command.py")
                if not os.path.exists(command_py_path):
                    print(f"[DEBUG] Exiting edit_command_implementation_tool with error: Command does not exist", file=sys.stderr)
                    return {"status": "error", "message": f"Command '{command_name}' does not exist"}
                
                # Write the new implementation
                with open(command_py_path, "w") as f:
                    f.write(implementation)
                
                # Check if the command is already registered
                if command_name in self.commands:
                    # Reload the command module
                    try:
                        # Re-import the module to update the implementation
                        from importlib import reload
                        import sys
                        
                        # Get the module name
                        module_name = f"evai.commands.{command_name}"
                        
                        # If the module is already loaded, reload it
                        if module_name in sys.modules:
                            reload(sys.modules[module_name])
                            
                        logger.info(f"Reloaded implementation for command '{command_name}'")
                    except Exception as e:
                        logger.warning(f"Failed to reload implementation for command '{command_name}': {e}")
                        print(f"[DEBUG] Warning: Failed to reload implementation: {e}", file=sys.stderr)
                
                result = {
                    "status": "success",
                    "message": f"Implementation for command '{command_name}' updated successfully",
                    "implementation_path": command_py_path
                }
                print(f"[DEBUG] Exiting edit_command_implementation_tool with success", file=sys.stderr)
                return result
                
            except Exception as e:
                logger.error(f"Error editing command implementation: {e}")
                print(f"[DEBUG] Exiting edit_command_implementation_tool with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
                
        @self.mcp.tool(name="edit_command_metadata")
        def edit_command_metadata_tool(command_name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            """
            Edit the metadata of an existing command.
            
            Args:
                command_name: The name of the command to edit
                metadata: The new metadata
                
            Returns:
                A dictionary with the status of the edit
            """
            print(f"[DEBUG] Entering edit_command_metadata_tool with command_name={command_name}", file=sys.stderr)
            try:
                # Get the command directory
                command_dir = get_command_dir(command_name)
                
                # Check if command exists
                command_yaml_path = os.path.join(command_dir, "command.yaml")
                if not os.path.exists(command_yaml_path):
                    print(f"[DEBUG] Exiting edit_command_metadata_tool with error: Command does not exist", file=sys.stderr)
                    return {"status": "error", "message": f"Command '{command_name}' does not exist"}
                
                # Ensure the name field matches the command_name
                metadata["name"] = command_name
                
                # Save the metadata
                save_command_metadata(command_dir, metadata)
                
                # Update the command metadata in memory
                if command_name in self.commands:
                    self.commands[command_name] = metadata
                    
                    # Re-register the command tool to update parameter metadata
                    # First, remove the existing tool if it exists
                    if command_name in self.mcp.tool.registry:
                        del self.mcp.tool.registry[command_name]
                    
                    # Register the command again with updated metadata
                    self._register_command_tool(command_name, metadata)
                
                result = {
                    "status": "success",
                    "message": f"Metadata for command '{command_name}' updated successfully",
                    "metadata_path": command_yaml_path
                }
                print(f"[DEBUG] Exiting edit_command_metadata_tool with success", file=sys.stderr)
                return result
                
            except Exception as e:
                logger.error(f"Error editing command metadata: {e}")
                print(f"[DEBUG] Exiting edit_command_metadata_tool with exception: {e}", file=sys.stderr)
                return {"status": "error", "message": str(e)}
        
        print(f"[DEBUG] Exiting EVAIServer._register_built_in_tools", file=sys.stderr)
    
    def _register_commands(self) -> None:
        """Register all available commands as MCP tools."""
        print(f"[DEBUG] Entering EVAIServer._register_commands", file=sys.stderr)
        # Get all available commands
        commands = list_commands()
        
        for command in commands:
            command_name = command["name"]
            command_dir = command["path"]
            
            try:
                # Load the command metadata
                metadata = load_command_metadata(command_dir)
                
                # Skip commands with MCP integration disabled
                if not metadata.get("mcp_integration", {}).get("enabled", True):
                    logger.info(f"Skipping command '{command_name}' (MCP integration disabled)")
                    print(f"[DEBUG] Skipping command '{command_name}' (MCP integration disabled)", file=sys.stderr)
                    continue
                
                # Store the command metadata for later use
                self.commands[command_name] = metadata
                
                # Register the command as an MCP tool
                self._register_command_tool(command_name, metadata)
                
                logger.info(f"Registered command '{command_name}' as MCP tool")
                print(f"[DEBUG] Registered command '{command_name}' as MCP tool", file=sys.stderr)
            except Exception as e:
                logger.error(f"Error registering command '{command_name}': {e}")
                print(f"[DEBUG] Error registering command '{command_name}': {e}", file=sys.stderr)
        
        print(f"[DEBUG] Exiting EVAIServer._register_commands", file=sys.stderr)
    
    def _register_command_tool(self, command_name: str, metadata: Dict[str, Any]) -> None:
        """
        Register a command as an MCP tool.
        
        Args:
            command_name: The name of the command
            metadata: The command metadata
        """
        print(f"[DEBUG] Entering EVAIServer._register_command_tool with command_name={command_name}", file=sys.stderr)
        
        try:
            # Get the command directory
            command_dir = get_command_dir(command_name)
            command_py_path = os.path.join(command_dir, "command.py")
            
            if not os.path.exists(command_py_path):
                logger.error(f"Command implementation file not found: {command_py_path}")
                print(f"[DEBUG] Command implementation file not found: {command_py_path}", file=sys.stderr)
                return
            
            # Create a module spec
            spec = importlib.util.spec_from_file_location(
                f"evai.commands.{command_name}", command_py_path
            )
            
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {command_py_path}")
                print(f"[DEBUG] Failed to create module spec for {command_py_path}", file=sys.stderr)
                return
            
            # Create the module
            module = importlib.util.module_from_spec(spec)
            
            # Add the module to sys.modules
            sys.modules[spec.name] = module
            
            # Add the MCP instance to the module
            module.mcp = self.mcp
            
            # Execute the module
            spec.loader.exec_module(module)
            print(f"[DEBUG] Executed module: {module}", file=sys.stderr)
            if hasattr(module, f"cmd_{command_name}"):
                mcp.tool(name=command_name)(getattr(module, f"cmd_{command_name}"))
                logger.info(f"Registered command tool via register_tool function: {command_name}")
                print(f"[DEBUG] Registered command tool via register_tool function: {command_name}", file=sys.stderr)
            else:
                logger.error(f"Command module doesn't have a run function: {command_name}")
                print(f"[DEBUG] Command module doesn't have a run function: {command_name}", file=sys.stderr)
            
            # # Check if the module has a register_tool function
            # if hasattr(module, 'register_tool'):
            #     # Call the register_tool function with the MCP instance
            #     module.register_tool(self.mcp)
            #     logger.info(f"Registered command tool via register_tool function: {command_name}")
            #     print(f"[DEBUG] Registered command tool via register_tool function: {command_name}", file=sys.stderr)
            # elif hasattr(module, 'run'):
            #     # If there's no register_tool function but there is a run function,
            #     # manually register the run function as a tool
            #     run_func = module.run
            #     # Update the function's docstring with the command description
            #     run_func.__doc__ = metadata.get("description", f"Execute the {command_name} command")
                
            #     # Register the run function as a tool
            #     self.mcp.tool(name=command_name)(run_func)
                
            #     logger.info(f"Manually registered run function as tool: {command_name}")
            #     print(f"[DEBUG] Manually registered run function as tool: {command_name}", file=sys.stderr)
            # else:
            #     logger.error(f"Command module doesn't have a run function: {command_name}")
            #     print(f"[DEBUG] Command module doesn't have a run function: {command_name}", file=sys.stderr)
            
        except Exception as e:
            logger.error(f"Error registering command tool: {e}")
            print(f"[DEBUG] Error registering command tool: {e}", file=sys.stderr)
        
        print(f"[DEBUG] Exiting EVAIServer._register_command_tool", file=sys.stderr)
    
    def run(self) -> None:
        """Run the MCP server."""
        print(f"[DEBUG] Entering EVAIServer.run", file=sys.stderr)
        try:
            print(f"[DEBUG] Starting MCP server with name '{self.name}'", file=sys.stderr)
            self.mcp.run()
        except KeyboardInterrupt:
            logger.info("MCP server stopped by user")
            print(f"[DEBUG] MCP server stopped by user", file=sys.stderr)
        except Exception as e:
            logger.error(f"Error running MCP server: {e}")
            print(f"[DEBUG] Error running MCP server: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[DEBUG] Exiting EVAIServer.run", file=sys.stderr)


def create_server(name: str = "EVAI Commands") -> EVAIServer:
    """
    Create an MCP server for EVAI CLI custom commands.
    
    Args:
        name: The name of the server
        
    Returns:
        An EVAIServer instance
    """
    print(f"[DEBUG] Entering create_server with name={name}", file=sys.stderr)
    server = EVAIServer(name)
    print(f"[DEBUG] Exiting create_server", file=sys.stderr)
    return server


def run_server(name: str = "EVAI Commands") -> None:
    """
    Run an MCP server for EVAI CLI custom commands.
    
    Args:
        name: The name of the server
    """
    print(f"[DEBUG] Entering run_server with name={name}", file=sys.stderr)
    server = create_server(name)
    server.run()
    print(f"[DEBUG] Exiting run_server", file=sys.stderr) 

server = EVAIServer(mcp)