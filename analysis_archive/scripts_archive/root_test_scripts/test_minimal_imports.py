#!/usr/bin/env python3
"""
Test minimal imports to find hanging point.
"""

import subprocess
import sys
from pathlib import Path

def test_import(import_statement, description):
    """Test a single import statement."""
    print(f"\n🔍 Testing: {description}")
    
    cmd = [
        sys.executable, '-c', 
        f'import sys; sys.path.insert(0, "."); {import_statement}; print("SUCCESS")'
    ]
    
    try:
        result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print(f"✅ {description}: PASS")
            return True
        else:
            print(f"❌ {description}: FAIL")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ {description}: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def main():
    """Test imports progressively to find hanging point."""
    print("🧪 Minimal Import Test")
    print("=" * 40)
    
    tests = [
        ("from mcp_server.storage.sqlite_store import SQLiteStore", "SQLiteStore"),
        ("from mcp_server.plugins.plugin_factory import PluginFactory", "PluginFactory"),
        ("from mcp_server.plugins.repository_plugin_loader import RepositoryPluginLoader", "RepositoryPluginLoader"),
        ("from mcp_server.utils.fuzzy_indexer import FuzzyIndexer", "FuzzyIndexer"),
        ("from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher", "EnhancedDispatcher"),
        ("factory = PluginFactory(); plugin = factory.get_plugin('python')", "PluginFactory.get_plugin"),
        ("loader = RepositoryPluginLoader(); required = loader.get_required_plugins()", "RepositoryPluginLoader methods"),
    ]
    
    passed = 0
    for import_stmt, desc in tests:
        if test_import(import_stmt, desc):
            passed += 1
        else:
            print(f"\n❌ Hanging/failing at: {desc}")
            print(f"   Statement: {import_stmt}")
            break
    
    print(f"\n🏁 Result: {passed}/{len(tests)} imports passed")
    
    if passed == len(tests):
        print("✅ All basic imports work - issue might be in specific method calls")
    else:
        print("⚠️  Import hanging detected - this is where to focus debugging")

if __name__ == "__main__":
    main()