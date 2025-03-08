#!/usr/bin/env python3
import logging
import sys
from fastmcp import FastMCP
from evai.mcp.mcp_tools import register_tool
from evai.tool_storage import load_tool_metadata

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger("test_tool_registration")

def main():
    # Create a FastMCP instance
    mcp = FastMCP()
    
    # Load the tool metadata
    tool_path = "math/subtract"
    metadata = load_tool_metadata(tool_path)
    
    # Register the tool
    register_tool(mcp, tool_path, "subtract", metadata)
    
    # Print the registered tools
    tools = mcp.list_tools()
    logger.info(f"Registered tools: {tools}")
    
    # Test the tool
    logger.info("Testing the subtract tool...")
    result = mcp.call_tool("subtract", minuend=10.0, subtrahend=5.0)
    logger.info(f"Result: {result}")

if __name__ == "__main__":
    main() 