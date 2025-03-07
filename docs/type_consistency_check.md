# Type Consistency Between YAML Metadata and Command Functions

## Overview

This document outlines the implementation of a type consistency check mechanism in the EVAI CLI. The check ensures that the type definitions in the YAML metadata match the type hints in the corresponding Python command functions, helping to maintain consistency and prevent runtime errors.

## Implementation

### Helper Functions

The implementation includes several helper functions:

1. `get_function_type_hints(func)`: Extracts type hints from command function parameters
2. `get_yaml_types(metadata)`: Extracts type information from YAML metadata
3. `map_type_to_yaml(type_hint)`: Maps Python type hints to YAML type strings
4. `validate_command_types(command_path)`: Performs the actual validation

### Type Mapping

| Python Type | YAML Type    |
|-------------|--------------|
| `str`       | `'string'`   |
| `int`       | `'integer'`  |
| `float`     | `'float'`    |
| `bool`      | `'boolean'`  |
| Other types | `'unknown'`  |

### Integration with Command Loading

The type consistency check is integrated into the command loading process in `run_command()`. After loading the command function and metadata but before executing the command, the check verifies that:

1. All parameters with type hints in the function have corresponding entries in the YAML metadata
2. The types specified in the YAML metadata match the type hints in the function
3. All parameters in the YAML metadata have corresponding parameters in the function

### Error Handling

The system uses a warning-based approach to handle type inconsistencies:

- When a type mismatch is detected, a warning is logged but execution proceeds
- If a parameter with a type hint is missing from the YAML metadata, a warning is logged
- If a parameter in the YAML metadata doesn't have a type hint in the function, it's allowed but a warning is logged

## Sample Command Updates

The sample command templates have been updated to include proper type hints:

### sample_command.py
```python
def command_sample(arg1: str, arg2: int, option1: bool = False):
    """
    Execute the sample command with the given arguments and options.
    
    Args:
        arg1: First argument (string)
        arg2: Second argument (integer)
        option1: Optional flag (boolean)
    
    Returns:
        A dictionary containing the command's output
    """
    # Example logic (replace with actual implementation)
    print(f"Received: {arg1}, {arg2}, option1={option1}")
    return {
        "status": "success",
        "arg1": arg1,
        "arg2": arg2,
        "option1": option1
    }
```

### sample_command.yaml
```yaml
name: "{command_name}"
description: "Default description"
arguments:
  - name: "arg1"
    type: "string"
    description: "First argument (string)"
  - name: "arg2"
    type: "integer"
    description: "Second argument (integer)"
options:
  - name: "option1"
    type: "boolean"
    description: "Optional flag (boolean)"
    required: false
    default: false
```

## Testing

The implementation includes comprehensive tests in `tests/test_type_consistency.py` that verify:

1. Successful validation when types match
2. Failure when there's a type mismatch
3. Failure when a parameter is missing in YAML metadata

## Best Practices

1. Always provide type hints in command functions that match the YAML metadata types
2. Update both function signatures and YAML metadata together when making changes
3. Use the standard Python types (`str`, `int`, `float`, `bool`) for better compatibility

## Benefits

- Early detection of type inconsistencies
- Improved code quality and maintainability
- Prevention of runtime errors due to type mismatches
- Enhanced developer experience with clear error messages