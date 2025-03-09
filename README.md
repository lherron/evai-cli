# EVAI CLI

A powerful command-line interface for creating, managing, and executing custom tools with LLM assistance.

## Overview

EVAI CLI enables you to create, manage, and run custom tools with the help of Large Language Models (LLMs). It provides:

- Creation of custom tools with LLM assistance
- Organization of tools as individual commands or in groups
- Integration with Model Context Protocol (MCP) for AI assistant interaction
- Exposure of your tools through a local MCP server for Claude Desktop compatibility

## Installation

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)

### Install from source

```bash
# Clone the repository
git clone https://github.com/lherron/evai-cli.git
cd evai-cli

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
pip install -e ".[dev]"
```

## Usage

### Basic Commands

```bash
# Show help
evai --help

# Add a new tool with LLM assistance
evai llm add

# List all available tools
evai tools list

# Edit a tool
evai tools edit <tool_name>

# Run a tool
evai <tool_name> [arguments]
```

### MCP Server

Start the MCP server to expose your tools to Claude Desktop or other MCP clients:

```bash
evai server start
```

## Tool Structure

EVAI CLI tools are stored in the `~/.evai/tools/` directory with the following structure:

```
~/.evai/tools/<tool_name>/
├── tool.yaml      # Tool metadata
└── <tool_name>.py # Tool implementation
```

### Tool Metadata

The tool metadata file (`tool.yaml`) defines:
- Name and description
- Arguments and options
- Type information
- MCP integration settings

### Tool Implementation

The implementation file contains the actual Python code that executes when the tool is run.

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
# Run all tests
pytest

# Run a specific test file
pytest tests/test_file.py

# Run a specific test
pytest tests/test_file.py::test_function_name
```

## Project Architecture

EVAI CLI follows a modular architecture with several key components:

- **CLI Core**: Command parser and executor built with Click
- **Tool Storage**: Persistent storage of tool definitions and implementations
- **LLM Client**: Interface with language models for tool generation
- **MCP Server**: MCP protocol implementation for AI assistant integration

For more details on the architecture, see the [Architecture Documentation](evai/docs/ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please make sure to run the linter and tests before submitting pull requests.

```bash
# Run linter
flake8

# Run tests
pytest
```