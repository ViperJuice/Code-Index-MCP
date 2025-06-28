#!/usr/bin/env python3
"""
Reindex test repositories for benchmark testing
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import subprocess
from tqdm import tqdm

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher


def find_test_repositories():
    """Find all test repositories."""
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    # Find all directories with .git folders
    for git_dir in test_repos_dir.rglob("*.git"):
        repo_path = git_dir.parent
        repo_name = f"{repo_path.parent.name}_{repo_path.name}"
        
        repos.append({
            "name": repo_name,
            "path": str(repo_path),
            "language": repo_path.parent.parent.name  # Category name as proxy for language
        })
    
    return repos


def index_repository(repo_info, output_dir):
    """Index a single repository."""
    repo_name = repo_info["name"]
    repo_path = repo_info["path"]
    
    print(f"\nIndexing {repo_name}...")
    
    # Create output directory
    index_dir = output_dir / repo_name.replace("/", "_")
    index_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize storage
    db_path = index_dir / "bm25_index.db"
    storage = SQLiteStore(str(db_path))
    
    # Initialize indexer
    indexer = BM25Indexer(storage)
    
    # Get all code files
    code_files = []
    for ext in ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift', '.kt']:
        code_files.extend(Path(repo_path).rglob(f"*{ext}"))
    
    # Index files
    documents = []
    for file_path in code_files[:1000]:  # Limit to 1000 files per repo
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            rel_path = file_path.relative_to(repo_path)
            
            documents.append({
                'id': str(hash(str(file_path))),  # Add ID field
                'file_id': str(file_path),
                'filepath': str(rel_path),
                'filename': file_path.name,
                'content': content,
                'language': file_path.suffix[1:] if file_path.suffix else 'unknown',
                'symbols': '',  # Would be extracted by language plugins
                'imports': '',
                'comments': ''
            })
            
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
    
    # Index documents
    if documents:
        indexer.index_documents(documents)
        print(f"  Indexed {len(documents)} files")
        
        # Skip metrics update - table structure doesn't match
    else:
        print(f"  No files found to index")
    
    return len(documents)


def main():
    """Main entry point."""
    # Find repositories
    repos = find_test_repositories()
    print(f"Found {len(repos)} test repositories")
    
    # Output directory
    output_dir = Path("/workspaces/Code-Index-MCP/test_indexes")
    
    # Index subset for testing (first 5)
    total_files = 0
    indexed_repos = []
    
    for repo in tqdm(repos[:5], desc="Indexing repositories"):
        try:
            file_count = index_repository(repo, output_dir)
            total_files += file_count
            indexed_repos.append({
                **repo,
                'indexed_files': file_count,
                'status': 'success'
            })
        except Exception as e:
            print(f"Error indexing {repo['name']}: {e}")
            indexed_repos.append({
                **repo,
                'indexed_files': 0,
                'status': 'failed',
                'error': str(e)
            })
    
    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_repos': len(indexed_repos),
        'successful': sum(1 for r in indexed_repos if r['status'] == 'success'),
        'total_files_indexed': total_files,
        'repositories': indexed_repos
    }
    
    summary_path = output_dir / "indexing_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Indexing complete!")
    print(f"   Repositories: {len(indexed_repos)}")
    print(f"   Total files: {total_files}")
    print(f"   Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()