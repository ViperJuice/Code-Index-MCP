"""
Comprehensive benchmark suite for MCP Server components.

This module defines benchmarks for:
- Symbol lookup performance (< 100ms p95)
- Search performance (< 500ms p95)
- Indexing throughput (10K files/minute target)
- Memory usage for large codebases
- Cache performance metrics
"""

import time
import psutil
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import logging

from ..dispatcher import Dispatcher
from ..gateway import Gateway
from ..plugin_base import IPlugin, SymbolDef, SearchResult
from ..storage.sqlite_store import SQLiteStore
from ..watcher import FileWatcher

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    operation: str
    samples: List[float] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def count(self) -> int:
        return len(self.samples)
    
    @property
    def mean(self) -> float:
        return np.mean(self.samples) if self.samples else 0.0
    
    @property
    def median(self) -> float:
        return np.median(self.samples) if self.samples else 0.0
    
    @property
    def p95(self) -> float:
        return np.percentile(self.samples, 95) if self.samples else 0.0
    
    @property
    def p99(self) -> float:
        return np.percentile(self.samples, 99) if self.samples else 0.0
    
    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0
    
    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0
    
    def add_sample(self, duration_ms: float):
        """Add a timing sample in milliseconds."""
        self.samples.append(duration_ms)
    
    def is_within_slo(self, target_p95_ms: float) -> bool:
        """Check if p95 latency is within target."""
        return self.p95 <= target_p95_ms


@dataclass
class BenchmarkResult:
    """Container for complete benchmark results."""
    suite_name: str
    metrics: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def add_metric(self, name: str, metric: PerformanceMetrics):
        """Add a performance metric to results."""
        self.metrics[name] = metric
    
    def add_error(self, error: str):
        """Record an error during benchmarking."""
        self.errors.append(error)
        logger.error(f"Benchmark error: {error}")
    
    def finalize(self):
        """Mark benchmark completion."""
        self.end_time = datetime.now()


class BenchmarkSuite:
    """Main benchmark suite for MCP Server performance validation."""
    
    # Performance SLOs from requirements
    SYMBOL_LOOKUP_TARGET_MS = 100  # p95 < 100ms
    SEARCH_TARGET_MS = 500         # p95 < 500ms
    CODE_SEARCH_TARGET_MS = 200    # p95 < 200ms
    INDEX_STATUS_TARGET_MS = 50    # p95 < 50ms
    FILES_PER_MINUTE_TARGET = 10000  # 10K files/minute
    MEMORY_TARGET_MB_PER_100K = 2048  # < 2GB for 100K files
    
    def __init__(self, plugins: List[IPlugin], db_path: Optional[Path] = None):
        self.plugins = plugins
        self.dispatcher = Dispatcher(plugins)
        self.db_path = db_path or Path(tempfile.mktemp(suffix=".db"))
        self.store = SQLiteStore(self.db_path)
        self.gateway = Gateway(self.dispatcher, self.store)
        self._process = psutil.Process(os.getpid())
        
    def _measure_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time in milliseconds."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000
        return result, duration_ms
    
    def _measure_memory(self) -> float:
        """Measure current memory usage in MB."""
        return self._process.memory_info().rss / (1024 * 1024)
    
    def _measure_cpu(self) -> float:
        """Measure CPU usage percentage."""
        return self._process.cpu_percent(interval=0.1)
    
    def _generate_test_files(self, count: int, base_path: Path) -> List[Path]:
        """Generate test files for benchmarking."""
        files = []
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Generate diverse file content
        templates = {
            ".py": '''
def function_{idx}(param1, param2):
    """Test function {idx}."""
    result = param1 + param2
    return result * {idx}

class TestClass{idx}:
    def __init__(self):
        self.value = {idx}
    
    def method_{idx}(self):
        return self.value ** 2
''',
            ".js": '''
function testFunction{idx}(a, b) {{
    return a + b + {idx};
}}

class TestClass{idx} {{
    constructor() {{
        this.value = {idx};
    }}
    
    method{idx}() {{
        return this.value * this.value;
    }}
}}
''',
            ".c": '''
#include <stdio.h>

int function_{idx}(int a, int b) {{
    return a + b + {idx};
}}

typedef struct {{
    int value;
}} TestStruct{idx};

void test_method_{idx}(TestStruct{idx}* s) {{
    s->value = {idx};
}}
'''
        }
        
        for i in range(count):
            # Rotate through different file types
            ext = list(templates.keys())[i % len(templates)]
            content = templates[ext].format(idx=i)
            
            # Create subdirectories for realistic structure
            subdir = f"module_{i // 100}"
            file_path = base_path / subdir / f"test_file_{i}{ext}"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content)
            files.append(file_path)
        
        return files
    
    def benchmark_symbol_lookup(self, iterations: int = 1000) -> PerformanceMetrics:
        """Benchmark symbol lookup performance."""
        metric = PerformanceMetrics("symbol_lookup")
        
        # Generate test symbols
        test_symbols = [
            f"function_{i}" for i in range(100)
        ] + [
            f"TestClass{i}" for i in range(100)
        ] + [
            f"method_{i}" for i in range(100)
        ]
        
        # Warm up
        for _ in range(10):
            self.dispatcher.lookup(test_symbols[0])
        
        # Benchmark
        for i in range(iterations):
            symbol = test_symbols[i % len(test_symbols)]
            _, duration_ms = self._measure_time(self.dispatcher.lookup, symbol)
            metric.add_sample(duration_ms)
        
        metric.memory_usage_mb = self._measure_memory()
        metric.cpu_percent = self._measure_cpu()
        
        return metric
    
    def benchmark_search(self, iterations: int = 500) -> Dict[str, PerformanceMetrics]:
        """Benchmark different search operations."""
        metrics = {}
        
        # Test different search types
        search_tests = [
            ("fuzzy_search", {"query": "test", "semantic": False}),
            ("semantic_search", {"query": "calculate sum", "semantic": True}),
            ("regex_search", {"query": "function_[0-9]+", "semantic": False}),
        ]
        
        for test_name, search_params in search_tests:
            metric = PerformanceMetrics(test_name)
            
            # Warm up
            for _ in range(5):
                list(self.dispatcher.search(**search_params))
            
            # Benchmark
            for _ in range(iterations):
                _, duration_ms = self._measure_time(
                    lambda: list(self.dispatcher.search(**search_params))
                )
                metric.add_sample(duration_ms)
            
            metric.memory_usage_mb = self._measure_memory()
            metric.cpu_percent = self._measure_cpu()
            metrics[test_name] = metric
        
        return metrics
    
    def benchmark_indexing(self, file_count: int = 1000) -> PerformanceMetrics:
        """Benchmark file indexing throughput."""
        metric = PerformanceMetrics("indexing_throughput")
        
        # Create test files
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir)
            test_files = self._generate_test_files(file_count, test_path)
            
            # Measure indexing time
            start_time = time.perf_counter()
            indexed_count = 0
            
            for file_path in test_files:
                try:
                    plugin = self.dispatcher._match_plugin(file_path)
                    content = file_path.read_text()
                    
                    _, duration_ms = self._measure_time(
                        plugin.index, file_path, content
                    )
                    metric.add_sample(duration_ms)
                    indexed_count += 1
                except Exception as e:
                    logger.error(f"Indexing error for {file_path}: {e}")
            
            total_time_seconds = time.perf_counter() - start_time
            files_per_minute = (indexed_count / total_time_seconds) * 60
            
            # Store throughput as a special metric
            metric.files_per_minute = files_per_minute
            metric.memory_usage_mb = self._measure_memory()
            metric.cpu_percent = self._measure_cpu()
        
        return metric
    
    def benchmark_memory_usage(self, file_counts: List[int] = None) -> Dict[int, float]:
        """Benchmark memory usage for different codebase sizes."""
        if file_counts is None:
            file_counts = [100, 1000, 10000]
        
        memory_usage = {}
        
        for count in file_counts:
            # Reset state
            self.dispatcher._file_cache.clear()
            if hasattr(self, 'store'):
                self.store._conn.execute("DELETE FROM files")
                self.store._conn.execute("DELETE FROM symbols")
                self.store._conn.commit()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            initial_memory = self._measure_memory()
            
            # Index files
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir)
                test_files = self._generate_test_files(count, test_path)
                
                for file_path in test_files:
                    try:
                        plugin = self.dispatcher._match_plugin(file_path)
                        content = file_path.read_text()
                        plugin.index(file_path, content)
                    except Exception as e:
                        logger.error(f"Memory benchmark error: {e}")
                
                # Measure memory after indexing
                final_memory = self._measure_memory()
                memory_usage[count] = final_memory - initial_memory
        
        return memory_usage
    
    def benchmark_cache_performance(self, iterations: int = 1000) -> Dict[str, PerformanceMetrics]:
        """Benchmark cache hit/miss performance."""
        metrics = {}
        
        # Setup test data
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir)
            test_files = self._generate_test_files(100, test_path)
            
            # Index files first
            for file_path in test_files:
                try:
                    plugin = self.dispatcher._match_plugin(file_path)
                    content = file_path.read_text()
                    plugin.index(file_path, content)
                except Exception:
                    pass
            
            # Test cache hits (repeated queries)
            cache_hit_metric = PerformanceMetrics("cache_hit")
            test_symbol = "function_0"
            
            for _ in range(iterations):
                _, duration_ms = self._measure_time(
                    self.dispatcher.lookup, test_symbol
                )
                cache_hit_metric.add_sample(duration_ms)
            
            # Test cache misses (unique queries)
            cache_miss_metric = PerformanceMetrics("cache_miss")
            
            for i in range(iterations):
                unique_symbol = f"nonexistent_symbol_{i}"
                _, duration_ms = self._measure_time(
                    self.dispatcher.lookup, unique_symbol
                )
                cache_miss_metric.add_sample(duration_ms)
            
            metrics["cache_hit"] = cache_hit_metric
            metrics["cache_miss"] = cache_miss_metric
        
        return metrics
    
    def run_all_benchmarks(self) -> BenchmarkResult:
        """Run complete benchmark suite."""
        result = BenchmarkResult("MCP Server Performance Benchmark")
        
        try:
            # Symbol lookup benchmark
            logger.info("Running symbol lookup benchmark...")
            symbol_metric = self.benchmark_symbol_lookup()
            result.add_metric("symbol_lookup", symbol_metric)
            
            # Search benchmarks
            logger.info("Running search benchmarks...")
            search_metrics = self.benchmark_search()
            for name, metric in search_metrics.items():
                result.add_metric(name, metric)
            
            # Indexing benchmark
            logger.info("Running indexing benchmark...")
            indexing_metric = self.benchmark_indexing()
            result.add_metric("indexing", indexing_metric)
            
            # Cache performance
            logger.info("Running cache performance benchmark...")
            cache_metrics = self.benchmark_cache_performance()
            for name, metric in cache_metrics.items():
                result.add_metric(name, metric)
            
            # Memory usage benchmark
            logger.info("Running memory usage benchmark...")
            memory_usage = self.benchmark_memory_usage()
            memory_metric = PerformanceMetrics("memory_usage")
            memory_metric.memory_per_file_count = memory_usage
            result.add_metric("memory_usage", memory_metric)
            
        except Exception as e:
            result.add_error(f"Benchmark suite error: {str(e)}")
            logger.exception("Benchmark suite failed")
        finally:
            result.finalize()
        
        return result
    
    def validate_performance_requirements(self, result: BenchmarkResult) -> Dict[str, bool]:
        """Validate results against performance requirements."""
        validations = {}
        
        # Symbol lookup < 100ms (p95)
        if "symbol_lookup" in result.metrics:
            metric = result.metrics["symbol_lookup"]
            validations["symbol_lookup_slo"] = metric.is_within_slo(self.SYMBOL_LOOKUP_TARGET_MS)
        
        # Search < 500ms (p95)
        if "fuzzy_search" in result.metrics:
            metric = result.metrics["fuzzy_search"]
            validations["search_slo"] = metric.is_within_slo(self.SEARCH_TARGET_MS)
        
        # Indexing throughput
        if "indexing" in result.metrics:
            metric = result.metrics["indexing"]
            if hasattr(metric, 'files_per_minute'):
                validations["indexing_throughput"] = metric.files_per_minute >= self.FILES_PER_MINUTE_TARGET
        
        # Memory usage
        if "memory_usage" in result.metrics:
            metric = result.metrics["memory_usage"]
            if hasattr(metric, 'memory_per_file_count') and 10000 in metric.memory_per_file_count:
                # Extrapolate to 100K files
                mb_per_10k = metric.memory_per_file_count[10000]
                mb_per_100k = mb_per_10k * 10
                validations["memory_usage"] = mb_per_100k <= self.MEMORY_TARGET_MB_PER_100K
        
        return validations