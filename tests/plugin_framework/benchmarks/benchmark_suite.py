"""
Comprehensive benchmark suite for language plugin performance testing.

This module provides standardized benchmarks that can be run across
different language plugins to compare performance characteristics.
"""

import time
import gc
import tracemalloc
import statistics
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from mcp_server.plugin_base import IPlugin
from ..test_data.test_data_manager import TestDataManager


@dataclass
class BenchmarkMetric:
    """Individual benchmark metric."""
    name: str
    value: float
    unit: str
    description: str
    iteration: int = 0


@dataclass
class BenchmarkResult:
    """Results from a single benchmark test."""
    test_name: str
    plugin_name: str
    language: str
    metrics: List[BenchmarkMetric]
    duration_seconds: float
    iterations: int
    timestamp: str
    memory_peak_mb: float
    success_rate: float
    error_messages: List[str]


class BenchmarkSuite:
    """
    Comprehensive benchmark suite for language plugins.
    
    Provides standardized benchmarks including:
    - File indexing performance
    - Symbol extraction accuracy  
    - Memory usage analysis
    - Concurrent operation performance
    - Scalability testing
    """
    
    def __init__(self, plugin: IPlugin, language: str):
        """Initialize benchmark suite for a specific plugin."""
        self.plugin = plugin
        self.language = language
        self.plugin_name = plugin.__class__.__name__
        self.test_data_manager = TestDataManager(language)
        
        # Results storage
        self.results: List[BenchmarkResult] = []
        
        # Configuration
        self.default_iterations = 10
        self.warmup_iterations = 3
        
    # ===== Core Benchmark Infrastructure =====
    
    def run_benchmark(self, 
                     test_name: str,
                     operation: Callable,
                     iterations: int = None,
                     warmup: bool = True,
                     *args, **kwargs) -> BenchmarkResult:
        """Run a single benchmark test with multiple iterations."""
        if iterations is None:
            iterations = self.default_iterations
        
        print(f"Running benchmark: {test_name} ({iterations} iterations)")
        
        # Warmup runs
        if warmup:
            for _ in range(self.warmup_iterations):
                try:
                    operation(*args, **kwargs)
                except Exception:
                    pass
                gc.collect()
        
        # Actual benchmark runs
        metrics = []
        error_messages = []
        successful_runs = 0
        
        start_time = time.time()
        tracemalloc.start()
        
        for i in range(iterations):
            gc.collect()  # Clean memory before each iteration
            
            iteration_start = time.time()
            
            try:
                # Execute operation
                result = operation(*args, **kwargs)
                iteration_end = time.time()
                
                # Record metrics
                duration = iteration_end - iteration_start
                metrics.append(BenchmarkMetric(
                    name="execution_time",
                    value=duration,
                    unit="seconds",
                    description="Time to execute operation",
                    iteration=i
                ))
                
                # Extract additional metrics from result if available
                if isinstance(result, dict):
                    symbols_count = len(result.get("symbols", []))
                    metrics.append(BenchmarkMetric(
                        name="symbols_extracted",
                        value=symbols_count,
                        unit="count",
                        description="Number of symbols extracted",
                        iteration=i
                    ))
                    
                    if symbols_count > 0 and duration > 0:
                        throughput = symbols_count / duration
                        metrics.append(BenchmarkMetric(
                            name="symbol_throughput",
                            value=throughput,
                            unit="symbols/second",
                            description="Symbol extraction throughput",
                            iteration=i
                        ))
                
                successful_runs += 1
                
            except Exception as e:
                error_messages.append(f"Iteration {i}: {str(e)}")
                iteration_end = time.time()
                
                # Still record timing for failed operations
                duration = iteration_end - iteration_start
                metrics.append(BenchmarkMetric(
                    name="execution_time",
                    value=duration,
                    unit="seconds", 
                    description="Time to execute operation (failed)",
                    iteration=i
                ))
        
        # Get memory statistics
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        end_time = time.time()
        
        # Calculate summary statistics
        execution_times = [m.value for m in metrics if m.name == "execution_time"]
        
        if execution_times:
            metrics.extend([
                BenchmarkMetric("avg_execution_time", statistics.mean(execution_times), 
                              "seconds", "Average execution time"),
                BenchmarkMetric("median_execution_time", statistics.median(execution_times),
                              "seconds", "Median execution time"),
                BenchmarkMetric("min_execution_time", min(execution_times),
                              "seconds", "Minimum execution time"),
                BenchmarkMetric("max_execution_time", max(execution_times),
                              "seconds", "Maximum execution time")
            ])
            
            if len(execution_times) > 1:
                metrics.append(BenchmarkMetric(
                    "stdev_execution_time", statistics.stdev(execution_times),
                    "seconds", "Standard deviation of execution time"
                ))
        
        # Create result
        result = BenchmarkResult(
            test_name=test_name,
            plugin_name=self.plugin_name,
            language=self.language,
            metrics=metrics,
            duration_seconds=end_time - start_time,
            iterations=iterations,
            timestamp=datetime.now().isoformat(),
            memory_peak_mb=peak / (1024 * 1024),
            success_rate=successful_runs / iterations,
            error_messages=error_messages
        )
        
        self.results.append(result)
        return result
    
    # ===== Standard Benchmarks =====
    
    def benchmark_small_file_indexing(self) -> BenchmarkResult:
        """Benchmark indexing of small files."""
        def index_small_file():
            content = self.test_data_manager.generate_small_file(5)
            return self.plugin.indexFile(
                Path(f"benchmark_small.{self.language}"), content
            )
        
        return self.run_benchmark(
            "small_file_indexing",
            index_small_file,
            iterations=50
        )
    
    def benchmark_medium_file_indexing(self) -> BenchmarkResult:
        """Benchmark indexing of medium files."""
        def index_medium_file():
            content = self.test_data_manager.generate_medium_file(50)
            return self.plugin.indexFile(
                Path(f"benchmark_medium.{self.language}"), content
            )
        
        return self.run_benchmark(
            "medium_file_indexing", 
            index_medium_file,
            iterations=20
        )
    
    def benchmark_large_file_indexing(self) -> BenchmarkResult:
        """Benchmark indexing of large files."""
        def index_large_file():
            content = self.test_data_manager.generate_large_file(500)
            return self.plugin.indexFile(
                Path(f"benchmark_large.{self.language}"), content
            )
        
        return self.run_benchmark(
            "large_file_indexing",
            index_large_file,
            iterations=5
        )
    
    def benchmark_symbol_extraction_accuracy(self) -> BenchmarkResult:
        """Benchmark symbol extraction accuracy."""
        accuracy_cases = self.test_data_manager.get_accuracy_test_files()
        
        def test_accuracy():
            total_expected = 0
            total_found = 0
            
            for case in accuracy_cases:
                result = self.plugin.indexFile(Path(case.file), case.content)
                symbols = result.get("symbols", [])
                
                expected_names = {s.name for s in case.expected_symbols}
                found_names = {s.get("symbol", s.get("name")) for s in symbols}
                
                total_expected += len(expected_names)
                total_found += len(expected_names & found_names)
            
            accuracy = total_found / total_expected if total_expected > 0 else 0
            return {"accuracy": accuracy, "found": total_found, "expected": total_expected}
        
        def accuracy_operation():
            result = test_accuracy()
            # Create fake indexing result for metrics extraction
            return {
                "symbols": [{"accuracy": result["accuracy"]}],
                "accuracy_score": result["accuracy"]
            }
        
        return self.run_benchmark(
            "symbol_extraction_accuracy",
            accuracy_operation,
            iterations=10
        )
    
    def benchmark_concurrent_indexing(self) -> BenchmarkResult:
        """Benchmark concurrent file indexing performance."""
        def concurrent_indexing():
            num_threads = 4
            files_per_thread = 5
            
            def index_file(thread_id, file_id):
                content = self.test_data_manager.generate_small_file(10)
                return self.plugin.indexFile(
                    Path(f"concurrent_{thread_id}_{file_id}.{self.language}"),
                    content
                )
            
            start_time = time.time()
            successful_operations = 0
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for thread_id in range(num_threads):
                    for file_id in range(files_per_thread):
                        future = executor.submit(index_file, thread_id, file_id)
                        futures.append(future)
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        successful_operations += 1
                    except Exception:
                        pass
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = successful_operations / duration if duration > 0 else 0
            
            return {
                "symbols": [{"count": successful_operations}],
                "throughput": throughput,
                "successful_operations": successful_operations
            }
        
        return self.run_benchmark(
            "concurrent_indexing",
            concurrent_indexing,
            iterations=5
        )
    
    def benchmark_memory_usage_scaling(self) -> BenchmarkResult:
        """Benchmark memory usage scaling with file size."""
        file_sizes = [10, 25, 50, 100, 200]
        
        def memory_scaling_test():
            memory_measurements = []
            
            for size in file_sizes:
                tracemalloc.start()
                
                content = self.test_data_manager.generate_medium_file(size)
                result = self.plugin.indexFile(
                    Path(f"memory_test_{size}.{self.language}"),
                    content
                )
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                memory_measurements.append({
                    "size": size,
                    "peak_memory": peak,
                    "symbols": len(result.get("symbols", []))
                })
            
            # Calculate memory growth rate
            if len(memory_measurements) > 1:
                first = memory_measurements[0]
                last = memory_measurements[-1]
                
                size_ratio = last["size"] / first["size"]
                memory_ratio = last["peak_memory"] / first["peak_memory"]
                growth_rate = memory_ratio / size_ratio
            else:
                growth_rate = 1.0
            
            return {
                "symbols": [{"growth_rate": growth_rate}],
                "memory_growth_rate": growth_rate,
                "measurements": memory_measurements
            }
        
        return self.run_benchmark(
            "memory_usage_scaling",
            memory_scaling_test,
            iterations=3
        )
    
    def benchmark_search_performance(self) -> BenchmarkResult:
        """Benchmark search functionality performance."""
        # First, index some content
        for i in range(10):
            content = self.test_data_manager.generate_medium_file(25)
            self.plugin.indexFile(
                Path(f"search_corpus_{i}.{self.language}"), content
            )
        
        def search_operation():
            search_terms = ["function", "class", "method", "test", "data"]
            results = []
            
            for term in search_terms:
                search_results = list(self.plugin.search(term, {"limit": 10}))
                results.extend(search_results)
            
            return {
                "symbols": [{"count": len(results)}],
                "search_results": len(results)
            }
        
        return self.run_benchmark(
            "search_performance",
            search_operation,
            iterations=20
        )
    
    # ===== Scalability Benchmarks =====
    
    def benchmark_symbol_count_scaling(self) -> BenchmarkResult:
        """Benchmark performance scaling with symbol count."""
        symbol_counts = [10, 25, 50, 100, 200, 500]
        
        def scaling_test():
            timing_results = []
            
            for count in symbol_counts:
                content = self.test_data_manager.generate_medium_file(count)
                
                start_time = time.time()
                result = self.plugin.indexFile(
                    Path(f"scaling_{count}.{self.language}"),
                    content
                )
                end_time = time.time()
                
                timing_results.append({
                    "symbol_count": count,
                    "duration": end_time - start_time,
                    "actual_symbols": len(result.get("symbols", []))
                })
            
            # Calculate scaling factor
            if len(timing_results) > 1:
                # Use linear regression to estimate O(n) vs O(n^2) behavior
                import numpy as np
                
                counts = [r["symbol_count"] for r in timing_results]
                times = [r["duration"] for r in timing_results]
                
                # Fit linear model: time = a * count + b
                A = np.vstack([counts, np.ones(len(counts))]).T
                linear_coeff, _ = np.linalg.lstsq(A, times, rcond=None)[0]
                
                # Fit quadratic model: time = a * count^2 + b * count + c
                A_quad = np.vstack([np.square(counts), counts, np.ones(len(counts))]).T
                quad_coeff, _, _, _ = np.linalg.lstsq(A_quad, times, rcond=None)
                
                scaling_factor = quad_coeff[0] / linear_coeff if linear_coeff > 0 else 0
            else:
                scaling_factor = 1.0
            
            return {
                "symbols": [{"scaling_factor": scaling_factor}],
                "scaling_factor": scaling_factor,
                "measurements": timing_results
            }
        
        return self.run_benchmark(
            "symbol_count_scaling",
            scaling_test,
            iterations=3
        )
    
    def benchmark_file_count_scaling(self) -> BenchmarkResult:
        """Benchmark performance when processing multiple files."""
        file_counts = [1, 5, 10, 20, 50]
        
        def file_count_test():
            timing_results = []
            
            for count in file_counts:
                start_time = time.time()
                
                for i in range(count):
                    content = self.test_data_manager.generate_small_file(10)
                    self.plugin.indexFile(
                        Path(f"multi_{count}_{i}.{self.language}"),
                        content
                    )
                
                end_time = time.time()
                
                timing_results.append({
                    "file_count": count,
                    "duration": end_time - start_time,
                    "avg_time_per_file": (end_time - start_time) / count
                })
            
            # Calculate efficiency (should be roughly constant for linear scaling)
            avg_times = [r["avg_time_per_file"] for r in timing_results]
            efficiency = max(avg_times) / min(avg_times) if min(avg_times) > 0 else 1.0
            
            return {
                "symbols": [{"efficiency": efficiency}],
                "scaling_efficiency": efficiency,
                "measurements": timing_results
            }
        
        return self.run_benchmark(
            "file_count_scaling",
            file_count_test,
            iterations=3
        )
    
    # ===== Error Handling Benchmarks =====
    
    def benchmark_error_handling(self) -> BenchmarkResult:
        """Benchmark error handling performance."""
        invalid_files = self.test_data_manager.get_invalid_syntax_files()
        
        def error_handling_test():
            successful_recoveries = 0
            total_tests = 0
            
            for filename, content in invalid_files.items():
                try:
                    result = self.plugin.indexFile(Path(filename), content)
                    # Should return valid structure even for invalid content
                    if isinstance(result, dict) and "language" in result:
                        successful_recoveries += 1
                except Exception:
                    pass  # Failed to handle error gracefully
                
                total_tests += 1
            
            recovery_rate = successful_recoveries / total_tests if total_tests > 0 else 0
            
            return {
                "symbols": [{"recovery_rate": recovery_rate}],
                "error_recovery_rate": recovery_rate,
                "successful_recoveries": successful_recoveries,
                "total_tests": total_tests
            }
        
        return self.run_benchmark(
            "error_handling",
            error_handling_test,
            iterations=10
        )
    
    # ===== Complete Benchmark Suite =====
    
    def run_complete_benchmark_suite(self) -> List[BenchmarkResult]:
        """Run the complete benchmark suite."""
        print(f"Running complete benchmark suite for {self.plugin_name} ({self.language})")
        print("=" * 60)
        
        benchmarks = [
            ("Small File Indexing", self.benchmark_small_file_indexing),
            ("Medium File Indexing", self.benchmark_medium_file_indexing),
            ("Large File Indexing", self.benchmark_large_file_indexing),
            ("Symbol Extraction Accuracy", self.benchmark_symbol_extraction_accuracy),
            ("Concurrent Indexing", self.benchmark_concurrent_indexing),
            ("Memory Usage Scaling", self.benchmark_memory_usage_scaling),
            ("Search Performance", self.benchmark_search_performance),
            ("Symbol Count Scaling", self.benchmark_symbol_count_scaling),
            ("File Count Scaling", self.benchmark_file_count_scaling),
            ("Error Handling", self.benchmark_error_handling)
        ]
        
        suite_results = []
        
        for benchmark_name, benchmark_func in benchmarks:
            print(f"\n{benchmark_name}...")
            try:
                result = benchmark_func()
                suite_results.append(result)
                
                # Print quick summary
                if result.metrics:
                    key_metric = next(
                        (m for m in result.metrics if m.name == "avg_execution_time"),
                        result.metrics[0]
                    )
                    print(f"  Result: {key_metric.value:.4f} {key_metric.unit}")
                    print(f"  Success rate: {result.success_rate:.1%}")
                
            except Exception as e:
                print(f"  Failed: {e}")
        
        print(f"\nBenchmark suite completed. {len(suite_results)} tests run.")
        return suite_results
    
    # ===== Results Analysis and Export =====
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance results."""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        summary = {
            "plugin_name": self.plugin_name,
            "language": self.language,
            "total_benchmarks": len(self.results),
            "overall_success_rate": statistics.mean([r.success_rate for r in self.results]),
            "tests": {}
        }
        
        for result in self.results:
            test_summary = {
                "success_rate": result.success_rate,
                "iterations": result.iterations,
                "memory_peak_mb": result.memory_peak_mb,
                "duration_seconds": result.duration_seconds
            }
            
            # Extract key metrics
            for metric in result.metrics:
                if metric.name in ["avg_execution_time", "symbol_throughput", 
                                 "accuracy", "scaling_factor", "recovery_rate"]:
                    test_summary[metric.name] = {
                        "value": metric.value,
                        "unit": metric.unit
                    }
            
            summary["tests"][result.test_name] = test_summary
        
        return summary
    
    def export_results(self, filename: Optional[str] = None) -> str:
        """Export benchmark results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{self.language}_{timestamp}.json"
        
        # Convert results to serializable format
        export_data = {
            "metadata": {
                "plugin_name": self.plugin_name,
                "language": self.language,
                "export_time": datetime.now().isoformat(),
                "total_benchmarks": len(self.results)
            },
            "summary": self.get_performance_summary(),
            "detailed_results": [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Benchmark results exported to: {filename}")
        return filename
    
    def print_performance_report(self):
        """Print a detailed performance report."""
        summary = self.get_performance_summary()
        
        print(f"\n{'='*60}")
        print(f"PERFORMANCE REPORT")
        print(f"{'='*60}")
        print(f"Plugin: {summary['plugin_name']}")
        print(f"Language: {summary['language']}")
        print(f"Total benchmarks: {summary['total_benchmarks']}")
        print(f"Overall success rate: {summary['overall_success_rate']:.1%}")
        
        print(f"\n{'Test Results:':<30} {'Time (s)':<12} {'Success':<8} {'Memory (MB)':<12}")
        print("-" * 64)
        
        for test_name, test_data in summary["tests"].items():
            time_str = f"{test_data.get('avg_execution_time', {}).get('value', 0):.4f}"
            success_str = f"{test_data['success_rate']:.1%}"
            memory_str = f"{test_data['memory_peak_mb']:.1f}"
            
            print(f"{test_name:<30} {time_str:<12} {success_str:<8} {memory_str:<12}")
        
        print("-" * 64)