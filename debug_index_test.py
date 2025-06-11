#!/usr/bin/env python3
"""Debug why .env files aren't showing up in the index."""

import os
import shutil
from pathlib import Path
import sqlite3
import sys

# Test in a subdirectory of /app
test_dir = Path("/app/test_debug_index")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()

os.chdir(test_dir)

# Import after changing directory
sys.path.insert(0, '/app')
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def main():
    """Debug indexing behavior."""
    print("\n🔍 DEBUG: Index Behavior Test")
    print("=" * 60)
    
    # Create test files
    Path(".env").write_text("API_KEY=secret123")
    Path("private.key").write_text("-----BEGIN PRIVATE KEY-----")
    Path("app.py").write_text("print('hello')")
    
    print("\n📁 Created test files:")
    for f in Path(".").iterdir():
        if f.is_file():
            print(f"   - {f.name}")
    
    # Initialize
    sqlite_store = SQLiteStore("debug_index.db")
    dispatcher = EnhancedDispatcher(
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False
    )
    
    # Index with debug
    print("\n📊 Starting indexing...")
    stats = dispatcher.index_directory(Path("."), recursive=False)
    
    print(f"\nStats: {stats}")
    
    # Check database directly
    conn = sqlite3.connect("debug_index.db")
    cursor = conn.cursor()
    
    # Check schema
    cursor.execute("PRAGMA table_info(files)")
    columns = cursor.fetchall()
    print(f"\n📋 Table 'files' columns: {[col[1] for col in columns]}")
    
    # Get all files
    cursor.execute("SELECT * FROM files")
    files = cursor.fetchall()
    
    print(f"\n📂 Files in database ({len(files)} total):")
    for row in files:
        print(f"   {row}")
    
    # Check if plugins support these files
    print("\n🔌 Plugin support check:")
    for f in [Path(".env"), Path("private.key"), Path("app.py")]:
        supported = False
        plugin_name = None
        
        # Check each plugin
        for plugin in dispatcher._plugins:
            if plugin.supports(f):
                supported = True
                plugin_name = plugin.lang
                break
        
        print(f"   {f.name}: {'✅ YES' if supported else '❌ NO'} {f'({plugin_name})' if supported else ''}")
    
    conn.close()
    
    # Cleanup
    os.chdir("/app")
    shutil.rmtree(test_dir)
    
    print("\n✅ Debug completed!")


if __name__ == "__main__":
    main()