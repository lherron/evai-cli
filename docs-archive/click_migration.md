# Migration from argparse to click

## Task Overview
We need to switch the EVAI CLI from using argparse to click. This involves:
- Adding click as a dependency
- Refactoring the CLI implementation in cli.py
- Updating the tests to work with click
- Ensuring all existing functionality continues to work

## Progress Tracking
- [X] Add click as a dependency in pyproject.toml
- [X] Refactor cli.py to use click instead of argparse
- [X] Update tests to work with click
- [X] Verify that all functionality continues to work

## Implementation Summary
1. Added click and pyyaml as dependencies in pyproject.toml
2. Refactored cli.py to use click's decorators and command groups:
   - Created a `cli()` function decorated with `@click.group`
   - Added version option with `@click.version_option`
   - Updated `main()` to call `cli()` and handle the case when no arguments are provided
3. Updated the tests to work with click's testing utilities:
   - Used `click.testing.CliRunner` to invoke the CLI
   - Updated assertions to match click's output format
   - Added a test for the case when no arguments are provided
4. Verified that all tests pass successfully
5. Manually tested the CLI to ensure it behaves correctly

## Benefits of Using Click
- More declarative and easier to read syntax with decorators
- Built-in support for command groups and subcommands
- Better help text formatting
- Easier testing with the CliRunner utility
- More robust argument parsing and validation

## Next Steps
The migration from argparse to click is now complete. The next step would be to implement the Command Directory & YAML Management functionality as outlined in the todo.md file. 