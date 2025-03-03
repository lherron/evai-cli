"""Tests for the EVAI CLI."""

import subprocess
import sys
from unittest import mock

import click.testing
import pytest

from evai import __version__
from evai.cli import cli, main


def test_version():
    """Test that the version is correct."""
    assert __version__ == "0.1.0"


def test_cli_help():
    """Test that the CLI prints help when invoked with --help."""
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "EVAI CLI - Command-line interface for EVAI" in result.output


def test_cli_version():
    """Test that the CLI prints version when invoked with --version."""
    runner = click.testing.CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert f"evai, version {__version__}" in result.output


def test_main_no_args():
    """Test that main() shows help when no arguments are provided."""
    with mock.patch("sys.argv", ["evai"]):
        with mock.patch("evai.cli.cli") as mock_cli:
            main()
            mock_cli.assert_called_once()
            # Check that --help was added to sys.argv
            assert sys.argv == ["evai", "--help"]


def test_cli_as_module():
    """Test that the CLI can be invoked as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "evai.cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert f"version {__version__}" in result.stdout 