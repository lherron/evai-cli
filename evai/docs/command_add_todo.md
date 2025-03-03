# Command Add Workflow Implementation

## Task Description
Implement the `command add` workflow for the EVAI CLI, which allows users to create custom commands that can be executed via the CLI or exposed through the MCP server.

## Completed Steps
[X] Implemented the `evai command add <command-name>` subcommand in `cli.py`
[X] Created functionality to generate default `command.yaml` with standard fields and placeholders
[X] Created functionality to generate default `command.py` with a stub function
[X] Added tests to confirm the directory and files are created with correct content
[X] Ensured all tests pass

## Implementation Details

### CLI Subcommand
Added a new subcommand group `command` with a subcommand `add` that takes a command name as an argument. The subcommand:
1. Validates the command name (alphanumeric, hyphens, and underscores only)
2. Creates the command directory using `get_command_dir`
3. Generates default metadata and saves it to `command.yaml`
4. Creates a default implementation in `command.py`
5. Provides feedback to the user about the created files

### Default Files
- `command.yaml`: Contains metadata about the command, including name, description, parameters, and integration settings
- `command.py`: Contains a simple implementation with a `run` function that prints "Hello World" and returns a success status

### Testing
Created `test_add_command.py` with tests that:
1. Verify the command is created successfully with valid names
2. Verify the command fails with invalid names
3. Check that the directory and files are created with the correct content

## Next Steps
The next phase of the implementation will be to add interactive editing of the `command.yaml` file:
- Check for the `$EDITOR` environment variable and default to `vi` if not set
- Open the newly created `command.yaml` in the editor
- Parse the YAML after saving
- If invalid, prompt the user to fix it or abort
- Add tests to simulate user edits and validate re-editing behavior

After that, we'll implement similar functionality for editing the `command.py` file, including lint checking with `flake8`. 