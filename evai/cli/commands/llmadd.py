"""LLM-assisted command creation for EVAI CLI."""

import os
import sys
import click
import yaml
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from evai.command_storage import (
    get_command_dir,
    save_command_metadata,
    edit_command_metadata,
    edit_command_implementation,
    run_lint_check
)
from evai.llm_client import (
    generate_default_metadata_with_llm,
    generate_implementation_with_llm,
    check_additional_info_needed,
    LLMClientError
)

# Initialize rich console
console = Console()


@click.command()
@click.argument("command_name")
def llmadd(command_name):
    """Add a new custom command using LLM assistance."""
    try:
        # Get the command directory
        command_dir = get_command_dir(command_name)
        
        # Get command description from user
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
        click.echo("\nGenerating command metadata with LLM...")
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
        save_command_metadata(command_dir, metadata)
        
        # Generate implementation with LLM
        click.echo("\nGenerating command implementation with LLM...")
        try:
            implementation = generate_implementation_with_llm(command_name, metadata)
            click.echo("Implementation generated successfully.")
            
            # Display the generated Python with rich formatting
            console.print("\n[bold green]Generated Python Implementation:[/bold green]")
            console.print(Panel(Syntax(implementation, "python", theme="monokai", line_numbers=True)))
        except Exception as e:
            click.echo(f"Error generating implementation with LLM: {e}", err=True)
            click.echo("Falling back to default implementation.")
            
            # Create default implementation
            implementation = '"""Custom command implementation."""\n\n\ndef run(**kwargs):\n    """Run the command with the given arguments."""\n    print("Hello World")\n    return {"status": "success"}\n'
        
        # Save the implementation
        command_py_path = os.path.join(command_dir, "command.py")
        with open(command_py_path, "w") as f:
            f.write(implementation)
        
        # Allow user to edit the generated files
        if click.confirm("\nWould you like to edit the generated metadata?", default=True):
            # Loop until the user provides valid YAML or chooses to abort
            while True:
                success, metadata_content = edit_command_metadata(command_dir)
                
                if success:
                    click.echo("Command metadata saved successfully.")
                    break
                else:
                    if not click.confirm("Invalid YAML. Would you like to try again?"):
                        click.echo("Keeping the generated metadata.")
                        break
                    click.echo("Opening command.yaml for editing again...")
        
        if click.confirm("\nWould you like to edit the generated implementation?", default=True):
            click.echo("Opening command.py for editing...")
            edit_command_implementation(command_dir)
            
            # Run lint check on the implementation file
            click.echo("Running lint check on command.py...")
            lint_success, lint_output = run_lint_check(command_dir)
            
            # Loop until the lint check passes or the user chooses to abort
            while not lint_success:
                click.echo("Lint check failed. Please fix the following issues:")
                click.echo(lint_output)
                
                if not click.confirm("Would you like to edit the file again?"):
                    click.echo("Aborting. The command implementation may contain lint errors.")
                    break
                    
                click.echo("Opening command.py for editing again...")
                edit_command_implementation(command_dir)
                
                click.echo("Running lint check on command.py...")
                lint_success, lint_output = run_lint_check(command_dir)
            
            if lint_success:
                click.echo("Lint check passed. Command implementation saved successfully.")
        
        click.echo(f"\nCommand '{command_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(command_dir, 'command.yaml')}")
        click.echo(f"- Implementation: {command_py_path}")
        click.echo(f"\nTo edit this command, run: evai command edit {command_name}")
        click.echo(f"To run this command, run: evai command run {command_name}")
        
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1) 