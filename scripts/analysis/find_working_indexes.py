#!/usr/bin/env python3
"""
Find indexes with the correct bm25_content structure.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

def find_working_indexes():
    """Find indexes with bm25_content table."""
    index_path = PathUtils.get_index_storage_path()
    working_indexes = []
    
    print("Searching for working indexes...")
    print("=" * 60)
    
    for db_file in index_path.glob("*/code_index.db"):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check if bm25_content exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'"
            )
            if cursor.fetchone():
                # Get row count
                cursor.execute("SELECT COUNT(*) FROM bm25_content")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    # Test a search
                    cursor.execute(
                        "SELECT COUNT(*) FROM bm25_content WHERE bm25_content MATCH 'def'"
                    )
                    search_count = cursor.fetchone()[0]
                    
                    print(f"\n✓ Working index: {db_file}")
                    print(f"  Total documents: {count}")
                    print(f"  'def' matches: {search_count}")
                    
                    working_indexes.append({
                        "path": db_file,
                        "repo_id": db_file.parent.name,
                        "doc_count": count,
                        "test_results": search_count
                    })
            
            conn.close()
        except Exception as e:
            print(f"✗ Error checking {db_file}: {e}")
    
    print(f"\n\nFound {len(working_indexes)} working indexes")
    
    # Check for current repository
    print("\n\nLooking for current repository index...")
    current_repo_path = str(PathUtils.get_workspace_root())
    
    for idx in working_indexes:
        conn = sqlite3.connect(idx["path"])
        cursor = conn.cursor()
        
        # Check if it contains files from current repo
        cursor.execute(
            "SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE ?",
            (f"%{current_repo_path}%",)
        )
        if cursor.fetchone()[0] > 0:
            print(f"✓ Found current repo index at: {idx['path']}")
            print(f"  Repo ID: {idx['repo_id']}")
            
            # Test PathUtils search
            cursor.execute(
                "SELECT filepath FROM bm25_content WHERE bm25_content MATCH 'PathUtils' LIMIT 5"
            )
            results = cursor.fetchall()
            print(f"  PathUtils search results: {len(results)}")
            for (path,) in results:
                print(f"    - {path}")
        
        conn.close()
    
    return working_indexes

if __name__ == "__main__":
    find_working_indexes()