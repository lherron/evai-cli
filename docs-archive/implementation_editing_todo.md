# Implementation Editing and Lint Checking

## Task Description
Implement the functionality to edit the command implementation file (`command.py`) and perform lint checking using flake8.

## Steps
[X] Add function `edit_command_implementation(command_dir)` to `command_storage.py`
  - Open the command.py file in the user's preferred editor
  - Return a boolean indicating success

[X] Add function `run_lint_check(command_dir)` to `command_storage.py`
  - Run flake8 on the command.py file
  - Return a tuple with a boolean indicating success and the error output if any

[X] Update the `add` command in `cli.py` to:
  - After metadata editing is complete, open the implementation file for editing
  - Run lint check on the implementation file
  - If lint check fails, show errors and prompt user to re-edit or abort
  - Loop until lint check passes or user aborts

[X] Create test file `tests/test_edit_implementation.py` with tests for:
  - Successful editing of implementation file
  - File not found error
  - Subprocess error
  - Successful lint check
  - Failed lint check
  - flake8 not found error
  - File not found error for lint check

[X] Update `tests/test_add_command.py` to include tests for:
  - Successful editing and lint checking
  - Lint failure followed by success
  - Lint failure and user abort

[X] Update `evai/docs/todo.md` to mark the implementation editing and lint checking as completed

## Implementation Details

### Command Storage Functions
- `edit_command_implementation(command_dir)`: Opens the command.py file in the user's preferred editor and returns a boolean indicating success.
- `run_lint_check(command_dir)`: Runs flake8 on the command.py file and returns a tuple with a boolean indicating success and the error output if any.

### CLI Command
The `add` command now includes:
1. Metadata editing (existing functionality)
2. Implementation editing
3. Lint checking with re-editing loop

### Testing
- `test_edit_implementation.py`: Tests for the implementation editing and lint checking functions
- Updated `test_add_command.py`: Tests for the full workflow including implementation editing and lint checking

## Completion Status
All tasks for implementation editing and lint checking have been completed successfully. 