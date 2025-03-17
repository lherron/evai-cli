# LLM Stop Reasons Implementation

## Task
Update the LLM command to handle all possible stop reasons from the Anthropic API:
- "end_turn": the model reached a natural stopping point
- "max_tokens": we exceeded the requested max_tokens or the model's maximum
- "stop_sequence": one of your provided custom stop_sequences was generated
- "tool_use": the model invoked one or more tools

Currently, the code only handles "tool_use" but needs to be updated to handle all possible stop reasons.

## Current Implementation
The current implementation in `evai/cli/commands/llm.py` only checks for `stop_reason == "tool_use"` to determine if the model wants to use a tool. It doesn't handle or provide feedback for the other stop reasons.

## Plan

[X] Review the current implementation in `evai/cli/commands/llm.py`
[X] Modify the `async_process_claude_response` function to handle all stop reasons
[X] Add appropriate logging for each stop reason
[X] Update the conversation loop to handle each stop reason appropriately
[X] Update the direct Claude API call to also handle stop reasons
[X] Add a new command-line option `--show-stop-reason` to display stop reason information in the output

## Implementation Details

### For "end_turn"
- [X] Log that the model reached a natural stopping point
- [X] Continue with normal response processing

### For "max_tokens"
- [X] Log a warning that the response was truncated due to token limit
- [X] Add a note to the final response indicating it was truncated
- [X] Continue with normal response processing

### For "stop_sequence"
- [X] Log which custom stop sequence was generated
- [X] Include information about the stop sequence in the response
- [X] Continue with normal response processing

### For "tool_use"
- [X] Keep the existing implementation
- [X] Ensure proper handling of tool calls

### General Changes
- [X] Create a helper function to process each stop reason
- [X] Add appropriate logging for each case
- [X] Ensure the user is informed about why the response ended

## Summary of Changes
1. Updated `async_process_claude_response` to handle all stop reasons and return stop reason information
2. Added a new `stop_reason_info` dictionary to track information about the stop reason
3. Updated the conversation loop to display stop reason information when needed
4. Added a new `--show-stop-reason` command-line option to display stop reason information in the output
5. Updated both the MCP and direct API call paths to handle stop reasons consistently 