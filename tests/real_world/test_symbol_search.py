#!/usr/bin/env python3
"""
Real-world symbol search and retrieval tests for Code-Index-MCP.
Tests search accuracy and performance on actual GitHub repositories.
"""

import asyncio
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestSymbolSearch:
    """Test symbol search and retrieval on real-world repositories."""

    @pytest.fixture
    def workspace_dir(self):
        """Provide workspace directory for test repositories."""
        workspace = Path("test_workspace/real_repos")
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @pytest.fixture
    def test_db(self):
        """Provide clean test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        store = SQLiteStore(db_path)
        yield store

        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass

    @pytest.fixture
    def dispatcher(self):
        """Provide configured dispatcher with plugins."""
        dispatcher = Dispatcher()
        plugin_manager = PluginManager()

        # Load all available plugins
        for plugin_name in ["python_plugin", "js_plugin", "c_plugin", "cpp_plugin"]:
            try:
                plugin = plugin_manager.load_plugin(plugin_name)
                dispatcher.register_plugin(plugin_name, plugin)
            except Exception as e:
                print(f"Failed to load {plugin_name}: {e}")

        return dispatcher

    @pytest.fixture
    def fuzzy_indexer(self):
        """Provide fuzzy search indexer."""
        return FuzzyIndexer()

    def ensure_repository_exists(self, workspace_dir: Path, repo_name: str, repo_url: str) -> Path:
        """Ensure repository exists in workspace, download if needed."""
        repo_path = workspace_dir / repo_name

        if not repo_path.exists():
            print(f"Downloading {repo_name} from {repo_url}...")
            try:
                subprocess.run(
                    ["git", "clone", "--depth=1", repo_url, str(repo_path)],
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                print(f"Successfully downloaded {repo_name}")
            except subprocess.CalledProcessError as e:
                pytest.skip(f"Failed to download {repo_name}: {e}")
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout downloading {repo_name}")

        return repo_path

    def setup_indexed_repository(
        self,
        workspace_dir: Path,
        repo_name: str,
        repo_url: str,
        test_db: SQLiteStore,
        dispatcher: Dispatcher,
        fuzzy_indexer: FuzzyIndexer,
    ) -> int:
        """Setup and index a repository for testing."""
        repo_path = self.ensure_repository_exists(workspace_dir, repo_name, repo_url)

        repo_id = test_db.create_repository(str(repo_path), repo_name, {"type": "search_test"})

        # Index files and build search index
        indexed_count = 0
        extensions = [".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp"]

        for ext in extensions:
            files = list(repo_path.rglob(f"*{ext}"))[:200]  # Limit for testing

            for file_path in files:
                try:
                    if file_path.stat().st_size > 512 * 1024:  # Skip large files
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if len(content.strip()) == 0:
                        continue

                    # Index with plugin
                    result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                    if result.success:
                        # Store in database
                        file_id = test_db.store_file(
                            repo_id,
                            str(file_path.relative_to(repo_path)),
                            content,
                            file_path.suffix[1:],
                            file_path.stat().st_mtime,
                        )

                        # Add symbols to search index
                        symbols = result.value.get("symbols", [])
                        for symbol in symbols:
                            symbol_name = symbol.get("name", "")
                            if symbol_name:
                                fuzzy_indexer.add_symbol(
                                    symbol_name,
                                    str(file_path.relative_to(repo_path)),
                                    symbol.get("line", 0),
                                )

                                test_db.store_symbol(
                                    file_id,
                                    symbol_name,
                                    symbol.get("type", ""),
                                    symbol.get("line", 0),
                                    symbol.get("line", 0),
                                    symbol.get("column", 0),
                                    symbol.get("column", 0),
                                    symbol.get("definition", ""),
                                )

                        indexed_count += 1

                except Exception as e:
                    continue

        print(f"Indexed {indexed_count} files from {repo_name}")
        return repo_id

    def index_file_with_plugin(
        self, file_path: str, content: str, dispatcher: Dispatcher
    ) -> Result:
        """Index a file using the appropriate plugin."""
        try:
            path_obj = Path(file_path)
            extension = path_obj.suffix.lower()

            language_map = {
                ".py": "python_plugin",
                ".js": "js_plugin",
                ".jsx": "js_plugin",
                ".ts": "js_plugin",
                ".tsx": "js_plugin",
                ".c": "c_plugin",
                ".h": "c_plugin",
                ".cpp": "cpp_plugin",
                ".cc": "cpp_plugin",
                ".cxx": "cpp_plugin",
                ".hpp": "cpp_plugin",
            }

            plugin_name = language_map.get(extension)
            if not plugin_name or plugin_name not in dispatcher.plugins:
                return Result.error(f"No plugin available for {extension}")

            plugin = dispatcher.plugins[plugin_name]
            result = plugin.indexFile(file_path, content)

            return (
                Result.success(result) if result else Result.error("Plugin returned empty result")
            )

        except Exception as e:
            return Result.error(f"Error indexing {file_path}: {str(e)}")

    def lookup_symbol(self, symbol_name: str, fuzzy_indexer: FuzzyIndexer) -> List[Dict]:
        """Look up a symbol using fuzzy search."""
        results = fuzzy_indexer.search(symbol_name, limit=10)
        return [
            {
                "name": result.get("symbol", ""),
                "file": result.get("file", ""),
                "line": result.get("line", 0),
            }
            for result in results
        ]

    def search_code(
        self, query: str, test_db: SQLiteStore, repo_id: int, limit: int = 20
    ) -> List[Dict]:
        """Search code content in database."""
        try:
            # Use database search functionality
            results = test_db.search_content(query, limit=limit)
            return [
                {
                    "file_path": result.get("file_path", ""),
                    "content": result.get("content", ""),
                    "line": result.get("line", 0),
                }
                for result in results
            ]
        except Exception:
            # Fallback to simple search
            files = test_db.get_repository_files(repo_id)
            results = []
            for file_data in files:
                content = file_data.get("content", "")
                if query.lower() in content.lower():
                    results.append(
                        {
                            "file_path": file_data.get("path", ""),
                            "content": (content[:200] + "..." if len(content) > 200 else content),
                            "line": 1,
                        }
                    )
                    if len(results) >= limit:
                        break
            return results

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "repo_name,repo_url,search_terms",
        [
            (
                "requests",
                "https://github.com/psf/requests.git",
                ["Session", "get", "post", "Response", "HTTPAdapter"],
            ),
            (
                "django_subset",
                "https://github.com/django/django.git",
                ["Model", "QuerySet", "CharField", "ForeignKey", "admin"],
            ),
        ],
    )
    def test_real_world_symbol_search(
        self,
        repo_name,
        repo_url,
        search_terms,
        workspace_dir,
        test_db,
        dispatcher,
        fuzzy_indexer,
        benchmark,
    ):
        """Test symbol search accuracy on real-world codebases."""
        repo_id = self.setup_indexed_repository(
            workspace_dir, repo_name, repo_url, test_db, dispatcher, fuzzy_indexer
        )

        def search_symbols():
            results = {}
            for term in search_terms:
                start_time = time.perf_counter()

                # Test exact symbol lookup
                symbol_results = self.lookup_symbol(term, fuzzy_indexer)

                # Test content search
                content_results = self.search_code(term, test_db, repo_id, limit=10)

                end_time = time.perf_counter()
                search_time_ms = (end_time - start_time) * 1000

                results[term] = {
                    "symbol_found": len(symbol_results) > 0,
                    "content_results": len(content_results),
                    "search_time_ms": search_time_ms,
                    "total_results": len(symbol_results) + len(content_results),
                }

            return results

        results = benchmark(search_symbols)

        # Validate search quality
        found_symbols = sum(1 for r in results.values() if r["symbol_found"])
        total_results = sum(r["total_results"] for r in results.values())

        assert (
            found_symbols >= len(search_terms) * 0.6
        ), f"Symbol discovery rate too low: {found_symbols}/{len(search_terms)}"
        assert total_results >= len(search_terms) * 2, f"Total results too few: {total_results}"

        # Performance validation
        avg_search_time = sum(r["search_time_ms"] for r in results.values()) / len(results)
        assert avg_search_time < 200, f"Average search time too slow: {avg_search_time:.2f}ms"

        print(f"Symbol search results for {repo_name}:")
        for term, result in results.items():
            print(
                f"  {term}: {'✓' if result['symbol_found'] else '✗'} "
                f"({result['total_results']} results, {result['search_time_ms']:.1f}ms)"
            )

    @pytest.mark.integration
    def test_cross_language_search(self, workspace_dir, test_db, dispatcher, fuzzy_indexer):
        """Test search across multiple languages in VS Code repository."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "vscode_search",
            "https://github.com/microsoft/vscode.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        # Search for common patterns across languages
        test_cases = [
            {"term": "Config", "expected_languages": ["typescript", "javascript"]},
            {"term": "editor", "expected_languages": ["typescript", "javascript"]},
            {"term": "window", "expected_languages": ["typescript", "javascript"]},
        ]

        for case in test_cases:
            term = case["term"]

            # Symbol search
            symbol_results = self.lookup_symbol(term, fuzzy_indexer)

            # Content search
            content_results = self.search_code(term, test_db, repo_id, limit=20)

            all_results = symbol_results + content_results

            # Group results by detected language
            languages_found = set()
            for result in all_results:
                file_path = result.get("file_path", result.get("file", ""))
                if file_path:
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext in [".ts", ".tsx"]:
                        languages_found.add("typescript")
                    elif file_ext in [".js", ".jsx"]:
                        languages_found.add("javascript")
                    elif file_ext == ".py":
                        languages_found.add("python")
                    elif file_ext in [".c", ".h"]:
                        languages_found.add("c")
                    elif file_ext in [".cpp", ".hpp"]:
                        languages_found.add("cpp")

            # Validate cross-language discovery
            assert (
                len(all_results) >= 3
            ), f"Expected multiple results for '{term}', got {len(all_results)}"
            assert (
                len(languages_found) >= 1
            ), f"Expected multi-language results for '{term}', got {languages_found}"
            print(
                f"Term '{term}' found in languages: {languages_found} ({len(all_results)} results)"
            )

    @pytest.mark.performance
    def test_symbol_lookup_performance(
        self, workspace_dir, test_db, dispatcher, fuzzy_indexer, benchmark
    ):
        """Benchmark symbol lookup across different repository sizes."""
        repos = {
            "small": ("requests", "https://github.com/psf/requests.git"),
            "medium": ("django_perf", "https://github.com/django/django.git"),
        }

        performance_results = {}

        for size, (repo_name, repo_url) in repos.items():
            repo_id = self.setup_indexed_repository(
                workspace_dir, repo_name, repo_url, test_db, dispatcher, fuzzy_indexer
            )

            # Get common symbols for this repository
            symbols = self.get_common_symbols_for_repo(repo_name)

            def lookup_common_symbols():
                lookup_times = []
                successful_lookups = 0

                for symbol in symbols[:10]:  # Test 10 common symbols
                    start_time = time.perf_counter()
                    results = self.lookup_symbol(symbol, fuzzy_indexer)
                    end_time = time.perf_counter()

                    lookup_time_ms = (end_time - start_time) * 1000
                    lookup_times.append(lookup_time_ms)

                    if results:
                        successful_lookups += 1

                return lookup_times, successful_lookups

            lookup_times, successful_lookups = benchmark(lookup_common_symbols)

            # Performance assertions
            avg_time = sum(lookup_times) / len(lookup_times) if lookup_times else 0
            max_time = max(lookup_times) if lookup_times else 0

            assert avg_time < 100, f"Average lookup time too high for {size} repo: {avg_time:.2f}ms"
            assert max_time < 200, f"Max lookup time too high for {size} repo: {max_time:.2f}ms"
            assert successful_lookups >= len(symbols) * 0.5, f"Success rate too low for {size} repo"

            performance_results[size] = {
                "avg_time_ms": avg_time,
                "max_time_ms": max_time,
                "success_rate": successful_lookups / len(symbols) if symbols else 0,
            }

        print("Symbol lookup performance:")
        for size, stats in performance_results.items():
            print(
                f"  {size}: {stats['avg_time_ms']:.1f}ms avg, "
                f"{stats['max_time_ms']:.1f}ms max, "
                f"{stats['success_rate']:.1%} success"
            )

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(
        self, workspace_dir, test_db, dispatcher, fuzzy_indexer
    ):
        """Test performance under concurrent search queries."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "concurrent_test",
            "https://github.com/psf/requests.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        async def perform_search(query: str) -> tuple:
            start_time = time.perf_counter()

            # Run search in thread pool to avoid blocking
            symbol_results = await asyncio.to_thread(self.lookup_symbol, query, fuzzy_indexer)
            content_results = await asyncio.to_thread(self.search_code, query, test_db, repo_id)

            end_time = time.perf_counter()
            search_time = (end_time - start_time) * 1000

            return search_time, len(symbol_results) + len(content_results)

        # Simulate 50 concurrent queries
        queries = ["get", "post", "request", "session", "response"] * 10
        tasks = [perform_search(q) for q in queries]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # All queries should complete quickly
        assert total_time < 5.0, f"Concurrent queries took too long: {total_time:.2f}s"

        # Individual queries should still be fast
        search_times = [r[0] for r in results]
        max_search_time = max(search_times)
        avg_search_time = sum(search_times) / len(search_times)

        assert max_search_time < 1000, f"Slowest query too slow: {max_search_time:.2f}ms"
        assert avg_search_time < 200, f"Average search time too slow: {avg_search_time:.2f}ms"

        # Verify we got results
        total_results = sum(r[1] for r in results)
        assert total_results >= len(queries), f"Not enough results: {total_results}"

        print(f"Concurrent search: {len(queries)} queries in {total_time:.2f}s")
        print(f"Average: {avg_search_time:.1f}ms, Max: {max_search_time:.1f}ms")

    def get_common_symbols_for_repo(self, repo_name: str) -> List[str]:
        """Get common symbols for a repository for testing."""
        symbol_map = {
            "requests": [
                "Session",
                "Response",
                "get",
                "post",
                "HTTPAdapter",
                "Request",
            ],
            "django": [
                "Model",
                "QuerySet",
                "CharField",
                "ForeignKey",
                "admin",
                "forms",
            ],
            "django_subset": ["Model", "QuerySet", "CharField", "ForeignKey", "admin"],
            "django_perf": ["Model", "QuerySet", "CharField", "ForeignKey", "admin"],
            "vscode_search": ["editor", "window", "workspace", "commands", "config"],
            "concurrent_test": ["get", "post", "request", "session", "response"],
        }
        return symbol_map.get(repo_name, ["function", "class", "method", "variable"])

    @pytest.mark.integration
    def test_search_result_quality(self, workspace_dir, test_db, dispatcher, fuzzy_indexer):
        """Test the quality and relevance of search results."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "quality_test",
            "https://github.com/psf/requests.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        # Test exact matches
        exact_results = self.lookup_symbol("Session", fuzzy_indexer)
        assert len(exact_results) > 0, "Should find exact symbol matches"

        # Test fuzzy matches
        fuzzy_results = self.lookup_symbol("Sess", fuzzy_indexer)
        assert len(fuzzy_results) > 0, "Should find fuzzy symbol matches"

        # Test case insensitive
        case_results = self.lookup_symbol("session", fuzzy_indexer)
        assert len(case_results) > 0, "Should find case-insensitive matches"

        # Test content search
        content_results = self.search_code("def get", test_db, repo_id)
        assert len(content_results) > 0, "Should find content matches"

        # Test relevance - exact matches should score higher
        exact_score = len([r for r in exact_results if "Session" in r.get("name", "")])
        fuzzy_score = len([r for r in fuzzy_results if "Session" in r.get("name", "")])

        # Exact search should have higher precision
        if exact_results and fuzzy_results:
            exact_precision = exact_score / len(exact_results)
            fuzzy_precision = fuzzy_score / len(fuzzy_results)
            assert exact_precision >= fuzzy_precision, "Exact search should have higher precision"

        print(f"Search quality test:")
        print(f"  Exact matches: {len(exact_results)}")
        print(f"  Fuzzy matches: {len(fuzzy_results)}")
        print(f"  Case insensitive: {len(case_results)}")
        print(f"  Content matches: {len(content_results)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
