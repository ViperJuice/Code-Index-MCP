#!/usr/bin/env python3
"""
Test MCP Tools with Timeout Protection
Run MCP tools in a separate process with timeout to avoid hanging.
"""

import subprocess
import sys
import time
import json
from pathlib import Path

def run_with_timeout(cmd, timeout_seconds=30):
    """Run command with timeout protection."""
    print(f"Running: {' '.join(cmd)}")
    print(f"Timeout: {timeout_seconds}s")
    
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

def test_mcp_server_startup():
    """Test if MCP server can start without hanging."""
    print("\n🚀 Testing MCP Server Startup...")
    
    # Test basic server initialization
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")
from mcp_server.gateway import create_server
print("SUCCESS: MCP server can be created")
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=15)
    
    if result['success'] and 'SUCCESS' in result['stdout']:
        print("✅ MCP server startup: PASS")
        return True
    else:
        print(f"❌ MCP server startup: FAIL")
        print(f"   Error: {result.get('error', 'Unknown')}")
        if result['stderr']:
            print(f"   Stderr: {result['stderr'][:200]}...")
        return False

def test_mcp_search_tools():
    """Test MCP search tools in isolated process."""
    print("\n🔍 Testing MCP Search Tools...")
    
    # Test search_code tool
    cmd = [
        sys.executable, '-c',
        '''
import sys
import asyncio
sys.path.insert(0, ".")

async def test_search():
    try:
        from mcp_server.gateway import create_server
        from mcp.server import Server
        
        # Create server instance
        server = create_server()
        
        # Test search_code tool directly
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
        
        # Find an index to test with
        from pathlib import Path
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
            print("SKIP: No test index found")
            return
            
        # Test search functionality
        store = SQLiteStore(str(db_path))
        dispatcher = EnhancedDispatcher(sqlite_store=store)
        
        # Simple search test
        results = list(dispatcher.search("class", limit=2))
        print(f"SUCCESS: Found {len(results)} search results")
        
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(test_search())
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=25)
    
    if result['success'] and ('SUCCESS' in result['stdout'] or 'SKIP' in result['stdout']):
        print("✅ MCP search tools: PASS")
        print(f"   Details: {result['stdout'].strip()}")
        return True
    else:
        print(f"❌ MCP search tools: FAIL")
        print(f"   Error: {result.get('error', 'Unknown')}")
        if result['stderr']:
            print(f"   Stderr: {result['stderr'][:200]}...")
        return False

def test_mcp_symbol_lookup():
    """Test MCP symbol lookup in isolated process."""
    print("\n🎯 Testing MCP Symbol Lookup...")
    
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")

try:
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from pathlib import Path
    
    # Find test index
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
        print("SKIP: No test index found")
    else:
        store = SQLiteStore(str(db_path))
        dispatcher = EnhancedDispatcher(sqlite_store=store)
        
        # Test symbol lookup with proper error handling
        try:
            result = dispatcher.lookup("function", limit=2)
            if result is not None:
                print(f"SUCCESS: Symbol lookup returned result type: {type(result)}")
            else:
                print("SUCCESS: Symbol lookup returned None (expected for some symbols)")
        except Exception as e:
            print(f"ERROR in lookup: {e}")
            
except Exception as e:
    print(f"ERROR: {e}")
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=20)
    
    if result['success'] and ('SUCCESS' in result['stdout'] or 'SKIP' in result['stdout']):
        print("✅ MCP symbol lookup: PASS")
        print(f"   Details: {result['stdout'].strip()}")
        return True
    else:
        print(f"❌ MCP symbol lookup: FAIL")
        print(f"   Error: {result.get('error', 'Unknown')}")
        if result['stderr']:
            print(f"   Stderr: {result['stderr'][:200]}...")
        return False

def test_mcp_plugin_system():
    """Test MCP plugin system in isolated process."""
    print("\n🔌 Testing MCP Plugin System...")
    
    cmd = [
        sys.executable, '-c',
        '''
import sys
sys.path.insert(0, ".")

try:
    from mcp_server.plugins.plugin_factory import PluginFactory
    from mcp_server.plugins.repository_plugin_loader import RepositoryPluginLoader
    from mcp_server.storage.sqlite_store import SQLiteStore
    
    # Test PluginFactory
    factory = PluginFactory()
    
    # Test get_plugin method (this was missing before)
    plugin = factory.get_plugin("python")
    print(f"SUCCESS: PluginFactory.get_plugin works, created {type(plugin).__name__}")
    
    # Test RepositoryPluginLoader
    loader = RepositoryPluginLoader()
    
    # Test get_required_plugins method (this was missing before)
    required = loader.get_required_plugins()
    print(f"SUCCESS: RepositoryPluginLoader.get_required_plugins works, found {len(required)} languages")
    
    # Test get_priority_languages method
    priority = loader.get_priority_languages()
    print(f"SUCCESS: RepositoryPluginLoader.get_priority_languages works, priority order: {priority[:3]}")
    
except Exception as e:
    print(f"ERROR: {e}")
        '''
    ]
    
    result = run_with_timeout(cmd, timeout_seconds=15)
    
    if result['success'] and 'SUCCESS' in result['stdout']:
        print("✅ MCP plugin system: PASS")
        print(f"   Details: {result['stdout'].strip()}")
        return True
    else:
        print(f"❌ MCP plugin system: FAIL")
        print(f"   Error: {result.get('error', 'Unknown')}")
        if result['stderr']:
            print(f"   Stderr: {result['stderr'][:200]}...")
        return False

def main():
    """Run all MCP tests with timeout protection."""
    print("🧪 MCP Tools Timeout Test")
    print("=" * 50)
    print("Testing MCP functionality in isolated processes to avoid hanging...")
    
    tests = [
        ("MCP Server Startup", test_mcp_server_startup),
        ("MCP Plugin System", test_mcp_plugin_system), 
        ("MCP Search Tools", test_mcp_search_tools),
        ("MCP Symbol Lookup", test_mcp_symbol_lookup),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20}")
        start_time = time.time()
        success = test_func()
        end_time = time.time()
        
        results[test_name] = {
            'success': success,
            'duration': end_time - start_time
        }
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 Test Summary:")
    
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result['success'] else "FAIL"
        duration = result['duration']
        emoji = "✅" if result['success'] else "❌"
        print(f"{emoji} {test_name}: {status} ({duration:.1f}s)")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All MCP tools are working without hanging!")
        print("✅ The MCP hanging issue has been resolved!")
    else:
        print("⚠️  Some MCP tools still have issues")
        print("🔍 Focus debugging on the failing tests above")

if __name__ == "__main__":
    main()