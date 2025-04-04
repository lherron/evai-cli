"""MCP resources for EVAI CLI."""

import logging
import os
from typing import Dict, Any, List, Optional, cast

try:
    from mcp.server.fastmcp import FastMCP
    import mcp.types as types
except ImportError:
    # Provide a helpful error message if MCP is not installed
    raise ImportError(
        "The MCP Python SDK is required for MCP server integration. "
        "Please install it with: pip install mcp"
    )

# Set up logging
logger = logging.getLogger(__name__)

# Define available resources
RESOURCES = {
    "project-file": types.ResourceTemplate(
        uriTemplate="file://{path}",
        name="Project File",
        description="Access file contents within the project",
    ),
    "config-file": types.Resource(
        uri=types.AnyUrl("config://evai.json"),
        name="EVAI Configuration",
        description="EVAI CLI configuration file",
        mimeType="application/json"
    )
}

def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path, "r") as f:
        return f.read()


def register_resources(mcp: FastMCP) -> None:
    """
    Register all available resources.
    
    Args:
        mcp: The MCP server instance
    """
    logger.debug("Registering resources")