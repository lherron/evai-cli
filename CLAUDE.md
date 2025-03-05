# EVAI CLI Development Guide

## Build & Test Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
- Run all tests: `pytest`
- Run single test file: `pytest tests/test_file.py`
- Run specific test: `pytest tests/test_file.py::test_function_name`
- Lint: `flake8`

## Code Style Guidelines
- Python 3.12+ required
- Use snake_case for variables, functions, modules
- Use PascalCase for classes
- Write unit tests using pytest
- Mock system components for testing
- Use Click for CLI commands, following existing patterns
- Use YAML for configuration files
- CLI tests use click.testing.CliRunner
- Never modify SQLAlchemy or SQLite code (PostgreSQL only)
- Prefer direct database access via db.entity_name.method_name pattern
- Use Pydantic 2 syntax for all data structures
- Include useful debug logging

## Project Organization
- Commands stored in ~/.evai/tools/ directory
- Tools have both metadata (YAML) and implementation (Python)
- Test modules are prefixed with "test_"
- Use the documentation in docs/ for understanding components