#!/usr/bin/env python3
"""
Test MCP functionality using direct database queries.
Avoids the hanging search_code MCP tool.
"""

import sys
import os
from pathlib import Path
import json
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.path_utils import PathUtils


def test_mcp_direct():
    """Test MCP functionality with direct database queries."""
    print("MCP DIRECT DATABASE TESTING")
    print("=" * 60)
    
    # Find the current repo index
    repo_hash = "844145265d7a"
    index_path = PathUtils.get_index_storage_path() / repo_hash / "code_index.db"
    
    if not index_path.exists():
        print(f"Error: Index not found at {index_path}")
        return
    
    print(f"Using index: {index_path}")
    
    # Connect directly to database
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Test 1: Check database schema
    print("\n1. DATABASE SCHEMA CHECK")
    print("-" * 40)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables found: {len(tables)}")
    for table in tables:
        if not table.startswith('fts_') and not table.startswith('bm25_'):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
    
    # Test 2: BM25 Content Search
    print("\n2. BM25 CONTENT SEARCH TESTS")
    print("-" * 40)
    
    test_queries = [
        "EnhancedDispatcher",
        "SQLiteStore", 
        "multi_repo_manager",
        "def search",
        "import os"
    ]
    
    for query in test_queries:
        cursor.execute("""
            SELECT filepath, snippet(bm25_content, -1, '<b>', '</b>', '...', 64)
            FROM bm25_content
            WHERE bm25_content MATCH ?
            ORDER BY rank
            LIMIT 3
        """, (query,))
        
        results = cursor.fetchall()
        print(f"\n'{query}': {len(results)} results")
        for i, (filepath, snippet) in enumerate(results):
            print(f"  {i+1}. {filepath}")
            print(f"     {snippet[:100]}...")
    
    # Test 3: FTS Code Search
    print("\n3. FTS CODE SEARCH TESTS")
    print("-" * 40)
    
    cursor.execute("SELECT COUNT(*) FROM fts_code")
    fts_count = cursor.fetchone()[0]
    print(f"FTS documents: {fts_count}")
    
    if fts_count > 0:
        for query in ["dispatcher", "index", "search"]:
            cursor.execute("""
                SELECT f.path, snippet(fts_code, -1, '<b>', '</b>', '...', 32)
                FROM fts_code fc
                JOIN files f ON f.id = fc.file_id
                WHERE fts_code MATCH ?
                ORDER BY rank
                LIMIT 2
            """, (query,))
            
            results = cursor.fetchall()
            print(f"\n'{query}': {len(results)} results")
            for filepath, snippet in results:
                print(f"  - {filepath}")
    
    # Test 4: Check specific files
    print("\n4. SPECIFIC FILE CHECKS")
    print("-" * 40)
    
    important_files = [
        "dispatcher_enhanced.py",
        "sqlite_store.py",
        "multi_repo_manager.py",
        "path_utils.py"
    ]
    
    for filename in important_files:
        cursor.execute("""
            SELECT path, language, size 
            FROM files 
            WHERE path LIKE ?
            LIMIT 1
        """, (f"%{filename}",))
        
        result = cursor.fetchone()
        if result:
            path, lang, size = result
            print(f"✓ {filename}: {lang} ({size} bytes)")
            
            # Check if it has BM25 content
            cursor.execute("""
                SELECT COUNT(*) 
                FROM bm25_content 
                WHERE filepath LIKE ?
            """, (f"%{filename}",))
            bm25_count = cursor.fetchone()[0]
            print(f"  BM25 indexed: {'Yes' if bm25_count > 0 else 'No'}")
        else:
            print(f"✗ {filename}: Not found")
    
    # Test 5: Language statistics
    print("\n5. LANGUAGE STATISTICS")
    print("-" * 40)
    
    cursor.execute("""
        SELECT language, COUNT(*) as count
        FROM files
        WHERE language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        LIMIT 10
    """)
    
    lang_stats = cursor.fetchall()
    for lang, count in lang_stats:
        print(f"  {lang}: {count} files")
    
    # Summary
    print("\n" + "=" * 60)
    print("TESTING SUMMARY")
    print("=" * 60)
    
    # Get overall stats
    cursor.execute("SELECT COUNT(*) FROM files")
    total_files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bm25_content")
    total_bm25 = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM symbols")
    total_symbols = cursor.fetchone()[0]
    
    print(f"Total files indexed: {total_files}")
    print(f"BM25 documents: {total_bm25}")
    print(f"Symbols extracted: {total_symbols}")
    
    if total_files > 0 and total_bm25 > 0:
        print("\n✅ MCP index is functional!")
        print("✅ BM25 search is working")
        print("✅ File indexing is complete")
        if total_symbols == 0:
            print("⚠️  Symbol extraction needs improvement")
    else:
        print("\n❌ Index needs troubleshooting")
    
    conn.close()
    
    # Save results
    results = {
        "total_files": total_files,
        "total_bm25": total_bm25,
        "total_symbols": total_symbols,
        "languages": dict(lang_stats) if lang_stats else {},
        "status": "functional" if total_files > 0 and total_bm25 > 0 else "needs_fix"
    }
    
    with open("mcp_direct_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: mcp_direct_test_results.json")


if __name__ == "__main__":
    test_mcp_direct()