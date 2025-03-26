"""Base interfaces for LLM providers and tool executors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

class Message(BaseModel):
    """A message in a conversation."""
    role: str
    content: str

class ToolDefinition(BaseModel):
    """Definition of a tool that can be used by the LLM."""
    name: str
    description: str
    parameters: Dict[str, Any]

class ToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None

class LLMResponse(BaseModel):
    """Response from an LLM."""
    content: str
    stop_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class LLMProviderBackend(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the LLM provider."""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            messages: List of conversation messages.
            tools: Optional list of tools available to the LLM.
            max_tokens: Maximum number of tokens to generate.
            
        Returns:
            LLMResponse containing the generated content and metadata.
        """
        pass

class ToolExecutorBackend(ABC):
    """Abstract base class for tool executors."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the tool executor."""
        pass
    
    @abstractmethod
    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools.
        
        Returns:
            List of available tool definitions.
        """
        pass
    
    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool with the given parameters.
        
        Args:
            tool_name: Name of the tool to execute.
            parameters: Parameters to pass to the tool.
            
        Returns:
            ToolResult containing the execution result or error.
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool executor."""
        pass
