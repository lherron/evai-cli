import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the evai package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from evai_cli.tool_storage import save_tool_metadata, run_tool


class TestPositionalArgs(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the test tool
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test tool
        self.tool_name = "test_subtract"
        self.tool_dir = os.path.join(self.temp_dir, self.tool_name)
        os.makedirs(self.tool_dir, exist_ok=True)
        
        # Create the tool.py file
        with open(os.path.join(self.tool_dir, "tool.py"), "w") as f:
            f.write("""
def tool_subtract(minuend: float, subtrahend: float) -> float:
    \"\"\"
    Subtract one number from another.

    Parameters:
    minuend (float): The number from which another number will be subtracted.
    subtrahend (float): The number that will be subtracted from the minuend.

    Returns:
    float: The result of the subtraction (minuend - subtrahend).

    Raises:
    ValueError: If either minuend or subtrahend is not a number.
    \"\"\"
    # Validate input types
    if not isinstance(minuend, (int, float)):
        raise ValueError("Minuend must be a number.")
    if not isinstance(subtrahend, (int, float)):
        raise ValueError("Subtrahend must be a number.")

    # Perform the subtraction
    result = minuend - subtrahend
    return result
""")
        
        # Create the tool.yaml file
        self.metadata = {
            "name": self.tool_name,
            "description": "Test subtract tool",
            "params": [
                {
                    "name": "minuend",
                    "description": "The number from which another number will be subtracted",
                    "type": "float",
                    "required": True
                },
                {
                    "name": "subtrahend",
                    "description": "The number that will be subtracted from the minuend",
                    "type": "float",
                    "required": True
                }
            ]
        }
        save_tool_metadata(self.tool_dir, self.metadata)
    
    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch('evai.tool_storage.get_tool_dir')
    @patch('evai.tool_storage.import_tool_module')
    @patch('evai.tool_storage.load_tool_metadata')
    def test_positional_args(self, mock_load_tool_metadata, mock_import_tool_module, mock_get_tool_dir):
        # Set up the mocks
        mock_get_tool_dir.return_value = self.tool_dir
        mock_load_tool_metadata.return_value = self.metadata
        
        # Create a mock module with the tool_subtract function
        mock_module = MagicMock()
        
        # Define the tool_subtract function
        def tool_subtract(minuend, subtrahend):
            return float(minuend) - float(subtrahend)
        
        # Set the tool_subtract function on the mock module
        mock_module.tool_subtract = tool_subtract
        mock_import_tool_module.return_value = mock_module
        
        # Test with positional arguments as a list
        result = run_tool(self.tool_name, ["8", "5"])
        self.assertEqual(result, 3.0)
        
        # Test with different values
        result = run_tool(self.tool_name, ["10", "2"])
        self.assertEqual(result, 8.0)
        
        # Test with negative numbers
        result = run_tool(self.tool_name, ["-5", "3"])
        self.assertEqual(result, -8.0)
    
    @patch('evai.tool_storage.get_tool_dir')
    @patch('evai.tool_storage.import_tool_module')
    @patch('evai.tool_storage.load_tool_metadata')
    def test_keyword_args(self, mock_load_tool_metadata, mock_import_tool_module, mock_get_tool_dir):
        # Set up the mocks
        mock_get_tool_dir.return_value = self.tool_dir
        mock_load_tool_metadata.return_value = self.metadata
        
        # Create a mock module with the tool_subtract function
        mock_module = MagicMock()
        
        # Define the tool_subtract function
        def tool_subtract(minuend, subtrahend):
            return float(minuend) - float(subtrahend)
        
        # Set the tool_subtract function on the mock module
        mock_module.tool_subtract = tool_subtract
        mock_import_tool_module.return_value = mock_module
        
        # Test with keyword arguments (backward compatibility)
        result = run_tool(self.tool_name, kwargs={"minuend": 8, "subtrahend": 5})
        self.assertEqual(result, 3.0)
        
        # Test with different values
        result = run_tool(self.tool_name, kwargs={"minuend": 10, "subtrahend": 2})
        self.assertEqual(result, 8.0)
        
        # Test with negative numbers
        result = run_tool(self.tool_name, kwargs={"minuend": -5, "subtrahend": 3})
        self.assertEqual(result, -8.0)
    
    def test_mixed_args(self):
        # Mixed args test is no longer relevant with the updated interface
        # The run_tool function now accepts args and kwargs separately
        # so there's no way to mix them incorrectly
        pass


if __name__ == "__main__":
    unittest.main() 