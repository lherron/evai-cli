Below is a detailed proposal to add functionality for creating new commands in the EVAI CLI, mirroring the existing tool creation process. The new commands will reside in ~/.evai/commands, be loaded on EVAI startup, and be registered in Click like the existing command structure. This proposal includes a step-by-step approach with specific instructions, code snippets, and a final prompt tailored for a less intelligent sub-LLM to implement incrementally, stopping for feedback at each step.
Proposal to Add Command Creation Functionality to EVAI CLI
General Approach
To meet your requirements, we'll extend the EVAI CLI by:
Mirroring the Tool Structure: Commands will follow a similar directory and file structure to tools (~/.evai/commands/<command_name>/ with command.yaml and command.py), leveraging existing utilities where possible.
Adding Command Storage: Create a new command_storage.py module to handle command-specific file operations, parallel to tool_storage.py.
Enhancing CLI: Introduce a commands group with an add subcommand, similar to tools add, to create new commands interactively.
Dynamic Registration: Modify cli.py to load and register user-defined commands in Click at startup, ensuring they integrate seamlessly with the existing structure.
Ensuring Specificity: Each step will be discrete, with clear instructions and code, stopping for feedback to keep the implementation on track.
This approach ensures that commands are treated as first-class citizens in the CLI, with a creation process akin to tools, and are automatically available upon startup.
Discrete Steps for Implementation
Step 1: Create command_storage.py Module
Purpose: Establish a dedicated module for command file operations, mirroring tool_storage.py.
Instructions:
Create a new file evai/command_storage.py.
Define functions to manage the ~/.evai/commands directory, load/save metadata, list commands, and import command modules.
Use pathlib.Path for cross-platform compatibility, similar to tool_storage.py.
Code:
python


"""Command storage utilities for EVAI CLI."""

import os
import yaml
from pathlib import Path
import importlib.util
import logging

logger = logging.getLogger(__name__)

COMMANDS_DIR = Path.home() / ".evai" / "commands"

def get_command_dir(command_name: str) -> Path:
    """Get the directory path for a command and create it if it doesn't exist."""
    command_dir = COMMANDS_DIR / command_name
    command_dir.mkdir(parents=True, exist_ok=True)
    return command_dir

def load_command_metadata(path: Path) -> dict:
    """Load command metadata from command.yaml."""
    yaml_path = path / "command.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Command metadata file not found: {yaml_path}")
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def save_command_metadata(path: Path, data: dict) -> None:
    """Save command metadata to command.yaml."""
    yaml_path = path / "command.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def list_commands() -> list[dict]:
    """List all available commands."""
    if not COMMANDS_DIR.exists():
        return []
    commands = []
    for cmd_dir in COMMANDS_DIR.iterdir():
        if cmd_dir.is_dir():
            try:
                metadata = load_command_metadata(cmd_dir)
                if not metadata.get("disabled", False):
                    commands.append({
                        "name": metadata.get("name", cmd_dir.name),
                        "description": metadata.get("description", "No description"),
                        "path": cmd_dir
                    })
            except Exception as e:
                logger.warning(f"Error loading command {cmd_dir.name}: {e}")
    return commands

def import_command_module(command_name: str):
    """Dynamically import a command module."""
    cmd_dir = get_command_dir(command_name)
    py_path = cmd_dir / "command.py"
    if not py_path.exists():
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    spec = importlib.util.spec_from_file_location(f"evai.commands.{command_name}", py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
Stop for Feedback: After implementing this step, verify that the module functions work as expected (e.g., get_command_dir creates directories, load_command_metadata reads YAML files correctly). Provide feedback before proceeding.
Step 2: Create Command Templates
Purpose: Define default templates for command.yaml and command.py, stored in evai/templates/, to streamline command creation.
Instructions:
Create evai/templates/sample_command.yaml with a metadata structure matching the tools' format but tailored for commands.
Create evai/templates/sample_command.py with a run(**kwargs) function, as required for dynamic registration.
Code:
evai/templates/sample_command.yaml:
yaml
name: "{command_name}"
description: "Default description"
arguments: []
options: []
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
evai/templates/sample_command.py:
python
"""Custom command implementation."""

def run(**kwargs):
    """Run the command with the given arguments."""
    print("Hello World")
    return {"status": "success"}
Stop for Feedback: Confirm that the templates are correctly placed and formatted. Test loading them manually to ensure they parse without errors. Provide feedback before moving on.
Step 3: Add commands Group and add Subcommand to cli.py
Purpose: Extend the CLI with a commands group and an add subcommand to create new commands, similar to tools add.
Instructions:
In evai/cli/cli.py, add a commands group using AliasedGroup.
Define an add subcommand that creates the command directory, saves default metadata, and writes the implementation file.
Reuse existing utilities from command_storage.py and adapt logic from tools.py.
Code:
Update evai/cli/cli.py:
python
# ... (existing imports remain unchanged)
from evai.command_storage import get_command_dir, save_command_metadata

# ... (existing cli group remains unchanged)

@cli.group(cls=AliasedGroup)
def commands():
    """Manage user-defined commands."""
    pass

@commands.command()
@click.argument("command_name")
def add(command_name):
    """Add a new custom command."""
    try:
        cmd_dir = get_command_dir(command_name)
        if list(cmd_dir.iterdir()):  # Check if directory is non-empty
            click.echo(f"Command '{command_name}' already exists.", err=True)
            sys.exit(1)

        # Load default metadata template
        with open(os.path.join(os.path.dirname(__file__), "../templates/sample_command.yaml"), "r") as f:
            metadata_content = f.read().replace("{command_name}", command_name)
            default_metadata = yaml.safe_load(metadata_content)

        # Save metadata
        save_command_metadata(cmd_dir, default_metadata)

        # Create default command.py
        with open(os.path.join(os.path.dirname(__file__), "../templates/sample_command.py"), "r") as f:
            with open(cmd_dir / "command.py", "w") as py_file:
                py_file.write(f.read())

        click.echo(f"Command '{command_name}' created successfully.")
        click.echo(f"- Metadata: {cmd_dir / 'command.yaml'}")
        click.echo(f"- Implementation: {cmd_dir / 'command.py'}")
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)

# ... (rest of cli.py remains unchanged, including import_commands and main)
Stop for Feedback: Test the evai commands add <command_name> command to ensure it creates the directory and files as expected. Verify the output messages and file contents. Provide feedback before proceeding.
Step 4: Dynamically Load and Register Commands in cli.py
Purpose: Load commands from ~/.evai/commands at startup and register them in Click under a user group.
Instructions:
Add a user group to cli.py for user-defined commands.
Implement a load_user_commands() function to scan ~/.evai/commands, create Click commands dynamically, and add them to the user group.
Use command_storage.py functions and Click's dynamic command creation capabilities.
Code:
Update evai/cli/cli.py:
python
# ... (add to existing imports)
from evai.command_storage import list_commands, import_command_module

# Type mapping for Click parameter types
TYPE_MAP = {
    "string": click.STRING,
    "integer": click.INT,
    "float": click.FLOAT,
    "boolean": click.BOOL,
}

# ... (existing cli and tools groups remain unchanged)

@cli.group(cls=AliasedGroup)
def user():
    """User-defined commands."""
    pass

def create_user_command(command_metadata: dict):
    """Create a Click command from command metadata."""
    command_name = command_metadata["name"]
    description = command_metadata.get("description", "")
    arg_names = [arg["name"] for arg in command_metadata.get("arguments", [])]

    def callback(*args, **kwargs):
        module = import_command_module(command_name)
        run_func = getattr(module, "run")
        params = dict(zip(arg_names, args))
        params.update(kwargs)
        result = run_func(**params)
        click.echo(result)

    command = click.command(name=command_name, help=description)(callback)

    # Add arguments
    for arg in command_metadata.get("arguments", []):
        command = click.argument(
            arg["name"],
            type=TYPE_MAP.get(arg.get("type", "string"), click.STRING)
        )(command)

    # Add options
    for opt in command_metadata.get("options", []):
        command = click.option(
            f"--{opt['name']}",
            type=TYPE_MAP.get(opt.get("type", "string"), click.STRING),
            help=opt.get("description", ""),
            required=opt.get("required", False),
            default=opt.get("default", None)
        )(command)

    return command

def load_user_commands():
    """Load and register user-defined commands from ~/.evai/commands."""
    commands_list = list_commands()
    for cmd_meta in commands_list:
        try:
            command = create_user_command(cmd_meta)
            user.add_command(command)
        except Exception as e:
            logger.warning(f"Failed to load command {cmd_meta['name']}: {e}")

# Call load_user_commands after defining groups
load_user_commands()

# ... (rest of cli.py remains unchanged)
Stop for Feedback: Run evai and check if the user group appears in the help output (evai --help). Create a test command and verify it’s listed under evai user --help and executable (e.g., evai user testcommand). Provide feedback before final integration.
Final Prompt for Sub-LLM
Below is a comprehensive prompt combining all steps, designed for a less intelligent sub-LLM. It includes explicit instructions, stresses specificity, and enforces discrete steps with feedback stops.
markdown
You are tasked with adding functionality to the EVAI CLI to allow users to create new commands, mirroring the existing tool creation process. The new commands will reside in `~/.evai/commands` and be loaded on EVAI startup, registered in Click like the existing command structure. Follow these **specific** steps EXACTLY as outlined, stopping after each step for feedback before proceeding. Do not skip steps or combine them. Assume the existing codebase (provided in context) is correct and must be extended without altering unrelated parts unless specified.

---

### Step 1: Create `command_storage.py` Module
- **Task**: Create a new file `evai/command_storage.py` to handle command file operations, similar to `tool_storage.py`.
- **Instructions**:
  - Use `pathlib.Path` for paths.
  - Define `COMMANDS_DIR = Path.home() / ".evai" / "commands"`.
  - Implement these functions:
    - `get_command_dir(command_name: str) -> Path`: Returns `COMMANDS_DIR / command_name`, creating it if needed.
    - `load_command_metadata(path: Path) -> dict`: Loads `command.yaml` from the path, raises FileNotFoundError if missing.
    - `save_command_metadata(path: Path, data: dict) -> None`: Saves dict to `command.yaml`.
    - `list_commands() -> list[dict]`: Lists all commands, skipping disabled ones, returns list of dicts with "name", "description", "path".
    - `import_command_module(command_name: str)`: Imports `command.py` from the command directory.
  - Include basic logging with `logger = logging.getLogger(__name__)`.
- **Code**:
```python
"""Command storage utilities for EVAI CLI."""

import os
import yaml
from pathlib import Path
import importlib.util
import logging

logger = logging.getLogger(__name__)

COMMANDS_DIR = Path.home() / ".evai" / "commands"

def get_command_dir(command_name: str) -> Path:
    """Get the directory path for a command and create it if it doesn't exist."""
    command_dir = COMMANDS_DIR / command_name
    command_dir.mkdir(parents=True, exist_ok=True)
    return command_dir

def load_command_metadata(path: Path) -> dict:
    """Load command metadata from command.yaml."""
    yaml_path = path / "command.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Command metadata file not found: {yaml_path}")
    with yaml_path.open("r") as f:
        return yaml.safe_load(f) or {}

def save_command_metadata(path: Path, data: dict) -> None:
    """Save command metadata to command.yaml."""
    yaml_path = path / "command.yaml"
    with yaml_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

def list_commands() -> list[dict]:
    """List all available commands."""
    if not COMMANDS_DIR.exists():
        return []
    commands = []
    for cmd_dir in COMMANDS_DIR.iterdir():
        if cmd_dir.is_dir():
            try:
                metadata = load_command_metadata(cmd_dir)
                if not metadata.get("disabled", False):
                    commands.append({
                        "name": metadata.get("name", cmd_dir.name),
                        "description": metadata.get("description", "No description"),
                        "path": cmd_dir
                    })
            except Exception as e:
                logger.warning(f"Error loading command {cmd_dir.name}: {e}")
    return commands

def import_command_module(command_name: str):
    """Dynamically import a command module."""
    cmd_dir = get_command_dir(command_name)
    py_path = cmd_dir / "command.py"
    if not py_path.exists():
        raise FileNotFoundError(f"Command implementation file not found: {py_path}")
    spec = importlib.util.spec_from_file_location(f"evai.commands.{command_name}", py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
Stop: After implementing this, stop and wait for feedback. Test each function manually (e.g., create a directory, save/load YAML, list commands) and report any issues.
Step 2: Create Command Templates
Task: Add sample_command.yaml and sample_command.py to evai/templates/ for default command files.
Instructions:
Create evai/templates/sample_command.yaml with placeholders {command_name} where needed.
Create evai/templates/sample_command.py with a run(**kwargs) function.
Ensure the YAML includes arguments and options fields instead of params to distinguish from tools.
Code:
evai/templates/sample_command.yaml:
yaml
name: "{command_name}"
description: "Default description"
arguments: []
options: []
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
evai/templates/sample_command.py:
python
"""Custom command implementation."""

def run(**kwargs):
    """Run the command with the given arguments."""
    print("Hello World")
    return {"status": "success"}
Stop: Verify the templates are in evai/templates/ and can be read correctly. Provide feedback on their contents and placement.
Step 3: Add commands Group and add Subcommand to cli.py
Task: Extend evai/cli/cli.py with a commands group and add subcommand.
Instructions:
Add @cli.group(cls=AliasedGroup) for commands.
Add @commands.command() for add, taking a command_name argument.
Use get_command_dir, save_command_metadata, and file operations to create the command.
Check for existing commands and exit with an error if found.
Code:
python
# In evai/cli/cli.py, add to imports:
from evai.command_storage import get_command_dir, save_command_metadata

# Add after existing groups:
@cli.group(cls=AliasedGroup)
def commands():
    """Manage user-defined commands."""
    pass

@commands.command()
@click.argument("command_name")
def add(command_name):
    """Add a new custom command."""
    try:
        cmd_dir = get_command_dir(command_name)
        if list(cmd_dir.iterdir()):  # Check if directory is non-empty
            click.echo(f"Command '{command_name}' already exists.", err=True)
            sys.exit(1)

        # Load default metadata template
        with open(os.path.join(os.path.dirname(__file__), "../templates/sample_command.yaml"), "r") as f:
            metadata_content = f.read().replace("{command_name}", command_name)
            default_metadata = yaml.safe_load(metadata_content)

        # Save metadata
        save_command_metadata(cmd_dir, default_metadata)

        # Create default command.py
        with open(os.path.join(os.path.dirname(__file__), "../templates/sample_command.py"), "r") as f:
            with open(cmd_dir / "command.py", "w") as py_file:
                py_file.write(f.read())

        click.echo(f"Command '{command_name}' created successfully.")
        click.echo(f"- Metadata: {cmd_dir / 'command.yaml'}")
        click.echo(f"- Implementation: {cmd_dir / 'command.py'}")
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)
Stop: Test evai commands add testcommand and check if the files are created in ~/.evai/commands/testcommand/. Provide feedback on functionality and output.
Step 4: Dynamically Load and Register Commands in cli.py
Task: Update evai/cli/cli.py to load and register commands at startup under a user group.
Instructions:
Add a user group with @cli.group(cls=AliasedGroup).
Define TYPE_MAP for parameter types.
Implement create_user_command to generate Click commands from metadata.
Implement load_user_commands to register all commands.
Call load_user_commands() after group definitions.
Code:
python
# In evai/cli/cli.py, add to imports:
from evai.command_storage import list_commands, import_command_module

# Add before groups:
TYPE_MAP = {
    "string": click.STRING,
    "integer": click.INT,
    "float": click.FLOAT,
    "boolean": click.BOOL,
}

# Add after 'commands' group:
@cli.group(cls=AliasedGroup)
def user():
    """User-defined commands."""
    pass

def create_user_command(command_metadata: dict):
    """Create a Click command from command metadata."""
    command_name = command_metadata["name"]
    description = command_metadata.get("description", "")
    arg_names = [arg["name"] for arg in command_metadata.get("arguments", [])]

    def callback(*args, **kwargs):
        module = import_command_module(command_name)
        run_func = getattr(module, "run")
        params = dict(zip(arg_names, args))
        params.update(kwargs)
        result = run_func(**params)
        click.echo(result)

    command = click.command(name=command_name, help=description)(callback)

    # Add arguments
    for arg in command_metadata.get("arguments", []):
        command = click.argument(
            arg["name"],
            type=TYPE_MAP.get(arg.get("type", "string"), click.STRING)
        )(command)

    # Add options
    for opt in command_metadata.get("options", []):
        command = click.option(
            f"--{opt['name']}",
            type=TYPE_MAP.get(opt.get("type", "string"), click.STRING),
            help=opt.get("description", ""),
            required=opt.get("required", False),
            default=opt.get("default", None)
        )(command)

    return command

def load_user_commands():
    """Load and register user-defined commands from ~/.evai/commands."""
    commands_list = list_commands()
    for cmd_meta in commands_list:
        try:
            command = create_user_command(cmd_meta)
            user.add_command(command)
        except Exception as e:
            logger.warning(f"Failed to load command {cmd_meta['name']}: {e}")

# Add after group definitions, before import_commands():
load_user_commands()
Stop: Run evai --help and evai user --help to verify the user group and loaded commands. Test a command (e.g., evai user testcommand) and provide feedback on registration and execution.
Final Notes: After completing all steps, the EVAI CLI will support command creation via evai commands add and load them at startup under the user group. Provide final feedback to confirm the implementation meets all requirements.
Please proceed with Step 1 and stop for feedback.
```