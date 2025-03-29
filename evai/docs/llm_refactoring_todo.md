# LLM Command Refactoring Task

## Goal
Refactor `evai/cli/commands/llm.py` to separate LLM/MCP interaction logic from CLI display logic.

## Design
1. **`evai/cli/commands/llm.py`:** Contains the Click command definition, argument parsing, user-facing output (using Rich), and calls to the LLM interaction library.
2. **`evai/llm_interaction.py`:** Contains functions to interact with the Anthropic API and the MCP server, returning data structures without any console printing.

## Status

[X] Create `evai/llm_interaction.py` with core LLM interaction functionality
[X] Move LLM/MCP interaction logic from `llm.py` to `llm_interaction.py`
[X] Create structured return types in `llm_interaction.py` to return data rather than printing
[X] Refactor `llm.py` to use the new `llm_interaction.py` library
[X] Add a proper display layer in `llm.py` for tool calls and responses

## Key Changes

### In `llm_interaction.py`
- Created functions that return data structures instead of printing to console
- Added proper typing to function parameters and return values
- Converted console print statements to logging calls
- Extracted shared functionality into reusable functions
- Added a primary public function `execute_llm_request` as the main entry point

### In `llm.py`
- Removed all LLM/MCP interaction logic
- Imported and used functions from `llm_interaction.py`
- Added a dedicated function to display tool calls
- Enhanced error handling with better user feedback
- Preserved the existing CLI interface with Click

## Next Steps

- [ ] Write unit tests for `llm_interaction.py` (mock API calls)
- [ ] Write unit tests for `llm.py` (mock `execute_llm_request` calls)
- [ ] Review and update docstrings for both files
- [ ] Consider making server_params configurable (not hardcoded)
- [ ] Improve error handling for common failure cases

## Benefits of Refactoring

1. **Separation of Concerns**: Clear separation between interaction logic and display logic
2. **Testability**: Each component can be tested independently
3. **Reusability**: LLM interaction library can be used by other components
4. **Maintainability**: Easier to maintain and extend each component separately
5. **Consistency**: Standardized return types and error handling 