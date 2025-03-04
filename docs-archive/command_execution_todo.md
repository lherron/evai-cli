# Command Execution & MCP Exposure

## Implementation Plan

### Command Listing and Execution
- [X] Implement `evai command list` to scan the command directory and list available commands
- [X] Implement `evai command run <command-name>` to execute a command
- [X] Add parameter support for command execution

### MCP Server Integration
- [X] Create a minimal MCP server using the MCP Python SDK
- [X] Scan command directory and load command metadata
- [X] Expose commands as MCP tools
- [X] Handle requests for command execution with JSON data

### Claude Desktop Integration
- [X] Add built-in tools for command management
  - [X] `add_command`: Create a new command with metadata and implementation
  - [X] `list_commands`: List all available commands
  - [X] `edit_command_implementation`: Edit the implementation of an existing command
  - [X] `edit_command_metadata`: Edit the metadata of an existing command

### Testing
- [X] Create test file for CLI command listing and execution
- [X] Create test file for MCP server integration
- [X] Fix test mocking for MCP server integration

## Current Status

All tasks for Command Execution & MCP Exposure have been completed successfully, including enhancements for Claude Desktop integration.

## Implementation Details

### Command Listing and Execution
- Commands are listed by scanning the `~/.evai/commands` directory
- Commands are executed by dynamically importing the command module and calling its `run` function
- Parameters are passed to the command as keyword arguments

### MCP Server Integration
- The MCP server is created using the MCP Python SDK
- Commands are registered as MCP tools with their metadata
- Requests for command execution are handled by calling the command's `run` function

### Claude Desktop Integration
- Built-in tools are registered in the MCP server for command management
- The `add_command` tool creates a new command with metadata and implementation
- The `list_commands` tool lists all available commands
- The `edit_command_implementation` tool edits the implementation of an existing command
- The `edit_command_metadata` tool edits the metadata of an existing command

### Test Fixes
- Fixed mocking of the MCP SDK in the tests
- Properly mocked command directory structure and metadata loading
- Added tests for built-in tools

## Dependencies
- MCP Python SDK
- Python importlib for dynamic module loading
- JSON for metadata handling

## Summary of Changes
1. Added functions to `command_storage.py` to:
   - List available commands
   - Dynamically import command modules
   - Run commands with arguments

2. Added CLI subcommands to `cli.py`:
   - `evai command list` to list available commands
   - `evai command run <command-name>` to run a command
   - `evai server` to start the MCP server

3. Created a new `mcp_server.py` file for MCP integration:
   - `EVAIServer` class to manage the MCP server
   - Registration of commands as MCP tools
   - Error handling for command execution

4. Enhanced the MCP server with built-in tools for Claude Desktop:
   - `add_command` tool to create new commands
   - `list_commands` tool to list available commands
   - `edit_command_implementation` tool to edit command implementation
   - `edit_command_metadata` tool to edit command metadata

5. Added tests:
   - `test_list_and_run.py` for CLI command listing and execution
   - `test_mcp_exposure.py` for MCP server integration and built-in tools

All tasks for Command Execution & MCP Exposure have been completed successfully, with additional enhancements for Claude Desktop integration. 