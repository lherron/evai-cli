# Comprehensive Specification for EVAI CLI Custom Commands Integration

## Overview
This specification outlines the requirements, architecture decisions, data management strategies, error handling, and testing guidelines necessary for integrating user-created commands via the EVAI CLI, exposing them through the MCP server, and optionally interacting with LLM calls.

## Requirements

### Functional Requirements
- Users must be able to define custom commands through the EVAI CLI.
- Custom commands should automatically be exposed through the MCP server.
- Commands can optionally invoke LLM interactions.
- Commands must be executable from two entry points:
  - Claude Desktop (interactive)
  - Terminal CLI (`evai`)

### Technical Requirements
- Commands are stateless and independently executable.
- Multi-line editing support through the user's preferred `$EDITOR`.
- LLM provides reasonable defaults for command metadata, which users can manually review and iteratively refine.
- Command metadata and implementation are stored persistently under:
  ```
  ~/.evai/commands/<command-name>/
  ```

### Metadata Management
- Metadata must be YAML-formatted:

```yaml
name: string (required)
description: string (required)
params:
  - name: string (required)
    type: string (default: "string")
    description: string (optional, default: "")
    required: boolean (default: true)
    default: any (optional, default: null)
hidden: boolean (default: false)
disabled: boolean (default: false)
mcp_integration:
  enabled: boolean (default: true)
  metadata:
    endpoint: string (default auto-generated)
    method: string (default: "POST")
    authentication_required: boolean (default: false)
llm_interaction:
  enabled: boolean (default: false)
  auto_apply: boolean (default: true)
  max_llm_turns: integer (default: 15)
```

### File Structure
Each command has the following standardized files:
```
~/.evai/commands/<command-name>/command.yaml
~/.evai/commands/<command-name>/command.py
```

## Architecture
- EVAI CLI handles command creation and editing.
- Commands exposed via MCP through automatic YAML metadata parsing.
- Stateless runtime ensures consistent behavior between Claude Desktop and CLI invocations.

### Command Creation Workflow
1. User initiates command creation via CLI:
   ```
   evai command add <command-name>
   ```
2. LLM generates default metadata.
3. Metadata reviewed and edited by the user through interactive CLI session.
4. User edits implementation code via `$EDITOR`.
5. Post-editing validation:
   - YAML syntax validation.
   - Python linting (flake8 default minimal rules).
   - Iterative LLM fixes (auto-applied, max 15 iterations).

## Data Handling
- Commands are stateless by default, no persistent command runtime data storage.
- Persistent storage limited strictly to metadata and command implementation files under user-managed `~/.evai` directory.

## Error Handling Strategy
- YAML Syntax Errors:
  - Immediate validation feedback after editing.
- Python Implementation Errors:
  - Auto-linting via `flake8`.
  - Iterative LLM-aided error correction.
  - Informative terminal messaging between LLM iterations to notify user of issues and progress.
- Runtime Execution Errors:
  - Clear, descriptive terminal messages provided upon exceptions.
  - Errors during LLM interaction clearly indicated with retry guidance.

## Testing Plan

### Unit Tests
- Validate YAML parsing.
- Verify command metadata correctly translates to MCP exposure.
- Command implementation execution correctness via isolated unit tests.

### Integration Tests
- Test commands via both CLI and Claude Desktop execution paths.
- MCP exposure tests verifying endpoint availability and authentication handling.

### End-to-End (E2E) Tests
- Command creation workflow (LLM metadata generation, user review/edit, file creation).
- Full-cycle test from command creation to execution via CLI and Claude Desktop.

### Linting and Validation Tests
- Automated `flake8` checks in CI/CD pipeline.
- YAML schema validation integrated into command creation workflow.

### User Acceptance Tests (UAT)
- Manual user workflow tests for command creation/editing.
- Verify user clarity and ease of understanding of error messaging and correction workflows.

## Deployment
- No explicit deployment steps required beyond ensuring `~/.evai` directory is correctly structured.
- Automatic MCP exposure upon command file creation and metadata validation.

## Security Considerations
- Commands execute under the user's environment.
- Default no-authentication model for MCP endpoints, configurable if required.
- Clearly documented guidance to users regarding secure practices for handling sensitive command parameters and implementations.

This specification provides developers with all details required to commence immediate and confident implementation of the EVAI CLI Custom Commands Integration.
