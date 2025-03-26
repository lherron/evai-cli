"""Backend factory system for dynamic backend loading."""

import logging
from typing import Dict, Optional, Type, Union

from ..config import LLMLibConfig
from ..errors import BackendNotFoundError, ConfigurationError
from .base import LLMProviderBackend, ToolExecutorBackend
from .anthropic import AnthropicBackend
from .mcp import MCPToolExecutor
from .local import LocalToolExecutor

logger = logging.getLogger(__name__)

# Registry of available backends
LLM_PROVIDERS: Dict[str, Type[LLMProviderBackend]] = {
    "anthropic": AnthropicBackend
}

TOOL_EXECUTORS: Dict[str, Type[ToolExecutorBackend]] = {
    "mcp": MCPToolExecutor,
    "local": LocalToolExecutor
}

def register_llm_provider(name: str, provider_class: Type[LLMProviderBackend]) -> None:
    """Register a new LLM provider backend.
    
    Args:
        name: Name to register the provider under.
        provider_class: The provider class to register.
        
    Raises:
        ValueError: If a provider with the same name is already registered.
    """
    if name in LLM_PROVIDERS:
        raise ValueError(f"LLM provider '{name}' is already registered")
        
    LLM_PROVIDERS[name] = provider_class

def register_tool_executor(name: str, executor_class: Type[ToolExecutorBackend]) -> None:
    """Register a new tool executor backend.
    
    Args:
        name: Name to register the executor under.
        executor_class: The executor class to register.
        
    Raises:
        ValueError: If an executor with the same name is already registered.
    """
    if name in TOOL_EXECUTORS:
        raise ValueError(f"Tool executor '{name}' is already registered")
        
    TOOL_EXECUTORS[name] = executor_class

def create_llm_provider(
    provider_name: Optional[str] = None,
    config: Optional[LLMLibConfig] = None
) -> LLMProviderBackend:
    """Create an LLM provider backend instance.
    
    Args:
        provider_name: Name of the provider to create.
                      If not provided, uses the default from config.
        config: Optional configuration to use.
                If not provided, loads the default config.
                
    Returns:
        An initialized LLM provider backend.
        
    Raises:
        BackendNotFoundError: If the requested provider is not found.
        ConfigurationError: If the configuration is invalid.
    """
    config = config or LLMLibConfig.load()
    provider_name = provider_name or config.default_provider
    
    if provider_name not in LLM_PROVIDERS:
        raise BackendNotFoundError(
            f"LLM provider '{provider_name}' not found. "
            f"Available providers: {', '.join(LLM_PROVIDERS.keys())}"
        )
    
    provider_class = LLM_PROVIDERS[provider_name]
    
    try:
        # Get provider-specific config from the main config
        provider_config = getattr(config, provider_name, None)
        return provider_class(config=provider_config)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to create LLM provider '{provider_name}': {str(e)}")

def create_tool_executor(
    executor_name: Optional[str] = None,
    config: Optional[LLMLibConfig] = None
) -> Optional[ToolExecutorBackend]:
    """Create a tool executor backend instance.
    
    Args:
        executor_name: Name of the executor to create.
                      If not provided, uses the default from config.
                      If "none", returns None.
        config: Optional configuration to use.
                If not provided, loads the default config.
                
    Returns:
        An initialized tool executor backend, or None if no executor is requested.
        
    Raises:
        BackendNotFoundError: If the requested executor is not found.
        ConfigurationError: If the configuration is invalid.
    """
    config = config or LLMLibConfig.load()
    executor_name = executor_name or config.default_tool_executor
    
    # Allow explicitly requesting no tool executor
    if executor_name.lower() == "none":
        return None
    
    if executor_name not in TOOL_EXECUTORS:
        raise BackendNotFoundError(
            f"Tool executor '{executor_name}' not found. "
            f"Available executors: {', '.join(TOOL_EXECUTORS.keys())}"
        )
    
    executor_class = TOOL_EXECUTORS[executor_name]
    
    try:
        # Get executor-specific config from the main config
        executor_config = getattr(config, executor_name, None)
        return executor_class(config=executor_config)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to create tool executor '{executor_name}': {str(e)}")

def create_session_backends(
    provider_name: Optional[str] = None,
    executor_name: Optional[str] = None,
    config: Optional[LLMLibConfig] = None
) -> tuple[LLMProviderBackend, Optional[ToolExecutorBackend]]:
    """Create both backends needed for a chat session.
    
    Args:
        provider_name: Name of the LLM provider to create.
        executor_name: Name of the tool executor to create.
        config: Optional configuration to use.
        
    Returns:
        A tuple of (llm_provider, tool_executor).
        tool_executor may be None if no executor is requested.
    """
    config = config or LLMLibConfig.load()
    
    llm_provider = create_llm_provider(provider_name, config)
    tool_executor = create_tool_executor(executor_name, config)
    
    return llm_provider, tool_executor
