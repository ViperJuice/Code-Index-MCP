#!/usr/bin/env python3
"""
Real-world performance scaling tests for Code-Index-MCP.
Tests how performance scales with repository size and complexity.
"""

import asyncio
import os
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import psutil
import pytest

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestPerformanceScaling:
    """Test performance scaling with different repository sizes and complexities."""

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

    def create_file_subset(
        self, repo_path: Path, max_files: int, extensions: List[str] = None
    ) -> List[Path]:
        """Create a subset of files from a repository for testing."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp"]

        all_files = []
        for ext in extensions:
            all_files.extend(repo_path.rglob(f"*{ext}"))

        # Filter out very large files and sort by size (smallest first)
        filtered_files = []
        for f in all_files:
            try:
                if f.is_file() and f.stat().st_size < 1024 * 1024:  # < 1MB
                    filtered_files.append(f)
            except OSError:
                continue

        # Sort by size to get consistent subsets
        filtered_files.sort(key=lambda f: f.stat().st_size)

        return filtered_files[:max_files]

    def measure_indexing_performance(
        self,
        files: List[Path],
        repo_path: Path,
        test_db: SQLiteStore,
        dispatcher: Dispatcher,
    ) -> Dict[str, Any]:
        """Measure indexing performance for a set of files."""
        repo_id = test_db.create_repository(str(repo_path), repo_path.name, {"type": "perf_test"})

        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        indexed_files = 0
        total_symbols = 0
        total_lines = 0
        total_chars = 0
        errors = 0

        file_times = []

        for file_path in files:
            try:
                file_start = time.perf_counter()
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                if len(content.strip()) == 0:
                    continue

                lines = len(content.splitlines())
                chars = len(content)

                result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                if result.success:
                    symbols = result.value.get("symbols", [])

                    # Store in database
                    file_id = test_db.store_file(
                        repo_id,
                        str(file_path.relative_to(repo_path)),
                        content,
                        file_path.suffix[1:],
                        file_path.stat().st_mtime,
                    )

                    for symbol in symbols:
                        test_db.store_symbol(
                            file_id,
                            symbol.get("name", ""),
                            symbol.get("type", ""),
                            symbol.get("line", 0),
                            symbol.get("line", 0),
                            symbol.get("column", 0),
                            symbol.get("column", 0),
                            symbol.get("definition", ""),
                        )

                    indexed_files += 1
                    total_symbols += len(symbols)
                    total_lines += lines
                    total_chars += chars
                else:
                    errors += 1

                file_end = time.perf_counter()
                file_times.append((file_end - file_start) * 1000)  # ms

            except Exception:
                errors += 1

        end_time = time.perf_counter()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        total_time = end_time - start_time
        memory_increase = end_memory - start_memory

        return {
            "total_time_s": total_time,
            "indexed_files": indexed_files,
            "total_symbols": total_symbols,
            "total_lines": total_lines,
            "total_chars": total_chars,
            "errors": errors,
            "memory_increase_mb": memory_increase,
            "files_per_second": indexed_files / total_time if total_time > 0 else 0,
            "lines_per_second": total_lines / total_time if total_time > 0 else 0,
            "chars_per_second": total_chars / total_time if total_time > 0 else 0,
            "symbols_per_second": total_symbols / total_time if total_time > 0 else 0,
            "avg_file_time_ms": statistics.mean(file_times) if file_times else 0,
            "max_file_time_ms": max(file_times) if file_times else 0,
            "success_rate": (
                indexed_files / (indexed_files + errors) if (indexed_files + errors) > 0 else 0
            ),
        }

    @pytest.mark.performance
    def test_indexing_performance_scaling(self, workspace_dir, test_db, dispatcher, benchmark):
        """Test how indexing performance scales with repository size."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "django_scaling", "https://github.com/django/django.git"
        )

        # Test different repository sizes
        test_sizes = [50, 100, 200, 500, 1000]
        results = {}

        for size in test_sizes:
            print(f"Testing indexing performance with {size} files...")

            files = self.create_file_subset(repo_path, size)
            if len(files) < size:
                print(f"Only found {len(files)} files, adjusting test size")
                size = len(files)

            # Create fresh database for each test
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                test_db_path = f.name

            test_store = SQLiteStore(test_db_path)

            try:
                perf_data = self.measure_indexing_performance(
                    files[:size], repo_path, test_store, dispatcher
                )

                results[size] = perf_data

                # Basic performance assertions
                assert (
                    perf_data["success_rate"] >= 0.8
                ), f"Success rate too low: {perf_data['success_rate']:.2%}"
                assert (
                    perf_data["files_per_second"] >= 1
                ), f"Indexing too slow: {perf_data['files_per_second']:.2f} files/s"
                assert (
                    perf_data["memory_increase_mb"] < 200
                ), f"Memory usage too high: {perf_data['memory_increase_mb']:.1f}MB"

            finally:
                try:
                    os.unlink(test_db_path)
                except OSError:
                    pass

        # Analyze scaling characteristics
        sizes = sorted(results.keys())
        throughputs = [results[s]["files_per_second"] for s in sizes]
        memory_usage = [results[s]["memory_increase_mb"] for s in sizes]

        print("\nIndexing Performance Scaling:")
        for size in sizes:
            r = results[size]
            print(
                f"  {size:4d} files: {r['files_per_second']:5.1f} files/s, "
                f"{r['symbols_per_second']:6.0f} symbols/s, "
                f"{r['memory_increase_mb']:5.1f}MB, "
                f"{r['success_rate']:5.1%} success"
            )

        # Check for reasonable scaling
        if len(sizes) >= 3:
            # Throughput should not degrade too much with size
            min_throughput = min(throughputs)
            max_throughput = max(throughputs)
            throughput_degradation = (max_throughput - min_throughput) / max_throughput
            assert (
                throughput_degradation < 0.5
            ), f"Throughput degrades too much: {throughput_degradation:.1%}"

            # Memory usage should scale roughly linearly
            memory_per_file_ratios = [memory_usage[i] / sizes[i] for i in range(len(sizes))]
            memory_variance = statistics.stdev(memory_per_file_ratios) / statistics.mean(
                memory_per_file_ratios
            )
            assert memory_variance < 1.0, f"Memory scaling too inconsistent: {memory_variance:.2f}"

    @pytest.mark.performance
    def test_search_performance_scaling(
        self, workspace_dir, test_db, dispatcher, fuzzy_indexer, benchmark
    ):
        """Test how search performance scales with index size."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "search_scaling", "https://github.com/django/django.git"
        )

        # Build progressively larger indices
        file_sizes = [100, 300, 500, 1000]
        search_results = {}

        for size in file_sizes:
            print(f"Testing search performance with {size} files indexed...")

            files = self.create_file_subset(repo_path, size)
            if len(files) < size:
                size = len(files)

            # Create fresh database and indexer
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                test_db_path = f.name

            test_store = SQLiteStore(test_db_path)
            test_fuzzy = FuzzyIndexer()

            try:
                # Index files
                repo_id = test_store.create_repository(
                    str(repo_path), repo_path.name, {"type": "search_test"}
                )

                for file_path in files:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(content.strip()) == 0:
                            continue

                        result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                        if result.success:
                            symbols = result.value.get("symbols", [])

                            for symbol in symbols:
                                symbol_name = symbol.get("name", "")
                                if symbol_name:
                                    test_fuzzy.add_symbol(
                                        symbol_name,
                                        str(file_path.relative_to(repo_path)),
                                        symbol.get("line", 0),
                                    )
                    except Exception:
                        continue

                # Test search performance
                search_terms = [
                    "Model",
                    "view",
                    "admin",
                    "form",
                    "test",
                    "get",
                    "post",
                    "save",
                    "delete",
                    "query",
                ]

                def run_search_suite():
                    search_times = []
                    result_counts = []

                    for term in search_terms:
                        start_time = time.perf_counter()
                        results = test_fuzzy.search(term, limit=20)
                        end_time = time.perf_counter()

                        search_time_ms = (end_time - start_time) * 1000
                        search_times.append(search_time_ms)
                        result_counts.append(len(results))

                    return search_times, result_counts

                search_times, result_counts = benchmark(run_search_suite)

                avg_search_time = statistics.mean(search_times)
                max_search_time = max(search_times)
                avg_results = statistics.mean(result_counts)

                search_results[size] = {
                    "avg_search_time_ms": avg_search_time,
                    "max_search_time_ms": max_search_time,
                    "avg_results": avg_results,
                    "total_queries": len(search_terms),
                }

                # Performance assertions
                assert avg_search_time < 50, f"Average search too slow: {avg_search_time:.2f}ms"
                assert max_search_time < 200, f"Slowest search too slow: {max_search_time:.2f}ms"

            finally:
                try:
                    os.unlink(test_db_path)
                except OSError:
                    pass

        # Analyze search scaling
        sizes = sorted(search_results.keys())
        avg_times = [search_results[s]["avg_search_time_ms"] for s in sizes]
        max_times = [search_results[s]["max_search_time_ms"] for s in sizes]

        print("\nSearch Performance Scaling:")
        for size in sizes:
            r = search_results[size]
            print(
                f"  {size:4d} files: {r['avg_search_time_ms']:5.1f}ms avg, "
                f"{r['max_search_time_ms']:5.1f}ms max, "
                f"{r['avg_results']:4.1f} avg results"
            )

        # Check scaling characteristics
        if len(sizes) >= 3:
            # Search time should not increase too much with index size
            time_increase_ratio = max(avg_times) / min(avg_times)
            assert (
                time_increase_ratio < 3.0
            ), f"Search time increases too much: {time_increase_ratio:.1f}x"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_codebase_performance(self, workspace_dir, test_db, dispatcher, benchmark):
        """Test performance on a large codebase subset."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "linux_subset", "https://github.com/torvalds/linux.git"
        )

        # Create a substantial subset for testing
        c_files = self.create_file_subset(repo_path, 2000, [".c", ".h"])
        print(f"Testing with {len(c_files)} C files from Linux kernel")

        def index_large_codebase():
            return self.measure_indexing_performance(c_files, repo_path, test_db, dispatcher)

        perf_data = benchmark(index_large_codebase)

        # Validate large codebase performance
        assert (
            perf_data["indexed_files"] >= len(c_files) * 0.8
        ), f"Should index most files: {perf_data['indexed_files']}/{len(c_files)}"
        assert (
            perf_data["total_symbols"] >= 10000
        ), f"Should extract many symbols: {perf_data['total_symbols']}"
        assert (
            perf_data["success_rate"] >= 0.85
        ), f"Success rate too low: {perf_data['success_rate']:.2%}"
        assert (
            perf_data["memory_increase_mb"] < 500
        ), f"Memory usage too high: {perf_data['memory_increase_mb']:.1f}MB"
        assert (
            perf_data["files_per_second"] >= 5
        ), f"Throughput too low: {perf_data['files_per_second']:.1f} files/s"

        print("\nLarge Codebase Performance:")
        print(
            f"  Files indexed: {perf_data['indexed_files']} ({perf_data['success_rate']:.1%} success)"
        )
        print(f"  Symbols extracted: {perf_data['total_symbols']}")
        print(f"  Total time: {perf_data['total_time_s']:.1f}s")
        print(
            f"  Throughput: {perf_data['files_per_second']:.1f} files/s, {perf_data['symbols_per_second']:.0f} symbols/s"
        )
        print(f"  Memory usage: {perf_data['memory_increase_mb']:.1f}MB")
        print(f"  Avg file time: {perf_data['avg_file_time_ms']:.1f}ms")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_indexing_scaling(self, workspace_dir, dispatcher):
        """Test how concurrent indexing scales with worker count."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "concurrent_scaling", "https://github.com/psf/requests.git"
        )

        files = self.create_file_subset(repo_path, 100, [".py"])
        print(f"Testing concurrent indexing with {len(files)} files")

        async def index_file_async(file_path: Path) -> Dict[str, Any]:
            """Index a single file asynchronously."""
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content.strip()) == 0:
                    return {"success": False, "reason": "empty"}

                start_time = time.perf_counter()
                result = await asyncio.to_thread(
                    self.index_file_with_plugin, str(file_path), content, dispatcher
                )
                end_time = time.perf_counter()

                if result.success:
                    symbols = result.value.get("symbols", [])
                    return {
                        "success": True,
                        "symbols": len(symbols),
                        "time_ms": (end_time - start_time) * 1000,
                        "lines": len(content.splitlines()),
                        "chars": len(content),
                    }
                else:
                    return {"success": False, "reason": result.error}
            except Exception as e:
                return {"success": False, "reason": str(e)}

        # Test different concurrency levels
        concurrency_levels = [1, 2, 4, 8]
        scaling_results = {}

        for max_concurrent in concurrency_levels:
            print(f"Testing with max {max_concurrent} concurrent workers...")

            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_index(file_path: Path):
                async with semaphore:
                    return await index_file_async(file_path)

            start_time = time.perf_counter()
            results = await asyncio.gather(*[limited_index(f) for f in files[:50]])
            end_time = time.perf_counter()

            total_time = end_time - start_time
            successful = [r for r in results if r.get("success", False)]

            scaling_results[max_concurrent] = {
                "total_time_s": total_time,
                "successful_files": len(successful),
                "total_symbols": sum(r.get("symbols", 0) for r in successful),
                "files_per_second": (len(successful) / total_time if total_time > 0 else 0),
                "success_rate": len(successful) / len(results) if results else 0,
            }

            # Validate concurrent performance
            assert (
                len(successful) >= len(files[:50]) * 0.8
            ), f"Too many failures with {max_concurrent} workers"
            assert total_time < 60, f"Concurrent indexing too slow: {total_time:.1f}s"

        # Analyze scaling efficiency
        print("\nConcurrent Indexing Scaling:")
        for workers, result in scaling_results.items():
            print(
                f"  {workers:2d} workers: {result['files_per_second']:5.1f} files/s, "
                f"{result['total_time_s']:5.1f}s total, "
                f"{result['success_rate']:5.1%} success"
            )

        # Check if concurrency improves performance
        sequential_throughput = scaling_results[1]["files_per_second"]
        best_concurrent_throughput = max(
            scaling_results[w]["files_per_second"] for w in concurrency_levels if w > 1
        )

        speedup = best_concurrent_throughput / sequential_throughput
        assert speedup >= 1.5, f"Concurrent indexing should provide speedup: {speedup:.1f}x"

        print(f"\nBest speedup: {speedup:.1f}x over sequential processing")

    @pytest.mark.performance
    def test_memory_scaling_characteristics(self, workspace_dir, dispatcher):
        """Test how memory usage scales with different workload characteristics."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "memory_scaling", "https://github.com/django/django.git"
        )

        # Test different file size distributions
        all_files = self.create_file_subset(repo_path, 1000, [".py"])

        # Sort files by size
        all_files.sort(key=lambda f: f.stat().st_size)

        test_scenarios = {
            "small_files": all_files[:100],  # Smallest files
            "medium_files": all_files[400:500],  # Medium-sized files
            "large_files": all_files[-50:],  # Largest files
            "mixed_files": all_files[::10][:100],  # Mixed distribution
        }

        memory_results = {}

        for scenario, files in test_scenarios.items():
            print(f"Testing memory scaling for {scenario}...")

            # Create fresh database for each test
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                test_db_path = f.name

            test_store = SQLiteStore(test_db_path)

            try:
                perf_data = self.measure_indexing_performance(
                    files, repo_path, test_store, dispatcher
                )

                # Calculate file size statistics
                file_sizes = [f.stat().st_size for f in files]
                avg_file_size = statistics.mean(file_sizes)
                total_file_size = sum(file_sizes)

                memory_results[scenario] = {
                    "memory_increase_mb": perf_data["memory_increase_mb"],
                    "indexed_files": perf_data["indexed_files"],
                    "total_symbols": perf_data["total_symbols"],
                    "avg_file_size_kb": avg_file_size / 1024,
                    "total_file_size_mb": total_file_size / (1024 * 1024),
                    "memory_per_file_kb": (
                        (perf_data["memory_increase_mb"] * 1024) / perf_data["indexed_files"]
                        if perf_data["indexed_files"] > 0
                        else 0
                    ),
                    "memory_per_symbol_bytes": (
                        (perf_data["memory_increase_mb"] * 1024 * 1024) / perf_data["total_symbols"]
                        if perf_data["total_symbols"] > 0
                        else 0
                    ),
                }

            finally:
                try:
                    os.unlink(test_db_path)
                except OSError:
                    pass

        print("\nMemory Scaling by File Characteristics:")
        for scenario, result in memory_results.items():
            print(
                f"  {scenario:12s}: {result['memory_increase_mb']:5.1f}MB total, "
                f"{result['memory_per_file_kb']:5.1f}KB/file, "
                f"{result['memory_per_symbol_bytes']:6.0f}B/symbol"
            )

        # Validate memory efficiency
        for scenario, result in memory_results.items():
            assert (
                result["memory_increase_mb"] < 100
            ), f"{scenario}: Memory usage too high: {result['memory_increase_mb']:.1f}MB"
            assert (
                result["memory_per_file_kb"] < 500
            ), f"{scenario}: Memory per file too high: {result['memory_per_file_kb']:.1f}KB"
            assert (
                result["memory_per_symbol_bytes"] < 1000
            ), f"{scenario}: Memory per symbol too high: {result['memory_per_symbol_bytes']:.0f}B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
