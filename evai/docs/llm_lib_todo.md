# LLM Utility Library Development Plan

## Overview
Create a reusable Python library that abstracts the LLM interaction functionality from the current EVAI CLI tool. The library should be robust, configurable, and usable by other Python applications.

## Current Status
Completed integration tests. Ready to begin CLI integration.

## Tasks

### Phase 1: Initial Setup and Core Structure
[X] Create new package structure for `evai_llm_lib`
[X] Define base interfaces and abstract classes
[X] Set up configuration management with Pydantic
[X] Create basic session management class

### Phase 2: Backend Implementations
[X] Implement Anthropic backend
[X] Implement MCP tool executor backend
[X] Create local tool executor backend
[X] Add backend factory system

### Phase 3: High-Level API
[X] Implement facade functions for common use cases
[X] Add async/sync compatibility layer
[X] Create configuration loading utilities
[X] Add comprehensive error handling

### Phase 4: Testing and Documentation
[X] Set up test infrastructure with mocks
[X] Write unit tests for high-level API
[X] Write unit tests for backend components
[X] Write integration tests
[X] Create API documentation
[X] Add usage examples

### Phase 5: CLI Integration
[ ] Refactor existing `evai llm` command to use new library
[ ] Update CLI error handling and display
[ ] Ensure backward compatibility
[ ] Add new CLI features enabled by library

## Implementation Notes

### Directory Structure
```
evai_llm_lib/
├── __init__.py
├── session.py          # Core LLMChatSession class
├── config.py           # Configuration management
├── api.py             # High-level facade functions
├── tools.py           # Tool definition models
├── errors.py          # Custom exceptions
├── backends/
│   ├── __init__.py
│   ├── base.py        # Abstract base classes
│   ├── anthropic.py   # Anthropic implementation
│   ├── mcp.py        # MCP tool executor
│   └── local.py      # Local tool executor
└── utils/
    ├── __init__.py
    └── async_helpers.py
```

### Key Design Decisions
1. Primary async-first design with sync wrappers
2. Pluggable backend system for LLM providers and tool executors
3. Pydantic-based configuration management
4. Standard Python logging instead of rich/click output
5. Optional MCP dependency

## Progress Update
- Completed all Phase 1 tasks
- Completed Phase 2 tasks:
  - Implemented Anthropic backend with:
    - Full async support
    - Proper error handling and conversion
    - Message and tool format conversion
    - Configuration management
    - Rate limit and authentication handling
  - Implemented MCP tool executor backend with:
    - Async MCP server connection
    - Tool schema conversion
    - Result value extraction
    - Proper cleanup and error handling
    - Context manager support
  - Implemented local tool executor backend with:
    - Python function wrapping with type validation
    - Automatic parameter schema generation
    - Support for sync and async functions
    - Module-based tool discovery
    - Tool decorator for easy registration
  - Added backend factory system with:
    - Dynamic backend registration
    - Configuration-based instantiation
    - Unified backend creation interface
    - Support for custom backends
- Completed Phase 3 tasks:
  - Implemented high-level API with:
    - Simple one-shot query functions (ask/ask_sync)
    - Multi-turn chat functions (chat/chat_sync)
    - Stateful chat sessions with tool support
    - Async and sync interfaces
    - Comprehensive error handling
    - Flexible message input formats
- Completed Phase 4 tasks:
  - Set up test infrastructure with:
    - Pytest configuration
    - Mock fixtures for providers and tools
    - Environment variable mocking
    - Async test support
  - Implemented comprehensive tests:
    - High-level API tests
    - Anthropic backend tests
    - Local tool executor tests
    - Session management tests
    - Integration tests for end-to-end flows
  - Created API documentation with:
    - Function and class descriptions
    - Usage examples
    - Tool support information
    - Error handling guidance

## Next Steps
1. Begin refactoring existing `evai llm` command to use the new library
2. Update CLI error handling and display
3. Ensure backward compatibility

## Questions/Issues to Resolve
- [ ] Determine exact configuration loading precedence
- [ ] Decide on logging strategy
- [ ] Plan migration strategy for existing CLI users 