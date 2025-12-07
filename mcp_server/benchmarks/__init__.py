"""
Benchmark suite for MCP Server performance validation.

This module provides comprehensive benchmarks to ensure all implementations
meet the performance requirements specified in architecture/performance_requirements.md

Key Performance Requirements:
- Symbol lookup < 100ms (p95)
- Search performance < 500ms (p95)
- Indexing speed: 10K files/minute target
- Memory usage: < 2GB for 100K files

Usage:
    # Run from command line
    python -m mcp_server.benchmarks.run_benchmarks

    # Use in tests
    pytest tests/test_benchmarks.py --benchmark-only

    # Programmatic usage
    from mcp_server.benchmarks import BenchmarkRunner
    runner = BenchmarkRunner()
    result = runner.run_benchmarks(plugins)
"""

from .benchmark_runner import BenchmarkRunner
from .benchmark_suite import (
    BenchmarkResult,
    BenchmarkSuite,
    PerformanceMetrics,
)
from .mcp_comparison_benchmark import (
    ComparisonMetrics,
    MCPComparisonBenchmark,
    run_comparison_benchmarks,
)

__all__ = [
    "BenchmarkSuite",
    "BenchmarkResult",
    "PerformanceMetrics",
    "BenchmarkRunner",
    "MCPComparisonBenchmark",
    "ComparisonMetrics",
    "run_comparison_benchmarks",
]
