"""LLM-assisted command and group creation for EVAI CLI."""

import sys
import os
import yaml
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from evai.command_storage import (
    get_command_dir,
    save_command_metadata,
    save_group_metadata,
    save_subcommand_metadata,
    parse_command_path
)
from evai.llm_client import (
    generate_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)

# Initialize rich console
console = Console()


def generate_default_metadata_with_llm(command_name: str, description: str) -> dict:
    """
    Generate default metadata for a command using LLM.
    
    Args:
        command_name: The name of the command
        description: A description of the command
        
    Returns:
        A dictionary containing the command metadata
    """
    # Generate metadata with LLM with special instructions for commands
    prompt = f"""Generate metadata for a command (not a tool) named '{command_name}'. 
Description: {description}

The metadata should include:
1. name: {command_name}
2. description: A one-line description
3. arguments: List of command-line positional arguments (NOT parameters)
4. options: List of command-line options with flags
5. hidden: Boolean (false by default)
6. disabled: Boolean (false by default)
7. mcp_integration and llm_interaction objects (can be copy-pasted from the example below)

Each argument should have:
- name
- description  
- type (string, integer, float, boolean)

Each option should have:
- name
- description
- type (string, integer, float, boolean)  
- required (boolean)
- default (optional)

Example structure (fill in the actual details):
```yaml
name: "{command_name}"
description: "Command description"
arguments: []
options: []
hidden: false
disabled: false
mcp_integration:
  enabled: true
  metadata:
    endpoint: ""
    method: "POST"
    authentication_required: false
llm_interaction:
  enabled: false
  auto_apply: true
  max_llm_turns: 15
```

Return ONLY the YAML, nothing else."""

    # Use the generic LLM client function but with our custom prompt
    try:
        from evai.llm_client import generate_content
        yaml_string = generate_content(prompt)
        
        # Try to parse the YAML
        return yaml.safe_load(yaml_string)
    except Exception as e:
        raise LLMClientError(f"Error generating command metadata: {e}")


def generate_group_metadata_with_llm(group_name: str, description: str) -> dict:
    """
    Generate metadata for a command group using LLM.
    
    Args:
        group_name: The name of the group
        description: A description of the group
        
    Returns:
        A dictionary containing the group metadata
    """
    # Generate metadata with LLM with special instructions for groups
    prompt = f"""Generate metadata for a command group named '{group_name}'. 
Description: {description}

The metadata should be minimal and include only:
1. name: {group_name}
2. description: A one-line description of the group

Example structure:
```yaml
name: "{group_name}"
description: "Group description"
```

Return ONLY the YAML, nothing else."""

    # Use the generic LLM client function but with our custom prompt
    try:
        from evai.llm_client import generate_content
        yaml_string = generate_content(prompt)
        
        # Try to parse the YAML
        return yaml.safe_load(yaml_string)
    except Exception as e:
        raise LLMClientError(f"Error generating group metadata: {e}")


@click.command()
@click.argument("name")
def llmadd(name):
    """Add a new command or group using LLM assistance."""
    try:
        # Ask if this is a command or a group
        entity_type = click.prompt(
            "Enter entity type",
            type=click.Choice(["command", "group"]),
            default="command"
        )
        
        # Ask if this is a subcommand
        parent = click.prompt(
            "Enter parent group (leave empty for none)",
            default="",
            type=str
        )
        
        # Get a description from the user
        description = click.prompt(f"Enter a description for the {entity_type}", type=str)
        
        if parent:
            # This is a subcommand
            parent_dir = get_command_dir([parent])
            if not (parent_dir / "group.yaml").exists():
                click.echo(f"Parent group '{parent}' does not exist.", err=True)
                sys.exit(1)
                
            if entity_type != "command":
                click.echo(f"Cannot create a {entity_type} under a group. Only commands can be added as subcommands.", err=True)
                sys.exit(1)
                
            # Check if subcommand already exists
            sub_yaml = parent_dir / f"{name}.yaml"
            if sub_yaml.exists():
                click.echo(f"Subcommand '{name}' already exists in group '{parent}'.", err=True)
                sys.exit(1)
                
            # Generate metadata with LLM
            click.echo("Generating subcommand metadata with LLM...")
            
            try:
                metadata = generate_default_metadata_with_llm(name, description)
                click.echo("Metadata generated successfully.")
                
                # Display the generated YAML with rich formatting
                yaml_str = yaml.dump(metadata, default_flow_style=False)
                console.print("\n[bold blue]Generated YAML Metadata:[/bold blue]")
                console.print(Panel(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)))
                
                # Save the metadata
                save_subcommand_metadata(parent_dir, name, metadata)
            except Exception as e:
                click.echo(f"Error generating metadata with LLM: {e}", err=True)
                click.echo("Falling back to default metadata.")
                
                # Create default metadata
                metadata = {
                    "name": name,
                    "description": description,
                    "arguments": [],
                    "options": [],
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
                save_subcommand_metadata(parent_dir, name, metadata)
            
            # Generate implementation with LLM
            click.echo("\nGenerating subcommand implementation with LLM...")
            
            try:
                # Custom prompt for command implementation
                function_name = f"command_{parent}_{name}"
                impl_prompt = f"""Create a Python implementation for a command-line interface subcommand with function name '{function_name}'.
Description: {description}

Here is the YAML metadata for this subcommand:
```yaml
{yaml.dump(metadata, default_flow_style=False)}
```

The implementation should:
1. Define a function named '{function_name}' with positional arguments for each argument in the metadata and keyword arguments for each option
2. Include type hints matching the metadata types (string, integer, float, boolean)
3. Process the arguments and options as needed
4. Return a dictionary with the command's results
5. Include a legacy 'run' function that calls '{function_name}' for backward compatibility

The file should include:
- A module docstring explaining the subcommand
- Proper error handling
- Informative docstrings

Example for metadata with arguments 'file' (string), 'count' (integer), and option 'verbose' (boolean, default false):
```python
\"\"\"Implementation for the subcommand.\"\"\"

def {function_name}(file: str, count: int, verbose: bool = False):
    \"\"\"Execute the subcommand with the given arguments.\"\"\"
    if verbose:
        print(f"Processing {{file}} {{count}} times")
    return {{"status": "success", "result": file * count}}
    
# Legacy support
def run(**kwargs):
    \"\"\"Legacy run function for backward compatibility.\"\"\"
    return {function_name}(**kwargs)
```

Return ONLY the Python code, nothing else."""

                from evai.llm_client import generate_content
                implementation = generate_content(impl_prompt)
                
                click.echo("Implementation generated successfully.")
                
                # Display the generated Python code with rich formatting
                console.print("\n[bold blue]Generated Python Implementation:[/bold blue]")
                console.print(Panel(Syntax(implementation, "python", theme="monokai", line_numbers=True)))
                
                # Save the implementation
                impl_path = parent_dir / f"{name}.py"
                with open(impl_path, "w") as f:
                    f.write(implementation)
            except Exception as e:
                click.echo(f"Error generating implementation with LLM: {e}", err=True)
                click.echo("Falling back to default implementation.")
                
                # Create default implementation
                impl_path = parent_dir / f"{name}.py"
                function_name = f"command_{parent}_{name}"
                with open(impl_path, "w") as f:
                    f.write(f'"""Implementation for the {name} subcommand in the {parent} group."""\n\n\ndef {function_name}(*args, **kwargs):\n    """Execute the {name} subcommand with the given arguments."""\n    print("Hello World")\n    return {{"status": "success"}}\n\n# Legacy support\ndef run(**kwargs):\n    """Legacy run function for backward compatibility."""\n    return {function_name}(**kwargs)\n')
            
            click.echo(f"\nSubcommand '{name}' created successfully under group '{parent}'.")
            click.echo(f"- Metadata: {sub_yaml}")
            click.echo(f"- Implementation: {impl_path}")
            click.echo(f"\nTo edit this subcommand, run: evai commands edit {parent} {name}")
        else:
            # This is a top-level entity (command or group)
            entity_dir = get_command_dir([name])
            
            if entity_dir.exists() and list(entity_dir.iterdir()):
                click.echo(f"Entity '{name}' already exists.", err=True)
                sys.exit(1)
                
            if entity_type == "group":
                # Create a group
                click.echo("Generating group metadata with LLM...")
                
                try:
                    metadata = generate_group_metadata_with_llm(name, description)
                    click.echo("Metadata generated successfully.")
                    
                    # Display the generated YAML with rich formatting
                    yaml_str = yaml.dump(metadata, default_flow_style=False)
                    console.print("\n[bold blue]Generated YAML Metadata:[/bold blue]")
                    console.print(Panel(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)))
                    
                    # Save the metadata
                    save_group_metadata(entity_dir, metadata)
                except Exception as e:
                    click.echo(f"Error generating metadata with LLM: {e}", err=True)
                    click.echo("Falling back to default metadata.")
                    
                    # Create default metadata
                    metadata = {
                        "name": name,
                        "description": description
                    }
                    
                    # Save the metadata
                    save_group_metadata(entity_dir, metadata)
                
                click.echo(f"\nGroup '{name}' created successfully.")
                click.echo(f"- Metadata: {entity_dir / 'group.yaml'}")
                click.echo(f"\nTo add a subcommand, run: evai commands add --type command --parent {name} --name <subcommand>")
            else:
                # Create a command
                # Check if additional information is needed
                try:
                    additional_info = check_additional_info_needed(name, description)
                    if additional_info:
                        click.echo("\nThe LLM suggests gathering more information:")
                        click.echo(additional_info)
                        
                        # Allow user to provide additional details
                        additional_details = click.prompt(
                            "Would you like to provide additional details? (leave empty to skip)",
                            default="",
                            type=str
                        )
                        
                        if additional_details:
                            description = f"{description}\n\nAdditional details: {additional_details}"
                except LLMClientError as e:
                    click.echo(f"Warning: {e}")
                    click.echo("Continuing with the provided description.")
                
                # Generate metadata with LLM
                click.echo("Generating command metadata with LLM...")
                
                try:
                    metadata = generate_default_metadata_with_llm(name, description)
                    click.echo("Metadata generated successfully.")
                    
                    # Display the generated YAML with rich formatting
                    yaml_str = yaml.dump(metadata, default_flow_style=False)
                    console.print("\n[bold blue]Generated YAML Metadata:[/bold blue]")
                    console.print(Panel(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)))
                    
                    # Save the metadata
                    save_command_metadata(entity_dir, metadata)
                except Exception as e:
                    click.echo(f"Error generating metadata with LLM: {e}", err=True)
                    click.echo("Falling back to default metadata.")
                    
                    # Create default metadata
                    metadata = {
                        "name": name,
                        "description": description,
                        "arguments": [],
                        "options": [],
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
                    save_command_metadata(entity_dir, metadata)
                
                # Generate implementation with LLM
                click.echo("\nGenerating command implementation with LLM...")
                
                try:
                    # Custom prompt for command implementation
                    function_name = f"command_{name}"
                    impl_prompt = f"""Create a Python implementation for a command-line interface command with function name '{function_name}'.
Description: {description}

Here is the YAML metadata for this command:
```yaml
{yaml.dump(metadata, default_flow_style=False)}
```

The implementation should:
1. Define a function named '{function_name}' with positional arguments for each argument in the metadata and keyword arguments for each option
2. Include type hints matching the metadata types (string, integer, float, boolean)
3. Process the arguments and options as needed
4. Return a dictionary with the command's results
5. Include a legacy 'run' function that calls '{function_name}' for backward compatibility

The file should include:
- A module docstring explaining the command
- Proper error handling
- Informative docstrings

Example for metadata with arguments 'file' (string), 'count' (integer), and option 'verbose' (boolean, default false):
```python
\"\"\"Implementation for the command.\"\"\"

def {function_name}(file: str, count: int, verbose: bool = False):
    \"\"\"Execute the command with the given arguments.\"\"\"
    if verbose:
        print(f"Processing {{file}} {{count}} times")
    return {{"status": "success", "result": file * count}}
    
# Legacy support
def run(**kwargs):
    \"\"\"Legacy run function for backward compatibility.\"\"\"
    return {function_name}(**kwargs)
```

Return ONLY the Python code, nothing else."""

                    from evai.llm_client import generate_content
                    implementation = generate_content(impl_prompt)
                    
                    click.echo("Implementation generated successfully.")
                    
                    # Display the generated Python code with rich formatting
                    console.print("\n[bold blue]Generated Python Implementation:[/bold blue]")
                    console.print(Panel(Syntax(implementation, "python", theme="monokai", line_numbers=True)))
                    
                    # Save the implementation
                    impl_path = entity_dir / f"{name}.py"
                    with open(impl_path, "w") as f:
                        f.write(implementation)
                except Exception as e:
                    click.echo(f"Error generating implementation with LLM: {e}", err=True)
                    click.echo("Falling back to default implementation.")
                    
                    # Create default implementation
                    impl_path = entity_dir / f"{name}.py"
                    function_name = f"command_{name}"
                    with open(impl_path, "w") as f:
                        f.write(f'"""Implementation for the {name} command."""\n\n\ndef {function_name}(*args, **kwargs):\n    """Execute the {name} command with the given arguments."""\n    print("Hello World")\n    return {{"status": "success"}}\n\n# Legacy support\ndef run(**kwargs):\n    """Legacy run function for backward compatibility."""\n    return {function_name}(**kwargs)\n')
                
                click.echo(f"\nCommand '{name}' created successfully.")
                click.echo(f"- Metadata: {entity_dir / f'{name}.yaml'}")
                click.echo(f"- Implementation: {impl_path}")
                click.echo(f"\nTo edit this command, run: evai commands edit {name}")
    except Exception as e:
        click.echo(f"Error creating {entity_type}: {e}", err=True)
        sys.exit(1)