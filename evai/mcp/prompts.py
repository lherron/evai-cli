"""MCP prompts for EVAI CLI."""

import logging
import os
from typing import Dict, Any, List

try:
    from mcp.server.fastmcp import FastMCP
    import mcp.types as types
    from mcp.types import PromptMessage
except ImportError:
    # Provide a helpful error message if MCP is not installed
    raise ImportError(
        "The MCP Python SDK is required for MCP server integration. "
        "Please install it with: pip install mcp"
    )

# Set up logging
logger = logging.getLogger(__name__)

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


def register_prompts(mcp: FastMCP, server: Any) -> None:
    """
    Register all available prompts.
    
    Args:
        mcp: The MCP server instance
        server: The EVAIServer instance for file reading
    """
    logger.debug("Registering prompts")
    
    # Register the analyze-file prompt
    @mcp.prompt(name="analyze-file", description="Analyze a file")
    async def analyze_file(path: str) -> list[PromptMessage]:
        """
        Analyze a file and provide insights.
        
        Args:
            path: Path to the file to analyze
            
        Returns:
            A list of prompt messages
        """
        logger.debug(f"Analyzing file: {path}")
        try:
            # Read the file
            content = server.read_file(path)
            
            # Return the file content as a prompt message
            return [PromptMessage(role="user", content=types.TextContent(type="text", text=f"Please analyze this file:\n\n```\n{content}\n```"))]
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return [PromptMessage(role="user", content=types.TextContent(type="text", text=f"Error analyzing file: {e}"))]
    
    logger.debug("Prompts registered successfully") 