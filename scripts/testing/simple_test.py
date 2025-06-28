#!/usr/bin/env python3
"""
Simple test script to validate core functionality without complex conftest.
"""

import tempfile
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_sqlite_store():
    """Test basic SQLiteStore functionality."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Test basic operations
        store = SQLiteStore(db_path)
        
        # Test repository creation
        repo_id = store.create_repository("/test/repo", "test-repo", {"type": "git"})
        assert repo_id is not None
        print(f"✅ Repository created with ID: {repo_id}")
        
        # Test file storage
        file_id = store.store_file(
            repo_id, "/test/repo/main.py", "main.py",
            language="python", size=1024, hash="abc123"
        )
        assert file_id is not None
        print(f"✅ File stored with ID: {file_id}")
        
        # Test symbol storage
        symbol_id = store.store_symbol(
            file_id, "main", "function",
            line_start=1, line_end=10,
            signature="def main() -> None",
            documentation="Main entry point"
        )
        assert symbol_id is not None
        print(f"✅ Symbol stored with ID: {symbol_id}")
        
        # Test search
        results = store.search_symbols_fuzzy("main")
        assert len(results) > 0
        print(f"✅ Search found {len(results)} results")
        
        print("✅ SQLiteStore basic functionality test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ SQLiteStore test FAILED: {e}")
        return False
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)

def test_python_plugin():
    """Test basic Python plugin functionality."""
    try:
        from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
        import tempfile
        
        # Create a temporary Python file in project directory
        test_file = Path("test_sample.py")
        test_file.write_text('''
def hello_world():
    """Say hello to the world."""
    print("Hello, World!")

class Calculator:
    """A simple calculator class."""
    
    def add(self, a: int, b: int) -> int:
        return a + b
''')
        
        try:
            # Create plugin instance 
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_tmp:
                db_path = db_tmp.name
            
            from mcp_server.storage.sqlite_store import SQLiteStore
            store = SQLiteStore(db_path)
            plugin = PythonPlugin(sqlite_store=store)
            
            # Test file support
            assert plugin.supports(test_file)
            print("✅ Python plugin supports .py files")
            
            # Test indexing
            content = test_file.read_text()
            result = plugin.indexFile(str(test_file), content)
            assert result.success
            assert len(result.value["symbols"]) > 0
            print(f"✅ Python plugin indexed {len(result.value['symbols'])} symbols")
            
            print("✅ Python plugin basic functionality test PASSED")
            return True
            
        finally:
            test_file.unlink(missing_ok=True)
            Path(db_path).unlink(missing_ok=True)
            
    except Exception as e:
        print(f"❌ Python plugin test FAILED: {e}")
        return False

def main():
    """Run simple validation tests."""
    print("🧪 Running simple validation tests...")
    
    tests = [
        ("SQLiteStore", test_sqlite_store),
        ("Python Plugin", test_python_plugin),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed")
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All basic tests PASSED! Core functionality is working.")
        return 0
    else:
        print("⚠️  Some tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())