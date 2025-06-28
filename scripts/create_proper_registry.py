#!/usr/bin/env python3
"""
Create a proper repository registry for the test repositories.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

def analyze_index(index_path):
    """Analyze an index database for statistics."""
    stats = {
        "language_stats": {},
        "total_files": 0,
        "total_symbols": 0
    }
    
    if not index_path.exists():
        return stats
    
    try:
        conn = sqlite3.connect(str(index_path))
        cursor = conn.cursor()
        
        # Count files
        cursor.execute("SELECT COUNT(*) FROM files")
        stats["total_files"] = cursor.fetchone()[0]
        
        # Count symbols
        cursor.execute("SELECT COUNT(*) FROM symbols")
        stats["total_symbols"] = cursor.fetchone()[0]
        
        # Count by language
        cursor.execute("""
            SELECT language, COUNT(*) 
            FROM files 
            GROUP BY language
        """)
        for lang, count in cursor:
            if lang:
                stats["language_stats"][lang] = count
        
        conn.close()
    except Exception as e:
        print(f"Error analyzing {index_path}: {e}")
    
    return stats


def create_proper_registry():
    """Create a proper registry for test repositories."""
    test_repos = [
        # Web frameworks
        ("d8df70cdcd6e", "django", "PathUtils.get_workspace_root()/test_repos/web/python/django"),
        ("a91ba02537ca", "flask", "PathUtils.get_workspace_root()/test_repos/web/python/flask"),
        ("bb4442cd5cc6", "express", "PathUtils.get_workspace_root()/test_repos/web/javascript/express"),
        ("7d20371e6e74", "rails", "PathUtils.get_workspace_root()/test_repos/web/ruby/rails"),
        ("e3acd2328eea", "TypeScript", "PathUtils.get_workspace_root()/test_repos/web/typescript/TypeScript"),
        ("40fdeba5e98b", "framework", "PathUtils.get_workspace_root()/test_repos/web/php/framework"),
        ("2652ff29a355", "requests", "PathUtils.get_workspace_root()/test_repos/web/python/requests"),
        ("d72d7e1e17d2", "react", "PathUtils.get_workspace_root()/test_repos/web/javascript/react"),
        ("1ccf33ab5afa", "mojo", "PathUtils.get_workspace_root()/test_repos/web/perl/mojo"),
        
        # Modern languages
        ("48f70bd595a6", "dart-sdk", "PathUtils.get_workspace_root()/test_repos/modern/dart/sdk"),
        ("e8f130fe30ac", "Alamofire", "PathUtils.get_workspace_root()/test_repos/modern/swift/Alamofire"),
        ("2c3a11a10667", "gin", "PathUtils.get_workspace_root()/test_repos/modern/go/gin"),
        ("2849ba16ec30", "terraform", "PathUtils.get_workspace_root()/test_repos/modern/go/terraform"),
    ]
    
    registry = {}
    
    for repo_id, name, path in test_repos:
        repo_path = Path(path)
        index_path = Path(f"PathUtils.get_workspace_root()/.indexes/{repo_id}/code_index.db")
        
        # Analyze the index
        stats = analyze_index(index_path)
        
        # Create registry entry
        registry[repo_id] = {
            "repository_id": repo_id,
            "name": name,
            "path": str(repo_path),
            "index_path": str(index_path),
            "language_stats": stats["language_stats"],
            "total_files": stats["total_files"],
            "total_symbols": stats["total_symbols"],
            "indexed_at": datetime.now().isoformat(),
            "active": True,
            "priority": 0
        }
        
        print(f"Added {name}: {stats['total_files']} files, {stats['total_symbols']} symbols")
    
    # Save registry
    output_path = Path("PathUtils.get_workspace_root()/.indexes/repository_registry_proper.json")
    with open(output_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\nRegistry saved to: {output_path}")
    print(f"Total repositories: {len(registry)}")


if __name__ == "__main__":
    create_proper_registry()