from dotenv import load_dotenv


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import asyncio
import json
import logging
import os
import shutil
import traceback
from contextlib import AsyncExitStack
from typing import Any, Optional


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


class MCPConfiguration:
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