"""Test multi-repository search functionality."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.sqlite_store import SQLiteStore
from tests.test_utilities import (
    PerformanceTracker,
    TestRepositoryBuilder,
    cleanup_test_environment,
    count_files_by_extension,
    create_test_environment,
)


class TestMultiRepoSearch:
    """Test suite for multi-repository search functionality."""

    @pytest.fixture
    def test_env(self):
        """Create a test environment."""
        env_path = create_test_environment()
        yield env_path
        cleanup_test_environment(env_path)

    @pytest.fixture
    def registry(self, test_env):
        """Create a test registry."""
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = str(test_env)

        registry = RepositoryRegistry()

        yield registry

        if original_home:
            os.environ["HOME"] = original_home

    def create_diverse_repos(self, test_env):
        """Create a set of diverse repositories for testing."""
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

        # Go microservice
        repo3 = TestRepositoryBuilder.create_repository(test_env, "go_service", language="go")
        repos.append(repo3)

        # Multi-language project
        repo4 = TestRepositoryBuilder.create_multi_language_repo(test_env, "full_stack_app")
        repos.append(repo4)

        # Documentation repository (markdown)
        repo5 = TestRepositoryBuilder.create_repository(test_env, "docs_repo", language="python")
        # Add markdown files
        (repo5.path / "README.md").write_text("# Documentation\n\nProject documentation.")
        (repo5.path / "docs" / "api.md").write_text("# API Reference\n\n## UserService\n")
        (repo5.path / "docs" / "setup.md").write_text("# Setup Guide\n\n1. Install dependencies")
        TestRepositoryBuilder.run_git_command("git add .", repo5.path)
        TestRepositoryBuilder.run_git_command("git commit -m 'Add docs'", repo5.path)
        repos.append(repo5)

        return repos

    def index_repository(self, repo_path: Path, repo_id: str, index_dir: Path):
        """Index a single repository."""
        index_path = index_dir / f"{repo_id}.db"
        store = SQLiteStore(str(index_path))

        # Create plugin manager and dispatcher
        plugin_manager = PluginManager()
        dispatcher = EnhancedDispatcher(sqlite_store=store)

        # Create index engine
        engine = IndexEngine(
            plugin_manager=plugin_manager, storage=store, repository_path=str(repo_path)
        )

        # Index the repository
        stats = engine.index_directory(str(repo_path))

        return stats

    def test_multi_repo_setup(self, test_env, registry):
        """Test setting up multiple repository indexes."""
        # Create repositories
        repos = self.create_diverse_repos(test_env)

        # Create index directory
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Register and index all repositories
        perf = PerformanceTracker()

        for repo in repos:
            # Register
            perf.start_timing(f"register_{repo.name}")
            repo_id = registry.register_repository(str(repo.path))
            reg_time = perf.end_timing(f"register_{repo.name}")

            # Index
            perf.start_timing(f"index_{repo.name}")
            stats = self.index_repository(repo.path, repo_id, index_dir)
            index_time = perf.end_timing(f"index_{repo.name}")

            print(f"\n{repo.name}:")
            print(f"  Registration: {reg_time:.3f}s")
            print(f"  Indexing: {index_time:.3f}s")
            print(f"  Files: {stats.total_files}")
            print(f"  Symbols: {stats.total_symbols}")

        # Verify all registered
        all_repos = registry.get_all_repositories()
        assert len(all_repos) == 5

        # Check performance
        summary = perf.get_summary()
        for op, stats in summary.items():
            if op.startswith("register_"):
                assert stats["average"] < 1.0, f"Registration too slow: {stats}"

    def test_cross_repository_search(self, test_env, registry):
        """Test searching across multiple repositories."""
        # Setup repositories
        repos = self.create_diverse_repos(test_env)
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Register and index
        repo_ids = []
        for repo in repos:
            repo_id = registry.register_repository(str(repo.path))
            repo_ids.append(repo_id)
            self.index_repository(repo.path, repo_id, index_dir)

        # Create multi-repo manager
        manager = MultiRepoIndexManager("primary", str(index_dir))

        # Add all repositories
        for i, (repo_id, repo) in enumerate(zip(repo_ids, repos)):
            manager.add_repository(repo_id, repo.path)

        # Test searches
        perf = PerformanceTracker()

        # Search for common terms across repos
        queries = [
            "UserService",  # Should be in Python and Go repos
            "Controller",  # Should be in JavaScript
            "create_user",  # Python method
            "async",  # JavaScript keyword
            "struct",  # Go keyword
            "def",  # Python keyword
            "API",  # Should be in docs
        ]

        for query in queries:
            perf.start_timing(f"search_{query}")
            results = manager.search_all_repositories(query, limit=20)
            search_time = perf.end_timing(f"search_{query}")

            print(f"\nQuery '{query}':")
            print(f"  Time: {search_time:.3f}s")
            print(f"  Results: {len(results)}")

            # Group by repository
            by_repo = {}
            for result in results:
                repo_id = result.get("repo_id", "unknown")
                if repo_id not in by_repo:
                    by_repo[repo_id] = 0
                by_repo[repo_id] += 1

            for repo_id, count in by_repo.items():
                repo_info = registry.get_repository(repo_id)
                if repo_info:
                    print(f"    {repo_info.name}: {count}")

        # Performance assertions
        avg_search = perf.get_average("search_UserService")
        assert avg_search < 1.0, f"Search too slow: {avg_search:.3f}s"

    def test_language_specific_filtering(self, test_env, registry):
        """Test filtering search results by language."""
        # Setup repositories
        repos = self.create_diverse_repos(test_env)
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Index repositories
        repo_map = {}
        for repo in repos:
            repo_id = registry.register_repository(str(repo.path))
            self.index_repository(repo.path, repo_id, index_dir)
            repo_map[repo_id] = repo

        # Create manager with language tracking
        manager = MultiRepoIndexManager("primary", str(index_dir))

        # Add repositories and detect languages
        for repo_id, repo in repo_map.items():
            manager.add_repository(repo_id, repo.path)

            # Detect languages in repository
            file_counts = count_files_by_extension(repo.path)
            languages = set()

            if file_counts.get(".py", 0) > 0:
                languages.add("python")
            if file_counts.get(".js", 0) > 0:
                languages.add("javascript")
            if file_counts.get(".go", 0) > 0:
                languages.add("go")

            manager.repo_languages[repo_id] = languages

        # Test language-specific searches
        # Search for Python-specific content
        python_repos = [rid for rid, langs in manager.repo_languages.items() if "python" in langs]

        results = manager.search_repositories("def __init__", repo_ids=python_repos)

        # Should only get results from Python repos
        for result in results:
            repo_id = result.get("repo_id")
            assert "python" in manager.repo_languages.get(repo_id, set())

    def test_concurrent_search_performance(self, test_env, registry):
        """Test concurrent searches across repositories."""
        # Setup repositories
        repos = self.create_diverse_repos(test_env)
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Index all
        repo_ids = []
        for repo in repos:
            repo_id = registry.register_repository(str(repo.path))
            repo_ids.append(repo_id)
            self.index_repository(repo.path, repo_id, index_dir)

        # Create manager
        manager = MultiRepoIndexManager("primary", str(index_dir))
        for repo_id, repo in zip(repo_ids, repos):
            manager.add_repository(repo_id, repo.path)

        # Test concurrent searches
        perf = PerformanceTracker()
        queries = ["User", "Service", "create", "get", "update"]

        # Sequential baseline
        perf.start_timing("sequential")
        sequential_results = []
        for query in queries:
            results = manager.search_all_repositories(query)
            sequential_results.append(len(results))
        seq_time = perf.end_timing("sequential")

        # Concurrent execution
        perf.start_timing("concurrent")

        async def concurrent_search():
            tasks = [manager.search_across_repos(query) for query in queries]
            return await asyncio.gather(*tasks)

        concurrent_results = asyncio.run(concurrent_search())
        conc_time = perf.end_timing("concurrent")

        print("\nConcurrency Performance:")
        print(f"  Sequential: {seq_time:.3f}s")
        print(f"  Concurrent: {conc_time:.3f}s")
        print(f"  Speedup: {seq_time/conc_time:.2f}x")

        # Concurrent should be faster
        assert conc_time < seq_time

        # Results should be the same
        for i, (seq_count, conc_results) in enumerate(zip(sequential_results, concurrent_results)):
            assert seq_count == len(conc_results), f"Query {i} result mismatch"

    def test_repository_priority_ranking(self, test_env, registry):
        """Test repository result ranking and prioritization."""
        # Create repositories with different characteristics
        repos = self.create_diverse_repos(test_env)
        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Index and set priorities
        repo_priorities = {}
        for i, repo in enumerate(repos):
            repo_id = registry.register_repository(str(repo.path))
            self.index_repository(repo.path, repo_id, index_dir)

            # Set priorities based on repository type
            if "webapp" in repo.name:
                repo_priorities[repo_id] = 100  # High priority
            elif "frontend" in repo.name:
                repo_priorities[repo_id] = 90
            elif "service" in repo.name:
                repo_priorities[repo_id] = 80
            else:
                repo_priorities[repo_id] = 50

        # Create manager
        manager = MultiRepoIndexManager("primary", str(index_dir))

        # Add repositories with priorities
        for repo_id, repo in zip(repo_priorities.keys(), repos):
            manager.add_repository(repo_id, repo.path)

        # Search and verify ranking
        results = manager.search_all_repositories("User", limit=50)

        # Group by repository and check order
        repo_order = []
        seen_repos = set()
        for result in results:
            repo_id = result.get("repo_id")
            if repo_id not in seen_repos:
                repo_order.append(repo_id)
                seen_repos.add(repo_id)

        # Higher priority repos should appear first
        for i in range(len(repo_order) - 1):
            pri1 = repo_priorities.get(repo_order[i], 0)
            pri2 = repo_priorities.get(repo_order[i + 1], 0)
            # Allow for some variation due to relevance scoring
            # but general trend should hold
            if abs(pri1 - pri2) > 20:
                assert pri1 >= pri2, f"Priority ordering violated: {pri1} < {pri2}"

    def test_memory_efficient_loading(self, test_env, registry):
        """Test memory-efficient repository index loading."""
        # Create many small repositories
        repos = []
        for i in range(10):
            repo = TestRepositoryBuilder.create_repository(
                test_env, f"small_repo_{i}", language="python"
            )
            repos.append(repo)

        index_dir = test_env / ".indexes"
        index_dir.mkdir(exist_ok=True)

        # Index all
        repo_ids = []
        for repo in repos:
            repo_id = registry.register_repository(str(repo.path))
            repo_ids.append(repo_id)
            self.index_repository(repo.path, repo_id, index_dir)

        # Create manager with limited concurrent repos
        manager = MultiRepoIndexManager("primary", str(index_dir))
        manager.max_concurrent_repos = 3  # Limit loaded indexes

        # Add all repositories
        for repo_id, repo in zip(repo_ids, repos):
            manager.add_repository(repo_id, repo.path)

        # Perform searches that touch all repos
        results = manager.search_all_repositories("def", limit=100)

        # Check that not all indexes are loaded
        assert len(manager.loaded_indexes) <= manager.max_concurrent_repos

        print("\nMemory Management:")
        print(f"  Total repos: {len(repo_ids)}")
        print(f"  Loaded indexes: {len(manager.loaded_indexes)}")
        print(f"  Search results: {len(results)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
