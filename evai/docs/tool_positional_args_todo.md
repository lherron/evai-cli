# Tool Positional Arguments Implementation

## Task Description
Modify the `run_tool` function to handle command-line style parameters for tool functions. The current implementation expects a dictionary of keyword arguments, but we need to adapt it to work with positional arguments from the command line.

For example, running `evai tools run subtract 8 5` should run the `tool_subtract` method in the subtract tool with `8` as the first parameter and `5` as the second parameter.

## Implementation Plan
[X] Modify the `run_tool` function in `tool_storage.py` to accept positional arguments
[X] Update the `run` command in `tools.py` to handle positional arguments
[X] Create tests to verify the changes
[X] Run the tests to ensure everything works correctly

## Changes Made

### 1. Modified `run_tool` function in `tool_storage.py`
- Added support for positional arguments using `*args`
- Added type conversion based on function signature
- Maintained backward compatibility with keyword arguments

### 2. Updated `run` command in `tools.py`
- Added support for positional arguments using Click's `nargs=-1` parameter
- Maintained backward compatibility with `--param` option
- Updated the help text to explain both usage patterns

### 3. Created tests
- Created unit tests for the `run_tool` function
- Created integration tests for the CLI

## Testing
All tests are passing, which verifies that:
- Positional arguments work correctly
- Keyword arguments still work (backward compatibility)
- Mixed arguments raise an appropriate error

## Example Usage
```bash
# Using positional arguments
evai tools run subtract 8 5
# Result: 3.0

# Using keyword arguments (backward compatibility)
evai tools run subtract --param minuend=8 --param subtrahend=5
# Result: 3.0
``` 