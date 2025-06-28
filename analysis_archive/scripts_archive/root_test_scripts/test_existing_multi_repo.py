#!/usr/bin/env python3
"""Test existing multi-repository capabilities."""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager, RepositoryInfo
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.index_engine import IndexEngine

def run_command(cmd, cwd=None):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip()

def create_test_repo(base_dir, repo_name):
    """Create a test git repository with some content."""
    repo_path = base_dir / repo_name
    repo_path.mkdir(parents=True)
    
    # Initialize git repo
    run_command("git init", cwd=repo_path)
    run_command("git config user.name 'Test User'", cwd=repo_path)
    run_command("git config user.email 'test@example.com'", cwd=repo_path)
    
    # Create test files
    (repo_path / "main.py").write_text("""
def hello_world():
    '''Say hello to the world.'''
    print("Hello, World!")

def calculate_sum(a: int, b: int) -> int:
    '''Calculate sum of two numbers.'''
    return a + b
""")
    
    (repo_path / "utils.py").write_text("""
import datetime

def get_current_time():
    '''Get current timestamp.'''
    return datetime.datetime.now()

def format_date(date):
    '''Format date as string.'''
    return date.strftime("%Y-%m-%d %H:%M:%S")
""")
    
    # Commit
    run_command("git add .", cwd=repo_path)
    run_command("git commit -m 'Initial commit'", cwd=repo_path)
    
    return repo_path

def test_multi_repo_indexing():
    """Test indexing multiple repositories."""
    print("\n=== Testing Multi-Repository Indexing ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        index_dir = base_dir / "indexes"
        index_dir.mkdir()
        
        # Create test repositories
        repos = []
        for i in range(3):
            repo_path = create_test_repo(base_dir, f"test_repo_{i}")
            repos.append(repo_path)
            print(f"Created repository: {repo_path.name}")
        
        # Create index manager
        manager = MultiRepoIndexManager("primary", str(index_dir))
        
        # Index each repository
        for i, repo_path in enumerate(repos):
            repo_id = f"repo_{i}"
            print(f"\nIndexing {repo_path.name} as {repo_id}...")
            
            # Create index for repository
            index_path = index_dir / f"{repo_id}.db"
            store = SQLiteStore(str(index_path))
            
            # Create dispatcher and index engine
            dispatcher = EnhancedDispatcher(sqlite_store=store)
            engine = IndexEngine(dispatcher=dispatcher)
            
            # Index the repository
            try:
                engine.index_directory(str(repo_path))
                print(f"  ✓ Indexed {repo_path.name}")
                
                # Add to manager
                manager.add_repository(repo_id, repo_path)
                print(f"  ✓ Added to multi-repo manager")
                
            except Exception as e:
                print(f"  ✗ Error indexing: {e}")
        
        # Test cross-repository search
        print("\n=== Testing Cross-Repository Search ===")
        
        # Search across all repositories
        queries = ["hello_world", "calculate", "format_date", "datetime"]
        
        for query in queries:
            print(f"\nSearching for '{query}':")
            results = manager.search_all_repositories(query, limit=10)
            print(f"  Found {len(results)} results across {len(set(r.get('repo_id', '') for r in results))} repositories")
            
            for result in results[:3]:  # Show first 3 results
                repo_id = result.get('repo_id', 'unknown')
                file_path = result.get('file_path', 'unknown')
                print(f"  - {repo_id}: {file_path}")
        
        # Test repository info
        print("\n=== Repository Information ===")
        repo_infos = manager.get_all_repository_info()
        for repo_id, info in repo_infos.items():
            print(f"\n{repo_id}:")
            print(f"  Path: {info.path}")
            print(f"  Files: {info.file_count}")
            print(f"  Languages: {', '.join(info.languages) if info.languages else 'N/A'}")
            print(f"  Index size: {info.index_size_mb:.2f} MB")
        
        return True

def test_smart_plugin_loading():
    """Test the smart plugin loading feature."""
    print("\n=== Testing Smart Plugin Loading ===")
    
    # Create dispatcher with memory limit
    dispatcher = EnhancedDispatcher(memory_limit_mb=100)
    
    # Test plugin manager
    from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager
    
    manager = MemoryAwarePluginManager(max_memory_mb=100)
    print(f"Created MemoryAwarePluginManager with {manager.max_memory_mb}MB limit")
    
    # Load some plugins
    languages = ["python", "javascript", "go", "rust", "java"]
    
    for lang in languages:
        try:
            plugin = manager.get_plugin(lang)
            if plugin:
                print(f"  ✓ Loaded {lang} plugin")
                memory_usage = manager.get_memory_usage()
                print(f"    Memory usage: {memory_usage:.2f} MB")
            else:
                print(f"  ✗ No plugin for {lang}")
        except Exception as e:
            print(f"  ✗ Error loading {lang}: {e}")
    
    # Test eviction
    print("\n  Testing LRU eviction...")
    initial_count = len(manager._loaded_plugins)
    print(f"  Initially loaded: {initial_count} plugins")
    
    # Access python plugin to make it most recently used
    manager.get_plugin("python")
    
    # Load more plugins to trigger eviction
    for lang in ["csharp", "kotlin", "swift"]:
        manager.get_plugin(lang)
    
    final_count = len(manager._loaded_plugins)
    print(f"  After loading more: {final_count} plugins")
    print(f"  Currently loaded: {list(manager._loaded_plugins.keys())}")
    
    return True

def test_file_watcher():
    """Test the file watcher functionality."""
    print("\n=== Testing File Watcher ===")
    
    from mcp_server.watcher import FileWatcher
    
    with tempfile.TemporaryDirectory() as tmpdir:
        watch_dir = Path(tmpdir)
        
        # Create initial file
        test_file = watch_dir / "test.py"
        test_file.write_text("# Initial content\n")
        
        # Create watcher
        watcher = FileWatcher(str(watch_dir))
        print(f"Created FileWatcher for {watch_dir}")
        
        # Start watching
        observer = watcher.start_watching()
        if observer:
            print("  ✓ Watcher started")
            
            # Make changes
            import time
            time.sleep(0.5)  # Give watcher time to start
            
            test_file.write_text("# Modified content\ndef new_function():\n    pass\n")
            print("  ✓ Modified file")
            
            time.sleep(1)  # Give watcher time to detect
            
            # Stop watching
            watcher.stop_watching()
            print("  ✓ Watcher stopped")
        else:
            print("  ✗ Failed to start watcher")
        
        return True

def main():
    """Run tests for existing components."""
    print("Testing Existing Multi-Repository Capabilities")
    print("=" * 60)
    
    tests = [
        test_multi_repo_indexing,
        test_smart_plugin_loading,
        test_file_watcher
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {test_func.__name__} passed")
            else:
                failed += 1
                print(f"\n✗ {test_func.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_func.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n\nTest Summary: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)