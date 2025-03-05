"""LLM-assisted command creation for EVAI CLI."""

import sys
import os
import yaml
import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from evai.command_storage import (
    get_command_dir,
    save_command_metadata
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


@click.command()
@click.argument("command_name")
def llmadd(command_name):
    """Add a new custom command using LLM assistance."""
    try:
        # Get the command directory
        cmd_dir = get_command_dir(command_name)
        
        if list(cmd_dir.iterdir()):  # Check if directory is non-empty
            click.echo(f"Command '{command_name}' already exists.", err=True)
            sys.exit(1)
        
        # Get a description from the user
        description = click.prompt("Enter a description for the command", type=str)
        
        # Check if additional information is needed
        try:
            additional_info = check_additional_info_needed(command_name, description)
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
            metadata = generate_default_metadata_with_llm(command_name, description)
            click.echo("Metadata generated successfully.")
            
            # Display the generated YAML with rich formatting
            yaml_str = yaml.dump(metadata, default_flow_style=False)
            console.print("\n[bold blue]Generated YAML Metadata:[/bold blue]")
            console.print(Panel(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)))
        except Exception as e:
            click.echo(f"Error generating metadata with LLM: {e}", err=True)
            click.echo("Falling back to default metadata.")
            
            # Create default metadata
            metadata = {
                "name": command_name,
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
        save_command_metadata(cmd_dir, metadata)
        
        # Generate implementation with LLM
        click.echo("\nGenerating command implementation with LLM...")
        
        try:
            # Custom prompt for command implementation
            impl_prompt = f"""Create a Python implementation for a command-line interface command named '{command_name}'.
Description: {description}

Here is the YAML metadata for this command:
```yaml
{yaml.dump(metadata, default_flow_style=False)}
```

The implementation should:
1. Define a 'run' function that accepts all arguments and options in the metadata
2. Process the arguments and options as needed
3. Return a dictionary with the command's results

The file should include:
- A module docstring explaining the command
- Type hints for all arguments
- Proper error handling
- Informative docstrings

Example structure:
```python
\"\"\"Implementation for the {command_name} command.\"\"\"

def run(**kwargs):
    \"\"\"Execute the {command_name} command with the given arguments.\"\"\"
    # Extract arguments from kwargs
    # Process the command logic
    # Return a dictionary with results
    return {{"status": "success", "data": {...}}}
```

Return ONLY the Python code, nothing else."""

            from evai.llm_client import generate_content
            implementation = generate_content(impl_prompt)
            
            click.echo("Implementation generated successfully.")
            
            # Display the generated Python code with rich formatting
            console.print("\n[bold blue]Generated Python Implementation:[/bold blue]")
            console.print(Panel(Syntax(implementation, "python", theme="monokai", line_numbers=True)))
            
            # Save the implementation
            cmd_py_path = os.path.join(cmd_dir, "command.py")
            with open(cmd_py_path, "w") as f:
                f.write(implementation)
        except Exception as e:
            click.echo(f"Error generating implementation with LLM: {e}", err=True)
            click.echo("Falling back to default implementation.")
            
            # Create default implementation
            cmd_py_path = os.path.join(cmd_dir, "command.py")
            with open(cmd_py_path, "w") as f:
                f.write(f'"""Implementation for the {command_name} command."""\n\n\ndef run(**kwargs):\n    """Execute the {command_name} command with the given arguments."""\n    print("Hello World")\n    return {{"status": "success"}}\n')
        
        click.echo(f"\nCommand '{command_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(cmd_dir, 'command.yaml')}")
        click.echo(f"- Implementation: {cmd_py_path}")
        click.echo(f"\nTo edit this command, run: evai commands edit {command_name}")
        
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)