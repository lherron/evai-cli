"""Sample command implementation."""

def command_sample(arg1: str, arg2: int, option1: bool = False):
    """
    Execute the sample command with the given arguments and options.
    
    Args:
        arg1: First argument (string)
        arg2: Second argument (integer)
        option1: Optional flag (boolean)
    
    Returns:
        A dictionary containing the command's output
    """
    # Example logic (replace with actual implementation)
    print(f"Received: {arg1}, {arg2}, option1={option1}")
    return {
        "status": "success",
        "arg1": arg1,
        "arg2": arg2,
        "option1": option1
    }