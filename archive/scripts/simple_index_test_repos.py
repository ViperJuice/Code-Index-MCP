#!/usr/bin/env python3
"""
Simple indexing script for test repositories.
"""

import os
import sys
import time
import hashlib
import subprocess
from pathlib import Path
import sqlite3

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer


def get_repo_hash(repo_path: Path) -> str:
    """Get repository hash for centralized storage."""
    return hashlib.sha256(str(repo_path.resolve()).encode()).hexdigest()[:12]


def simple_index_repo(repo_path: Path) -> bool:
    """Simple indexing of a repository."""
    print(f"Indexing {repo_path.name}...", end=" ", flush=True)
    
    try:
        # Get central storage location
        repo_hash = get_repo_hash(repo_path)
        central_dir = Path.home() / ".mcp" / "indexes" / repo_hash
        central_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index database
        db_path = central_dir / "simple_index.db"
        
        # Initialize storage
        storage = SQLiteStore(str(db_path))
        
        # Initialize BM25 indexer
        indexer = BM25Indexer(storage)
        
        # Find code files
        code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php']
        files_indexed = 0
        
        for ext in code_extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                # Skip test files and common exclusions
                if any(skip in str(file_path) for skip in ['test_', '__pycache__', 'node_modules', '.git']):
                    continue
                    
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Create document
                    doc = {
                        'id': hashlib.md5(str(file_path).encode()).hexdigest(),
                        'file_id': str(file_path),
                        'filepath': str(file_path.relative_to(repo_path)),
                        'filename': file_path.name,
                        'content': content,
                        'language': ext[1:],  # Remove dot
                        'symbols': '',  # Simple indexing doesn't extract symbols
                        'imports': '',
                        'comments': ''
                    }
                    
                    # Index document
                    indexer.index_documents([doc])
                    files_indexed += 1
                    
                    # Limit files per repo for speed
                    if files_indexed >= 100:
                        break
                        
                except Exception:
                    continue
                    
            if files_indexed >= 100:
                break
        
        # Create symlink for current
        current_link = central_dir / "current.db"
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to("simple_index.db")
        
        # Verify indexing
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        conn.close()
        
        if doc_count > 0:
            print(f"✅ ({doc_count} files)")
            return True
        else:
            print("❌ (no files indexed)")
            return False
            
    except Exception as e:
        print(f"❌ ({str(e)[:30]}...)")
        return False


def main():
    """Main function."""
    print("Simple Test Repository Indexing")
    print("=" * 60)
    
    # Get test repos
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    print(f"Found {len(repos)} repositories\n")
    
    # Index first 20 repos
    success_count = 0
    
    for i, repo in enumerate(repos[:20]):
        print(f"[{i+1}/20] ", end="")
        if simple_index_repo(repo):
            success_count += 1
    
    print(f"\n✅ Successfully indexed: {success_count}/20 repositories")
    
    # Also index the main Code-Index-MCP repo
    print("\nIndexing main Code-Index-MCP repository...")
    main_repo = Path("/workspaces/Code-Index-MCP")
    if simple_index_repo(main_repo):
        print("✅ Main repository indexed")
    
    return success_count


if __name__ == "__main__":
    main()