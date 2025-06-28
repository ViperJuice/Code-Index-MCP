#!/usr/bin/env python3
"""Run comprehensive tests for git-integrated repository tracking."""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.test_utilities import (
    TestRepositoryBuilder,
    GitCommit,
    create_test_environment,
    cleanup_test_environment,
    PerformanceTracker,
    count_files_by_extension,
    measure_index_size
)
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.git_index_manager import GitAwareIndexManager
from mcp_server.indexing.change_detector import ChangeDetector
from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRunner:
    """Simple test runner without pytest dependency."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.perf_tracker = PerformanceTracker()
    
    def run_test(self, test_name, test_func):
        """Run a single test function."""
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            start_time = time.time()
            test_func()
            duration = time.time() - start_time
            
            self.passed += 1
            print(f"✓ PASSED in {duration:.3f}s")
            
        except Exception as e:
            self.failed += 1
            self.errors.append((test_name, e))
            print(f"✗ FAILED: {str(e)}")
            traceback.print_exc()
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        
        if self.errors:
            print("\nFailed Tests:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {str(error)}")
        
        # Performance summary
        perf_summary = self.perf_tracker.get_summary()
        if perf_summary:
            print("\nPerformance Summary:")
            for op, stats in perf_summary.items():
                print(f"  {op}:")
                print(f"    Average: {stats['average']:.3f}s")
                print(f"    Min: {stats['min']:.3f}s, Max: {stats['max']:.3f}s")


def test_repository_registration():
    """Test basic repository registration."""
    test_env = create_test_environment()
    
    try:
        # Setup registry with test environment
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)
        
        registry = RepositoryRegistry()
        
        # Create test repositories
        print("Creating test repositories...")
        repos = []
        for i in range(3):
            repo = TestRepositoryBuilder.create_repository(
                test_env, f"test_repo_{i}", 
                language=["python", "javascript", "go"][i]
            )
            repos.append(repo)
        
        # Register repositories
        print("\nRegistering repositories...")
        repo_ids = []
        for repo in repos:
            repo_id = registry.register_repository(str(repo.path))
            repo_ids.append(repo_id)
            print(f"  Registered {repo.name}: {repo_id[:8]}...")
        
        # Verify registration
        assert len(repo_ids) == 3
        assert len(set(repo_ids)) == 3  # All unique
        
        # Test retrieval
        for repo_id, repo in zip(repo_ids, repos):
            info = registry.get_repository(repo_id)
            assert info is not None
            assert info.path == str(repo.path)
            assert info.name == repo.name
            print(f"  ✓ Retrieved {info.name}")
        
        # Test listing
        all_repos = registry.get_all_repositories()
        assert len(all_repos) == 3
        print(f"\n✓ Successfully registered and retrieved {len(all_repos)} repositories")
        
    finally:
        if 'original_home' in locals() and original_home:
            os.environ["HOME"] = original_home
        cleanup_test_environment(test_env)


def test_git_change_detection():
    """Test detecting changes between git commits."""
    test_env = create_test_environment()
    
    try:
        # Create repository
        print("Creating repository with git history...")
        repo = TestRepositoryBuilder.create_repository(
            test_env, "change_test_repo", language="python"
        )
        
        initial_commit = repo.commit_history[0]
        print(f"Initial commit: {initial_commit[:8]}")
        
        # Make various changes
        changes = [
            GitCommit("Add new feature", {"src/new_feature.py": "add"}),
            GitCommit("Update services", {"src/services.py": "modify"}),
            GitCommit("Remove old test", {"tests/test_services.py": "delete"})
        ]
        
        print("\nApplying changes...")
        for commit in changes:
            TestRepositoryBuilder.apply_commit(repo, commit)
            print(f"  Applied: {commit.message}")
        
        # Detect changes
        print("\nDetecting changes...")
        detector = ChangeDetector(str(repo.path))
        detected_changes = detector.get_changes_since_commit(
            initial_commit, repo.commit_history[-1]
        )
        
        print(f"Found {len(detected_changes)} changes:")
        for change in detected_changes:
            print(f"  - {change.action}: {change.path}")
        
        # Verify changes
        assert len(detected_changes) == 3
        actions = {c.action for c in detected_changes}
        assert "add" in actions
        assert "modify" in actions
        assert "delete" in actions
        
        print("\n✓ Change detection working correctly")
        
    finally:
        cleanup_test_environment(test_env)


def test_multi_repository_search():
    """Test searching across multiple repositories."""
    test_env = create_test_environment()
    perf = PerformanceTracker()
    
    try:
        # Setup registry
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)
        registry = RepositoryRegistry()
        
        # Create diverse repositories
        print("Creating diverse repositories...")
        repos = []
        
        # Python web app
        repo1 = TestRepositoryBuilder.create_repository(
            test_env, "python_webapp", language="python"
        )
        repos.append(repo1)
        
        # JavaScript frontend
        repo2 = TestRepositoryBuilder.create_repository(
            test_env, "js_frontend", language="javascript"
        )
        repos.append(repo2)
        
        # Multi-language project
        repo3 = TestRepositoryBuilder.create_multi_language_repo(
            test_env, "fullstack_app"
        )
        repos.append(repo3)
        
        # Create indexes
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)
        
        print("\nIndexing repositories...")
        repo_ids = []
        for repo in repos:
            # Register
            repo_id = registry.register_repository(str(repo.path))
            repo_ids.append(repo_id)
            
            # Create simple index (simulate)
            index_path = index_dir / f"{repo_id}.db"
            store = SQLiteStore(str(index_path))
            
            # Add some test data
            store.add_symbol(
                repo_id=repo_id,
                file_path="test.py",
                symbol_name="UserService",
                symbol_type="class",
                line_number=10
            )
            
            print(f"  Indexed {repo.name}")
        
        # Test multi-repo manager
        print("\nTesting multi-repository search...")
        manager = MultiRepoIndexManager("primary", str(index_dir))
        
        # Add repositories
        for repo_id, repo in zip(repo_ids, repos):
            manager.add_repository(repo_id, repo.path)
        
        # Search across repos
        perf.start_timing("multi_search")
        results = manager.search_all_repositories("UserService", limit=20)
        search_time = perf.end_timing("multi_search")
        
        print(f"\nSearch completed in {search_time:.3f}s")
        print(f"Found {len(results)} results")
        
        # Group by repository
        by_repo = {}
        for result in results:
            repo_id = result.get("repo_id", "unknown")
            by_repo[repo_id] = by_repo.get(repo_id, 0) + 1
        
        for repo_id, count in by_repo.items():
            info = registry.get_repository(repo_id)
            if info:
                print(f"  {info.name}: {count} results")
        
        print("\n✓ Multi-repository search working")
        
    finally:
        if 'original_home' in locals() and original_home:
            os.environ["HOME"] = original_home
        cleanup_test_environment(test_env)


def test_incremental_indexing():
    """Test incremental vs full indexing."""
    test_env = create_test_environment()
    perf = PerformanceTracker()
    
    try:
        # Setup
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)
        registry = RepositoryRegistry()
        
        # Create repository with multiple files
        print("Creating repository with multiple files...")
        repo = TestRepositoryBuilder.create_repository(
            test_env, "incremental_test", language="python"
        )
        
        # Add more files
        for i in range(10):
            file_path = repo.path / f"module_{i}.py"
            file_path.write_text(f"# Module {i}\ndef func_{i}():\n    pass\n")
        
        TestRepositoryBuilder.run_git_command("git add .", repo.path)
        TestRepositoryBuilder.run_git_command("git commit -m 'Add modules'", repo.path)
        
        # Register repository
        repo_id = registry.register_repository(str(repo.path))
        
        # Setup indexing
        index_path = Path(registry.get_repository(repo_id).index_location)
        index_path.mkdir(parents=True, exist_ok=True)
        store = SQLiteStore(str(index_path / "current.db"))
        dispatcher = EnhancedDispatcher(sqlite_store=store)
        manager = GitAwareIndexManager(registry, dispatcher)
        
        # Full index
        print("\nPerforming full index...")
        perf.start_timing("full_index")
        result = manager.sync_repository_index(repo_id, force_full=True)
        full_time = perf.end_timing("full_index")
        print(f"  Full index: {result.files_processed} files in {full_time:.3f}s")
        
        # Make small change
        print("\nMaking small change...")
        (repo.path / "small_change.py").write_text("# Small change\ndef new_func():\n    pass\n")
        TestRepositoryBuilder.run_git_command("git add .", repo.path)
        TestRepositoryBuilder.run_git_command("git commit -m 'Small change'", repo.path)
        registry.update_current_commit(repo_id)
        
        # Incremental update
        print("Performing incremental update...")
        perf.start_timing("incremental")
        result = manager.sync_repository_index(repo_id)
        inc_time = perf.end_timing("incremental")
        print(f"  Incremental: {result.files_processed} files in {inc_time:.3f}s")
        
        # Verify incremental is faster
        speedup = full_time / inc_time if inc_time > 0 else 999
        print(f"  Speedup: {speedup:.1f}x")
        assert inc_time < full_time
        
        print("\n✓ Incremental indexing working efficiently")
        
    finally:
        if 'original_home' in locals() and original_home:
            os.environ["HOME"] = original_home
        cleanup_test_environment(test_env)


def test_repository_discovery():
    """Test discovering repositories in directories."""
    test_env = create_test_environment()
    
    try:
        # Setup
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)
        registry = RepositoryRegistry()
        
        # Create nested repository structure
        print("Creating nested repository structure...")
        workspace = test_env / "workspace"
        
        repos = []
        repos.append(TestRepositoryBuilder.create_repository(
            workspace, "project1", language="python"
        ))
        repos.append(TestRepositoryBuilder.create_repository(
            workspace / "frontend", "web_app", language="javascript"
        ))
        repos.append(TestRepositoryBuilder.create_repository(
            workspace / "backend" / "services", "api", language="go"
        ))
        
        # Create non-git directories
        (workspace / "docs").mkdir(parents=True)
        (workspace / "build").mkdir(parents=True)
        
        # Discover repositories
        print("\nDiscovering repositories...")
        discovered = registry.discover_repositories([str(workspace)])
        
        print(f"Found {len(discovered)} repositories:")
        for path in discovered:
            print(f"  - {Path(path).name} at {Path(path).relative_to(workspace)}")
        
        assert len(discovered) == 3
        
        # Register all discovered
        print("\nRegistering discovered repositories...")
        for path in discovered:
            repo_id = registry.register_repository(path)
            info = registry.get_repository(repo_id)
            print(f"  Registered {info.name}")
        
        print("\n✓ Repository discovery working correctly")
        
    finally:
        if 'original_home' in locals() and original_home:
            os.environ["HOME"] = original_home
        cleanup_test_environment(test_env)


def main():
    """Run all tests."""
    print("GIT-INTEGRATED REPOSITORY TRACKING TEST SUITE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    runner = TestRunner()
    
    # Phase 1: Core functionality tests
    print("\n\nPHASE 1: CORE FUNCTIONALITY TESTS")
    print("-" * 60)
    
    runner.run_test("Repository Registration", test_repository_registration)
    runner.run_test("Git Change Detection", test_git_change_detection)
    runner.run_test("Multi-Repository Search", test_multi_repository_search)
    runner.run_test("Incremental Indexing", test_incremental_indexing)
    runner.run_test("Repository Discovery", test_repository_discovery)
    
    # Print summary
    runner.print_summary()
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return runner.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)