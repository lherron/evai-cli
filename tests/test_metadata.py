"""Tests for the command storage module."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from evai.tool_storage import (
    get_command_dir,
    load_command_metadata,
    save_command_metadata,
)


@pytest.fixture
def temp_home_dir():
    """Create a temporary directory to use as the home directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with mock.patch.dict(os.environ, {"HOME": temp_dir}):
            yield temp_dir


class TestGetCommandDir:
    """Tests for the get_command_dir function."""

    def test_get_command_dir_creates_directory(self, temp_home_dir):
        """Test that get_command_dir creates the directory if it doesn't exist."""
        command_name = "test-command"
        expected_path = os.path.join(temp_home_dir, ".evai", "commands", command_name)
        
        # Ensure the directory doesn't exist yet
        assert not os.path.exists(expected_path)
        
        # Call the function
        result = get_command_dir(command_name)
        
        # Check that the directory was created
        assert os.path.exists(expected_path)
        assert os.path.isdir(expected_path)
        assert result == expected_path

    def test_get_command_dir_with_existing_directory(self, temp_home_dir):
        """Test that get_command_dir returns the correct path for an existing directory."""
        command_name = "existing-command"
        expected_path = os.path.join(temp_home_dir, ".evai", "commands", command_name)
        
        # Create the directory
        os.makedirs(expected_path, exist_ok=True)
        
        # Call the function
        result = get_command_dir(command_name)
        
        # Check that the correct path was returned
        assert result == expected_path

    def test_get_command_dir_with_empty_name(self):
        """Test that get_command_dir raises ValueError for an empty command name."""
        with pytest.raises(ValueError, match="Command name cannot be empty"):
            get_command_dir("")

    def test_get_command_dir_with_invalid_name(self):
        """Test that get_command_dir raises ValueError for an invalid command name."""
        with pytest.raises(ValueError, match="Command name must contain only alphanumeric"):
            get_command_dir("invalid/command")


class TestLoadCommandMetadata:
    """Tests for the load_command_metadata function."""

    def test_load_command_metadata(self, temp_home_dir):
        """Test that load_command_metadata correctly loads YAML data."""
        # Create a test directory and YAML file
        test_dir = os.path.join(temp_home_dir, "test-dir")
        os.makedirs(test_dir, exist_ok=True)
        
        test_data = {
            "name": "test-command",
            "description": "Test command",
            "params": [{"name": "param1", "type": "string"}],
        }
        
        yaml_path = os.path.join(test_dir, "command.yaml")
        with open(yaml_path, "w") as f:
            yaml.dump(test_data, f)
        
        # Call the function
        result = load_command_metadata(test_dir)
        
        # Check that the correct data was loaded
        assert result == test_data

    def test_load_command_metadata_file_not_found(self, temp_home_dir):
        """Test that load_command_metadata raises FileNotFoundError if the file doesn't exist."""
        test_dir = os.path.join(temp_home_dir, "nonexistent-dir")
        os.makedirs(test_dir, exist_ok=True)
        
        with pytest.raises(FileNotFoundError):
            load_command_metadata(test_dir)

    def test_load_command_metadata_invalid_yaml(self, temp_home_dir):
        """Test that load_command_metadata raises YAMLError for invalid YAML."""
        # Create a test directory and invalid YAML file
        test_dir = os.path.join(temp_home_dir, "invalid-yaml-dir")
        os.makedirs(test_dir, exist_ok=True)
        
        yaml_path = os.path.join(test_dir, "command.yaml")
        with open(yaml_path, "w") as f:
            f.write("invalid: yaml: :")
        
        with pytest.raises(yaml.YAMLError):
            load_command_metadata(test_dir)


class TestSaveCommandMetadata:
    """Tests for the save_command_metadata function."""

    def test_save_command_metadata(self, temp_home_dir):
        """Test that save_command_metadata correctly saves YAML data."""
        # Create a test directory
        test_dir = os.path.join(temp_home_dir, "save-test-dir")
        os.makedirs(test_dir, exist_ok=True)
        
        test_data = {
            "name": "test-command",
            "description": "Test command",
            "params": [{"name": "param1", "type": "string"}],
        }
        
        # Call the function
        save_command_metadata(test_dir, test_data)
        
        # Check that the file was created with the correct content
        yaml_path = os.path.join(test_dir, "command.yaml")
        assert os.path.exists(yaml_path)
        
        with open(yaml_path, "r") as f:
            loaded_data = yaml.safe_load(f)
        
        assert loaded_data == test_data

    def test_save_command_metadata_creates_directory(self, temp_home_dir):
        """Test that save_command_metadata creates the directory if it doesn't exist."""
        test_dir = os.path.join(temp_home_dir, "nonexistent-dir")
        
        test_data = {"name": "test-command"}
        
        # Call the function
        save_command_metadata(test_dir, test_data)
        
        # Check that the directory and file were created
        yaml_path = os.path.join(test_dir, "command.yaml")
        assert os.path.exists(yaml_path)

    def test_save_command_metadata_empty_data(self, temp_home_dir):
        """Test that save_command_metadata raises ValueError for empty data."""
        test_dir = os.path.join(temp_home_dir, "empty-data-dir")
        os.makedirs(test_dir, exist_ok=True)
        
        with pytest.raises(ValueError, match="Command metadata cannot be empty"):
            save_command_metadata(test_dir, {}) 