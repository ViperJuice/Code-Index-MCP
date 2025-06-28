#!/usr/bin/env python3
"""Quick script to index current repo to central location."""

import subprocess
import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Index the current repo
repo_path = "PathUtils.get_workspace_root()"
print(f"Indexing {repo_path} to central location...")

# Use the existing indexing script
cmd = [
    sys.executable,
    "PathUtils.get_workspace_root()/scripts/utilities/index_complete.py",
    repo_path
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print(f"Exit code: {result.returncode}")