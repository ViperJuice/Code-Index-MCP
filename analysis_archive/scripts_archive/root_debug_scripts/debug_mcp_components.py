#!/usr/bin/env python3
"""
Debug MCP Components Directly
Test MCP functionality without using MCP tools to avoid circular dependencies.
"""

import sys
import time
import signal
import functools
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

def timeout(seconds):
    """Decorator to add timeout to functions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function '{func.__name__}' timed out after {seconds} seconds")
            
            # Set up timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Cancel timeout
                signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
                return result
            except TimeoutError as e:
                signal.alarm(0)  # Cancel timeout
                signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
                return f"TIMEOUT: {e}"
            except Exception as e:
                signal.alarm(0)  # Cancel timeout
                signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
                return f"ERROR: {e}"
        return wrapper
    return decorator

def print_status(step, status, details=""):
    """Print status with consistent formatting."""
    status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_emoji} {step}: {status}")
    if details:
        print(f"   Details: {details}")

def find_existing_index():
    """Find an existing SQLite index to test with."""
    # Common index locations
    search_paths = [
        Path.home() / ".mcp" / "indexes",
        Path.cwd() / ".indexes", 
        Path.cwd() / "test_indexes",
        Path.cwd(),
    ]
    
    for base_path in search_paths:
        if base_path.exists():
            for db_file in base_path.rglob("*.db"):
                if db_file.stat().st_size > 1000:  # At least 1KB
                    return db_file
    return None

@timeout(10)
def test_imports():
    """Test that all required modules can be imported."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
    from mcp_server.plugins.generic_treesitter_plugin import GenericTreeSitterPlugin
    return "SUCCESS"

@timeout(10) 
def test_sqlite_store(db_path):
    """Test SQLiteStore initialization and basic operations."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    
    store = SQLiteStore(str(db_path))
    
    # Test connection
    with store._get_connection() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
    
    return f"SUCCESS - Found tables: {tables}"

@timeout(10)
def test_fuzzy_indexer_schema_detection(db_path):
    """Test FuzzyIndexer schema detection."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
    
    store = SQLiteStore(str(db_path))
    indexer = FuzzyIndexer(sqlite_store=store)
    
    return f"SUCCESS - Detected schema: {indexer._schema_type}"

@timeout(15)
def test_dispatcher_initialization(db_path):
    """Test EnhancedDispatcher initialization."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    
    store = SQLiteStore(str(db_path))
    dispatcher = EnhancedDispatcher(sqlite_store=store)
    
    return f"SUCCESS - Dispatcher created with {len(dispatcher._plugins)} initial plugins"

@timeout(20)
def test_plugin_loading(db_path):
    """Test loading plugins."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    
    store = SQLiteStore(str(db_path))
    dispatcher = EnhancedDispatcher(sqlite_store=store, lazy_load=True, use_plugin_factory=True)
    
    # Try to load all plugins
    dispatcher._load_all_plugins()
    
    return f"SUCCESS - Loaded {len(dispatcher._plugins)} plugins"

@timeout(15)
def test_search_functionality(db_path):
    """Test search functionality."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    
    store = SQLiteStore(str(db_path))
    dispatcher = EnhancedDispatcher(sqlite_store=store)
    
    # Test search
    results = list(dispatcher.search("def", limit=3))
    
    return f"SUCCESS - Found {len(results)} search results"

@timeout(15)
def test_symbol_lookup(db_path):
    """Test symbol lookup functionality."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    
    store = SQLiteStore(str(db_path))
    dispatcher = EnhancedDispatcher(sqlite_store=store)
    
    # Test symbol lookup
    symbols = list(dispatcher.lookup("function", limit=3))
    
    return f"SUCCESS - Found {len(symbols)} symbol results"

def main():
    """Main test function."""
    print("🔍 MCP Component Debug Test")
    print("=" * 50)
    
    # Step 1: Test imports
    print("\n1. Testing Imports...")
    result = test_imports()
    print_status("Import test", "PASS" if result == "SUCCESS" else "FAIL", result)
    
    if "ERROR" in result or "TIMEOUT" in result:
        print("❌ Cannot proceed - import failures")
        return
    
    # Step 2: Find an index to test with
    print("\n2. Finding Test Index...")
    db_path = find_existing_index()
    if not db_path:
        print_status("Index discovery", "FAIL", "No existing SQLite index found")
        return
    
    print_status("Index discovery", "PASS", f"Using: {db_path}")
    
    # Step 3: Test SQLite store
    print("\n3. Testing SQLite Store...")
    result = test_sqlite_store(db_path)
    print_status("SQLite store", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    # Step 4: Test FuzzyIndexer schema detection
    print("\n4. Testing FuzzyIndexer Schema Detection...")
    result = test_fuzzy_indexer_schema_detection(db_path)
    print_status("Schema detection", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    # Step 5: Test dispatcher initialization
    print("\n5. Testing Dispatcher Initialization...")
    result = test_dispatcher_initialization(db_path)
    print_status("Dispatcher init", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    # Step 6: Test plugin loading (this is where we expect issues)
    print("\n6. Testing Plugin Loading...")
    result = test_plugin_loading(db_path)
    print_status("Plugin loading", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    # Step 7: Test search functionality
    print("\n7. Testing Search Functionality...")
    result = test_search_functionality(db_path)
    print_status("Search test", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    # Step 8: Test symbol lookup
    print("\n8. Testing Symbol Lookup...")
    result = test_symbol_lookup(db_path)
    print_status("Symbol lookup", "PASS" if "SUCCESS" in result else "FAIL", result)
    
    print("\n" + "=" * 50)
    print("🏁 Debug test completed!")
    print("\nNext steps:")
    print("- If any step failed/timed out, that's where the MCP hanging issue is")
    print("- Focus debugging efforts on the first failing component")
    print("- Once all steps pass, MCP tools should work without hanging")

if __name__ == "__main__":
    main()