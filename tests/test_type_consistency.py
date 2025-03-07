"""Tests for type consistency checking between command functions and YAML metadata."""

import os
import tempfile
import pytest
import yaml
from unittest import mock
from pathlib import Path

from evai.command_storage import (
    get_function_type_hints,
    get_yaml_types,
    map_type_to_yaml,
    validate_command_types,
    get_command_dir,
    COMMANDS_DIR
)


# Sample command function with type hints for testing
def command_sample_add(a: int, b: int, c: str = "default"):
    return {"result": a + b, "message": c}


@pytest.fixture
def mock_commands_dir():
    """Create a temporary directory for commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the Path.home method
        with mock.patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(temp_dir)
            
            # Create the commands directory
            commands_dir = Path(temp_dir) / ".evai" / "commands"
            commands_dir.mkdir(parents=True, exist_ok=True)
            
            yield Path(temp_dir)


def test_get_function_type_hints():
    """Test extracting type hints from a function."""
    type_hints = get_function_type_hints(command_sample_add)
    
    assert len(type_hints) == 3
    assert type_hints["a"] == int
    assert type_hints["b"] == int
    assert type_hints["c"] == str


def test_map_type_to_yaml():
    """Test mapping Python types to YAML type strings."""
    assert map_type_to_yaml(int) == 'integer'
    assert map_type_to_yaml(str) == 'string'
    assert map_type_to_yaml(float) == 'float'
    assert map_type_to_yaml(bool) == 'boolean'
    assert map_type_to_yaml(list) == 'unknown'


def test_get_yaml_types():
    """Test extracting types from YAML metadata."""
    metadata = {
        "arguments": [
            {"name": "a", "type": "integer"},
            {"name": "b", "type": "integer"}
        ],
        "options": [
            {"name": "c", "type": "string"}
        ]
    }
    
    yaml_types = get_yaml_types(metadata)
    
    assert len(yaml_types) == 3
    assert yaml_types["a"] == "integer"
    assert yaml_types["b"] == "integer"
    assert yaml_types["c"] == "string"


def test_validate_command_types_success(mock_commands_dir, monkeypatch):
    """Test successful validation of command types."""
    # Create a sample command
    command_name = "sample-add"
    cmd_dir = COMMANDS_DIR / command_name
    cmd_dir.mkdir(parents=True, exist_ok=True)
    
    # Create command metadata
    metadata = {
        "name": command_name,
        "description": "Sample addition command",
        "arguments": [
            {"name": "a", "type": "integer", "description": "First number"},
            {"name": "b", "type": "integer", "description": "Second number"}
        ],
        "options": [
            {"name": "c", "type": "string", "description": "Optional message"}
        ]
    }
    
    with open(cmd_dir / f"{command_name}.yaml", "w") as f:
        yaml.dump(metadata, f)
    
    # Create command implementation
    with open(cmd_dir / f"{command_name}.py", "w") as f:
        f.write("""
def command_sample_add(a: int, b: int, c: str = "default"):
    return {"result": a + b, "message": c}
        """)
    
    # Mock the module loading and function access
    mock_module = mock.Mock()
    mock_module.command_sample_add = command_sample_add
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *args: mock.Mock())
    monkeypatch.setattr("importlib.util.module_from_spec", lambda *args: mock_module)
    
    # Run the validation - should not raise any exceptions
    validate_command_types("sample-add")


def test_validate_command_types_mismatch(mock_commands_dir, monkeypatch):
    """Test validation failure when types don't match."""
    # Create a sample command
    command_name = "sample-mismatch"
    cmd_dir = COMMANDS_DIR / command_name
    cmd_dir.mkdir(parents=True, exist_ok=True)
    
    # Create command metadata with type mismatch
    metadata = {
        "name": command_name,
        "description": "Sample command with type mismatch",
        "arguments": [
            {"name": "a", "type": "string", "description": "First argument"},  # Mismatch: should be integer
            {"name": "b", "type": "integer", "description": "Second argument"}
        ],
        "options": [
            {"name": "c", "type": "string", "description": "Optional message"}
        ]
    }
    
    with open(cmd_dir / f"{command_name}.yaml", "w") as f:
        yaml.dump(metadata, f)
    
    # Create command implementation
    with open(cmd_dir / f"{command_name}.py", "w") as f:
        f.write("""
def command_sample_mismatch(a: int, b: int, c: str = "default"):
    return {"result": a + b, "message": c}
        """)
    
    # Define a mock function with type hints
    def mock_command_func(a: int, b: int, c: str = "default"):
        return {"result": a + b, "message": c}
    
    # Mock the module loading and function access
    mock_module = mock.Mock()
    mock_module.__dict__[f"command_{command_name}"] = mock_command_func
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *args: mock.Mock())
    monkeypatch.setattr("importlib.util.module_from_spec", lambda *args: mock_module)
    
    # Run the validation - should raise ValueError due to type mismatch
    with pytest.raises(ValueError) as excinfo:
        validate_command_types(command_name)
    
    assert "Type mismatch" in str(excinfo.value)
    assert "parameter 'a'" in str(excinfo.value)
    assert "function expects 'integer'" in str(excinfo.value)
    assert "YAML specifies 'string'" in str(excinfo.value)


def test_validate_command_types_missing_parameter(mock_commands_dir, monkeypatch):
    """Test validation failure when a parameter is missing from YAML."""
    # Create a sample command
    command_name = "sample-missing"
    cmd_dir = COMMANDS_DIR / command_name
    cmd_dir.mkdir(parents=True, exist_ok=True)
    
    # Create command metadata with missing parameter
    metadata = {
        "name": command_name,
        "description": "Sample command with missing parameter",
        "arguments": [
            {"name": "a", "type": "integer", "description": "First argument"}
            # Missing 'b' parameter
        ],
        "options": [
            {"name": "c", "type": "string", "description": "Optional message"}
        ]
    }
    
    with open(cmd_dir / f"{command_name}.yaml", "w") as f:
        yaml.dump(metadata, f)
    
    # Create command implementation
    with open(cmd_dir / f"{command_name}.py", "w") as f:
        f.write("""
def command_sample_missing(a: int, b: int, c: str = "default"):
    return {"result": a + b, "message": c}
        """)
    
    # Define a mock function with type hints
    def mock_command_func(a: int, b: int, c: str = "default"):
        return {"result": a + b, "message": c}
    
    # Mock the module loading and function access
    mock_module = mock.Mock()
    mock_module.__dict__[f"command_{command_name}"] = mock_command_func
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *args: mock.Mock())
    monkeypatch.setattr("importlib.util.module_from_spec", lambda *args: mock_module)
    
    # Run the validation - should raise ValueError due to missing parameter
    with pytest.raises(ValueError) as excinfo:
        validate_command_types(command_name)
    
    assert "Parameter 'b'" in str(excinfo.value)
    assert "is not defined in YAML metadata" in str(excinfo.value)