#!/usr/bin/env python3
"""
Convert repository registry to the format expected by RepositoryRegistry.
"""

import json
from pathlib import Path
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

def convert_registry():
    """Convert registry format."""
    registry_path = Path("PathUtils.get_workspace_root()/PathUtils.get_repo_registry_path()")
    
    # Read current registry
    with open(registry_path, 'r') as f:
        current_data = json.load(f)
    
    # Convert to new format
    new_registry = {}
    
    if "repositories" in current_data:
        # Current format has nested structure
        for repo_id, repo_info in current_data["repositories"].items():
            # Convert to flat format expected by RepositoryRegistry
            new_registry[repo_id] = {
                "repository_id": repo_id,
                "name": repo_info.get("name", "unknown"),
                "path": repo_info.get("path", ""),
                "index_path": f"PathUtils.get_workspace_root()/.indexes/{repo_id}/code_index.db",
                "language_stats": {},  # Would need to analyze
                "total_files": 0,
                "total_symbols": 0,
                "indexed_at": repo_info.get("last_indexed", datetime.now().isoformat()),
                "active": True,
                "priority": 0
            }
    else:
        # Already in correct format?
        new_registry = current_data
    
    # Write converted registry
    output_path = registry_path.with_suffix(".converted.json")
    with open(output_path, 'w') as f:
        json.dump(new_registry, f, indent=2)
    
    print(f"Converted registry saved to: {output_path}")
    print(f"Found {len(new_registry)} repositories")
    
    # Show a few entries
    for repo_id, info in list(new_registry.items())[:3]:
        print(f"  - {repo_id}: {info['name']} at {info['path']}")


if __name__ == "__main__":
    convert_registry()