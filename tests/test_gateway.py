"""
Comprehensive tests for the MCP Server API Gateway.

This module tests all API endpoints including:
- Symbol lookup
- Search functionality (fuzzy and semantic)
- Server status
- Plugin information
- Reindexing operations
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugin_base import SearchResult, SymbolDef


class TestGatewayStartupShutdown:
    """Test server startup and shutdown events."""

    @patch("mcp_server.gateway.SQLiteStore")
    @patch("mcp_server.gateway.PythonPlugin")
    @patch("mcp_server.gateway.Dispatcher")
    @patch("mcp_server.gateway.FileWatcher")
    def test_startup_success(
        self, mock_watcher, mock_dispatcher, mock_plugin, mock_store, test_client
    ):
        """Test successful server startup."""
        # Trigger startup event
        with test_client:
            # Verify components were initialized
            mock_store.assert_called_once_with("code_index.db")
            mock_plugin.assert_called_once()
            mock_dispatcher.assert_called_once()
            mock_watcher.assert_called_once()

    @patch("mcp_server.gateway.SQLiteStore")
    def test_startup_failure(self, mock_store, test_client):
        """Test server startup with initialization failure."""
        mock_store.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            with test_client:
                pass

    def test_shutdown_stops_watcher(self, test_client_with_dispatcher):
        """Test that shutdown stops the file watcher."""
        # Mock the file watcher
        mock_watcher = Mock()
        test_client_with_dispatcher.app.state.file_watcher = mock_watcher

        # Trigger shutdown by exiting context
        with test_client_with_dispatcher:
            pass

        # Watcher stop should have been called
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
        assert data["name"] == "sample_function"
        assert data["kind"] == "function"
        assert data["path"] == "/test/sample.py"
        assert data["line"] == 10

    def test_symbol_lookup_not_found(self, test_client_with_dispatcher):
        """Test symbol lookup when symbol doesn't exist."""
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(return_value=None)

        response = test_client_with_dispatcher.get("/symbol?symbol=nonexistent")

        assert response.status_code == 200
        assert response.json() is None

    def test_symbol_lookup_no_dispatcher(self, test_client):
        """Test symbol lookup when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        gateway.dispatcher = None

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
        mock_symbol = SymbolDef(name=symbol_name, kind="function", path="/test.py", line=1)
        test_client_with_dispatcher.app.state.dispatcher.lookup = Mock(return_value=mock_symbol)

        response = test_client_with_dispatcher.get(f"/symbol?symbol={symbol_name}")

        assert response.status_code == 200
        assert response.json()["name"] == symbol_name


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
        assert results[0]["name"] == "function_one"
        assert results[0]["score"] == 0.95

    def test_search_semantic(self, test_client_with_dispatcher):
        """Test semantic search."""
        test_client_with_dispatcher.app.state.dispatcher.search = Mock(return_value=[])

        response = test_client_with_dispatcher.get("/search?q=test&semantic=true")

        assert response.status_code == 200
        # Verify semantic parameter was passed
        test_client_with_dispatcher.app.state.dispatcher.search.assert_called_with(
            "test", semantic=True, limit=20
        )

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

    def test_search_no_dispatcher(self, test_client):
        """Test search when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        gateway.dispatcher = None

        response = test_client.get("/search?q=test")

        assert response.status_code == 503
        assert "Dispatcher not ready" in response.json()["detail"]

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
            SearchResult(name=f"result_{i}", kind="function", path=f"/file{i}.py", score=1.0)
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
        # Mock dispatcher statistics
        test_client_with_dispatcher.app.state.dispatcher.get_statistics = Mock(
            return_value={"total": 10, "by_language": {"python": 10}}
        )
        test_client_with_dispatcher.app.state.sqlite_store = populated_sqlite_store

        response = test_client_with_dispatcher.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["plugins"] == 1
        assert data["indexed_files"]["total"] == 10
        assert "database" in data
        assert data["version"] == "0.1.0"

    def test_status_no_dispatcher(self, test_client):
        """Test status when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        gateway.dispatcher = None

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
        # Remove get_statistics method to test fallback
        delattr(test_client_with_dispatcher.app.state.dispatcher, "get_statistics")

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

    def test_plugins_list(self, test_client_with_dispatcher):
        """Test listing loaded plugins."""
        # Mock plugins
        mock_py_plugin = Mock()
        mock_py_plugin.__class__.__name__ = "PythonPlugin"
        mock_py_plugin.language = "python"

        mock_js_plugin = Mock()
        mock_js_plugin.__class__.__name__ = "JavaScriptPlugin"
        mock_js_plugin.lang = "javascript"

        test_client_with_dispatcher.app.state.dispatcher._plugins = [
            mock_py_plugin,
            mock_js_plugin,
        ]

        response = test_client_with_dispatcher.get("/plugins")

        assert response.status_code == 200
        plugins = response.json()
        assert len(plugins) == 2
        assert plugins[0]["name"] == "PythonPlugin"
        assert plugins[0]["language"] == "python"
        assert plugins[1]["name"] == "JavaScriptPlugin"
        assert plugins[1]["language"] == "javascript"

    def test_plugins_no_dispatcher(self, test_client):
        """Test plugins endpoint when dispatcher is not initialized."""
        import mcp_server.gateway as gateway

        gateway.dispatcher = None

        response = test_client.get("/plugins")

        assert response.status_code == 503
        assert "Dispatcher not ready" in response.json()["detail"]

    def test_plugins_error(self, test_client_with_dispatcher):
        """Test plugins endpoint with internal error."""
        # Make _plugins attribute raise an error
        type(test_client_with_dispatcher.app.state.dispatcher)._plugins = property(
            lambda self: (_ for _ in ()).throw(Exception("Plugin error"))
        )

        response = test_client_with_dispatcher.get("/plugins")

        assert response.status_code == 500
        assert "Internal error getting plugins" in response.json()["detail"]


class TestReindexEndpoint:
    """Test /reindex endpoint."""

    @pytest.mark.asyncio
    async def test_reindex_all(self, test_client_with_dispatcher, temp_code_directory):
        """Test reindexing all files."""
        # Mock index_file method
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
            assert "Python files" in data["message"]

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
    async def test_reindex_error(self, test_client_with_dispatcher):
        """Test reindex with internal error."""
        test_client_with_dispatcher.app.state.dispatcher.index_file = Mock(
            side_effect=Exception("Index error")
        )

        response = test_client_with_dispatcher.post("/reindex?path=/tmp/test.py")

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
            return_value=SymbolDef(name="test", kind="function", path="/test.py", line=1)
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
                SearchResult(name=f"result_{i}", kind="function", path=f"/file{i}.py", score=1.0)
                for i in range(20)
            ]
        )

        with measure_time("search", benchmark_results):
            for _ in range(100):
                response = test_client_with_dispatcher.get("/search?q=test")
                assert response.status_code == 200
