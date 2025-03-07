# MCP Integration Scratchpad

## Task
Implement the `run_llm_command_with_mcp` function in the EVAI CLI to integrate with the Model Context Protocol (MCP).

## Plan
1. [X] Understand the MCP Python SDK and its capabilities
2. [X] Implement the `run_llm_command_with_mcp` function
3. [X] Create a default MCP server implementation
4. [X] Update the requirements.txt file to include MCP dependencies
5. [X] Create tests for the MCP integration

## Implementation Details

### MCP Integration
The MCP integration consists of two main components:
1. The `run_llm_command_with_mcp` function in `evai/cli/commands/llm.py` that connects to an MCP server and sends prompts
2. A default MCP server implementation in `evai/cli/mcp_server.py` that provides a simple interface to Claude

The integration follows these steps:
1. The CLI command calls `run_llm_command_with_mcp` with the user's prompt
2. The function connects to the MCP server using the stdio transport
3. It tries to use a default prompt if available, or falls back to a tool or resource
4. The MCP server processes the prompt using Claude and returns the response

### Configuration
The MCP server path can be configured using the `MCP_SERVER_PATH` environment variable. If not set, it defaults to `evai/cli/mcp_server.py`.

### Testing
Tests have been created to verify both the direct Claude API call and the MCP integration. The tests use mocks to avoid making actual API calls.

## Future Improvements
- [ ] Add more configuration options for the MCP server
- [ ] Support for custom MCP servers
- [ ] Add more tools and prompts to the default MCP server
- [ ] Implement streaming responses
- [ ] Add support for file uploads and other MCP features 