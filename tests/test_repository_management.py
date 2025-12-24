"""Test repository registration and management functionality."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.repository_registry import RepositoryRegistry
from tests.test_utilities import (
    PerformanceTracker,
    TestRepositoryBuilder,
    cleanup_test_environment,
    create_test_environment,
)


class TestRepositoryManagement:
    """Test suite for repository management functionality."""

    @pytest.fixture
    def test_env(self):
        """Create a test environment."""
        env_path = create_test_environment()
        yield env_path
        cleanup_test_environment(env_path)

    @pytest.fixture
    def registry(self, test_env):
        """Create a test registry with custom location."""
        registry_path = test_env / ".mcp" / "test_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Temporarily override the registry path
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)

        registry = RepositoryRegistry()

        yield registry

        # Restore original home
        if original_home:
            os.environ["HOME"] = original_home

    def test_register_single_repository(self, test_env, registry):
        """Test registering a single repository."""
        # Create test repository
        repo = TestRepositoryBuilder.create_repository(test_env, "test_repo", language="python")

        # Register repository
        repo_id = registry.register_repository(str(repo.path))

        # Verify registration
        assert repo_id is not None
        assert len(repo_id) == 64  # SHA256 hash length

        # Check repository info
        info = registry.get_repository(repo_id)
        assert info is not None
        assert info.path == str(repo.path)
        assert info.name == "test_repo"
        assert info.auto_sync is True
        assert info.current_commit is not None

    def test_register_multiple_repositories(self, test_env, registry):
        """Test registering multiple repositories."""
        perf = PerformanceTracker()

        # Create multiple repositories
        repos = []
        for i in range(5):
            lang = ["python", "javascript", "go"][i % 3]
            repo = TestRepositoryBuilder.create_repository(test_env, f"repo_{i}", language=lang)
            repos.append(repo)

        # Register all repositories
        repo_ids = []
        for repo in repos:
            perf.start_timing("register")
            repo_id = registry.register_repository(str(repo.path))
            duration = perf.end_timing("register")
            repo_ids.append(repo_id)

            print(f"Registered {repo.name} in {duration:.3f}s")

        # Verify all registered
        assert len(repo_ids) == 5
        assert len(set(repo_ids)) == 5  # All unique

        # Test listing
        all_repos = registry.get_all_repositories()
        assert len(all_repos) == 5

        # Performance check
        avg_time = perf.get_average("register")
        assert avg_time < 1.0, f"Registration too slow: {avg_time:.3f}s average"

    def test_repository_discovery(self, test_env, registry):
        """Test discovering repositories in nested directories."""
        # Create nested repository structure
        workspace = test_env / "workspace"

        # Create repos at different levels
        repos = []
        repos.append(
            TestRepositoryBuilder.create_repository(workspace, "top_level", language="python")
        )
        repos.append(
            TestRepositoryBuilder.create_repository(
                workspace / "frontend", "web_app", language="javascript"
            )
        )
        repos.append(
            TestRepositoryBuilder.create_repository(
                workspace / "backend" / "services", "api_service", language="go"
            )
        )

        # Create non-git directory
        (workspace / "docs").mkdir(parents=True)
        (workspace / "docs" / "README.md").write_text("# Documentation")

        # Discover repositories
        discovered = registry.discover_repositories([str(workspace)])

        # Verify discovery
        assert len(discovered) == 3
        discovered_paths = [Path(p).name for p in discovered]
        assert "top_level" in discovered_paths
        assert "web_app" in discovered_paths
        assert "api_service" in discovered_paths

    def test_registry_persistence(self, test_env, registry):
        """Test that registry persists across sessions."""
        # Register repositories
        repo1 = TestRepositoryBuilder.create_repository(
            test_env, "persist_repo_1", language="python"
        )
        repo2 = TestRepositoryBuilder.create_repository(
            test_env, "persist_repo_2", language="javascript"
        )

        repo1_id = registry.register_repository(str(repo1.path))
        repo2_id = registry.register_repository(str(repo2.path))

        # Get registry file path
        registry_file = Path(registry.registry_file)
        assert registry_file.exists()

        # Create new registry instance
        registry2 = RepositoryRegistry()

        # Verify repositories are loaded
        all_repos = registry2.get_all_repositories()
        assert len(all_repos) >= 2  # May have more from other tests

        # Check specific repos
        info1 = registry2.get_repository(repo1_id)
        info2 = registry2.get_repository(repo2_id)

        assert info1 is not None
        assert info1.path == str(repo1.path)
        assert info2 is not None
        assert info2.path == str(repo2.path)

    def test_repository_status_tracking(self, test_env, registry):
        """Test tracking repository status and git state."""
        # Create repository with commits
        repo = TestRepositoryBuilder.create_repository(test_env, "status_repo", language="python")

        # Register repository
        repo_id = registry.register_repository(str(repo.path))

        # Check initial status
        info = registry.get_repository(repo_id)
        initial_commit = info.current_commit
        assert initial_commit is not None
        assert info.last_indexed_commit is None  # Not indexed yet

        # Simulate indexing
        registry.update_last_indexed(repo_id, initial_commit)

        # Make changes and commit
        new_file = repo.path / "new_feature.py"
        new_file.write_text("def new_feature():\n    pass\n")
        TestRepositoryBuilder.run_git_command("git add .", repo.path)
        TestRepositoryBuilder.run_git_command("git commit -m 'Add new feature'", repo.path)

        # Update current commit
        registry.update_current_commit(repo_id)

        # Check updated status
        info = registry.get_repository(repo_id)
        assert info.current_commit != initial_commit
        assert info.last_indexed_commit == initial_commit

        # Get repositories needing update
        needs_update = registry.get_repositories_needing_update()
        assert len(needs_update) == 1
        assert needs_update[0][0] == repo_id

    def test_auto_sync_configuration(self, test_env, registry):
        """Test auto-sync configuration for repositories."""
        # Create repositories with different auto-sync settings
        repo1 = TestRepositoryBuilder.create_repository(
            test_env, "auto_sync_repo", language="python"
        )
        repo2 = TestRepositoryBuilder.create_repository(
            test_env, "manual_sync_repo", language="javascript"
        )

        # Register with different settings
        repo1_id = registry.register_repository(str(repo1.path), auto_sync=True)
        repo2_id = registry.register_repository(str(repo2.path), auto_sync=False)

        # Verify settings
        info1 = registry.get_repository(repo1_id)
        info2 = registry.get_repository(repo2_id)

        assert info1.auto_sync is True
        assert info2.auto_sync is False

        # Test filtering by auto-sync
        all_repos = registry.get_all_repositories()
        auto_sync_repos = {rid: info for rid, info in all_repos.items() if info.auto_sync}

        assert repo1_id in auto_sync_repos
        assert repo2_id not in auto_sync_repos

    def test_repository_path_lookup(self, test_env, registry):
        """Test looking up repositories by path."""
        # Create and register repository
        repo = TestRepositoryBuilder.create_repository(test_env, "lookup_repo", language="go")
        repo_id = registry.register_repository(str(repo.path))

        # Test exact path lookup
        info = registry.get_repository_by_path(str(repo.path))
        assert info is not None
        assert info.repo_id == repo_id

        # Test with trailing slash
        info = registry.get_repository_by_path(str(repo.path) + "/")
        assert info is not None
        assert info.repo_id == repo_id

        # Test with subdirectory
        subdir = repo.path / "internal" / "models"
        subdir.mkdir(parents=True, exist_ok=True)
        info = registry.get_repository_by_path(str(subdir))
        assert info is not None
        assert info.repo_id == repo_id

        # Test non-existent path
        info = registry.get_repository_by_path("/non/existent/path")
        assert info is None

    def test_repository_deletion(self, test_env, registry):
        """Test removing repositories from registry."""
        # Create and register repositories
        repo1 = TestRepositoryBuilder.create_repository(
            test_env, "delete_repo_1", language="python"
        )
        repo2 = TestRepositoryBuilder.create_repository(
            test_env, "delete_repo_2", language="javascript"
        )

        repo1_id = registry.register_repository(str(repo1.path))
        repo2_id = registry.register_repository(str(repo2.path))

        # Verify both registered
        assert len(registry.get_all_repositories()) == 2

        # Remove one repository
        success = registry.remove_repository(repo1_id)
        assert success is True

        # Verify removal
        assert len(registry.get_all_repositories()) == 1
        assert registry.get_repository(repo1_id) is None
        assert registry.get_repository(repo2_id) is not None

        # Try removing non-existent
        success = registry.remove_repository("non_existent_id")
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
