#!/usr/bin/env python3
"""
Standalone script to run MCP Server benchmarks.

Usage:
    python -m mcp_server.benchmarks.run_benchmarks [options]

Options:
    --output-dir PATH    Directory for benchmark results (default: ./benchmark_results)
    --plugins LANGS      Comma-separated list of plugins to test (default: python,javascript,c)
    --quick              Run quick benchmarks only
    --full               Run full benchmark suite including large tests
    --compare            Compare with previous results
"""

import argparse
import logging
import sys
from pathlib import Path

from ..plugins.c_plugin.plugin import CPlugin
from ..plugins.js_plugin.plugin import JavaScriptPlugin
from ..plugins.python_plugin.plugin import PythonPlugin
from .benchmark_runner import BenchmarkRunner


def main():
    """Run MCP Server benchmarks."""
    parser = argparse.ArgumentParser(description="Run MCP Server performance benchmarks")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_results"),
        help="Directory for benchmark results",
    )
    parser.add_argument(
        "--plugins",
        default="python,javascript,c",
        help="Comma-separated list of plugins to test",
    )
    parser.add_argument("--quick", action="store_true", help="Run quick benchmarks only")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full benchmark suite including large tests",
    )
    parser.add_argument("--compare", action="store_true", help="Compare with previous results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize plugins
    plugin_map = {
        "python": PythonPlugin,
        "javascript": JavaScriptPlugin,
        "c": CPlugin,
    }

    plugins = []
    for lang in args.plugins.split(","):
        lang = lang.strip().lower()
        if lang in plugin_map:
            plugins.append(plugin_map[lang]())
        else:
            print(f"Warning: Unknown plugin '{lang}', skipping")

    if not plugins:
        print("Error: No valid plugins specified")
        return 1

    # Create runner
    runner = BenchmarkRunner(args.output_dir)

    # Run benchmarks
    print(f"Running benchmarks with {len(plugins)} plugins...")
    print(f"Output directory: {args.output_dir}")

    try:
        result = runner.run_benchmarks(
            plugins, save_results=True, compare_with_previous=args.compare
        )

        # Print summary
        print("\n" + "=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)

        # Performance metrics
        print("\nPerformance Metrics:")
        print(f"{'Metric':<30} {'P95 (ms)':<15} {'P99 (ms)':<15} {'Samples':<10}")
        print("-" * 70)

        for name, metric in result.metrics.items():
            print(f"{name:<30} {metric.p95:<15.2f} {metric.p99:<15.2f} {metric.count:<10}")

        # SLO validation
        if hasattr(result, "validations"):
            print("\nSLO Validation:")
            passed = sum(1 for v in result.validations.values() if v)
            total = len(result.validations)
            print(f"Passed: {passed}/{total}")

            for req, status in result.validations.items():
                status_str = "✓ PASS" if status else "✗ FAIL"
                print(f"  {req}: {status_str}")

        # Regression report
        if hasattr(result, "regression_report") and result.regression_report:
            report = result.regression_report
            if report["status"] == "checked" and report["regressions"]:
                print("\n⚠️  Performance Regressions Detected:")
                for reg in report["regressions"]:
                    print(
                        f"  - {reg['metric']}: "
                        f"{reg['previous_p95']:.2f}ms -> {reg['current_p95']:.2f}ms "
                        f"(+{reg['change_percent']:.1f}%)"
                    )

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  - {error}")

        print(f"\nReports saved to: {args.output_dir}")
        print(f"  - HTML: {args.output_dir}/benchmark_report.html")
        print(f"  - Text: {args.output_dir}/benchmark_summary.txt")
        print(f"  - JSON: {args.output_dir}/benchmark_*.json")

        # Exit code based on validation
        if hasattr(result, "validations"):
            return 0 if all(result.validations.values()) else 1
        return 0

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        logging.exception("Benchmark execution failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
