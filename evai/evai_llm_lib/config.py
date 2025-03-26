"""Configuration management for the LLM library."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AnthropicConfig(BaseModel):
    """Configuration for Anthropic LLM provider."""
    api_key: str = Field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 1000

class MCPConfig(BaseModel):
    """Configuration for MCP tool executor."""
    command: str = "uv"
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    server_script_path: Optional[str] = None

class LocalToolsConfig(BaseModel):
    """Configuration for local tool executor."""
    module_paths: List[str] = Field(default_factory=list)
    function_whitelist: Optional[List[str]] = None
    function_blacklist: Optional[List[str]] = None

class LLMLibConfig(BaseSettings):
    """Main configuration for the LLM library."""
    model_config = SettingsConfigDict(
        env_prefix="EVAI_LLM_",
        env_nested_delimiter="__",
        case_sensitive=False
    )
    
    # LLM Provider configuration
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    
    # Tool executor configuration
    mcp: Optional[MCPConfig] = None
    local_tools: Optional[LocalToolsConfig] = None
    
    # General settings
    default_provider: str = "anthropic"
    default_tool_executor: str = "mcp"
    log_level: str = "INFO"
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "LLMLibConfig":
        """Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file (YAML or JSON).
            
        Returns:
            LLMLibConfig instance.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the file format is not supported.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
            
        if file_path.suffix.lower() == ".json":
            import json
            with open(file_path) as f:
                config_dict = json.load(f)
        elif file_path.suffix.lower() in {".yaml", ".yml"}:
            import yaml
            with open(file_path) as f:
                config_dict = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
            
        return cls.model_validate(config_dict)
    
    @classmethod
    def load(cls) -> "LLMLibConfig":
        """Load configuration from environment variables and default config locations.
        
        The following locations are checked in order:
        1. Environment variables with EVAI_LLM_ prefix
        2. ~/.config/evai/llm_config.yaml
        3. ./evai_llm_config.yaml
        4. Default values
        
        Returns:
            LLMLibConfig instance.
        """
        # Start with environment variables
        config = cls()
        
        # Check user config directory
        user_config = Path.home() / ".config" / "evai" / "llm_config.yaml"
        if user_config.exists():
            try:
                user_settings = cls.from_file(user_config)
                config = config.model_copy(update=user_settings.model_dump())
            except Exception as e:
                import logging
                logging.warning(f"Error loading user config from {user_config}: {e}")
        
        # Check local config file
        local_config = Path("evai_llm_config.yaml")
        if local_config.exists():
            try:
                local_settings = cls.from_file(local_config)
                config = config.model_copy(update=local_settings.model_dump())
            except Exception as e:
                import logging
                logging.warning(f"Error loading local config from {local_config}: {e}")
        
        return config
