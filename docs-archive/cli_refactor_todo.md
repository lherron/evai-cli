# CLI Refactoring Task

## Task Description
Move all commands for the cli.group called "command" into a new command.py submodule in the commands directory.

## Steps Taken
[X] Create a new file `evai/cli/commands/command.py`
[X] Move all command functions from `cli.py` to `command.py`
[X] Update `cli.py` to remove the command functions
[X] Test the refactored code to ensure it works correctly

## Implementation Details

1. Created a new file `evai/cli/commands/command.py` with all the command functions:
   - `add`: Add a new custom command
   - `edit`: Edit an existing command
   - `list`: List available commands
   - `run`: Run a command with the given arguments

2. Removed these functions from `cli.py` and added a comment indicating where they were moved to.

3. The existing import mechanism in `cli.py` already handles importing commands from the `commands` directory, so no additional changes were needed for the import logic.

4. Tested the refactored code to ensure all commands are still accessible and working correctly.

## Result
The refactoring was successful. All commands are now properly organized in the `commands` directory, making the codebase more modular and easier to maintain.

The command group structure is preserved:
```
evai command add <command_name>
evai command edit <command_name>
evai command list
evai command run <command_name>
```

All functionality remains the same, but the code is now better organized. 