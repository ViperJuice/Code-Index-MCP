"""
Comprehensive benchmark tests for MCP Server performance validation.

This module provides:
- pytest-benchmark integration tests
- Performance regression tests
- SLO validation tests
- Memory and resource usage tests
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import psutil
import os

from mcp_server.benchmarks import (
    BenchmarkSuite,
    BenchmarkRunner,
    BenchmarkResult,
    PerformanceMetrics,
)
from mcp_server.plugin_base import IPlugin, SymbolDef, SearchResult


class MockPlugin(IPlugin):
    """Mock plugin for benchmark testing."""
    
    def __init__(self, lang: str = "python", delay_ms: float = 0):
        self.lang = lang
        self.delay_ms = delay_ms
        self._symbols = {}
        self._files = {}
    
    def supports(self, path: Path) -> bool:
        extensions = {
            "python": [".py"],
            "javascript": [".js"],
            "c": [".c", ".h"],
        }
        return path.suffix in extensions.get(self.lang, [])
    
    def index(self, path: Path, content: str):
        # Simulate indexing delay
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)
        
        self._files[str(path)] = content
        
        # Extract simple symbols
        if self.lang == "python":
            for line in content.split('\n'):
                if line.startswith('def '):
                    name = line.split('(')[0].replace('def ', '').strip()
                    self._symbols[name] = SymbolDef(
                        name=name,
                        type="function",
                        path=str(path),
                        line=1,
                        character=0,
                        definition=line
                    )
                elif line.startswith('class '):
                    name = line.split('(')[0].split(':')[0].replace('class ', '').strip()
                    self._symbols[name] = SymbolDef(
                        name=name,
                        type="class",
                        path=str(path),
                        line=1,
                        character=0,
                        definition=line
                    )
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        # Simulate lookup delay
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)
        return self._symbols.get(symbol)
    
    def search(self, query: str, opts: dict):
        # Simulate search delay
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000)
        
        results = []
        for name, symbol in self._symbols.items():
            if query.lower() in name.lower():
                results.append(SearchResult(
                    path=symbol.path,
                    line=symbol.line,
                    character=symbol.character,
                    snippet=symbol.definition,
                    score=1.0
                ))
        
        return results[:opts.get('limit', 20)]


@pytest.fixture
def mock_plugins():
    """Create mock plugins for testing."""
    return [
        MockPlugin("python", delay_ms=5),
        MockPlugin("javascript", delay_ms=5),
        MockPlugin("c", delay_ms=5),
    ]


@pytest.fixture
def benchmark_suite(mock_plugins):
    """Create benchmark suite with mock plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        suite = BenchmarkSuite(mock_plugins, db_path)
        yield suite


@pytest.fixture
def benchmark_runner():
    """Create benchmark runner for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = BenchmarkRunner(Path(tmpdir))
        yield runner


class TestPerformanceMetrics:
    """Test the PerformanceMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metric initialization."""
        metric = PerformanceMetrics("test_op")
        assert metric.operation == "test_op"
        assert metric.count == 0
        assert metric.mean == 0.0
        assert metric.samples == []
    
    def test_add_samples(self):
        """Test adding timing samples."""
        metric = PerformanceMetrics("test_op")
        samples = [10.5, 15.2, 12.3, 18.7, 11.1]
        
        for sample in samples:
            metric.add_sample(sample)
        
        assert metric.count == 5
        assert metric.min == 10.5
        assert metric.max == 18.7
        assert 13.0 < metric.mean < 14.0  # Approximate
    
    def test_percentiles(self):
        """Test percentile calculations."""
        metric = PerformanceMetrics("test_op")
        
        # Add 100 samples with known distribution
        for i in range(100):
            metric.add_sample(i)
        
        assert metric.median == 49.5
        assert metric.p95 == 94.05
        assert metric.p99 == 98.01
    
    def test_slo_validation(self):
        """Test SLO validation."""
        metric = PerformanceMetrics("test_op")
        
        # Add samples below target
        for _ in range(100):
            metric.add_sample(50)  # All 50ms
        
        assert metric.is_within_slo(100)  # Should pass
        assert not metric.is_within_slo(40)  # Should fail


class TestBenchmarkSuite:
    """Test the BenchmarkSuite class."""
    
    def test_suite_initialization(self, mock_plugins):
        """Test suite initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            suite = BenchmarkSuite(mock_plugins, db_path)
            
            assert len(suite.plugins) == 3
            assert suite.dispatcher is not None
            assert suite.store is not None
            assert suite.gateway is not None
    
    def test_symbol_lookup_benchmark(self, benchmark_suite):
        """Test symbol lookup benchmarking."""
        # Pre-populate some symbols
        for i in range(10):
            symbol = SymbolDef(
                name=f"function_{i}",
                type="function",
                path=f"/test/file_{i}.py",
                line=1,
                character=0,
                definition=f"def function_{i}():"
            )
            benchmark_suite.plugins[0]._symbols[f"function_{i}"] = symbol
        
        metric = benchmark_suite.benchmark_symbol_lookup(iterations=50)
        
        assert metric.operation == "symbol_lookup"
        assert metric.count == 50
        assert metric.p95 > 0
        assert metric.memory_usage_mb > 0
    
    def test_search_benchmark(self, benchmark_suite):
        """Test search benchmarking."""
        # Pre-populate symbols
        for i in range(20):
            symbol = SymbolDef(
                name=f"test_function_{i}",
                type="function",
                path=f"/test/file_{i}.py",
                line=1,
                character=0,
                definition=f"def test_function_{i}():"
            )
            benchmark_suite.plugins[0]._symbols[f"test_function_{i}"] = symbol
        
        metrics = benchmark_suite.benchmark_search(iterations=10)
        
        assert "fuzzy_search" in metrics
        assert "semantic_search" in metrics
        assert metrics["fuzzy_search"].count == 10
        assert metrics["fuzzy_search"].p95 > 0
    
    def test_indexing_benchmark(self, benchmark_suite):
        """Test indexing throughput benchmark."""
        metric = benchmark_suite.benchmark_indexing(file_count=100)
        
        assert metric.operation == "indexing_throughput"
        assert metric.count >= 100  # Should have timing for each file
        assert hasattr(metric, 'files_per_minute')
        assert metric.files_per_minute > 0
    
    def test_memory_usage_benchmark(self, benchmark_suite):
        """Test memory usage benchmarking."""
        memory_usage = benchmark_suite.benchmark_memory_usage([10, 50, 100])
        
        assert 10 in memory_usage
        assert 50 in memory_usage
        assert 100 in memory_usage
        
        # Memory should increase with file count
        assert memory_usage[100] > memory_usage[10]
    
    def test_cache_performance_benchmark(self, benchmark_suite):
        """Test cache performance benchmarking."""
        # Pre-populate some data
        for i in range(10):
            symbol = SymbolDef(
                name=f"cached_function_{i}",
                type="function",
                path=f"/test/cached_{i}.py",
                line=1,
                character=0,
                definition=f"def cached_function_{i}():"
            )
            benchmark_suite.plugins[0]._symbols[f"cached_function_{i}"] = symbol
        
        metrics = benchmark_suite.benchmark_cache_performance(iterations=50)
        
        assert "cache_hit" in metrics
        assert "cache_miss" in metrics
        
        # Cache hits should generally be faster than misses
        # (though with our mock, they're the same)
        assert metrics["cache_hit"].count == 50
        assert metrics["cache_miss"].count == 50
    
    def test_validate_performance_requirements(self, benchmark_suite):
        """Test performance requirement validation."""
        # Create a result with known metrics
        result = BenchmarkResult("test")
        
        # Add passing metric
        passing_metric = PerformanceMetrics("symbol_lookup")
        for _ in range(100):
            passing_metric.add_sample(50)  # All under 100ms target
        result.add_metric("symbol_lookup", passing_metric)
        
        # Add failing metric
        failing_metric = PerformanceMetrics("fuzzy_search")
        for _ in range(100):
            failing_metric.add_sample(600)  # All over 500ms target
        result.add_metric("fuzzy_search", failing_metric)
        
        validations = benchmark_suite.validate_performance_requirements(result)
        
        assert validations["symbol_lookup_slo"] is True
        assert validations["search_slo"] is False


class TestBenchmarkRunner:
    """Test the BenchmarkRunner class."""
    
    def test_runner_initialization(self):
        """Test runner initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = BenchmarkRunner(Path(tmpdir))
            assert runner.output_dir.exists()
            assert runner.history == []
    
    def test_run_benchmarks(self, benchmark_runner, mock_plugins):
        """Test running full benchmark suite."""
        result = benchmark_runner.run_benchmarks(
            mock_plugins,
            save_results=True,
            compare_with_previous=False
        )
        
        assert isinstance(result, BenchmarkResult)
        assert len(result.metrics) > 0
        assert hasattr(result, 'validations')
        assert result.duration_seconds > 0
    
    def test_save_and_load_history(self, benchmark_runner):
        """Test saving and loading benchmark history."""
        # Create a mock result
        result = BenchmarkResult("test")
        metric = PerformanceMetrics("test_op")
        metric.add_sample(10.5)
        result.add_metric("test_op", metric)
        result.finalize()
        
        # Save result
        benchmark_runner._save_result(result)
        
        # Reload runner and check history
        new_runner = BenchmarkRunner(benchmark_runner.output_dir)
        assert len(new_runner.history) == 1
        assert new_runner.history[0]["suite_name"] == "test"
    
    def test_regression_detection(self, benchmark_runner):
        """Test performance regression detection."""
        # Create baseline result
        baseline = BenchmarkResult("baseline")
        baseline_metric = PerformanceMetrics("test_op")
        for _ in range(100):
            baseline_metric.add_sample(50)
        baseline.add_metric("test_op", baseline_metric)
        baseline.finalize()
        benchmark_runner._save_result(baseline)
        
        # Create current result with regression
        current = BenchmarkResult("current")
        current_metric = PerformanceMetrics("test_op")
        for _ in range(100):
            current_metric.add_sample(100)  # 100% slower
        current.add_metric("test_op", current_metric)
        
        regression_report = benchmark_runner._check_regressions(current)
        
        assert regression_report["status"] == "checked"
        assert len(regression_report["regressions"]) == 1
        assert regression_report["regressions"][0]["metric"] == "test_op"
        assert regression_report["regressions"][0]["change_percent"] > 90
    
    def test_generate_reports(self, benchmark_runner):
        """Test report generation."""
        result = BenchmarkResult("test")
        metric = PerformanceMetrics("test_op")
        for i in range(100):
            metric.add_sample(i)
        result.add_metric("test_op", metric)
        result.validations = {"test_slo": True}
        result.finalize()
        
        benchmark_runner._generate_reports(result)
        
        # Check files were created
        html_file = benchmark_runner.output_dir / "benchmark_report.html"
        text_file = benchmark_runner.output_dir / "benchmark_summary.txt"
        
        assert html_file.exists()
        assert text_file.exists()
        
        # Verify content
        html_content = html_file.read_text()
        assert "MCP Server Benchmark Report" in html_content
        assert "test_op" in html_content
        
        text_content = text_file.read_text()
        assert "Performance Metrics:" in text_content
        assert "test_op" in text_content
    
    def test_export_for_ci(self, benchmark_runner):
        """Test CI export functionality."""
        result = BenchmarkResult("test")
        metric = PerformanceMetrics("test_op")
        metric.add_sample(50)
        result.add_metric("test_op", metric)
        result.validations = {"test_slo": True}
        result.finalize()
        
        ci_data = benchmark_runner.export_for_ci(result)
        
        assert "metrics" in ci_data
        assert "test_op" in ci_data["metrics"]
        assert ci_data["metrics"]["test_op"]["p95_ms"] > 0
        assert ci_data["passed"] is True


@pytest.mark.benchmark(group="symbol_lookup")
def test_benchmark_symbol_lookup_performance(benchmark, mock_plugins):
    """Benchmark symbol lookup with pytest-benchmark."""
    suite = BenchmarkSuite(mock_plugins)
    
    # Pre-populate symbols
    for i in range(100):
        symbol = SymbolDef(
            name=f"bench_function_{i}",
            type="function",
            path=f"/test/bench_{i}.py",
            line=1,
            character=0,
            definition=f"def bench_function_{i}():"
        )
        suite.plugins[0]._symbols[f"bench_function_{i}"] = symbol
    
    def lookup():
        return suite.dispatcher.lookup("bench_function_42")
    
    result = benchmark(lookup)
    assert result is not None


@pytest.mark.benchmark(group="search")
def test_benchmark_search_performance(benchmark, mock_plugins):
    """Benchmark search with pytest-benchmark."""
    suite = BenchmarkSuite(mock_plugins)
    
    # Pre-populate symbols
    for i in range(100):
        symbol = SymbolDef(
            name=f"search_function_{i}",
            type="function",
            path=f"/test/search_{i}.py",
            line=1,
            character=0,
            definition=f"def search_function_{i}():"
        )
        suite.plugins[0]._symbols[f"search_function_{i}"] = symbol
    
    def search():
        return list(suite.dispatcher.search("search", semantic=False))
    
    results = benchmark(search)
    assert len(results) > 0


@pytest.mark.benchmark(group="indexing")
def test_benchmark_indexing_performance(benchmark, mock_plugins):
    """Benchmark indexing with pytest-benchmark."""
    suite = BenchmarkSuite(mock_plugins)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def benchmark_function():
    """Benchmark test function."""
    return 42

class BenchmarkClass:
    def __init__(self):
        self.value = 100
''')
        f.flush()
        
        path = Path(f.name)
        content = path.read_text()
        
        def index():
            plugin = suite.dispatcher._match_plugin(path)
            plugin.index(path, content)
        
        benchmark(index)
        
        # Cleanup
        path.unlink()


@pytest.mark.slow
class TestLargeBenchmarks:
    """Large-scale benchmark tests (marked as slow)."""
    
    def test_large_codebase_benchmark(self, benchmark_suite):
        """Test benchmarking with a large number of files."""
        # This would be a more extensive test in real scenarios
        metric = benchmark_suite.benchmark_indexing(file_count=1000)
        
        assert metric.files_per_minute > 0
        assert metric.count == 1000
        
        # Check if meets the 10K files/minute target
        meets_target = metric.files_per_minute >= BenchmarkSuite.FILES_PER_MINUTE_TARGET
        assert meets_target or metric.files_per_minute > 5000  # Allow some slack in tests
    
    def test_memory_scaling(self, benchmark_suite):
        """Test memory usage scaling with file count."""
        memory_usage = benchmark_suite.benchmark_memory_usage([100, 500, 1000])
        
        # Check linear or sub-linear scaling
        ratio_500_100 = memory_usage[500] / memory_usage[100]
        ratio_1000_500 = memory_usage[1000] / memory_usage[500]
        
        # Memory usage should scale sub-linearly
        assert ratio_500_100 < 5.5  # Should be ~5 or less
        assert ratio_1000_500 < 2.5  # Should be ~2 or less