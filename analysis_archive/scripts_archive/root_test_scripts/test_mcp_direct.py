#\!/usr/bin/env python3
"""Test MCP server directly."""

import asyncio
import json
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

async def test_dispatcher():
    """Test the dispatcher directly."""
    # Initialize SQLite store
    db_path = Path.home() / ".mcp/indexes/f7b49f5d0ae0/current.db"
    print(f"Testing with database: {db_path}")
    print(f"Database exists: {db_path.exists()}")
    
    if not db_path.exists():
        print("ERROR: Database not found\!")
        return
    
    # Create store
    store = SQLiteStore(str(db_path))
    print(f"SQLite store initialized")
    
    # Create dispatcher
    dispatcher = EnhancedDispatcher(
        plugins=[],
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False
    )
    print(f"Dispatcher created with {len(dispatcher._plugins)} plugins")
    
    # Test symbol lookup
    print("\n=== Testing symbol lookup ===")
    result = dispatcher.lookup("BM25Indexer")
    print(f"Lookup result: {json.dumps(result, indent=2)}")
    
    # Test search
    print("\n=== Testing search ===")
    results = list(dispatcher.search("reranking", limit=5))
    print(f"Search found {len(results)} results")
    for i, r in enumerate(results[:3]):
        print(f"{i+1}. {r.get('file')}:{r.get('line')} - {r.get('snippet', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_dispatcher())
EOF < /dev/null
