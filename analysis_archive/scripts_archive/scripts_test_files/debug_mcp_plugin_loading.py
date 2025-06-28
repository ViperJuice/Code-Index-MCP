#!/usr/bin/env python3
"""
Debug why plugins aren't loading in the MCP server.
"""

import sys
import logging
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add MCP server to path
sys.path.insert(0, "/workspaces/Code-Index-MCP")

from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


def debug_plugin_loading():
    """Debug the plugin loading process."""
    
    print("Debugging Plugin Loading")
    print("=" * 80)
    
    # Check for index
    index_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "current.db"
    print(f"\n1. Index path: {index_path}")
    print(f"   Exists: {index_path.exists()}")
    
    if index_path.exists():
        # Initialize SQLiteStore
        print("\n2. Initializing SQLiteStore...")
        try:
            sqlite_store = SQLiteStore(str(index_path))
            print("   ✓ SQLiteStore initialized")
            
            # Check what tables exist
            with sqlite_store._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                print(f"   Tables in database: {tables}")
        except Exception as e:
            print(f"   ✗ Error initializing SQLiteStore: {e}")
            return
    else:
        print("   Index not found!")
        return
    
    # Initialize PluginManager
    print("\n3. Initializing PluginManager...")
    try:
        plugin_manager = PluginManager(sqlite_store=sqlite_store)
        print("   ✓ PluginManager initialized")
    except Exception as e:
        print(f"   ✗ Error initializing PluginManager: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to load plugins
    print("\n4. Loading plugins...")
    config_path = Path("plugins.yaml")
    print(f"   Config path: {config_path} (exists: {config_path.exists()})")
    
    try:
        result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
        print(f"   Load result success: {result.success}")
        
        if result.error:
            print(f"   Error: {result.error.message}")
            print(f"   Type: {result.error.error_type}")
            if result.error.details:
                print(f"   Details: {result.error.details}")
        
        if result.metadata:
            print(f"   Metadata: {result.metadata}")
            
    except Exception as e:
        print(f"   ✗ Error loading plugins: {e}")
        import traceback
        traceback.print_exc()
    
    # Check active plugins
    print("\n5. Active plugins:")
    try:
        active_plugins = plugin_manager.get_active_plugins()
        print(f"   Count: {len(active_plugins)}")
        for name, plugin in active_plugins.items():
            print(f"   - {name}: {plugin}")
    except Exception as e:
        print(f"   ✗ Error getting active plugins: {e}")
    
    # Check plugin registry
    print("\n6. Plugin Registry:")
    try:
        if hasattr(plugin_manager, 'registry'):
            registry = plugin_manager.registry
            print(f"   Registry type: {type(registry)}")
            if hasattr(registry, 'plugins'):
                print(f"   Registered plugins: {len(registry.plugins)}")
                for plugin_id, plugin_info in list(registry.plugins.items())[:5]:
                    print(f"   - {plugin_id}: {plugin_info}")
    except Exception as e:
        print(f"   ✗ Error checking registry: {e}")
    
    # Try to import a specific plugin directly
    print("\n7. Direct plugin import test:")
    try:
        from mcp_server.plugins.python_plugin import PythonPlugin
        print("   ✓ Successfully imported PythonPlugin")
        
        # Try to instantiate it
        plugin = PythonPlugin(sqlite_store=sqlite_store)
        print(f"   ✓ Instantiated PythonPlugin: {plugin}")
        
    except Exception as e:
        print(f"   ✗ Error importing PythonPlugin: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_plugin_loading()