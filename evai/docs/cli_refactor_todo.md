# CLI Refactoring Task

## Task Description
Move the click decorators for llmadd into llmadd.py and have click add all commands in the "commands" submodule automatically.

## Steps Taken

[X] Move the click decorator from cli.py to llmadd.py
- Added `@click.command()` and `@click.argument("command_name")` decorators to the llmadd function in llmadd.py

[X] Update cli.py to automatically add all commands from the commands submodule
- Removed the explicit llmadd command definition from cli.py
- Added an `import_commands()` function that:
  - Gets the package path for the commands module
  - Iterates through all modules in the commands package
  - Imports each module
  - Finds all Click commands in each module
  - Adds each command to the command group
- Called `import_commands()` to register all commands

[X] Update the __init__.py file in the commands directory
- Removed the explicit import of llmadd
- Removed the __all__ list
- Added a comment explaining that commands will be automatically imported by the CLI

[X] Tested the changes
- Verified that the CLI still works correctly
- Confirmed that the llmadd command is properly registered under the command group

## Benefits of the Changes

1. **Modularity**: Each command is now self-contained in its own module, with its own click decorators.
2. **Extensibility**: New commands can be added simply by creating a new module in the commands directory with click-decorated functions.
3. **Maintainability**: The CLI code is now more organized and easier to maintain.
4. **Discoverability**: All commands are automatically discovered and registered, reducing the chance of errors.

## Future Improvements

- Consider adding a way to specify the order of commands in the help output
- Add support for command aliases
- Consider adding a way to group commands into subgroups 