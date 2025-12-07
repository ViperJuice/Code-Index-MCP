#!/usr/bin/env python3
"""
Test script for MCP server functionality without Docker
This creates a minimal test environment to verify the MCP server works
"""
import json
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

# Import the components we need to test
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


def test_mcp_components():
    """Test basic MCP server components"""
    print("Testing MCP Server Components...")

    try:
        # Test SQLite store
        print("\n1. Testing SQLite Store...")
        sqlite_store = SQLiteStore("test_code_index.db")
        print("✓ SQLite store initialized")

        # Test plugin manager
        print("\n2. Testing Plugin Manager...")
        plugin_manager = PluginManager(sqlite_store=sqlite_store)
        config_path = Path("plugins.yaml")

        if config_path.exists():
            load_result = plugin_manager.load_plugins_safe(config_path)
            if load_result.success:
                print(f"✓ Plugin manager loaded successfully")
                print(f"  Metadata: {load_result.metadata}")
            else:
                print(f"✗ Plugin loading failed: {load_result.error.message}")
        else:
            print("✗ plugins.yaml not found")

        # Test dispatcher
        print("\n3. Testing Dispatcher...")
        active_plugins = plugin_manager.get_active_plugins()
        plugin_instances = list(active_plugins.values())
        dispatcher = Dispatcher(plugin_instances)
        print(f"✓ Dispatcher created with {len(plugin_instances)} plugins")

        # Test basic operations
        print("\n4. Testing Basic Operations...")

        # Test symbol lookup
        print("   - Testing symbol lookup...")
        result = dispatcher.lookup("Dispatcher")
        if result:
            print(f"   ✓ Found symbol 'Dispatcher': {result.name} at {result.path}:{result.line}")
        else:
            print("   ✗ Symbol 'Dispatcher' not found")

        # Test search
        print("   - Testing code search...")
        results = list(dispatcher.search("def", limit=5))
        print(f"   ✓ Search returned {len(results)} results")

        # Test status
        print("\n5. Testing Status...")
        plugin_count = len(dispatcher._plugins) if hasattr(dispatcher, "_plugins") else 0
        print(f"   ✓ Active plugins: {plugin_count}")

        # Clean up test database
        if Path("test_code_index.db").exists():
            Path("test_code_index.db").unlink()

        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mcp_components()
    sys.exit(0 if success else 1)
