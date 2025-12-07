#!/usr/bin/env python3
"""
Real-world developer workflow tests for Code-Index-MCP.
Tests realistic developer search and navigation patterns.
"""

import asyncio
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pytest

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.interfaces.shared_interfaces import Result
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestDeveloperWorkflows:
    """Test realistic developer search and navigation patterns."""

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

        repo_id = test_db.create_repository(str(repo_path), repo_name, {"type": "workflow_test"})

        # Index files and build search index
        indexed_count = 0
        extensions = [".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp"]

        for ext in extensions:
            files = list(repo_path.rglob(f"*{ext}"))[:150]  # Limit for testing

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
                            if symbol_name and len(symbol_name) > 1:
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

                except Exception:
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
        results = fuzzy_indexer.search(symbol_name, limit=20)
        return [
            {
                "name": result.get("symbol", ""),
                "file": result.get("file", ""),
                "line": result.get("line", 0),
            }
            for result in results
        ]

    def search_code(
        self, query: str, test_db: SQLiteStore, repo_id: int, limit: int = 30
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
                    # Find line number
                    lines = content.splitlines()
                    line_num = 1
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            line_num = i + 1
                            break

                    results.append(
                        {
                            "file_path": file_data.get("path", ""),
                            "content": (content[:300] + "..." if len(content) > 300 else content),
                            "line": line_num,
                        }
                    )
                    if len(results) >= limit:
                        break
            return results

    def find_symbol_references(
        self,
        symbol_name: str,
        test_db: SQLiteStore,
        fuzzy_indexer: FuzzyIndexer,
        repo_id: int,
    ) -> List[Dict]:
        """Find all references to a symbol."""
        # Combine symbol lookup and content search
        symbol_results = self.lookup_symbol(symbol_name, fuzzy_indexer)
        content_results = self.search_code(symbol_name, test_db, repo_id, limit=50)

        # Deduplicate and combine
        all_results = []
        seen_files = set()

        for result in symbol_results:
            file_path = result.get("file", "")
            if file_path and file_path not in seen_files:
                all_results.append(
                    {
                        "file_path": file_path,
                        "line": result.get("line", 0),
                        "type": "symbol_definition",
                        "name": result.get("name", ""),
                    }
                )
                seen_files.add(file_path)

        for result in content_results:
            file_path = result.get("file_path", "")
            if file_path and file_path not in seen_files:
                all_results.append(
                    {
                        "file_path": file_path,
                        "line": result.get("line", 0),
                        "type": "content_reference",
                        "content": result.get("content", "")[:100],
                    }
                )
                seen_files.add(file_path)

        return all_results

    @pytest.mark.integration
    @pytest.mark.workflow
    def test_find_function_usage(self, workspace_dir, test_db, dispatcher, fuzzy_indexer):
        """Test finding where a function is used across codebase."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "django_usage",
            "https://github.com/django/django.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        # Test finding Django's get_object_or_404 function usage
        function_name = "get_object_or_404"

        # Find symbol definition
        symbol_results = self.lookup_symbol(function_name, fuzzy_indexer)
        assert len(symbol_results) > 0, f"Should find {function_name} definition"

        # Find usage patterns
        usage_results = self.search_code(function_name, test_db, repo_id, limit=20)
        assert len(usage_results) > 0, f"Should find {function_name} usage examples"

        # Validate result quality
        usage_files = set(result["file_path"] for result in usage_results)
        assert len(usage_files) >= 3, f"Should span multiple files, got {len(usage_files)}"

        # Check for common usage patterns
        common_patterns = ["from", "import", "def", "get_object_or_404("]
        found_patterns = 0

        for result in usage_results:
            content = result.get("content", "")
            for pattern in common_patterns:
                if pattern in content:
                    found_patterns += 1
                    break

        pattern_coverage = found_patterns / len(usage_results) if usage_results else 0
        assert pattern_coverage >= 0.5, f"Should find common usage patterns: {pattern_coverage:.1%}"

        print(
            f"Function usage test: Found {len(symbol_results)} definitions, "
            f"{len(usage_results)} usages across {len(usage_files)} files"
        )

    @pytest.mark.integration
    @pytest.mark.workflow
    def test_class_hierarchy_discovery(self, workspace_dir, test_db, dispatcher, fuzzy_indexer):
        """Test discovering class inheritance patterns."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "django_classes",
            "https://github.com/django/django.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        # Search for Model class and its subclasses
        base_class = "Model"
        model_results = self.search_code(f"class.*{base_class}", test_db, repo_id, limit=30)

        # Should find base Model class and many subclasses
        assert len(model_results) >= 5, f"Should find {base_class} class hierarchy"

        # Check for inheritance patterns
        inheritance_patterns = [r"class.*Model\(", r"Model\)", r"models\.Model"]

        found_patterns = 0
        for pattern in inheritance_patterns:
            pattern_results = [
                r for r in model_results if re.search(pattern, r.get("content", ""), re.IGNORECASE)
            ]
            if pattern_results:
                found_patterns += 1

        assert (
            found_patterns >= 2
        ), f"Should find inheritance patterns: {found_patterns}/{len(inheritance_patterns)}"

        # Look for specific model subclasses
        subclass_results = self.lookup_symbol("User", fuzzy_indexer)
        if subclass_results:
            # Should find User model or similar
            user_files = [r["file"] for r in subclass_results if "model" in r["file"].lower()]
            print(f"Found User-related symbols in {len(user_files)} model files")

        print(f"Class hierarchy test: Found {len(model_results)} Model-related classes")

    @pytest.mark.integration
    @pytest.mark.workflow
    def test_api_discovery(self, workspace_dir, test_db, dispatcher, fuzzy_indexer):
        """Test discovering API endpoints and interfaces."""
        repo_id = self.setup_indexed_repository(
            workspace_dir,
            "requests_api",
            "https://github.com/psf/requests.git",
            test_db,
            dispatcher,
            fuzzy_indexer,
        )

        # Find HTTP method implementations
        http_methods = ["get", "post", "put", "delete", "patch"]
        method_results = {}

        for method in http_methods:
            # Look for function definitions
            symbol_results = self.lookup_symbol(method, fuzzy_indexer)
            content_results = self.search_code(f"def {method}", test_db, repo_id, limit=5)

            combined_results = symbol_results + [
                {"name": method, "file": r["file_path"], "line": r["line"]} for r in content_results
            ]

            method_results[method] = combined_results

            if combined_results:
                print(f"Found {method} method in {len(combined_results)} locations")

        # Should find most HTTP methods
        found_methods = [method for method, results in method_results.items() if results]
        assert len(found_methods) >= 3, f"Should find common HTTP methods: {found_methods}"

        # Look for Session class (main API entry point)
        session_results = self.lookup_symbol("Session", fuzzy_indexer)
        assert len(session_results) > 0, "Should find Session class"

        # Look for request/response patterns
        api_patterns = ["request", "response", "headers", "cookies"]
        api_coverage = 0

        for pattern in api_patterns:
            pattern_results = self.search_code(pattern, test_db, repo_id, limit=5)
            if pattern_results:
                api_coverage += 1

        coverage_rate = api_coverage / len(api_patterns)
        assert coverage_rate >= 0.5, f"Should find API patterns: {coverage_rate:.1%}"

        print(
            f"API discovery test: Found {len(found_methods)} HTTP methods, "
            f"{len(session_results)} Session references"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
