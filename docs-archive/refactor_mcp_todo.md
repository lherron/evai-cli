# MCP Refactoring Plan

## Task
Refactor the MCP server code by:
1. Moving prompt registration into a new `mcp_prompts.py` file
2. Moving tool registration into a new `mcp_tools.py` file

## Current Structure
- `mcp_server.py` contains:
  - `_register_built_in_tools()` - Registers built-in tools
  - `_register_tools()` - Registers all available tools
  - `_register_tool_tool()` - Helper to register a single tool
  - `_register_prompts()` - Registers all available prompts

## Refactoring Steps
[X] Create `mcp_prompts.py` file
[X] Move prompt-related code from `mcp_server.py` to `mcp_prompts.py`
[X] Create `mcp_tools.py` file
[X] Move tool-related code from `mcp_server.py` to `mcp_tools.py`
[X] Update `mcp_server.py` to import and use the new modules
[X] Test the refactored code

## Implementation Details

### mcp_prompts.py (COMPLETED)
- Contains:
  - The `PROMPTS` dictionary
  - A function to register all prompts
  - The `analyze_file` prompt function

### mcp_tools.py (COMPLETED)
- Contains:
  - Functions to register built-in tools
  - Functions to register custom tools
  - The tool implementation functions

### mcp_server.py (UPDATED)
- Now:
  - Imports the new modules
  - Calls the registration functions from the new modules
  - Keeps the server initialization and running logic

## Summary of Changes
1. Created `mcp_prompts.py` with:
   - Moved the `PROMPTS` dictionary
   - Added a `register_prompts()` function
   - Moved the `analyze_file` prompt function

2. Created `mcp_tools.py` with:
   - Added a `register_built_in_tools()` function for built-in tools
   - Added a `register_tools()` function for all available tools
   - Added a `register_tool()` function to register a single tool
   - Moved all tool implementation functions

3. Updated `mcp_server.py`:
   - Removed the old registration methods
   - Added imports for the new modules
   - Updated the `__init__` method to use the new registration functions
   - Kept the `read_file` method needed by the prompts module

## Testing Results
The refactored code was tested by creating a server instance, which completed successfully. The warnings about tools and prompts already existing are expected because the server is initialized twice in the test script (once in the global scope and once in the create_server function).

The refactoring is complete and the code is now more modular and easier to maintain. 