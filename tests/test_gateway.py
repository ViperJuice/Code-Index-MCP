"""
Comprehensive tests for the MCP Server API Gateway.

This module tests all API endpoints including:
- Symbol lookup
- Search functionality (fuzzy and semantic)
- Server status
- Plugin information
- Reindexing operations
"""

import os
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugin_base import SearchResult, SymbolDef


@contextmanager
def measure_time(test_name: str, benchmark_results: dict):
    """Context manager to measure test execution time."""
    start = time.time()
    yield
    elapsed = time.time() - start
    if test_name not in benchmark_results:
        benchmark_results[test_name] = []
    benchmark_results[test_name].append(elapsed)


class TestGatewayStartupShutdown:
    """Test server startup and shutdown events."""

    @patch("mcp_server.gateway.format_preflight_report")
    @patch("mcp_server.gateway.run_startup_preflight")
    @patch("mcp_server.gateway.SQLiteStore")
    @patch("mcp_server.gateway.EnhancedDispatcher")
    @patch("mcp_server.gateway.FileWatcher")
    def test_startup_success(
        self,
        mock_watcher,
        mock_dispatcher,
        mock_store,
        mock_run_preflight,
        mock_format_preflight,
        test_client,
    ):
        """Test successful server startup."""
        mock_run_preflight.return_value = type(
            "PreflightResult", (), {"status": "warning", "checks": []}
        )()
        mock_format_preflight.return_value = ["warning"]
        # Trigger startup event
        with test_client:
            # Verify components were initialized
            mock_run_preflight.assert_called_once()
            mock_store.assert_called_once()
            mock_dispatcher.assert_called_once()
            mock_watcher.assert_called_once()

    @patch("mcp_server.gateway.SQLiteStore")
    def test_startup_failure(self, mock_store, test_client):
        """Test server startup with initialization failure."""
        mock_store.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            with test_client:
                pass

    @patch("mcp_server.gateway.FileWatcher")
    def test_shutdown_stops_watcher(self, mock_watcher_class, test_client_with_dispatcher):
        """Test that shutdown stops the file watcher."""
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        # Trigger startup+shutdown via context manager
        with test_client_with_dispatcher:
            pass

        # Watcher stop should have been called during shutdown
        mock_watcher.stop.assert_called_once()


class TestSymbolEndpoint:
    """Test /symbol endpoint."""

    def test_symbol_lookup_success(self, test_client_with_dispatcher, sample_symbol_def):
        """Test successful symbol lookup."""
        # Configure dispatcher mock
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(
            return_value=sample_symbol_def
        )

        response = test_client_with_dispatcher.get("/symbol?symbol=sample_function")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "sample_function"
        assert data["kind"] == "function"
        assert data["defined_in"] == "/test/sample.py"
        assert data["start_line"] == 10

    def test_symbol_lookup_not_found(self, test_client_with_dispatcher):
        """Test symbol lookup when symbol doesn't exist."""
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(return_value=None)

        response = test_client_with_dispatcher.get("/symbol?symbol=nonexistent")

        assert response.status_code == 200
        assert response.json() is None

    def test_symbol_lookup_no_dispatcher(self, test_client, monkeypatch):
        """Test symbol lookup when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        monkeypatch.setattr(gateway, "dispatcher", None)

        response = test_client.get("/symbol?symbol=test")

        assert response.status_code == 503
        assert "Dispatcher not ready" in response.json()["detail"]

    def test_symbol_lookup_error(self, test_client_with_dispatcher):
        """Test symbol lookup with internal error."""
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(
            side_effect=Exception("Lookup error")
        )

        response = test_client_with_dispatcher.get("/symbol?symbol=test")

        assert response.status_code == 500
        assert "Internal error during symbol lookup" in response.json()["detail"]

    @pytest.mark.parametrize(
        "symbol_name",
        [
            "simple_name",
            "CamelCaseName",
            "name_with_underscores",
            "name123",
            "🐍python_emoji",  # Unicode support
        ],
    )
    def test_symbol_lookup_various_names(self, test_client_with_dispatcher, symbol_name):
        """Test symbol lookup with various name formats."""
        mock_symbol = SymbolDef(
            symbol=symbol_name,
            kind="function",
            language="python",
            signature="def f()",
            doc=None,
            defined_in="/test.py",
            start_line=1,
            end_line=1,
            span=(1, 1),
        )
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(return_value=mock_symbol)

        response = test_client_with_dispatcher.get(f"/symbol?symbol={symbol_name}")

        assert response.status_code == 200
        assert response.json()["symbol"] == symbol_name


class TestSearchEndpoint:
    """Test /search endpoint."""

    def test_search_basic(self, test_client_with_dispatcher, sample_search_results):
        """Test basic search functionality."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(
            return_value=sample_search_results
        )

        response = test_client_with_dispatcher.get("/search?q=function")

        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        assert results[0]["file"] == "/test/file1.py"

    def test_search_semantic(self, test_client_with_dispatcher):
        """Test semantic search."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=[])

        response = test_client_with_dispatcher.get("/search?q=test&semantic=true")

        assert response.status_code == 200
        # Verify semantic parameter was passed
        test_client_with_dispatcher.app.state.dispatcher.search.assert_called_with(
            "test", semantic=True, limit=20
        )

    def test_search_auto_prefers_semantic_path_when_requested(
        self, test_client_with_dispatcher, monkeypatch
    ):
        """Auto mode should prefer semantic path instead of hybrid when semantic=true."""
        import mcp_server.gateway as gateway

        test_client_with_dispatcher.app.state.dispatcher.search = Mock(
            return_value=[{"file": "mcp_server/gateway.py", "line": 1, "snippet": "gateway"}]
        )

        class FakeHybrid:
            async def search(self, query, filters, limit):
                return [{"file": "htmlcov/function_index.html", "line": 1, "snippet": "bad"}]

        gateway.hybrid_search = FakeHybrid()
        gateway.query_cache = None

        login_response = test_client_with_dispatcher.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123!"},
        )
        token = login_response.json()["access_token"]

        response = test_client_with_dispatcher.get(
            "/search?q=test&semantic=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload[0]["file"] == "mcp_server/gateway.py"
        test_client_with_dispatcher.app.state.dispatcher.search.assert_called_with(
            "test", semantic=True, limit=20
        )

    def test_search_normalizes_internal_result_shapes(self, test_client_with_dispatcher):
        """Search should normalize internal file_path/filepath payloads to API schema."""
        import mcp_server.gateway as gateway

        test_client_with_dispatcher.app.state.dispatcher.search = Mock(
            return_value=[
                {"file_path": "a.py", "snippet": "hello", "score": 0.9},
                {"filepath": "b.py", "context": "world", "line": 4, "score": 0.7},
            ]
        )
        gateway.query_cache = None

        response = test_client_with_dispatcher.get("/search?q=test&semantic=true&mode=semantic")

        assert response.status_code == 200
        payload = response.json()
        assert payload[0]["file"] == "a.py"
        assert payload[0]["start_line"] == 1
        assert payload[1]["file"] == "b.py"
        assert payload[1]["start_line"] == 4

    def test_search_with_limit(self, test_client_with_dispatcher):
        """Test search with custom limit."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=[])

        response = test_client_with_dispatcher.get("/search?q=test&limit=50")

        assert response.status_code == 200
        test_client_with_dispatcher.app.state.dispatcher.search.assert_called_with(
            "test", semantic=False, limit=50
        )

    def test_search_empty_query(self, test_client_with_dispatcher):
        """Test search with empty query."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=[])

        response = test_client_with_dispatcher.get("/search?q=")

        assert response.status_code == 200
        assert response.json() == []

    def test_search_no_dispatcher(self, test_client, monkeypatch):
        """Test search when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        monkeypatch.setattr(gateway, "dispatcher", None)
        for _attr in ("bm25_indexer", "hybrid_search", "fuzzy_indexer"):
            if hasattr(gateway, _attr):
                monkeypatch.setattr(gateway, _attr, None)

        response = test_client.get("/search?q=test&mode=classic")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "not ready" in detail or "not available" in detail

    def test_search_error(self, test_client_with_dispatcher):
        """Test search with internal error."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(
            side_effect=Exception("Search error")
        )

        response = test_client_with_dispatcher.get("/search?q=test")

        assert response.status_code == 500
        assert "Internal error during search" in response.json()["detail"]

    @pytest.mark.parametrize(
        "query,expected_results",
        [
            ("", 0),
            ("a", 5),
            ("test function", 10),
            ("very long query " * 10, 2),
        ],
    )
    def test_search_various_queries(self, test_client_with_dispatcher, query, expected_results):
        """Test search with various query types."""
        results = [
            SearchResult(file=f"/file{i}.py", start_line=1, end_line=1, snippet=f"result_{i}")
            for i in range(expected_results)
        ]
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=results)

        response = test_client_with_dispatcher.get(f"/search?q={query}")

        assert response.status_code == 200
        assert len(response.json()) == expected_results


class TestStatusEndpoint:
    """Test /status endpoint."""

    def test_status_operational(self, test_client_with_dispatcher, populated_sqlite_store):
        """Test status endpoint when server is operational."""
        dispatcher = test_client_with_dispatcher.app.state.dispatcher
        # Mock dispatcher statistics and plugin list
        dispatcher.get_statistics = Mock(return_value={"total": 10, "by_language": {"python": 10}})
        dispatcher._plugins = [Mock()]  # 1 plugin
        test_client_with_dispatcher.app.state.sqlite_store = populated_sqlite_store

        response = test_client_with_dispatcher.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["plugins"] == 1
        assert data["indexed_files"]["total"] == 10
        assert "database" in data
        assert data["version"] == "0.1.0"

    def test_status_no_dispatcher(self, test_client, monkeypatch):
        """Test status when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        monkeypatch.setattr(gateway, "dispatcher", None)

        response = test_client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Dispatcher not initialized"

    def test_status_with_error(self, test_client_with_dispatcher):
        """Test status endpoint with internal error."""
        test_client_with_dispatcher.app.state.dispatcher.get_statistics = Mock(
            side_effect=Exception("Stats error")
        )

        response = test_client_with_dispatcher.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Stats error" in data["message"]

    def test_status_plugin_statistics(self, test_client_with_dispatcher):
        """Test status with plugin-level statistics."""
        # SimpleDispatcher has no get_statistics, so fallback to _plugins is used
        # Mock plugin with statistics
        mock_plugin = Mock()
        mock_plugin.get_indexed_count.return_value = 5
        mock_plugin.language = "python"
        test_client_with_dispatcher.app.state.dispatcher._plugins = [mock_plugin]

        response = test_client_with_dispatcher.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["indexed_files"]["total"] == 5
        assert data["indexed_files"]["by_language"]["python"] == 5


class TestPluginsEndpoint:
    """Test /plugins endpoint."""

    def test_plugins_list(self, test_client_with_dispatcher, monkeypatch):
        """Test listing loaded plugins."""
        import mcp_server.gateway as gateway

        # Build mock plugin_manager using the actual structure expected by the endpoint
        # Note: Mock(name=...) sets the mock's display name, not .name attribute
        mock_py_info = Mock(
            version="1.0", description="", author="", language="python", file_extensions=[".py"]
        )
        mock_py_info.name = "PythonPlugin"
        mock_js_info = Mock(
            version="1.0", description="", author="", language="javascript", file_extensions=[".js"]
        )
        mock_js_info.name = "JavaScriptPlugin"
        mock_pm = Mock()
        mock_pm._registry.list_plugins.return_value = [mock_py_info, mock_js_info]
        mock_pm.get_plugin_status.return_value = {}
        monkeypatch.setattr(gateway, "plugin_manager", mock_pm)

        response = test_client_with_dispatcher.get("/plugins")

        assert response.status_code == 200
        plugins = response.json()
        assert len(plugins) == 2
        assert plugins[0]["name"] == "PythonPlugin"
        assert plugins[0]["language"] == "python"
        assert plugins[1]["name"] == "JavaScriptPlugin"
        assert plugins[1]["language"] == "javascript"

    def test_plugins_no_dispatcher(self, test_client, monkeypatch):
        """Test plugins endpoint when plugin manager is not initialized."""
        import mcp_server.gateway as gateway

        monkeypatch.setattr(gateway, "plugin_manager", None)

        response = test_client.get("/plugins")

        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]

    def test_plugins_error(self, test_client_with_dispatcher, monkeypatch):
        """Test plugins endpoint with internal error."""
        import mcp_server.gateway as gateway

        mock_pm = Mock()
        mock_pm._registry.list_plugins.side_effect = Exception("Plugin error")
        monkeypatch.setattr(gateway, "plugin_manager", mock_pm)

        response = test_client_with_dispatcher.get("/plugins")

        assert response.status_code == 500
        assert "Internal error getting plugins" in response.json()["detail"]


class TestReindexEndpoint:
    """Test /reindex endpoint."""

    @pytest.mark.asyncio
    async def test_reindex_all(self, test_client_with_dispatcher, temp_code_directory):
        """Test reindexing all files."""
        # Mock index_file method and _plugins (SimpleDispatcher lacks _plugins by default)
        mock_plugin = Mock()
        mock_plugin.supports.side_effect = lambda p: Path(p).suffix == ".py"
        test_client_with_dispatcher.app.state.dispatcher._plugins = [mock_plugin]
        test_client_with_dispatcher.app.state.dispatcher.index_file = Mock()

        # Change to temp directory for testing
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_code_directory)

            response = test_client_with_dispatcher.post("/reindex")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert "Reindexed" in data["message"]
            # endpoint formats as ".py files", not "Python files"
            assert ".py files" in data["message"]

            # Verify index_file was called for Python files
            assert test_client_with_dispatcher.app.state.dispatcher.index_file.call_count >= 2
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_reindex_specific_file(self, test_client_with_dispatcher, temp_code_directory):
        """Test reindexing a specific file."""
        test_client_with_dispatcher.app.state.dispatcher.index_file = Mock()
        file_path = temp_code_directory / "sample.py"

        response = test_client_with_dispatcher.post(f"/reindex?path={file_path}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "Reindexed 1 files" in data["message"]

        test_client_with_dispatcher.app.state.dispatcher.index_file.assert_called_once_with(
            file_path
        )

    @pytest.mark.asyncio
    async def test_reindex_directory(self, test_client_with_dispatcher, temp_code_directory):
        """Test reindexing a directory."""
        test_client_with_dispatcher.app.state.dispatcher.index_file = Mock()

        # Mock plugin supports method
        mock_plugin = Mock()
        mock_plugin.supports.side_effect = lambda p: p.suffix == ".py"
        test_client_with_dispatcher.app.state.dispatcher._plugins = [mock_plugin]

        response = test_client_with_dispatcher.post(f"/reindex?path={temp_code_directory}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "Reindexed" in data["message"]

        # Should have indexed Python files
        assert test_client_with_dispatcher.app.state.dispatcher.index_file.call_count >= 2

    @pytest.mark.asyncio
    async def test_reindex_nonexistent_path(self, test_client_with_dispatcher):
        """Test reindexing with non-existent path."""
        response = test_client_with_dispatcher.post("/reindex?path=/nonexistent/path")

        assert response.status_code == 404
        assert "Path not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reindex_no_dispatcher(self, test_client):
        """Test reindex when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        gateway.dispatcher = None

        response = test_client.post("/reindex")

        assert response.status_code == 503
        assert "Dispatcher not ready" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reindex_error(self, test_client_with_dispatcher, tmp_path):
        """Test reindex with internal error."""
        test_client_with_dispatcher.app.state.dispatcher.index_file = Mock(
            side_effect=Exception("Index error")
        )
        # Create a real file so the existence check passes
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        response = test_client_with_dispatcher.post(f"/reindex?path={test_file}")

        assert response.status_code == 500
        assert "Reindexing failed" in response.json()["detail"]


class TestErrorHandling:
    """Test error handling across all endpoints."""

    def test_invalid_endpoint(self, test_client):
        """Test accessing invalid endpoint."""
        response = test_client.get("/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self, test_client):
        """Test using wrong HTTP method."""
        response = test_client.post("/symbol")
        assert response.status_code == 405

    @pytest.mark.parametrize(
        "endpoint,method",
        [
            ("/symbol", "get"),
            ("/search", "get"),
            ("/status", "get"),
            ("/plugins", "get"),
        ],
    )
    def test_missing_required_params(self, test_client_with_dispatcher, endpoint, method):
        """Test endpoints with missing required parameters."""
        client_method = getattr(test_client_with_dispatcher, method)

        if endpoint == "/symbol":
            # Symbol requires 'symbol' parameter
            response = client_method(endpoint)
            assert response.status_code == 422  # Unprocessable Entity
        elif endpoint == "/search":
            # Search requires 'q' parameter
            response = client_method(endpoint)
            assert response.status_code == 422


class TestConcurrency:
    """Test concurrent request handling."""

    @pytest.mark.parametrize("num_requests", [10, 50])
    def test_concurrent_requests(self, test_client_with_dispatcher, num_requests):
        """Test handling multiple concurrent requests."""
        import concurrent.futures

        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=[])

        def make_request(i):
            return test_client_with_dispatcher.get(f"/search?q=test{i}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)
        assert test_client_with_dispatcher.app.state.dispatcher.search.call_count == num_requests


class TestPerformance:
    """Performance benchmarks for API endpoints."""

    @pytest.mark.benchmark
    def test_symbol_lookup_performance(self, test_client_with_dispatcher, benchmark_results):
        """Benchmark symbol lookup performance."""
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(
            return_value=SymbolDef(
                symbol="test",
                kind="function",
                language="python",
                signature="def test()",
                doc=None,
                defined_in="/test.py",
                start_line=1,
                end_line=1,
                span=(1, 1),
            )
        )

        with measure_time("symbol_lookup", benchmark_results):
            for _ in range(100):
                response = test_client_with_dispatcher.get("/symbol?symbol=test")
                assert response.status_code == 200

    @pytest.mark.benchmark
    def test_search_performance(self, test_client_with_dispatcher, benchmark_results):
        """Benchmark search performance."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(
            return_value=[
                SearchResult(file=f"/file{i}.py", start_line=1, end_line=1, snippet=f"result_{i}")
                for i in range(20)
            ]
        )

        with measure_time("search", benchmark_results):
            for _ in range(100):
                response = test_client_with_dispatcher.get("/search?q=test")
                assert response.status_code == 200
