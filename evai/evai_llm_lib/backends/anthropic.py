"""Anthropic LLM provider backend implementation."""

import logging
from typing import Any, Dict, List, Optional
import anthropic

from ..config import AnthropicConfig, LLMLibConfig
from ..errors import (
    AuthenticationError,
    LLMProviderError,
    LLMResponseError,
    RateLimitError,
    ValidationError
)
from .base import (
    Message,
    ToolDefinition,
    LLMResponse,
    LLMProviderBackend
)

logger = logging.getLogger(__name__)

class AnthropicBackend(LLMProviderBackend):
    """Anthropic Claude implementation of the LLM provider backend."""
    
    def __init__(self, config: Optional[AnthropicConfig] = None):
        """Initialize the Anthropic backend.
        
        Args:
            config: Optional Anthropic-specific configuration.
                   If not provided, will be loaded from the default config.
        """
        self.config = config or LLMLibConfig.load().anthropic
        self._client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Anthropic client.
        
        Raises:
            AuthenticationError: If the API key is not set or invalid.
        """
        if self._initialized:
            return
            
        if not self.config.api_key:
            raise AuthenticationError("Anthropic API key not configured")
            
        try:
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
            self._initialized = True
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Anthropic client: {str(e)}")
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert our Message objects to Anthropic's message format.
        
        Args:
            messages: List of Message objects.
            
        Returns:
            List of messages in Anthropic's format.
            
        Raises:
            ValidationError: If a message has an invalid role.
        """
        anthropic_messages = []
        
        # Map our roles to Anthropic roles
        role_map = {
            "user": "user",
            "assistant": "assistant",
            "system": "user"  # Anthropic doesn't have a system role, prefix with "System: "
        }
        
        for msg in messages:
            if msg.role not in role_map:
                raise ValidationError(f"Invalid message role: {msg.role}")
                
            content = msg.content
            if msg.role == "system":
                content = f"System: {content}"
                
            anthropic_messages.append({
                "role": role_map[msg.role],
                "content": content
            })
            
        return anthropic_messages
    
    def _convert_tools(self, tools: List[ToolDefinition]) -> Dict[str, Any]:
        """Convert our tool definitions to Anthropic's tool format.
        
        Args:
            tools: List of tool definitions.
            
        Returns:
            Tool definitions in Anthropic's format.
        """
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for tool in tools
            ]
        }
    
    async def generate_response(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a response from Claude.
        
        Args:
            messages: List of conversation messages.
            tools: Optional list of tools available to Claude.
            max_tokens: Maximum number of tokens to generate.
                       If not provided, uses the config value.
        
        Returns:
            LLMResponse containing Claude's response.
            
        Raises:
            LLMProviderError: If there is an error calling Claude.
            AuthenticationError: If the API key is invalid.
            RateLimitError: If rate limits are exceeded.
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Convert messages to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            
            # Prepare the API call parameters
            params = {
                "model": self.config.model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens or self.config.max_tokens
            }
            
            # Add tools if provided
            if tools:
                params.update(self._convert_tools(tools))
            
            # Call Claude
            response = self._client.messages.create(**params)
            
            # Extract tool calls if present
            tool_calls = None
            if hasattr(response, "tool_calls"):
                tool_calls = response.tool_calls
            
            return LLMResponse(
                content=response.content[0].text,
                stop_reason=response.stop_reason,
                tool_calls=tool_calls
            )
            
        except anthropic.RateLimitError as e:
            retry_after = getattr(e, "retry_after", None)
            raise RateLimitError(str(e), retry_after=retry_after)
            
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(f"Anthropic authentication failed: {str(e)}")
            
        except anthropic.APIError as e:
            raise LLMProviderError(f"Anthropic API error: {str(e)}")
            
        except Exception as e:
            raise LLMResponseError(
                f"Error generating response from Claude: {str(e)}",
                response_data=getattr(e, "response", None)
            )
