#!/usr/bin/env python3
"""
Verify test repository indexes and prepare for comprehensive testing.
"""

import os
import sys
import subprocess
import hashlib
import sqlite3
from pathlib import Path
import json
from typing import Dict, List, Tuple

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_repo_hash(repo_path: Path) -> str:
    """Get repository hash for centralized storage."""
    try:
        # Get git remote URL
        result = subprocess.run(
            ['git', '-C', str(repo_path), 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, check=True
        )
        remote_url = result.stdout.strip()
    except:
        # If no remote, use absolute path
        remote_url = str(repo_path.resolve())
    
    # Generate hash
    return hashlib.sha256(remote_url.encode()).hexdigest()[:12]


def check_index_status(repo_path: Path) -> Dict[str, any]:
    """Check if repository has a valid index."""
    repo_hash = get_repo_hash(repo_path)
    central_dir = Path.home() / ".mcp" / "indexes" / repo_hash
    
    status = {
        "path": str(repo_path),
        "name": repo_path.name,
        "hash": repo_hash,
        "has_index": False,
        "index_path": None,
        "document_count": 0,
        "has_bm25": False,
        "has_semantic": False
    }
    
    # Check for current.db symlink
    current_db = central_dir / "current.db"
    if current_db.exists():
        try:
            # Get actual index path
            index_path = current_db.resolve()
            status["index_path"] = str(index_path)
            status["has_index"] = True
            
            # Check document count
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            
            # Check for documents
            try:
                cursor.execute("SELECT COUNT(*) FROM documents")
                status["document_count"] = cursor.fetchone()[0]
            except:
                pass
            
            # Check for BM25 data
            try:
                cursor.execute("SELECT COUNT(*) FROM bm25_index")
                status["has_bm25"] = cursor.fetchone()[0] > 0
            except:
                pass
            
            # Check for semantic data (embeddings)
            try:
                cursor.execute("SELECT COUNT(*) FROM embeddings")
                status["has_semantic"] = cursor.fetchone()[0] > 0
            except:
                pass
            
            conn.close()
            
        except Exception as e:
            status["error"] = str(e)
    
    return status


def find_test_repositories() -> List[Path]:
    """Find all test repositories."""
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    # Find all .git directories
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    return repos


def main():
    """Main function to verify test repo indexes."""
    print("Verifying Test Repository Indexes")
    print("=" * 60)
    
    repos = find_test_repositories()
    print(f"Found {len(repos)} test repositories\n")
    
    # Check each repository
    indexed_repos = []
    need_indexing = []
    need_semantic = []
    
    for repo in repos:
        status = check_index_status(repo)
        
        if status["has_index"] and status["document_count"] > 0:
            indexed_repos.append(status)
            if not status["has_semantic"]:
                need_semantic.append(status)
        else:
            need_indexing.append(status)
    
    # Summary
    print(f"\nSummary:")
    print(f"  Fully indexed: {len(indexed_repos) - len(need_semantic)}")
    print(f"  Missing semantic data: {len(need_semantic)}")
    print(f"  Need indexing: {len(need_indexing)}")
    print(f"  Total: {len(repos)}")
    
    # Detailed status
    print("\n" + "=" * 60)
    print("Repository Status Details")
    print("=" * 60)
    
    print("\n✅ Fully Indexed Repositories:")
    for status in indexed_repos:
        if status not in need_semantic:
            print(f"  {status['name']:20} - {status['document_count']:5} docs, "
                  f"BM25: {'✓' if status['has_bm25'] else '✗'}, "
                  f"Semantic: {'✓' if status['has_semantic'] else '✗'}")
    
    if need_semantic:
        print("\n⚠️  Missing Semantic Data:")
        for status in need_semantic:
            print(f"  {status['name']:20} - {status['document_count']:5} docs")
    
    if need_indexing:
        print("\n❌ Need Indexing:")
        for status in need_indexing:
            print(f"  {status['name']:20} - {status['path']}")
    
    # Save detailed report
    report = {
        "total_repos": len(repos),
        "indexed": len(indexed_repos),
        "need_semantic": len(need_semantic),
        "need_indexing": len(need_indexing),
        "repositories": {
            "indexed": indexed_repos,
            "need_semantic": need_semantic,
            "need_indexing": need_indexing
        }
    }
    
    report_path = Path("/workspaces/Code-Index-MCP/test_repo_index_status.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Return repos ready for testing
    ready_repos = [r for r in indexed_repos if r not in need_semantic]
    print(f"\n✅ {len(ready_repos)} repositories ready for testing")
    
    return ready_repos


if __name__ == "__main__":
    main()