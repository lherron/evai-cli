"""LLM base command for EVAI CLI."""

import click
import asyncio
import os
import sys
import traceback
import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rich_print
from rich.syntax import Syntax
from rich.theme import Theme
from rich.table import Table
from rich.box import ROUNDED
import asyncio

from evai.mcp_tools import MCPConfiguration, MCPServer
from evai.llm_interaction import (
    LLMSession,
    extract_tool_result_value,
)

# Create Rich console for stderr and stdout
console = Console()
error_console = Console(stderr=True)

# Custom theme for different message types
custom_theme = Theme({
    "user_prompt": "green bold",
    "assistant_response": "blue",
    "tool_name": "yellow bold",
    "tool_result": "cyan",
    "error": "red bold",
    "info": "purple"
})

# Create themed console
themed_console = Console(theme=custom_theme)

# Function to format text with Rich styling
def format_rich_text(text: str, style: Optional[str] = None) -> str:
    """Format text with Rich styling."""
    if style:
        return f"[{style}]{text}[/{style}]"
    return text

# Function to strip Rich formatting tags from text
def strip_rich_formatting(text: str) -> str:
    """Remove Rich formatting tags from text."""
    # Pattern to match Rich formatting tags like [tag]...[/tag]
    pattern = r'\[(.*?)\](.*?)\[/\1\]'
    
    # Replace each tag with just the content
    while re.search(pattern, text):
        text = re.sub(pattern, r'\2', text)
    
    return text

def print_tools_table(claude_tools: List[Any]) -> None:
    """Print a table of available tools.
    
    Args:
        claude_tools: List of tools to display.
    """
    # Create tool descriptions for the panel content
    tool_descriptions = []
    
    # Using Any type to handle different possible structures
    for tool in claude_tools:
        try:
            # Try accessing as a dictionary
            if hasattr(tool, 'get'):
                name = tool.get('name', 'Unknown')
                description = tool.get('description', '')
            # Try accessing as an object with attributes
            elif hasattr(tool, 'name'):
                name = getattr(tool, 'name', 'Unknown')
                description = getattr(tool, 'description', '')
            else:
                name = str(tool)
                description = ''
            
            # Add formatted tool information to the list
            tool_descriptions.append(f"[yellow bold]{name}[/yellow bold]: [cyan]{description}[/cyan]")
        except Exception:
            # Fallback for any other type
            tool_descriptions.append(f"[yellow bold]{str(tool)}[/yellow bold]")
    
    # Join all tool descriptions with newlines
    panel_content = "\n\n".join(tool_descriptions)
    
    # Create and display the panel with width set to expand to terminal width
    tools_panel = Panel(
        panel_content,
        title="[yellow bold]Available Tools[/yellow bold]",
        border_style="yellow",
        expand=True,  # Make panel expand to full width
        width=error_console.width  # Set width to console width
    )
    
    error_console.print(tools_panel)

def display_tool_calls(tool_calls: List[Dict[str, Any]]) -> None:
    """Display tool calls in a nice format.
    
    Args:
        tool_calls: List of tool call information.
    """
    if not tool_calls:
        return
        
    for tool_call in tool_calls:
        tool_name = tool_call.get("tool_name", "Unknown Tool")
        tool_args = tool_call.get("tool_args", {})
        error = tool_call.get("error")
        
        if error:
            # Format error panel
            error_panel = Panel(
                f"[cyan]Arguments:[/cyan] {tool_args}\n\n[red]Error:[/red] {error}",
                title=f"[red bold]Tool Error: {tool_name}[/red bold]",
                border_style="red"
            )
            error_console.print(error_panel)
        else:
            # Format result panel
            result = tool_call.get("result", "")
            extracted_result = tool_call.get("extracted_result", extract_tool_result_value(str(result)))
            
            result_panel = Panel(
                f"[cyan]Arguments:[/cyan] {tool_args}\n\n[cyan]Result:[/cyan] {extracted_result}",
                title=f"[yellow bold]Tool Request: {tool_name}[/yellow bold]",
                border_style="cyan"
            )
            error_console.print(result_panel)

async def llm_async(prompt: str, debug: bool = False, show_stop_reason: bool = False, allowed_tools: Optional[str] = None) -> Dict[str, Any]:
    """Async function to handle all LLM operations.
    
    Args:
        prompt: The user's prompt to send to the LLM
        debug: Whether to show debug information
        show_stop_reason: Whether to show the stop reason in the output
        allowed_tools: Optional comma-separated list of allowed tool names
        
    Returns:
        Dict containing the result of the LLM interaction
    """
    # Initialize configuration and load server settings
    error_console.print("[purple]Initializing LLM session with configured MCP servers...[/purple]")
    config = MCPConfiguration()
    
    # Load server configurations
    try:
        servers_config_path = os.getenv("EVAI_SERVERS_CONFIG", "servers_config.json")
        if debug:
            error_console.print(f"[purple]Using servers config from: {servers_config_path}[/purple]")
        server_config = config.load_config(servers_config_path)
        servers = [
            MCPServer(name, srv_config)
            for name, srv_config in server_config.get("mcpServers", {}).items()
        ]
        if not servers:
            error_console.print("[yellow]No MCP servers found in configuration. Proceeding without tools.[/yellow]")
    except FileNotFoundError:
        error_console.print(f"[yellow]Warning: {servers_config_path} not found. Proceeding without MCP servers.[/yellow]")
        servers = []
    except json.JSONDecodeError:
        error_console.print(f"[yellow]Warning: Invalid JSON in {servers_config_path}. Proceeding without MCP servers.[/yellow]")
        servers = []
    
    # Create LLM session
    session = LLMSession(servers)
    
    try:
        await session.start_servers()
        # Convert comma-separated string to list if provided
        allowed_tool_list = allowed_tools.split(",") if allowed_tools else None
        result = await session.send_request(
            prompt=prompt,
            debug=debug,
            show_stop_reason=show_stop_reason,
            allowed_tools=allowed_tool_list
        )
    finally:
        # await session.stop_servers()
        pass
        
    return result

@click.command()
@click.argument("prompt", type=str, default="What is the capital of France?")
@click.option("--debug", is_flag=True, help="Show debug information", default=False)
@click.option("--show-stop-reason", is_flag=True, help="Show the stop reason in the output", default=False)
@click.option("--allowed-tools", help="Comma-separated list of allowed tool names", default=None)
def llm(prompt: str, debug: bool = False, show_stop_reason: bool = False, allowed_tools: Optional[str] = None) -> None:
    """Prompts Claude with configured tools.
    
    Uses MCP servers configured in servers_config.json to provide tools integration.
    """
    print(f"*****************************************")
    print(f"******** LLM request: {prompt}")
    print(f"*****************************************")
    # Load environment variables from .env file
    load_dotenv()
    
    # Configure basic logging for CLI output
    import logging
    logging.basicConfig(
        level=logging.INFO if not debug else logging.DEBUG,
        format="%(message)s"  # Simpler format for CLI output
    ) 

    try:
        # Display the user prompt in a nice panel
        error_console.print(Panel(prompt, title="[green bold]User Prompt[/green bold]", border_style="green"))
        
        print(f"******** LLM request: {prompt}")
        # Run the async operations
        result = asyncio.run(llm_async(prompt, debug, show_stop_reason, allowed_tools))

        print(f"******** LLM result: {result}")
        # Check if the request was successful
        if not result["success"]:
            # Print error to stderr
            error_message = result.get("error", "Unknown error")
            error_console.print(Panel(error_message, title="[red bold]Error[/red bold]", border_style="red"))
            
            # Handle specific error cases
            if "ANTHROPIC_API_KEY" in error_message:
                error_console.print("[red bold]Please set the ANTHROPIC_API_KEY environment variable to use the LLM command.[/red bold]")
                
            sys.exit(1)

        # Display any tool calls
        if result.get("tool_calls"):
            display_tool_calls(result["tool_calls"])
        
        # Display the final response
        response_text = result.get("response", "")
        
        # Try to parse as markdown for better formatting
        try:
            # Display the result in a nice panel with markdown rendering
            console.print(Panel(Markdown(response_text), title="[blue]Claude Response[/blue]", border_style="blue"))
        except Exception:
            # Fallback to plain text if markdown parsing fails
            console.print(Panel(response_text, title="[blue]Claude Response[/blue]", border_style="blue"))
        
        # Show stop reason information if requested and available
        if show_stop_reason and result.get("stop_reason_info"):
            stop_reason_info = result["stop_reason_info"]
            if stop_reason_info.get("should_notify_user"):
                error_console.print(Panel(
                    stop_reason_info.get("message", ""),
                    title="[yellow bold]Response Information[/yellow bold]",
                    border_style="yellow"
                ))
        
        # Debug: show message history if requested
        if debug and result.get("messages"):
            debug_panel = Panel(
                f"Message history contains {len(result['messages'])} messages",
                title="[purple bold]Debug Information[/purple bold]",
                border_style="purple"
            )
            error_console.print(debug_panel)
            
    except Exception as e:
        # Print the exception to stderr for debugging
        print(f"Error in llm command: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        error_console.print(Panel(f"Error: {e}", title="[red bold]Error[/red bold]", border_style="red"))
        if "ANTHROPIC_API_KEY" not in os.environ:
            error_console.print("[red bold]Please set the ANTHROPIC_API_KEY environment variable to use the LLM command.[/red bold]")
        sys.exit(1)