"""
MCP server integration for EVAI CLI.

An stdio implementation of an MCP server.  It is spawned from MCP
clients (Claude Desktop, Claude Code, etc).  
"""

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
    run_lint_check,
    import_tool_module
)

# Import the new modules
from evai.mcp.prompts import register_prompts
from evai.mcp.tools import register_built_in_tools, register_tools, register_tool

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
        
        # Use the new modules for registration
        register_built_in_tools(self.mcp)
        register_prompts(self.mcp, self)
        register_tools(self.mcp)
        
        print(f"[DEBUG] Exiting EVAIServer.__init__", file=sys.stderr)
    
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

server = EVAIServer(mcp)