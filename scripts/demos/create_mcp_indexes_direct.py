#!/usr/bin/env python3
"""
Create MCP-compatible indexes directly for test repositories.
This script creates indexes that work with the MCP server.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging
import os
import hashlib
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_bm25_index(db_path: str):
    """Create the BM25 FTS5 table in the database."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Create the FTS5 table for BM25 indexing
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS bm25_content USING fts5(
            path,
            content,
            tokenize='unicode61 remove_diacritics 2'
        )
    """)
    
    # Create metadata table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bm25_metadata (
            path TEXT PRIMARY KEY,
            file_hash TEXT,
            size INTEGER,
            language TEXT,
            indexed_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def index_file(conn: sqlite3.Connection, file_path: Path, repo_path: Path) -> bool:
    """Index a single file."""
    try:
        # Read file content
        content = file_path.read_text(encoding='utf-8')
        relative_path = str(file_path.relative_to(repo_path))
        
        # Calculate file hash
        file_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Detect language from extension
        ext = file_path.suffix.lower()
        language_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.cs': 'csharp',
            '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
            '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.dart': 'dart', '.lua': 'lua', '.pl': 'perl', '.ex': 'elixir'
        }
        language = language_map.get(ext, 'unknown')
        
        # Insert into FTS5 table
        conn.execute(
            "INSERT OR REPLACE INTO bm25_content(path, content) VALUES (?, ?)",
            (relative_path, content)
        )
        
        # Insert metadata
        conn.execute(
            """INSERT OR REPLACE INTO bm25_metadata
               (path, file_hash, size, language, indexed_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (relative_path, file_hash, len(content), language, datetime.now().isoformat())
        )
        
        return True
    except Exception as e:
        logger.debug(f"Failed to index {file_path}: {e}")
        return False


def create_index_for_repo(repo_path: Path, index_path: Path) -> Dict[str, Any]:
    """Create an MCP-compatible index for a single repository."""
    logger.info(f"Creating index for {repo_path.name} at {index_path}")
    
    # Ensure index directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing index if present
    if index_path.exists():
        os.remove(index_path)
    
    # Create database and tables
    create_bm25_index(str(index_path))
    
    # Open connection for indexing
    conn = sqlite3.connect(str(index_path))
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Index the repository
    indexed_files = 0
    errors = 0
    
    # Walk through all files in the repository
    for file_path in repo_path.rglob("*"):
        if file_path.is_file():
            # Skip common non-code files
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if file_path.suffix in ['.pyc', '.pyo', '.so', '.dylib', '.dll', '.jar', '.class']:
                continue
            if file_path.stat().st_size > 1024 * 1024:  # Skip files > 1MB
                continue
            
            # Try to index the file
            if index_file(conn, file_path, repo_path):
                indexed_files += 1
                if indexed_files % 50 == 0:
                    logger.info(f"  Indexed {indexed_files} files...")
                    conn.commit()  # Commit periodically
            else:
                errors += 1
    
    # Final commit and optimize
    conn.commit()
    conn.execute("INSERT INTO bm25_content(bm25_content) VALUES('optimize')")
    conn.close()
    
    # Create metadata
    metadata = {
        "repository": repo_path.name,
        "path": str(repo_path),
        "indexed_files": indexed_files,
        "errors": errors,
        "status": "success" if indexed_files > 0 else "error",
        "created_at": datetime.now().isoformat()
    }
    
    logger.info(f"Completed indexing {repo_path.name}: {indexed_files} files indexed, {errors} errors")
    
    return metadata


def main():
    """Main function to create indexes for all test repositories."""
    # Base paths
    test_repos_base = Path("PathUtils.get_workspace_root()/test_repos")
    test_indexes_base = Path("PathUtils.get_workspace_root()/test_indexes")
    
    # Select a subset of repos for testing
    test_repos = [
        # Start with the ones from the original indexing_summary.json
        ("other/csharp/aspnetcore", "csharp_aspnetcore"),
        ("other/lua/kong", "lua_kong"),
        ("modern/swift/Alamofire", "swift_Alamofire"),
        ("modern/dart/sdk", "dart_sdk"),
        ("modern/go/gin", "go_gin"),
        
        # Add a few more
        ("systems/c/redis", "c_redis"),
        ("web/python/django", "python_django"),
        ("web/javascript/react", "javascript_react"),
        ("systems/rust/tokio", "rust_tokio"),
        ("web/typescript/TypeScript", "typescript_TypeScript"),
    ]
    
    results = []
    
    for repo_subpath, index_name in test_repos:
        repo_path = test_repos_base / repo_subpath
        
        if not repo_path.exists():
            logger.warning(f"Repository not found: {repo_path}")
            continue
            
        # Create index path - use code_index.db for MCP compatibility
        index_dir = test_indexes_base / index_name
        index_path = index_dir / "code_index.db"
        
        # Create the index
        try:
            result = create_index_for_repo(repo_path, index_path)
            results.append(result)
            
            # Create MCP configuration files
            if result["status"] == "success":
                # Create .mcp-index.json
                mcp_config = {
                    "version": "1.0",
                    "enabled": True,
                    "auto_download": False,
                    "github_artifacts": {
                        "enabled": False
                    }
                }
                
                config_path = index_dir / ".mcp-index.json"
                with open(config_path, 'w') as f:
                    json.dump(mcp_config, f, indent=2)
                
                # Create .index_metadata.json  
                metadata = {
                    "version": "1.0",
                    "created_at": result["created_at"],
                    "indexed_files": result["indexed_files"],
                    "repository": result["repository"],
                    "path": result["path"]
                }
                
                metadata_path = index_dir / ".index_metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Failed to index {repo_path.name}: {e}")
            results.append({
                "repository": repo_path.name,
                "status": "error",
                "error": str(e)
            })
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_repos": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "total_files_indexed": sum(r.get("indexed_files", 0) for r in results),
        "repositories": results
    }
    
    summary_path = test_indexes_base / "mcp_indexing_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nIndexing complete!")
    logger.info(f"Total repositories: {summary['total_repos']}")
    logger.info(f"Successful: {summary['successful']}") 
    logger.info(f"Total files indexed: {summary['total_files_indexed']}")
    logger.info(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()