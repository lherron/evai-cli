"""MCP tool executor backend implementation."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types

from ..config import MCPConfig, LLMLibConfig
from ..errors import (
    ToolExecutorError,
    ToolExecutionError,
    ValidationError
)
from .base import (
    ToolDefinition,
    ToolResult,
    ToolExecutorBackend
)

logger = logging.getLogger(__name__)

class MCPToolExecutor(ToolExecutorBackend):
    """MCP implementation of the tool executor backend."""
    
    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize the MCP tool executor.
        
        Args:
            config: Optional MCP-specific configuration.
                   If not provided, will be loaded from the default config.
        """
        self.config = config or LLMLibConfig.load().mcp
        if not self.config:
            raise ValidationError("MCP configuration not found")
            
        self._session: Optional[ClientSession] = None
        self._client_context = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the MCP connection.
        
        Raises:
            ToolExecutorError: If connection to the MCP server fails.
        """
        if self._initialized:
            return
            
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env
            )
            
            # Connect to the MCP server
            self._client_context = stdio_client(server_params)
            read, write = await self._client_context.__aenter__()
            
            # Create and initialize session
            self._session = ClientSession(read, write)
            await self._session.__aenter__()
            await self._session.initialize()
            
            self._initialized = True
            
        except Exception as e:
            raise ToolExecutorError(f"Failed to initialize MCP connection: {str(e)}")
    
    def _convert_tool_schema(self, tool: types.Tool) -> ToolDefinition:
        """Convert MCP tool schema to our ToolDefinition format.
        
        Args:
            tool: MCP tool definition.
            
        Returns:
            ToolDefinition in our format.
        """
        return ToolDefinition(
            name=tool.name,
            description=tool.description or "",
            parameters=tool.inputSchema
        )
    
    def _extract_result_value(self, result_str: str) -> Any:
        """Extract the actual result value from MCP tool result string.
        
        Args:
            result_str: The raw result string from MCP tool execution.
            
        Returns:
            The extracted result value.
        """
        try:
            # Check if the result contains TextContent
            if "TextContent" in result_str and "text='" in result_str:
                # Extract the text value between text=' and '
                import re
                match = re.search(r"text='([^']*)'", result_str)
                if match:
                    extracted_text = match.group(1)
                    
                    # Check if the extracted text is JSON
                    if extracted_text.strip().startswith('{') and extracted_text.strip().endswith('}'):
                        try:
                            return json.loads(extracted_text)
                        except:
                            return extracted_text
                    
                    return extracted_text
            
            # If it's a JSON string, try to parse it
            if result_str.strip().startswith('{') and result_str.strip().endswith('}'):
                try:
                    return json.loads(result_str)
                except:
                    pass
                    
            # Return the original string if no extraction method worked
            return result_str
            
        except Exception:
            # If any error occurs, return the original string
            return result_str
    
    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools from the MCP server.
        
        Returns:
            List of available tool definitions.
            
        Raises:
            ToolExecutorError: If listing tools fails.
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            tools_result = await self._session.list_tools()
            if not tools_result or not hasattr(tools_result, 'tools'):
                return []
                
            return [self._convert_tool_schema(tool) for tool in tools_result.tools]
            
        except Exception as e:
            raise ToolExecutorError(f"Failed to list tools: {str(e)}")
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool through the MCP server.
        
        Args:
            tool_name: Name of the tool to execute.
            parameters: Parameters to pass to the tool.
            
        Returns:
            ToolResult containing the execution result or error.
            
        Raises:
            ToolExecutionError: If tool execution fails.
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Execute the tool
            raw_result = await self._session.call_tool(
                tool_name,
                arguments=parameters
            )
            
            # Extract and process the result
            result_value = self._extract_result_value(str(raw_result))
            
            return ToolResult(
                success=True,
                result=result_value
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed - {tool_name}: {str(e)}")
            raise ToolExecutionError(
                tool_name=tool_name,
                error=str(e),
                details={"parameters": parameters}
            )
    
    async def cleanup(self) -> None:
        """Clean up the MCP connection."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except:
                pass
            
        if self._client_context:
            try:
                await self._client_context.__aexit__(None, None, None)
            except:
                pass
            
        self._initialized = False
