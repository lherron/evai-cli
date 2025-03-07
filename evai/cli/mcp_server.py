"""
Default MCP server for EVAI CLI.

This server provides a simple MCP implementation that can be used with the EVAI CLI.
It exposes a tool for generating text using Claude and a prompt for interacting with Claude.
"""

import os
import anthropic
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("EVAI LLM")

# Check for API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Warning: ANTHROPIC_API_KEY environment variable is not set. Some functionality may be limited.")

def call_claude(prompt: str, max_tokens: int = 1000) -> str:
    """Call Claude Sonnet 3.7 directly.
    
    Args:
        prompt: The text prompt to send to Claude.
        max_tokens: Maximum number of tokens to generate.
        
    Returns:
        The text response from Claude.
    """
    if not api_key:
        return "Error: ANTHROPIC_API_KEY environment variable is not set"
    
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)
    
    # Call Claude Sonnet 3.7
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=max_tokens
    )
    
    # Return the text response
    return response.content[0].text

@mcp.tool()
def generate(prompt: str, max_tokens: int = 1000) -> str:
    """Generate text using Claude Sonnet 3.7.
    
    Args:
        prompt: The text prompt to send to Claude.
        max_tokens: Maximum number of tokens to generate.
        
    Returns:
        The text response from Claude.
    """
    return call_claude(prompt, max_tokens)

@mcp.prompt()
def default(text: str) -> list:
    """Default prompt for interacting with Claude.
    
    Args:
        text: The text to send to Claude.
        
    Returns:
        A list of messages for the prompt.
    """
    # Call Claude and get the response
    response = call_claude(text)
    
    # Return the messages
    return [
        {"role": "user", "content": text},
        {"role": "assistant", "content": response}
    ]

@mcp.resource("prompt://{text}")
def prompt_resource(text: str) -> str:
    """Resource for getting a response to a prompt.
    
    Args:
        text: The text to send to Claude.
        
    Returns:
        The text response from Claude.
    """
    return call_claude(text)

if __name__ == "__main__":
    # Run the MCP server
    mcp.run() 