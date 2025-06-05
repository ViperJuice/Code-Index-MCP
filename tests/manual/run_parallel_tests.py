#!/usr/bin/env python3
"""
Comprehensive Parallel Testing Execution Script for Code-Index-MCP

This script implements comprehensive parallel testing plan,
providing intelligent test orchestration, resource management, and reporting.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import multiprocessing


@dataclass
class TestPhase:
    """Represents a testing phase with its configuration."""
    name: str
    description: str
    test_groups: List[Dict[str, str]]
    parallel_workers: int
    estimated_duration_minutes: int
    dependencies: List[str] = None


@dataclass
class TestResult:
    """Represents the result of a test execution."""
    phase: str
    group: str
    command: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    success: bool


class ParallelTestRunner:
    """Orchestrates parallel test execution across all phases."""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 24)
        self.results: List[TestResult] = []
        self.start_time = time.time()
        
    def create_test_phases(self) -> List[TestPhase]:
        """Create the test phase configuration."""
        return [
            TestPhase(
                name="interface_compliance",
                description="Interface Compliance Testing",
                test_groups=[
                    {
                        "name": "shared_interfaces",
                        "command": "pytest tests/test_shared_interfaces.py -n 4 --dist=loadfile --tb=short",
                        "workers": 4
                    },
                    {
                        "name": "plugin_interfaces", 
                        "command": "pytest tests/test_*_plugin.py::*InterfaceCompliance* -n 6 --dist=loadgroup --tb=short",
                        "workers": 6
                    },
                    {
                        "name": "storage_interfaces",
                        "command": "pytest tests/test_sqlite_store.py -n 3 --dist=loadfile --tb=short",
                        "workers": 3
                    }
                ],
                parallel_workers=3,
                estimated_duration_minutes=45
            ),
            
            TestPhase(
                name="plugin_functionality",
                description="Plugin Functionality Testing",
                test_groups=[
                    {
                        "name": "python_plugin",
                        "command": "pytest tests/test_python_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "javascript_plugin",
                        "command": "pytest tests/test_js_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "c_plugin",
                        "command": "pytest tests/test_c_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "cpp_plugin",
                        "command": "pytest tests/test_cpp_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "dart_plugin",
                        "command": "pytest tests/test_dart_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "html_css_plugin",
                        "command": "pytest tests/test_html_css_plugin.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    }
                ],
                parallel_workers=6,
                estimated_duration_minutes=60,
                dependencies=["interface_compliance"]
            ),
            
            TestPhase(
                name="integration_testing",
                description="Integration Testing",
                test_groups=[
                    {
                        "name": "api_integration",
                        "command": "pytest tests/integration/test_mcp_integration.py -n 4 --dist=loadscope --tb=short",
                        "workers": 4
                    },
                    {
                        "name": "component_integration",
                        "command": "pytest tests/test_dispatcher*.py -n 3 --dist=loadfile --tb=short",
                        "workers": 3
                    },
                    {
                        "name": "watcher_integration", 
                        "command": "pytest tests/test_watcher.py -v --tb=short",
                        "workers": 1
                    }
                ],
                parallel_workers=3,
                estimated_duration_minutes=30,
                dependencies=["plugin_functionality"]
            ),
            
            TestPhase(
                name="performance_validation",
                description="Performance & SLO Validation",
                test_groups=[
                    {
                        "name": "benchmark_suite",
                        "command": "pytest tests/test_benchmarks.py --benchmark-autosave --benchmark-max-time=60 --tb=short",
                        "workers": 1
                    },
                    {
                        "name": "cache_performance",
                        "command": "pytest tests/test_cache.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "indexer_performance",
                        "command": "pytest tests/test_indexer*.py --benchmark-autosave --tb=short",
                        "workers": 2
                    }
                ],
                parallel_workers=3,
                estimated_duration_minutes=45,
                dependencies=["integration_testing"]
            ),
            
            TestPhase(
                name="resilience_testing",
                description="Error Handling & Edge Cases",
                test_groups=[
                    {
                        "name": "error_handling",
                        "command": "pytest tests/ -k 'error or exception or failure' -n 4 --tb=short",
                        "workers": 4
                    },
                    {
                        "name": "edge_cases",
                        "command": "pytest tests/ -k 'edge or boundary or limit' -n 3 --tb=short", 
                        "workers": 3
                    }
                ],
                parallel_workers=2,
                estimated_duration_minutes=30,
                dependencies=["performance_validation"]
            ),
            
            TestPhase(
                name="real_world_validation",
                description="Real-World Codebase Testing",
                test_groups=[
                    {
                        "name": "repository_indexing",
                        "command": "pytest tests/real_world/test_repository_indexing.py -v --benchmark-autosave --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "symbol_search",
                        "command": "pytest tests/real_world/test_symbol_search.py -v --tb=short",
                        "workers": 2
                    },
                    {
                        "name": "performance_scaling",
                        "command": "pytest tests/real_world/test_performance_scaling.py -v --benchmark-autosave --tb=short",
                        "workers": 1
                    },
                    {
                        "name": "memory_usage",
                        "command": "pytest tests/real_world/test_memory_usage.py -v --tb=short",
                        "workers": 1
                    },
                    {
                        "name": "developer_workflows",
                        "command": "pytest tests/real_world/test_developer_workflows.py -v --tb=short",
                        "workers": 2
                    }
                ],
                parallel_workers=3,
                estimated_duration_minutes=90,
                dependencies=["resilience_testing"]
            ),
            
            TestPhase(
                name="dormant_features_validation",
                description="Dormant Features Activation Testing",
                test_groups=[
                    {
                        "name": "semantic_search",
                        "command": "pytest tests/real_world/test_semantic_search.py -v --tb=short -m semantic",
                        "workers": 1
                    },
                    {
                        "name": "redis_caching",
                        "command": "pytest tests/real_world/test_redis_caching.py -v --tb=short -m cache",
                        "workers": 1
                    },
                    {
                        "name": "advanced_indexing",
                        "command": "pytest tests/real_world/test_advanced_indexing.py -v --tb=short -m advanced_indexing",
                        "workers": 2
                    },
                    {
                        "name": "cross_language",
                        "command": "pytest tests/real_world/test_cross_language.py -v --tb=short -m cross_language",
                        "workers": 2
                    }
                ],
                parallel_workers=2,
                estimated_duration_minutes=60,
                dependencies=["real_world_validation"]
            )
        ]
    
    async def run_test_command(self, group_name: str, command: str, phase_name: str) -> TestResult:
        """Execute a single test command asynchronously."""
        print(f"🚀 Starting {phase_name}::{group_name}: {command}")
        start_time = time.time()
        
        try:
            # Create process with proper environment
            env = os.environ.copy()
            env.update({
                "PYTHONPATH": str(Path.cwd()),
                "MCP_TEST_MODE": "1",
                "LOG_LEVEL": "WARNING",  # Reduce log noise during tests
                "MCP_TEST_PARALLEL": "1"
            })
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            duration = time.time() - start_time
            
            result = TestResult(
                phase=phase_name,
                group=group_name,
                command=command,
                exit_code=process.returncode,
                duration_seconds=duration,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'),
                success=process.returncode == 0
            )
            
            status_emoji = "✅" if result.success else "❌"
            print(f"{status_emoji} Completed {phase_name}::{group_name} in {duration:.1f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                phase=phase_name,
                group=group_name,
                command=command,
                exit_code=-1,
                duration_seconds=duration,
                stdout="",
                stderr=str(e),
                success=False
            )
            print(f"❌ Failed {phase_name}::{group_name}: {e}")
            return result
    
    async def run_phase(self, phase: TestPhase) -> List[TestResult]:
        """Execute all test groups in a phase concurrently."""
        print(f"\n🔄 Phase: {phase.name} - {phase.description}")
        print(f"📊 Running {len(phase.test_groups)} test groups with {phase.parallel_workers} workers")
        
        # Create semaphore to limit concurrent test groups
        semaphore = asyncio.Semaphore(phase.parallel_workers)
        
        async def run_with_semaphore(group):
            async with semaphore:
                return await self.run_test_command(
                    group["name"], 
                    group["command"], 
                    phase.name
                )
        
        # Execute all test groups concurrently
        tasks = [run_with_semaphore(group) for group in phase.test_groups]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and convert to TestResults
        phase_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Convert exception to failed TestResult
                phase_results.append(TestResult(
                    phase=phase.name,
                    group=phase.test_groups[i]["name"],
                    command=phase.test_groups[i]["command"],
                    exit_code=-1,
                    duration_seconds=0,
                    stdout="",
                    stderr=str(result),
                    success=False
                ))
            else:
                phase_results.append(result)
        
        # Print phase summary
        successful = sum(1 for r in phase_results if r.success)
        total = len(phase_results)
        total_duration = sum(r.duration_seconds for r in phase_results)
        
        print(f"📈 Phase {phase.name} complete: {successful}/{total} groups passed in {total_duration:.1f}s")
        
        return phase_results
    
    def check_dependencies(self, phase: TestPhase) -> bool:
        """Check if phase dependencies have been satisfied."""
        if not phase.dependencies:
            return True
            
        completed_phases = {r.phase for r in self.results if r.success}
        return all(dep in completed_phases for dep in phase.dependencies)
    
    async def run_all_phases(self, phases: List[TestPhase], fail_fast: bool = False) -> Dict:
        """Execute all test phases in dependency order."""
        print("🧪 Starting Comprehensive Parallel Testing Suite")
        print(f"⚙️  Configuration: {self.max_workers} max workers, {len(phases)} phases")
        
        remaining_phases = phases.copy()
        
        while remaining_phases:
            # Find phases that can run (dependencies satisfied)
            ready_phases = [p for p in remaining_phases if self.check_dependencies(p)]
            
            if not ready_phases:
                print("❌ Circular dependency detected or no runnable phases")
                break
            
            # Run ready phases
            for phase in ready_phases:
                phase_results = await self.run_phase(phase)
                self.results.extend(phase_results)
                remaining_phases.remove(phase)
                
                # Check for failures
                failed_groups = [r for r in phase_results if not r.success]
                if failed_groups and fail_fast:
                    print(f"💥 Fail-fast triggered. Failed groups in {phase.name}:")
                    for failure in failed_groups:
                        print(f"   ❌ {failure.group}: {failure.stderr[:100]}...")
                    return self.generate_report()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test execution report."""
        total_duration = time.time() - self.start_time
        
        # Group results by phase
        phases_summary = {}
        for phase_name in set(r.phase for r in self.results):
            phase_results = [r for r in self.results if r.phase == phase_name]
            phases_summary[phase_name] = {
                "total_groups": len(phase_results),
                "successful_groups": sum(1 for r in phase_results if r.success),
                "failed_groups": sum(1 for r in phase_results if not r.success),
                "total_duration": sum(r.duration_seconds for r in phase_results),
                "average_duration": sum(r.duration_seconds for r in phase_results) / len(phase_results) if phase_results else 0
            }
        
        # Overall statistics
        total_groups = len(self.results)
        successful_groups = sum(1 for r in self.results if r.success)
        success_rate = (successful_groups / total_groups * 100) if total_groups > 0 else 0
        
        report = {
            "execution_summary": {
                "total_duration_seconds": total_duration,
                "total_groups": total_groups,
                "successful_groups": successful_groups,
                "failed_groups": total_groups - successful_groups,
                "success_rate_percent": success_rate,
                "parallel_efficiency": total_duration / sum(r.duration_seconds for r in self.results) if self.results else 0
            },
            "phases_summary": phases_summary,
            "detailed_results": [asdict(r) for r in self.results],
            "failed_tests": [asdict(r) for r in self.results if not r.success],
            "performance_metrics": {
                "fastest_group": min(self.results, key=lambda r: r.duration_seconds, default=None),
                "slowest_group": max(self.results, key=lambda r: r.duration_seconds, default=None),
                "total_test_time": sum(r.duration_seconds for r in self.results)
            }
        }
        
        return report
    
    def print_summary(self, report: Dict):
        """Print human-readable test execution summary."""
        summary = report["execution_summary"]
        
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE PARALLEL TEST EXECUTION SUMMARY")
        print("="*80)
        
        print(f"⏱️  Total Execution Time: {summary['total_duration_seconds']:.1f} seconds")
        print(f"📊 Test Groups: {summary['successful_groups']}/{summary['total_groups']} passed ({summary['success_rate_percent']:.1f}%)")
        print(f"⚡ Parallel Efficiency: {summary['parallel_efficiency']:.2f}x speedup")
        
        print(f"\n📈 Phase Results:")
        for phase_name, phase_data in report["phases_summary"].items():
            status_emoji = "✅" if phase_data["failed_groups"] == 0 else "❌"
            print(f"  {status_emoji} {phase_name}: {phase_data['successful_groups']}/{phase_data['total_groups']} groups ({phase_data['total_duration']:.1f}s)")
        
        if report["failed_tests"]:
            print(f"\n❌ Failed Test Groups ({len(report['failed_tests'])}):")
            for failure in report["failed_tests"]:
                print(f"  💥 {failure['phase']}::{failure['group']}")
                print(f"     Command: {failure['command']}")
                print(f"     Error: {failure['stderr'][:200]}...")
                print()
        
        print("\n🎯 Next Steps:")
        if summary["success_rate_percent"] == 100:
            print("  ✨ All tests passed! Code-Index-MCP is ready for production.")
        elif summary["success_rate_percent"] >= 90:
            print("  ⚠️  Minor issues detected. Review failed tests and fix.")
        else:
            print("  🔴 Significant issues detected. Address failures before proceeding.")
        
        print(f"\n📄 Detailed results saved to: test_results/parallel_test_report.json")


def setup_test_environment():
    """Set up the test environment and dependencies."""
    print("🔧 Setting up test environment...")
    
    # Create test results directories
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    (results_dir / "reports").mkdir(exist_ok=True)
    (results_dir / "benchmarks").mkdir(exist_ok=True)
    (results_dir / "coverage").mkdir(exist_ok=True)
    
    # Install test dependencies if missing
    try:
        import pytest_benchmark  # noqa
        import pytest_html  # noqa
        import pytest_cov  # noqa
        import pytest_xdist  # noqa
    except ImportError:
        print("📦 Installing missing test dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "pytest-benchmark", "pytest-html", "pytest-cov", "pytest-xdist"
        ], check=True)
    
    print("✅ Test environment ready")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Run comprehensive parallel tests for Code-Index-MCP")
    parser.add_argument("--phases", nargs="+", help="Specific phases to run", 
                       choices=["interface_compliance", "plugin_functionality", "integration_testing", 
                               "performance_validation", "resilience_testing", "real_world_validation", 
                               "dormant_features_validation"])
    parser.add_argument("--max-workers", type=int, help="Maximum parallel workers")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first phase failure")
    parser.add_argument("--setup-only", action="store_true", help="Only setup environment, don't run tests")
    parser.add_argument("--setup-real-world", action="store_true", help="Setup real-world testing environment and download repositories")
    
    args = parser.parse_args()
    
    # Setup environment
    setup_test_environment()
    
    if args.setup_only:
        print("✅ Environment setup complete. Run without --setup-only to execute tests.")
        return
    
    # Setup real-world testing environment if requested
    if args.setup_real_world:
        print("🌍 Setting up real-world testing environment...")
        try:
            # Run the repository download script
            subprocess.run([
                sys.executable, "scripts/development/download_test_repos.py", "--tier", "tier1"
            ], check=True)
            print("✅ Real-world testing environment setup complete.")
            print("   Run with --phases real_world_validation to execute real-world tests.")
            return
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup real-world environment: {e}")
            sys.exit(1)
    
    # Create test runner
    runner = ParallelTestRunner(max_workers=args.max_workers)
    phases = runner.create_test_phases()
    
    # Filter phases if specific ones requested
    if args.phases:
        phases = [p for p in phases if p.name in args.phases]
        print(f"🎯 Running specific phases: {', '.join(args.phases)}")
    
    # Execute tests
    try:
        report = await runner.run_all_phases(phases, fail_fast=args.fail_fast)
        
        # Save detailed report
        report_path = Path("test_results/parallel_test_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        runner.print_summary(report)
        
        # Exit with appropriate code
        success_rate = report["execution_summary"]["success_rate_percent"]
        sys.exit(0 if success_rate == 100 else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())