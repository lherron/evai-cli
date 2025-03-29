# Show Command Implementation Plan

The task is to add a "evai tools show" command that displays detailed information about tools, including:
- Tool description
- Tool arguments

## Implementation Steps

[X] Review existing tools.py file structure and command patterns
[X] Research the available functions from evai.tool_storage module
[X] Design the "show" command logic:
  - Accept a tool path as argument
  - Load the tool metadata using load_tool_metadata
  - Format and display the tool details including:
    - Name
    - Description
    - Arguments
    - Options
    - Parameters
[X] Add the command to tools.py and its alias
[X] Add the needed import for yaml
[X] Test the command with various tools

## Implementation Approach

1. [X] Create a new `@click.command()` decorator function named `show` in tools.py
2. [X] It should take a `path` argument to identify the tool to show
3. [X] Use the `load_tool_metadata` function to get the tool details
4. [X] Format the output using rich console for better readability
5. [X] Add a shorthand alias (`s`) similar to how other commands have aliases

## Command Output Format

```
Tool: <tool_name>
Description: <description>

Arguments:
- <arg_name>: <description> [required]
... 

Options:
- <option_name>: <description> [required]
...

Parameters:
- <param_name>: <description> [required]
...
```

## Implementation Summary
- Added `show` command to display detailed information about a tool or group
- The command shows:
  - Tool/group name and description
  - For tools: arguments, options, parameters, and additional metadata like MCP integration
  - For groups: lists all tools in the group
- Added `s` command as an alias for `show`
- Used the `rich` console for better formatted output with colors

## Testing Results
- Command `evai tools show` works correctly and displays usage instructions
- Command `evai tools show --help` shows help text
- Command `evai tools s --help` confirms alias works correctly
- Command `evai tools show subtract` successfully displays details of the "subtract" tool including:
  - Name and description
  - Parameters
  - MCP integration status

## Code Structure
```python
@click.command()
@click.argument("path")
def show(path):
    """Show detailed information about a tool."""
    try:
        # Load tool metadata
        metadata = load_tool_metadata(path)
        
        # Display tool information
        console.print(f"[bold]Tool:[/bold] {metadata.get('name', path)}")
        console.print(f"[bold]Description:[/bold] {metadata.get('description', 'No description')}")
        
        # Display arguments
        if metadata.get("arguments"):
            console.print("\n[bold]Arguments:[/bold]")
            for arg in metadata["arguments"]:
                # Format and display each argument
                
        # Display options
        if metadata.get("options"):
            console.print("\n[bold]Options:[/bold]")
            for opt in metadata["options"]:
                # Format and display each option
                
        # Display parameters
        if metadata.get("params"):
            console.print("\n[bold]Parameters:[/bold]")
            for param in metadata["params"]:
                # Format and display each parameter
                
    except Exception as e:
        click.echo(f"Error showing tool: {e}", err=True)
        sys.exit(1)
        
# Add alias
@click.command()
@click.argument("tool_name")
def s(tool_name):
    """Alias for 'show' - Show detailed information about a tool."""
    show.callback(tool_name) 