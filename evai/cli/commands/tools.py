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
    load_sample_tool_yaml,
    remove_tool
)
from rich.console import Console

# Initialize rich console
console = Console()


@click.command()
@click.option("--type", type=click.Choice(["tool", "group"]), required=True, help="Type of entity to create")
@click.option("--name", required=True, help="Name of the entity")
@click.option("--parent", default=None, help="Parent group for subtools")
def add(type, name, parent):
    """Add a new tool or group."""
    try:
        # Construct the full path based on parent
        path = f"{parent}/{name}" if parent else name
        
        if type == "group":
            # Create a group
            metadata = {
                "name": name,
                "description": f"Group for {name} tools",
                "type": "group"
            }
            
            # Add the group using the new unified function
            add_tool(path, metadata, "")
            
            click.echo(f"Group '{path}' created successfully.")
            click.echo(f"\nTo add a subtool, run: evai tools add --type tool --parent {path} --name <subtool_name>")
        else:
            # Create a tool
            try:
                default_metadata = load_sample_tool_yaml(name)
                # Update the name to match the provided name
                default_metadata["name"] = name
            except Exception as e:
                click.echo(f"Error loading sample tool.yaml template: {e}", err=True)
                click.echo("Falling back to default metadata.")
                
                # Create default metadata
                default_metadata = {
                    "name": name,
                    "description": "Default description",
                    "arguments": [],
                    "options": [],
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
            
            # Create default implementation
            try:
                implementation = load_sample_tool_py()
                # Replace any tool_name references with the actual name
                implementation = implementation.replace("tool_name", f"tool_{name}")
            except Exception as e:
                click.echo(f"Error loading sample tool.py template: {e}", err=True)
                click.echo("Falling back to default implementation.")
                
                # Create a simple default implementation
                implementation = f'"""Custom tool implementation for {name}."""\n\n\ndef tool_{name}() -> dict:\n    """Execute the tool."""\n    return {{"status": "success"}}\n'
            
            # Add the tool using the new unified function
            add_tool(path, default_metadata, implementation)
            
            click.echo(f"Tool '{path}' created successfully.")
            click.echo(f"\nTo edit this tool, run: evai tools edit {path}")
        
    except Exception as e:
        click.echo(f"Error creating {type}: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
def new(tool_name):
    """Alias for 'add' - Add a new custom tool."""
    add.callback(tool_name)


@click.command()
@click.argument("path")
@click.option("--metadata/--no-metadata", default=True, help="Edit tool metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit tool implementation")
def edit(path, metadata, implementation):
    """Edit an existing tool or group."""
    try:
        # Get the tool directory
        dir_path = get_tool_dir(path)
        
        # Get the name from the path
        name = path.split('/')[-1]
        
        # Determine if this is a group
        is_group = os.path.exists(os.path.join(dir_path, "group.yaml"))
        
        # Edit metadata if requested
        if metadata:
            # Determine the correct yaml file path
            yaml_paths = [
                os.path.join(dir_path, f"{name}.yaml"),  # <name>.yaml (preferred for tools)
                os.path.join(dir_path, "tool.yaml"),     # tool.yaml (legacy for tools)
                os.path.join(dir_path, "group.yaml")     # group.yaml (for groups)
            ]
            
            yaml_path = None
            for p in yaml_paths:
                if os.path.exists(p):
                    yaml_path = p
                    break
            
            if not yaml_path:
                click.echo(f"Metadata file not found for '{path}'.", err=True)
                sys.exit(1)
            
            click.echo(f"Opening {os.path.basename(yaml_path)} for editing...")
            
            # Open the editor for the user to edit the file
            click.edit(filename=yaml_path)
            
            # Validate YAML after editing
            try:
                with open(yaml_path, "r") as f:
                    metadata_content = yaml.safe_load(f)
                
                if not metadata_content:
                    click.echo("Warning: Metadata file is empty or invalid YAML.", err=True)
                else:
                    click.echo("Metadata saved successfully.")
            except Exception as e:
                click.echo(f"Error validating metadata: {e}", err=True)
                if click.confirm("Would you like to try again?"):
                    return edit(path, True, False)
                click.echo("Skipping metadata validation.")
        
        # Edit implementation if requested
        if implementation and not is_group:
            # Determine the correct python file path
            py_paths = [
                os.path.join(dir_path, f"{name}.py"),  # <name>.py (preferred)
                os.path.join(dir_path, "tool.py")      # tool.py (legacy)
            ]
            
            py_path = None
            for p in py_paths:
                if os.path.exists(p):
                    py_path = p
                    break
            
            if not py_path:
                # Create a new implementation file if it doesn't exist
                py_path = os.path.join(dir_path, f"{name}.py")
                with open(py_path, "w") as f:
                    f.write(f'"""Implementation for {path}."""\n\n\ndef tool_{name}() -> dict:\n    """Execute the tool."""\n    return {{"status": "success"}}\n')
                click.echo(f"Created new implementation file: {py_path}")
            
            click.echo(f"Opening {os.path.basename(py_path)} for editing...")
            
            # Open the editor for the user to edit the file
            click.edit(filename=py_path)
            
            # Run a lint check on the edited file
            try:
                result = subprocess.run(
                    ["flake8", py_path],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    click.echo("Lint check passed.")
                else:
                    click.echo("Lint check failed with the following errors:")
                    click.echo(result.stdout)
                    
                    if click.confirm("Would you like to fix the lint errors?"):
                        # Loop until the user fixes the lint errors or chooses to abort
                        while True:
                            click.echo(f"Opening {os.path.basename(py_path)} for editing...")
                            
                            # Open the editor for the user to edit the file
                            click.edit(filename=py_path)
                            
                            # Run a lint check on the edited file
                            result = subprocess.run(
                                ["flake8", py_path],
                                check=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            
                            if result.returncode == 0:
                                click.echo("Lint check passed.")
                                break
                            else:
                                click.echo("Lint check failed with the following errors:")
                                click.echo(result.stdout)
                                
                                if not click.confirm("Would you like to try again?"):
                                    click.echo("Skipping lint errors.")
                                    break
            except FileNotFoundError:
                click.echo("flake8 is not installed, skipping lint check.")
        elif implementation and is_group:
            click.echo("Groups do not have implementation files.")
        
        click.echo(f"{'Group' if is_group else 'Tool'} '{path}' edited successfully.")
        
    except Exception as e:
        click.echo(f"Error editing: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
@click.option("--metadata/--no-metadata", default=True, help="Edit tool metadata")
@click.option("--implementation/--no-implementation", default=True, help="Edit tool implementation")
def e(tool_name, metadata, implementation):
    """Alias for 'edit' - Edit an existing tool."""
    edit.callback(tool_name, metadata, implementation)


@click.command()
def list():
    """List all available tools and groups."""
    try:
        # Get the list of tools and groups
        entities = list_tools()
        
        if not entities:
            click.echo("No tools or groups found.")
            return
        
        # First collect all groups
        groups = [e for e in entities if e["type"] == "group"]
        
        # Then collect all top-level tools (not in a group)
        top_level_tools = [e for e in entities if e["type"] == "tool" and "/" not in e["path"]]
        
        # Print the list of groups with their tools
        if groups:
            click.echo("Available groups:")
            for group in groups:
                group_name = group["path"]
                click.echo(f"- {group_name} (group): {group['description']}")
                
                # Find tools belonging to this group
                group_tools = [e for e in entities if e["type"] == "tool" and e["path"].startswith(f"{group_name}/")]
                
                for tool in group_tools:
                    # Extract just the tool name without the group prefix
                    tool_name = tool["path"].split("/")[-1]
                    click.echo(f"  - {tool_name}: {tool['description']}")
        
        # Print the list of top-level tools
        if top_level_tools:
            if groups:
                click.echo("\nTop-level tools:")
            else:
                click.echo("Available tools:")
                
            for tool in top_level_tools:
                click.echo(f"- {tool['name']}: {tool['description']}")
        
    except Exception as e:
        click.echo(f"Error listing tools and groups: {e}", err=True)
        sys.exit(1)


@click.command()
def ls():
    """Alias for 'list' - List all available tools."""
    list.callback()


@click.command()
@click.argument("path")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Tool parameters in the format key=value (for backward compatibility)")
def run(path, args, param):
    """Run a tool with the given arguments.
    
    Arguments can be provided as positional arguments after the tool path,
    or as key=value pairs with the --param/-p option for backward compatibility.
    
    Examples:
        evai tools run subtract 8 5
        evai tools run math/subtract 8 5
        evai tools run subtract --param minuend=8 --param subtrahend=5
    """
    try:
        # Parse parameters from --param options (backward compatibility)
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
        
        # Load the tool metadata
        try:
            metadata = load_tool_metadata(path)
        except FileNotFoundError:
            click.echo(f"Tool '{path}' not found.", err=True)
            sys.exit(1)
        
        # Check if this is a group
        dir_path = get_tool_dir(path)
        if os.path.exists(os.path.join(dir_path, "group.yaml")):
            click.echo(f"Cannot run a group: {path}", err=True)
            sys.exit(1)
        
        # If using --param options, check required parameters
        if not args:
            # Check CLI arguments
            for arg_def in metadata.get("arguments", []):
                arg_name = arg_def.get("name")
                if arg_name and arg_name not in kwargs:
                    click.echo(f"Missing required argument: {arg_name}", err=True)
                    sys.exit(1)
            
            # Check CLI options
            for opt_def in metadata.get("options", []):
                opt_name = opt_def.get("name")
                if opt_name and opt_def.get("required", False) and opt_name not in kwargs:
                    # If option has a default value, use it
                    if "default" in opt_def and opt_def["default"] is not None:
                        kwargs[opt_name] = opt_def["default"]
                    else:
                        click.echo(f"Missing required option: {opt_name}", err=True)
                        sys.exit(1)
            
            # Check MCP parameters
            for param_def in metadata.get("params", []):
                param_name = param_def.get("name")
                if param_name and param_def.get("required", True) and param_name not in kwargs:
                    # If parameter has a default value, use it
                    if "default" in param_def and param_def["default"] is not None:
                        kwargs[param_name] = param_def["default"]
                    else:
                        click.echo(f"Missing required parameter: {param_name}", err=True)
                        sys.exit(1)
        
        # Run the tool with positional args if provided, otherwise use kwargs
        if args:
            result = run_tool(path, args=list(args), kwargs=kwargs)
        else:
            result = run_tool(path, kwargs=kwargs)
        
        # Print the result
        if isinstance(result, dict):
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error running tool: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
@click.argument("args", nargs=-1)
@click.option("--param", "-p", multiple=True, help="Tool parameters in the format key=value (for backward compatibility)")
def r(tool_name, args, param):
    """Alias for 'run' - Run a tool with the given arguments."""
    run.callback(tool_name, args, param)


@click.command()
@click.argument("path")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def remove(path, force):
    """Remove a tool or group."""
    try:
        # Determine if the path exists and what type it is
        dir_path = get_tool_dir(path)
        is_group = os.path.exists(os.path.join(dir_path, "group.yaml"))
        entity_type = "group" if is_group else "tool"
        
        # If this is a group, check if it has tools
        if is_group and not force:
            # Get all entities
            entities = list_tools()
            
            # Find tools belonging to this group
            group_tools = [e for e in entities if e["type"] == "tool" and e["path"].startswith(f"{path}/")]
            
            if group_tools:
                click.echo(f"Group '{path}' contains {len(group_tools)} tools.")
                if not click.confirm(f"Are you sure you want to remove group '{path}' and all its tools?"):
                    click.echo("Operation cancelled.")
                    return
        elif not force:
            # Confirm removal unless force flag is set
            if not click.confirm(f"Are you sure you want to remove {entity_type} '{path}'?"):
                click.echo("Operation cancelled.")
                return
        
        # Remove the tool or group
        remove_tool(path)
        
        click.echo(f"{entity_type.capitalize()} '{path}' removed successfully.")
        
    except FileNotFoundError:
        click.echo(f"'{path}' not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error removing: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("tool_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
def rm(tool_name, force):
    """Alias for 'remove' - Remove a custom tool."""
    remove.callback(tool_name, force) 