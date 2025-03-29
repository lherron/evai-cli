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


def register_resources(mcp: FastMCP, server: Any) -> None:
    """
    Register all available resources.
    
    Args:
        mcp: The MCP server instance
        server: The EVAIServer instance for file access
    """
    logger.debug("Registering resources")
    
    # Register file resource
    @mcp.resource("file://{path}")
    async def read_file(path: str) -> str:
        """
        Read file content from the specified path.
        
        Args:
            path: Path to the file to read
            
        Returns:
            The file content as a string
        """
        logger.debug(f"Reading file: {path}")
        try:
            # Read the file
            content = server.read_file(path)
            return str(content)
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise ValueError(f"Error reading file: {e}")
    
    # Register config resource
    @mcp.resource("config://evai.json")
    async def read_config() -> str:
        """
        Read EVAI configuration.
        
        Returns:
            The configuration as a JSON string
        """
        logger.debug("Reading EVAI configuration")
        try:
            # Get the configuration
            config = server.get_config()
            # Ensure we always return a string
            return str(config) if config is not None else "{}"
        except Exception as e:
            logger.error(f"Error reading configuration: {e}")
            raise ValueError(f"Error reading configuration: {e}")
    
    # Register env resource
    @mcp.resource("env://{name}")
    async def read_env_var(name: str) -> str:
        """
        Read environment variable.
        
        Args:
            name: Name of the environment variable
            
        Returns:
            The value of the environment variable
        """
        logger.debug(f"Reading environment variable: {name}")
        try:
            value = os.environ.get(name)
            if value is None:
                raise ValueError(f"Environment variable {name} not found")
            return value
        except Exception as e:
            logger.error(f"Error reading environment variable: {e}")
            raise ValueError(f"Error reading environment variable: {e}")
    
    logger.debug("Resources registered successfully") 