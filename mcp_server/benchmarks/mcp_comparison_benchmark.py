"""
MCP Server comparison benchmarks.

This module extends the benchmark suite to compare MCP server performance
against direct file operations, measuring token usage and efficiency.
"""

import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.token_counter import TokenCounter, TokenMetrics, TokenUsageTracker
from .benchmark_suite import BenchmarkResult, BenchmarkSuite, PerformanceMetrics


@dataclass
class ComparisonMetrics:
    """Metrics comparing MCP vs direct approaches."""

    operation: str
    query: str

    # Performance
    mcp_latency_ms: float = 0.0
    direct_latency_ms: float = 0.0
    speedup_factor: float = 0.0  # direct/mcp (>1 means MCP is faster)

    # Token usage
    mcp_tokens: TokenMetrics = field(default_factory=TokenMetrics)
    direct_tokens: TokenMetrics = field(default_factory=TokenMetrics)
    token_efficiency: float = 0.0  # direct/mcp tokens (>1 means MCP uses fewer)

    # Result quality
    mcp_result_count: int = 0
    direct_result_count: int = 0
    result_overlap_ratio: float = 0.0

    # Resource usage
    mcp_memory_mb: float = 0.0
    direct_memory_mb: float = 0.0

    def calculate_derived_metrics(self):
        """Calculate derived metrics after data collection."""
        # Speedup factor
        if self.mcp_latency_ms > 0:
            self.speedup_factor = self.direct_latency_ms / self.mcp_latency_ms

        # Token efficiency
        if self.mcp_tokens.total_tokens > 0:
            self.token_efficiency = self.direct_tokens.total_tokens / self.mcp_tokens.total_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation": self.operation,
            "query": self.query,
            "performance": {
                "mcp_latency_ms": self.mcp_latency_ms,
                "direct_latency_ms": self.direct_latency_ms,
                "speedup_factor": self.speedup_factor,
                "mcp_faster": self.speedup_factor > 1,
            },
            "tokens": {
                "mcp": self.mcp_tokens.to_dict(),
                "direct": self.direct_tokens.to_dict(),
                "efficiency_factor": self.token_efficiency,
                "mcp_more_efficient": self.token_efficiency < 1,
            },
            "results": {
                "mcp_count": self.mcp_result_count,
                "direct_count": self.direct_result_count,
                "overlap_ratio": self.result_overlap_ratio,
            },
            "resources": {
                "mcp_memory_mb": self.mcp_memory_mb,
                "direct_memory_mb": self.direct_memory_mb,
            },
        }


class MCPComparisonBenchmark(BenchmarkSuite):
    """
    Extended benchmark suite that compares MCP server against direct approaches.
    """

    def __init__(self, plugins: List[Any], db_path: Optional[Path] = None):
        super().__init__(plugins, db_path)

        # Token counting
        self.token_counter = TokenCounter("generic")
        self.mcp_token_tracker = TokenUsageTracker("voyage-2")  # For semantic search
        self.direct_token_tracker = TokenUsageTracker("generic")

        # Check for ripgrep
        self.has_ripgrep = shutil.which("rg") is not None
        if not self.has_ripgrep:
            print("Warning: ripgrep not found. Direct search will be slower.")

    def _run_direct_search(
        self, query: str, search_type: str = "pattern"
    ) -> Tuple[List[Dict], float]:
        """
        Run direct search using grep/ripgrep.

        Returns:
            Tuple of (results, duration_ms)
        """
        results = []
        start_time = time.perf_counter()

        try:
            if search_type == "symbol":
                # Build symbol search patterns
                patterns = [
                    f"def {query}",
                    f"function {query}",
                    f"class {query}",
                    f"struct {query}",
                    f"interface {query}",
                    f"trait {query}",
                ]
                pattern = "|".join(patterns)
            else:
                pattern = query

            if self.has_ripgrep:
                cmd = [
                    "rg",
                    "--json",  # JSON output for easier parsing
                    "--max-count",
                    "50",  # Limit results
                    "-e",
                    pattern,
                    ".",
                ]
            else:
                cmd = ["grep", "-r", "-n", "-E", "--max-count=50", pattern, "."]

            # Run search
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.db_path.parent) if self.db_path else ".",
            )

            if self.has_ripgrep and process.stdout:
                # Parse ripgrep JSON output
                for line in process.stdout.splitlines():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            match_data = data.get("data", {})
                            results.append(
                                {
                                    "file": match_data.get("path", {}).get("text", ""),
                                    "line": match_data.get("line_number", 0),
                                    "content": match_data.get("lines", {}).get("text", "").strip(),
                                }
                            )
                    except json.JSONDecodeError:
                        continue
            else:
                # Parse grep output
                for line in process.stdout.splitlines():
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        results.append(
                            {
                                "file": parts[0],
                                "line": int(parts[1]) if parts[1].isdigit() else 0,
                                "content": parts[2].strip(),
                            }
                        )

        except subprocess.TimeoutExpired:
            print(f"Direct search timed out for query: {query}")
        except Exception as e:
            print(f"Direct search error: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000
        return results, duration_ms

    def compare_symbol_lookup(self, symbol: str) -> ComparisonMetrics:
        """Compare symbol lookup performance between MCP and direct search."""
        metrics = ComparisonMetrics(operation="symbol_lookup", query=symbol)

        # MCP search
        mcp_start = time.perf_counter()
        mcp_result = self.dispatcher.lookup(symbol)
        metrics.mcp_latency_ms = (time.perf_counter() - mcp_start) * 1000

        # Process MCP results
        if mcp_result:
            metrics.mcp_result_count = 1

            # Count tokens
            input_text = symbol
            output_text = json.dumps(mcp_result, default=str)
            metrics.mcp_tokens = self.mcp_token_tracker.track_operation(
                "symbol_lookup", input_text, output_text
            )

        # Direct search
        direct_results, direct_latency = self._run_direct_search(symbol, "symbol")
        metrics.direct_latency_ms = direct_latency
        metrics.direct_result_count = len(direct_results)

        # Count tokens for direct search
        if direct_results:
            input_text = symbol
            output_text = json.dumps(direct_results, default=str)
            metrics.direct_tokens = self.direct_token_tracker.track_operation(
                "symbol_lookup", input_text, output_text
            )

        # Calculate overlap
        if mcp_result and direct_results:
            mcp_file = mcp_result.get("defined_in", "")
            direct_files = {r["file"] for r in direct_results}
            if mcp_file in direct_files:
                metrics.result_overlap_ratio = 1.0

        # Resource usage
        metrics.mcp_memory_mb = self._measure_memory()
        metrics.direct_memory_mb = self._measure_memory()

        # Calculate derived metrics
        metrics.calculate_derived_metrics()

        return metrics

    def compare_pattern_search(self, pattern: str, limit: int = 50) -> ComparisonMetrics:
        """Compare pattern search performance between MCP and direct search."""
        metrics = ComparisonMetrics(operation="pattern_search", query=pattern)

        # MCP search
        mcp_start = time.perf_counter()
        mcp_results = list(self.dispatcher.search(pattern, semantic=False, limit=limit))
        metrics.mcp_latency_ms = (time.perf_counter() - mcp_start) * 1000
        metrics.mcp_result_count = len(mcp_results)

        # Count MCP tokens
        if mcp_results:
            input_text = pattern
            output_text = "\n".join(
                [f"{r.file_path}:{r.line_number} {r.content}" for r in mcp_results]
            )
            metrics.mcp_tokens = self.mcp_token_tracker.track_operation(
                "pattern_search", input_text, output_text
            )

        # Direct search
        direct_results, direct_latency = self._run_direct_search(pattern, "pattern")
        metrics.direct_latency_ms = direct_latency
        metrics.direct_result_count = len(direct_results)

        # Count direct tokens
        if direct_results:
            input_text = pattern
            output_text = json.dumps(direct_results, default=str)
            metrics.direct_tokens = self.direct_token_tracker.track_operation(
                "pattern_search", input_text, output_text
            )

        # Calculate overlap
        if mcp_results and direct_results:
            mcp_files = {r.file_path for r in mcp_results}
            direct_files = {r["file"] for r in direct_results}
            overlap = len(mcp_files & direct_files)
            total = len(mcp_files | direct_files)
            metrics.result_overlap_ratio = overlap / total if total > 0 else 0

        # Resource usage
        metrics.mcp_memory_mb = self._measure_memory()
        metrics.direct_memory_mb = self._measure_memory()

        # Calculate derived metrics
        metrics.calculate_derived_metrics()

        return metrics

    def benchmark_comparison_suite(self) -> Dict[str, Any]:
        """Run comprehensive comparison benchmarks."""
        print("Running MCP vs Direct Comparison Benchmarks...")
        print("=" * 60)

        comparison_results = []

        # Test queries
        test_symbols = [
            "function_0",
            "TestClass0",
            "method_0",
            "parseFile",
            "handleRequest",
            "calculate",
        ]

        test_patterns = [
            "def .*\\(",
            "class .*:",
            "function.*\\{",
            "TODO|FIXME",
            "import|require",
            "async|await",
        ]

        # Symbol lookup comparisons
        print("\nSymbol Lookup Comparisons:")
        print("-" * 40)
        for symbol in test_symbols:
            print(f"Testing symbol: {symbol}")
            metrics = self.compare_symbol_lookup(symbol)
            comparison_results.append(metrics)

            print(f"  MCP: {metrics.mcp_result_count} results in {metrics.mcp_latency_ms:.2f}ms")
            print(
                f"  Direct: {metrics.direct_result_count} results in {metrics.direct_latency_ms:.2f}ms"
            )
            print(f"  Speedup: {metrics.speedup_factor:.2f}x")
            print(f"  Token efficiency: {metrics.token_efficiency:.2f}x")

        # Pattern search comparisons
        print("\nPattern Search Comparisons:")
        print("-" * 40)
        for pattern in test_patterns:
            print(f"Testing pattern: {pattern}")
            metrics = self.compare_pattern_search(pattern)
            comparison_results.append(metrics)

            print(f"  MCP: {metrics.mcp_result_count} results in {metrics.mcp_latency_ms:.2f}ms")
            print(
                f"  Direct: {metrics.direct_result_count} results in {metrics.direct_latency_ms:.2f}ms"
            )
            print(f"  Speedup: {metrics.speedup_factor:.2f}x")
            print(f"  Token efficiency: {metrics.token_efficiency:.2f}x")

        # Calculate summary statistics
        summary = self._calculate_comparison_summary(comparison_results)

        # Print summary
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)
        print(f"Total comparisons: {summary['total_comparisons']}")
        print("\nPerformance:")
        print(f"  Average MCP latency: {summary['avg_mcp_latency']:.2f}ms")
        print(f"  Average Direct latency: {summary['avg_direct_latency']:.2f}ms")
        print(f"  Average speedup: {summary['avg_speedup']:.2f}x")
        print(f"  MCP faster: {summary['mcp_faster_count']} times")
        print(f"  Direct faster: {summary['direct_faster_count']} times")

        print("\nToken Usage:")
        print(f"  Total MCP tokens: {summary['total_mcp_tokens']:,}")
        print(f"  Total Direct tokens: {summary['total_direct_tokens']:,}")
        print(f"  Average token efficiency: {summary['avg_token_efficiency']:.2f}x")

        print("\nEstimated Costs:")
        print(f"  MCP cost: ${summary['mcp_total_cost']:.4f}")
        print(f"  Direct cost: ${summary['direct_total_cost']:.4f}")
        print(
            f"  Cost savings: ${abs(summary['cost_savings']):.4f} ({summary['cost_savings_percent']:.1f}%)"
        )

        return {
            "comparisons": [m.to_dict() for m in comparison_results],
            "summary": summary,
            "token_usage": {
                "mcp": self.mcp_token_tracker.get_summary(),
                "direct": self.direct_token_tracker.get_summary(),
            },
        }

    def _calculate_comparison_summary(self, results: List[ComparisonMetrics]) -> Dict[str, Any]:
        """Calculate summary statistics from comparison results."""
        if not results:
            return {}

        # Performance statistics
        mcp_latencies = [r.mcp_latency_ms for r in results]
        direct_latencies = [r.direct_latency_ms for r in results]
        speedups = [r.speedup_factor for r in results]

        # Token statistics
        mcp_tokens = sum(r.mcp_tokens.total_tokens for r in results)
        direct_tokens = sum(r.direct_tokens.total_tokens for r in results)
        token_efficiencies = [r.token_efficiency for r in results if r.token_efficiency > 0]

        # Win counts
        mcp_faster = sum(1 for r in results if r.speedup_factor > 1)
        direct_faster = sum(1 for r in results if r.speedup_factor < 1)

        # Cost calculations
        mcp_cost = self.mcp_token_tracker.total_metrics.total_cost
        direct_cost = self.direct_token_tracker.total_metrics.total_cost
        cost_savings = direct_cost - mcp_cost
        cost_savings_percent = (cost_savings / direct_cost * 100) if direct_cost > 0 else 0

        return {
            "total_comparisons": len(results),
            # Performance
            "avg_mcp_latency": sum(mcp_latencies) / len(mcp_latencies),
            "avg_direct_latency": sum(direct_latencies) / len(direct_latencies),
            "avg_speedup": sum(speedups) / len(speedups),
            "mcp_faster_count": mcp_faster,
            "direct_faster_count": direct_faster,
            # Tokens
            "total_mcp_tokens": mcp_tokens,
            "total_direct_tokens": direct_tokens,
            "avg_token_efficiency": (
                sum(token_efficiencies) / len(token_efficiencies) if token_efficiencies else 0
            ),
            # Costs
            "mcp_total_cost": mcp_cost,
            "direct_total_cost": direct_cost,
            "cost_savings": cost_savings,
            "cost_savings_percent": cost_savings_percent,
            # Quality
            "avg_result_overlap": sum(r.result_overlap_ratio for r in results) / len(results),
        }

    def run_all_benchmarks(self) -> BenchmarkResult:
        """Run complete benchmark suite including comparisons."""
        # Run base benchmarks
        result = super().run_all_benchmarks()

        # Add comparison benchmarks
        try:
            comparison_data = self.benchmark_comparison_suite()

            # Create a special metric for comparisons
            comparison_metric = PerformanceMetrics("mcp_vs_direct_comparison")
            comparison_metric.comparison_data = comparison_data

            result.add_metric("comparison", comparison_metric)

        except Exception as e:
            result.add_error(f"Comparison benchmark error: {str(e)}")

        return result


def run_comparison_benchmarks(plugins: List[Any], output_file: Optional[Path] = None):
    """
    Run MCP comparison benchmarks and save results.

    Args:
        plugins: List of loaded plugins
        output_file: Optional path to save results
    """
    # Create temporary test files
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir)

        # Generate test files
        benchmark = MCPComparisonBenchmark(plugins, test_path / "test.db")
        test_files = benchmark._generate_test_files(100, test_path)

        print(f"Generated {len(test_files)} test files in {test_path}")

        # Index files with MCP
        print("Indexing files with MCP...")
        for file_path in test_files:
            try:
                plugin = benchmark.dispatcher._match_plugin(file_path)
                content = file_path.read_text()
                plugin.index(file_path, content)
            except Exception as e:
                print(f"Failed to index {file_path}: {e}")

        # Run comparison benchmarks
        comparison_results = benchmark.benchmark_comparison_suite()

        # Save results if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(comparison_results, f, indent=2)
            print(f"\nResults saved to: {output_file}")

        return comparison_results
