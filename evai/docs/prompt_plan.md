Below is a comprehensive plan that evolves in multiple iterations, starting from a high-level blueprint, then breaking the tasks into more detailed, smaller steps until each part can be implemented safely and cleanly. Finally, you will find a collection of prompts that you can feed into a code-generation LLM (e.g., ChatGPT, Claude, etc.) to implement each step in a test-driven manner, ensuring no large leaps in complexity.

1. High-Level Blueprint
	1.	Initialize Core Project Structure
	•	Create a Python package or directory (evai/) for the CLI.
	•	Set up a minimal setup.py or a pyproject.toml if needed.
	•	Create a basic CLI entry point (evai) using argparse or click.
	2.	Implement Command File Management
	•	Define a directory structure under ~/.evai/commands/<command-name>/.
	•	Specify the required YAML file (command.yaml) and Python file (command.py).
	•	Implement a utility for reading, writing, and validating command metadata from YAML.
	3.	Add Command Creation Workflow
	•	Implement evai command add <command-name> to:
	1.	Generate default YAML metadata.
	2.	Prompt user to review and edit the metadata in $EDITOR.
	3.	Prompt user to implement the Python code in $EDITOR.
	4.	Perform post-editing validation (YAML schema check, flake8 lint check).
	5.	Handle re-editing if any validation fails.
	4.	MCP Integration
	•	Implement a minimal MCP server that picks up all commands from ~/.evai/commands/*/command.yaml.
	•	Expose each command at an endpoint, e.g., /commands/<command-name>.
	5.	LLM Interaction
	•	(Optional step, but included for completeness.)
	•	Include a submodule for LLM calls (e.g., Anthropic or OpenAI).
	•	Hook LLM calls when the command’s llm_interaction metadata is enabled.
	6.	Testing, Linting, and Validation
	•	Add unit tests for YAML metadata reading/writing.
	•	Add integration tests ensuring commands are recognized by evai and the MCP server.
	•	Validate the user editing/linting cycle with flake8 and a basic YAML schema check.
	7.	Deployment / Packaging
	•	Confirm everything runs with a local install.
	•	(Optionally) Release to PyPI or a local environment.

2. Breaking the Blueprint into Iterative Chunks

Below is a more detailed breakdown of the same blueprint, with each chunk building on the previous chunk.
	1.	Chunk 1: Project Scaffolding
	•	Set up basic Python project.
	•	Create minimal CLI entry point using argparse (or your chosen CLI library).
	•	Verify evai can run and display a help message.
	2.	Chunk 2: Command Directory & YAML Management
	•	Implement a helper function to locate ~/.evai/commands/<command-name>/.
	•	Implement reading/writing YAML metadata (using PyYAML or equivalent).
	•	Create unit tests to verify metadata read/write.
	3.	Chunk 3: command add Workflow (Initial Version)
	•	Implement evai command add <command-name> that:
	•	Creates the directory structure.
	•	Generates a default command.yaml.
	•	Generates a stub command.py.
	•	Writes minimal content.
	•	Add basic tests.
	4.	Chunk 4: Interactive Editing
	•	Add $EDITOR invocation to let the user edit the YAML.
	•	Validate YAML structure after edit.
	•	If validation fails, keep re-invoking $EDITOR.
	5.	Chunk 5: Implementation Editing & Lint Checking
	•	Prompt user to open command.py in $EDITOR.
	•	Validate Python code via flake8.
	•	If linting fails, re-prompt user.
	6.	Chunk 6: Command Execution & MCP Exposure
	•	Make the evai CLI able to list commands.
	•	Add a minimal embedded MCP server.
	•	Expose each command at a route for remote invocation.
	•	Write tests verifying command execution from CLI and from MCP.
	7.	Chunk 7: Optional LLM Interaction
	•	Integrate an LLM client to propose default metadata.
	•	If llm_interaction.enabled is true, call the LLM from within the command logic.
	•	Add tests for the LLM interaction path.
	8.	Chunk 8: Polishing & Final Testing
	•	Write final integration tests and ensure everything is consistent.
	•	Confirm TDD with all tests passing.

3. Breaking Chunks into Smaller Steps

Below is another iteration, splitting each chunk into smaller, incremental steps that are feasible to implement safely, with strong testing at each stage.
	1.	Chunk 1: Project Scaffolding
	1.	Create evai/ folder and basic Python package structure.
	2.	Add __init__.py.
	3.	Add cli.py using argparse or click.
	4.	Implement a placeholder main() that prints a version or help.
	5.	Add a simple test (test_cli.py) that checks for the printed help message.
	6.	Confirm the test passes.
	2.	Chunk 2: Command Directory & YAML Management
	1.	Implement a function: get_command_dir(command_name) to build ~/.evai/commands/<command-name>.
	2.	Implement load_command_metadata(path) and save_command_metadata(path, data).
	3.	Use PyYAML to parse and write metadata.
	4.	Write tests (test_metadata.py) for each function to ensure correct directory resolution and file read/write.
	3.	Chunk 3: command add Workflow (Initial Version)
	1.	Add subcommand: evai command add <command-name>.
	2.	Within that, create the command directory.
	3.	Generate default YAML metadata (in memory).
	4.	Generate a stub Python implementation file.
	5.	Save the files to disk.
	6.	Test this by verifying the directory and files exist.
	4.	Chunk 4: Interactive Editing
	1.	After stub files are created, call $EDITOR to open command.yaml.
	2.	On save, parse the updated YAML.
	3.	If invalid, print an error and reopen $EDITOR.
	4.	Write tests to simulate successful and failing edits (possibly mocking $EDITOR calls).
	5.	Chunk 5: Implementation Editing & Lint Checking
	1.	Prompt user to open command.py in $EDITOR.
	2.	Run flake8 programmatically on command.py.
	3.	If lint errors exist, prompt the user to re-edit.
	4.	Test with a good Python file and a file with a known lint error.
	6.	Chunk 6: Command Execution & MCP Exposure
	1.	In the CLI, add evai command list to show available commands.
	2.	Add evai command run <command-name> --param1=... --param2=... to execute the command directly.
	3.	Implement a minimal MCP server that runs in a background thread or in the main thread, listing available commands.
	4.	Test it by calling the CLI subcommands, verifying output.
	7.	Chunk 7: Optional LLM Interaction
	1.	Implement a function generate_default_metadata_with_llm(command_name) that queries an LLM.
	2.	Use the response to populate default command metadata.
	3.	Add tests that mock the LLM client, ensuring fallback if the LLM is unreachable.
	8.	Chunk 8: Polishing & Final Testing
	1.	Add final integration tests across all subcommands and flows.
	2.	Ensure TDD coverage is near 100%.
	3.	Validate final usage from a typical user perspective (UAT).

4. Prompts for a Code-Generation LLM (Test-Driven Implementation)

Below is a set of sequential prompts you can feed into a code-generation LLM (such as ChatGPT, Claude, etc.). Each prompt is self-contained but references the outputs from prior steps. They are designed to walk through implementing the entire project in small, test-driven increments. You would copy each prompt (as a single code block) into your LLM, let it generate the code or confirm it, then proceed to the next prompt. The final prompt wires everything together, ensuring no hanging or orphaned code.

Prompt 1: Project Scaffolding

You are implementing an EVAI CLI in Python. In this step, create a minimal project scaffold:

- Create a folder structure: `evai/` with an `__init__.py`.
- Add a `cli.py` that uses `argparse` and has a `main()` function. 
- When `python -m evai.cli` is run, it should print a version or help text. 
- Create a test file `tests/test_cli.py` that checks the CLI prints some expected text (like "EVAI CLI version 0.1").

Please:
1. Write the code for `evai/__init__.py`.
2. Write the code for `evai/cli.py`.
3. Write the `tests/test_cli.py`.
4. Include instructions (a shell command or two) on how to run these tests with `pytest`.
Use best practices, including a `if __name__ == "__main__": main()` guard in `cli.py`.

Prompt 2: Command Directory & YAML Management

Building on the previous code, add functionality to manage a command repository under the user’s home directory:

1. Implement a function `get_command_dir(command_name)` in a new file `evai/command_storage.py` that returns the path: `~/.evai/commands/<command_name>`. It should create the directory if it doesn’t exist.
2. Implement `load_command_metadata(path) -> dict` and `save_command_metadata(path, data: dict) -> None` in the same file. Use PyYAML to parse/write YAML to a file named `command.yaml` in that directory.
3. Update your test suite in a new file `tests/test_metadata.py` to test these three functions.
4. Provide a final updated tree structure of the project, including new files, and the commands to run tests.

Make sure tests pass and we follow best practices for Python code.

Prompt 3: command add <command-name> Workflow (Initial Version)

Extend the CLI with a subcommand: `evai command add <command-name>`.

1. In `cli.py`, add a subcommand group `command` with a subcommand `add`.
2. When called, it should:
   - Use `get_command_dir` to find/create the directory.
   - Create a default Python file `command.py` with a simple `def run(**kwargs): print("Hello World")`.
   - Create a default YAML file `command.yaml` with fields:
     ```
     name: <command-name>
     description: "Default description"
     params: []
     hidden: false
     disabled: false
     mcp_integration:
       enabled: true
       metadata:
         endpoint: ""
         method: "POST"
         authentication_required: false
     llm_interaction:
       enabled: false
       auto_apply: true
       max_llm_turns: 15
     ```
3. Write tests in `tests/test_add_command.py` verifying that after running `evai command add <command-name>`, the directory is created with the above files containing the correct content.

Provide the updated code changes and the test code.

Prompt 4: Interactive Editing of command.yaml

Add interactive editing support for `command.yaml`:

1. After creating the default metadata, invoke an editor for the user to review/edit. Respect the environment variable `$EDITOR`, or default to `vi` if `$EDITOR` is not set.
2. When the user saves and exits, parse the YAML again. If invalid, re-open the editor until the user fixes it or chooses to abort.
3. In `tests/test_add_command.py`, add a test that mocks the editor call to simulate user changes. For the real editor invocation, you can use a subprocess call.

Provide updated code. Include any new helper functions and test code. Ensure the user can exit gracefully if they want to abort.

Prompt 5: Implementation Editing & Lint Checking

Now add a similar interactive editing step for `command.py`. Then perform a lint check:

1. Once `command.yaml` is finalized, open `command.py` in the editor.
2. After the user saves, run `flake8` (or a Python wrapper around it). 
3. If errors are found, display them and re-open the editor. 
4. Allow user to abort if they can’t fix the issues.
5. Create `tests/test_edit_implementation.py` that checks if a file with a known lint error triggers a re-edit.
6. Provide updated code for everything needed, including how you handle the lint check programmatically in Python.

Prompt 6: Command Execution & MCP Exposure

Next, enable listing and executing commands, and expose them via an MCP server:

1. Add `evai command list` to scan `~/.evai/commands` and print available command names.
2. Add `evai command run <command-name>` with optional `--param key=value` pairs. This should:
   - Load `command.py` dynamically (e.g., via importlib).
   - Call the `run(**kwargs)`.
3. Implement a minimal MCP server that reads all `command.yaml` files, and for each command with `mcp_integration.enabled=True`, expose a route like `/commands/<command-name>`. 
   - The route handles a POST request with JSON data. 
   - Translate that data into keyword args for `run()`.
4. Add tests: `test_list_and_run.py` for the CLI behaviors, `test_mcp_exposure.py` for verifying the MCP routes respond correctly. 
5. Provide updated code and instructions on how to run the MCP server for local testing.

Prompt 7: Optional LLM Interaction

Implement optional LLM interaction for default metadata generation and in-command usage:

1. Add a function `generate_default_metadata_with_llm(command_name)` that makes a mock or real LLM call, returning YAML metadata. If the call fails, use standard defaults.
2. Modify `evai command add <command-name>` so that it offers to call `generate_default_metadata_with_llm` for initial metadata if `llm_interaction.enabled` is set.
3. In command execution, if `llm_interaction.enabled=True`, optionally call an LLM inside `command.py` if the user so desires. This is not strictly necessary but can be tested with a mock LLM.
4. Add or update tests in `test_llm.py`, ensuring that if the LLM is unreachable, we gracefully revert to basic defaults.

Return the updated code, focusing on minimal or mock LLM calls, plus the new/updated tests.

Prompt 8: Final Polishing & Integration Tests

Time to finalize and polish:

1. Add final integration tests that create a command, edit it, lint it, execute it, run it from MCP, etc.
2. Ensure best practices: handle exceptions gracefully, provide clear error messages.
3. Confirm TDD with all tests passing.
4. Provide instructions for running the entire test suite, manually verifying the workflow, and any final details needed to consider this project “complete.”

Return the final integrated code. 

These prompts are designed to build the EVAI CLI Custom Commands Integration in small, test-driven increments, ensuring each step is validated before moving on.