"""
Benchmark runner with reporting and analysis capabilities.

This module provides:
- Automated benchmark execution implementing IBenchmarkRunner interface
- Result persistence and comparison
- Performance regression detection
- HTML and JSON report generation
"""

import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Template

from ..interfaces.indexing_interfaces import IBenchmarkRunner
from ..interfaces.shared_interfaces import Error, Result
from ..plugin_base import IPlugin
from .benchmark_suite import BenchmarkResult, BenchmarkSuite

logger = logging.getLogger(__name__)


class BenchmarkRunner(IBenchmarkRunner):
    """Orchestrates benchmark execution and reporting, implementing IBenchmarkRunner interface."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.output_dir / "benchmark_history.json"
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load historical benchmark results."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
        return []

    def _save_history(self):
        """Save benchmark history to disk."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2, default=str)

    def run_benchmarks(
        self,
        plugins: List[IPlugin],
        save_results: bool = True,
        compare_with_previous: bool = True,
    ) -> BenchmarkResult:
        """Run complete benchmark suite."""
        suite = BenchmarkSuite(plugins)

        logger.info("Starting benchmark suite execution...")
        start_time = time.time()

        result = suite.run_all_benchmarks()

        logger.info(f"Benchmark suite completed in {time.time() - start_time:.2f}s")

        # Validate against requirements
        validations = suite.validate_performance_requirements(result)
        result.validations = validations

        if save_results:
            self._save_result(result)
            self._generate_reports(result)

        if compare_with_previous and len(self.history) > 0:
            regression_report = self._check_regressions(result)
            result.regression_report = regression_report

        return result

    # Implementation of IBenchmarkRunner interface methods

    async def run_indexing_benchmark(self, file_paths: List[str]) -> Result[Dict[str, Any]]:
        """Run indexing performance benchmark."""
        try:
            # Create a minimal plugin set for indexing benchmark
            from ..plugins.c_plugin import CPlugin
            from ..plugins.js_plugin import JSPlugin
            from ..plugins.python_plugin import PythonPlugin

            plugins = [PythonPlugin(), JSPlugin(), CPlugin()]
            suite = BenchmarkSuite(plugins)

            # Run indexing benchmark with provided files
            start_time = time.perf_counter()
            indexed_count = 0
            errors = []
            timing_samples = []

            for file_path in file_paths:
                try:
                    path_obj = Path(file_path)
                    if not path_obj.exists():
                        continue

                    content = path_obj.read_text()
                    plugin = suite.dispatcher._match_plugin(path_obj)

                    if plugin:
                        file_start = time.perf_counter()
                        plugin.index(path_obj, content)
                        file_duration = (time.perf_counter() - file_start) * 1000
                        timing_samples.append(file_duration)
                        indexed_count += 1
                except Exception as e:
                    errors.append(f"Error indexing {file_path}: {str(e)}")

            total_time = time.perf_counter() - start_time
            files_per_minute = (indexed_count / total_time) * 60 if total_time > 0 else 0

            metrics = {
                "indexed_files": indexed_count,
                "total_time_seconds": total_time,
                "files_per_minute": files_per_minute,
                "average_time_per_file_ms": (
                    sum(timing_samples) / len(timing_samples) if timing_samples else 0
                ),
                "p95_time_ms": (
                    sorted(timing_samples)[int(len(timing_samples) * 0.95)] if timing_samples else 0
                ),
                "errors": errors,
                "meets_target": files_per_minute >= suite.FILES_PER_MINUTE_TARGET,
            }

            return Result.success_result(metrics)

        except Exception as e:
            error = Error(
                code="indexing_benchmark_failed",
                message=f"Indexing benchmark failed: {str(e)}",
                details={"exception_type": type(e).__name__},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    async def run_search_benchmark(self, queries: List[str]) -> Result[Dict[str, Any]]:
        """Run search performance benchmark."""
        try:
            from ..plugins.c_plugin import CPlugin
            from ..plugins.js_plugin import JSPlugin
            from ..plugins.python_plugin import PythonPlugin

            plugins = [PythonPlugin(), JSPlugin(), CPlugin()]
            suite = BenchmarkSuite(plugins)

            # Populate some test data first
            test_symbols = {
                "test_function": "function test_function() { return 42; }",
                "calculate_sum": "def calculate_sum(a, b): return a + b",
                "MyClass": "class MyClass: pass",
                "process_data": "void process_data(int* data, size_t len) {}",
            }

            for symbol, definition in test_symbols.items():
                plugins[0]._symbols[symbol] = type(
                    "SymbolDef",
                    (),
                    {
                        "name": symbol,
                        "type": "function",
                        "path": "/test.py",
                        "line": 1,
                        "character": 0,
                        "definition": definition,
                    },
                )()

            timing_samples = []
            result_counts = []
            errors = []

            for query in queries:
                try:
                    start_time = time.perf_counter()
                    results = list(suite.dispatcher.search(query, semantic=False))
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    timing_samples.append(duration_ms)
                    result_counts.append(len(results))
                except Exception as e:
                    errors.append(f"Error searching '{query}': {str(e)}")

            metrics = {
                "queries_executed": len(timing_samples),
                "total_queries": len(queries),
                "average_time_ms": (
                    sum(timing_samples) / len(timing_samples) if timing_samples else 0
                ),
                "p95_time_ms": (
                    sorted(timing_samples)[int(len(timing_samples) * 0.95)] if timing_samples else 0
                ),
                "p99_time_ms": (
                    sorted(timing_samples)[int(len(timing_samples) * 0.99)] if timing_samples else 0
                ),
                "average_results": (
                    sum(result_counts) / len(result_counts) if result_counts else 0
                ),
                "errors": errors,
                "meets_symbol_target": (
                    all(t <= suite.SYMBOL_LOOKUP_TARGET_MS for t in timing_samples[:10])
                    if timing_samples
                    else False
                ),
                "meets_search_target": (
                    all(t <= suite.SEARCH_TARGET_MS for t in timing_samples)
                    if timing_samples
                    else False
                ),
            }

            return Result.success_result(metrics)

        except Exception as e:
            error = Error(
                code="search_benchmark_failed",
                message=f"Search benchmark failed: {str(e)}",
                details={"exception_type": type(e).__name__},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    async def run_memory_benchmark(self, file_count: int) -> Result[Dict[str, Any]]:
        """Run memory usage benchmark."""
        try:
            from ..plugins.c_plugin import CPlugin
            from ..plugins.js_plugin import JSPlugin
            from ..plugins.python_plugin import PythonPlugin

            plugins = [PythonPlugin(), JSPlugin(), CPlugin()]
            suite = BenchmarkSuite(plugins)

            import gc

            import psutil

            # Force garbage collection and get initial memory
            gc.collect()
            process = psutil.Process()
            initial_memory_mb = process.memory_info().rss / (1024 * 1024)

            # Generate test files and index them
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir)
                test_files = suite._generate_test_files(file_count, test_path)

                memory_samples = []

                for i, file_path in enumerate(test_files):
                    try:
                        content = file_path.read_text()
                        plugin = suite.dispatcher._match_plugin(file_path)

                        if plugin:
                            plugin.index(file_path, content)

                        # Sample memory every 100 files
                        if i % 100 == 0:
                            current_memory_mb = process.memory_info().rss / (1024 * 1024)
                            memory_samples.append(current_memory_mb - initial_memory_mb)

                    except Exception as e:
                        logger.warning(f"Memory benchmark error for {file_path}: {e}")

                final_memory_mb = process.memory_info().rss / (1024 * 1024)
                total_memory_used = final_memory_mb - initial_memory_mb

                # Extrapolate to 100K files
                memory_per_100k_files = (total_memory_used / file_count) * 100000

                metrics = {
                    "files_indexed": file_count,
                    "initial_memory_mb": initial_memory_mb,
                    "final_memory_mb": final_memory_mb,
                    "memory_used_mb": total_memory_used,
                    "memory_per_file_kb": (
                        (total_memory_used * 1024) / file_count if file_count > 0 else 0
                    ),
                    "projected_memory_100k_files_mb": memory_per_100k_files,
                    "meets_memory_target": memory_per_100k_files <= suite.MEMORY_TARGET_MB_PER_100K,
                    "memory_samples": memory_samples,
                }

                return Result.success_result(metrics)

        except Exception as e:
            error = Error(
                code="memory_benchmark_failed",
                message=f"Memory benchmark failed: {str(e)}",
                details={"exception_type": type(e).__name__},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    async def generate_benchmark_report(self) -> Result[str]:
        """Generate benchmark report."""
        try:
            if not self.history:
                return Result.success_result("No benchmark history available.")

            latest_result = self.history[-1]

            # Generate comprehensive report
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("MCP SERVER PERFORMANCE BENCHMARK REPORT")
            report_lines.append("=" * 80)
            report_lines.append(f"Generated: {datetime.now().isoformat()}")
            report_lines.append(f"Latest Run: {latest_result['timestamp']}")
            report_lines.append(f"Suite: {latest_result['suite_name']}")
            report_lines.append("")

            # Performance Summary
            report_lines.append("PERFORMANCE SUMMARY")
            report_lines.append("-" * 40)

            if "metrics" in latest_result:
                for metric_name, metric_data in latest_result["metrics"].items():
                    p95_ms = metric_data.get("p95", 0)

                    # Determine status against targets
                    status = "UNKNOWN"
                    if metric_name == "symbol_lookup":
                        status = (
                            "PASS" if p95_ms <= BenchmarkSuite.SYMBOL_LOOKUP_TARGET_MS else "FAIL"
                        )
                    elif "search" in metric_name:
                        status = "PASS" if p95_ms <= BenchmarkSuite.SEARCH_TARGET_MS else "FAIL"

                    report_lines.append(f"{metric_name:<30} P95: {p95_ms:>8.2f}ms [{status}]")

            # Special metrics
            if "metrics" in latest_result and "indexing" in latest_result["metrics"]:
                indexing_metric = latest_result["metrics"]["indexing"]
                if "files_per_minute" in indexing_metric:
                    fpm = indexing_metric["files_per_minute"]
                    status = "PASS" if fpm >= BenchmarkSuite.FILES_PER_MINUTE_TARGET else "FAIL"
                    report_lines.append(
                        f"{'Indexing Throughput':<30} {fpm:>8.0f} files/min [{status}]"
                    )

            # SLO Summary
            report_lines.append("")
            report_lines.append("SLO VALIDATION")
            report_lines.append("-" * 40)

            if "validations" in latest_result:
                passed = sum(1 for v in latest_result["validations"].values() if v)
                total = len(latest_result["validations"])
                report_lines.append(f"Overall: {passed}/{total} SLOs passed")

                for slo_name, passed in latest_result["validations"].items():
                    status = "PASS" if passed else "FAIL"
                    report_lines.append(f"  {slo_name:<35} [{status}]")

            # Trending
            if len(self.history) > 1:
                report_lines.append("")
                report_lines.append("PERFORMANCE TRENDS")
                report_lines.append("-" * 40)

                previous_result = self.history[-2]
                if "metrics" in latest_result and "metrics" in previous_result:
                    for metric_name in latest_result["metrics"]:
                        if metric_name in previous_result["metrics"]:
                            current_p95 = latest_result["metrics"][metric_name].get("p95", 0)
                            previous_p95 = previous_result["metrics"][metric_name].get("p95", 0)

                            if previous_p95 > 0:
                                change_pct = ((current_p95 - previous_p95) / previous_p95) * 100
                                trend = "↑" if change_pct > 5 else "↓" if change_pct < -5 else "→"
                                report_lines.append(
                                    f"  {metric_name:<30} {trend} {change_pct:>+6.1f}%"
                                )

            # Errors
            if "errors" in latest_result and latest_result["errors"]:
                report_lines.append("")
                report_lines.append("ERRORS")
                report_lines.append("-" * 40)
                for error in latest_result["errors"]:
                    report_lines.append(f"  • {error}")

            report_lines.append("")
            report_lines.append("=" * 80)

            report_text = "\n".join(report_lines)

            # Save report to file
            report_file = self.output_dir / "comprehensive_report.txt"
            report_file.write_text(report_text)

            return Result.success_result(report_text)

        except Exception as e:
            error = Error(
                code="report_generation_failed",
                message=f"Report generation failed: {str(e)}",
                details={"exception_type": type(e).__name__},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def _save_result(self, result: BenchmarkResult):
        """Save benchmark result to history."""
        # Convert to serializable format
        result_dict = {
            "suite_name": result.suite_name,
            "timestamp": result.start_time.isoformat(),
            "duration_seconds": result.duration_seconds,
            "metrics": {},
            "validations": getattr(result, "validations", {}),
            "errors": result.errors,
        }

        for name, metric in result.metrics.items():
            result_dict["metrics"][name] = {
                "operation": metric.operation,
                "count": metric.count,
                "mean": metric.mean,
                "median": metric.median,
                "p95": metric.p95,
                "p99": metric.p99,
                "min": metric.min,
                "max": metric.max,
                "memory_usage_mb": metric.memory_usage_mb,
                "cpu_percent": metric.cpu_percent,
            }
            # Add any custom attributes
            if hasattr(metric, "files_per_minute"):
                result_dict["metrics"][name]["files_per_minute"] = metric.files_per_minute
            if hasattr(metric, "memory_per_file_count"):
                result_dict["metrics"][name]["memory_per_file_count"] = metric.memory_per_file_count

        self.history.append(result_dict)
        self._save_history()

        # Save individual result file
        result_file = self.output_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, "w") as f:
            json.dump(result_dict, f, indent=2)

    def _check_regressions(
        self, current: BenchmarkResult, threshold_percent: float = 10.0
    ) -> Dict[str, Any]:
        """Check for performance regressions compared to previous run."""
        if not self.history:
            return {"status": "no_history"}

        previous = self.history[-1]
        regressions = []
        improvements = []

        for metric_name, current_metric in current.metrics.items():
            if metric_name in previous["metrics"]:
                prev_metric = previous["metrics"][metric_name]

                # Compare p95 latencies
                if current_metric.p95 > 0 and prev_metric["p95"] > 0:
                    change_percent = (
                        (current_metric.p95 - prev_metric["p95"]) / prev_metric["p95"]
                    ) * 100

                    if change_percent > threshold_percent:
                        regressions.append(
                            {
                                "metric": metric_name,
                                "previous_p95": prev_metric["p95"],
                                "current_p95": current_metric.p95,
                                "change_percent": change_percent,
                            }
                        )
                    elif change_percent < -threshold_percent:
                        improvements.append(
                            {
                                "metric": metric_name,
                                "previous_p95": prev_metric["p95"],
                                "current_p95": current_metric.p95,
                                "change_percent": change_percent,
                            }
                        )

        return {
            "status": "checked",
            "regressions": regressions,
            "improvements": improvements,
            "threshold_percent": threshold_percent,
        }

    def _generate_reports(self, result: BenchmarkResult):
        """Generate HTML and text reports."""
        # Generate HTML report
        html_report = self._generate_html_report(result)
        html_file = self.output_dir / "benchmark_report.html"
        with open(html_file, "w") as f:
            f.write(html_report)

        # Generate text summary
        text_report = self._generate_text_report(result)
        text_file = self.output_dir / "benchmark_summary.txt"
        with open(text_file, "w") as f:
            f.write(text_report)

        logger.info(f"Reports generated in {self.output_dir}")

    def _generate_html_report(self, result: BenchmarkResult) -> str:
        """Generate HTML benchmark report."""
        template = Template(
            """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Benchmark Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
        .metric { background-color: #f9f9f9; }
        .summary { background-color: #e6f3ff; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>MCP Server Performance Benchmark Report</h1>
    <div class="summary">
        <p><strong>Suite:</strong> {{ result.suite_name }}</p>
        <p><strong>Date:</strong> {{ result.start_time }}</p>
        <p><strong>Duration:</strong> {{ "%.2f"|format(result.duration_seconds) }} seconds</p>
    </div>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Samples</th>
            <th>Mean (ms)</th>
            <th>Median (ms)</th>
            <th>P95 (ms)</th>
            <th>P99 (ms)</th>
            <th>Memory (MB)</th>
            <th>CPU %</th>
        </tr>
        {% for name, metric in result.metrics.items() %}
        <tr class="metric">
            <td>{{ name }}</td>
            <td>{{ metric.count }}</td>
            <td>{{ "%.2f"|format(metric.mean) }}</td>
            <td>{{ "%.2f"|format(metric.median) }}</td>
            <td>{{ "%.2f"|format(metric.p95) }}</td>
            <td>{{ "%.2f"|format(metric.p99) }}</td>
            <td>{{ "%.2f"|format(metric.memory_usage_mb) }}</td>
            <td>{{ "%.1f"|format(metric.cpu_percent) }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>SLO Validation</h2>
    <table>
        <tr>
            <th>Requirement</th>
            <th>Status</th>
        </tr>
        {% for req, passed in validations.items() %}
        <tr>
            <td>{{ req }}</td>
            <td class="{{ 'pass' if passed else 'fail' }}">
                {{ 'PASS' if passed else 'FAIL' }}
            </td>
        </tr>
        {% endfor %}
    </table>
    
    {% if regression_report %}
    <h2>Regression Analysis</h2>
    {% if regression_report.regressions %}
    <h3>Performance Regressions Detected</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Previous P95</th>
            <th>Current P95</th>
            <th>Change %</th>
        </tr>
        {% for reg in regression_report.regressions %}
        <tr>
            <td>{{ reg.metric }}</td>
            <td>{{ "%.2f"|format(reg.previous_p95) }}</td>
            <td>{{ "%.2f"|format(reg.current_p95) }}</td>
            <td class="fail">+{{ "%.1f"|format(reg.change_percent) }}%</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    {% endif %}
    
    {% if result.errors %}
    <h2>Errors</h2>
    <ul>
        {% for error in result.errors %}
        <li class="fail">{{ error }}</li>
        {% endfor %}
    </ul>
    {% endif %}
</body>
</html>
        """
        )

        return template.render(
            result=result,
            validations=getattr(result, "validations", {}),
            regression_report=getattr(result, "regression_report", None),
        )

    def _generate_text_report(self, result: BenchmarkResult) -> str:
        """Generate text summary report."""
        lines = []
        lines.append("=" * 70)
        lines.append("MCP Server Performance Benchmark Report")
        lines.append("=" * 70)
        lines.append(f"Suite: {result.suite_name}")
        lines.append(f"Date: {result.start_time}")
        lines.append(f"Duration: {result.duration_seconds:.2f} seconds")
        lines.append("")

        # Performance metrics
        lines.append("Performance Metrics:")
        lines.append("-" * 70)
        lines.append(f"{'Metric':<30} {'P95 (ms)':<15} {'Status':<20}")
        lines.append("-" * 70)

        for name, metric in result.metrics.items():
            status = "OK"
            if hasattr(result, "validations"):
                if f"{name}_slo" in result.validations:
                    status = "PASS" if result.validations[f"{name}_slo"] else "FAIL"

            lines.append(f"{name:<30} {metric.p95:<15.2f} {status:<20}")

        # Special metrics
        lines.append("")
        if "indexing" in result.metrics:
            metric = result.metrics["indexing"]
            if hasattr(metric, "files_per_minute"):
                lines.append(f"Indexing Throughput: {metric.files_per_minute:.0f} files/minute")

        # Memory usage
        if "memory_usage" in result.metrics:
            metric = result.metrics["memory_usage"]
            if hasattr(metric, "memory_per_file_count"):
                lines.append("")
                lines.append("Memory Usage:")
                for count, mb in metric.memory_per_file_count.items():
                    lines.append(f"  {count} files: {mb:.2f} MB")

        # Validation summary
        if hasattr(result, "validations"):
            lines.append("")
            lines.append("SLO Validation Summary:")
            lines.append("-" * 70)
            passed = sum(1 for v in result.validations.values() if v)
            total = len(result.validations)
            lines.append(f"Passed: {passed}/{total}")

            for req, status in result.validations.items():
                lines.append(f"  {req}: {'PASS' if status else 'FAIL'}")

        # Errors
        if result.errors:
            lines.append("")
            lines.append("Errors:")
            for error in result.errors:
                lines.append(f"  - {error}")

        lines.append("=" * 70)

        return "\n".join(lines)

    def export_for_ci(self, result: BenchmarkResult, output_file: Path = None) -> Dict[str, Any]:
        """Export results in CI-friendly format (e.g., for GitHub Actions)."""
        if output_file is None:
            output_file = self.output_dir / "ci_metrics.json"

        ci_data = {
            "timestamp": result.start_time.isoformat(),
            "duration_seconds": result.duration_seconds,
            "metrics": {},
            "validations": getattr(result, "validations", {}),
            "passed": (
                all(getattr(result, "validations", {}).values())
                if hasattr(result, "validations")
                else True
            ),
            "summary": {
                "total_tests": len(result.metrics),
                "errors": len(result.errors),
            },
        }

        # Add key metrics for CI
        for name, metric in result.metrics.items():
            ci_data["metrics"][name] = {
                "p95_ms": metric.p95,
                "p99_ms": metric.p99,
                "samples": metric.count,
            }

        with open(output_file, "w") as f:
            json.dump(ci_data, f, indent=2)

        return ci_data


def run_pytest_benchmarks(benchmark, plugins: List[IPlugin]):
    """Integration with pytest-benchmark for standard testing."""
    suite = BenchmarkSuite(plugins)

    # Define individual benchmark functions
    def bench_symbol_lookup():
        return suite.dispatcher.lookup("test_function")

    def bench_fuzzy_search():
        return list(suite.dispatcher.search("test", semantic=False))

    def bench_semantic_search():
        return list(suite.dispatcher.search("calculate sum", semantic=True))

    # Run with pytest-benchmark
    benchmark.group = "mcp_server"

    if benchmark.name == "test_symbol_lookup":
        benchmark(bench_symbol_lookup)
    elif benchmark.name == "test_fuzzy_search":
        benchmark(bench_fuzzy_search)
    elif benchmark.name == "test_semantic_search":
        benchmark(bench_semantic_search)
