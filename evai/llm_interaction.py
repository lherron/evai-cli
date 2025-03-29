"""LLM interaction library for EVAI CLI.

This module handles LLM and MCP server interactions, returning structured results
without directly printing to the console.
"""

import asyncio
import json
import logging
import os
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types

# Configure logging
logger = logging.getLogger(__name__)

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

async def fetch_available_tools(session: ClientSession) -> List[Dict[str, Any]]:
    """Fetch available tools from the MCP server.
    
    Args:
        session: The MCP client session.
        
    Returns:
        list: A list of available tools in Claude format.
    """
    tools_result = await session.list_tools()
    claude_tools: List[Dict[str, Any]] = []
    if tools_result and hasattr(tools_result, 'tools'):
        tools_list = getattr(tools_result, 'tools', [])
        for tool in tools_list:
            claude_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
    
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
        logger.error(f"Claude API error: {str(e)}")
        raise

async def process_claude_response(response: Any) -> Dict[str, Any]:
    """Process Claude's response and prepare message content.
    
    Args:
        response: The response from Claude.
        
    Returns:
        Dictionary containing processed response information.
    """
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
    elif stop_reason == "stop_sequence":
        stop_reason_info["message"] = f"Response ended due to a custom stop sequence."
        if hasattr(response, "stop_sequence") and response.stop_sequence:
            stop_reason_info["message"] += f" Stop sequence: {response.stop_sequence}"
    elif stop_reason == "tool_use":
        stop_reason_info["message"] = "Claude is requesting to use a tool."
    else:
        stop_reason_info["message"] = f"Response ended with unknown stop reason: {stop_reason}"
        stop_reason_info["should_notify_user"] = True
    
    logger.debug(f"Stop reason: {stop_reason_info['message']}")
    
    # Process Claude's response
    assistant_message_content = []
    final_response_parts = []
    
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
    
    return {
        "assistant_message_content": assistant_message_content,
        "has_tool_use": has_tool_use,
        "stop_reason_info": stop_reason_info,
        "final_response_parts": final_response_parts
    }

async def execute_tool_calls(session: ClientSession, response: Any) -> Dict[str, Any]:
    """Execute tool calls requested by Claude.
    
    Args:
        session: The MCP client session.
        response: The response from Claude containing tool calls.
        
    Returns:
        Dictionary containing tool results and response information.
    """
    # Create a new user message with tool results
    tool_results_content = []
    tool_calls = []
    final_response_parts = []
    
    # Process each tool use request
    for content in response.content:
        if content.type == "tool_use":
            tool_name = content.name
            tool_args = content.input
            tool_id = content.id
            
            try:
                # Execute the tool call through MCP
                logger.debug(f"Executing Tool: {tool_name}...")
                tool_result = await session.call_tool(tool_name, arguments=tool_args)
                
                # Extract the actual result value
                extracted_result = extract_tool_result_value(str(tool_result))
                
                # Add plain text result to final response
                tool_response = f"\nTool: {tool_name}\nResult: {extracted_result}\n"
                final_response_parts.append(tool_response)
                
                # Add tool result to the content for the next user message
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(tool_result)
                })
                
                # Add tool information for return data
                tool_calls.append({
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_id": tool_id,
                    "result": str(tool_result),
                    "extracted_result": extracted_result,
                    "error": None
                })
            except Exception as tool_error:
                # Add plain text error to final response
                error_msg = f"\nTool: {tool_name}\nError: {str(tool_error)}\n"
                final_response_parts.append(error_msg)
                
                # Add error to the content for the next user message
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(tool_error)
                })
                
                # Add tool error information for return data
                tool_calls.append({
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_id": tool_id,
                    "result": None,
                    "extracted_result": None,
                    "error": str(tool_error)
                })
    
    return {
        "tool_results_content": tool_results_content,
        "tool_calls": tool_calls,
        "final_response_parts": final_response_parts
    }

async def run_conversation_loop(session: ClientSession, client: anthropic.Anthropic, claude_tools: List[Dict[str, Any]], messages: List[Dict[str, Any]], debug: bool = False, show_stop_reason: bool = False) -> Dict[str, Any]:
    """Run the main conversation loop with Claude.
    
    Args:
        session: The MCP client session.
        client: The Anthropic client.
        claude_tools: Available tools in Claude format.
        messages: Initial message history.
        debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        Dictionary containing the conversation results and information.
    """
    # Main conversation loop
    final_response_parts: List[str] = []
    conversation_active = True
    last_stop_reason_info = None
    all_tool_calls = []
    
    while conversation_active:
        logger.debug(f"Calling Claude with {len(claude_tools)} available tools and {len(messages)} messages in history...")
        
        # Debug: Log message structure before sending to Claude
        if debug:
            logger.debug(f"Sending message structure to Claude:")
            for i, msg in enumerate(messages):
                logger.debug(f"  Message {i} - Role: {msg['role']}")
                if isinstance(msg['content'], list):
                    logger.debug(f"    Content is a list with {len(msg['content'])} items")
                    for j, content_item in enumerate(msg['content']):
                        if isinstance(content_item, dict):
                            if content_item.get('type') == 'tool_use':
                                logger.debug(f"      Item {j}: tool_use - Name: {content_item.get('name')}, ID: {content_item.get('id', 'MISSING')}")
                            elif content_item.get('type') == 'tool_result':
                                logger.debug(f"      Item {j}: tool_result - Tool Use ID: {content_item.get('tool_use_id', 'MISSING')}")
                                content_preview = str(content_item.get('content', ''))[:50] + "..." if len(str(content_item.get('content', ''))) > 50 else str(content_item.get('content', ''))
                                logger.debug(f"        Content: {content_preview}")
                            else:
                                logger.debug(f"      Item {j}: {content_item.get('type', 'unknown type')}")
                        else:
                            logger.debug(f"      Item {j}: {type(content_item)}")
                else:
                    content_preview = str(msg['content'])[:50] + "..." if len(str(msg['content'])) > 50 else str(msg['content'])
                    logger.debug(f"    Content: {content_preview}")
        
        # Call Claude with the current message history
        response = await call_claude_with_tools(client, messages, claude_tools)
        
        # Process Claude's response
        response_data = await process_claude_response(response)
        assistant_message_content = response_data["assistant_message_content"]
        has_tool_use = response_data["has_tool_use"]
        stop_reason_info = response_data["stop_reason_info"]
        final_response_parts.extend(response_data["final_response_parts"])
        
        last_stop_reason_info = stop_reason_info
        
        # Add assistant's response to message history
        if assistant_message_content:
            assistant_message = {
                "role": "assistant",
                "content": assistant_message_content
            }
            messages.append(assistant_message)
            logger.debug(f"Added assistant response to message history. History now has {len(messages)} messages.")
        
        # If Claude requested to use tools, execute them and send results back
        if has_tool_use:
            logger.debug("Claude requested tool calls, executing...")
            
            # Execute tool calls
            tool_result_data = await execute_tool_calls(session, response)
            tool_results_content = tool_result_data["tool_results_content"]
            tool_calls = tool_result_data["tool_calls"]
            final_response_parts.extend(tool_result_data["final_response_parts"])
            
            # Add tool calls to the collection of all tool calls
            all_tool_calls.extend(tool_calls)
            
            # Add the tool results as a new user message
            if tool_results_content:
                tool_results_message = {
                    "role": "user",
                    "content": tool_results_content
                }
                messages.append(tool_results_message)
                logger.debug(f"Added tool results to message history. History now has {len(messages)} messages.")
            
            # Continue the conversation to get Claude's final response
            continue
        else:
            # No more tool calls, end the conversation
            logger.debug(f"No more tool calls, ending conversation. Final stop reason: {stop_reason_info['reason']}")
            conversation_active = False
    
    # Combine all response parts
    final_response = "\n".join(final_response_parts)
    
    # Add stop reason information to the final response if requested
    if show_stop_reason and last_stop_reason_info:
        stop_reason_text = f"\n\n---\nStop reason: {last_stop_reason_info['reason']}"
        if last_stop_reason_info["message"]:
            stop_reason_text += f" - {last_stop_reason_info['message']}"
        final_response += stop_reason_text
    
    # Return a structured result
    return {
        "success": True,
        "response": final_response,
        "error": None,
        "messages": messages,
        "tool_calls": all_tool_calls,
        "stop_reason_info": last_stop_reason_info,
        "final_response_parts": final_response_parts
    }

async def async_run_mcp_command(prompt: str, server_params: StdioServerParameters, debug: bool = False, show_stop_reason: bool = False) -> Dict[str, Any]:
    """Async implementation of the MCP command execution with context re-injection.
    
    Args:
        prompt: The text prompt to send.
        server_params: MCP server parameters.
        debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.
        
    Returns:
        Dictionary containing the conversation results and information.
    """
    session = None
    client_context = None
    
    try:
        # Set up MCP session
        session, client_context = await async_setup_mcp_session(server_params)
        
        # Get Anthropic client
        client = await get_anthropic_client()
        
        # Fetch available tools
        claude_tools = await fetch_available_tools(session)
        
        # Initialize conversation with the user's prompt
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Run the conversation loop
        result = await run_conversation_loop(session, client, claude_tools, messages, debug, show_stop_reason)
        
        return result

    except Exception as e:
        logger.exception("MCP Error")
        return {
            "success": False,
            "response": None,
            "error": f"MCP Error: {str(e)}",
            "messages": None,
            "tool_calls": None,
            "stop_reason_info": None,
            "final_response_parts": None
        }
    finally:
        # Clean up resources
        if session:
            await session.__aexit__(None, None, None)
        if client_context:
            await client_context.__aexit__(None, None, None)

def create_mcp_server_params() -> StdioServerParameters:
    """Create server parameters for MCP.
    
    Returns:
        MCP server parameters.
    """
    return StdioServerParameters(
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

async def execute_llm_request_async(
    prompt: str,
    use_mcp: bool,
    server_params: Optional[StdioServerParameters] = None,
    debug: bool = False,
    show_stop_reason: bool = False
) -> Dict[str, Any]:
    """
    Executes an LLM request, either directly or via MCP.

    Args:
        prompt: The text prompt to send to the LLM.
        use_mcp: Whether to use MCP server integration.
        server_params: MCP server parameters (required if use_mcp is True).
        debug: Whether to show debug information.
        show_stop_reason: Whether to show the stop reason in the output.

    Returns:
        A dictionary containing the structured result:
        {
            "success": bool,
            "response": Optional[str], # Final text response
            "error": Optional[str],
            "tool_calls": Optional[List[Dict]], # List of tool call details
            "stop_reason_info": Optional[Dict], # Info about the final stop reason
            "messages": Optional[List[Dict]] # Full conversation history (for debug)
        }
    """
    try:
        if use_mcp:
            if not server_params:
                raise ValueError("server_params are required when use_mcp is True")
            # Call the refactored MCP command logic
            return await async_run_mcp_command(prompt, server_params, debug, show_stop_reason)
        else:
            # Call the refactored direct command logic
            direct_response = await call_claude_directly(prompt, show_stop_reason=show_stop_reason)
            # For simplicity, assume call_claude_directly returns only the text for now
            return {
                "success": True,
                "response": direct_response,
                "error": None,
                "tool_calls": None,
                "stop_reason_info": None, # Direct calls don't have the same stop reason structure easily accessible here yet
                "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": direct_response}] # Simplified history
            }
    except Exception as e:
        logger.exception("Error during LLM request execution")
        return {
            "success": False,
            "response": None,
            "error": str(e),
            "tool_calls": None,
            "stop_reason_info": None,
            "messages": None
        }

def execute_llm_request(
    prompt: str,
    use_mcp: bool,
    server_params: Optional[StdioServerParameters] = None,
    debug: bool = False,
    show_stop_reason: bool = False
) -> Dict[str, Any]:
    """
    Synchronous wrapper for execute_llm_request_async.
    
    See execute_llm_request_async for parameter and return details.
    """
    return asyncio.run(execute_llm_request_async(
        prompt=prompt,
        use_mcp=use_mcp,
        server_params=server_params,
        debug=debug,
        show_stop_reason=show_stop_reason
    )) 