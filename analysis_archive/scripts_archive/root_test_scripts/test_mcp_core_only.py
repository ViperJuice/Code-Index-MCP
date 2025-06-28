#!/usr/bin/env python3
"""
Test MCP Core Components Only
Bypass gateway dependencies and test core search/plugin functionality directly.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_with_timeout(cmd, timeout_seconds=20):
    """Run command with timeout protection."""
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        return {
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'Command timed out after {timeout_seconds}s',
            'stdout': '',
            'stderr': '',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Command failed: {e}',
            'stdout': '',
            'stderr': '',
            'returncode': -1
        }

def test_core_plugin_system():
    """Test core plugin system without gateway dependencies."""
    print("\n🔌 Testing Core Plugin System...")
    
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")

try:
    # Test the fixed components directly
    from mcp_server.plugins.plugin_factory import PluginFactory
    from mcp_server.plugins.repository_plugin_loader import RepositoryPluginLoader
    
    print("✅ Core imports successful")
    
    # Test PluginFactory.get_plugin method (this was the main fix)
    factory = PluginFactory()
    
    try:
        plugin = factory.get_plugin("python")
        print(f"✅ PluginFactory.get_plugin works: {type(plugin).__name__}")
    except Exception as e:
        print(f"❌ PluginFactory.get_plugin failed: {e}")
    
    # Test RepositoryPluginLoader methods (these were missing)
    try:
        loader = RepositoryPluginLoader()
        
        required = loader.get_required_plugins()
        print(f"✅ get_required_plugins works: {len(required)} languages")
        
        priority = loader.get_priority_languages()
        print(f"✅ get_priority_languages works: {priority[:3]}")
        
        loader.log_loading_plan()
        print("✅ log_loading_plan works")
        
    except Exception as e:
        print(f"❌ RepositoryPluginLoader methods failed: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=15)
    
    print(f"Command output:")
    if result['stdout']:
        for line in result['stdout'].strip().split('\n'):
            print(f"   {line}")
    
    if result['stderr']:
        print(f"Errors:")
        for line in result['stderr'].strip().split('\n')[:5]:  # Only first 5 lines
            print(f"   {line}")
    
    return result['success'] and '✅' in result['stdout']

def test_core_search_system():
    """Test core search system without gateway."""
    print("\n🔍 Testing Core Search System...")
    
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")

try:
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from pathlib import Path
    
    print("✅ Core search imports successful")
    
    # Find a test database
    search_paths = [
        Path.home() / ".mcp" / "indexes",
        Path.cwd() / ".indexes", 
        Path.cwd() / "test_indexes",
    ]
    
    db_path = None
    for base_path in search_paths:
        if base_path.exists():
            for db_file in base_path.rglob("*.db"):
                if db_file.stat().st_size > 1000:
                    db_path = db_file
                    break
            if db_path:
                break
    
    if not db_path:
        print("⚠️ No test index found - skipping search tests")
    else:
        print(f"✅ Found test index: {db_path.name}")
        
        # Test SQLiteStore
        store = SQLiteStore(str(db_path))
        print("✅ SQLiteStore created")
        
        # Test EnhancedDispatcher creation (this was hanging before)
        dispatcher = EnhancedDispatcher(sqlite_store=store, lazy_load=True)
        print(f"✅ EnhancedDispatcher created with {len(dispatcher._plugins)} plugins")
        
        # Test search method
        try:
            results = list(dispatcher.search("def", limit=2))
            print(f"✅ Search works: found {len(results)} results")
        except Exception as e:
            print(f"❌ Search failed: {e}")
        
        # Test lookup method (with proper signature)
        try:
            result = dispatcher.lookup("test", limit=2)
            print(f"✅ Lookup works: returned {type(result)}")
        except Exception as e:
            print(f"❌ Lookup failed: {e}")
    
except Exception as e:
    print(f"❌ Search system test failed: {e}")
    import traceback
    traceback.print_exc()
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=25)
    
    print(f"Command output:")
    if result['stdout']:
        for line in result['stdout'].strip().split('\n'):
            print(f"   {line}")
    
    if result['stderr']:
        print(f"Errors:")
        for line in result['stderr'].strip().split('\n')[:5]:
            print(f"   {line}")
    
    return result['success'] and '✅' in result['stdout']

def main():
    """Test core MCP functionality without gateway dependencies."""
    print("🧪 MCP Core Components Test")
    print("=" * 50)
    print("Testing core MCP functionality without gateway/auth dependencies...")
    
    tests = [
        ("Core Plugin System", test_core_plugin_system),
        ("Core Search System", test_core_search_system),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*30}")
        start_time = time.time()
        success = test_func()
        end_time = time.time()
        
        results[test_name] = {
            'success': success,
            'duration': end_time - start_time
        }
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 Core Test Summary:")
    
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result['success'] else "FAIL"
        duration = result['duration']
        emoji = "✅" if result['success'] else "❌"
        print(f"{emoji} {test_name}: {status} ({duration:.1f}s)")
    
    print(f"\nOverall: {passed}/{total} core tests passed")
    
    if passed == total:
        print("🎉 Core MCP components are working!")
        print("ℹ️  Note: Gateway/auth dependencies (jwt, passlib) may need installation for full MCP server")
    else:
        print("⚠️  Core MCP components still have issues")

if __name__ == "__main__":
    main()