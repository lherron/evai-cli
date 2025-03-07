# Type Consistency Between Metadata and Commands

This document describes the implementation of a type consistency check between the type hints in command functions and the types specified in YAML metadata.

## Purpose

The type consistency check ensures that the type definitions in the YAML metadata match the type hints in the corresponding Python command functions. This helps catch discrepancies early, maintaining consistency and preventing runtime errors.

## Implementation Details

The type consistency check is integrated into the command loading process and includes the following components:

### 1. Helper Functions

#### `get_function_type_hints(func)`
- Extracts type hints from command function parameters using Python's `inspect` module
- Returns a dictionary mapping parameter names to their type hints

#### `get_yaml_types(metadata)`
- Extracts type information from YAML metadata for arguments and options
- Returns a dictionary mapping parameter names to their YAML-defined types

#### `map_type_to_yaml(type_hint)`
- Maps Python type hints to YAML type strings
- For example, converts `int` to `'integer'`, `str` to `'string'`, etc.

### 2. Validation Function

#### `validate_command_types(command_path)`
- Loads the command's metadata and function
- Extracts type hints from the function and types from the YAML metadata
- Compares the types and raises a `ValueError` if discrepancies are found

### 3. Integration with Command Loading

The validation is performed as part of the command loading process in `run_command()`, ensuring type consistency before the command is executed.

## Type Mapping

| Python Type | YAML Type   |
|-------------|-------------|
| `str`       | `'string'`  |
| `int`       | `'integer'` |
| `float`     | `'float'`   |
| `bool`      | `'boolean'` |
| Other types | `'unknown'` |

## Error Handling

- Type mismatches: A warning is logged, but execution proceeds
- Missing parameters: If a parameter with a type hint is not defined in the YAML metadata, a warning is logged
- Missing type hints: If a parameter in the YAML metadata does not have a type hint in the function, it's allowed but a warning is logged

## Best Practices

1. Always provide type hints in command functions that match the YAML metadata types
2. Use the standard Python types (`str`, `int`, `float`, `bool`) for better compatibility
3. Update both function signatures and YAML metadata together when making changes

## Example

### YAML Metadata
```yaml
arguments:
  - name: a
    type: integer
  - name: b
    type: integer
options:
  - name: c
    type: string
```

### Python Function
```python
def command_subtract(a: int, b: int, c: str = "default"):
    return {"result": a - b, "message": c}
```

## Testing

The type consistency check includes comprehensive tests that verify:
- Successful validation when types match
- Failure when there's a type mismatch
- Failure when a parameter is missing in YAML metadata