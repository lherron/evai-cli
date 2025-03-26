"""Custom error classes for the LLM library."""

class LLMLibError(Exception):
    """Base exception class for LLM library errors."""
    pass

class ConfigurationError(LLMLibError):
    """Raised when there is an error in the configuration."""
    pass

class LLMProviderError(LLMLibError):
    """Raised when there is an error with the LLM provider."""
    pass

class ToolExecutorError(LLMLibError):
    """Raised when there is an error with the tool executor."""
    pass

class ToolExecutionError(ToolExecutorError):
    """Raised when a tool execution fails."""
    def __init__(self, tool_name: str, error: str, details: dict = None):
        self.tool_name = tool_name
        self.error = error
        self.details = details or {}
        super().__init__(f"Tool execution failed - {tool_name}: {error}")

class LLMResponseError(LLMProviderError):
    """Raised when there is an error in the LLM response."""
    def __init__(self, message: str, response_data: dict = None):
        self.response_data = response_data or {}
        super().__init__(message)

class AuthenticationError(LLMLibError):
    """Raised when there is an authentication error (e.g., invalid API key)."""
    pass

class RateLimitError(LLMLibError):
    """Raised when rate limits are exceeded."""
    def __init__(self, message: str, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message)

class ValidationError(LLMLibError):
    """Raised when there is a validation error in the input or output."""
    pass

class BackendNotFoundError(LLMLibError):
    """Raised when a requested backend is not found or not configured."""
    pass

class SessionError(LLMLibError):
    """Raised when there is an error with the chat session."""
    pass
