# Tool Storage Renaming Task

## Overview
We are renaming the "command" entity to "tool" in the tool_storage.py file (previously command_storage.py). The module has already been renamed, but we need to update all references to "command" within the file and update any imports or usages in other files.

## Changes Needed in tool_storage.py

### Function Renames
- `get_command_dir` -> `get_tool_dir`
- `load_command_metadata` -> `load_tool_metadata`
- `save_command_metadata` -> `save_tool_metadata`
- `edit_command_metadata` -> `edit_tool_metadata`
- `edit_command_implementation` -> `edit_tool_implementation`
- `run_lint_check` -> No change needed (function is generic)
- `list_commands` -> `list_tools`
- `import_command_module` -> `import_tool_module`
- `run_command` -> `run_tool`

### Path Changes
- `~/.evai/commands/` -> `~/.evai/tools/`
- `command.yaml` -> `tool.yaml`
- `command.py` -> `tool.py`

### Variable/Parameter Renames
- `command_name` -> `tool_name`
- `command_dir` -> `tool_dir`
- `commands` -> `tools`
- Other similar variable names

## Files That Need Updates
1. evai/cli/commands/llmadd.py
2. evai/cli/commands/command.py (may need to be renamed to tool.py)
3. evai/cli/cli.py
4. evai/mcp/mcp_server.py
5. tests/test_list_and_run.py

## Implementation Strategy
1. First update tool_storage.py
2. Then update imports and function calls in other files
3. Rename any files that need to be renamed (like command.py -> tool.py)
4. Update tests

## Progress
- [X] Update tool_storage.py
- [X] Update tests/test_list_and_run.py
- [X] Update evai/cli/commands/llmadd.py
- [X] Create evai/cli/commands/tool.py (replacing command.py)
- [X] Update evai/cli/cli.py
- [X] Update evai/mcp/mcp_server.py
- [X] Delete the old command.py file

## Summary
We have successfully completed the renaming of the "command" entity to "tool" throughout the codebase. This included:

1. Updating all function names in tool_storage.py
2. Updating all variable names and paths in tool_storage.py
3. Creating a new tool.py file to replace command.py
4. Updating imports and function calls in all dependent files
5. Deleting the old command.py file

The renaming is now complete and the codebase should be consistent in its use of "tool" terminology. 

## Verification
We have verified that the changes work correctly by:

1. Running the CLI with the `--help` flag to confirm that the tool commands are properly registered
2. Running `tool --help` to verify that all tool subcommands are available
3. Checking that the tool directory is created correctly at `~/.evai/tools/`
4. Creating a new test tool with `tool add test-tool2` and confirming it was created successfully
5. Listing available tools with `tool list` and confirming our test tool appears
6. Running the test tool with `tool run test-tool2` and confirming it executes correctly

All tests passed successfully, confirming that the renaming from "command" to "tool" has been implemented correctly throughout the codebase. 

# Externalize Sample Tool Templates

## Task Description
Externalize the sample tool.py and tool.yaml templates that are currently hardcoded in the `evai/cli/commands/tool.py` file. This will make them easier to maintain and update.

## Current Implementation
Currently, the sample templates are hardcoded in the `add` command in `evai/cli/commands/tool.py`:

1. Default tool.yaml template:
```python
default_metadata = {
    "name": tool_name,
    "description": "Default description",
    "params": [],
    "hidden": False,
    "disabled": False,
    "mcp_integration": {
        "enabled": True,
        "metadata": {
            "endpoint": "",
            "method": "POST",
            "authentication_required": False
        }
    },
    "llm_interaction": {
        "enabled": False,
        "auto_apply": True,
        "max_llm_turns": 15
    }
}
```

2. Default tool.py template:
```python
"""Custom tool implementation."""


def run(**kwargs):
    """Run the tool with the given arguments."""
    print("Hello World")
    return {"status": "success"}
```

## Plan

1. [X] Create a templates directory in the evai package
2. [X] Create sample_tool.py and sample_tool.yaml files
3. [X] Update the tool_storage.py to load these templates
4. [X] Update the tool.py command to use the externalized templates
5. [X] Update the llmadd.py command to use the externalized templates

## Implementation Steps

1. [X] Create templates directory and files
   - Created `evai/templates` directory
   - Created `evai/templates/sample_tool.py`
   - Created `evai/templates/sample_tool.yaml`

2. [X] Add functions to tool_storage.py to load the templates
   - Added `load_sample_tool_py()` function
   - Added `load_sample_tool_yaml(tool_name)` function
   - Added `TEMPLATES_DIR` constant

3. [X] Update the add command in tool.py to use the new functions
   - Updated the `add` command to use the externalized templates
   - Added fallback to hardcoded templates if loading fails

4. [X] Update the llmadd command in llmadd.py to use the new functions
   - Updated the `llmadd` command to use the externalized templates
   - Added fallback to hardcoded templates if loading fails

## Testing

To test the changes:

1. Run `evai tool add test-tool` to create a new tool
2. Verify that the tool is created successfully
3. Run `evai tool llmadd test-llm-tool` to create a new tool with LLM assistance
4. Verify that the tool is created successfully

## Conclusion

The sample tool templates have been successfully externalized to the `evai/templates` directory. This makes them easier to maintain and update in the future. The code now loads these templates from the filesystem instead of having them hardcoded in the source code. 