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
import httpx
from mcp.client.stdio import stdio_client
from mcp import types
from contextlib import AsyncExitStack
import shutil
from dotenv import load_dotenv
# Configure logging
logger = logging.getLogger(__name__)


class MCPTool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self, name: str, description: str, input_schema: dict[str, Any]
    ) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: dict[str, Any] = input_schema

    def format_for_llm(self) -> str:
        """Format tool information for LLM.

        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                arg_desc = (
                    f"- {param_name}: {param_info.get('description', 'No description')}"
                )
                if param_name in self.input_schema.get("required", []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)

        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args_desc)}
"""


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.load_env()
        self.api_key = os.getenv("LLM_API_KEY")

    @staticmethod
    def load_env() -> None:
        """Load environment variables from .env file."""
        load_dotenv()

    @staticmethod
    def load_config(file_path: str) -> dict[str, Any]:
        """Load server configuration from JSON file.

        Args:
            file_path: Path to the JSON configuration file.

        Returns:
            Dict containing server configuration.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            JSONDecodeError: If configuration file is invalid JSON.
        """
        with open(file_path, "r") as f:
            return json.load(f)

    @property
    def llm_api_key(self) -> str:
        """Get the LLM API key.

        Returns:
            The API key as a string.

        Raises:
            ValueError: If the API key is not found in environment variables.
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in environment variables")
        return self.api_key




class MCPServer:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.stdio_context: Any | None = None
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack | None = None
        self._stack_task = None
        self._process = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env={**os.environ, **self.config["env"]}
            if self.config.get("env")
            else None,
        )
        try:
            # Create a new exit stack for each initialization
            self.exit_stack = AsyncExitStack()
            # Store the current task so we can ensure cleanup happens in the same task
            self._stack_task = asyncio.current_task()
            
            # Enter the stdio client context
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            
            # Enter the client session context
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            # Store session and mark as initialized
            self.session = session
            self._initialized = True
            
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            # Cleanup if initialization fails
            if self.exit_stack:
                try:
                    await self.exit_stack.aclose()
                except Exception as close_err:
                    logging.warning(f"Error closing exit stack during initialization cleanup: {close_err}")
                self.exit_stack = None
            raise

    async def list_tools(self) -> list[Any]:
        """List available tools from the server.

        Returns:
            A list of available tools.

        Raises:
            RuntimeError: If the server is not initialized.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                logging.info("Tools:")
                for tool in item[1]:
                    logging.info(f"Tool: name='{tool.name}' description='{tool.description}'")
                    tools.append(MCPTool(name=tool.name, description=tool.description, input_schema=tool.inputSchema))

        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            retries: Number of retry attempts.
            delay: Delay between retries in seconds.

        Returns:
            Tool execution result.

        Raises:
            RuntimeError: If server is not initialized.
            Exception: If tool execution fails after all retries.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                logging.info(f"Executing {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)

                return result

            except Exception as e:
                attempt += 1
                logging.warning(
                    f"Error executing tool: {e}. Attempt {attempt} of {retries}."
                )
                if attempt < retries:
                    logging.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("Max retries reached. Failing.")
                    raise

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            # If not initialized, nothing to clean up
            if not self._initialized:
                return
                
            try:
                # Check if we're in the same task that created the exit stack
                current_task = asyncio.current_task()
                if self._stack_task != current_task:
                    logging.warning(
                        f"Cleanup attempted in different task than initialization. "
                        f"Stack task: {self._stack_task}, current task: {current_task}"
                    )
                
                # Close resources regardless of task
                if self.session:
                    self.session = None
                
                # Close exit stack if it exists
                if self.exit_stack:
                    try:
                        # Handle cancel scope errors by using a shield
                        await asyncio.shield(self.exit_stack.aclose())
                    except asyncio.CancelledError:
                        logging.warning(f"Cancel operation during cleanup of server {self.name}")
                    except Exception as stack_err:
                        logging.warning(f"Error closing exit stack for server {self.name}: {stack_err}")
                    
                    # Always set to None to allow garbage collection
                    self.exit_stack = None
                
                # Clean up remaining attributes  
                self.stdio_context = None
                self._stack_task = None
                self._initialized = False
                
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")
                # Ensure initialization state is reset even on error
                self._initialized = False







class LLMClient:
    """Manages communication with the LLM provider."""

    def __init__(self, api_key: str) -> None:
        self.api_key: str = api_key

    def get_response(self, messages: list[dict[str, str]]) -> str:
        """Get a response from the LLM.

        Args:
            messages: A list of message dictionaries.

        Returns:
            The LLM's response as a string.

        Raises:
            httpx.RequestError: If the request to the LLM fails.
        """
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "messages": messages,
            "model": "llama-3.2-90b-vision-preview",
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 1,
            "stream": False,
            "stop": None,
        }

        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.RequestError as e:
            error_message = f"Error getting LLM response: {str(e)}"
            logging.error(error_message)

            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code
                logging.error(f"Status code: {status_code}")
                logging.error(f"Response details: {e.response.text}")

            return (
                f"I encountered an error: {error_message}. "
                "Please try again or rephrase your request."
            )






class LLMSession:
    """Orchestrates the interaction between user, LLM, and tools."""

    def __init__(self, servers: list[MCPServer]) -> None:
        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.servers: list[MCPServer] = servers
        self.llm_client = LLMClient(api_key)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.initialized: bool = False

    async def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True

        """Initialize all MCPServer instances if not already initialized."""
        for server in self.servers:
            if server.session is None:
                await server.initialize()

    async def cleanup_servers(self) -> None:
        """Clean up all servers properly."""
        if not self.initialized:
            return

        cleanup_errors = []
        
        # Gather all servers that need cleanup
        servers_to_cleanup = [server for server in self.servers if server.session is not None]
        
        # Clean up each server, collecting any errors
        for server in servers_to_cleanup:
            try:
                await server.cleanup()
            except Exception as e:
                error_msg = f"Warning during cleanup of server {server.name}: {e}"
                logging.warning(error_msg)
                cleanup_errors.append(error_msg)
        
        # Set initialized to False regardless of cleanup errors
        self.initialized = False
        
        # If all cleanups had errors and we had servers to clean up, log a summary
        if cleanup_errors and len(cleanup_errors) == len(servers_to_cleanup):
            logging.error(f"All server cleanups failed: {len(cleanup_errors)} errors")

    async def process_llm_response(self, llm_response: str) -> str:
        """Process the LLM response and execute tools if needed.

        Args:
            llm_response: The response from the LLM.

        Returns:
            The result of tool execution or the original response.
        """
        import json

        try:
            tool_call = json.loads(llm_response)
            if "tool" in tool_call and "arguments" in tool_call:
                logging.info(f"Executing tool: {tool_call['tool']}")
                logging.info(f"With arguments: {tool_call['arguments']}")

                for server in self.servers:
                    tools = await server.list_tools()
                    if any(tool.name == tool_call["tool"] for tool in tools):
                        try:
                            result = await server.execute_tool(
                                tool_call["tool"], tool_call["arguments"]
                            )

                            if isinstance(result, dict) and "progress" in result:
                                progress = result["progress"]
                                total = result["total"]
                                percentage = (progress / total) * 100
                                logging.info(
                                    f"Progress: {progress}/{total} "
                                    f"({percentage:.1f}%)"
                                )

                            return f"Tool execution result: {result}"
                        except Exception as e:
                            error_msg = f"Error executing tool: {str(e)}"
                            logging.error(error_msg)
                            return error_msg

                return f"No server found with tool: {tool_call['tool']}"
            return llm_response
        except json.JSONDecodeError:
            return llm_response

    async def start(self) -> None:
        """Main chat session handler."""
        try:
            for server in self.servers:
                try:
                    await server.initialize()
                except Exception as e:
                    logging.error(f"Failed to initialize server: {e}")
                    await self.cleanup_servers()
                    return

            all_tools = []
            for server in self.servers:
                tools = await server.list_tools()
                all_tools.extend(tools)

            tools_description = "\n".join([tool.format_for_llm() for tool in all_tools])

            system_message = (
                "You are a helpful assistant with access to these tools:\n\n"
                f"{tools_description}\n"
                "Choose the appropriate tool based on the user's question. "
                "If no tool is needed, reply directly.\n\n"
                "IMPORTANT: When you need to use a tool, you must ONLY respond with "
                "the exact JSON object format below, nothing else:\n"
                "{\n"
                '    "tool": "tool-name",\n'
                '    "arguments": {\n'
                '        "argument-name": "value"\n'
                "    }\n"
                "}\n\n"
                "After receiving a tool's response:\n"
                "1. Transform the raw data into a natural, conversational response\n"
                "2. Keep responses concise but informative\n"
                "3. Focus on the most relevant information\n"
                "4. Use appropriate context from the user's question\n"
                "5. Avoid simply repeating the raw data\n\n"
                "Please use only the tools that are explicitly defined above."
            )

            messages = [{"role": "system", "content": system_message}]

            while True:
                try:
                    user_input = input("You: ").strip().lower()
                    if user_input in ["quit", "exit"]:
                        logging.info("\nExiting...")
                        break

                    messages.append({"role": "user", "content": user_input})

                    llm_response = self.llm_client.get_response(messages)
                    logging.info("\nAssistant: %s", llm_response)

                    result = await self.process_llm_response(llm_response)

                    if result != llm_response:
                        messages.append({"role": "assistant", "content": llm_response})
                        messages.append({"role": "system", "content": result})

                        final_response = self.llm_client.get_response(messages)
                        logging.info("\nFinal response: %s", final_response)
                        messages.append(
                            {"role": "assistant", "content": final_response}
                        )
                    else:
                        messages.append({"role": "assistant", "content": llm_response})

                except KeyboardInterrupt:
                    logging.info("\nExiting...")
                    break

        finally:
            await self.cleanup_servers()

    async def send_request(self, prompt: str, debug: bool = False, show_stop_reason: bool = False) -> Dict[str, Any]:
        """Execute an LLM request with tool use independently of the chat loop.

        Args:
            prompt: The text prompt to send to the LLM.
            debug: Whether to show debug information.
            show_stop_reason: Whether to include the stop reason in the output.

        Returns:
            A dictionary containing the structured result:
            {
                "success": bool,
                "response": Optional[str],
                "error": Optional[str],
                "tool_calls": List[Dict],
                "stop_reason_info": Dict,
                "messages": List[Dict]
            }
        """
        try:
            # Ensure servers are initialized
            await self.initialize()

            # Collect tools from all servers and map tool names to servers
            all_tools = []
            tool_to_server = {}
            for server in self.servers:
                tools = await server.list_tools()
                for tool in tools:
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    }
                    all_tools.append(tool_dict)
                    tool_to_server[tool.name] = server

            # Initialize conversation history
            messages = [{"role": "user", "content": prompt}]
            final_response_parts = []
            tool_calls = []
            conversation_active = True
            last_stop_reason_info = None

            # Conversation loop
            while conversation_active:
                if debug:
                    logger.debug(f"Calling Anthropic with {len(messages)} messages and {len(all_tools)} tools")

                # Call Anthropic API
                response = self.client.messages.create(
                    model="claude-3-7-sonnet-latest",
                    messages=messages,
                    tools=all_tools,
                    max_tokens=4000
                )

                # Process response
                assistant_content = []
                for content in response.content:
                    if content.type == "text":
                        assistant_content.append({"type": "text", "text": content.text})
                        final_response_parts.append(content.text)
                    elif content.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "name": content.name,
                            "id": content.id,
                            "input": content.input
                        })

                if assistant_content:
                    messages.append({"role": "assistant", "content": assistant_content})

                # Handle tool calls
                if response.stop_reason == "tool_use":
                    tool_results_content = []
                    for content in response.content:
                        if content.type == "tool_use":
                            tool_name = content.name
                            tool_args = content.input
                            tool_id = content.id
                            server = tool_to_server.get(tool_name)

                            if server:
                                try:
                                    result = await server.execute_tool(tool_name, tool_args)
                                    extracted_result = extract_tool_result_value(str(result))
                                    final_response_parts.append(f"Tool: {tool_name}\nResult: {extracted_result}")
                                    tool_results_content.append({
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": str(result)
                                    })
                                    tool_calls.append({
                                        "tool_name": tool_name,
                                        "tool_args": tool_args,
                                        "result": extracted_result
                                    })
                                except Exception as e:
                                    error_msg = f"Error executing tool {tool_name}: {str(e)}"
                                    final_response_parts.append(error_msg)
                                    tool_results_content.append({
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": error_msg
                                    })
                                    tool_calls.append({
                                        "tool_name": tool_name,
                                        "tool_args": tool_args,
                                        "error": str(e)
                                    })
                            else:
                                error_msg = f"No server found for tool: {tool_name}"
                                final_response_parts.append(error_msg)
                                tool_results_content.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": error_msg
                                })

                    if tool_results_content:
                        messages.append({"role": "user", "content": tool_results_content})
                else:
                    conversation_active = False
                    last_stop_reason_info = {"reason": response.stop_reason}

            # Combine response parts
            final_response = "\n".join(final_response_parts)
            if show_stop_reason and last_stop_reason_info:
                final_response += f"\n\nStop reason: {last_stop_reason_info['reason']}"

            await self.cleanup_servers()

            return {
                "success": True,
                "response": final_response,
                "error": None,
                "tool_calls": tool_calls,
                "stop_reason_info": last_stop_reason_info,
                "messages": messages
            }

        except Exception as e:
            logger.exception("Error in send_request")
            return {
                "success": False,
                "response": None,
                "error": str(e),
                "tool_calls": [],
                "stop_reason_info": None,
                "messages": messages if 'messages' in locals() else []
            }










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

# async def call_claude_directly(prompt: str, max_tokens: int = 1000, show_stop_reason: bool = False) -> str:
#     """Call Claude Sonnet 3.7 directly without using MCP.
    
#     Args:
#         prompt: The text prompt to send to Claude.
#         max_tokens: Maximum number of tokens to generate.
#         show_stop_reason: Whether to show the stop reason in the output.
        
#     Returns:
#         The text response from Claude.
#     """
#     # Check for API key
#     api_key = os.environ.get("ANTHROPIC_API_KEY")
#     if not api_key:
#         raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
#     # Initialize Anthropic client
#     client = anthropic.Anthropic(api_key=api_key)
    
#     # Call Claude Sonnet 3.7 - use synchronous API for simplicity
#     response = client.messages.create(
#         model="claude-3-7-sonnet-20250219",
#         messages=[{
#             "role": "user",
#             "content": prompt
#         }],
#         max_tokens=max_tokens
#     )
    
#     # Get the text response
#     text_block = response.content[0]
#     if text_block.type == "text":
#         result = text_block.text
#     else:
#         result = str(text_block)
    
#     # Add stop reason if requested
#     if show_stop_reason:
#         stop_reason = response.stop_reason
#         stop_reason_message = ""
        
#         if stop_reason == "end_turn":
#             stop_reason_message = "Claude reached a natural stopping point."
#         elif stop_reason == "max_tokens":
#             stop_reason_message = "Response was truncated due to token limit."
#             # Add a note to the response
#             result += "\n\n[Note: This response was truncated due to reaching the maximum token limit.]"
#         elif stop_reason == "stop_sequence":
#             stop_reason_message = "Response ended due to a custom stop sequence."
#             if hasattr(response, "stop_sequence") and response.stop_sequence:
#                 stop_reason_message += f" Stop sequence: {response.stop_sequence}"
#         else:
#             stop_reason_message = f"Unknown stop reason: {stop_reason}"
        
#         # Add stop reason to the result
#         result += f"\n\n---\nStop reason: {stop_reason} - {stop_reason_message}"
    
#     return result

# def call_claude_sync(prompt: str, max_tokens: int = 1000, show_stop_reason: bool = False) -> str:
#     """Call Claude Sonnet 3.7 directly using synchronous API.
    
#     Args:
#         prompt: The text prompt to send to Claude.
#         max_tokens: Maximum number of tokens to generate.
#         show_stop_reason: Whether to show the stop reason in the output.
        
#     Returns:
#         The text response from Claude.
#     """
#     # Use asyncio to run the async function
#     return asyncio.run(call_claude_directly(prompt, max_tokens, show_stop_reason))

# async def get_anthropic_client() -> anthropic.Anthropic:
#     """Create and return an Anthropic client.
    
#     Returns:
#         An initialized Anthropic client.
        
#     Raises:
#         ValueError: If the ANTHROPIC_API_KEY environment variable is not set.
#     """
#     # Check for API key
#     api_key = os.environ.get("ANTHROPIC_API_KEY")
#     if not api_key:
#         raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
#     # Initialize and return Anthropic client
#     return anthropic.Anthropic(api_key=api_key)

# async def async_setup_mcp_session(server_params: StdioServerParameters) -> Tuple[ClientSession, Any]:
#     """Set up an MCP session.
    
#     Args:
#         server_params: MCP server parameters.
        
#     Returns:
#         tuple: A tuple containing (session, client_context) for the MCP connection.
        
#     Raises:
#         Exception: If connection to the MCP server fails.
#     """
#     # Connect to the MCP server using context managers
#     client_context = stdio_client(server_params)
#     read, write = await client_context.__aenter__()
#     session = ClientSession(read, write)
#     await session.__aenter__()
    
#     # Initialize the connection
#     await session.initialize()
    
#     return session, client_context

# async def fetch_available_tools(session: ClientSession) -> List[Dict[str, Any]]:
#     """Fetch available tools from the MCP server.
    
#     Args:
#         session: The MCP client session.
        
#     Returns:
#         list: A list of available tools in Claude format.
#     """
#     tools_result = await session.list_tools()
#     claude_tools: List[Dict[str, Any]] = []
#     if tools_result and hasattr(tools_result, 'tools'):
#         tools_list = getattr(tools_result, 'tools', [])
#         for tool in tools_list:
#             claude_tools.append({
#                 "name": tool.name,
#                 "description": tool.description,
#                 "input_schema": tool.inputSchema
#             })
    
#     return claude_tools

# async def call_claude_with_tools(client: Any, messages: List[Dict[str, Any]], claude_tools: List[Dict[str, Any]]) -> Any:
#     """Call Claude API with the current message history and tools.
    
#     Args:
#         client: The Anthropic client.
#         messages: The conversation message history.
#         claude_tools: Available tools in Claude format.
        
#     Returns:
#         The response from Claude.
        
#     Raises:
#         Exception: If the API call fails.
#     """
#     try:
#         # Call Claude with the current message history
#         response = client.messages.create(
#             model="claude-3-7-sonnet-latest",
#             messages=messages,
#             tools=claude_tools if claude_tools else None,
#             max_tokens=10000
#         )
#         return response
#     except Exception as e:
#         logger.error(f"Claude API error: {str(e)}")
#         raise

# async def process_claude_response(response: Any) -> Dict[str, Any]:
#     """Process Claude's response and prepare message content.
    
#     Args:
#         response: The response from Claude.
        
#     Returns:
#         Dictionary containing processed response information.
#     """
#     # Check the stop reason
#     stop_reason = response.stop_reason
#     has_tool_use = stop_reason == "tool_use"
    
#     # Create a dictionary to hold information about the stop reason
#     stop_reason_info = {
#         "reason": stop_reason,
#         "message": "",
#         "should_notify_user": False
#     }
    
#     # Process different stop reasons
#     if stop_reason == "end_turn":
#         stop_reason_info["message"] = "Claude reached a natural stopping point."
#     elif stop_reason == "max_tokens":
#         stop_reason_info["message"] = "Response was truncated due to token limit."
#         stop_reason_info["should_notify_user"] = True
#     elif stop_reason == "stop_sequence":
#         stop_reason_info["message"] = f"Response ended due to a custom stop sequence."
#         if hasattr(response, "stop_sequence") and response.stop_sequence:
#             stop_reason_info["message"] += f" Stop sequence: {response.stop_sequence}"
#     elif stop_reason == "tool_use":
#         stop_reason_info["message"] = "Claude is requesting to use a tool."
#     else:
#         stop_reason_info["message"] = f"Response ended with unknown stop reason: {stop_reason}"
#         stop_reason_info["should_notify_user"] = True
    
#     logger.debug(f"Stop reason: {stop_reason_info['message']}")
    
#     # Process Claude's response
#     assistant_message_content = []
#     final_response_parts = []
    
#     for content in response.content:
#         if content.type == "text":
#             final_response_parts.append(content.text)
#             assistant_message_content.append({"type": "text", "text": content.text})
#         elif content.type == "tool_use":
#             # Extract tool call details
#             tool_name = content.name
#             tool_args = content.input
#             tool_id = content.id
            
#             # Add tool use to assistant message
#             assistant_message_content.append({
#                 "type": "tool_use",
#                 "name": tool_name,
#                 "id": tool_id,
#                 "input": tool_args
#             })
    
#     return {
#         "assistant_message_content": assistant_message_content,
#         "has_tool_use": has_tool_use,
#         "stop_reason_info": stop_reason_info,
#         "final_response_parts": final_response_parts
#     }

# async def execute_tool_calls(session: ClientSession, response: Any) -> Dict[str, Any]:
#     """Execute tool calls requested by Claude.
    
#     Args:
#         session: The MCP client session.
#         response: The response from Claude containing tool calls.
        
#     Returns:
#         Dictionary containing tool results and response information.
#     """
#     # Create a new user message with tool results
#     tool_results_content = []
#     tool_calls = []
#     final_response_parts = []
    
#     # Process each tool use request
#     for content in response.content:
#         if content.type == "tool_use":
#             tool_name = content.name
#             tool_args = content.input
#             tool_id = content.id
            
#             try:
#                 # Execute the tool call through MCP
#                 logger.debug(f"Executing Tool: {tool_name}...")
#                 tool_result = await session.call_tool(tool_name, arguments=tool_args)
                
#                 # Extract the actual result value
#                 extracted_result = extract_tool_result_value(str(tool_result))
                
#                 # Add plain text result to final response
#                 tool_response = f"\nTool: {tool_name}\nResult: {extracted_result}\n"
#                 final_response_parts.append(tool_response)
                
#                 # Add tool result to the content for the next user message
#                 tool_results_content.append({
#                     "type": "tool_result",
#                     "tool_use_id": tool_id,
#                     "content": str(tool_result)
#                 })
                
#                 # Add tool information for return data
#                 tool_calls.append({
#                     "tool_name": tool_name,
#                     "tool_args": tool_args,
#                     "tool_id": tool_id,
#                     "result": str(tool_result),
#                     "extracted_result": extracted_result,
#                     "error": None
#                 })
#             except Exception as tool_error:
#                 # Add plain text error to final response
#                 error_msg = f"\nTool: {tool_name}\nError: {str(tool_error)}\n"
#                 final_response_parts.append(error_msg)
                
#                 # Add error to the content for the next user message
#                 tool_results_content.append({
#                     "type": "tool_result",
#                     "tool_use_id": tool_id,
#                     "content": str(tool_error)
#                 })
                
#                 # Add tool error information for return data
#                 tool_calls.append({
#                     "tool_name": tool_name,
#                     "tool_args": tool_args,
#                     "tool_id": tool_id,
#                     "result": None,
#                     "extracted_result": None,
#                     "error": str(tool_error)
#                 })
    
#     return {
#         "tool_results_content": tool_results_content,
#         "tool_calls": tool_calls,
#         "final_response_parts": final_response_parts
#     }

# async def run_conversation_loop(session: ClientSession, client: anthropic.Anthropic, claude_tools: List[Dict[str, Any]], messages: List[Dict[str, Any]], debug: bool = False, show_stop_reason: bool = False) -> Dict[str, Any]:
#     """Run the main conversation loop with Claude.
    
#     Args:
#         session: The MCP client session.
#         client: The Anthropic client.
#         claude_tools: Available tools in Claude format.
#         messages: Initial message history.
#         debug: Whether to show debug information.
#         show_stop_reason: Whether to show the stop reason in the output.
        
#     Returns:
#         Dictionary containing the conversation results and information.
#     """
#     # Main conversation loop
#     final_response_parts: List[str] = []
#     conversation_active = True
#     last_stop_reason_info = None
#     all_tool_calls = []
    
#     while conversation_active:
#         logger.debug(f"Calling Claude with {len(claude_tools)} available tools and {len(messages)} messages in history...")
        
#         # Debug: Log message structure before sending to Claude
#         if debug:
#             logger.debug(f"Sending message structure to Claude:")
#             for i, msg in enumerate(messages):
#                 logger.debug(f"  Message {i} - Role: {msg['role']}")
#                 if isinstance(msg['content'], list):
#                     logger.debug(f"    Content is a list with {len(msg['content'])} items")
#                     for j, content_item in enumerate(msg['content']):
#                         if isinstance(content_item, dict):
#                             if content_item.get('type') == 'tool_use':
#                                 logger.debug(f"      Item {j}: tool_use - Name: {content_item.get('name')}, ID: {content_item.get('id', 'MISSING')}")
#                             elif content_item.get('type') == 'tool_result':
#                                 logger.debug(f"      Item {j}: tool_result - Tool Use ID: {content_item.get('tool_use_id', 'MISSING')}")
#                                 content_preview = str(content_item.get('content', ''))[:50] + "..." if len(str(content_item.get('content', ''))) > 50 else str(content_item.get('content', ''))
#                                 logger.debug(f"        Content: {content_preview}")
#                             else:
#                                 logger.debug(f"      Item {j}: {content_item.get('type', 'unknown type')}")
#                         else:
#                             logger.debug(f"      Item {j}: {type(content_item)}")
#                 else:
#                     content_preview = str(msg['content'])[:50] + "..." if len(str(msg['content'])) > 50 else str(msg['content'])
#                     logger.debug(f"    Content: {content_preview}")
        
#         # Call Claude with the current message history
#         response = await call_claude_with_tools(client, messages, claude_tools)
        
#         # Process Claude's response
#         response_data = await process_claude_response(response)
#         assistant_message_content = response_data["assistant_message_content"]
#         has_tool_use = response_data["has_tool_use"]
#         stop_reason_info = response_data["stop_reason_info"]
#         final_response_parts.extend(response_data["final_response_parts"])
        
#         last_stop_reason_info = stop_reason_info
        
#         # Add assistant's response to message history
#         if assistant_message_content:
#             assistant_message = {
#                 "role": "assistant",
#                 "content": assistant_message_content
#             }
#             messages.append(assistant_message)
#             logger.debug(f"Added assistant response to message history. History now has {len(messages)} messages.")
        
#         # If Claude requested to use tools, execute them and send results back
#         if has_tool_use:
#             logger.debug("Claude requested tool calls, executing...")
            
#             # Execute tool calls
#             tool_result_data = await execute_tool_calls(session, response)
#             tool_results_content = tool_result_data["tool_results_content"]
#             tool_calls = tool_result_data["tool_calls"]
#             final_response_parts.extend(tool_result_data["final_response_parts"])
            
#             # Add tool calls to the collection of all tool calls
#             all_tool_calls.extend(tool_calls)
            
#             # Add the tool results as a new user message
#             if tool_results_content:
#                 tool_results_message = {
#                     "role": "user",
#                     "content": tool_results_content
#                 }
#                 messages.append(tool_results_message)
#                 logger.debug(f"Added tool results to message history. History now has {len(messages)} messages.")
            
#             # Continue the conversation to get Claude's final response
#             continue
#         else:
#             # No more tool calls, end the conversation
#             logger.debug(f"No more tool calls, ending conversation. Final stop reason: {stop_reason_info['reason']}")
#             conversation_active = False
    
#     # Combine all response parts
#     final_response = "\n".join(final_response_parts)
    
#     # Add stop reason information to the final response if requested
#     if show_stop_reason and last_stop_reason_info:
#         stop_reason_text = f"\n\n---\nStop reason: {last_stop_reason_info['reason']}"
#         if last_stop_reason_info["message"]:
#             stop_reason_text += f" - {last_stop_reason_info['message']}"
#         final_response += stop_reason_text
    
#     # Return a structured result
#     return {
#         "success": True,
#         "response": final_response,
#         "error": None,
#         "messages": messages,
#         "tool_calls": all_tool_calls,
#         "stop_reason_info": last_stop_reason_info,
#         "final_response_parts": final_response_parts
#     }

# async def async_run_mcp_command(prompt: str, server_params: StdioServerParameters, debug: bool = True, show_stop_reason: bool = False) -> Dict[str, Any]:
#     """Async implementation of the MCP command execution with context re-injection.
    
#     Args:
#         prompt: The text prompt to send.
#         server_params: MCP server parameters.
#         debug: Whether to show debug information.
#         show_stop_reason: Whether to show the stop reason in the output.
        
#     Returns:
#         Dictionary containing the conversation results and information.
#     """
#     session = None
#     client_context = None
    
#     try:
#         # Set up MCP session
#         session, client_context = await async_setup_mcp_session(server_params)
        
#         # Get Anthropic client
#         client = await get_anthropic_client()
        
#         # Fetch available tools
#         claude_tools = await fetch_available_tools(session)
#         if debug:
#             logger.debug(f"Available tools: {claude_tools}")

        
#         # Initialize conversation with the user's prompt
#         messages = [
#             {
#                 "role": "user",
#                 "content": prompt
#             }
#         ]
        
#         # Run the conversation loop
#         result = await run_conversation_loop(session, client, claude_tools, messages, debug, show_stop_reason)
        
#         return result

#     except Exception as e:
#         logger.exception("MCP Error")
#         return {
#             "success": False,
#             "response": None,
#             "error": f"MCP Error: {str(e)}",
#             "messages": None,
#             "tool_calls": None,
#             "stop_reason_info": None,
#             "final_response_parts": None
#         }
#     finally:
#         # Clean up resources
#         if session:
#             await session.__aexit__(None, None, None)
#         if client_context:
#             await client_context.__aexit__(None, None, None)

# def create_mcp_server_params() -> StdioServerParameters:
#     """Create server parameters for MCP.
    
#     Returns:
#         MCP server parameters.
#     """
#     return StdioServerParameters(
#         command="uv",  # Executable
#         args=[
#             "run",
#             "--directory",
#             "/Users/lherron/projects/evai-cli",
#             "--with",
#             "mcp[cli]",
#             "mcp",
#             "run",
#             "/Users/lherron/projects/evai-cli/evai/mcp/server.py"
#         ],  # Path to the MCP server script
#         env=None  # Using default environment
#     )

# async def execute_llm_request_async(
#     prompt: str,
#     use_mcp: bool,
#     server_params: Optional[StdioServerParameters] = None,
#     debug: bool = True,
#     show_stop_reason: bool = False
# ) -> Dict[str, Any]:
#     """
#     Executes an LLM request with MCP server 

#     Args:
#         prompt: The text prompt to send to the LLM.
#         use_mcp: Whether to use MCP server integration.
#         server_params: MCP server parameters (required if use_mcp is True).
#         debug: Whether to show debug information.
#         show_stop_reason: Whether to show the stop reason in the output.

#     Returns:
#         A dictionary containing the structured result:
#         {
#             "success": bool,
#             "response": Optional[str], # Final text response
#             "error": Optional[str],
#             "tool_calls": Optional[List[Dict]], # List of tool call details
#             "stop_reason_info": Optional[Dict], # Info about the final stop reason
#             "messages": Optional[List[Dict]] # Full conversation history (for debug)
#         }
#     """
#     try:
#         if use_mcp:
#             if not server_params:
#                 raise ValueError("server_params are required when use_mcp is True")
#             # Call the refactored MCP command logic
#             return await async_run_mcp_command(prompt, server_params, debug, show_stop_reason)
#         else:
#             # Call the refactored direct command logic
#             direct_response = await call_claude_directly(prompt, show_stop_reason=show_stop_reason)
#             # For simplicity, assume call_claude_directly returns only the text for now
#             return {
#                 "success": True,
#                 "response": direct_response,
#                 "error": None,
#                 "tool_calls": None,
#                 "stop_reason_info": None, # Direct calls don't have the same stop reason structure easily accessible here yet
#                 "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": direct_response}] # Simplified history
#             }
#     except Exception as e:
#         logger.exception("Error during LLM request execution")
#         return {
#             "success": False,
#             "response": None,
#             "error": str(e),
#             "tool_calls": None,
#             "stop_reason_info": None,
#             "messages": None
#         }

# def execute_llm_request(
#     prompt: str,
#     use_mcp: bool,
#     server_params: Optional[StdioServerParameters] = None,
#     debug: bool = False,
#     show_stop_reason: bool = False
# ) -> Dict[str, Any]:
#     """
#     Synchronous wrapper for execute_llm_request_async.
    
#     See execute_llm_request_async for parameter and return details.
#     """
#     return asyncio.run(execute_llm_request_async(
#         prompt=prompt,
#         use_mcp=use_mcp,
#         server_params=server_params,
#         debug=debug,
#         show_stop_reason=show_stop_reason
#     )) 

# Main function for demonstration
# if __name__ == "__main__":
#     # Configure logging to show debug information
#     logging.basicConfig(
#         level=logging.DEBUG,
#         format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     )
#     # set httpcore to INFO
#     logging.getLogger("httpcore").setLevel(logging.INFO)
#     logging.getLogger("anthropic").setLevel(logging.INFO)
#     # Example prompt that should trigger tool use
#     prompt = "subtract 8 from 3"
    
#     print(f"Sending prompt to LLM: \"{prompt}\"")
#     print("Using MCP for tool integration...")
    
#     # # Create server parameters
#     server_params = create_mcp_server_params()
    
#     # Execute LLM request with MCP enabled
#     result = execute_llm_request(
#         prompt=prompt,
#         use_mcp=True,
#         server_params=server_params,
#         debug=True,
#         show_stop_reason=True
#     )

#     # Print results
#     print("\n--- RESULT ---")
#     if result["success"]:
#         print("Success: True")
#         print(f"Response:\n{result['response']}")
        
#         # Print tool calls if any
#         if result["tool_calls"]:
#             print("\n--- TOOL CALLS ---")
#             for i, tool_call in enumerate(result["tool_calls"], 1):
#                 print(f"Tool Call {i}:")
#                 print(f"  Tool: {tool_call['tool_name']}")
#                 print(f"  Args: {tool_call['tool_args']}")
#                 print(f"  Result: {tool_call['extracted_result']}")
#                 if tool_call['error']:
#                     print(f"  Error: {tool_call['error']}")
#     else:
#         print("Success: False")
#         print(f"Error: {result['error']}") 

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # Filter out some excessive logging
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    
    # Ignore asyncio cancel scope errors that happen during cleanup
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)

    config = Configuration()
    
    # Load server configurations from server_config.json
    try:
        server_config = config.load_config("servers_config.json")
        servers = [
            MCPServer(name, srv_config)
            for name, srv_config in server_config["mcpServers"].items()
        ]
        if not servers:
            logging.warning("No MCP servers found in configuration. Proceeding without tools.")
    except FileNotFoundError:
        logging.warning("server_config.json not found. Proceeding without MCP servers.")
        servers = []
    except json.JSONDecodeError:
        logging.error("Invalid JSON in server_config.json. Proceeding without MCP servers.")
        servers = []
    
    session = LLMSession(servers)
    
    try:
        prompt = "subtract 8 from 3"
        result = asyncio.run(session.send_request(prompt, debug=True, show_stop_reason=True))
        
        print("\n--- RESULT ---")
        if result["success"]:
            print("Success: True")
            print(f"Response:\n{result['response']}")
            if result["tool_calls"]:
                print("\n--- TOOL CALLS ---")
                for i, call in enumerate(result["tool_calls"], 1):
                    print(f"Tool Call {i}: {call['tool_name']} - Result: {call.get('result', 'Error: ' + call.get('error', 'Unknown'))}")
        else:
            print("Success: False")
            print(f"Error: {result['error']}")
    except Exception as e:
        print(f"An error occurred: {e}")
        # In the case of an error, ensure server processes are killed
        import signal
        import os
        import psutil
        
        # Get current process
        current_process = psutil.Process(os.getpid())
        
        # Kill all child processes to clean up any hanging MCP servers
        for child in current_process.children(recursive=True):
            try:
                child.kill()
            except:
                pass