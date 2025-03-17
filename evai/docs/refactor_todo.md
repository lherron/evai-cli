# Refactoring `async_run_mcp_command` Function

## Current Structure Analysis
The `async_run_mcp_command` function is quite large and handles multiple responsibilities:
1. MCP server connection setup
2. Anthropic client initialization
3. Tool discovery and display
4. Conversation management
5. Claude API calls
6. Tool execution
7. Response processing
8. Error handling

## Refactoring Plan
Break down the function into smaller, more focused functions:

### Proposed Functions
1. ✅ `async_setup_mcp_session` - Handle MCP server connection and session initialization
2. ✅ `get_anthropic_client` - Create and return the Anthropic client
3. ✅ `async_fetch_available_tools` - Get and display available tools from MCP server
4. ✅ `async_call_claude_with_tools` - Make API calls to Claude with error handling
5. ✅ `async_process_claude_response` - Process Claude's response and update message history
6. ✅ `async_execute_tool_calls` - Execute tool calls and format results
7. ✅ `async_run_conversation_loop` - Main conversation loop orchestrating the other functions

## Implementation Strategy
- ✅ Extract each function with clear input/output parameters
- ✅ Maintain state through function parameters rather than shared variables
- ✅ Improve error handling at each level
- ✅ Add better type hints
- ✅ Reduce code duplication

## Improvements Made
1. ✅ Properly handled context managers for MCP session
2. ✅ Added debug parameter to control debug output
3. ✅ Improved resource cleanup with proper finally blocks
4. ✅ Added CLI option for debug mode

## Next Steps
1. Test the refactored code to ensure it works as expected
2. Consider adding more detailed documentation
3. Consider adding more robust error handling for specific error types 