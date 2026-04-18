#!/usr/bin/env python3
# Shim — logic lives in mcp_server.cli.stdio_runner (P2B SL-2).
from mcp_server.cli.stdio_runner import main, run  # noqa: F401

if __name__ == "__main__":
    run()
