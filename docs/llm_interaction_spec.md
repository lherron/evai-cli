Okay, here is a markdown description of the `llm_interaction.py` interface, designed for an LLM user.

```markdown
# llm_interaction.py Interface Description

## Overview

This module provides the core logic for interacting with a Large Language Model (LLM) (specifically Anthropic's Claude 3.7 Sonnet) and integrating with Model Context Protocol (MCP) servers to enable tool use. It handles the conversation flow, tool discovery, tool execution via MCP, and returns structured results.

**Key Goal:** To abstract the complexities of LLM calls and MCP interactions, providing a clean interface to send a prompt and receive a final response, potentially after several rounds of tool use.

## Core Component: `LLMSession`

The primary class for interacting with the LLM and tools.

### Initialization

```python
from evai.llm_interaction import LLMSession, MCPServer, Configuration

# 1. Load server configurations (typically from servers_config.json)
config = Configuration()
server_configs = config.load_config("servers_config.json") # Or your config path

# 2. Create MCPServer instances
servers = [
    MCPServer(name, srv_config)
    for name, srv_config in server_configs.get("mcpServers", {}).items()
]

# 3. Instantiate LLMSession
session = LLMSession(servers=servers)
```

-   **`__init__(self, servers: list[MCPServer])`**:
    -   Requires a list of `MCPServer` objects. These objects represent the configured MCP servers that provide tools.
    -   Requires the `ANTHROPIC_API_KEY` environment variable to be set for authentication with the Anthropic API.

### Connection Management

```python
import asyncio

async def main():
    # ... (setup session as above)
    try:
        await session.initialize()
        # ... use session.send_request ...
    finally:
        await session.cleanup_servers()

asyncio.run(main())
```

-   **`async initialize(self)`**:
    -   **Must be called** (`await`) before making any requests (`send_request`).
    -   Establishes connections to all configured MCP servers defined during initialization.
-   **`async cleanup_servers(self)`**:
    -   Should be called (`await`) when the session is no longer needed (e.g., in a `finally` block).
    -   Closes connections to MCP servers and cleans up resources (like subprocesses).

### Main Interaction Method

```python
async def send_request(self, prompt: str, debug: bool = False, show_stop_reason: bool = False) -> Dict[str, Any]
```

-   This is the primary method to send a user prompt to the LLM and get a final response.
-   **Parameters**:
    -   `prompt` (str): The user's input/question.
    -   `debug` (bool, optional): If `True`, enables more verbose logging during the process. Defaults to `False`.
    -   `show_stop_reason` (bool, optional): If `True`, includes the LLM's stop reason in the output. Defaults to `False`.
-   Handles the entire interaction loop, including:
    -   Sending the prompt to the LLM.
    -   Discovering available tools from initialized MCP servers.
    -   Facilitating LLM's decision to use tools.
    -   Executing tools via the corresponding `MCPServer`.
    -   Sending tool results back to the LLM.
    -   Repeating tool use if necessary.
    -   Returning the final consolidated response from the LLM.
    -   Cleaning up any lingering processes to prevent resource leaks.
-   **Returns** (Dict[str, Any]): A dictionary containing the results of the interaction:
    -   `"success"` (bool): `True` if the request completed without fatal errors, `False` otherwise.
    -   `"response"` (Optional[str]): The final text response from the LLM after all interactions (including tool use). `None` if an error occurred before getting a response.
    -   `"error"` (Optional[str]): An error message if `success` is `False`. `None` otherwise.
    -   `"tool_calls"` (List[Dict]): A list of dictionaries, each representing a tool call made during the interaction. Each dictionary has:
        -   `"tool_name"` (str): The name of the tool called.
        -   `"tool_args"` (Dict): The arguments passed to the tool.
        -   `"result"` (Optional[str]): The processed result returned by the tool if successful.
        -   `"error"` (Optional[str]): An error message if the tool execution failed.
    -   `"stop_reason_info"` (Optional[Dict]): Information about why the LLM stopped generating (e.g., `{"reason": "end_turn"}`). `None` if not available or `show_stop_reason` is `False`.
    -   `"messages"` (List[Dict]): The complete history of messages exchanged with the LLM during this request (useful for debugging).

## Helper Functions

-   **`extract_tool_result_value(result_str: str) -> str`**:
    -   A utility function to attempt parsing the raw string result received from an MCP tool execution into a more readable format. It tries to extract text content or format JSON nicely.
    -   Used internally by `LLMSession.send_request` to populate the `"result"` field in the `"tool_calls"` list.

## Usage Example

```python
import asyncio
import os
from evai.llm_interaction import LLMSession, MCPServer, Configuration

async def run_llm_request(user_prompt: str):
    # Ensure ANTHROPIC_API_KEY is set in environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        return

    session = None
    try:
        # 1. Load server configurations
        config = Configuration()
        # Ensure servers_config.json exists or handle FileNotFoundError
        try:
            server_configs = config.load_config("servers_config.json")
            servers = [
                MCPServer(name, srv_config)
                for name, srv_config in server_configs.get("mcpServers", {}).items()
            ]
        except FileNotFoundError:
            print("Warning: servers_config.json not found. Running without tools.")
            servers = []
        except Exception as e:
            print(f"Error loading server config: {e}")
            return

        # 2. Instantiate LLMSession
        session = LLMSession(servers=servers)

        # 3. Initialize connections
        print("Initializing MCP connections...")
        await session.initialize()
        print("Initialization complete.")

        # 4. Send the request
        print(f"Sending prompt: '{user_prompt}'")
        result = await session.send_request(prompt=user_prompt, debug=False)
        print("Request processed.")

        # 5. Process the result
        if result["success"]:
            print("\n--- LLM Response ---")
            print(result["response"])

            if result["tool_calls"]:
                print("\n--- Tool Calls ---")
                for i, call in enumerate(result["tool_calls"], 1):
                    print(f"Call {i}:")
                    print(f"  Tool: {call['tool_name']}")
                    print(f"  Args: {call['tool_args']}")
                    if "result" in call:
                        print(f"  Result: {call['result']}")
                    elif "error" in call:
                        print(f"  Error: {call['error']}")
        else:
            print("\n--- Error ---")
            print(result["error"])

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 6. Cleanup
        if session and session.initialized:
            print("\nCleaning up server connections...")
            await session.cleanup_servers()
            print("Cleanup complete.")

if __name__ == "__main__":
    # Example usage:
    # Make sure servers_config.json is present and configured
    # and ANTHROPIC_API_KEY is set in your environment.
    # Example: export ANTHROPIC_API_KEY='your_key_here'
    prompt_to_run = "What is 10 minus 4 using the subtract tool?"
    asyncio.run(run_llm_request(prompt_to_run))
```

## Assumptions & Prerequisites

1.  **Environment Variable**: The `ANTHROPIC_API_KEY` environment variable must be set.
2.  **MCP Servers**: For tool usage, MCP servers must be defined in a configuration file (like `servers_config.json`) and be runnable by the `MCPServer` class.
3.  **Async Environment**: The library requires an `asyncio` environment to run (`async`/`await`).
```



