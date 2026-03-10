"""
Main entry point for running loadgen as a module.

This module enables running the CLI via 'python3 -m loadgen'.
"""

from loadgen.cli import cli

if __name__ == "__main__":
    cli()
