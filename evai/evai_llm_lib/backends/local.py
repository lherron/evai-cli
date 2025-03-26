"""Local tool executor backend implementation."""

import asyncio
import inspect
import importlib
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from pydantic import BaseModel, create_model

from ..config import LocalToolsConfig, LLMLibConfig
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

class LocalTool:
    """Wrapper for a local Python function that can be used as a tool."""
    
    def __init__(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """Initialize a local tool.
        
        Args:
            func: The Python function to wrap.
            name: Optional name for the tool. Defaults to the function name.
            description: Optional description. Defaults to the function's docstring.
        """
        self.func = func
        self.name = name or func.__name__
        self.description = description or inspect.getdoc(func) or ""
        
        # Get function signature
        self.signature = inspect.signature(func)
        
        # Create Pydantic model for parameters
        self.param_model = self._create_param_model()
    
    def _create_param_model(self) -> type[BaseModel]:
        """Create a Pydantic model for the function parameters.
        
        Returns:
            A Pydantic model class for validating parameters.
        """
        fields = {}
        for name, param in self.signature.parameters.items():
            if param.kind in {param.VAR_POSITIONAL, param.VAR_KEYWORD}:
                continue  # Skip *args and **kwargs
                
            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                annotation = Any
                
            default = ... if param.default == param.empty else param.default
            fields[name] = (annotation, default)
        
        return create_model(
            f"{self.name}Params",
            **fields
        )
    
    def get_tool_definition(self) -> ToolDefinition:
        """Get the tool definition for this function.
        
        Returns:
            ToolDefinition describing this tool.
        """
        # Convert Pydantic model schema to tool parameters
        schema = self.param_model.model_json_schema()
        parameters = {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", [])
        }
        
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=parameters
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the function with the given parameters.
        
        Args:
            parameters: Parameters to pass to the function.
            
        Returns:
            The function's return value.
            
        Raises:
            ValidationError: If parameters are invalid.
            ToolExecutionError: If execution fails.
        """
        try:
            # Validate parameters
            validated = self.param_model(**parameters)
            params_dict = validated.model_dump()
            
            # Execute the function
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(**params_dict)
            else:
                # Run sync functions in the default executor
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.func(**params_dict)
                )
                
            return result
            
        except ValidationError as e:
            raise ValidationError(f"Invalid parameters for {self.name}: {str(e)}")
        except Exception as e:
            raise ToolExecutionError(
                tool_name=self.name,
                error=str(e),
                details={"parameters": parameters}
            )

class LocalToolExecutor(ToolExecutorBackend):
    """Local Python function tool executor backend."""
    
    def __init__(self, config: Optional[LocalToolsConfig] = None):
        """Initialize the local tool executor.
        
        Args:
            config: Optional configuration for local tools.
                   If not provided, will be loaded from the default config.
        """
        self.config = config or LLMLibConfig.load().local_tools
        if not self.config:
            raise ValidationError("Local tools configuration not found")
            
        self.tools: Dict[str, LocalTool] = {}
        self._initialized = False
    
    def register_tool(
        self,
        func: Union[Callable, LocalTool],
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> None:
        """Register a function as a tool.
        
        Args:
            func: Function or LocalTool to register.
            name: Optional name for the tool.
            description: Optional description for the tool.
            
        Raises:
            ValidationError: If the tool is invalid or a tool with the same name exists.
        """
        if isinstance(func, LocalTool):
            tool = func
        else:
            tool = LocalTool(func, name=name, description=description)
            
        if tool.name in self.tools:
            raise ValidationError(f"Tool with name '{tool.name}' already registered")
            
        self.tools[tool.name] = tool
    
    async def initialize(self) -> None:
        """Initialize the tool executor by loading tools from configured modules.
        
        Raises:
            ToolExecutorError: If loading tools fails.
        """
        if self._initialized:
            return
            
        try:
            # Load tools from configured modules
            for module_path in self.config.module_paths:
                try:
                    module = importlib.import_module(module_path)
                    
                    # Find functions marked as tools
                    for name, obj in inspect.getmembers(module):
                        if hasattr(obj, "__is_tool__") and obj.__is_tool__:
                            self.register_tool(obj)
                            
                except Exception as e:
                    logger.error(f"Failed to load tools from module {module_path}: {str(e)}")
            
            self._initialized = True
            
        except Exception as e:
            raise ToolExecutorError(f"Failed to initialize local tool executor: {str(e)}")
    
    async def list_tools(self) -> List[ToolDefinition]:
        """List available tools.
        
        Returns:
            List of available tool definitions.
        """
        if not self._initialized:
            await self.initialize()
            
        return [
            tool.get_tool_definition()
            for tool in self.tools.values()
            if (not self.config.function_whitelist or tool.name in self.config.function_whitelist)
            and (not self.config.function_blacklist or tool.name not in self.config.function_blacklist)
        ]
    
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
            
        Raises:
            ToolExecutionError: If tool execution fails.
        """
        if not self._initialized:
            await self.initialize()
            
        if tool_name not in self.tools:
            raise ToolExecutionError(tool_name, f"Tool '{tool_name}' not found")
            
        tool = self.tools[tool_name]
        
        try:
            result = await tool.execute(parameters)
            return ToolResult(
                success=True,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed - {tool_name}: {str(e)}")
            raise ToolExecutionError(
                tool_name=tool_name,
                error=str(e),
                details={"parameters": parameters}
            )
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.tools.clear()
        self._initialized = False

def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to mark a function as a tool.
    
    Args:
        name: Optional name for the tool. Defaults to the function name.
        description: Optional description. Defaults to the function's docstring.
        
    Returns:
        The decorated function.
    """
    def decorator(func: Callable) -> Callable:
        func.__is_tool__ = True
        func.__tool_name__ = name
        func.__tool_description__ = description
        return func
    return decorator
