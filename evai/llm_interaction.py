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
import shutil
import anthropic
from mcp import ClientSession, StdioServerParameters
import httpx
from mcp.client.stdio import stdio_client
from mcp import types
from contextlib import AsyncExitStack
from dotenv import load_dotenv
# Configure logging
logger = logging.getLogger(__name__)


class MCPTool:
    """Represents a tool with its properties and formatting."""

    def __init__(
        self, name: str, server_name: str, description: str, input_schema: dict[str, Any]
    ) -> None:
        self.name: str = name
        self.server_name: str = server_name
        self.description: str = description
        self.input_schema: dict[str, Any] = input_schema

#     def format_for_llm(self) -> str:
#         """Format tool information for LLM.

#         Returns:
#             A formatted string describing the tool.
#         """
#         args_desc = []
#         if "properties" in self.input_schema:
#             for param_name, param_info in self.input_schema["properties"].items():
#                 arg_desc = (
#                     f"- {param_name}: {param_info.get('description', 'No description')}"
#                 )
#                 if param_name in self.input_schema.get("required", []):
#                     arg_desc += " (required)"
#                 args_desc.append(arg_desc)

#         return f"""
# Tool: {self.name}
# Description: {self.description}
# Arguments:
# {chr(10).join(args_desc)}
# """


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




# --- MCPServer Class (Cleanup Simplified) ---
class MCPServer:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
            self.name: str = name
            self.config: dict[str, Any] = config
            self.session: Optional[ClientSession] = None
            self._cleanup_lock: asyncio.Lock = asyncio.Lock()
            self.exit_stack: Optional[AsyncExitStack] = None
            self._process_pid: Optional[int] = None
            self._initialized: bool = False
            self.initialized_event = asyncio.Event()  # Signals when initialization is complete

    async def initialize(self) -> None:
        """Initialize the server connection."""
        if self._initialized:
             logger.debug(f"Server {self.name} already initialized.")
             return

        if self.config["command"] == "npx":
            command = shutil.which("npx")
        else:
            command = self.config["command"]

        if command is None:
            raise ValueError(f"Command '{self.config['command']}' not found or not executable.")

        if self.config.get("env"):
            env = {**os.environ, **self.config["env"]}
        else:
            env = os.environ

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env=env
        )
        logger.info(f"Initializing server {self.name} with command: {' '.join([command] + server_params.args)}")

        # Create and manage the exit stack within the initialization
        # to ensure it's tied to this specific attempt
        exit_stack = AsyncExitStack()
        try:
            # --- Use a temporary variable for the stack ---
            temp_exit_stack = AsyncExitStack()

            stdio_context = stdio_client(server_params)
            # Store the context manager itself to access the process later if needed
            self._stdio_context_manager = stdio_context

            stdio_transport = await temp_exit_stack.enter_async_context(stdio_context)

            # Try to get the process PID robustly
            process_obj = None
            if hasattr(stdio_context, '_process_context') and hasattr(stdio_context._process_context, '_process'):
                 process_obj = stdio_context._process_context._process
                 if process_obj:
                    self._process_pid = process_obj.pid
                    logger.debug(f"Server {self.name} process started with PID: {self._process_pid}")


            read, write = stdio_transport

            session_context = ClientSession(read, write)
            session = await temp_exit_stack.enter_async_context(session_context)
            try:
                await session.initialize()
            except Exception as e:
                logger.error(f"Error initializing server {self.name}: {e}", exc_info=True)
                # stack trace
                traceback.print_exc()
                raise # Re-raise the original exception

            # --- If successful, assign the stack and session ---
            self.exit_stack = temp_exit_stack
            self.session = session
            self._initialized = True
            logger.info(f"Server {self.name} initialized successfully.")

        except Exception as e:
            logger.error(f"Error initializing server {self.name}: {e}", exc_info=True)
            # --- Ensure cleanup if initialization fails ---
            try:
                # Use the temporary stack for cleanup here
                await temp_exit_stack.aclose()
            except Exception as close_err:
                logger.warning(f"Error closing exit stack during initialization cleanup for {self.name}: {close_err}")
            # Reset state
            self.exit_stack = None
            self.session = None
            self._process_pid = None
            self._initialized = False
            raise # Re-raise the original exception

    async def run(self) -> None:
        """Run the server's lifecycle in a single task."""
        logger.info(f"Starting server {self.name}...")
        try:
            await self.initialize()
            self.initialized_event.set()  # Signal that initialization is complete
            # Keep the server alive until cancelled
            await asyncio.Event().wait()  # Wait indefinitely
        except asyncio.CancelledError:
            logger.info(f"Server {self.name} task cancelled, initiating cleanup.")
        except Exception as e:
            logger.error(f"Error in server {self.name} run loop: {e}", exc_info=True)
        finally:
            await self.cleanup()


    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized or session is None")

        try:
            tools_response = await self.session.list_tools()
        except Exception as e:
            logger.error(f"Error listing tools for server {self.name}: {e}")
            # Attempt to re-initialize or mark as uninitialized? For now, just raise.
            raise RuntimeError(f"Failed to list tools for {self.name}: {e}") from e

        tools = []
        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                logging.info(f"Tools for {self.name}:")
                for tool in item[1]:
                    logging.info(f"\tTool: name='{tool.name}' description='{tool.description}'")
                    tools.append(MCPTool(name=tool.name, server_name=self.name, description=tool.description, input_schema=tool.inputSchema))


        return tools


    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 1, # Reduced default retries, can be overridden
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized or session is None")

        attempt = 0
        last_exception = None
        while attempt <= retries: # Use <= to include the initial try + retries
            try:
                logger.info(f"Executing tool '{tool_name}' on server {self.name} (Attempt {attempt + 1}/{retries + 1})")
                if logger.level == logging.DEBUG:
                     logger.debug(f"Arguments: {json.dumps(arguments)}")

                result = await self.session.call_tool(tool_name, arguments)
                logger.info(f"Tool '{tool_name}' executed successfully on server {self.name}.")
                if logger.level == logging.DEBUG:
                    logger.debug(f"Raw result: {result}")
                return result # Success

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Error executing tool '{tool_name}' on {self.name} (Attempt {attempt + 1}): {e}"
                )
                attempt += 1
                if attempt <= retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries ({retries}) reached for tool '{tool_name}' on {self.name}. Failing.")
                    raise RuntimeError(f"Tool execution failed after {retries} retries on {self.name}") from last_exception

        # Should not be reachable, but satisfy type checker
        raise RuntimeError(f"Tool execution failed unexpectedly for {tool_name} on {self.name}")


    async def cleanup(self) -> None:
        """Clean up server resources using the AsyncExitStack."""
        # Use a lock to prevent concurrent cleanup attempts
        async with self._cleanup_lock:
            if not self._initialized and not self.exit_stack:
                logger.debug(f"Cleanup skipped for server {self.name}: Not initialized.")
                return

            logger.info(f"Starting cleanup for server {self.name}...")
            try:
                if self.exit_stack:
                    logger.debug(f"Closing AsyncExitStack for {self.name}.")
                    await self.exit_stack.aclose()
                    logger.debug(f"AsyncExitStack for {self.name} closed.")
                else:
                    logger.warning(f"No AsyncExitStack found for cleanup on server {self.name}, potential resource leak if initialized.")

                 # Attempt graceful process termination if PID known and stack closing failed?
                 # This is risky as the stack *should* handle it. Only use as last resort.
                # if self._process_pid:
                #     try:
                #         proc = psutil.Process(self._process_pid)
                #         if proc.is_running():
                #             logger.warning(f"Force terminating potentially orphaned process PID {self._process_pid} for server {self.name}")
                #             proc.terminate()
                #             await asyncio.sleep(0.1) # Give time to terminate
                #             if proc.is_running():
                #                 proc.kill()
                #     except psutil.NoSuchProcess:
                #         logger.debug(f"Process PID {self._process_pid} for {self.name} already exited.")
                #     except Exception as p_err:
                #         logger.error(f"Error during forceful termination of PID {self._process_pid} for {self.name}: {p_err}")


            except Exception as e:
                # Log specific errors during cleanup
                if isinstance(e, ProcessLookupError):
                     logger.warning(f"Cleanup warning for {self.name}: Process was already gone when trying to terminate.")
                elif "cancel scope" in str(e):
                     logger.error(f"FATAL Cleanup Error for {self.name}: Cancel scope issue detected. This should not happen with the new structure. Error: {e}", exc_info=True)
                else:
                    logger.error(f"Error during AsyncExitStack cleanup for server {self.name}: {e}", exc_info=True)
            finally:
                 # Always reset state after attempting cleanup
                logger.info(f"Cleanup finished for server {self.name}.")
                self.session = None
                self.exit_stack = None
                self._process_pid = None
                # Keep _stdio_context_manager? Probably not needed after cleanup.
                self._stdio_context_manager = None
                self._initialized = False # Mark as not initialized after cleanup



class LLMSession:
    """Orchestrates the interaction between user, LLM, and tools."""

    def __init__(self, servers: list[MCPServer]) -> None:
        config = Configuration() # Get config to access API key
        self.servers: list[MCPServer] = servers
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.servers: list[MCPServer] = servers
        self.anthropic_client = anthropic.Anthropic(api_key=api_key)
        self.initialized_servers: bool = False # Track server initialization state
        self.server_tasks: list[asyncio.Task] = []  # Store server tasks

    async def start_servers(self) -> None:
        """Start all server tasks."""
        logger.info(f"Starting {len(self.servers)} MCP server tasks...")
        self.server_tasks = [
            asyncio.create_task(server.run(), name=f"mcp_server_{server.name}")
            for server in self.servers
        ]
        # Wait for all servers to initialize
        await asyncio.gather(*[server.initialized_event.wait() for server in self.servers])
        logger.info("All MCP servers have started and initialized.")

    async def stop_servers(self) -> None:
        """Stop all server tasks and trigger cleanup."""
        if not self.server_tasks:
            logger.debug("No server tasks to stop.")
            return
        logger.info(f"Stopping {len(self.server_tasks)} MCP server tasks...")
        for task in self.server_tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.server_tasks, return_exceptions=True)
        self.server_tasks = []
        logger.info("All MCP server tasks have stopped.")
    
    async def initialize_servers(self) -> None:
        """Initialize all MCPServer instances if not already initialized."""
        if self.initialized_servers:
             logger.debug("Servers already initialized.")
             return

        logger.info(f"Initializing {len(self.servers)} MCP servers...")
        init_tasks = [server.initialize() for server in self.servers]
        results = await asyncio.gather(*init_tasks, return_exceptions=True)

        successful_initializations = 0
        for i, result in enumerate(results):
            server_name = self.servers[i].name
            if isinstance(result, Exception):
                logger.error(f"Failed to initialize server '{server_name}': {result}")
                # Server's own initialize method should have reset its state
            else:
                logger.info(f"Server '{server_name}' initialized successfully.")
                successful_initializations += 1

        if successful_initializations == len(self.servers):
            self.initialized_servers = True
            logger.info("All servers initialized successfully.")
        elif successful_initializations > 0:
             # Maybe proceed with available servers? For now, mark as partial/failed.
             self.initialized_servers = False # Or a new state like 'partially_initialized'?
             logger.warning(f"Only {successful_initializations}/{len(self.servers)} servers initialized.")
             # Depending on requirements, you might want to raise an error here
             # raise RuntimeError("Failed to initialize all required MCP servers.")
        else:
            self.initialized_servers = False
            logger.error("No MCP servers could be initialized.")
            raise RuntimeError("Failed to initialize any MCP servers.")


    async def cleanup_servers(self) -> None:
        """Clean up all MCPServer instances."""
        if not self.initialized_servers and not any(s._initialized for s in self.servers):
             logger.debug("Skipping server cleanup: No servers were successfully initialized.")
             return

        logger.info(f"Starting cleanup of {len(self.servers)} MCP servers...")
        cleanup_tasks = [server.cleanup() for server in self.servers]
        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        errors = []
        for i, result in enumerate(results):
            server_name = self.servers[i].name
            if isinstance(result, Exception):
                 error_msg = f"Error during cleanup of server {server_name}: {result}"
                 logger.error(error_msg)
                 errors.append(error_msg)
            else:
                 logger.info(f"Server '{server_name}' cleaned up successfully.")

        # Always mark as uninitialized after attempting cleanup
        self.initialized_servers = False
        logger.info("Server cleanup process finished.")
        if errors:
             logger.warning(f"Cleanup completed with {len(errors)} errors.")
             # Optionally re-raise a combined error or handle as needed
             # raise RuntimeError("Errors occurred during server cleanup:\n" + "\n".join(errors))


    # --- process_llm_response (removed, logic integrated into send_request) ---

    # --- start (removed, focus on send_request) ---

    async def send_request(self, prompt: str, debug: bool = False, show_stop_reason: bool = False, allowed_tools: list[str] = None) -> Dict[str, Any]:
        """Execute an LLM request with tool use independently."""
        # Use a try/finally block to ensure cleanup
        try:
            logger.info("Starting LLM request processing.")
            if debug:
                logger.debug(f"Prompt: {prompt}")

            # --- Initialize Servers ---
            # await self.initialize_servers() # This now handles initialization state
            # Servers are already initialized; check their state
            for server in self.servers:
                if not server._initialized or not server.session:
                    raise RuntimeError(f"Server {server.name} is not initialized or has no session.")
            # --- Collect Tools ---
            logger.info("Collecting tools from initialized servers.")
            all_tools_for_api = []
            tool_to_server_map = {}
            for server in self.servers:
                if server._initialized and server.session: # Check if server is actually ready
                    try:
                        tools = await server.list_tools()
                        if len(tools) == 0:
                            logger.warning(f"No tools found in server {server.name}")
                        else:
                            for tool in tools:
                                # Format for Anthropic API
                                tool_api_dict = {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "input_schema": tool.input_schema
                                }
                                all_tools_for_api.append(tool_api_dict)
                                tool_to_server_map[tool.name] = server
                    except Exception as e:
                        logger.error(f"Could not list tools from server {server.name}: {e}. Skipping its tools.")
                else:
                     logger.warning(f"Skipping tool collection from server {server.name}: Not initialized or no session.")

            # if allowed_tools is None, use all tools
            if allowed_tools is None:
                logger.info(f"Using all tools in API call: {all_tools_for_api}")
            else:
                # Filter tools based on allowed_tools
                all_tools_for_api = [tool for tool in all_tools_for_api if tool["name"] in allowed_tools]
                logger.info(f"Using only the following tools in API call: {all_tools_for_api}")
            # --- Conversation Loop ---
            messages = [{"role": "user", "content": prompt}]
            final_response_parts = []
            tool_calls_executed = []
            stop_reason_info = None
            max_turns = 5 # Add a safety limit for tool use loops
            turn = 0

            while turn < max_turns:
                turn += 1
                logger.info(f"LLM Interaction - Turn {turn}")

                try:
                    # --- Call Anthropic API ---
                    logger.debug(f"Sending {len(messages)} messages and {len(all_tools_for_api)} tools to Anthropic.")
                    logger.debug(f"Messages: {messages}")
                    logger.debug(f"Tools: {all_tools_for_api}")
                    response = self.anthropic_client.messages.create(
                        # model="claude-3-haiku-20240307", # Consider Haiku for speed/cost
                        model="claude-3-7-sonnet-latest", # Use the newer Sonnet
                        messages=messages,
                        tools=all_tools_for_api,
                        max_tokens=4000,
                        # Consider adding system prompt here if needed
                    )
                    logger.info(f"Received response from Anthropic. Stop reason: {response.stop_reason}")
                    logger.debug(f"Response: {response}")
                    stop_reason_info = {"reason": response.stop_reason, "stop_sequence": response.stop_sequence}


                    # --- Process Response ---
                    assistant_response_content = []
                    tool_uses_in_response = []

                    for content_block in response.content:
                        if content_block.type == "text":
                            logger.debug(f"LLM Text: {content_block.text[:100]}...")
                            final_response_parts.append(content_block.text)
                            assistant_response_content.append({"type": "text", "text": content_block.text})
                        elif content_block.type == "tool_use":
                            logger.info(f"LLM requests Tool Use: {content_block.name} (ID: {content_block.id})")
                            if debug:
                                logger.debug(f"Tool Input Args: {json.dumps(content_block.input)}")
                            assistant_response_content.append({
                                "type": "tool_use",
                                "id": content_block.id,
                                "name": content_block.name,
                                "input": content_block.input
                            })
                            tool_uses_in_response.append(content_block) # Keep track
                        elif content_block.type == "message":
                            # Handle message type content blocks
                            logger.debug(f"LLM Message: {str(content_block)[:100]}...")
                            # Extract relevant information from the message
                            message_info = {
                                "id": getattr(content_block, "id", None),
                                "role": getattr(content_block, "role", None),
                                "content": getattr(content_block, "content", []),
                                "model": getattr(content_block, "model", None),
                                "stop_reason": getattr(content_block, "stop_reason", None),
                                "stop_sequence": getattr(content_block, "stop_sequence", None),
                                "usage": getattr(content_block, "usage", None)
                            }
                            # Add to response content
                            assistant_response_content.append({
                                "type": "message",
                                "message": message_info
                            })
                            # If the message has text content, add it to final response
                            if message_info["content"]:
                                for msg_content in message_info["content"]:
                                    if getattr(msg_content, "type", None) == "text":
                                        final_response_parts.append(msg_content.text)

                    # Add assistant's turn (text and tool requests) to messages
                    if assistant_response_content:
                         messages.append({"role": "assistant", "content": assistant_response_content})

                    # --- Handle Tool Calls (if any) ---
                    if response.stop_reason == "tool_use" and tool_uses_in_response:
                        logger.info(f"Executing {len(tool_uses_in_response)} tool(s).")
                        tool_results_for_next_turn = []

                        # Execute tools concurrently
                        tool_tasks = []
                        for tool_use in tool_uses_in_response:
                             tool_name = tool_use.name
                             tool_args = tool_use.input
                             tool_id = tool_use.id
                             server = tool_to_server_map.get(tool_name)

                             if server and server._initialized and server.session:
                                 # Create a task for each tool execution
                                 tool_tasks.append(
                                      asyncio.create_task(
                                          self._execute_and_format_tool(server, tool_name, tool_args, tool_id, debug),
                                          name=f"tool_exec_{tool_name}_{tool_id}" # Name task for debugging
                                      )
                                  )
                             else:
                                 logger.warning(f"Cannot execute tool '{tool_name}': Server not found or not ready.")
                                 # Provide an error result back to the LLM
                                 error_result = {
                                     "type": "tool_result",
                                     "tool_use_id": tool_id,
                                     "content": f"Error: Tool '{tool_name}' is not available or its server is not ready.",
                                     "is_error": True # Add flag for clarity
                                 }
                                 tool_results_for_next_turn.append(error_result)
                                 tool_calls_executed.append({ # Log the failed attempt
                                     "tool_name": tool_name,
                                     "tool_args": tool_args,
                                     "error": f"Tool server for '{tool_name}' not available/ready."
                                 })


                        # Wait for all tool execution tasks to complete
                        if tool_tasks:
                            tool_execution_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

                            for result_or_exc in tool_execution_results:
                                if isinstance(result_or_exc, Exception):
                                    # This shouldn't happen if _execute_and_format_tool handles exceptions
                                    logger.error(f"Unexpected exception during tool execution gather: {result_or_exc}")
                                    # How to handle this? Maybe create a generic error result?
                                else:
                                    # result_or_exc contains the tuple (formatted_result, execution_log)
                                    formatted_result, execution_log = result_or_exc
                                    tool_results_for_next_turn.append(formatted_result)
                                    tool_calls_executed.append(execution_log)


                        # Add tool results message for the next LLM turn
                        if tool_results_for_next_turn:
                             messages.append({"role": "user", "content": tool_results_for_next_turn}) # Use 'user' role for tool results

                        # Continue the loop for the LLM to process the results
                        continue

                    else:
                        # Conversation ends (stop_reason is 'end_turn', 'max_tokens', etc.)
                        logger.info("LLM interaction finished.")
                        break

                except anthropic.APIError as e:
                    logger.error(f"Anthropic API Error: {e}", exc_info=debug)
                    raise # Re-raise API errors as they indicate a problem with the request/service
                except Exception as e:
                    logger.exception("Unexpected error during LLM interaction loop")
                    raise # Re-raise other unexpected errors


            if turn >= max_turns:
                 logger.warning(f"Reached maximum conversation turns ({max_turns}).")

            # --- Final Response ---
            final_response_text = "\n".join(final_response_parts).strip()
            logger.info("LLM request processing complete.")
            if debug:
                 logger.debug(f"Final constructed response text:\n{final_response_text}")
                 logger.debug(f"Tool calls executed: {json.dumps(tool_calls_executed, indent=2)}")


            return {
                "success": True,
                "response": final_response_text,
                "error": None,
                "tool_calls": tool_calls_executed,
                "stop_reason_info": stop_reason_info,
                "messages": messages if debug else None # Only include messages in debug mode
            }

        except Exception as e:
            logger.exception("Error during send_request execution")
            return {
                "success": False,
                "response": None,
                "error": str(e),
                "tool_calls": tool_calls_executed if 'tool_calls_executed' in locals() else [],
                "stop_reason_info": stop_reason_info if 'stop_reason_info' in locals() else None,
                "messages": messages if debug and 'messages' in locals() else None
            }
        # finally:
        #     # --- ENSURE CLEANUP ---
        #     logger.info("Running cleanup after send_request.")
        #     await self.cleanup_servers()


    async def _execute_and_format_tool(self, server: MCPServer, tool_name: str, tool_args: Dict[str, Any], tool_id: str, debug: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Helper to execute a tool, format result for LLM, and log execution."""
        execution_log = {"tool_name": tool_name, "tool_args": tool_args}
        formatted_result: Dict[str, Any]
        try:
            # Execute the tool (MCPServer.execute_tool handles retries)
            raw_result = await server.execute_tool(tool_name, tool_args)
            logger.info(f"Tool '{tool_name}' execution successful (ID: {tool_id}).")

            # Process/Format the result for the LLM
            # Anthropic expects a JSON-serializable object or a list of content blocks
            # For simplicity, let's send the string representation, potentially extracted
            extracted_result_str = extract_tool_result_value(str(raw_result))
            if debug:
                 logger.debug(f"Raw Result (ID: {tool_id}): {raw_result}")
                 logger.debug(f"Extracted Result String (ID: {tool_id}): {extracted_result_str}")

            formatted_result = {
                "type": "tool_result",
                "tool_use_id": tool_id,
                # Send the extracted string as content
                "content": extracted_result_str,
            }
            execution_log["result"] = extracted_result_str # Log the processed result
            # execution_log["raw_result"] = str(raw_result) # Optionally log raw result

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}' (ID: {tool_id}): {e}", exc_info=debug)
            error_msg = f"Error: Tool '{tool_name}' execution failed. Details: {str(e)}"
            formatted_result = {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": error_msg,
                "is_error": True, # Flag as error for Anthropic
            }
            execution_log["error"] = str(e)

        return formatted_result, execution_log


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


# --- Main Execution Block ---
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, # Use DEBUG for detailed logs
        format="%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
        datefmt="%H:%M:%S"
    )
    # Filter noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    # logging.getLogger("anyio").setLevel(logging.INFO) # Keep commented unless debugging anyio


    config = Configuration()
    servers = []
    try:
        server_configs = config.load_config("servers_config.json")
        mcp_servers_config = server_configs.get("mcpServers", {})
        if not mcp_servers_config:
             logger.warning("No 'mcpServers' key found or empty in servers_config.json.")
        else:
            servers = [
                MCPServer(name, srv_config)
                for name, srv_config in mcp_servers_config.items()
            ]
            if not servers:
                 logger.warning("MCP server list is empty after processing config.")

    except FileNotFoundError:
        logger.warning("servers_config.json not found. Proceeding without MCP servers.")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in servers_config.json. Proceeding without MCP servers.")
    except Exception as e:
         logger.exception("Error loading server configuration.")
         # Depending on requirements, might want to exit here
         # sys.exit(1)


    session = LLMSession(servers)
    main_task = None # Keep track of the main task for potential cancellation

    async def run_main():
        global main_task
        main_task = asyncio.current_task()
        # Example prompt that requires a tool
        # prompt = "list the available tools"
        prompt = "subtract 8 from 3"
        # prompt = "what is 5 plus 12 using the calculator?" # Another example
        print(f"\n--- Starting Servers ---\n")

        try:
            await session.start_servers()  # Start all servers

            print(f"\n--- Sending Request ---\nPrompt: {prompt}\n")
            # The send_request method now includes its own try/finally for cleanup
            result = await session.send_request(prompt, debug=True, show_stop_reason=True)
        finally:
            await session.stop_servers()  # Stop all servers




        print("\n--- LLM Interaction Result ---")
        print(f"Success: {result['success']}")
        if result["success"]:
            print("\nFinal Response:")
            print(result['response'])
            if result["tool_calls"]:
                print("\nTool Calls Made:")
                for i, call in enumerate(result["tool_calls"], 1):
                    outcome = f"Result: {call.get('result', 'N/A')}" if 'error' not in call else f"Error: {call.get('error', 'Unknown')}"
                    print(f"  {i}. Tool: {call['tool_name']}")
                    print(f"     Args: {json.dumps(call['tool_args'])}")
                    print(f"     Outcome: {outcome}")
            if result["stop_reason_info"]:
                 print(f"\nStop Reason: {result['stop_reason_info'].get('reason', 'N/A')}")

        else:
            print(f"\nError: {result['error']}")

        # Print messages only if debug was True during the call and they exist
        if result.get("messages"):
            print("\n--- Message History (Debug) ---")
            for msg in result["messages"]:
                 role = msg.get('role', 'unknown')
                 content = msg.get('content', '')
                 if isinstance(content, list): # Handle tool use/result content blocks
                      content_str = "\n".join([str(c) for c in content])
                 else:
                      content_str = str(content)
                 print(f"[{role.upper()}]:\n{content_str}\n---")

    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        # Graceful shutdown is now handled within send_request's finally block
        # If the interruption happens *before* send_request finishes,
        # asyncio.run() will handle cancelling the task and triggering the finally.
        # If it happens during cleanup, cleanup might be interrupted.
        if main_task and not main_task.done():
             print("Attempting to cancel the main task...")
             main_task.cancel()
             # Allow loop to process cancellation - This might not fully run if loop is closing
             # try:
             #      asyncio.get_event_loop().run_until_complete(main_task)
             # except asyncio.CancelledError:
             #      print("Main task cancelled.")
             # except RuntimeError: # Loop might already be closed
             #      pass

    except Exception as e:
         print(f"\n--- An unhandled error occurred in main execution ---")
         # Print the traceback for the specific error
         import traceback
         traceback.print_exc()
    finally:
        # The explicit psutil cleanup is removed.
        # Cleanup is now handled by the `finally` block within `LLMSession.send_request`
        # which calls `LLMSession.cleanup_servers`.
        print("\n--- Main execution finished ---")
        # Any lingering processes would indicate a failure in the async cleanup logic itself.
        print("Exiting.")