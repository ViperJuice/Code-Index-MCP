#!/usr/bin/env python3
"""Compatibility wrapper for packaged artifact download logic."""

from __future__ import annotations

import sys

from mcp_server.artifacts.artifact_download import main


if __name__ == "__main__":
    sys.exit(main())
