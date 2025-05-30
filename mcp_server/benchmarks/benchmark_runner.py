"""
Benchmark runner with reporting and analysis capabilities.

This module provides:
- Automated benchmark execution
- Result persistence and comparison
- Performance regression detection
- HTML and JSON report generation
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import statistics
import logging
from dataclasses import asdict

import pytest_benchmark
from jinja2 import Template

from .benchmark_suite import BenchmarkSuite, BenchmarkResult, PerformanceMetrics
from ..plugin_base import IPlugin

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Orchestrates benchmark execution and reporting."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.output_dir / "benchmark_history.json"
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load historical benchmark results."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
        return []
    
    def _save_history(self):
        """Save benchmark history to disk."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)
    
    def run_benchmarks(self, plugins: List[IPlugin], 
                      save_results: bool = True,
                      compare_with_previous: bool = True) -> BenchmarkResult:
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
    
    def _save_result(self, result: BenchmarkResult):
        """Save benchmark result to history."""
        # Convert to serializable format
        result_dict = {
            "suite_name": result.suite_name,
            "timestamp": result.start_time.isoformat(),
            "duration_seconds": result.duration_seconds,
            "metrics": {},
            "validations": getattr(result, 'validations', {}),
            "errors": result.errors
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
            if hasattr(metric, 'files_per_minute'):
                result_dict["metrics"][name]["files_per_minute"] = metric.files_per_minute
            if hasattr(metric, 'memory_per_file_count'):
                result_dict["metrics"][name]["memory_per_file_count"] = metric.memory_per_file_count
        
        self.history.append(result_dict)
        self._save_history()
        
        # Save individual result file
        result_file = self.output_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(result_dict, f, indent=2)
    
    def _check_regressions(self, current: BenchmarkResult, 
                          threshold_percent: float = 10.0) -> Dict[str, Any]:
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
                    change_percent = ((current_metric.p95 - prev_metric["p95"]) / 
                                    prev_metric["p95"]) * 100
                    
                    if change_percent > threshold_percent:
                        regressions.append({
                            "metric": metric_name,
                            "previous_p95": prev_metric["p95"],
                            "current_p95": current_metric.p95,
                            "change_percent": change_percent
                        })
                    elif change_percent < -threshold_percent:
                        improvements.append({
                            "metric": metric_name,
                            "previous_p95": prev_metric["p95"],
                            "current_p95": current_metric.p95,
                            "change_percent": change_percent
                        })
        
        return {
            "status": "checked",
            "regressions": regressions,
            "improvements": improvements,
            "threshold_percent": threshold_percent
        }
    
    def _generate_reports(self, result: BenchmarkResult):
        """Generate HTML and text reports."""
        # Generate HTML report
        html_report = self._generate_html_report(result)
        html_file = self.output_dir / "benchmark_report.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        # Generate text summary
        text_report = self._generate_text_report(result)
        text_file = self.output_dir / "benchmark_summary.txt"
        with open(text_file, 'w') as f:
            f.write(text_report)
        
        logger.info(f"Reports generated in {self.output_dir}")
    
    def _generate_html_report(self, result: BenchmarkResult) -> str:
        """Generate HTML benchmark report."""
        template = Template('''
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
        ''')
        
        return template.render(
            result=result,
            validations=getattr(result, 'validations', {}),
            regression_report=getattr(result, 'regression_report', None)
        )
    
    def _generate_text_report(self, result: BenchmarkResult) -> str:
        """Generate text summary report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"MCP Server Performance Benchmark Report")
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
            if hasattr(result, 'validations'):
                if f"{name}_slo" in result.validations:
                    status = "PASS" if result.validations[f"{name}_slo"] else "FAIL"
            
            lines.append(f"{name:<30} {metric.p95:<15.2f} {status:<20}")
        
        # Special metrics
        lines.append("")
        if "indexing" in result.metrics:
            metric = result.metrics["indexing"]
            if hasattr(metric, 'files_per_minute'):
                lines.append(f"Indexing Throughput: {metric.files_per_minute:.0f} files/minute")
        
        # Memory usage
        if "memory_usage" in result.metrics:
            metric = result.metrics["memory_usage"]
            if hasattr(metric, 'memory_per_file_count'):
                lines.append("")
                lines.append("Memory Usage:")
                for count, mb in metric.memory_per_file_count.items():
                    lines.append(f"  {count} files: {mb:.2f} MB")
        
        # Validation summary
        if hasattr(result, 'validations'):
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
            "validations": getattr(result, 'validations', {}),
            "passed": all(getattr(result, 'validations', {}).values()) if hasattr(result, 'validations') else True,
            "summary": {
                "total_tests": len(result.metrics),
                "errors": len(result.errors)
            }
        }
        
        # Add key metrics for CI
        for name, metric in result.metrics.items():
            ci_data["metrics"][name] = {
                "p95_ms": metric.p95,
                "p99_ms": metric.p99,
                "samples": metric.count
            }
        
        with open(output_file, 'w') as f:
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