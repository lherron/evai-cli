"""Test configuration and shared fixtures."""

import os
import pytest
from typing import Generator
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test_key",
        "EVAI_DEFAULT_PROVIDER": "anthropic",
        "EVAI_DEFAULT_TOOL_EXECUTOR": "local"
    }):
        yield

@pytest.fixture(autouse=True)
def mock_asyncio_sleep():
    """Mock asyncio.sleep to speed up tests."""
    with patch("asyncio.sleep", return_value=None):
        yield

@pytest.fixture(autouse=True)
def mock_logging():
    """Mock logging to avoid output during tests."""
    with patch("logging.getLogger") as mock_logger:
        yield mock_logger 