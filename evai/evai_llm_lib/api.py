"""High-level API for common LLM interaction use cases."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from .config import LLMLibConfig
from .session import LLMChatSession
from .backends import create_llm_provider, create_tool_executor, create_session_backends
from .backends.base import Message, ToolDefinition, ToolResult
from .errors import LLMLibError

logger = logging.getLogger(__name__)

async def ask(
    prompt: str,
    *,
    provider: Optional[str] = None,
    config: Optional[LLMLibConfig] = None,
    max_tokens: Optional[int] = None
) -> str:
    """Simple one-shot query to an LLM.
    
    Args:
        prompt: The text prompt to send.
        provider: Optional provider name to use.
        config: Optional configuration to use.
        max_tokens: Optional maximum tokens to generate.
        
    Returns:
        The LLM's response text.
        
    Raises:
        LLMLibError: If there is an error communicating with the LLM.
    """
    llm = create_llm_provider(provider, config)
    await llm.initialize()
    
    try:
        response = await llm.generate_response(
            messages=[Message(role="user", content=prompt)],
            max_tokens=max_tokens
        )
        return response.content
        
    finally:
        # No cleanup needed for most providers
        pass

def ask_sync(
    prompt: str,
    *,
    provider: Optional[str] = None,
    config: Optional[LLMLibConfig] = None,
    max_tokens: Optional[int] = None
) -> str:
    """Synchronous version of ask()."""
    return asyncio.run(ask(
        prompt,
        provider=provider,
        config=config,
        max_tokens=max_tokens
    ))

async def chat(
    messages: List[Union[str, Dict[str, str], Message]],
    *,
    provider: Optional[str] = None,
    config: Optional[LLMLibConfig] = None,
    max_tokens: Optional[int] = None
) -> str:
    """Multi-turn chat interaction with an LLM.
    
    Args:
        messages: List of messages. Can be strings (treated as user messages),
                 dicts with 'role' and 'content' keys, or Message objects.
        provider: Optional provider name to use.
        config: Optional configuration to use.
        max_tokens: Optional maximum tokens to generate.
        
    Returns:
        The LLM's response text.
        
    Raises:
        LLMLibError: If there is an error communicating with the LLM.
    """
    # Convert messages to Message objects
    processed_messages = []
    for msg in messages:
        if isinstance(msg, str):
            processed_messages.append(Message(role="user", content=msg))
        elif isinstance(msg, dict):
            processed_messages.append(Message(**msg))
        else:
            processed_messages.append(msg)
    
    llm = create_llm_provider(provider, config)
    await llm.initialize()
    
    try:
        response = await llm.generate_response(
            messages=processed_messages,
            max_tokens=max_tokens
        )
        return response.content
        
    finally:
        # No cleanup needed for most providers
        pass

def chat_sync(
    messages: List[Union[str, Dict[str, str], Message]],
    *,
    provider: Optional[str] = None,
    config: Optional[LLMLibConfig] = None,
    max_tokens: Optional[int] = None
) -> str:
    """Synchronous version of chat()."""
    return asyncio.run(chat(
        messages,
        provider=provider,
        config=config,
        max_tokens=max_tokens
    ))

class ChatSession:
    """High-level chat session with optional tool support."""
    
    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        tool_executor: Optional[str] = None,
        config: Optional[LLMLibConfig] = None
    ):
        """Initialize a new chat session.
        
        Args:
            provider: Optional LLM provider name.
            tool_executor: Optional tool executor name.
            config: Optional configuration to use.
        """
        self.config = config or LLMLibConfig.load()
        self._session: Optional[LLMChatSession] = None
        self._provider_name = provider
        self._executor_name = tool_executor
    
    async def __aenter__(self) -> "ChatSession":
        """Enter the async context manager."""
        llm_provider, tool_executor = await create_session_backends(
            provider_name=self._provider_name,
            executor_name=self._executor_name,
            config=self.config
        )
        
        self._session = LLMChatSession(
            llm_provider=llm_provider,
            tool_executor=tool_executor,
            config=self.config
        )
        
        await self._session.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        if self._session:
            await self._session.cleanup()
    
    async def send_message(self, content: str) -> str:
        """Send a message and get the response.
        
        Args:
            content: The message content to send.
            
        Returns:
            The assistant's response.
            
        Raises:
            LLMLibError: If there is an error processing the message.
        """
        if not self._session:
            raise LLMLibError("Session not initialized. Use as async context manager.")
            
        await self._session.add_user_message(content)
        return await self._session.run_turn()
    
    @property
    def available_tools(self) -> Optional[List[ToolDefinition]]:
        """Get the list of available tools, if any."""
        if not self._session:
            return None
        return self._session.available_tools

class SyncChatSession:
    """Synchronous wrapper for ChatSession."""
    
    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        tool_executor: Optional[str] = None,
        config: Optional[LLMLibConfig] = None
    ):
        """Initialize a new synchronous chat session."""
        self._async_session = ChatSession(
            provider=provider,
            tool_executor=tool_executor,
            config=config
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def __enter__(self) -> "SyncChatSession":
        """Enter the context manager."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_session.__aenter__())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        if self._loop:
            self._loop.run_until_complete(self._async_session.__aexit__(exc_type, exc_val, exc_tb))
            self._loop.close()
            self._loop = None
    
    def send_message(self, content: str) -> str:
        """Synchronous version of send_message()."""
        if not self._loop:
            raise LLMLibError("Session not initialized. Use as context manager.")
            
        return self._loop.run_until_complete(
            self._async_session.send_message(content)
        )
    
    @property
    def available_tools(self) -> Optional[List[ToolDefinition]]:
        """Get the list of available tools, if any."""
        return self._async_session.available_tools
