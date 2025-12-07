#!/usr/bin/env python3
"""Parallel test runner for document processing features."""

import asyncio
import json
import multiprocessing
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class TestResult:
    """Test execution result."""

    name: str
    group: str
    status: str  # 'passed', 'failed', 'error'
    duration: float
    message: str = ""
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class TestGroup:
    """Group of related tests to run in parallel."""

    name: str
    tests: List[str]
    max_workers: int = 4


class ParallelTestRunner:
    """Orchestrates parallel test execution."""

    def __init__(self, output_dir: Path = Path("test_results")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    def run_test(self, test_name: str, group_name: str) -> TestResult:
        """Run a single test and return results."""
        start = time.time()

        try:
            # Run test as subprocess to isolate failures
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-xvs", test_name],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            duration = time.time() - start

            if result.returncode == 0:
                return TestResult(
                    name=test_name,
                    group=group_name,
                    status="passed",
                    duration=duration,
                    message=f"Test passed in {duration:.2f}s",
                )
            else:
                # Extract error details from output
                errors = []
                if result.stderr:
                    errors.append(result.stderr)
                if "FAILED" in result.stdout:
                    # Extract failure details
                    lines = result.stdout.split("\n")
                    for i, line in enumerate(lines):
                        if "FAILED" in line:
                            errors.append("\n".join(lines[max(0, i - 5) : i + 5]))

                return TestResult(
                    name=test_name,
                    group=group_name,
                    status="failed",
                    duration=duration,
                    message=f"Test failed with code {result.returncode}",
                    errors=errors,
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return TestResult(
                name=test_name,
                group=group_name,
                status="error",
                duration=duration,
                message="Test timed out after 5 minutes",
                errors=["Timeout exceeded"],
            )
        except Exception as e:
            duration = time.time() - start
            return TestResult(
                name=test_name,
                group=group_name,
                status="error",
                duration=duration,
                message=f"Test error: {str(e)}",
                errors=[traceback.format_exc()],
            )

    async def run_group_async(self, group: TestGroup) -> List[TestResult]:
        """Run a test group asynchronously."""
        print(f"\n🚀 Starting test group: {group.name} ({len(group.tests)} tests)")

        with ProcessPoolExecutor(max_workers=group.max_workers) as executor:
            # Submit all tests
            futures = []
            for test in group.tests:
                future = executor.submit(self.run_test, test, group.name)
                futures.append((test, future))

            # Collect results
            results = []
            for test, future in futures:
                try:
                    result = future.result()
                    results.append(result)

                    # Print progress
                    status_icon = "✅" if result.status == "passed" else "❌"
                    print(f"  {status_icon} {test}: {result.message}")

                except Exception as e:
                    result = TestResult(
                        name=test,
                        group=group.name,
                        status="error",
                        duration=0,
                        message=f"Failed to execute: {str(e)}",
                        errors=[traceback.format_exc()],
                    )
                    results.append(result)
                    print(f"  ❌ {test}: Execution failed")

            return results

    async def run_all_groups(self, groups: List[TestGroup]):
        """Run all test groups in parallel."""
        self.start_time = datetime.now()

        # Run all groups concurrently
        tasks = [self.run_group_async(group) for group in groups]
        group_results = await asyncio.gather(*tasks)

        # Flatten results
        for results in group_results:
            self.results.extend(results)

        self.end_time = datetime.now()

    def generate_report(self) -> Dict:
        """Generate comprehensive test report."""
        total_duration = (self.end_time - self.start_time).total_seconds()

        # Calculate statistics
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status == "error")

        # Group results by test group
        by_group = {}
        for result in self.results:
            if result.group not in by_group:
                by_group[result.group] = []
            by_group[result.group].append(result)

        # Calculate group statistics
        group_stats = {}
        for group, results in by_group.items():
            group_stats[group] = {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == "passed"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "errors": sum(1 for r in results if r.status == "error"),
                "duration": sum(r.duration for r in results),
            }

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": f"{(passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
                "total_duration": f"{total_duration:.2f}s",
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
            },
            "group_statistics": group_stats,
            "failed_tests": [
                {
                    "name": r.name,
                    "group": r.group,
                    "message": r.message,
                    "errors": r.errors,
                    "duration": r.duration,
                }
                for r in self.results
                if r.status in ["failed", "error"]
            ],
            "all_results": [
                {
                    "name": r.name,
                    "group": r.group,
                    "status": r.status,
                    "duration": r.duration,
                    "message": r.message,
                }
                for r in self.results
            ],
        }

        # Save report
        report_path = (
            self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        self.print_summary(report)

        return report

    def print_summary(self, report: Dict):
        """Print test execution summary."""
        print("\n" + "=" * 80)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 80)

        summary = report["summary"]
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Total Duration: {summary['total_duration']}")

        print("\n📈 GROUP STATISTICS:")
        for group, stats in report["group_statistics"].items():
            print(f"\n{group}:")
            print(f"  Total: {stats['total']}")
            print(f"  Passed: {stats['passed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Duration: {stats['duration']:.2f}s")

        if report["failed_tests"]:
            print("\n❌ FAILED TESTS:")
            for test in report["failed_tests"]:
                print(f"\n{test['name']} ({test['group']}):")
                print(f"  Message: {test['message']}")
                if test["errors"]:
                    print("  Errors:")
                    for error in test["errors"]:
                        print(f"    {error[:200]}..." if len(error) > 200 else f"    {error}")


# Define test groups
def get_test_groups() -> List[TestGroup]:
    """Define all test groups for parallel execution."""
    return [
        TestGroup(
            name="Unit Tests",
            tests=[
                "test_markdown_parser.py",
                "test_plaintext_nlp.py",
                "test_chunk_optimizer.py",
                "test_metadata_extractor.py",
                "test_document_interfaces.py",
            ],
            max_workers=5,
        ),
        TestGroup(
            name="Integration Tests",
            tests=[
                "test_plugin_integration.py",
                "test_dispatcher_document_routing.py",
                "test_semantic_document_integration.py",
                "test_document_storage.py",
            ],
            max_workers=4,
        ),
        TestGroup(
            name="Feature Tests",
            tests=[
                "test_natural_language_queries.py",
                "test_document_structure_extraction.py",
                "test_cross_document_search.py",
                "test_metadata_search.py",
                "test_section_search.py",
            ],
            max_workers=5,
        ),
        TestGroup(
            name="Performance Tests",
            tests=[
                "test_document_indexing_performance.py",
                "test_document_search_performance.py",
                "test_document_memory_usage.py",
            ],
            max_workers=3,
        ),
        TestGroup(
            name="Edge Cases",
            tests=[
                "test_malformed_documents.py",
                "test_document_edge_cases.py",
                "test_unicode_documents.py",
                "test_document_error_recovery.py",
            ],
            max_workers=4,
        ),
    ]


async def main():
    """Main test execution."""
    print("🧪 DOCUMENT PROCESSING PARALLEL TEST SUITE")
    print("=" * 80)

    runner = ParallelTestRunner()
    groups = get_test_groups()

    print(f"\n📋 Test Groups: {len(groups)}")
    total_tests = sum(len(g.tests) for g in groups)
    print(f"📝 Total Tests: {total_tests}")
    print(f"🖥️  CPU Cores: {multiprocessing.cpu_count()}")

    # Run all tests
    await runner.run_all_groups(groups)

    # Generate report
    report = runner.generate_report()

    # Exit with appropriate code
    if report["summary"]["failed"] > 0 or report["summary"]["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
