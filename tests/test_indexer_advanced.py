"""
Comprehensive tests for the indexer package.

This module provides extensive testing coverage for the IndexEngine,
QueryOptimizer, and related components.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from mcp_server.indexer.index_engine import (
    BatchIndexResult,
    IndexEngine,
    IndexOptions,
    IndexProgress,
    IndexResult,
    IndexTask,
)
from mcp_server.indexer.query_optimizer import (
    IndexSuggestion,
    IndexType,
    OptimizedQuery,
    PerformanceReport,
    Query,
    QueryCost,
    QueryOptimizer,
    QueryType,
    SearchPlan,
)
from mcp_server.core.path_resolver import PathResolver
from mcp_server.plugin_system.interfaces import IPluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestIndexEngine:
    """Test cases for the IndexEngine class."""

    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock plugin manager."""
        manager = Mock(spec=IPluginManager)

        # Mock plugin
        mock_plugin = Mock()
        mock_plugin.parse_file.return_value = {
            "language": "python",
            "symbols": [
                {
                    "name": "test_function",
                    "kind": "function",
                    "line_start": 1,
                    "line_end": 5,
                    "signature": "def test_function():",
                    "documentation": "A test function",
                }
            ],
            "references": [],
            "metadata": {},
        }

        manager.get_plugin_for_file.return_value = mock_plugin
        return manager

    @pytest.fixture
    def mock_storage(self):
        """Create a mock SQLite storage."""
        storage = Mock(spec=SQLiteStore)
        storage.create_repository.return_value = 1
        storage.store_file.return_value = 1
        storage.store_symbol.return_value = 1
        storage.get_file.return_value = None
        storage.get_statistics.return_value = {
            "files": 0,
            "symbols": 0,
            "symbol_references": 0,
        }
        return storage

    @pytest.fixture
    def mock_fuzzy_indexer(self):
        """Create a mock fuzzy indexer."""
        indexer = Mock(spec=FuzzyIndexer)
        return indexer

    @pytest.fixture
    def index_engine(self, mock_plugin_manager, mock_storage, mock_fuzzy_indexer):
        """Create an IndexEngine instance for testing."""
        return IndexEngine(
            plugin_manager=mock_plugin_manager,
            storage=mock_storage,
            fuzzy_indexer=mock_fuzzy_indexer,
            repository_path="/test/repo",
        )

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                '''
def test_function():
    """A test function."""
    return "hello world"

class TestClass:
    """A test class."""
    
    def method(self):
        return 42
'''
            )
            temp_path = f.name

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_index_file_success(self, index_engine, temp_file):
        """Test successful file indexing."""
        result = await index_engine.index_file(temp_file)

        assert result.success is True
        assert result.file_path == temp_file
        assert result.symbols_count == 1  # Based on mock return
        assert result.duration_ms > 0
        assert result.language == "python"

    @pytest.mark.asyncio
    async def test_index_file_not_found(self, index_engine):
        """Test indexing a non-existent file."""
        result = await index_engine.index_file("/nonexistent/file.py")

        assert result.success is False
        assert result.error == "File not found"

    @pytest.mark.asyncio
    async def test_index_file_no_plugin(self, index_engine, temp_file):
        """Test indexing a file with no available plugin."""
        index_engine.plugin_manager.get_plugin_for_file.return_value = None

        result = await index_engine.index_file(temp_file)

        assert result.success is False
        assert "No plugin available" in result.error

    @pytest.mark.asyncio
    async def test_index_file_force_reindex(self, index_engine, temp_file):
        """Test force reindexing of a file."""
        # First index
        result1 = await index_engine.index_file(temp_file)
        assert result1.success is True

        # Mock that file is already indexed
        index_engine.storage.get_file.return_value = {
            "hash": index_engine._get_file_hash(temp_file)
        }

        # Index without force - should skip
        result2 = await index_engine.index_file(temp_file, force=False)
        assert result2.success is True
        assert "already indexed" in result2.error

        # Index with force - should proceed
        result3 = await index_engine.index_file(temp_file, force=True)
        assert result3.success is True
        assert result3.error is None

    @pytest.mark.asyncio
    async def test_index_directory(self, index_engine, tmp_path):
        """Test directory indexing."""
        # Create test files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.py").write_text("def func3(): pass")

        result = await index_engine.index_directory(str(tmp_path))

        assert isinstance(result, BatchIndexResult)
        assert result.total_files == 3  # Should find all .py files
        assert result.successful >= 0

    @pytest.mark.asyncio
    async def test_update_index(self, index_engine, temp_file):
        """Test index updating."""
        result = await index_engine.update_index(temp_file)

        assert isinstance(result, IndexResult)
        assert result.file_path == temp_file

    @pytest.mark.asyncio
    async def test_remove_from_index(self, index_engine, temp_file):
        """Test removing file from index."""
        # Should not raise an exception
        await index_engine.remove_from_index(temp_file)

    def test_get_index_status_file(self, index_engine, temp_file):
        """Test getting index status for a file."""
        # Mock file record
        index_engine.storage.get_file.return_value = {
            "indexed_at": "2024-01-01T12:00:00",
            "hash": "abc123",
            "language": "python",
        }

        status = index_engine.get_index_status(temp_file)

        assert status["indexed"] is True
        assert status["language"] == "python"

    def test_get_index_status_directory(self, index_engine, tmp_path):
        """Test getting index status for a directory."""
        status = index_engine.get_index_status(str(tmp_path))

        assert "total_files" in status
        assert "total_symbols" in status

    @pytest.mark.asyncio
    async def test_rebuild_index(self, index_engine):
        """Test index rebuilding."""
        await index_engine.rebuild_index()

        # Should call clear on fuzzy indexer
        index_engine.fuzzy_indexer.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinate_indexing(self, index_engine, tmp_path):
        """Test coordinating indexing of multiple paths."""
        # Create test files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")

        options = IndexOptions(force_reindex=True)
        paths = [str(tmp_path / "file1.py"), str(tmp_path / "file2.py")]

        result = await index_engine.coordinate_indexing(paths, options)

        assert isinstance(result, BatchIndexResult)
        assert result.total_files == 2

    @pytest.mark.asyncio
    async def test_schedule_reindex(self, index_engine, temp_file):
        """Test scheduling a reindex task."""
        task_id = await index_engine.schedule_reindex(temp_file, priority=5)

        assert task_id in index_engine._task_queue
        task = index_engine._task_queue[task_id]
        assert task.path == temp_file
        assert task.priority == 5
        assert task.status == "pending"

    def test_get_pending_tasks(self, index_engine):
        """Test getting pending tasks."""
        # Add some tasks
        task1 = IndexTask(id="1", path="/path1", status="pending")
        task2 = IndexTask(id="2", path="/path2", status="running")
        task3 = IndexTask(id="3", path="/path3", status="pending")

        index_engine._task_queue = {"1": task1, "2": task2, "3": task3}

        pending = index_engine.get_pending_tasks()

        assert len(pending) == 2
        assert all(task.status == "pending" for task in pending)

    def test_cancel_task(self, index_engine):
        """Test cancelling a task."""
        # Add a pending task
        task = IndexTask(id="test", path="/path", status="pending")
        index_engine._task_queue["test"] = task

        # Cancel it
        result = index_engine.cancel_task("test")
        assert result is True
        assert task.status == "cancelled"

        # Try to cancel non-existent task
        result = index_engine.cancel_task("nonexistent")
        assert result is False

    def test_get_progress(self, index_engine):
        """Test getting indexing progress."""
        index_engine._progress = IndexProgress(total=100, completed=50, failed=5)
        index_engine._start_time = datetime.now() - timedelta(seconds=30)

        progress = index_engine.get_progress()

        assert progress.total == 100
        assert progress.completed == 50
        assert progress.failed == 5
        assert progress.elapsed_time is not None
        assert progress.throughput > 0

    def test_should_index_new_file(self, index_engine, temp_file):
        """Test should_index for a new file."""
        # Mock that file doesn't exist in storage
        index_engine.storage.get_file.return_value = None

        should_index = index_engine._should_index(temp_file)
        assert should_index is True

    def test_should_index_unchanged_file(self, index_engine, temp_file):
        """Test should_index for an unchanged file."""
        file_hash = index_engine._get_file_hash(temp_file)

        # Mock that file exists in storage with same hash
        index_engine.storage.get_file.return_value = {"hash": file_hash}

        should_index = index_engine._should_index(temp_file)
        assert should_index is False

    def test_should_index_changed_file(self, index_engine, temp_file):
        """Test should_index for a changed file."""
        # Mock that file exists in storage with different hash
        index_engine.storage.get_file.return_value = {"hash": "different_hash"}

        should_index = index_engine._should_index(temp_file)
        assert should_index is True

    def test_get_file_hash(self, index_engine, temp_file):
        """Test file hash calculation."""
        hash1 = index_engine._get_file_hash(temp_file)
        hash2 = index_engine._get_file_hash(temp_file)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_collect_files(self, index_engine, tmp_path):
        """Test file collection from directory."""
        # Create test files
        (tmp_path / "file1.py").write_text("# Python file")
        (tmp_path / "file2.js").write_text("// JavaScript file")
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.py").write_text("# Another Python file")

        # Mock plugin manager to only support .py files
        def mock_get_plugin(path):
            return Mock() if path.suffix == ".py" else None

        index_engine.plugin_manager.get_plugin_for_file.side_effect = mock_get_plugin

        options = IndexOptions(include_patterns=["*.py"])
        files = index_engine._collect_files(str(tmp_path), True, options)

        # Should find 2 Python files
        py_files = [f for f in files if f.endswith(".py")]
        assert len(py_files) == 2


class TestQueryOptimizer:
    """Test cases for the QueryOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create a QueryOptimizer instance for testing."""
        return QueryOptimizer()

    @pytest.fixture
    def sample_query(self):
        """Create a sample query for testing."""
        return Query(
            query_type=QueryType.SYMBOL_SEARCH,
            text="test_function",
            filters={"kind": "function", "language": "python"},
            limit=10,
        )

    def test_optimize_query(self, optimizer, sample_query):
        """Test query optimization."""
        optimized = optimizer.optimize_query(sample_query)

        assert isinstance(optimized, OptimizedQuery)
        assert optimized.original == sample_query
        assert optimized.rewritten_text is not None
        assert optimized.index_choice is not None
        assert optimized.estimated_cost is not None
        assert len(optimized.optimization_notes) > 0

    def test_estimate_cost(self, optimizer, sample_query):
        """Test query cost estimation."""
        cost = optimizer.estimate_cost(sample_query)

        assert isinstance(cost, QueryCost)
        assert cost.estimated_rows > 0
        assert cost.estimated_time_ms > 0
        assert cost.total_cost > 0
        assert 0 <= cost.confidence <= 1

    def test_suggest_indexes(self, optimizer):
        """Test index suggestion based on query patterns."""
        queries = [
            Query(QueryType.SYMBOL_SEARCH, "func", {"kind": "function"}),
            Query(QueryType.SYMBOL_SEARCH, "class", {"kind": "class"}),
            Query(QueryType.SYMBOL_SEARCH, "var", {"kind": "function"}),  # kind used again
        ]

        suggestions = optimizer.suggest_indexes(queries)

        assert isinstance(suggestions, list)
        assert all(isinstance(s, IndexSuggestion) for s in suggestions)

        # Should suggest index for 'kind' column (used in all queries)
        kind_suggestions = [s for s in suggestions if "kind" in s.columns]
        assert len(kind_suggestions) > 0

    def test_analyze_query_performance(self, optimizer, sample_query):
        """Test query performance analysis."""
        report = optimizer.analyze_query_performance(
            query=sample_query, actual_time_ms=150.0, actual_rows=25
        )

        assert isinstance(report, PerformanceReport)
        assert report.query == sample_query
        assert report.actual_time_ms == 150.0
        assert report.actual_rows == 25
        assert isinstance(report.bottlenecks, list)
        assert isinstance(report.suggestions, list)

    def test_plan_search(self, optimizer, sample_query):
        """Test search plan generation."""
        plan = optimizer.plan_search(sample_query)

        assert isinstance(plan, SearchPlan)
        assert plan.query == sample_query
        assert len(plan.steps) > 0
        assert plan.estimated_cost is not None

        # Should have index scan step
        index_steps = [s for s in plan.steps if s["type"] == "index_scan"]
        assert len(index_steps) > 0

    @pytest.mark.asyncio
    async def test_execute_plan(self, optimizer, sample_query):
        """Test search plan execution."""
        plan = optimizer.plan_search(sample_query)

        result = await optimizer.execute_plan(plan)

        assert isinstance(result, dict)
        assert "results" in result
        # In the mock implementation, this returns empty results
        assert result["results"] == []

    def test_optimize_plan(self, optimizer, sample_query):
        """Test search plan optimization."""
        original_plan = optimizer.plan_search(sample_query)
        optimized_plan = optimizer.optimize_plan(original_plan)

        assert isinstance(optimized_plan, SearchPlan)
        assert optimized_plan.query == original_plan.query

    def test_get_search_statistics(self, optimizer):
        """Test getting search statistics."""
        stats = optimizer.get_search_statistics()

        assert hasattr(stats, "total_queries")
        assert hasattr(stats, "avg_response_time_ms")
        assert hasattr(stats, "cache_hit_rate")
        assert hasattr(stats, "index_usage")
        assert hasattr(stats, "query_patterns")

    def test_rewrite_query_text_fuzzy(self, optimizer):
        """Test query text rewriting for fuzzy search."""
        query = Query(QueryType.FUZZY_SEARCH, "TestFunction")
        rewritten = optimizer._rewrite_query_text(query)

        assert rewritten == "testfunction"  # Should be lowercased

    def test_rewrite_query_text_fts(self, optimizer):
        """Test query text rewriting for full-text search."""
        query = Query(QueryType.TEXT_SEARCH, "hello world")
        rewritten = optimizer._rewrite_query_text(query)

        assert "AND" in rewritten  # Should add AND operators
        assert '"hello"' in rewritten
        assert '"world"' in rewritten

    def test_choose_index_symbol_search(self, optimizer):
        """Test index choice for symbol search."""
        query = Query(QueryType.SYMBOL_SEARCH, "function_name")
        choice = optimizer._choose_index(query)

        assert choice.index_name in optimizer._index_stats
        assert choice.cost > 0
        assert choice.reason is not None

    def test_choose_index_fuzzy_search(self, optimizer):
        """Test index choice for fuzzy search."""
        query = Query(QueryType.FUZZY_SEARCH, "func")
        choice = optimizer._choose_index(query)

        # Should prefer trigram index for fuzzy search
        if "symbol_trigrams" in optimizer._index_stats:
            assert choice.index_type == IndexType.TRIGRAM or choice.cost < 1000

    def test_optimize_filter_order(self, optimizer):
        """Test filter order optimization."""
        query = Query(
            QueryType.SYMBOL_SEARCH,
            "test",
            filters={
                "kind": "function",  # More selective
                "language": "python",  # Less selective
                "file_path": "/specific/path",  # Very selective
            },
        )

        order = optimizer._optimize_filter_order(query)

        assert len(order) == 3
        # Most selective filters should come first
        assert "file_path" in order[:2]  # Should be first or second

    def test_estimate_filter_selectivity(self, optimizer):
        """Test filter selectivity estimation."""
        # Test known selective filters
        kind_sel = optimizer._estimate_filter_selectivity("kind", "function")
        path_sel = optimizer._estimate_filter_selectivity("file_path", "/path")
        lang_sel = optimizer._estimate_filter_selectivity("language", "python")

        # file_path should be most selective
        assert path_sel < kind_sel
        assert path_sel < lang_sel

    def test_should_use_cache(self, optimizer):
        """Test cache usage decision."""
        # Expensive queries should be cached
        semantic_query = Query(QueryType.SEMANTIC_SEARCH, "test")
        assert optimizer._should_use_cache(semantic_query) is True

        # Simple queries without filters should be cached
        simple_query = Query(QueryType.SYMBOL_SEARCH, "test")
        assert optimizer._should_use_cache(simple_query) is True

    def test_estimate_base_rows(self, optimizer):
        """Test base row estimation for different query types."""
        symbol_rows = optimizer._estimate_base_rows(Query(QueryType.SYMBOL_SEARCH, "test"))
        semantic_rows = optimizer._estimate_base_rows(Query(QueryType.SEMANTIC_SEARCH, "test"))

        # Symbol search should estimate more rows than semantic
        assert symbol_rows > semantic_rows

    def test_calculate_selectivity(self, optimizer):
        """Test selectivity calculation."""
        # Query with no filters
        query1 = Query(QueryType.SYMBOL_SEARCH, "test")
        sel1 = optimizer._calculate_selectivity(query1)
        assert sel1 == 1.0

        # Query with filters
        query2 = Query(
            QueryType.SYMBOL_SEARCH,
            "test",
            filters={"kind": "function", "language": "python"},
        )
        sel2 = optimizer._calculate_selectivity(query2)
        assert sel2 < 1.0

    def test_generate_cache_key(self, optimizer, sample_query):
        """Test cache key generation."""
        key1 = optimizer._generate_cache_key(sample_query)
        key2 = optimizer._generate_cache_key(sample_query)

        # Same query should generate same key
        assert key1 == key2

        # Different query should generate different key
        different_query = Query(QueryType.TEXT_SEARCH, "different")
        key3 = optimizer._generate_cache_key(different_query)
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cache_functionality(self, optimizer, sample_query):
        """Test query result caching."""
        plan = optimizer.plan_search(sample_query)

        # First execution
        result1 = await optimizer.execute_plan(plan)

        # Second execution should use cache if cache_key is set
        if plan.cache_key:
            result2 = await optimizer.execute_plan(plan)
            # Results should be identical (from cache)
            assert result1 == result2


class TestIndexEngineIntegration:
    """Integration tests for IndexEngine with real components."""

    @pytest.fixture
    def real_storage(self, tmp_path):
        """Create a real SQLite storage for integration testing."""
        db_path = tmp_path / "integration.db"
        storage = SQLiteStore(str(db_path), path_resolver=PathResolver(repository_root=tmp_path))
        yield storage

    @pytest.fixture
    def real_fuzzy_indexer(self, real_storage):
        """Create a real FuzzyIndexer for integration testing."""
        return FuzzyIndexer(real_storage)

    @pytest.fixture
    def indexed_sample_file(self, real_storage, real_fuzzy_indexer, tmp_path):
        """Index a sample file end-to-end for reuse across integration tests."""
        mock_plugin_manager = Mock(spec=IPluginManager)
        mock_plugin = Mock()
        mock_plugin.parse_file.return_value = {
            "language": "python",
            "symbols": [
                {
                    "name": "indexed_function",
                    "kind": "function",
                    "line_start": 1,
                    "line_end": 2,
                    "signature": "def indexed_function():",
                }
            ],
            "references": [],
            "metadata": {},
        }
        mock_plugin_manager.get_plugin_for_file.return_value = mock_plugin

        engine = IndexEngine(
            plugin_manager=mock_plugin_manager,
            storage=real_storage,
            fuzzy_indexer=real_fuzzy_indexer,
            repository_path=str(tmp_path),
        )

        test_file = tmp_path / "indexed_sample.py"
        test_file.write_text("def indexed_function():\n    return 1\n")

        result = asyncio.run(engine.index_file(str(test_file)))

        return {
            "storage": real_storage,
            "file_path": str(test_file),
            "repository_id": engine._repository_id,
            "result": result,
        }

    def test_full_indexing_workflow(self, real_storage, real_fuzzy_indexer, tmp_path):
        """Test complete indexing workflow with real components."""
        # Create mock plugin manager
        mock_plugin_manager = Mock(spec=IPluginManager)
        mock_plugin = Mock()
        mock_plugin.parse_file.return_value = {
            "language": "python",
            "symbols": [
                {
                    "name": "test_function",
                    "kind": "function",
                    "line_start": 1,
                    "line_end": 3,
                    "signature": "def test_function():",
                    "documentation": "Test function",
                }
            ],
            "references": [],
            "metadata": {},
        }
        mock_plugin_manager.get_plugin_for_file.return_value = mock_plugin

        # Create index engine
        engine = IndexEngine(
            plugin_manager=mock_plugin_manager,
            storage=real_storage,
            fuzzy_indexer=real_fuzzy_indexer,
            repository_path=str(tmp_path),
        )

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test_function():\n    return 42\n")

        # Index the file
        result = asyncio.run(engine.index_file(str(test_file)))

        # Verify results
        assert result.success is True
        assert result.symbols_count == 1

        # Verify data was stored
        stats = real_storage.get_statistics()
        assert stats["files"] >= 1
        assert stats["symbols"] >= 1

        # Test fuzzy search
        fuzzy_results = real_fuzzy_indexer.search_symbols("test")
        assert len(fuzzy_results) > 0

    def test_indexed_file_has_hashes_and_flags(
        self, indexed_sample_file: Dict[str, Any], real_storage: SQLiteStore
    ):
        """Verify stored files include hashes and soft-delete defaults."""
        result = indexed_sample_file["result"]
        repository_id = indexed_sample_file["repository_id"]
        file_path = indexed_sample_file["file_path"]

        assert result.success is True

        record = real_storage.get_file(file_path, repository_id)
        assert record is not None
        assert record["hash"]
        assert record["content_hash"]
        assert record["relative_path"].endswith("indexed_sample.py")
        assert record["is_deleted"] in (False, 0)
        assert record["deleted_at"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
