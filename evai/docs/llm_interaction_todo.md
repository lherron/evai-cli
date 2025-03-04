# LLM Interaction Implementation Plan

## Task Overview
Implement todo #7 LLM Interaction for the EVAI CLI, which includes:
- Creating a new CLI command `evai command llmadd <command-name>`
- Querying the user for command description
- Calling an LLM with the description and name to generate metadata and implementation
- Building templates for metadata and implementation
- Implementing LLM-based default metadata generation
- Implementing LLM integration inside command.py logic
- Creating tests for the LLM functionality

## Implementation Steps

### 1. Create LLM Client Module
- [X] Create a new file `evai/llm_client.py` to handle LLM API interactions
- [X] Implement OpenAI API client using the OpenAI Python SDK
- [X] Create functions for generating command metadata and implementation

### 2. Add LLM Command to CLI
- [X] Add `llmadd` subcommand to the `command` group in `cli.py`
- [X] Implement user interaction to get command description
- [X] Call LLM to generate metadata and implementation

### 3. Update Command Storage
- [X] Add functions in `command_storage.py` to support LLM-generated metadata and implementation
- [X] Implement fallback mechanisms for when LLM is unavailable

### 4. Testing
- [X] Create `tests/test_llm.py` to test LLM interaction
- [X] Mock LLM API calls for testing
- [X] Test fallback mechanisms

## Implementation Details

### LLM Client
- [X] Use OpenAI API for LLM interactions
- [X] Support environment variable for API key: `OPENAI_API_KEY`
- [X] Implement retry logic for API failures
- [X] Create prompts for generating metadata and implementation

### CLI Command
- [X] `evai command llmadd <command-name>` will:
  1. Ask user for command description
  2. Call LLM to generate metadata and implementation
  3. Save generated files
  4. Allow user to edit generated files

### Testing Strategy
- [X] Mock OpenAI API responses
- [X] Test with valid and invalid inputs
- [X] Test fallback mechanisms 