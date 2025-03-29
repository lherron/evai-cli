"""LLM client for EVAI CLI."""

import os
import logging
import json
import yaml
from typing import Dict, Any, Optional, Tuple, List, cast
import time

# Set up logging
logger = logging.getLogger(__name__)

# Default metadata template
DEFAULT_METADATA = {
    "name": "",
    "description": "",
    "params": [],
    "hidden": False,
    "disabled": False,
    "mcp_integration": {
        "enabled": True,
        "metadata": {
            "endpoint": "",
            "method": "POST",
            "authentication_required": False
        }
    },
    "llm_interaction": {
        "enabled": False,
        "auto_apply": True,
        "max_llm_turns": 15
    }
}

# Default implementation template
DEFAULT_IMPLEMENTATION = '''"""Custom command implementation."""


def command_name(*args, **kwargs):
    """Execute the command with the given arguments."""
    print("Hello World")
    return {"status": "success"}
'''

class LLMClientError(Exception):
    """Exception raised for errors in the LLM client."""
    pass


def get_openai_client() -> Any:
    """
    Get an OpenAI client instance.
    
    Returns:
        OpenAI client instance
        
    Raises:
        LLMClientError: If the OpenAI package is not installed or API key is not set
    """
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("OpenAI package not installed. Install with: pip install openai")
        raise LLMClientError("OpenAI package not installed. Install with: pip install openai")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        raise LLMClientError("OPENAI_API_KEY environment variable not set. Please set it to use LLM features.")
    
    return OpenAI(api_key=api_key)


def generate_metadata_with_llm(command_name: str, description: str) -> Dict[str, Any]:
    """
    Generate command metadata using an LLM.
    
    Args:
        command_name: The name of the command
        description: User-provided description of the command
        
    Returns:
        Dictionary containing the generated command metadata
        
    Raises:
        LLMClientError: If there's an error communicating with the LLM
    """
    try:
        client = get_openai_client()
        
        # Create a prompt for the LLM
        prompt = f"""
        Generate YAML metadata for a command named '{command_name}' with the following description:
        
        {description}
        
        The metadata should follow this structure:
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
        
        Based on the description, infer appropriate parameters that the command might need.
        Return only the YAML content, nothing else.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a smaller model for cost efficiency
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates YAML metadata for commands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic output
            max_tokens=1000
        )
        
        # Extract the YAML content from the response
        yaml_content = response.choices[0].message.content.strip()
        
        # If the response contains markdown code blocks, extract just the YAML
        if "```yaml" in yaml_content:
            yaml_content = yaml_content.split("```yaml")[1].split("```")[0].strip()
        elif "```" in yaml_content:
            yaml_content = yaml_content.split("```")[1].split("```")[0].strip()
        
        # Parse the YAML content
        metadata = yaml.safe_load(yaml_content)
        
        # Ensure the command name is set correctly
        metadata["name"] = command_name
        
        # Validate the metadata structure
        if "description" not in metadata:
            metadata["description"] = description
        
        # Ensure all required fields are present
        for key, value in DEFAULT_METADATA.items():
            if key not in metadata:
                metadata[key] = value
        
        return cast(Dict[str, Any], metadata)
    
    except Exception as e:
        logger.error(f"Error generating metadata with LLM: {e}")
        raise LLMClientError(f"Error generating metadata with LLM: {e}")

implementation_guidelines = """
            The implementation should be a Python file with a `tool_<command_name>()` function that:
            1. Accepts the parameters defined in the metadata
            2. Implements the functionality described in the metadata description
            3. Returns a result as defined in the metadata
            
            Follow these guidelines:
            - The entry point of the tool is the tool_<command_name>() function.  Other functions are allowed.
            - The input args should be simple python types
            - The output should be a simple python type
            - Include proper docstrings
            - This is not a Flask app, do not include any Flask-specific code
            - Handle parameter validation
            - Include error handling
            - Follow PEP 8 style guidelines
"""

def generate_implementation_with_llm(command_name: str, metadata: Dict[str, Any]) -> str:
    """
    Generate command implementation using an LLM.
    
    Args:
        command_name: The name of the command
        metadata: The command metadata
        
    Returns:
        String containing the generated command implementation
        
    Raises:
        LLMClientError: If there's an error communicating with the LLM
    """
    try:
        client = get_openai_client()
        
        # Create a prompt for the LLM
        prompt = f"""
        Generate a Python implementation for a command named '{command_name}' with the following metadata:
        
        ```yaml
        {yaml.dump(metadata, default_flow_style=False)}
        ```
        
        {implementation_guidelines}
        Return only the Python code, nothing else.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a smaller model for cost efficiency
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates Python code for commands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic output
            max_tokens=2000
        )
        
        # Extract the Python code from the response
        code_content = response.choices[0].message.content.strip()
        
        # If the response contains markdown code blocks, extract just the Python code
        if "```python" in code_content:
            code_content = code_content.split("```python")[1].split("```")[0].strip()
        elif "```" in code_content:
            code_content = code_content.split("```")[1].split("```")[0].strip()
        
        return cast(str, code_content)
    
    except Exception as e:
        logger.error(f"Error generating implementation with LLM: {e}")
        raise LLMClientError(f"Error generating implementation with LLM: {e}")


def check_additional_info_needed(command_name: str, description: str) -> Optional[str]:
    """
    Check if additional information is needed from the user to generate a good command.
    
    Args:
        command_name: The name of the command
        description: User-provided description of the command
        
    Returns:
        String with follow-up questions if more information is needed, None otherwise
        
    Raises:
        LLMClientError: If there's an error communicating with the LLM
    """
    try:
        client = get_openai_client()
        
        # Create a prompt for the LLM
        prompt = f"""
        I'm creating a command named '{command_name}' with the following description:
        ```
        {description}
        {implementation_guidelines}
        ```
        Based on this information, do you need any additional details to create a good command implementation?
        If yes, provide specific questions that would help clarify the command's purpose and functionality.
        If no, just respond with "No additional information needed."
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a smaller model for cost efficiency
            messages=[
                {"role": "system", "content": "You are a helpful assistant that helps users create commands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic output
            max_tokens=500
        )
        
        # Extract the response
        response_text = response.choices[0].message.content.strip()
        
        # Check if additional information is needed
        if "no additional information needed" in response_text.lower():
            return None
        
        return cast(str, response_text)
    
    except Exception as e:
        logger.error(f"Error checking for additional information: {e}")
        # Don't raise an exception here, just return None to continue with available information
        return None


def generate_default_metadata_with_llm(command_name: str, description: str = "") -> Dict[str, Any]:
    """
    Generate default metadata for a command using an LLM, with fallback to basic defaults.
    
    Args:
        command_name: The name of the command
        description: Optional description of the command
        
    Returns:
        Dictionary containing the command metadata
    """
    try:
        # If no description is provided, use a generic one
        if not description:
            description = f"Command named {command_name}"
        
        # Generate metadata with LLM
        metadata = generate_metadata_with_llm(command_name, description)
        return metadata
    
    except LLMClientError as e:
        logger.warning(f"Falling back to default metadata: {e}")
        
        # Create basic default metadata
        metadata = DEFAULT_METADATA.copy()
        metadata["name"] = command_name
        metadata["description"] = description or f"Command named {command_name}"
        
        return metadata
    
    except Exception as e:
        logger.error(f"Unexpected error generating metadata: {e}")
        
        # Create basic default metadata
        metadata = DEFAULT_METADATA.copy()
        metadata["name"] = command_name
        metadata["description"] = description or f"Command named {command_name}"
        
        return metadata 