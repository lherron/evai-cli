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
            stdio_context = stdio_client(server_params)
            stdio_transport = await self.exit_stack.enter_async_context(stdio_context)
            
            # Store a reference to the process for proper cleanup
            if hasattr(stdio_context, '_process_context') and hasattr(stdio_context._process_context, '_process'):
                self._process = stdio_context._process_context._process
            
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
                # Properly terminate subprocesses first
                if hasattr(self, '_process') and self._process:
                    try:
                        import signal
                        import os
                        
                        # Try to terminate the process group if possible
                        try:
                            pgid = os.getpgid(self._process.pid)
                            os.killpg(pgid, signal.SIGTERM)
                        except (ProcessLookupError, PermissionError, AttributeError):
                            # Fall back to terminating just the process
                            try:
                                self._process.terminate()
                            except ProcessLookupError:
                                pass
                    except Exception as proc_err:
                        logging.debug(f"Error terminating process for server {self.name}: {proc_err}")
                
                # Close the session first (if it exists)
                if self.session:
                    # Just set to None - we'll close the connection via the exit stack
                    self.session = None
                
                # Use a new async task to close the exit stack if we're in a different task
                # This prevents the "cancel scope in different task" error
                current_task = asyncio.current_task()
                
                if self.exit_stack:
                    # Different approach depending on whether we're in the same task
                    if self._stack_task == current_task:
                        # If we're in the same task, close directly
                        try:
                            await self.exit_stack.aclose()
                        except Exception as stack_err:
                            logging.debug(f"Error in exit stack cleanup for server {self.name}: {stack_err}")
                    else:
                        # If we're in a different task, we need to create a new exit stack
                        # and manually close our resources to avoid cancel scope errors
                        try:
                            # Just record that we attempted to clean up - the process will be cleaned up
                            # when the program exits
                            logging.debug(f"Server {self.name} cleanup in different task - will be cleaned up on exit")
                        except Exception as cleanup_err:
                            logging.debug(f"Alternative cleanup error for server {self.name}: {cleanup_err}")
                    
                    # Always set to None to allow garbage collection
                    self.exit_stack = None
                
                # Clean up remaining attributes  
                self.stdio_context = None
                self._stack_task = None
                self._initialized = False
                
            except Exception as e:
                logging.debug(f"Error during cleanup of server {self.name}: {e}")
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
        logging.debug(f"Starting cleanup of {len(self.servers)} servers")
        
        # Clean up each server sequentially to avoid any potential race conditions
        for server in self.servers:
            if server._initialized or server.session is not None:
                try:
                    await server.cleanup()
                except Exception as e:
                    error_msg = f"Error during cleanup of server {server.name}: {e}"
                    logging.debug(error_msg)
                    cleanup_errors.append(error_msg)
        
        # Set initialized to False regardless of cleanup errors
        self.initialized = False
        
        # Collect any lingering processes that need to be terminated
        import psutil
        import os
        import signal
        
        # Clean up any child processes that might still be running
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            
            for child in children:
                try:
                    child_name = child.name()
                    if any(child_name.startswith(svc) for svc in ['uv', 'python', 'node']):
                        logging.debug(f"Terminating lingering process: {child_name} (PID: {child.pid})")
                        child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logging.debug(f"Error cleaning up child processes: {e}")
        
        logging.debug(f"Server cleanup complete. {len(cleanup_errors)} errors encountered.")

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
                    # Mark as not initialized rather than attempting cleanup
                    self.initialized = False
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

            # Store process information for manual cleanup later
            self._child_processes = []
            for server in self.servers:
                if hasattr(server, '_process') and server._process:
                    self._child_processes.append(server._process.pid)

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
            # Clean up without waiting for it to complete
            # We'll do this in a non-blocking way to prevent cancellation issues
            for server in self.servers:
                server.session = None
                server._initialized = False
            
            # Schedule cleanup to happen after this function returns
            import threading
            def cleanup_processes():
                import time
                import os
                import signal
                import psutil
                
                # Give a small delay to ensure the main operation has completed
                time.sleep(0.5)
                
                try:
                    # Clean up processes that we know about
                    for pid in getattr(self, '_child_processes', []):
                        try:
                            process = psutil.Process(pid)
                            process.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        
                    # Clean up any other child processes
                    current_process = psutil.Process(os.getpid())
                    for child in current_process.children(recursive=True):
                        if child.is_running():
                            try:
                                child.terminate()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                except Exception as e:
                    # Just log but don't raise
                    logging.debug(f"Error in cleanup thread: {e}")
            
            # Start cleanup thread
            threading.Thread(target=cleanup_processes, daemon=True).start()
            
            # Mark servers as not initialized
            self.initialized = False

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

            # Store process information for manual cleanup later
            self._child_processes = []
            for server in self.servers:
                if hasattr(server, '_process') and server._process:
                    self._child_processes.append(server._process.pid)

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

            # Clean up without waiting for it to complete
            # We'll do this in a non-blocking way to prevent cancellation issues
            for server in self.servers:
                server.session = None
                server._initialized = False

            # Schedule cleanup to happen after this function returns
            import threading
            def cleanup_processes():
                import time
                import os
                import signal
                import psutil
                
                # Give a small delay to ensure the main operation has completed
                time.sleep(0.5)
                
                try:
                    # Clean up processes that we know about
                    for pid in getattr(self, '_child_processes', []):
                        try:
                            process = psutil.Process(pid)
                            process.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        
                    # Clean up any other child processes
                    current_process = psutil.Process(os.getpid())
                    for child in current_process.children(recursive=True):
                        if child.is_running():
                            try:
                                child.terminate()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                except Exception as e:
                    # Just log but don't raise
                    logger.debug(f"Error in cleanup thread: {e}")
            
            # Start cleanup thread
            threading.Thread(target=cleanup_processes, daemon=True).start()
            
            # Mark servers as not initialized
            self.initialized = False

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