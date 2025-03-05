"""Tool management functions for EVAI CLI."""

import sys
import os
import json
import click
from evai.tool_storage import (
    get_tool_dir, 
    save_tool_metadata, 
    edit_tool_metadata,
    edit_tool_implementation,
    run_lint_check,
    list_tools,
    run_tool,
    load_tool_metadata,
    load_sample_tool_py,
    load_sample_tool_yaml
)
from rich.console import Console

# Initialize rich console
console = Console()


@click.command()
@click.argument("tool_name")
def add(tool_name):
    """Add a new custom tool."""
    try:
        # Get the tool directory
        tool_dir = get_tool_dir(tool_name)
        
        # Load the sample tool.yaml template
        try:
            default_metadata = load_sample_tool_yaml(tool_name)
        except Exception as e:
            click.echo(f"Error loading sample tool.yaml template: {e}", err=True)
            click.echo("Falling back to default metadata.")
            
            # Create default metadata
            default_metadata = {
                "name": tool_name,
                "description": "Default description",
                "params": [],
                "hidden": False,
                "disabled": False,
                "mcp_integration": {
                    "enabled": True,
                    "metadata": {
                        "endpoint": "",
                        "method": "POST",
                        "authentication_required": False
                    }
                },
                "llm_interaction": {
                    "enabled": False,
                    "auto_apply": True,
                    "max_llm_turns": 15
                }
            }
        
        # Save the metadata
        save_tool_metadata(tool_dir, default_metadata)
        
        # Create default tool.py
        tool_py_path = os.path.join(tool_dir, "tool.py")
        try:
            tool_py_content = load_sample_tool_py()
            with open(tool_py_path, "w") as f:
                f.write(tool_py_content)
        except Exception as e:
            click.echo(f"Error loading sample tool.py template: {e}", err=True)
            click.echo("Falling back to default implementation.")
            
            # Create default tool.py
            with open(tool_py_path, "w") as f:
                f.write('"""Custom tool implementation."""\n\n\ndef run(**kwargs):\n    """Run the tool with the given arguments."""\n    print("Hello World")\n    return {"status": "success"}\n')
        
        click.echo(f"Tool '{tool_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(tool_dir, 'tool.yaml')}")
        click.echo(f"- Implementation: {tool_py_path}")
        click.echo(f"\nTo edit this tool, run: evai tool edit {tool_name}")
        
    except Exception as e:
        click.echo(f"Error creating tool: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
@click.option("--metadata/--no-metadata", default=True, help="Edit tool metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit tool implementation")
def edit(tool_name, metadata, implementation):
    """Edit an existing tool."""
    try:
        # Get the tool directory
        tool_dir = get_tool_dir(tool_name)
        
        # Edit metadata if requested
        if metadata:
            click.echo(f"Opening tool.yaml for editing...")
            
            # Loop until the user provides valid YAML or chooses to abort
            while True:
                success, metadata_content = edit_tool_metadata(tool_dir)
                
                if success:
                    click.echo("Tool metadata saved successfully.")
                    break
                else:
                    if not click.confirm("Invalid YAML. Would you like to try again?"):
                        click.echo("Aborting metadata edit.")
                        break
                    click.echo("Opening tool.yaml for editing again...")
        
        # Edit implementation if requested
        if implementation:
            click.echo(f"Opening tool.py for editing...")
            
            # Open the editor for the user to edit the file
            edit_tool_implementation(tool_dir)
            
            # Run a lint check on the edited file
            lint_success, lint_output = run_lint_check(tool_dir)
            
            if not lint_success:
                click.echo("Lint check failed with the following errors:")
                click.echo(lint_output)
                
                if click.confirm("Would you like to fix the lint errors?"):
                    # Loop until the user fixes the lint errors or chooses to abort
                    while True:
                        click.echo(f"Opening tool.py for editing...")
                        
                        # Open the editor for the user to edit the file
                        edit_tool_implementation(tool_dir)
                        
                        # Run a lint check on the edited file
                        lint_success, lint_output = run_lint_check(tool_dir)
                        
                        if lint_success:
                            click.echo("Lint check passed.")
                            break
                        else:
                            click.echo("Lint check failed with the following errors:")
                            click.echo(lint_output)
                            
                            if not click.confirm("Would you like to try again?"):
                                click.echo("Skipping lint errors.")
                                break
            else:
                click.echo("Lint check passed.")
        
        click.echo(f"Tool '{tool_name}' edited successfully.")
        
    except Exception as e:
        click.echo(f"Error editing tool: {e}", err=True)
        sys.exit(1)


@click.command()
def list():
    """List all available tools."""
    try:
        # Get the list of tools
        tools = list_tools()
        
        if not tools:
            click.echo("No tools found.")
            return
        
        # Print the list of tools
        click.echo("Available tools:")
        for tool in tools:
            click.echo(f"- {tool['name']}: {tool['description']}")
        
    except Exception as e:
        click.echo(f"Error listing tools: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
@click.option("--param", "-p", multiple=True, help="Tool parameters in the format key=value")
def run(tool_name, param):
    """Run a tool with the given arguments."""
    try:
        # Parse parameters
        kwargs = {}
        for p in param:
            try:
                key, value = p.split("=", 1)
                # Try to parse the value as JSON
                try:
                    kwargs[key] = json.loads(value)
                except json.JSONDecodeError:
                    # If not valid JSON, use the raw string
                    kwargs[key] = value
            except ValueError:
                click.echo(f"Invalid parameter format: {p}. Use key=value format.", err=True)
                sys.exit(1)
        
        # Get tool metadata to check parameter requirements
        tool_dir = get_tool_dir(tool_name)
        metadata = load_tool_metadata(tool_dir)
        
        # Check required parameters
        if "params" in metadata:
            for param_def in metadata.get("params", []):
                param_name = param_def.get("name")
                if param_name and param_def.get("required", True) and param_name not in kwargs:
                    # If parameter has a default value, use it
                    if "default" in param_def and param_def["default"] is not None:
                        kwargs[param_name] = param_def["default"]
                    else:
                        click.echo(f"Missing required parameter: {param_name}", err=True)
                        sys.exit(1)
        
        # Run the tool
        result = run_tool(tool_name, **kwargs)
        
        # Print the result
        if isinstance(result, dict):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error running tool: {e}", err=True)
        sys.exit(1) 