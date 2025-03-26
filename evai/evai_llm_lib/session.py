"""Core chat session management for the LLM library."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from .backends.base import (
    Message,
    ToolDefinition,
    ToolResult,
    LLMResponse,
    LLMProviderBackend,
    ToolExecutorBackend
)
from .config import LLMLibConfig
from .errors import (
    LLMLibError,
    SessionError,
    ToolExecutionError,
    ValidationError
)

logger = logging.getLogger(__name__)

class ChatTurn(BaseModel):
    """Represents a single turn in the conversation."""
    messages: List[Message]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[ToolResult]] = None

class LLMChatSession:
    """Manages a conversation session with an LLM, coordinating between the LLM provider and tool executor."""
    
    def __init__(
        self,
        llm_provider: LLMProviderBackend,
        tool_executor: Optional[ToolExecutorBackend] = None,
        config: Optional[LLMLibConfig] = None
    ):
        """Initialize a new chat session.
        
        Args:
            llm_provider: Backend for interacting with the LLM.
            tool_executor: Optional backend for executing tools.
            config: Optional configuration for the session.
        """
        self.llm_provider = llm_provider
        self.tool_executor = tool_executor
        self.config = config or LLMLibConfig.load()
        
        self.conversation_history: List[ChatTurn] = []
        self.available_tools: Optional[List[ToolDefinition]] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the session, including the LLM provider and tool executor."""
        if self._initialized:
            return
            
        # Initialize LLM provider
        await self.llm_provider.initialize()
        
        # Initialize tool executor if available
        if self.tool_executor:
            await self.tool_executor.initialize()
            self.available_tools = await self.tool_executor.list_tools()
            
        self._initialized = True
    
    async def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation.
        
        Args:
            content: The message content.
        """
        if not self._initialized:
            await self.initialize()
            
        # Create a new turn if needed or the last turn is complete
        if (not self.conversation_history or 
            self.conversation_history[-1].tool_results is not None):
            self.conversation_history.append(ChatTurn(messages=[]))
            
        self.conversation_history[-1].messages.append(
            Message(role="user", content=content)
        )
    
    async def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation.
        
        Args:
            content: The message content.
        """
        if not self.conversation_history:
            raise SessionError("Cannot add assistant message without a prior user message")
            
        self.conversation_history[-1].messages.append(
            Message(role="assistant", content=content)
        )
    
    async def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute a list of tool calls.
        
        Args:
            tool_calls: List of tool calls from the LLM.
            
        Returns:
            List of tool execution results.
        """
        if not self.tool_executor:
            raise SessionError("No tool executor configured")
            
        results = []
        for tool_call in tool_calls:
            try:
                name = tool_call.get("name")
                if not name:
                    raise ValidationError("Tool call missing name")
                    
                parameters = tool_call.get("parameters", {})
                result = await self.tool_executor.execute_tool(name, parameters)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Tool execution failed - {name}: {str(e)}")
                results.append(ToolResult(
                    success=False,
                    result=None,
                    error=str(e)
                ))
                
        return results
    
    def _get_conversation_messages(self) -> List[Message]:
        """Get all messages from the conversation history.
        
        Returns:
            List of all messages in chronological order.
        """
        messages = []
        for turn in self.conversation_history:
            messages.extend(turn.messages)
            
            # If the turn has tool results, add them as system messages
            if turn.tool_results:
                for result in turn.tool_results:
                    content = (
                        f"Tool execution {'succeeded' if result.success else 'failed'}\n"
                        f"Result: {result.result if result.success else result.error}"
                    )
                    messages.append(Message(role="system", content=content))
                    
        return messages
    
    async def run_turn(self) -> str:
        """Run a single conversation turn, including tool execution if needed.
        
        Returns:
            The final assistant response for this turn.
            
        Raises:
            SessionError: If there is no user message to respond to.
        """
        if not self._initialized:
            await self.initialize()
            
        if not self.conversation_history:
            raise SessionError("No conversation history")
            
        current_turn = self.conversation_history[-1]
        if not current_turn.messages or current_turn.messages[-1].role != "user":
            raise SessionError("No user message to respond to")
            
        # Get the full conversation history
        messages = self._get_conversation_messages()
        
        # Generate LLM response
        response = await self.llm_provider.generate_response(
            messages=messages,
            tools=self.available_tools
        )
        
        # Handle tool calls if present
        if response.tool_calls:
            current_turn.tool_calls = response.tool_calls
            current_turn.tool_results = await self._execute_tools(response.tool_calls)
            
            # Get another response after tool execution
            messages = self._get_conversation_messages()
            response = await self.llm_provider.generate_response(
                messages=messages,
                tools=self.available_tools
            )
        
        # Add the final response
        await self.add_assistant_message(response.content)
        return response.content
    
    async def cleanup(self) -> None:
        """Clean up resources used by the session."""
        if self.tool_executor:
            await self.tool_executor.cleanup()
            
    async def __aenter__(self) -> "LLMChatSession":
        """Enter the context manager."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        await self.cleanup()
