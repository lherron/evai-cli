"""LLM base command for EVAI CLI."""

import click
import asyncio
import os
import os.path
import sys
import traceback
import anthropic
import urllib.parse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rich_print
from rich.syntax import Syntax
from rich.theme import Theme
from rich.table import Table
from rich.box import ROUNDED
import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union, cast

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

# Function to extract the actual result value from MCP tool result
def extract_tool_result_value(result_str: str) -> str:
    """Extract the actual result value from MCP tool result string.
    
    Args:
        result_str: The raw result string from MCP tool execution.
        
    Returns:
        The extracted result value or the original string if extraction fails.
    """
    try:
        # Check if the result contains TextContent
        if "TextContent" in result_str and "text='" in result_str:
            # Extract the text value between text=' and '
            match = re.search(r"text='([^']*)'", result_str)
            if match:
                extracted_text = match.group(1)
                
                # Check if the extracted text is JSON
                if extracted_text.strip().startswith('{') and extracted_text.strip().endswith('}'):
                    try:
                        json_obj = json.loads(extracted_text)
                        # Format the JSON for better readability
                        if "tools" in json_obj and isinstance(json_obj["tools"], list):
                            # Special handling for tool list
                            tool_list = []
                            for tool in json_obj["tools"]:
                                tool_info = f"{tool.get('name', 'Unknown')}"
                                if "description" in tool:
                                    tool_info += f": {tool['description']}"
                                tool_list.append(tool_info)
                            return "\n- " + "\n- ".join(tool_list)
                        else:
                            # Return a formatted JSON string
                            return json.dumps(json_obj, indent=2)
                    except:
                        # If JSON parsing fails, return the extracted text
                        return extracted_text
                
                return extracted_text
        
        # If it's a JSON string, try to parse it
        if result_str.strip().startswith('{') and result_str.strip().endswith('}'):
            try:
                json_obj = json.loads(result_str)
                if isinstance(json_obj, dict):
                    # Return a formatted JSON string
                    return json.dumps(json_obj, indent=2)
            except:
                pass
                
        # Return the original string if no extraction method worked
        return result_str
    except Exception:
        # If any error occurs, return the original string
        return result_str

async def call_claude_directly(prompt: str, max_tokens: int = 1000, show_stop_reason: bool = False) -> str:
    """Call Claude Sonnet 3.7 directly without using MCP.
    
    Args:
        prompt: The text prompt to send to Claude.
        max_tokens: Maximum number of tokens to generate.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        The text response from Claude.
    """
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=api_key)
    
    # Call Claude Sonnet 3.7 - use synchronous API for simplicity
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=max_tokens
    )
    
    # Get the text response
    text_block = response.content[0]
    if text_block.type == "text":
        result = text_block.text
    else:
        result = str(text_block)
    
    # Add stop reason if requested
    if show_stop_reason:
        stop_reason = response.stop_reason
        stop_reason_message = ""
        
        if stop_reason == "end_turn":
            stop_reason_message = "Claude reached a natural stopping point."
        elif stop_reason == "max_tokens":
            stop_reason_message = "Response was truncated due to token limit."
            # Add a note to the response
            result += "\n\n[Note: This response was truncated due to reaching the maximum token limit.]"
        elif stop_reason == "stop_sequence":
            stop_reason_message = "Response ended due to a custom stop sequence."
            if hasattr(response, "stop_sequence") and response.stop_sequence:
                stop_reason_message += f" Stop sequence: {response.stop_sequence}"
        else:
            stop_reason_message = f"Unknown stop reason: {stop_reason}"
        
        # Add stop reason to the result
        result += f"\n\n---\nStop reason: {stop_reason} - {stop_reason_message}"
    
    return result

def call_claude_sync(prompt: str, max_tokens: int = 1000, show_stop_reason: bool = False) -> str:
    """Call Claude Sonnet 3.7 directly using synchronous API.
    
    Args:
        prompt: The text prompt to send to Claude.
        max_tokens: Maximum number of tokens to generate.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        The text response from Claude.
    """
    # Use asyncio to run the async function
    return asyncio.run(call_claude_directly(prompt, max_tokens, show_stop_reason))

async def async_run_mcp_command(prompt: str, show_tools: bool, server_params: StdioServerParameters, debug: bool = False, show_stop_reason: bool = False) -> str:
    """Async implementation of the MCP command execution with context re-injection.
    
    Args:
        prompt: The text prompt to send.
        show_tools: Whether to display detailed tool information.
        server_params: MCP server parameters.
        debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        The text response from the MCP server.
    """
    session = None
    client_context = None
    
    try:
        # Set up MCP session
        session, client_context = await async_setup_mcp_session(server_params)
        
        # Get Anthropic client
        client = await get_anthropic_client()
        
        # Fetch available tools
        claude_tools = await fetch_available_tools(session, show_tools)
        
        # Initialize conversation with the user's prompt
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Run the conversation loop
        final_response = await async_run_conversation_loop(session, client, claude_tools, messages, debug, show_stop_reason)
        
        return final_response

    except Exception as e:
        # Print the exception to stderr for debugging
        error_console.print(Panel(f"MCP Error: {str(e)}", title="[red bold]Error[/red bold]", border_style="red"))
        print(traceback.format_exc(), file=sys.stderr)
        return f"MCP Error: {str(e)}"
    finally:
        # Clean up resources
        if session:
            await session.__aexit__(None, None, None)
        if client_context:
            await client_context.__aexit__(None, None, None)

def run_llm_command_with_mcp(prompt: str, show_tools: bool = False, debug: bool = False, show_stop_reason: bool = False) -> str:
    """Call Claude through an MCP server integration.
    
    Args:
        prompt: The text prompt to send to Claude via MCP.
        show_tools: Whether to display detailed tool information.
        debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        The text response from Claude.
    """
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="uv",  # Executable
        args=[
        "run",
        "--directory",
        "/Users/lherron/projects/evai-cli",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/Users/lherron/projects/evai-cli/evai/mcp/server.py"
        ],  # Path to the MCP server script
        env=None  # Using default environment
    )
    
    # Run the async function and return the result
    return asyncio.run(async_run_mcp_command(prompt, show_tools, server_params, debug, show_stop_reason))

async def get_anthropic_client() -> anthropic.Anthropic:
    """Create and return an Anthropic client.
    
    Returns:
        An initialized Anthropic client.
        
    Raises:
        ValueError: If the ANTHROPIC_API_KEY environment variable is not set.
    """
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
    # Initialize and return Anthropic client
    return anthropic.Anthropic(api_key=api_key)

async def async_setup_mcp_session(server_params: StdioServerParameters) -> Tuple[ClientSession, Any]:
    """Set up an MCP session.
    
    Args:
        server_params: MCP server parameters.
        
    Returns:
        tuple: A tuple containing (session, client_context) for the MCP connection.
        
    Raises:
        Exception: If connection to the MCP server fails.
    """
    # Connect to the MCP server using context managers
    client_context = stdio_client(server_params)
    read, write = await client_context.__aenter__()
    session = ClientSession(read, write)
    await session.__aenter__()
    
    # Initialize the connection
    await session.initialize()
    
    return session, client_context

def print_tools_table(claude_tools: List[Any]) -> None:
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
        
async def fetch_available_tools(session: ClientSession, show_tools: bool = False) -> List[Any]:
    """Fetch available tools from the MCP server.
    
    Args:
        session: The MCP client session.
        show_tools: Whether to display detailed tool information.
        
    Returns:
        list: A list of available tools in Claude format.
    """
    tools_result = await session.list_tools()
    claude_tools: List[Any] = []
    if tools_result and hasattr(tools_result, 'tools'):
        tools_list = getattr(tools_result, 'tools', [])
        for tool in tools_list:
            claude_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
    
    print_tools_table(claude_tools)

    return claude_tools

async def call_claude_with_tools(client: Any, messages: List[Dict[str, Any]], claude_tools: List[Dict[str, Any]]) -> Any:
    """Call Claude API with the current message history and tools.
    
    Args:
        client: The Anthropic client.
        messages: The conversation message history.
        claude_tools: Available tools in Claude format.
        
    Returns:
        The response from Claude.
        
    Raises:
        Exception: If the API call fails.
    """
    try:
        # Call Claude with the current message history
        response = client.messages.create(
            model="claude-3-7-sonnet-latest",
            messages=messages,
            tools=claude_tools if claude_tools else None,
            max_tokens=10000
        )
        return response
    except Exception as e:
        print(f"[ERROR] Claude API error: {str(e)}", file=sys.stderr)
        # If we have a message format error, try to recover by simplifying the message history
        # if "messages" in str(e) and len(messages) > 1:
        #     # Keep only the initial user message
        #     simplified_messages = [messages[0]]
        #     response = client.messages.create(
        #         model="claude-3-7-sonnet-latest",
        #         messages=simplified_messages,
        #         tools=claude_tools if claude_tools else None,
        #         max_tokens=1000
        #     )
        #     return response
        raise

def async_process_claude_response(response: Any, final_response_parts: List[str]) -> Tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
    """Process Claude's response and prepare message content.
    
    Args:
        response: The response from Claude.
        final_response_parts: List to collect response parts.
        
    Returns:
        tuple: A tuple containing (assistant_message_content, has_tool_use, stop_reason_info).
    """
    # Debug log response
    print(f"[DEBUG] Claude response: {response}")
    
    # Check the stop reason
    stop_reason = response.stop_reason
    has_tool_use = stop_reason == "tool_use"
    
    # Create a dictionary to hold information about the stop reason
    stop_reason_info = {
        "reason": stop_reason,
        "message": "",
        "should_notify_user": False
    }
    
    # Process different stop reasons
    if stop_reason == "end_turn":
        stop_reason_info["message"] = "Claude reached a natural stopping point."
    elif stop_reason == "max_tokens":
        stop_reason_info["message"] = "Response was truncated due to token limit."
        stop_reason_info["should_notify_user"] = True
        # Add a note to the final response
        truncation_note = "\n\n[Note: This response was truncated due to reaching the maximum token limit.]"
        final_response_parts.append(truncation_note)
    elif stop_reason == "stop_sequence":
        stop_reason_info["message"] = f"Response ended due to a custom stop sequence."
        if hasattr(response, "stop_sequence") and response.stop_sequence:
            stop_reason_info["message"] += f" Stop sequence: {response.stop_sequence}"
    elif stop_reason == "tool_use":
        stop_reason_info["message"] = "Claude is requesting to use a tool."
    else:
        stop_reason_info["message"] = f"Response ended with unknown stop reason: {stop_reason}"
        stop_reason_info["should_notify_user"] = True
    
    # Log the stop reason
    error_console.print(f"[purple]Stop reason: {stop_reason_info['message']}[/purple]")
    
    # Process Claude's response
    assistant_message_content = []
    
    for content in response.content:
        if content.type == "text":
            final_response_parts.append(content.text)
            assistant_message_content.append({"type": "text", "text": content.text})
        elif content.type == "tool_use":
            # Extract tool call details
            tool_name = content.name
            tool_args = content.input
            tool_id = content.id
            
            # Add tool use to assistant message
            assistant_message_content.append({
                "type": "tool_use",
                "name": tool_name,
                "id": tool_id,
                "input": tool_args
            })
    
    return assistant_message_content, has_tool_use, stop_reason_info

async def async_execute_tool_calls(session: ClientSession, response: Any, final_response_parts: List[str]) -> List[Dict[str, Any]]:
    """Execute tool calls requested by Claude.
    
    Args:
        session: The MCP client session.
        response: The response from Claude containing tool calls.
        final_response_parts: List to collect response parts.
        
    Returns:
        list: A list of tool results content for the next user message.
    """
    # Create a new user message with tool results
    tool_results_content = []
    
    # Process each tool use request
    for content in response.content:
        if content.type == "tool_use":
            tool_name = content.name
            tool_args = content.input
            tool_id = content.id
            
            # Create a panel for tool execution
            tool_panel = Panel(
                f"[cyan]Arguments:[/cyan] {tool_args}",
                title=f"[yellow bold]Executing Tool: {tool_name}[/yellow bold]",
                border_style="yellow"
            )
            error_console.print(tool_panel)
            
            try:
                # Execute the tool call through MCP
                tool_result = await session.call_tool(tool_name, arguments=tool_args)
                
                # Unused variable - we kept it for future implementation but need a pass to satisfy mypy
                pass
                
                # Format tool result for display
                result_panel = Panel(
                    str(tool_result),
                    title=f"[cyan]Tool Result: {tool_name}[/cyan]",
                    border_style="cyan"
                )
                error_console.print(result_panel)
                
                # Extract the actual result value
                extracted_result = extract_tool_result_value(str(tool_result))
                
                # Add plain text result to final response (without Rich formatting)
                tool_response = f"\nTool: {tool_name}\nResult: {extracted_result}\n"
                final_response_parts.append(tool_response)
                
                # Add tool result to the content for the next user message
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(tool_result)
                })
            except Exception as tool_error:
                # Format error for display
                error_panel = Panel(
                    str(tool_error),
                    title=f"[red bold]Tool Error: {tool_name}[/red bold]",
                    border_style="red"
                )
                error_console.print(error_panel)
                
                # Add plain text error to final response (without Rich formatting)
                error_msg = f"\nTool: {tool_name}\nError: {str(tool_error)}\n"
                final_response_parts.append(error_msg)
                
                # Add error to the content for the next user message
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(tool_error)
                })
    
    return tool_results_content

async def async_run_conversation_loop(session: ClientSession, client: anthropic.Anthropic, claude_tools: List[Dict[str, Any]], messages: List[Dict[str, Any]], show_debug: bool = False, show_stop_reason: bool = False) -> str:
    """Run the main conversation loop with Claude.
    
    Args:
        session: The MCP client session.
        client: The Anthropic client.
        claude_tools: Available tools in Claude format.
        messages: Initial message history.
        show_debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        str: The final response from the conversation.
    """
    # Main conversation loop
    final_response_parts: List[str] = []
    conversation_active = True
    last_stop_reason_info = None
    
    while conversation_active:
        error_console.print(f"[purple]Calling Claude with {len(claude_tools)} available tools and {len(messages)} messages in history...[/purple]")
        
        # Debug: Print message structure before sending to Claude
        if show_debug:
            print(f"\n[DEBUG] Sending message structure to Claude:", file=sys.stderr)
            for i, msg in enumerate(messages):
                print(f"  Message {i} - Role: {msg['role']}", file=sys.stderr)
                if isinstance(msg['content'], list):
                    print(f"    Content is a list with {len(msg['content'])} items", file=sys.stderr)
                    for j, content_item in enumerate(msg['content']):
                        if isinstance(content_item, dict):
                            if content_item.get('type') == 'tool_use':
                                print(f"      Item {j}: tool_use - Name: {content_item.get('name')}, ID: {content_item.get('id', 'MISSING')}", file=sys.stderr)
                            elif content_item.get('type') == 'tool_result':
                                print(f"      Item {j}: tool_result - Tool Use ID: {content_item.get('tool_use_id', 'MISSING')}", file=sys.stderr)
                                content_preview = str(content_item.get('content', ''))[:50] + "..." if len(str(content_item.get('content', ''))) > 50 else str(content_item.get('content', ''))
                                print(f"        Content: {content_preview}", file=sys.stderr)
                            else:
                                print(f"      Item {j}: {content_item.get('type', 'unknown type')}", file=sys.stderr)
                        else:
                            print(f"      Item {j}: {type(content_item)}", file=sys.stderr)
                else:
                    content_preview = str(msg['content'])[:50] + "..." if len(str(msg['content'])) > 50 else str(msg['content'])
                    print(f"    Content: {content_preview}", file=sys.stderr)
        
        # Call Claude with the current message history
        response = await call_claude_with_tools(client, messages, claude_tools)
        
        # Process Claude's response
        assistant_message_content, has_tool_use, stop_reason_info = async_process_claude_response(response, final_response_parts)
        last_stop_reason_info = stop_reason_info
        
        # Add assistant's response to message history
        if assistant_message_content:
            assistant_message = {
                "role": "assistant",
                "content": assistant_message_content
            }
            messages.append(assistant_message)
            error_console.print(f"[purple]Added assistant response to message history. History now has {len(messages)} messages.[/purple]")
        
        # If the stop reason should be displayed to the user, show it
        if stop_reason_info["should_notify_user"]:
            error_console.print(Panel(
                stop_reason_info["message"],
                title="[yellow bold]Response Information[/yellow bold]",
                border_style="yellow"
            ))
        
        # If Claude requested to use tools, execute them and send results back
        if has_tool_use:
            error_console.print("[yellow bold]Claude requested tool calls, executing...[/yellow bold]")
            
            # Execute tool calls
            tool_results_content = await async_execute_tool_calls(session, response, final_response_parts)
            
            # Add the tool results as a new user message
            if tool_results_content:
                tool_results_message = {
                    "role": "user",
                    "content": tool_results_content
                }
                messages.append(tool_results_message)
                error_console.print(f"[purple]Added tool results to message history. History now has {len(messages)} messages.[/purple]")
            
            # Continue the conversation to get Claude's final response
            continue
        else:
            # No more tool calls, end the conversation
            error_console.print(f"[purple]No more tool calls, ending conversation. Final stop reason: {stop_reason_info['reason']}[/purple]")
            conversation_active = False
    
    # Combine all response parts
    final_response = "\n".join(final_response_parts)
    
    # Add stop reason information to the final response if requested
    if show_stop_reason and last_stop_reason_info:
        stop_reason_text = f"\n\n---\nStop reason: {last_stop_reason_info['reason']}"
        if last_stop_reason_info["message"]:
            stop_reason_text += f" - {last_stop_reason_info['message']}"
        final_response += stop_reason_text
    
    return final_response


@click.command()
@click.argument("prompt")
@click.option("--use-mcp", is_flag=True, help="Use MCP server integration instead of direct API call", default=True)
@click.option("--list-tools", is_flag=True, help="Display detailed information about available tools", default=False)
@click.option("--debug", is_flag=True, help="Show debug information", default=False)
@click.option("--show-stop-reason", is_flag=True, help="Show the stop reason in the output", default=False)
def llm(prompt: str, use_mcp: bool = True, list_tools: bool = False, debug: bool = False, show_stop_reason: bool = False) -> None:
    """Prompts Claude with configured tools.
    
    By default, calls Claude directly via the API. Use --use-mcp to use MCP server integration.
    """
    try:
        # Display the user prompt in a nice panel
        error_console.print(Panel(prompt, title="[green bold]User Prompt[/green bold]", border_style="green"))
        
        if use_mcp:
            # Use the MCP server integration
            error_console.print("[purple]Using MCP server integration...[/purple]")
            result = run_llm_command_with_mcp(prompt, list_tools, debug, show_stop_reason)
        else:
            # Use the synchronous function directly
            error_console.print("[purple]Using direct Claude API...[/purple]")
            result = call_claude_sync(prompt, show_stop_reason)
        
        # Check if the result starts with "Error:" or "MCP Error:"
        if result.startswith("Error:") or result.startswith("MCP Error:"):
            # Print error to stderr
            error_console.print(Panel(result, title="[red bold]Error[/red bold]", border_style="red"))
            sys.exit(1)
        else:
            # Print the result to stdout
            # Try to parse as markdown for better formatting
            try:
                # Display the result in a nice panel with markdown rendering
                console.print(Panel(Markdown(result), title="[blue]Claude Response[/blue]", border_style="blue"))
            except Exception:
                # Fallback to plain text if markdown parsing fails
                console.print(Panel(result, title="[blue]Claude Response[/blue]", border_style="blue"))
            
            # Also print the raw result for scripts that might be parsing the output
            # Make sure to strip any Rich formatting tags that might have been included
            # print(strip_rich_formatting(result))
            
    except Exception as e:
        # Print the exception to stderr for debugging
        print(f"Error in llm command: {str(e)}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        error_console.print(Panel(f"Error: {e}", title="[red bold]Error[/red bold]", border_style="red"))
        if "ANTHROPIC_API_KEY" not in os.environ:
            error_console.print("[red bold]Please set the ANTHROPIC_API_KEY environment variable to use the LLM command.[/red bold]")
        sys.exit(1)