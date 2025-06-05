"""
Performance testing base class for language plugins.

This module provides comprehensive performance testing capabilities including
benchmarking, profiling, memory usage analysis, and scalability testing.
"""

import abc
import gc
import time
import tracemalloc
import threading
import statistics
from pathlib import Path
from typing import Type, List, Dict, Any, Optional, Callable
from unittest.mock import Mock
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from mcp_server.plugin_base import IPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from ..test_data.test_data_manager import TestDataManager


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation: str
    duration: float
    memory_peak: int
    memory_current: int
    cpu_usage: Optional[float] = None
    throughput: Optional[float] = None
    error_rate: Optional[float] = None


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    test_name: str
    metrics: List[PerformanceMetrics]
    summary: Dict[str, Any]
    iterations: int
    total_duration: float


class PerformanceTestBase(abc.ABC):
    """
    Base class for performance testing of language plugins.
    
    Provides comprehensive performance testing including:
    - Execution time benchmarks
    - Memory usage analysis  
    - Concurrency testing
    - Scalability analysis
    - Parser backend comparisons
    """
    
    # Abstract attributes that must be defined by subclasses
    plugin_class: Type[IPlugin] = None
    language: str = None
    file_extensions: List[str] = []
    
    # Performance thresholds (can be overridden by subclasses)
    max_indexing_time_small = 1.0  # seconds for small files
    max_indexing_time_medium = 5.0  # seconds for medium files  
    max_indexing_time_large = 30.0  # seconds for large files
    max_memory_usage = 100 * 1024 * 1024  # 100MB
    min_throughput_files_per_second = 10.0
    
    @classmethod
    def setup_class(cls):
        """Set up test class with validation."""
        if cls.plugin_class is None:
            raise ValueError(f"{cls.__name__} must define plugin_class")
        if cls.language is None:
            raise ValueError(f"{cls.__name__} must define language")
        if not cls.file_extensions:
            raise ValueError(f"{cls.__name__} must define file_extensions")
        
        cls.test_data_manager = TestDataManager(cls.language)
        cls.benchmark_results = []
        
    def setup_method(self):
        """Set up each test method."""
        self.plugin = self.plugin_class()
        self.mock_sqlite_store = Mock(spec=SQLiteStore)
        
    def teardown_method(self):
        """Clean up after each test method."""
        # Force garbage collection
        gc.collect()
    
    # ===== Core Performance Testing Methods =====
    
    def measure_execution_time(self, operation: Callable, *args, **kwargs) -> PerformanceMetrics:
        """Measure execution time and memory usage of an operation."""
        # Start memory tracing
        tracemalloc.start()
        
        # Record start time
        start_time = time.time()
        
        # Execute operation
        try:
            result = operation(*args, **kwargs)
            error_occurred = False
        except Exception as e:
            result = None
            error_occurred = True
        
        # Record end time
        end_time = time.time()
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return PerformanceMetrics(
            operation=operation.__name__,
            duration=end_time - start_time,
            memory_peak=peak,
            memory_current=current,
            error_rate=1.0 if error_occurred else 0.0
        )
    
    def run_benchmark(self, test_name: str, operation: Callable, iterations: int = 10, 
                     *args, **kwargs) -> BenchmarkResult:
        """Run a benchmark with multiple iterations."""
        metrics = []
        total_start = time.time()
        
        for i in range(iterations):
            # Force garbage collection between iterations
            gc.collect()
            
            metric = self.measure_execution_time(operation, *args, **kwargs)
            metrics.append(metric)
        
        total_end = time.time()
        
        # Calculate summary statistics
        durations = [m.duration for m in metrics]
        memory_peaks = [m.memory_peak for m in metrics]
        error_rates = [m.error_rate for m in metrics]
        
        summary = {
            "duration_mean": statistics.mean(durations),
            "duration_median": statistics.median(durations),
            "duration_stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "duration_min": min(durations),
            "duration_max": max(durations),
            "memory_peak_mean": statistics.mean(memory_peaks),
            "memory_peak_max": max(memory_peaks),
            "error_rate": statistics.mean(error_rates),
            "throughput": iterations / sum(durations) if sum(durations) > 0 else 0
        }
        
        result = BenchmarkResult(
            test_name=test_name,
            metrics=metrics,
            summary=summary,
            iterations=iterations,
            total_duration=total_end - total_start
        )
        
        self.benchmark_results.append(result)
        return result
    
    # ===== File Size Benchmarks =====
    
    def test_small_file_performance(self):
        """Benchmark performance on small files (< 1KB)."""
        def index_small_file():
            content = self.test_data_manager.generate_small_file(5)  # ~5 symbols
            return self.plugin.indexFile(
                Path(f"small{self.file_extensions[0]}"), content
            )
        
        result = self.run_benchmark(
            "small_file_indexing", 
            index_small_file, 
            iterations=50
        )
        
        # Performance assertions
        assert result.summary["duration_mean"] <= self.max_indexing_time_small, \
            f"Small file indexing too slow: {result.summary['duration_mean']:.3f}s"
        
        assert result.summary["error_rate"] == 0.0, \
            f"Errors occurred during small file indexing: {result.summary['error_rate']}"
        
        return result
    
    def test_medium_file_performance(self):
        """Benchmark performance on medium files (1-10KB).""" 
        def index_medium_file():
            content = self.test_data_manager.generate_medium_file(50)  # ~50 symbols
            return self.plugin.indexFile(
                Path(f"medium{self.file_extensions[0]}"), content
            )
        
        result = self.run_benchmark(
            "medium_file_indexing",
            index_medium_file,
            iterations=20
        )
        
        # Performance assertions
        assert result.summary["duration_mean"] <= self.max_indexing_time_medium, \
            f"Medium file indexing too slow: {result.summary['duration_mean']:.3f}s"
        
        assert result.summary["error_rate"] == 0.0, \
            f"Errors occurred during medium file indexing: {result.summary['error_rate']}"
        
        return result
    
    def test_large_file_performance(self):
        """Benchmark performance on large files (> 10KB)."""
        def index_large_file():
            content = self.test_data_manager.generate_large_file(500)  # ~500 symbols
            return self.plugin.indexFile(
                Path(f"large{self.file_extensions[0]}"), content
            )
        
        result = self.run_benchmark(
            "large_file_indexing",
            index_large_file, 
            iterations=5
        )
        
        # Performance assertions
        assert result.summary["duration_mean"] <= self.max_indexing_time_large, \
            f"Large file indexing too slow: {result.summary['duration_mean']:.3f}s"
        
        assert result.summary["error_rate"] == 0.0, \
            f"Errors occurred during large file indexing: {result.summary['error_rate']}"
        
        return result
    
    # ===== Memory Usage Tests =====
    
    def test_memory_usage_scaling(self):
        """Test memory usage scaling with file size."""
        file_sizes = [10, 50, 100, 200, 500]  # Number of symbols
        memory_usage = []
        
        for size in file_sizes:
            content = self.test_data_manager.generate_medium_file(size)
            
            metric = self.measure_execution_time(
                self.plugin.indexFile,
                Path(f"memory_test_{size}{self.file_extensions[0]}"),
                content
            )
            
            memory_usage.append((size, metric.memory_peak))
            
            # Check memory doesn't exceed threshold
            assert metric.memory_peak <= self.max_memory_usage, \
                f"Memory usage too high for {size} symbols: {metric.memory_peak} bytes"
        
        # Check memory scaling is reasonable (should be roughly linear)
        sizes, memories = zip(*memory_usage)
        
        # Memory growth should not be exponential
        memory_ratios = []
        for i in range(1, len(memories)):
            ratio = memories[i] / memories[i-1]
            size_ratio = sizes[i] / sizes[i-1]
            memory_ratios.append(ratio / size_ratio)
        
        # Memory growth should be roughly proportional to content size
        avg_memory_ratio = statistics.mean(memory_ratios)
        assert avg_memory_ratio <= 3.0, \
            f"Memory usage growing too fast: {avg_memory_ratio}x per unit increase"
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        initial_memory = self._get_current_memory()
        
        # Index many files
        for i in range(100):
            content = self.test_data_manager.generate_small_file(10)
            self.plugin.indexFile(
                Path(f"leak_test_{i}{self.file_extensions[0]}"), content
            )
            
            # Periodic garbage collection
            if i % 20 == 0:
                gc.collect()
        
        final_memory = self._get_current_memory()
        
        # Memory should not grow excessively
        memory_growth = final_memory - initial_memory
        assert memory_growth <= 50 * 1024 * 1024, \
            f"Potential memory leak detected: {memory_growth} bytes growth"
    
    def _get_current_memory(self) -> int:
        """Get current memory usage."""
        tracemalloc.start()
        current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return current
    
    # ===== Concurrency Tests =====
    
    def test_concurrent_indexing_performance(self):
        """Test performance under concurrent load."""
        def index_concurrent_file(file_id: int):
            content = self.test_data_manager.generate_medium_file(25)
            return self.plugin.indexFile(
                Path(f"concurrent_{file_id}{self.file_extensions[0]}"), content
            )
        
        num_threads = 4
        files_per_thread = 10
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for thread_id in range(num_threads):
                for file_id in range(files_per_thread):
                    future = executor.submit(
                        index_concurrent_file, 
                        thread_id * files_per_thread + file_id
                    )
                    futures.append(future)
            
            # Wait for all to complete
            results = []
            errors = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    errors += 1
        
        end_time = time.time()
        
        total_files = num_threads * files_per_thread
        throughput = total_files / (end_time - start_time)
        
        # Performance assertions
        assert errors == 0, f"Errors during concurrent indexing: {errors}/{total_files}"
        assert throughput >= self.min_throughput_files_per_second, \
            f"Concurrent throughput too low: {throughput:.1f} files/sec"
        
        # All results should be valid
        assert len(results) == total_files
        for result in results:
            assert isinstance(result, dict)
            assert result.get("language") == self.language
    
    def test_thread_safety(self):
        """Test thread safety of plugin operations."""
        content = self.test_data_manager.generate_medium_file(30)
        
        def index_same_content(thread_id: int):
            return self.plugin.indexFile(
                Path(f"thread_safety_{thread_id}{self.file_extensions[0]}"), 
                content
            )
        
        num_threads = 8
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(index_same_content, i) 
                for i in range(num_threads)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # All results should be identical (or at least consistent)
        assert len(results) == num_threads
        
        # Compare symbol counts - should be consistent
        symbol_counts = [len(result.get("symbols", [])) for result in results]
        assert len(set(symbol_counts)) <= 1, \
            f"Inconsistent results across threads: {symbol_counts}"
    
    # ===== Parser Backend Comparison =====
    
    def test_parser_backend_performance(self):
        """Compare performance across different parser backends."""
        if not hasattr(self.plugin, 'get_parser_info'):
            pytest.skip("Plugin does not support multiple parser backends")
        
        parser_info = self.plugin.get_parser_info()
        available_backends = parser_info.get("available_backends", [])
        
        if len(available_backends) <= 1:
            pytest.skip("Plugin only has one parser backend available")
        
        backend_results = {}
        content = self.test_data_manager.generate_medium_file(100)
        
        for backend in available_backends:
            if self.plugin.switch_parser_backend(backend):
                result = self.run_benchmark(
                    f"backend_{backend}_indexing",
                    self.plugin.indexFile,
                    10,  # iterations
                    Path(f"backend_test{self.file_extensions[0]}"),
                    content
                )
                backend_results[backend] = result
        
        # Compare backend performance
        if len(backend_results) >= 2:
            durations = {
                backend: result.summary["duration_mean"] 
                for backend, result in backend_results.items()
            }
            
            fastest_backend = min(durations, key=durations.get)
            slowest_backend = max(durations, key=durations.get)
            
            speed_ratio = durations[slowest_backend] / durations[fastest_backend]
            
            print(f"Backend performance comparison:")
            for backend, duration in durations.items():
                print(f"  {backend}: {duration:.3f}s avg")
            print(f"Speed ratio (slowest/fastest): {speed_ratio:.2f}x")
    
    # ===== Scalability Tests =====
    
    def test_symbol_count_scaling(self):
        """Test performance scaling with number of symbols."""
        symbol_counts = [10, 25, 50, 100, 200, 500]
        scaling_results = []
        
        for count in symbol_counts:
            content = self.test_data_manager.generate_medium_file(count)
            
            metric = self.measure_execution_time(
                self.plugin.indexFile,
                Path(f"scaling_{count}{self.file_extensions[0]}"),
                content
            )
            
            scaling_results.append({
                "symbol_count": count,
                "duration": metric.duration,
                "memory_peak": metric.memory_peak,
                "throughput": count / metric.duration if metric.duration > 0 else 0
            })
        
        # Analyze scaling characteristics
        for i, result in enumerate(scaling_results):
            print(f"Symbols: {result['symbol_count']:3d}, "
                  f"Time: {result['duration']:.3f}s, "
                  f"Memory: {result['memory_peak']//1024:4d}KB, "
                  f"Throughput: {result['throughput']:.1f} symbols/s")
        
        # Performance should not degrade exponentially
        for i in range(1, len(scaling_results)):
            prev = scaling_results[i-1]
            curr = scaling_results[i]
            
            symbol_ratio = curr["symbol_count"] / prev["symbol_count"] 
            time_ratio = curr["duration"] / prev["duration"]
            
            # Time complexity should be reasonable (not worse than O(n^2))
            assert time_ratio <= symbol_ratio ** 1.5, \
                f"Performance degradation too severe: {time_ratio:.2f}x time for " \
                f"{symbol_ratio:.2f}x symbols"
    
    def test_file_count_scaling(self):
        """Test performance when indexing multiple files sequentially."""
        file_counts = [1, 5, 10, 20, 50]
        
        for count in file_counts:
            def index_multiple_files():
                for i in range(count):
                    content = self.test_data_manager.generate_small_file(10)
                    self.plugin.indexFile(
                        Path(f"multi_{count}_{i}{self.file_extensions[0]}"), 
                        content
                    )
            
            result = self.run_benchmark(
                f"multiple_files_{count}",
                index_multiple_files,
                iterations=3
            )
            
            # Performance should scale roughly linearly with file count
            expected_max_time = count * self.max_indexing_time_small * 1.5
            assert result.summary["duration_mean"] <= expected_max_time, \
                f"Multiple file indexing too slow for {count} files: " \
                f"{result.summary['duration_mean']:.3f}s"
    
    # ===== Performance Regression Tests =====
    
    def test_performance_regression(self):
        """Test for performance regressions against baseline."""
        # This would typically compare against stored baseline metrics
        # For now, just ensure basic performance requirements are met
        
        baseline_tests = [
            ("small_file", self.test_small_file_performance),
            ("medium_file", self.test_medium_file_performance), 
            ("large_file", self.test_large_file_performance)
        ]
        
        regression_detected = False
        
        for test_name, test_method in baseline_tests:
            try:
                result = test_method()
                
                # Store result for future baseline comparison
                # In a real implementation, this would compare against stored baselines
                print(f"{test_name} performance: {result.summary['duration_mean']:.3f}s avg")
                
            except AssertionError as e:
                print(f"Performance regression detected in {test_name}: {e}")
                regression_detected = True
        
        assert not regression_detected, "Performance regressions detected"
    
    # ===== Utility Methods =====
    
    def save_benchmark_results(self, filename: Optional[str] = None):
        """Save benchmark results to JSON file."""
        import json
        from datetime import datetime
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{self.language}_{timestamp}.json"
        
        results_data = {
            "language": self.language,
            "plugin_class": self.plugin_class.__name__,
            "timestamp": datetime.now().isoformat(),
            "results": []
        }
        
        for result in self.benchmark_results:
            result_data = {
                "test_name": result.test_name,
                "iterations": result.iterations,
                "total_duration": result.total_duration,
                "summary": result.summary,
                "metrics": [
                    {
                        "operation": m.operation,
                        "duration": m.duration,
                        "memory_peak": m.memory_peak,
                        "memory_current": m.memory_current,
                        "error_rate": m.error_rate
                    }
                    for m in result.metrics
                ]
            }
            results_data["results"].append(result_data)
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"Benchmark results saved to: {filename}")
    
    def print_performance_summary(self):
        """Print a summary of all performance test results."""
        print(f"\n=== Performance Summary for {self.language} Plugin ===")
        print(f"Plugin class: {self.plugin_class.__name__}")
        print(f"Total benchmarks run: {len(self.benchmark_results)}")
        
        for result in self.benchmark_results:
            print(f"\n{result.test_name}:")
            print(f"  Iterations: {result.iterations}")
            print(f"  Avg duration: {result.summary['duration_mean']:.3f}s")
            print(f"  Peak memory: {result.summary['memory_peak_max']//1024:,}KB")
            print(f"  Error rate: {result.summary['error_rate']:.1%}")
            if result.summary.get('throughput'):
                print(f"  Throughput: {result.summary['throughput']:.1f} ops/sec")