#!/usr/bin/env python3
"""Debug plugin count issue."""

import os
import sys
sys.path.insert(0, '/app')

# Set environment
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"

from mcp_server.dispatcher import Dispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from pathlib import Path

# Initialize components
print("Initializing components...")
store = SQLiteStore(":memory:")
plugin_manager = PluginManager(sqlite_store=store)

# Load plugins
print("\nLoading plugins...")
config_path = Path("plugins.yaml")
load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
print(f"Plugin loading result: {load_result.success}")

# Get active plugins
active_plugins = plugin_manager.get_active_plugins()
plugin_instances = list(active_plugins.values())

print(f"\nLoaded {len(plugin_instances)} plugins:")
for plugin in plugin_instances:
    print(f"  - {plugin.__class__.__name__}")
    print(f"    lang attribute: {getattr(plugin, 'lang', 'NOT FOUND')}")
    print(f"    language attribute: {getattr(plugin, 'language', 'NOT FOUND')}")
    
    # Check indexer
    if hasattr(plugin, '_indexer'):
        indexer = plugin._indexer
        if hasattr(indexer, 'index'):
            print(f"    Files in index: {len(indexer.index)}")
        else:
            print(f"    No 'index' attribute in indexer")
    
    # Try get_indexed_count
    if hasattr(plugin, 'get_indexed_count'):
        count = plugin.get_indexed_count()
        print(f"    get_indexed_count(): {count}")
    print()

# Create dispatcher
print("\nCreating dispatcher...")
dispatcher = Dispatcher(plugin_instances)

# Test indexing a Python file
print("\nTesting Python file indexing...")
test_file = Path("/app/test_files/test.py")
if test_file.exists():
    dispatcher.index_file(test_file)
    
    # Check counts again
    print("\nAfter indexing test file:")
    for plugin in dispatcher._plugins:
        if hasattr(plugin, 'lang') and plugin.lang == 'python':
            print(f"  Python plugin count: {plugin.get_indexed_count()}")
            if hasattr(plugin, '_indexer') and hasattr(plugin._indexer, 'index'):
                print(f"  Files in index: {list(plugin._indexer.index.keys())}")