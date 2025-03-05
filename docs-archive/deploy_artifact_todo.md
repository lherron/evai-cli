# Deploy Artifact Tool

## Task
Create a new MCP tool called `deploy_artifact` that will save React component artifacts to the artifacts directory.

## Requirements
- Input: Artifact Name and the source of the React Component artifact
- Output: Save the component to a .tsx file in the "artifacts" directory
- The tool should create the artifacts directory if it doesn't exist

## Steps
- [X] Understand how tools are implemented in the codebase
- [X] Create the artifacts directory if it doesn't exist
- [X] Create the deploy_artifact tool implementation
- [X] Create the deploy_artifact tool metadata
- [X] Test the tool

## Implementation Details
1. Created the artifacts directory at `evai/artifacts`
2. Created the tool directory at `~/.evai/tools/deploy_artifact`
3. Implemented the tool function in `~/.evai/tools/deploy_artifact/tool.py`
4. Created the tool metadata in `~/.evai/tools/deploy_artifact/tool.yaml`

The tool will:
- Take an artifact name and source code as input
- Ensure the artifact name has a .tsx extension
- Save the source code to a file in the artifacts directory
- Return success/failure status with the path to the saved file 