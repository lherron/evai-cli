def tool_subtract(minuend: float, subtrahend: float) -> float:
    """
    Subtract one number from another.

    Parameters:
    minuend (float): The number from which another number will be subtracted.
    subtrahend (float): The number that will be subtracted from the minuend.

    Returns:
    float: The result of the subtraction (minuend - subtrahend).

    Raises:
    ValueError: If either minuend or subtrahend is not a number.
    """
    # Validate input types
    if not isinstance(minuend, (int, float)):
        raise ValueError("Minuend must be a number.")
    if not isinstance(subtrahend, (int, float)):
        raise ValueError("Subtrahend must be a number.")

    # Perform the subtraction
    result = minuend - subtrahend
    return result 