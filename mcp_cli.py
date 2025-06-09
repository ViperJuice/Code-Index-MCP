#!/usr/bin/env python3
"""
MCP Server CLI - Main entry point for command-line tools.

Usage:
    python mcp_cli.py index check-compatibility
    python mcp_cli.py index rebuild --force
    python mcp_cli.py index status
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

from mcp_server.cli import cli

if __name__ == '__main__':
    cli()