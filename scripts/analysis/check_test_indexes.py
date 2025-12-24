#!/usr/bin/env python3
"""
Check test_indexes directory for available BM25 indexes.
"""

import sqlite3
import json
from pathlib import Path
from mcp_server.core.path_utils import PathUtils


def check_bm25_index(db_path: Path) -> dict:
    """Check if a BM25 index exists and is valid."""
    info = {
        'path': str(db_path),
        'exists': db_path.exists(),
        'valid': False,
        'row_count': 0,
        'error': None
    }
    
    if not db_path.exists():
        info['error'] = 'File does not exist'
        return info
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check for bm25_content table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bm25_content'
        """)
        
        if cursor.fetchone():
            # Count rows
            cursor.execute("SELECT COUNT(*) FROM bm25_content")
            count = cursor.fetchone()[0]
            info['row_count'] = count
            info['valid'] = count > 0
            
            # Get sample
            cursor.execute("""
                SELECT filepath, snippet(bm25_content, -1, '', '', '...', 10)
                FROM bm25_content
                LIMIT 3
            """)
            info['samples'] = cursor.fetchall()
        else:
            info['error'] = 'No bm25_content table found'
        
        conn.close()
        
    except Exception as e:
        info['error'] = str(e)
    
    return info


def main():
    """Check all test indexes."""
    
    print("Checking Test Indexes Directory")
    print("=" * 80)
    
    test_indexes_dir = Path("PathUtils.get_workspace_root()/test_indexes")
    
    if not test_indexes_dir.exists():
        print("Test indexes directory not found!")
        return
    
    # Find all subdirectories
    repos_with_indexes = []
    
    for repo_dir in sorted(test_indexes_dir.iterdir()):
        if repo_dir.is_dir() and not repo_dir.name.startswith('.'):
            # Look for BM25 indexes
            bm25_candidates = [
                repo_dir / "simple_bm25.db",
                repo_dir / "bm25_index.db",
                repo_dir / "code_index.db"
            ]
            
            for db_path in bm25_candidates:
                if db_path.exists():
                    info = check_bm25_index(db_path)
                    if info['valid']:
                        repos_with_indexes.append({
                            'repo_name': repo_dir.name,
                            'db_file': db_path.name,
                            'db_path': db_path,
                            'row_count': info['row_count'],
                            'samples': info.get('samples', [])
                        })
                        break
    
    print(f"\nFound {len(repos_with_indexes)} repositories with valid BM25 indexes:")
    
    for i, repo in enumerate(repos_with_indexes, 1):
        print(f"\n{i}. {repo['repo_name']}")
        print(f"   DB: {repo['db_file']}")
        print(f"   Rows: {repo['row_count']}")
        if repo['samples']:
            print("   Samples:")
            for filepath, snippet in repo['samples'][:2]:
                print(f"     - {filepath}")
                print(f"       {snippet[:80]}...")
    
    # Check if we can create symlinks to central location
    print("\n\nChecking if we can link these to central storage...")
    
    central_dir = Path.home() / ".mcp" / "indexes"
    
    # For now, let's use these local indexes directly
    print("\nThese indexes are in test_indexes directory, not centralized.")
    print("We can either:")
    print("1. Move them to central location")
    print("2. Modify MCP to check test_indexes directory")
    print("3. Create new indexes using mcp-index tool")
    
    # Save summary
    summary = {
        'test_indexes_found': len(repos_with_indexes),
        'repositories': repos_with_indexes
    }
    
    with open('test_indexes_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\nSummary saved to test_indexes_summary.json")


if __name__ == "__main__":
    main()