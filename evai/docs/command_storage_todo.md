# Command Directory & YAML Management Implementation

## Task Description
Implement functionality to manage a command repository under the user's home directory:

1. Create a function `get_command_dir(command_name)` in a new file `evai/command_storage.py` that:
   - Returns the path: `~/.evai/commands/<command-name>`
   - Creates the directory if it doesn't exist

2. Implement `load_command_metadata(path) -> dict` and `save_command_metadata(path, data: dict) -> None` that:
   - Use PyYAML to parse/write YAML to a file named `command.yaml` in that directory
   - Handle errors gracefully

3. Create tests in `tests/test_metadata.py` to test these functions

## Implementation Plan

[X] Create `evai/command_storage.py` with the required functions
[X] Install PyYAML if not already installed
[X] Create `tests/test_metadata.py` with tests for the functions
[X] Ensure tests pass and follow best practices

## Implementation Details

### `get_command_dir(command_name)`
- Use `os.path.expanduser` to get the user's home directory
- Create the directory structure if it doesn't exist using `os.makedirs`
- Return the path as a string

### `load_command_metadata(path) -> dict`
- Open and read the YAML file at the given path
- Parse it using PyYAML
- Return the parsed data as a dictionary
- Handle file not found and YAML parsing errors

### `save_command_metadata(path, data: dict) -> None`
- Convert the dictionary to YAML using PyYAML
- Write it to the file at the given path
- Create parent directories if they don't exist
- Handle file writing errors

### Testing
- Test that `get_command_dir` creates the directory if it doesn't exist
- Test that `load_command_metadata` correctly loads YAML data
- Test that `save_command_metadata` correctly saves YAML data
- Test error handling for both functions

## Summary of Implementation

We have successfully implemented the Command Directory & YAML Management functionality for the EVAI CLI project. The implementation includes:

1. A function `get_command_dir(command_name)` that:
   - Returns the path to the command directory
   - Creates the directory if it doesn't exist
   - Validates the command name

2. Functions `load_command_metadata(path)` and `save_command_metadata(path, data)` that:
   - Load and save YAML metadata for commands
   - Handle errors gracefully
   - Provide detailed error messages

3. Comprehensive tests in `tests/test_metadata.py` that:
   - Test the functionality of all functions
   - Test error handling
   - Use temporary directories to avoid affecting the user's actual home directory

All tests are passing, and the implementation follows best practices for Python code, including:
- Type hints
- Comprehensive docstrings
- Proper error handling
- Logging
- Clean code structure

The implementation is now ready for the next step: implementing the `command add` workflow. 