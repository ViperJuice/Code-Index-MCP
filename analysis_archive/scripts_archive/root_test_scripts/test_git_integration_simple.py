#!/usr/bin/env python3
"""Simple test to verify git integration components exist."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        print("  - Importing repository_registry...", end="")
        from mcp_server.storage.repository_registry import RepositoryRegistry
        print(" OK")
        
        print("  - Importing git_index_manager...", end="")
        from mcp_server.storage.git_index_manager import GitAwareIndexManager
        print(" OK")
        
        print("  - Importing change_detector...", end="")
        from mcp_server.indexing.change_detector import ChangeDetector
        print(" OK")
        
        print("  - Importing incremental_indexer...", end="")
        from mcp_server.indexing.incremental_indexer import IncrementalIndexer
        print(" OK")
        
        print("  - Importing commit_artifacts...", end="")
        from mcp_server.artifacts.commit_artifacts import CommitArtifactManager
        print(" OK")
        
        print("  - Importing watcher_multi_repo...", end="")
        from mcp_server.watcher_multi_repo import MultiRepositoryWatcher
        print(" OK")
        
        print("\nAll imports successful!")
        return True
        
    except ImportError as e:
        print(f"\nImport failed: {e}")
        return False

def test_existing_components():
    """Test what components are actually available in the codebase."""
    print("\nChecking existing components...")
    
    # Check for existing multi-repo support
    try:
        from mcp_server.storage.multi_repo_manager import MultiRepoManager
        print("  ✓ MultiRepoManager exists")
    except ImportError:
        print("  ✗ MultiRepoManager not found")
    
    # Check for existing indexer
    try:
        from mcp_server.indexer.index_engine import IndexEngine
        print("  ✓ IndexEngine exists")
    except ImportError:
        print("  ✗ IndexEngine not found")
    
    # Check for existing dispatcher
    try:
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
        print("  ✓ EnhancedDispatcher exists")
    except ImportError:
        print("  ✗ EnhancedDispatcher not found")
    
    # Check for existing watcher
    try:
        from mcp_server.watcher import FileWatcher
        print("  ✓ FileWatcher exists")
    except ImportError:
        print("  ✗ FileWatcher not found")
    
    # Check for CLI
    try:
        from mcp_server.cli import cli
        print("  ✓ CLI exists")
    except ImportError:
        print("  ✗ CLI not found")
    
    return True

def test_simple_registry():
    """Test basic repository registry functionality."""
    print("\nTesting simple registry operations...")
    
    try:
        from mcp_server.storage.repository_registry import RepositoryRegistry
        
        # Create registry
        registry = RepositoryRegistry()
        print("  ✓ Created RepositoryRegistry")
        
        # Test registry file location
        registry_file = Path.home() / ".mcp" / "repository_registry.json"
        print(f"  - Registry file: {registry_file}")
        print(f"  - Registry exists: {registry_file.exists()}")
        
        # Try to list repositories
        repos = registry.get_all_repositories()
        print(f"  - Found {len(repos)} registered repositories")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run simple tests."""
    print("Git Integration Component Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_existing_components,
        test_simple_registry
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_func.__name__} error: {e}")
    
    print(f"\n\nSummary: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)