# EVAI LLM Library API Documentation

## Overview

The EVAI LLM Library (`evai_llm_lib`) provides a clean, powerful interface for interacting with LLMs and executing tools. The library offers both high-level and low-level APIs, with async-first design and synchronous wrappers for convenience.

## Key Features

- **Multiple LLM Providers**: Support for Anthropic Claude and extensible for other providers
- **Tool Execution**: Built-in support for function calling/tool use
- **Session Management**: Stateful conversations with history tracking
- **Async and Sync APIs**: Async-first design with convenient sync wrappers
- **Configurability**: Environment variables, config files, and explicit parameters
- **Error Handling**: Consistent error classes and propagation

## High-Level API

The high-level API provides simple interfaces for common use cases.

### Simple Queries

For one-shot interactions with an LLM:

```python
from evai_llm_lib.api import ask, ask_sync

# Async usage
response = await ask("What is the capital of France?")

# Sync usage
response = ask_sync("What is the capital of France?")

# With specific provider
response = ask_sync("What is the capital of France?", provider="anthropic")
```

**Tool Support**: These functions do not support tool use.

### Multi-turn Chat

For stateless multi-turn conversations:

```python
from evai_llm_lib.api import chat, chat_sync

# Async usage with string messages (treated as user messages)
response = await chat([
    "Hello, who are you?",
    "What can you help me with?"
])

# Sync usage with explicit roles
response = chat_sync([
    {"role": "user", "content": "Hello, who are you?"},
    {"role": "assistant", "content": "I'm an AI assistant."},
    {"role": "user", "content": "What can you help me with?"}
])

# With specific provider and model
response = chat_sync(
    messages=[...],
    provider="anthropic",
    config=LLMLibConfig(default_model="claude-3-opus-20240229")
)
```

**Tool Support**: These functions do not support tool use.

### Stateful Chat Sessions

For ongoing conversations with tool support:

```python
from evai_llm_lib.api import ChatSession, SyncChatSession

# Async usage with context manager
async with ChatSession() as session:
    response1 = await session.send_message("Hello, who are you?")
    response2 = await session.send_message("What can you help me with?")
    
    # Access available tools
    tools = session.available_tools
    
# Sync usage with context manager
with SyncChatSession(tool_executor="local") as session:
    response1 = session.send_message("Hello, who are you?")
    response2 = session.send_message("Can you help me with calculations?")
```

**Tool Support**: Both `ChatSession` and `SyncChatSession` support tool use when a tool executor is provided.

## Configuration

The library uses a layered configuration approach:

```python
from evai_llm_lib.config import LLMLibConfig

# Load from environment/config files
config = LLMLibConfig.load()

# Create explicit config
config = LLMLibConfig(
    anthropic_api_key="your-key",
    default_provider="anthropic",
    default_model="claude-3-sonnet-20240229",
    default_tool_executor="local"
)

# Use in API calls
response = ask_sync("Hello", config=config)
```

### Environment Variables

- `ANTHROPIC_API_KEY`: API key for Anthropic
- `EVAI_DEFAULT_PROVIDER`: Default LLM provider (e.g., "anthropic")
- `EVAI_DEFAULT_MODEL`: Default model to use
- `EVAI_DEFAULT_TOOL_EXECUTOR`: Default tool executor (e.g., "local", "mcp")

## Tool System

The library provides a flexible tool execution system.

### Local Tools

Register Python functions as tools:

```python
from evai_llm_lib.backends.local import LocalToolExecutor

# Create executor
executor = LocalToolExecutor()

# Register tools
@executor.tool
def calculator(operation: str, a: float, b: float) -> float:
    """Perform basic math operations."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    # ...

# Or register existing functions
def search_docs(query: str) -> dict:
    """Search documentation."""
    # implementation...
    
executor.register_tool("search_docs", search_docs)
```

### Tool-Enabled Sessions

Use tools in chat sessions:

```python
from evai_llm_lib.api import ChatSession
from evai_llm_lib.backends.local import LocalToolExecutor

# Set up tools
executor = LocalToolExecutor()

@executor.tool
def get_weather(location: str) -> dict:
    """Get weather for a location."""
    # Implementation...
    return {"temperature": 72, "conditions": "sunny"}

# Create session with tools
async with ChatSession(tool_executor=executor) as session:
    # LLM can now use the get_weather tool
    response = await session.send_message(
        "What's the weather like in New York?"
    )
```

## Low-Level API

For more control, use the lower-level components:

### Session Management

```python
from evai_llm_lib.session import LLMChatSession
from evai_llm_lib.backends import create_llm_provider, create_tool_executor

# Create components manually
llm = await create_llm_provider("anthropic")
tools = await create_tool_executor("local") 

# Create session
session = LLMChatSession(llm_provider=llm, tool_executor=tools)
await session.initialize()

# Use session
await session.add_user_message("Hello")
response = await session.run_turn()

# Clean up
await session.cleanup()
```

### Direct Provider Usage

```python
from evai_llm_lib.backends.anthropic import AnthropicProvider
from evai_llm_lib.backends.base import Message

# Create provider directly
provider = AnthropicProvider()
await provider.initialize()

# Generate responses
response = await provider.generate_response([
    Message(role="user", content="Hello")
])

# Clean up
await provider.cleanup()
```

## Error Handling

All errors are wrapped in `LLMLibError`:

```python
from evai_llm_lib.errors import LLMLibError

try:
    response = await ask("Hello")
except LLMLibError as e:
    print(f"Error: {e}")
```

## API Reference

### Functions with Tool Support

| Function/Class | Tool Support | Notes |
|----------------|-------------|-------|
| `ask()` | ❌ | Simple one-shot query |
| `ask_sync()` | ❌ | Synchronous wrapper for `ask()` |
| `chat()` | ❌ | Multi-turn chat without state |
| `chat_sync()` | ❌ | Synchronous wrapper for `chat()` |
| `ChatSession` | ✅ | Stateful session with optional tool support |
| `SyncChatSession` | ✅ | Synchronous wrapper for `ChatSession` |
| `LLMChatSession` | ✅ | Low-level session with tool support |
| `LLMProvider.generate_response()` | ✅ | Direct provider usage with optional tools |

## Usage Examples

### Example 1: Simple Question Answering

```python
from evai_llm_lib.api import ask_sync

# Ask a simple question
answer = ask_sync("What is the capital of France?")
print(answer)  # Paris
```

### Example 2: Multi-turn Conversation

```python
from evai_llm_lib.api import chat_sync

# Have a conversation
messages = [
    "What are the three primary colors?",
    "Can you explain why they're called primary?"
]

response = chat_sync(messages)
print(response)
```

### Example 3: Using Tools in a Conversation

```python
from evai_llm_lib.api import SyncChatSession
from evai_llm_lib.backends.local import LocalToolExecutor

# Create and register tools
executor = LocalToolExecutor()

@executor.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@executor.tool
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Use in a session
with SyncChatSession(tool_executor=executor) as session:
    response = session.send_message("What is 123 multiplied by 456?")
    print(response)
    
    response = session.send_message("Now divide that by 7.")
    print(response)
```

### Example 4: Custom Configuration

```python
from evai_llm_lib.api import ask_sync
from evai_llm_lib.config import LLMLibConfig

# Create custom configuration
config = LLMLibConfig(
    anthropic_api_key="your-key-here",
    default_model="claude-3-opus-20240229",
    max_retries=3,
    timeout=60
)

# Use in API call
response = ask_sync(
    "Explain quantum computing in simple terms.",
    config=config,
    max_tokens=2000
)
print(response)
```

## Next Steps

For more detailed information, see:
- Tool creation guide
- Provider implementation guide
- Configuration reference
- Error handling guide 