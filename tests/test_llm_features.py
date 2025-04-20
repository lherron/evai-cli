import asyncio
import os
from typing import Dict, Any, Optional

from evai_cli.llm import LLMSession
from evai_cli.mcp.client_tools import MCPServer, MCPConfiguration

async def test_new_features():
    """Test the new features in the LLMSession class."""
    # Load environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set, skipping test")
        return
    
    # Load servers from config
    config = MCPConfiguration()
    servers = []
    try:
        server_config_path = os.getenv("EVAI_SERVERS_CONFIG", "servers_config.json")
        server_configs = config.load_config(server_config_path)
        mcp_servers_config = server_configs.get("mcpServers", {})
        servers = [
            MCPServer(name, srv_config)
            for name, srv_config in mcp_servers_config.items()
        ]
    except Exception as e:
        print(f"Error loading server configuration: {e}")
        # Create minimal server list for testing
        servers = []
    
    session = LLMSession(servers=servers)
    await session.start_servers()
    
    try:
        print("\n--- Testing system_prompt and user_prompt ---")
        result1 = await session.send_request(
            user_prompt="What is the capital of France?",
            system_prompt="You are a geography expert. Keep your answer very brief.",
            debug=True
        )
        
        print(f"Success: {result1['success']}")
        print(f"Response: {result1['response']}")
        assert result1["success"], "System prompt test failed"
        
        print("\n--- Testing structured output ---")
        structured_tool = {
            "name": "final_answer",
            "description": "Provide the final answer in structured format.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["answer", "confidence"]
            }
        }
        
        result2 = await session.send_request(
            user_prompt="What is the capital of France? Use the 'final_answer' tool to provide your response.",
            system_prompt="Always use the final_answer tool to respond with structured data.",
            structured_output_tool=structured_tool,
            debug=True
        )
        
        print(f"Success: {result2['success']}")
        print(f"Response: {result2['response']}")
        print(f"Structured Response: {result2['structured_response']}")
        
        if result2["structured_response"]:
            assert "answer" in result2["structured_response"], "Structured output missing 'answer' field"
            assert "confidence" in result2["structured_response"], "Structured output missing 'confidence' field"
            print("Structured output test passed!")
        else:
            print("Structured output not returned, LLM may not have used the tool")
            
    finally:
        await session.stop_servers()

if __name__ == "__main__":
    asyncio.run(test_new_features()) 