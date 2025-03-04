# Command Refactor Task

## Current Understanding
- The `add` command currently creates a new command and then opens an editor for interactive editing
- The editing logic includes:
  - Opening the command.yaml file in an editor and validating it
  - Opening the command.py file in an editor
  - Running lint checks on command.py and allowing re-editing if there are issues
- We need to simplify it to only create the command and validate YAML
- The editing functionality should be moved to a new `edit` command

## Tasks
- [X] Examine the current `add` command implementation fully
- [X] Identify the editing logic that needs to be moved
- [X] Simplify the `add` command to only create and validate
- [X] Create a new `edit` command with the moved editing logic
- [X] Ensure both commands work properly together
- [X] Update any related documentation or help text

## Implementation Summary

### 1. Simplified the `add` command
- Removed the interactive editing logic
- Kept only the command creation and basic validation
- Updated the help text to suggest using the new edit command

### 2. Created a new `edit` command
- Created a new command function `edit` in the command group
- Implemented the editing logic that was removed from `add`
- Added options to edit either metadata or implementation or both
- Included the lint checking functionality

### 3. Key Changes
- The `add` command now only creates the command with default templates
- The `edit` command provides interactive editing with validation
- Users can choose which parts of the command to edit (metadata, implementation, or both)
- The lint checking functionality is preserved in the edit command

### 4. Benefits
- Clearer separation of concerns between command creation and editing
- More flexibility for users to edit specific parts of commands
- Simplified workflow for creating new commands
- Better adherence to the Unix philosophy of "do one thing well" 