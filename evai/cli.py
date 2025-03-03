"""Command-line interface for EVAI."""

import sys
import os
import click
from . import __version__
from .command_storage import (
    get_command_dir, 
    save_command_metadata, 
    edit_command_metadata,
    edit_command_implementation,
    run_lint_check
)


@click.group(help="EVAI CLI - Command-line interface for EVAI")
@click.version_option(version=__version__, prog_name="evai")
def cli():
    """EVAI CLI - Command-line interface for EVAI."""
    pass


@cli.group()
def command():
    """Manage custom commands."""
    pass


@command.command()
@click.argument("command_name")
@click.option("--test-mode", is_flag=True, hidden=True, help="Run in test mode (for testing only)")
def add(command_name, test_mode=False):
    """Add a new custom command."""
    try:
        # Get the command directory
        command_dir = get_command_dir(command_name)
        
        # Create default command.yaml
        default_metadata = {
            "name": command_name,
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
        save_command_metadata(command_dir, default_metadata)
        
        # Create default command.py
        command_py_path = os.path.join(command_dir, "command.py")
        with open(command_py_path, "w") as f:
            f.write('"""Custom command implementation."""\n\n\ndef run(**kwargs):\n    """Run the command with the given arguments."""\n    print("Hello World")\n    return {"status": "success"}\n')
        
        click.echo(f"Command '{command_name}' created successfully.")
        click.echo(f"- Metadata: {os.path.join(command_dir, 'command.yaml')}")
        click.echo(f"- Implementation: {command_py_path}")
        
        # Skip editing in test mode
        if test_mode:
            click.echo("Test mode: Skipping editor.")
            return
        
        # Open the editor for the user to edit the metadata
        click.echo("\nOpening command.yaml for editing...")
        
        # Loop until the user provides valid YAML or chooses to abort
        while True:
            success, metadata = edit_command_metadata(command_dir)
            
            if success:
                click.echo("Command metadata saved successfully.")
                break
            else:
                if not click.confirm("Invalid YAML. Would you like to try again?"):
                    click.echo("Aborting. The command has been created with default metadata.")
                    break
                click.echo("Opening command.yaml for editing again...")
        
        # Now edit the implementation file
        click.echo("\nOpening command.py for editing...")
        edit_command_implementation(command_dir)
        
        # Run lint check on the implementation file
        click.echo("\nRunning lint check on command.py...")
        lint_success, lint_output = run_lint_check(command_dir)
        
        # Loop until the lint check passes or the user chooses to abort
        while not lint_success:
            click.echo("Lint check failed. Please fix the following issues:")
            click.echo(lint_output)
            
            if not click.confirm("Would you like to edit the file again?"):
                click.echo("Aborting. The command has been created but may contain lint errors.")
                break
                
            click.echo("Opening command.py for editing again...")
            edit_command_implementation(command_dir)
            
            click.echo("Running lint check on command.py...")
            lint_success, lint_output = run_lint_check(command_dir)
        
        if lint_success:
            click.echo("Lint check passed. Command implementation saved successfully.")
            
        click.echo(f"\nCommand '{command_name}' setup complete.")
        
    except Exception as e:
        click.echo(f"Error creating command: {e}", err=True)
        sys.exit(1)


def main():
    """Run the EVAI CLI."""
    # If no arguments are provided, show help
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    return cli()


if __name__ == "__main__":
    sys.exit(main()) 