# TODO: Implementation Steps for EVAI CLI Custom Commands Integration

A comprehensive, step-by-step checklist to guide the development of the EVAI CLI, command storage, and MCP integration. Mark each step as completed once done.

---

## 1. Project Scaffolding
- [X] **Create Project Structure**  
  - [X] Create `__init__.py` inside `evai/`.
  - [X] Create `cli.py` with a basic `main()` function.
- [X] **Command-Line Entry Point**  
  - [X] Decide on `argparse`, `click`, or similar.
  - [X] Implement minimal CLI that prints help/version info.
- [X] **Basic Testing**  
  - [X] Create `tests/` folder with a simple test (`test_cli.py`).
  - [X] Verify that invoking CLI with `python -m evai.cli` works.

---

## 2. Command Directory & YAML Management
- [X] **Utility Functions**  
  - [X] `get_command_dir(command_name)`: Return (and create if needed) `~/.evai/commands/<command-name>/`.
  - [X] `load_command_metadata(path) -> dict`: Load YAML from `command.yaml`.
  - [X] `save_command_metadata(path, data: dict) -> None`: Write YAML data to `command.yaml`.
- [X] **Testing**  
  - [X] Write `test_metadata.py` to cover file I/O, YAML parse/write, and directory creation.
  - [X] Confirm that all tests pass before proceeding.

---

## 3. `command add` Workflow (Initial Version)
- [X] **CLI Subcommand**  
  - [X] Implement `evai command add <command-name>` in `cli.py`.
- [X] **File Creation**  
  - [X] Within this subcommand, create default `command.yaml` with standard fields and placeholders.
  - [X] Create default `command.py` with a stub `def run(**kwargs): print("Hello World")`.
- [X] **Testing**  
  - [X] In `test_add_command.py`, confirm the directory and files are created with correct content.

---

## 4. Editing of `command.yaml`
- [X] **Non-interactive editing**
- [X] **Environment Variable `$EDITOR`**  
  - [X] Check `$EDITOR`; default to `vi` if not set.
- [X] **Editing Loop**
  - [X] Open the newly created `command.yaml` in the editor.
  - [X] Parse YAML on save.  
  - [X] If invalid, prompt user to fix it. Offer to abort if needed.
- [X] **Testing**  
  - [X] Mock the editor call in `test_add_command.py` or a new test file to simulate user edits.
  - [X] Validate re-editing behavior on invalid YAML.

---

## 5. Implementation Editing & Lint Checking
- [X] **Editor Invocation**  
  - [X] Open `command.py` in `$EDITOR`.
- [X] **Lint Check**  
  - [X] Run `flake8` on `command.py` programmatically.
  - [X] If lint errors, show them to the user and re-open editor.
  - [X] Offer user the option to abort if unresolved.
- [X] **Testing**  
  - [X] Create `test_edit_implementation.py` to ensure a known lint error triggers re-edit.
  - [X] Confirm passing code requires no further edits.

---

## 6. Command Execution & MCP Exposure
- [ ] **List & Run**  
  - [ ] `evai command list`: Scan `~/.evai/commands` and list command names.
  - [ ] `evai command run <command-name>`: Dynamically import `command.py` and call `run(**kwargs)`.
- [ ] **MCP Server**  
  - [ ] Create a minimal server that:
    - [ ] Scans `command.yaml` files.
    - [ ] For each command with `mcp_integration.enabled = true`, exposes `/commands/<command-name>` (POST).
    - [ ] Executes corresponding `run()` with JSON data as kwargs.
- [ ] **Testing**  
  - [ ] `test_list_and_run.py`: CLI tests for listing and running commands.
  - [ ] `test_mcp_exposure.py`: Confirm commands are reachable via MCP server, verifying correct endpoints and data flow.

---

## 7. Optional LLM Interaction
- [ ] **LLM for Default Metadata**  
  - [ ] `generate_default_metadata_with_llm(command_name)`: Populate YAML metadata from an LLM.
  - [ ] Fallback to basic defaults if LLM is unreachable or disabled.
- [ ] **LLM in Command Execution**  
  - [ ] If `llm_interaction.enabled` is `true`, integrate a call to the LLM inside `command.py` logic as needed.
- [ ] **Testing**  
  - [ ] `test_llm.py`: Mock the LLM.  
  - [ ] Ensure graceful fallback on LLM failures.

---

## 8. Final Polishing & Integration Tests
- [ ] **Integration Testing**  
  - [ ] Create tests that simulate full workflow: adding a command, editing files, lint checking, executing via CLI, executing via MCP.
  - [ ] Ensure robust error handling for each step.
- [ ] **User Acceptance**  
  - [ ] Confirm typical user can navigate the CLI steps easily.
  - [ ] Ensure error messaging is clear and user-friendly.
- [ ] **Final Validation**  
  - [ ] Run entire test suite.  
  - [ ] Verify all features are consistent with requirements.  
  - [ ] Document usage for future maintainers.

---

## 9. Release or Local Deployment
- [ ] **Installation**  
  - [ ] Confirm local install with `pip install .` or equivalent works.
- [ ] **Packaging**  
  - [ ] (Optional) Publish to PyPI if desired, or maintain locally.
- [ ] **Documentation**  
  - [ ] Provide a README with usage, environment variables, and known limitations.

---

**End of Checklist**