"""Sample command implementation."""

def command_sample(*args, **kwargs):
    """
    Execute the sample command with the given arguments and options.
    
    Define the signature based on your command's metadata, e.g.:
    def command_sample(arg1: str, arg2: int, option1: bool = False):
        ...
    """
    # Example logic (replace with actual implementation)
    print("Hello World")
    return {"status": "success"}

# Legacy support
def run(**kwargs):
    """Legacy run function for backward compatibility."""
    return command_sample(**kwargs)