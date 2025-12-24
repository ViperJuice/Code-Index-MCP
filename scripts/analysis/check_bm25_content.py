#!/usr/bin/env python3
"""
Check BM25 index content to diagnose why searches return 0 results.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

def check_bm25_content():
    """Check content in BM25 indexes."""
    index_path = PathUtils.get_index_storage_path()
    db_files = list(index_path.glob("*/code_index.db"))
    
    print(f"Found {len(db_files)} index databases")
    
    for db_file in db_files[:3]:  # Check first 3
        repo_id = db_file.parent.name
        print(f"\n[Repository: {repo_id}]")
        print(f"Database: {db_file}")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Check table structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Tables: {tables}")
            
            # Check code_blocks table
            if 'code_blocks' in tables:
                cursor.execute("SELECT COUNT(*) FROM code_blocks")
                count = cursor.fetchone()[0]
                print(f"Total code blocks: {count}")
                
                # Sample content
                cursor.execute("SELECT file, content FROM code_blocks LIMIT 3")
                for file, content in cursor.fetchall():
                    print(f"\nFile: {file}")
                    print(f"Content preview: {content[:100]}...")
                    if content.startswith("sha256:"):
                        print("⚠️  WARNING: Content is stored as hash, not actual text!")
            
            # Check if FTS5 tables exist
            fts_tables = [t for t in tables if 'fts5' in t.lower() or t.endswith('_fts')]
            if fts_tables:
                print(f"\nFTS5 tables: {fts_tables}")
                for fts_table in fts_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
                    count = cursor.fetchone()[0]
                    print(f"  {fts_table}: {count} entries")
            else:
                print("\n⚠️  No FTS5 tables found!")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading database: {e}")
    
    # Check current repository specifically
    print("\n" + "="*60)
    print("CHECKING CURRENT REPOSITORY")
    current_db = index_path / "current" / "code_index.db"
    if current_db.exists():
        print(f"Current repo DB: {current_db}")
        try:
            conn = sqlite3.connect(current_db)
            cursor = conn.cursor()
            
            # Check if we have actual indexed content
            cursor.execute("SELECT COUNT(*) FROM code_blocks WHERE content NOT LIKE 'sha256:%'")
            good_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM code_blocks WHERE content LIKE 'sha256:%'")
            hash_count = cursor.fetchone()[0]
            
            print(f"Blocks with actual content: {good_count}")
            print(f"Blocks with hash content: {hash_count}")
            
            if hash_count > 0 and good_count == 0:
                print("\n⚠️  CRITICAL: All content is stored as hashes!")
                print("This is why searches return 0 results.")
                print("The indexes need to be rebuilt with actual content.")
            
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No index found for current repository")

if __name__ == "__main__":
    check_bm25_content()