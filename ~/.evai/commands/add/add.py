"""Add command implementation."""
import sys

def command_add(a: int, b: int):
    """Add a and b."""
    print(f"DEBUG - Types: a={type(a)} ({a}), b={type(b)} ({b})", file=sys.stderr)
    return {"result": a + b}