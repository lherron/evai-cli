"""LLM-assisted tool creation for EVAI CLI."""

import sys
import os
import yaml
import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from evai.tool_storage import (
    get_tool_dir, 
    save_tool_metadata,
    load_sample_tool_yaml
)
from evai.llm_client import (
    generate_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)

# Initialize rich console
console = Console()


def generate_default_metadata_with_llm(tool_name: str, description: str) -> dict:
    """
    Generate default metadata for a tool using LLM.
    
    Args:
        tool_name: The name of the tool
        description: A description of the tool
        
    Returns:
        A dictionary containing the tool metadata
    """
    # Generate metadata with LLM
    metadata = generate_metadata_with_llm(tool_name, description)
    
    # Ensure required fields are present
    if "name" not in metadata:
        metadata["name"] = tool_name
    if "description" not in metadata:
        metadata["description"] = description
    if "params" not in metadata:
        metadata["params"] = []
    if "hidden" not in metadata:
        metadata["hidden"] = False
    if "disabled" not in metadata:
        metadata["disabled"] = False
    if "mcp_integration" not in metadata:
        metadata["mcp_integration"] = {
            "enabled": True,
            "metadata": {
                "endpoint": "",
                "method": "POST",
                "authentication_required": False
            }
        }
    if "llm_interaction" not in metadata:
        metadata["llm_interaction"] = {
            "enabled": False,
            "auto_apply": True,
            "max_llm_turns": 15
        }
    
    return metadata


@click.command()
@click.argument("tool_name")
def llmadd(tool_name):
    """Add a new custom tool using LLM assistance."""
    try:
        # Get the tool directory
        tool_dir = get_tool_dir(tool_name)
        
        # Get a description from the user
        description = click.prompt("Enter a description for the tool", type=str)
        
        # Check if additional information is needed
        try:
            additional_info = check_additional_info_needed(tool_name, description)
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
        click.echo("Generating metadata with LLM...")
        
        try:
            metadata = generate_default_metadata_with_llm(tool_name, description)
            click.echo("Metadata generated successfully.")
            
            # Display the generated YAML with rich formatting
            yaml_str = yaml.dump(metadata, default_flow_style=False)
            console.print("\n[bold blue]Generated YAML Metadata:[/bold blue]")
            console.print(Panel(Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)))
        except Exception as e:
            click.echo(f"Error generating metadata with LLM: {e}", err=True)
            click.echo("Falling back to default metadata.")
            
            # Try to load the sample template
            try:
                metadata = load_sample_tool_yaml(tool_name)
                metadata["description"] = description
            except Exception as template_error:
                click.echo(f"Error loading sample template: {template_error}", err=True)
                
                # Create default metadata
                metadata = {
                    "name": tool_name,
                    "description": description,
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
        save_tool_metadata(tool_dir, metadata)
        
        # Generate implementation with LLM
        click.echo("\nGenerating tool implementation with LLM...")
        
        try:
            implementation = generate_implementation_with_llm(tool_name, metadata)
            click.echo("Implementation generated successfully.")
            
            # Display the generated Python code with rich formatting
            console.print("\n[bold blue]Generated Python Implementation:[/bold blue]")
            console.print(Panel(Syntax(implementation, "python", theme="monokai", line_numbers=True)))
            
            # Save the implementation
            tool_py_path = os.path.join(tool_dir, "tool.py")
            with open(tool_py_path, "w") as f:
                f.write(implementation)
        except Exception as e:
            click.echo(f"Error generating implementation with LLM: {e}", err=True)
            click.echo("Falling back to default implementation.")
            
            # Create default implementation
            tool_py_path = os.path.join(tool_dir, "tool.py")
            with open(tool_py_path, "w") as f:
                f.write(f'"""Custom tool implementation for {tool_name}."""\n\n\ndef run(**kwargs):\n    """Run the tool with the given arguments."""\n    print("Hello World")\n    return {{"status": "success"}}\n')
        
        click.echo(f"\nTool '{tool_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(tool_dir, 'tool.yaml')}")
        click.echo(f"- Implementation: {tool_py_path}")
        click.echo(f"\nTo edit this tool, run: evai tool edit {tool_name}")
        
    except Exception as e:
        click.echo(f"Error creating tool: {e}", err=True)
        sys.exit(1) 