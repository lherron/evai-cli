"""
Tool for deploying React component artifacts.

This tool saves React component artifacts to the artifacts directory.
"""

import os
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

def tool_deploy_artifact(artifact_name: str, source_code: str) -> Dict[str, Any]:
    """
    Deploy a React component artifact to the artifacts directory.
    
    Args:
        artifact_name: The name of the artifact (will be used as the filename)
        source_code: The source code of the React component
        
    Returns:
        A dictionary with the status of the deployment
    """
    logger.debug(f"Deploying artifact: {artifact_name}")
    
    try:
        # Ensure artifact name is valid
        if not artifact_name:
            raise ValueError("Artifact name cannot be empty")
        
        # Ensure artifact name has proper extension
        if not artifact_name.endswith('.tsx'):
            artifact_name = f"{artifact_name}.tsx"
        
        # Get the artifacts directory path
        artifacts_dir = os.path.expanduser("~/projects/evai-cli/evai/artifacts")
        
        # Create the directory if it doesn't exist
        os.makedirs(artifacts_dir, exist_ok=True)
        
        # Create the full path to the artifact file
        artifact_path = os.path.join(artifacts_dir, artifact_name)
        
        # Write the source code to the file
        with open(artifact_path, "w") as f:
            f.write(source_code)
        
        logger.info(f"Successfully deployed artifact to {artifact_path}")
        
        return {
            "status": "success",
            "message": f"Artifact '{artifact_name}' deployed successfully",
            "path": artifact_path
        }
        
    except Exception as e:
        logger.error(f"Error deploying artifact: {e}")
        return {
            "status": "error",
            "message": str(e)
        } 