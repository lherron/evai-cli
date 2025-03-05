# EVAI CLI

A powerful command-line interface for creating, managing, and executing custom commands with LLM assistance.

## Overview

EVAI CLI is a tool that allows you to create, manage, and run custom commands with the help of Large Language Models (LLMs). It provides a seamless way to:

- Create custom commands with LLM assistance
- Edit command metadata and implementation
- Run commands with parameters
- Integrate with MCP (Machine Control Protocol) for advanced AI interactions
- Expose your commands as a local API server

## Installation

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/evai-cli.git
cd evai-cli

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
pip install -e .
```

## Usage

### Basic Commands

```bash
# Show help
evai --help

# Show version
evai --version

# List all available commands and groups
evai commands list

# Add a new command
evai commands add --type command --name <command_name>

# Add a new group
evai commands add --type group --name <group_name>

# Add a subcommand to a group
evai commands add --type command --parent <group_name> --name <subcommand_name>

# Add a new command/group with LLM assistance
evai commands llmadd <name>

# Edit a command
evai commands edit <command_name>

# Edit a subcommand
evai commands edit <group_name> <subcommand_name>

# Run a command
evai commands run <command_name> --param key=value

# Run a subcommand
evai commands run "<group_name> <subcommand_name>" --param key=value

# Use a command from the user group
evai user <command_name> [arguments]

# Use a subcommand from the user group
evai user <group_name> <subcommand_name> [arguments]
```

### MCP Server

Start the MCP server to expose your commands as a local API:

```bash
evai server --name "My EVAI Commands"
```

## Command Structure

EVAI CLI supports both individual commands and command groups.

### Command Types

1. **Top-level Commands** - Individual commands at the root level
2. **Command Groups** - Collections of related subcommands

### Command & Group Structure

Commands and groups are stored in the `~/.evai/commands/` directory with the following structures:

#### Top-level Commands

```
~/.evai/commands/<command_name>/
├── <command_name>.yaml    # Command metadata
└── <command_name>.py      # Command implementation
```

#### Command Groups

```
~/.evai/commands/<group_name>/
├── group.yaml      # Group metadata
├── <subcommand1>.yaml  # Subcommand metadata
├── <subcommand1>.py    # Subcommand implementation
├── <subcommand2>.yaml  # Another subcommand metadata
└── <subcommand2>.py    # Another subcommand implementation
```

This organization keeps all subcommands for a group together in a single directory, making it easier to manage related commands.

### Command Metadata

The command metadata file (`command.yaml` or `<subcommand>.yaml`) contains information about the command:

```yaml
name: command_name
description: Description of what the command does
arguments:         # Positional arguments
  - name: arg1
    description: Description of argument 1
    type: string   # string, integer, float, boolean
options:           # Named options (flags)
  - name: option1
    description: Description of option 1
    type: string   # string, integer, float, boolean
    required: false
    default: null
hidden: false
disabled: false
mcp_integration:
  enabled: true
  metadata:
    endpoint: ""
    method: POST
    authentication_required: false
llm_interaction:
  enabled: false
  auto_apply: true
  max_llm_turns: 15
```

### Group Metadata

The group metadata file (`group.yaml`) is simpler and just defines the group itself:

```yaml
name: group_name
description: Description of the command group
```

### Command Implementation

The implementation file (`command.py` or `<subcommand>.py`) contains the actual command logic:

```python
"""Custom command implementation."""

def run(**kwargs):
    """Run the command with the given arguments."""
    # Your command logic here
    return {"status": "success", "data": {...}}
```

## Project Structure

```
evai-cli/
├── evai/                      # Main package
│   ├── __init__.py            # Package initialization
│   ├── cli/                   # CLI module
│   │   ├── __init__.py        # CLI package initialization
│   │   ├── cli.py             # Main CLI implementation
│   │   └── commands/          # CLI command modules
│   │       ├── __init__.py    # Commands package initialization
│   │       └── llmadd.py      # LLM-assisted command creation
│   ├── command_storage.py     # Command storage utilities
│   ├── llm_client.py          # LLM client for AI assistance
│   └── mcp_server.py          # MCP server integration
├── tests/                     # Test suite
├── .venv/                     # Virtual environment (created during setup)
├── pyproject.toml             # Project metadata and dependencies
├── requirements.txt           # Pinned dependencies
└── README.md                  # This file
```

## LLM Integration

EVAI CLI integrates with LLMs to help you:

1. Generate command metadata based on your description
2. Generate command implementation based on metadata
3. Suggest additional information needed for better command generation

## MCP Integration

EVAI CLI integrates with the Machine Control Protocol (MCP) to:

1. Expose your commands as tools in an MCP server
2. Provide built-in tools for managing commands
3. Support prompt templates for common tasks

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/evai-cli.git
cd evai-cli

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## Troubleshooting

### Missing `__init__.py` in Commands Directory

If you encounter an error like:

```
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

When running the `evai` command, ensure that there is an `__init__.py` file in the `evai/cli/commands/` directory. This file is required to make the commands directory a proper Python package.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
