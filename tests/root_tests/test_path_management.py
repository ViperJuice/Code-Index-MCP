#!/usr/bin/env python3
"""Test script for path management implementation."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.watcher import FileWatcher


def test_path_resolver():
    """Test PathResolver functionality."""
    print("\n=== Testing PathResolver ===")
    
    resolver = PathResolver()
    print(f"Repository root: {resolver.repository_root}")
    
    # Test path normalization
    test_file = Path(__file__).resolve()
    relative_path = resolver.normalize_path(test_file)
    print(f"Absolute: {test_file}")
    print(f"Relative: {relative_path}")
    
    # Test path resolution
    resolved = resolver.resolve_path(relative_path)
    print(f"Resolved back: {resolved}")
    assert resolved == test_file, "Path resolution failed"
    
    # Test content hashing
    content_hash = resolver.compute_content_hash(test_file)
    print(f"Content hash: {content_hash[:16]}...")
    
    print("✓ PathResolver tests passed")


def test_sqlite_store():
    """Test SQLiteStore with path management."""
    print("\n=== Testing SQLiteStore ===")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize store
        store = SQLiteStore(db_path)
        
        # Create repository
        repo_id = store.create_repository("/test/repo", "Test Repository")
        print(f"Created repository: {repo_id}")
        
        # Store a file using absolute path
        test_file = Path(__file__).resolve()
        file_id = store.store_file(repo_id, test_file, language="python", size=1000)
        print(f"Stored file: {file_id}")
        
        # Get file by relative path
        file_info = store.get_file(test_file, repo_id)
        assert file_info is not None, "Failed to retrieve file"
        print(f"Retrieved file: relative_path={file_info['relative_path']}")
        
        # Test content hash
        assert file_info['content_hash'] is not None, "Content hash not computed"
        print(f"Content hash: {file_info['content_hash'][:16]}...")
        
        # Test file operations
        store.mark_file_deleted(file_info['relative_path'], repo_id)
        print("✓ Marked file as deleted")
        
        # Verify soft delete
        deleted_file = store.get_file(test_file, repo_id)
        assert deleted_file is None, "Soft delete failed"
        
        print("✓ SQLiteStore tests passed")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_file_operations():
    """Test file move and delete operations."""
    print("\n=== Testing File Operations ===")
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test files
        old_file = tmpdir / "old_name.py"
        new_file = tmpdir / "new_name.py"
        old_file.write_text("print('hello world')")
        
        # Initialize components
        resolver = PathResolver(tmpdir)
        db_path = tmpdir / "test.db"
        store = SQLiteStore(str(db_path), path_resolver=resolver)
        
        # Create repository
        repo_id = store.create_repository(str(tmpdir), "Test")
        
        # Store original file
        file_id = store.store_file(repo_id, old_file)
        original_info = store.get_file(old_file, repo_id)
        print(f"Original file: {original_info['relative_path']}")
        
        # Move file
        shutil.move(str(old_file), str(new_file))
        content_hash = resolver.compute_content_hash(new_file)
        
        # Update in database
        store.move_file(
            original_info['relative_path'],
            resolver.normalize_path(new_file),
            repo_id,
            content_hash
        )
        print(f"Moved to: {resolver.normalize_path(new_file)}")
        
        # Verify move
        old_info = store.get_file(old_file, repo_id)
        new_info = store.get_file(new_file, repo_id)
        
        assert old_info is None, "Old file still exists"
        assert new_info is not None, "New file not found"
        assert new_info['content_hash'] == content_hash, "Content hash mismatch"
        
        print("✓ File operations tests passed")


def test_integration():
    """Test integrated path management with dispatcher."""
    print("\n=== Testing Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test file
        test_file = tmpdir / "test.py"
        test_file.write_text("""
def hello():
    '''Say hello'''
    print('Hello, world!')

class TestClass:
    def method(self):
        pass
""")
        
        # Initialize components
        db_path = tmpdir / "test.db"
        resolver = PathResolver(tmpdir)
        store = SQLiteStore(str(db_path), path_resolver=resolver)
        
        # Create repository
        repo_id = store.create_repository(str(tmpdir), "Test")
        
        # Initialize dispatcher
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            use_plugin_factory=True,
            lazy_load=True
        )
        
        # Index file
        dispatcher.index_file(test_file)
        print("✓ File indexed")
        
        # Search for content
        results = list(dispatcher.search("hello", limit=5))
        assert len(results) > 0, "Search returned no results"
        print(f"✓ Search found {len(results)} results")
        
        # Test file removal
        dispatcher.remove_file(test_file)
        print("✓ File removed from index")
        
        print("✓ Integration tests passed")


def main():
    """Run all tests."""
    print("Path Management Implementation Tests")
    print("=" * 40)
    
    try:
        test_path_resolver()
        test_sqlite_store()
        test_file_operations()
        test_integration()
        
        print("\n" + "=" * 40)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()