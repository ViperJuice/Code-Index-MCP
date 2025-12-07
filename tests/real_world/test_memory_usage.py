#!/usr/bin/env python3
"""
Real-world memory usage tests for Code-Index-MCP.
Tests memory efficiency and leak detection during indexing operations.
"""

import gc
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import pytest
from memory_profiler import memory_usage

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestMemoryUsage:
    """Test memory usage patterns and efficiency during real-world operations."""

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

    def get_memory_info(self) -> Dict[str, float]:
        """Get current memory information in MB."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }

    @pytest.mark.performance
    @pytest.mark.memory
    def test_memory_usage_large_codebase(self, workspace_dir, test_db, dispatcher):
        """Test memory usage during large codebase indexing."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "linux_memory", "https://github.com/torvalds/linux.git"
        )

        # Get C files for testing (limit to reasonable number)
        c_files = list(repo_path.rglob("*.c"))[:2000]
        print(f"Testing memory usage with {len(c_files)} C files from Linux kernel")

        initial_memory = self.get_memory_info()
        print(f"Initial memory: {initial_memory['rss_mb']:.1f}MB RSS")

        repo_id = test_db.create_repository(
            str(repo_path), "linux_memory_test", {"type": "memory_test"}
        )

        indexed_count = 0
        memory_samples = [initial_memory["rss_mb"]]
        peak_memory = initial_memory["rss_mb"]

        for i, file_path in enumerate(c_files):
            try:
                # Skip very large files to focus on memory patterns
                if file_path.stat().st_size > 1024 * 1024:  # 1MB
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content.strip()) == 0:
                    continue

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

                    indexed_count += 1

                # Sample memory every 50 files
                if i % 50 == 0:
                    current_memory = self.get_memory_info()
                    memory_samples.append(current_memory["rss_mb"])
                    peak_memory = max(peak_memory, current_memory["rss_mb"])

                    # Force garbage collection periodically
                    if i % 200 == 0:
                        gc.collect()

            except Exception as e:
                continue

        final_memory = self.get_memory_info()
        memory_increase = final_memory["rss_mb"] - initial_memory["rss_mb"]
        peak_increase = peak_memory - initial_memory["rss_mb"]

        print(f"\nMemory Usage Results:")
        print(f"  Files indexed: {indexed_count}")
        print(f"  Initial memory: {initial_memory['rss_mb']:.1f}MB")
        print(f"  Final memory: {final_memory['rss_mb']:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(f"  Memory increase: {memory_increase:.1f}MB")
        print(f"  Peak increase: {peak_increase:.1f}MB")
        print(
            f"  Memory per file: {memory_increase / indexed_count * 1024:.1f}KB"
            if indexed_count > 0
            else "  N/A"
        )

        # Memory usage assertions
        assert memory_increase < 1000, f"Memory increase too high: {memory_increase:.1f}MB"
        assert peak_increase < 1500, f"Peak memory usage too high: {peak_increase:.1f}MB"
        assert (
            indexed_count >= len(c_files) * 0.7
        ), f"Should index most files: {indexed_count}/{len(c_files)}"

        # Check for memory leaks (memory should not continuously grow)
        if len(memory_samples) > 4:
            # Compare early vs late samples
            early_avg = sum(memory_samples[1:3]) / 2
            late_avg = sum(memory_samples[-3:-1]) / 2
            growth_rate = (late_avg - early_avg) / len(memory_samples)

            assert (
                growth_rate < 5
            ), f"Possible memory leak detected: {growth_rate:.1f}MB/sample growth rate"

    @pytest.mark.performance
    @pytest.mark.memory
    def test_memory_leak_detection(self, workspace_dir, test_db, dispatcher):
        """Test for memory leaks during repeated indexing operations."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "leak_test", "https://github.com/psf/requests.git"
        )

        python_files = list(repo_path.rglob("*.py"))[:50]
        print(f"Testing memory leaks with {len(python_files)} Python files")

        initial_memory = self.get_memory_info()
        memory_samples = []

        # Perform repeated indexing cycles
        for cycle in range(5):
            cycle_start_memory = self.get_memory_info()
            print(f"\nCycle {cycle + 1}: Starting with {cycle_start_memory['rss_mb']:.1f}MB")

            repo_id = test_db.create_repository(
                str(repo_path), f"leak_test_cycle_{cycle}", {"type": "leak_test"}
            )

            indexed_count = 0
            for file_path in python_files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if len(content.strip()) == 0:
                        continue

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

                        indexed_count += 1

                except Exception:
                    continue

            # Force garbage collection after each cycle
            gc.collect()

            cycle_end_memory = self.get_memory_info()
            cycle_increase = cycle_end_memory["rss_mb"] - cycle_start_memory["rss_mb"]
            total_increase = cycle_end_memory["rss_mb"] - initial_memory["rss_mb"]

            memory_samples.append(
                {
                    "cycle": cycle,
                    "start_mb": cycle_start_memory["rss_mb"],
                    "end_mb": cycle_end_memory["rss_mb"],
                    "cycle_increase_mb": cycle_increase,
                    "total_increase_mb": total_increase,
                    "indexed_files": indexed_count,
                }
            )

            print(f"  Indexed {indexed_count} files")
            print(f"  Cycle memory increase: {cycle_increase:.1f}MB")
            print(f"  Total memory increase: {total_increase:.1f}MB")

            # Memory growth should stabilize after first few cycles
            if cycle > 2:
                assert (
                    cycle_increase < 30
                ), f"Cycle {cycle}: Memory increase too high: {cycle_increase:.1f}MB"
                assert (
                    total_increase < 100
                ), f"Cycle {cycle}: Total memory growth too high: {total_increase:.1f}MB"

        # Analyze memory growth pattern
        cycle_increases = [s["cycle_increase_mb"] for s in memory_samples]
        total_increases = [s["total_increase_mb"] for s in memory_samples]

        print(f"\nMemory Leak Analysis:")
        for sample in memory_samples:
            print(
                f"  Cycle {sample['cycle']}: +{sample['cycle_increase_mb']:.1f}MB "
                f"(total: +{sample['total_increase_mb']:.1f}MB)"
            )

        # Check for memory leaks
        final_memory_increase = memory_samples[-1]["total_increase_mb"]

        # Memory should stabilize (later cycles should not increase much)
        if len(memory_samples) >= 4:
            late_cycle_increases = cycle_increases[-2:]
            avg_late_increase = sum(late_cycle_increases) / len(late_cycle_increases)
            assert (
                avg_late_increase < 15
            ), f"Memory leak detected: avg late cycle increase {avg_late_increase:.1f}MB"

        assert (
            final_memory_increase < 80
        ), f"Total memory growth too high: {final_memory_increase:.1f}MB"

    @pytest.mark.performance
    @pytest.mark.memory
    def test_memory_efficiency_by_language(self, workspace_dir, test_db, dispatcher):
        """Test memory efficiency across different programming languages."""
        # Test multiple repositories for different languages
        test_repos = [
            ("python_memory", "https://github.com/psf/requests.git", [".py"], "Python"),
            (
                "js_memory",
                "https://github.com/facebook/react.git",
                [".js", ".jsx"],
                "JavaScript",
            ),
            (
                "cpp_memory",
                "https://github.com/microsoft/terminal.git",
                [".cpp", ".hpp"],
                "C++",
            ),
        ]

        language_results = {}

        for repo_name, repo_url, extensions, language in test_repos:
            print(f"\nTesting memory efficiency for {language}...")

            repo_path = self.ensure_repository_exists(workspace_dir, repo_name, repo_url)

            # Get files for this language
            files = []
            for ext in extensions:
                files.extend(list(repo_path.rglob(f"*{ext}"))[:100])  # Limit per language

            if not files:
                print(f"No {language} files found, skipping")
                continue

            # Create fresh database for each language test
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                test_db_path = f.name

            test_store = SQLiteStore(test_db_path)

            try:
                initial_memory = self.get_memory_info()

                repo_id = test_store.create_repository(
                    str(repo_path),
                    f"{repo_name}_efficiency",
                    {"type": "efficiency_test"},
                )

                indexed_count = 0
                total_symbols = 0
                total_lines = 0

                for file_path in files:
                    try:
                        if file_path.stat().st_size > 512 * 1024:  # Skip large files
                            continue

                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(content.strip()) == 0:
                            continue

                        result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                        if result.success:
                            symbols = result.value.get("symbols", [])

                            file_id = test_store.store_file(
                                repo_id,
                                str(file_path.relative_to(repo_path)),
                                content,
                                file_path.suffix[1:],
                                file_path.stat().st_mtime,
                            )

                            for symbol in symbols:
                                test_store.store_symbol(
                                    file_id,
                                    symbol.get("name", ""),
                                    symbol.get("type", ""),
                                    symbol.get("line", 0),
                                    symbol.get("line", 0),
                                    symbol.get("column", 0),
                                    symbol.get("column", 0),
                                    symbol.get("definition", ""),
                                )

                            indexed_count += 1
                            total_symbols += len(symbols)
                            total_lines += len(content.splitlines())

                    except Exception:
                        continue

                final_memory = self.get_memory_info()
                memory_increase = final_memory["rss_mb"] - initial_memory["rss_mb"]

                language_results[language] = {
                    "memory_increase_mb": memory_increase,
                    "indexed_files": indexed_count,
                    "total_symbols": total_symbols,
                    "total_lines": total_lines,
                    "memory_per_file_kb": (
                        (memory_increase * 1024) / indexed_count if indexed_count > 0 else 0
                    ),
                    "memory_per_symbol_bytes": (
                        (memory_increase * 1024 * 1024) / total_symbols if total_symbols > 0 else 0
                    ),
                    "memory_per_line_bytes": (
                        (memory_increase * 1024 * 1024) / total_lines if total_lines > 0 else 0
                    ),
                }

            finally:
                try:
                    os.unlink(test_db_path)
                except OSError:
                    pass

        print(f"\nMemory Efficiency by Language:")
        for language, result in language_results.items():
            print(
                f"  {language:10s}: {result['memory_increase_mb']:5.1f}MB total, "
                f"{result['memory_per_file_kb']:5.1f}KB/file, "
                f"{result['memory_per_symbol_bytes']:6.0f}B/symbol"
            )

            # Language-specific assertions
            assert (
                result["memory_increase_mb"] < 50
            ), f"{language}: Memory usage too high: {result['memory_increase_mb']:.1f}MB"
            assert (
                result["memory_per_file_kb"] < 200
            ), f"{language}: Memory per file too high: {result['memory_per_file_kb']:.1f}KB"
            assert (
                result["indexed_files"] >= len(files) * 0.7
            ), f"{language}: Should index most files"

    @pytest.mark.performance
    @pytest.mark.memory
    def test_memory_usage_with_profiler(self, workspace_dir, dispatcher):
        """Test memory usage using memory_profiler for detailed analysis."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "profiler_test", "https://github.com/psf/requests.git"
        )

        python_files = list(repo_path.rglob("*.py"))[:30]
        print(f"Profiling memory usage with {len(python_files)} Python files")

        def index_files_for_profiling():
            """Function to profile memory usage during indexing."""
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                db_path = f.name

            try:
                store = SQLiteStore(db_path)
                repo_id = store.create_repository(
                    str(repo_path), "profiler_test", {"type": "profile_test"}
                )

                indexed_count = 0
                for file_path in python_files:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(content.strip()) == 0:
                            continue

                        result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                        if result.success:
                            symbols = result.value.get("symbols", [])

                            file_id = store.store_file(
                                repo_id,
                                str(file_path.relative_to(repo_path)),
                                content,
                                file_path.suffix[1:],
                                file_path.stat().st_mtime,
                            )

                            for symbol in symbols:
                                store.store_symbol(
                                    file_id,
                                    symbol.get("name", ""),
                                    symbol.get("type", ""),
                                    symbol.get("line", 0),
                                    symbol.get("line", 0),
                                    symbol.get("column", 0),
                                    symbol.get("column", 0),
                                    symbol.get("definition", ""),
                                )

                            indexed_count += 1

                    except Exception:
                        continue

                return indexed_count

            finally:
                try:
                    os.unlink(db_path)
                except OSError:
                    pass

        # Profile memory usage
        mem_usage = memory_usage(index_files_for_profiling, interval=0.1)

        # Analyze memory profile
        min_memory = min(mem_usage)
        max_memory = max(mem_usage)
        avg_memory = sum(mem_usage) / len(mem_usage)
        memory_range = max_memory - min_memory

        print(f"\nMemory Profile Analysis:")
        print(f"  Minimum memory: {min_memory:.1f}MB")
        print(f"  Maximum memory: {max_memory:.1f}MB")
        print(f"  Average memory: {avg_memory:.1f}MB")
        print(f"  Memory range: {memory_range:.1f}MB")
        print(f"  Samples taken: {len(mem_usage)}")

        # Memory profile assertions
        assert memory_range < 100, f"Memory usage range too high: {memory_range:.1f}MB"
        assert (
            max_memory < min_memory + 80
        ), f"Peak memory usage too high: {max_memory:.1f}MB vs {min_memory:.1f}MB baseline"

        # Check for memory spikes (rapid increases)
        memory_deltas = [mem_usage[i] - mem_usage[i - 1] for i in range(1, len(mem_usage))]
        max_spike = max(memory_deltas) if memory_deltas else 0
        min_drop = min(memory_deltas) if memory_deltas else 0

        assert max_spike < 20, f"Memory spike too large: {max_spike:.1f}MB"
        print(f"  Largest memory spike: {max_spike:.1f}MB")
        print(f"  Largest memory drop: {min_drop:.1f}MB")

    @pytest.mark.performance
    @pytest.mark.memory
    def test_concurrent_memory_usage(self, workspace_dir, dispatcher):
        """Test memory usage under concurrent indexing operations."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "concurrent_memory", "https://github.com/psf/requests.git"
        )

        python_files = list(repo_path.rglob("*.py"))[:50]
        print(f"Testing concurrent memory usage with {len(python_files)} files")

        def index_files_concurrently():
            """Index files using multiple threads."""
            import queue
            import threading

            file_queue = queue.Queue()
            for f in python_files:
                file_queue.put(f)

            results = []
            errors = []

            def worker():
                with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                    db_path = f.name

                try:
                    store = SQLiteStore(db_path)
                    repo_id = store.create_repository(
                        str(repo_path),
                        f"concurrent_test_{threading.current_thread().ident}",
                        {"type": "concurrent_test"},
                    )

                    while True:
                        try:
                            file_path = file_queue.get_nowait()
                        except queue.Empty:
                            break

                        try:
                            content = file_path.read_text(encoding="utf-8", errors="ignore")
                            if len(content.strip()) == 0:
                                continue

                            result = self.index_file_with_plugin(
                                str(file_path), content, dispatcher
                            )
                            if result.success:
                                results.append(file_path)
                            else:
                                errors.append(file_path)

                        except Exception as e:
                            errors.append(file_path)
                        finally:
                            file_queue.task_done()

                finally:
                    try:
                        os.unlink(db_path)
                    except OSError:
                        pass

            # Start multiple worker threads
            threads = []
            for i in range(3):
                t = threading.Thread(target=worker)
                t.start()
                threads.append(t)

            # Wait for completion
            for t in threads:
                t.join()

            return len(results), len(errors)

        # Profile concurrent memory usage
        mem_usage = memory_usage(index_files_concurrently, interval=0.1)

        # Analyze concurrent memory profile
        min_memory = min(mem_usage)
        max_memory = max(mem_usage)
        memory_range = max_memory - min_memory

        print(f"\nConcurrent Memory Usage:")
        print(f"  Memory range: {memory_range:.1f}MB")
        print(f"  Peak memory: {max_memory:.1f}MB")
        print(f"  Baseline memory: {min_memory:.1f}MB")

        # Concurrent memory assertions
        assert memory_range < 150, f"Concurrent memory usage range too high: {memory_range:.1f}MB"
        assert max_memory < min_memory + 120, f"Concurrent peak memory too high: {max_memory:.1f}MB"

        print("Concurrent memory usage test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
