#!/usr/bin/env python3
"""Test script for git-integrated repository tracking and index syncing."""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.git_index_manager import GitAwareIndexManager
from mcp_server.indexing.change_detector import ChangeDetector
from mcp_server.indexing.incremental_indexer import IncrementalIndexer
from mcp_server.artifacts.commit_artifacts import CommitArtifactManager
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

def run_command(cmd, cwd=None):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"Error: {result.stderr}")
    return result.stdout.strip()

def create_test_repo(base_dir, repo_name):
    """Create a test git repository with some content."""
    repo_path = base_dir / repo_name
    repo_path.mkdir(parents=True)
    
    # Initialize git repo
    run_command("git init", cwd=repo_path)
    run_command("git config user.name 'Test User'", cwd=repo_path)
    run_command("git config user.email 'test@example.com'", cwd=repo_path)
    
    # Create initial files
    (repo_path / "README.md").write_text(f"# {repo_name}\n\nTest repository for MCP integration.")
    (repo_path / "main.py").write_text("""
def greet(name: str) -> str:
    '''Greet a person by name.'''
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    '''Add two numbers.'''
    return a + b

if __name__ == "__main__":
    print(greet("World"))
    print(f"2 + 3 = {add(2, 3)}")
""")
    
    # Create subdirectory with more files
    (repo_path / "utils").mkdir()
    (repo_path / "utils" / "__init__.py").write_text("")
    (repo_path / "utils" / "helpers.py").write_text("""
def format_date(date):
    '''Format a date object.'''
    return date.strftime("%Y-%m-%d")

def calculate_percentage(value, total):
    '''Calculate percentage.'''
    if total == 0:
        return 0
    return (value / total) * 100
""")
    
    # Initial commit
    run_command("git add .", cwd=repo_path)
    run_command("git commit -m 'Initial commit'", cwd=repo_path)
    
    return repo_path

def test_repository_registration():
    """Test registering repositories."""
    print("\n=== Testing Repository Registration ===")
    
    registry = RepositoryRegistry()
    
    # Create test repositories
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create multiple test repos
        repo1 = create_test_repo(base_dir, "test_repo_1")
        repo2 = create_test_repo(base_dir, "test_repo_2")
        
        # Register repositories
        print(f"\nRegistering {repo1.name}...")
        repo1_id = registry.register_repository(str(repo1))
        print(f"  ID: {repo1_id}")
        
        print(f"\nRegistering {repo2.name}...")
        repo2_id = registry.register_repository(str(repo2), auto_sync=False)
        print(f"  ID: {repo2_id}")
        
        # List repositories
        print("\nListing all repositories:")
        repos = registry.get_all_repositories()
        for repo_id, info in repos.items():
            print(f"  - {info.name} [{repo_id[:8]}...]")
            print(f"    Path: {info.path}")
            print(f"    Auto-sync: {info.auto_sync}")
            print(f"    Current commit: {info.current_commit[:8] if info.current_commit else 'None'}")
        
        # Test path lookup
        print(f"\nLooking up repository by path {repo1}...")
        found_info = registry.get_repository_by_path(str(repo1))
        if found_info:
            print(f"  Found: {found_info.name}")
        
        return True

def test_git_change_detection():
    """Test detecting changes between commits."""
    print("\n=== Testing Git Change Detection ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        repo_path = create_test_repo(base_dir, "change_detection_repo")
        
        # Get initial commit
        initial_commit = run_command("git rev-parse HEAD", cwd=repo_path)
        print(f"Initial commit: {initial_commit[:8]}")
        
        # Make changes
        print("\nMaking changes...")
        
        # Modify existing file
        (repo_path / "main.py").write_text((repo_path / "main.py").read_text() + """

def multiply(a: int, b: int) -> int:
    '''Multiply two numbers.'''
    return a * b
""")
        
        # Add new file
        (repo_path / "utils" / "math_utils.py").write_text("""
import math

def square_root(n):
    '''Calculate square root.'''
    return math.sqrt(n)

def power(base, exp):
    '''Calculate power.'''
    return base ** exp
""")
        
        # Delete a file
        (repo_path / "utils" / "helpers.py").unlink()
        
        # Commit changes
        run_command("git add .", cwd=repo_path)
        run_command("git commit -m 'Add math functions and refactor'", cwd=repo_path)
        new_commit = run_command("git rev-parse HEAD", cwd=repo_path)
        print(f"New commit: {new_commit[:8]}")
        
        # Test change detection
        detector = ChangeDetector(str(repo_path))
        changes = detector.get_changes_since_commit(initial_commit, new_commit)
        
        print(f"\nDetected {len(changes)} changes:")
        for change in changes:
            print(f"  - {change.action}: {change.path}")
            if change.old_path and change.old_path != change.path:
                print(f"    (was: {change.old_path})")
        
        return True

def test_incremental_indexing():
    """Test incremental index updates."""
    print("\n=== Testing Incremental Indexing ===")
    
    registry = RepositoryRegistry()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        repo_path = create_test_repo(base_dir, "incremental_test_repo")
        
        # Register repository
        repo_id = registry.register_repository(str(repo_path))
        repo_info = registry.get_repository(repo_id)
        
        # Create index directory
        index_dir = Path(repo_info.index_location)
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        store = SQLiteStore(str(index_dir / "current.db"))
        dispatcher = EnhancedDispatcher(sqlite_store=store)
        index_manager = GitAwareIndexManager(registry, dispatcher)
        
        # Initial index
        print("\nPerforming initial index...")
        result = index_manager.sync_repository_index(repo_id, force_full=True)
        print(f"  Action: {result.action}")
        print(f"  Files processed: {result.files_processed}")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        
        # Make incremental changes
        print("\nMaking incremental changes...")
        (repo_path / "new_module.py").write_text("""
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        self.result += value
        return self.result
""")
        
        run_command("git add .", cwd=repo_path)
        run_command("git commit -m 'Add calculator module'", cwd=repo_path)
        
        # Update current commit in registry
        registry.update_current_commit(repo_id)
        
        # Incremental update
        print("\nPerforming incremental update...")
        result = index_manager.sync_repository_index(repo_id)
        print(f"  Action: {result.action}")
        print(f"  Files processed: {result.files_processed}")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        
        # Verify index contains new content
        search_results = dispatcher.search_code("Calculator", limit=5)
        print(f"\nSearch for 'Calculator' found {len(search_results)} results")
        
        return True

def test_artifact_management():
    """Test commit-based artifact management."""
    print("\n=== Testing Artifact Management ===")
    
    registry = RepositoryRegistry()
    artifact_manager = CommitArtifactManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        repo_path = create_test_repo(base_dir, "artifact_test_repo")
        
        # Register repository
        repo_id = registry.register_repository(str(repo_path))
        repo_info = registry.get_repository(repo_id)
        
        # Create test index
        index_dir = Path(repo_info.index_location)
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "current.db").write_text("test index content")
        
        # Get current commit
        commit = run_command("git rev-parse HEAD", cwd=repo_path)
        
        # Create artifact
        print(f"\nCreating artifact for commit {commit[:8]}...")
        artifact_path = artifact_manager.create_commit_artifact(repo_id, commit, index_dir)
        if artifact_path:
            print(f"  Created: {artifact_path.name}")
            print(f"  Size: {artifact_path.stat().st_size} bytes")
        
        # List artifacts
        print("\nListing artifacts...")
        artifacts = artifact_manager.list_repository_artifacts(repo_id)
        for artifact in artifacts:
            print(f"  - {artifact['commit'][:8]}: {artifact['filename']}")
            print(f"    Created: {artifact['created']}")
            print(f"    Size: {artifact['size_mb']:.2f} MB")
        
        # Test cleanup
        print("\nTesting artifact cleanup...")
        removed = artifact_manager.cleanup_old_artifacts(repo_id, keep_last=0)
        print(f"  Removed {removed} artifact(s)")
        
        return True

def test_repository_discovery():
    """Test discovering repositories in directories."""
    print("\n=== Testing Repository Discovery ===")
    
    registry = RepositoryRegistry()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create nested repositories
        repos = []
        repos.append(create_test_repo(base_dir, "project1"))
        repos.append(create_test_repo(base_dir / "workspace", "project2"))
        repos.append(create_test_repo(base_dir / "workspace" / "libs", "library1"))
        
        # Create non-git directory
        (base_dir / "not_a_repo").mkdir()
        (base_dir / "not_a_repo" / "file.txt").write_text("test")
        
        # Discover repositories
        print(f"\nDiscovering repositories in {base_dir}...")
        discovered = registry.discover_repositories([str(base_dir)])
        
        print(f"Found {len(discovered)} repositories:")
        for repo_path in discovered:
            print(f"  - {Path(repo_path).name} at {repo_path}")
        
        # Register discovered repos
        print("\nRegistering discovered repositories...")
        for repo_path in discovered:
            repo_id = registry.register_repository(repo_path)
            print(f"  Registered {Path(repo_path).name} as {repo_id[:8]}...")
        
        return True

def test_cli_integration():
    """Test CLI command integration."""
    print("\n=== Testing CLI Integration ===")
    
    # Test CLI commands using subprocess
    cli_path = project_root / "mcp_server" / "cli" / "__init__.py"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        repo_path = create_test_repo(base_dir, "cli_test_repo")
        
        # Change to repo directory
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Test repository registration via CLI
            print("\nTesting CLI repository registration...")
            result = run_command(f"python {cli_path} repository register .")
            print(result)
            
            # Test repository list
            print("\nTesting CLI repository list...")
            result = run_command(f"python {cli_path} repository list --verbose")
            print(result)
            
            # Test repository status
            print("\nTesting CLI repository status...")
            result = run_command(f"python {cli_path} repository status")
            print(result)
            
        finally:
            os.chdir(original_cwd)
        
        return True

def main():
    """Run all tests."""
    print("Testing Git-Integrated Repository Tracking and Index Syncing")
    print("=" * 60)
    
    tests = [
        test_repository_registration,
        test_git_change_detection,
        test_incremental_indexing,
        test_artifact_management,
        test_repository_discovery,
        test_cli_integration
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