#!/usr/bin/env python3
"""
Real-world repository indexing tests for Code-Index-MCP.
Tests indexing performance and accuracy on actual GitHub repositories.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRepositoryIndexing:
    """Test indexing performance on real-world repositories."""

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
            # Detect language from file extension
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

    @pytest.mark.performance
    @pytest.mark.parametrize(
        "repo_name,repo_url,expected_files,expected_symbols",
        [
            ("requests", "https://github.com/psf/requests.git", 50, 500),
            ("terminal_subset", "https://github.com/microsoft/terminal.git", 200, 2000),
        ],
    )
    def test_small_repository_indexing(
        self,
        repo_name,
        repo_url,
        expected_files,
        expected_symbols,
        workspace_dir,
        test_db,
        dispatcher,
        benchmark,
    ):
        """Test indexing performance on small real-world repositories."""
        repo_path = self.ensure_repository_exists(workspace_dir, repo_name, repo_url)

        def index_repository():
            repo_id = test_db.create_repository(str(repo_path), repo_name, {"type": "test"})

            indexed_files = 0
            total_symbols = 0
            errors = []

            # Find relevant source files
            extensions = [".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp"]
            source_files = []
            for ext in extensions:
                source_files.extend(repo_path.rglob(f"*{ext}"))

            # Limit to reasonable number for testing
            source_files = source_files[:1000]

            for file_path in source_files:
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(content.strip()) == 0:
                            continue

                        result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                        if result.success:
                            indexed_files += 1
                            symbols = result.value.get("symbols", [])
                            total_symbols += len(symbols)

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
                        else:
                            errors.append(f"{file_path}: {result.error}")

                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")

            return indexed_files, total_symbols, len(errors)

        # Benchmark the indexing process
        result = benchmark(index_repository)
        indexed_files, total_symbols, error_count = result

        # Validate results
        assert (
            indexed_files >= expected_files * 0.6
        ), f"Expected at least {expected_files * 0.6} files, got {indexed_files}"
        assert (
            total_symbols >= expected_symbols * 0.6
        ), f"Expected at least {expected_symbols * 0.6} symbols, got {total_symbols}"
        assert error_count < indexed_files * 0.2, f"Too many errors: {error_count}/{indexed_files}"

        # Performance assertions
        assert benchmark.stats.mean < 60.0, f"Indexing took too long: {benchmark.stats.mean:.2f}s"

        print(f"Indexed {indexed_files} files with {total_symbols} symbols, {error_count} errors")
        print(f"Success rate: {(indexed_files / (indexed_files + error_count)) * 100:.1f}%")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_repository_indexing(self, workspace_dir, test_db, dispatcher, benchmark):
        """Test indexing performance on Django (large Python codebase)."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "django", "https://github.com/django/django.git"
        )

        def index_django():
            repo_id = test_db.create_repository(str(repo_path), "django", {"type": "large_test"})

            indexed_files = 0
            total_symbols = 0
            errors = []

            # Index only Python files to focus on our plugin
            python_files = list(repo_path.rglob("*.py"))
            print(f"Found {len(python_files)} Python files")

            # Limit to 1000 files for testing performance
            test_files = python_files[:1000]

            for file_path in test_files:
                try:
                    # Skip very large files
                    if file_path.stat().st_size > 1024 * 1024:  # 1MB
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if len(content.strip()) == 0:
                        continue

                    result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                    if result.success:
                        indexed_files += 1
                        symbols = result.value.get("symbols", [])
                        total_symbols += len(symbols)
                    else:
                        errors.append(f"{file_path}: {result.error}")

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            return indexed_files, total_symbols, len(errors)

        result = benchmark(index_django)
        indexed_files, total_symbols, error_count = result

        # Performance and quality assertions
        assert indexed_files >= 800, f"Should index most files successfully, got {indexed_files}"
        assert total_symbols >= 10000, f"Django should have many symbols, got {total_symbols}"
        assert (
            error_count < indexed_files * 0.1
        ), f"Error rate too high: {error_count}/{indexed_files}"
        assert benchmark.stats.mean < 180.0, f"Indexing took too long: {benchmark.stats.mean:.2f}s"

        print(
            f"Django indexing: {indexed_files} files, {total_symbols} symbols, {error_count} errors"
        )
        print(f"Rate: {indexed_files / benchmark.stats.mean:.1f} files/second")

    @pytest.mark.integration
    def test_multi_language_repository(self, workspace_dir, test_db, dispatcher):
        """Test indexing a multi-language repository like VS Code."""
        repo_path = self.ensure_repository_exists(
            workspace_dir, "vscode_subset", "https://github.com/microsoft/vscode.git"
        )

        repo_id = test_db.create_repository(
            str(repo_path), "vscode_subset", {"type": "multi_lang_test"}
        )

        language_stats = {}
        total_indexed = 0

        # Find files for each language
        language_extensions = {
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "python": [".py"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".hpp"],
        }

        for language, extensions in language_extensions.items():
            language_files = []
            for ext in extensions:
                language_files.extend(list(repo_path.rglob(f"*{ext}"))[:100])  # Limit per language

            indexed_count = 0
            symbol_count = 0

            for file_path in language_files:
                try:
                    if file_path.stat().st_size > 512 * 1024:  # Skip files > 512KB
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if len(content.strip()) == 0:
                        continue

                    result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                    if result.success:
                        indexed_count += 1
                        symbols = result.value.get("symbols", [])
                        symbol_count += len(symbols)

                except Exception:
                    continue

            language_stats[language] = {
                "files": len(language_files),
                "indexed": indexed_count,
                "symbols": symbol_count,
            }
            total_indexed += indexed_count

        # Validate multi-language support
        languages_with_results = [
            lang for lang, stats in language_stats.items() if stats["indexed"] > 0
        ]
        assert (
            len(languages_with_results) >= 2
        ), f"Should support multiple languages, got: {languages_with_results}"
        assert total_indexed >= 50, f"Should index reasonable number of files, got {total_indexed}"

        for language, stats in language_stats.items():
            if stats["files"] > 0:
                success_rate = stats["indexed"] / stats["files"]
                print(
                    f"{language}: {stats['indexed']}/{stats['files']} files ({success_rate:.1%}), {stats['symbols']} symbols"
                )

    @pytest.mark.performance
    def test_indexing_memory_efficiency(self, workspace_dir, test_db, dispatcher):
        """Test memory efficiency during large repository indexing."""
        import os

        import psutil

        repo_path = self.ensure_repository_exists(
            workspace_dir, "requests", "https://github.com/psf/requests.git"
        )

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        repo_id = test_db.create_repository(
            str(repo_path), "requests_memory_test", {"type": "memory_test"}
        )

        indexed_files = 0
        memory_samples = [initial_memory]

        python_files = list(repo_path.rglob("*.py"))

        for i, file_path in enumerate(python_files):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result = self.index_file_with_plugin(str(file_path), content, dispatcher)
                if result.success:
                    indexed_files += 1

                # Sample memory every 10 files
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)

            except Exception:
                continue

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_samples)

        # Memory efficiency assertions
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"
        assert max_memory < initial_memory + 150, f"Peak memory too high: {max_memory:.1f}MB"
        assert indexed_files >= 20, f"Should index reasonable number of files: {indexed_files}"

        print(
            f"Memory test: {indexed_files} files, {memory_increase:.1f}MB increase, {max_memory:.1f}MB peak"
        )

        # Check for memory leaks
        if len(memory_samples) > 2:
            memory_trend = memory_samples[-1] - memory_samples[1]
            assert memory_trend < 50, f"Possible memory leak detected: {memory_trend:.1f}MB trend"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
