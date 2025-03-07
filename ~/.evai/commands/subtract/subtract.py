"""Subtract command implementation."""
import sys

def command_subtract(a: int, b: int):
    """Subtract b from a."""
    print(f"DEBUG - Types: a={type(a)} ({a}), b={type(b)} ({b})", file=sys.stderr)
    return {"result": a - b}