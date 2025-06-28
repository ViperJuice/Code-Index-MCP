#!/usr/bin/env python3
"""Test MCP functionality directly"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mcp_directly():
    """Test MCP functionality without the server wrapper"""
    
    # Find the correct database
    index_path = Path(".indexes/f7b49f5d0ae0/current.db")
    
    if not index_path.exists():
        print(f"Database not found at {index_path}")
        return
    
    print(f"Using database: {index_path}")
    
    # Initialize SQLite store
    sqlite_store = SQLiteStore(str(index_path))
    
    # Create dispatcher
    dispatcher = EnhancedDispatcher(
        plugins=[],
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False  # Disable semantic for now
    )
    
    # Test 1: Symbol lookup
    print("\n=== Testing Symbol Lookup ===")
    result = dispatcher.lookup("EnhancedDispatcher")
    print(f"Lookup result: {result}")
    
    # Test 2: Code search
    print("\n=== Testing Code Search ===")
    results = list(dispatcher.search("dispatcher", limit=5))
    print(f"Search found {len(results)} results")
    for i, r in enumerate(results[:3]):
        print(f"\nResult {i+1}:")
        print(f"  File: {r.get('file', 'N/A')}")
        print(f"  Line: {r.get('line', 'N/A')}")
        print(f"  Match: {r.get('match', 'N/A')[:100]}...")
    
    # Test 3: Check database content
    print("\n=== Checking Database Content ===")
    try:
        import sqlite3
        conn = sqlite3.connect(str(index_path))
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        # Check content count
        cursor.execute("SELECT COUNT(*) FROM bm25_content;")
        count = cursor.fetchone()[0]
        print(f"Total entries in bm25_content: {count}")
        
        # Sample content
        cursor.execute("SELECT filepath, language FROM bm25_content LIMIT 5;")
        samples = cursor.fetchall()
        print("\nSample entries:")
        for filepath, language in samples:
            print(f"  {filepath} ({language})")
        
        conn.close()
    except Exception as e:
        print(f"Database check error: {e}")


if __name__ == "__main__":
    test_mcp_directly()