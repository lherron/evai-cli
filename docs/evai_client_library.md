# EVAI Client Library Documentation

## Overview

The EVAI Client Library provides a Python interface for interacting with large language models (LLMs) and managing Model Control Protocol (MCP) servers. It is designed to facilitate seamless integration of LLMs with custom tools, enabling developers to build powerful command-line interfaces, automation scripts, or other applications. The library is part of the EVAI CLI project and leverages the `evai.llm` and `evai.mcp.client_tools` modules.

This documentation covers the core components, installation, configuration, usage examples, and best practices for working with the EVAI Client Library.

## Installation

To install the EVAI Client Library, use pip to install the `evai-cli` package:

```bash
pip install evai-cli
```

Ensure you have Python 3.12 or higher installed, as specified in the project's `pyproject.toml`.

### Dependencies

The library depends on the following packages (listed in `requirements.txt`):
- `anthropic>=0.18.0` - For LLM interactions with Anthropic's Claude models.
- `mcp>=1.6.0` - For MCP server communication.
- `python-dotenv>=1.0.0` - For environment variable management.
- `psutil>=5.9.0` - For process management.

## Core Components

### `LLMSession` (from `evai.llm`)

The `LLMSession` class is the primary interface for orchestrating interactions between users, LLMs, and MCP-based tools. It manages server lifecycles and processes LLM requests with optional tool integration.

#### Initialization

```python
from evai.llm import LLMSession
from evai.mcp.client_tools import MCPServerFactory

# Load server configurations
servers_config_path = os.getenv("EVAI_SERVERS_CONFIG", "servers_config.json")
servers = MCPServerFactory.load_servers(servers_config_path)

# Initialize the LLM session
llm_session = LLMSession(servers=servers)
```

- **Parameters**:
  - `servers`: A list of `MCPServer` instances (can be empty if no tools are needed).
- **Requirements**:
  - The `ANTHROPIC_API_KEY` environment variable must be set for Claude interactions.

#### Key Methods

1. **`start_servers()`**
   - Starts all configured MCP servers asynchronously.
   - Example:
     ```python
     await llm_session.start_servers()
     ```

2. **`send_request(user_prompt, system_prompt=None, debug=False, show_stop_reason=False, allowed_tools=None, structured_output_tool=None)`**
   - Sends a prompt to the LLM and processes the response, potentially invoking tools.
   - Parameters:
     - `user_prompt` (str): The user's input prompt sent to the LLM as a "user" role message.
     - `system_prompt` (Optional[str]): An optional string providing context or instructions to the LLM, passed as the `system` parameter to the Anthropic API. Defaults to `None`.
     - `debug` (bool): If `True`, includes detailed logging and message history in the result.
     - `show_stop_reason` (bool): If `True`, includes stop reason details in the result (useful for debugging).
     - `allowed_tools` (list[str] or None): Optional list of tool names to restrict tool usage.
     - `structured_output_tool` (Optional[Dict[str, Any]]): Optional dictionary defining a tool for structured output, with keys `name` (str), `description` (str), and `input_schema` (dict). If provided, this tool is included in the tools list sent to Anthropic, and its use results in a structured response available in `result["structured_response"]`.
   - Returns: A dictionary with the response structure (see below).
   - Example:
     ```python
     result = await llm_session.send_request(
         user_prompt="What is the capital of France?",
         debug=False,
         allowed_tools=["get_location_info"]
     )
     ```

3. **`stop_servers()`**
   - Stops all running MCP servers and cleans up resources.
   - Example:
     ```python
     await llm_session.stop_servers()
     ```

#### Result Structure

The `send_request` method returns a dictionary with the following fields:

```python
{
    "success": bool,                     # Indicates if the request was successful
    "response": str,                     # The final text response from the LLM
    "error": str or None,                # Error message if success=False
    "structured_response": dict or None, # Structured data from structured_output_tool if used
    "tool_calls": list[dict],            # List of executed tool calls
    "stop_reason_info": dict or None,    # Details about why the LLM stopped (if show_stop_reason=True)
    "messages": list or None             # Full message history (if debug=True)
}
```

- **`tool_calls` Entry Example**:
  ```python
  {
      "tool_name": "get_location_info",
      "tool_args": {"location": "France"},
      "result": "The capital of France is Paris."
  }
  ```
- **`stop_reason_info` Example**:
  ```python
  {
      "reason": "end_turn",
      "stop_sequence": None
  }
  ```

##### Structured Output Usage

To request structured output, provide a `structured_output_tool` dictionary and instruct the LLM to use it via `system_prompt` or `user_prompt`. The tool's `input_schema` defines the expected output structure. When the LLM uses this tool, the structured data is returned in `result["structured_response"]` and the conversation ends immediately after capturing the structured output.

**Important:** When the LLM uses the structured output tool, the conversation loop terminates immediately after capturing the structured data. This ensures you get a clean structured response without additional text output.

**Example using Pydantic:**

```python
from pydantic import BaseModel, Field
from datetime import datetime as dt
from typing import Dict, Any
import json
import asyncio
from evai.llm import LLMSession
from evai.mcp.client_tools import MCPServerFactory

# Define a Pydantic model for person information
class PersonInfo(BaseModel):
    name: str = Field(description="The person's full name")
    age: int = Field(description="The person's age")
    occupation: str = Field(description="The person's job or occupation")

async def run_structured_example():
    """Run the structured output example."""
    print(f"\n--- Sending Request with Structured Output ---\n")

    # Get current date for age calculation
    now = dt.now()
    structured_prompt = f"Use subtract tool to calculate the age and then Extract the following information: name is John Doe, birth_year is 1970, occupation is Software Engineer. Current date is {now}"
    
    # Generate schema from Pydantic model
    person_schema = {
        "name": "extract_person_info",
        "description": "Extract structured information about a person",
        "input_schema": PersonInfo.model_json_schema()
    }
    
    # Initialize LLM session
    servers = MCPServerFactory.load_servers()
    session = LLMSession(servers=servers)
    
    try:
        # Start servers
        await session.start_servers()
        
        # Send request with structured output tool
        structured_result = await session.send_request(
            user_prompt=structured_prompt, 
            debug=True, 
            show_stop_reason=True,
            structured_output_tool=person_schema
        )
        
        # Print results
        print("\n--- Structured Output LLM Interaction Result ---")
        print(f"Success: {structured_result['success']}")
        if structured_result["success"]:
            print("\nFinal Response:")
            print(structured_result['response'])
            
            if structured_result["structured_response"]:
                print("\nStructured Response:")
                print(json.dumps(structured_result["structured_response"], indent=2))
                
                # Demonstrate parsing the response with Pydantic
                try:
                    parsed_person = PersonInfo(**structured_result["structured_response"])
                    print("\nParsed with Pydantic:")
                    print(f"Name: {parsed_person.name}")
                    print(f"Age: {parsed_person.age}")
                    print(f"Occupation: {parsed_person.occupation}")
                except Exception as e:
                    print(f"\nError parsing with Pydantic: {str(e)}")
                
            if structured_result["stop_reason_info"]:
                print(f"\nStop Reason: {structured_result['stop_reason_info'].get('reason', 'N/A')}")
        else:
            print(f"\nError: {structured_result['error']}")
            
        return structured_result
            
    finally:
        # Clean up
        await session.stop_servers()

if __name__ == "__main__":
    asyncio.run(run_structured_example())

This example demonstrates:
- Using Pydantic models to define structured data schemas
- Automatic schema generation from Pydantic models
- Type-safe data handling and validation
- Integration with LLM tools for age calculation
- Proper error handling and cleanup
- Detailed output formatting and validation

The structured output will be returned in the following format:
```python
{
    "name": "John Doe",
    "age": 55,  # Calculated from birth year
    "occupation": "Software Engineer"
}
```

Benefits of using Pydantic for structured output:
1. **Type Safety**: Pydantic provides runtime type checking and validation
2. **Schema Generation**: Automatic JSON Schema generation with `model_json_schema()`
3. **Documentation**: Field descriptions are included in the schema
4. **Validation**: Automatic validation of incoming data against the model
5. **IDE Support**: Better code completion and type hints in modern IDEs
6. **Extensibility**: Easy to add custom validators and field types

### `MCPServerFactory` (from `evai.mcp.client_tools`)

This utility class creates `MCPServer` instances from a configuration file.

#### Usage

```python
from evai.mcp.client_tools import MCPServerFactory

servers = MCPServerFactory.load_servers("servers_config.json")
```

- **Parameters**:
  - `config_path` (str, optional): Path to the configuration file. Defaults to `EVAI_SERVERS_CONFIG` environment variable or `"servers_config.json"`.
- **Returns**: A list of `MCPServer` instances.
- **Behavior**: Returns an empty list if the config file is missing or invalid, with appropriate logging.

### `MCPServer` (from `evai.mcp.client_tools`)

The `MCPServer` class manages the lifecycle of an MCP server and provides methods for tool interaction.

#### Initialization

Typically instantiated via `MCPServerFactory`, but can be created manually:

```python
from evai.mcp.client_tools import MCPServer

server = MCPServer(
    name="example_server",
    config={"command": "python", "args": ["-m", "evai.mcp.server", "tool_config.json"]}
)
```

#### Key Methods

1. **`initialize()`**
   - Starts the server process and establishes a connection.
   - Example:
     ```python
     await server.initialize()
     ```

2. **`list_tools()`**
   - Retrieves a list of available tools from the server.
   - Returns: List of `MCPTool` objects.
   - Example:
     ```python
     tools = await server.list_tools()
     for tool in tools:
         print(f"Tool: {tool.name}, Description: {tool.description}")
     ```

3. **`execute_tool(tool_name, arguments, retries=1, delay=1.0)`**
   - Executes a specified tool with given arguments.
   - Parameters:
     - `tool_name` (str): Name of the tool to execute.
     - `arguments` (dict): Arguments for the tool.
     - `retries` (int): Number of retry attempts (default: 1).
     - `delay` (float): Delay between retries in seconds (default: 1.0).
   - Returns: The tool's execution result.
   - Example:
     ```python
     result = await server.execute_tool("echo", {"message": "Hello"})
     ```

4. **`cleanup()`**
   - Terminates the server process and releases resources.
   - Example:
     ```python
     await server.cleanup()
     ```

#### `MCPTool`

Represents a tool hosted by an MCP server.

```python
class MCPTool:
    def __init__(self, name, server_name, description, input_schema):
        self.name = name                # str: Tool name
        self.server_name = server_name  # str: Hosting server name
        self.description = description  # str: Tool description
        self.input_schema = input_schema  # dict: JSON schema for tool inputs
```

## Configuration

### Configuration Files

MCP servers are configured via a JSON file (default: `servers_config.json`):

```json
{
  "mcpServers": {
    "example_server": {
      "command": "python",
      "args": ["-m", "evai.mcp.server", "tool_config.json"],
      "env": {
        "CUSTOM_VAR": "value"
      }
    }
  }
}
```

- **Fields**:
  - `command`: The executable to run the server (e.g., `python`).
  - `args`: List of arguments for the command.
  - `env`: Optional dictionary of environment variables.

### Environment Variables

- **`ANTHROPIC_API_KEY`** (required): API key for Anthropic's Claude models.
- **`EVAI_SERVERS_CONFIG`** (optional): Path to the MCP servers configuration file (defaults to `servers_config.json`).

Set these in a `.env` file or your environment:

```bash
# .env.example
ANTHROPIC_API_KEY=your_api_key_here
EVAI_SERVERS_CONFIG=servers_config.json
```

Load them using `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```

## Usage Examples

### Example 1: Basic LLM Interaction with Tools

From `evai.cli.commands.llm`:

```python
import asyncio
import os
import logging
from evai.llm import LLMSession
from evai.mcp.client_tools import MCPServerFactory

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Load server configurations
    config_path = os.getenv("EVAI_SERVERS_CONFIG", "servers_config.json")
    servers = MCPServerFactory.load_servers(config_path)
    if not servers:
        logger.warning("No MCP servers found. Proceeding without tools.")

    # Initialize LLM session
    session = LLMSession(servers=servers)
    
    try:
        # Start servers
        await session.start_servers()
        
        # Send request
        result = await session.send_request(
            user_prompt="What is the capital of France?",
            debug=False,
            allowed_tools=None  # Use all available tools
        )
        
        if result["success"]:
            logger.info(f"Response: {result['response']}")
            if result["tool_calls"]:
                for call in result["tool_calls"]:
                    logger.info(f"Tool {call['tool_name']} called with {call['tool_args']}")
        else:
            logger.error(f"Error: {result['error']}")
    
    finally:
        # Clean up
        await session.stop_servers()

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: Custom Client with Error Handling

From the additional example provided:

```python
import asyncio
import os
import logging
from evai.llm import LLMSession
from evai.mcp.client_tools import MCPServerFactory

async def generate_response(prompt: str) -> str:
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Load server configurations
    servers = []
    config_path = os.getenv("EVAI_SERVERS_CONFIG", "servers_config.json")
    servers = MCPServerFactory.load_servers(config_path)
    if not servers:
        logger.warning("No MCP servers found. Proceeding without tools.")

    # Initialize LLM session
    llm_session = LLMSession(servers=servers)
    await llm_session.start_servers()

    try:
        # Send request
        result = await llm_session.send_request(
            user_prompt=prompt,
            debug=False,
            allowed_tools=None
        )
        await llm_session.stop_servers()

        if not result["success"]:
            error_message = result.get("error", "Unknown error")
            logger.error(f"Failed to generate response from LLM: {error_message}")
            raise Exception(error_message)

        markdown_response = result["response"]
        logger.info("Generated Markdown response")
        return markdown_response

    except Exception as e:
        logger.error(f"Failed to generate response using LLMSession: {e}")
        raise

if __name__ == "__main__":
    response = asyncio.run(generate_response("Summarize the weather today"))
    print(response)
```

### Example 3: Using Structured Output

```python
import asyncio
import os
import json
from typing import Dict, Any
from evai.llm import LLMSession
from evai.mcp.client_tools import MCPServerFactory
from dotenv import load_dotenv

async def get_structured_data():
    # Load environment variables
    load_dotenv()
    
    # Configure structured output tool
    structured_output_tool = {
        "name": "extract_data",
        "description": "Extract structured data from the input",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "population": {"type": "integer"},
                "landmarks": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["location", "population", "landmarks"]
        }
    }
    
    # Load server configurations
    servers = MCPServerFactory.load_servers()
    
    # Initialize LLM session
    session = LLMSession(servers=servers)
    
    try:
        # Start servers
        await session.start_servers()
        
        # Send request with structured output tool
        result = await session.send_request(
            user_prompt="Provide information about Paris, France.",
            system_prompt="Extract structured data about the location using the extract_data tool.",
            structured_output_tool=structured_output_tool,
            debug=False
        )
        
        if result["success"]:
            if result["structured_response"]:
                # We have structured data
                print("Structured data:")
                print(json.dumps(result["structured_response"], indent=2))
                return result["structured_response"]
            else:
                # No structured data, just text response
                print("No structured data received.")
                print("Text response:", result["response"])
                return None
        else:
            print(f"Error: {result['error']}")
            return None
            
    finally:
        # Clean up
        await session.stop_servers()

if __name__ == "__main__":
    asyncio.run(get_structured_data())

## Error Handling

The library provides robust error handling:

1. **Server Initialization Failures**:
   - Handled within `MCPServer.initialize()`. Logs errors and resets server state.
   - Check `server._initialized` to verify success.

2. **Tool Execution Failures**:
   - `MCPServer.execute_tool()` includes a retry mechanism (configurable via `retries` and `delay`).
   - Errors are logged and returned in the `tool_calls` list with an `"error"` key.

3. **LLM API Errors**:
   - Caught in `send_request()` and returned as `{"success": False, "error": str(e)}`.
   - Common issues include missing `ANTHROPIC_API_KEY`.

4. **Resource Cleanup**:
   - Use `try`/`finally` blocks to ensure `stop_servers()` or `cleanup()` is called:
     ```python
     try:
         await session.start_servers()
         result = await session.send_request("Test prompt")
     finally:
         await session.stop_servers()
     ```

## Best Practices

- **Environment Setup**: Always load environment variables at the start of your application using `load_dotenv()`.
- **Logging**: Configure logging to capture detailed information, especially in debug mode.
- **Server Management**: Start servers only when needed and stop them promptly to free resources.
- **Tool Filtering**: Use `allowed_tools` to limit tool usage for specific requests, improving performance and security.
- **Error Recovery**: Check `result["success"]` and handle errors gracefully, logging details for debugging.
- **System Instructions**: Use the `system_prompt` parameter for providing consistent guidance to the LLM across user interactions, improving the reliability of responses.
- **Structured Output**: When you need data in a specific format, use the `structured_output_tool` to get consistently structured responses that can be directly used in your application without parsing text.

## Troubleshooting

- **"ANTHROPIC_API_KEY not set"**: Ensure the environment variable is defined in `.env` or your shell.
- **No Tools Available**: Verify `servers_config.json` exists and is correctly formatted.
- **Server Initialization Fails**: Check the `command` and `args` in your config file for typos or missing executables.