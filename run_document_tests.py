#!/usr/bin/env python3
"""Run document processing tests in parallel."""

import asyncio
import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class TestResult:
    name: str
    status: str
    duration: float
    message: str = ""
    errors: List[str] = field(default_factory=list)


class SimpleTestRunner:
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def run_test(self, test_file: str) -> TestResult:
        """Run a single test file."""
        start = time.time()
        
        try:
            # Run pytest on the file
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-q", "--no-cov"],
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout per test
            )
            
            duration = time.time() - start
            
            if result.returncode == 0:
                # Count passed tests
                passed = result.stdout.count(" PASSED")
                return TestResult(
                    name=test_file,
                    status="passed",
                    duration=duration,
                    message=f"{passed} tests passed"
                )
            else:
                # Extract failure info
                failed = result.stdout.count(" FAILED")
                errors = []
                if "FAILED" in result.stdout:
                    errors.append(result.stdout)
                if result.stderr:
                    errors.append(result.stderr)
                    
                return TestResult(
                    name=test_file,
                    status="failed",
                    duration=duration,
                    message=f"{failed} tests failed",
                    errors=errors[:5]  # Limit error output
                )
                
        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_file,
                status="timeout",
                duration=60.0,
                message="Test timed out"
            )
        except Exception as e:
            return TestResult(
                name=test_file,
                status="error",
                duration=time.time() - start,
                message=str(e)
            )
    
    async def run_tests_parallel(self, test_files: List[str], max_workers: int = 4):
        """Run tests in parallel."""
        self.start_time = datetime.now()
        print(f"🚀 Running {len(test_files)} test files with {max_workers} workers")
        print("="*60)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tests
            futures = [(f, executor.submit(self.run_test, f)) for f in test_files]
            
            # Collect results
            for test_file, future in futures:
                try:
                    result = future.result(timeout=90)
                    self.results.append(result)
                    
                    # Print progress
                    icon = "✅" if result.status == "passed" else "❌"
                    print(f"{icon} {Path(test_file).stem}: {result.message} ({result.duration:.2f}s)")
                    
                except Exception as e:
                    print(f"❌ {Path(test_file).stem}: Error - {e}")
                    self.results.append(TestResult(
                        name=test_file,
                        status="error",
                        duration=0,
                        message=str(e)
                    ))
        
        self.end_time = datetime.now()
    
    def print_summary(self):
        """Print test summary."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        errors = sum(1 for r in self.results if r.status in ["error", "timeout"])
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors/Timeouts: {errors}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        
        if failed > 0 or errors > 0:
            print("\n❌ FAILED TESTS:")
            for r in self.results:
                if r.status in ["failed", "error", "timeout"]:
                    print(f"\n{r.name}:")
                    print(f"  Status: {r.status}")
                    print(f"  Message: {r.message}")
                    if r.errors:
                        print("  First error:")
                        print("  " + "\n  ".join(r.errors[0].split('\n')[:5]))
        
        # Save detailed report
        report = {
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "duration": total_duration,
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat()
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "duration": r.duration,
                    "message": r.message
                }
                for r in self.results
            ]
        }
        
        with open("test_results/document_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return passed == len(self.results)


async def main():
    # Define test files to run
    test_files = [
        # Unit tests
        "test_markdown_parser.py",
        "test_plaintext_nlp.py",
        "test_chunk_optimizer.py",
        "test_metadata_extractor.py",
        "test_document_interfaces.py",
        
        # Integration tests  
        "test_plugin_integration.py",
        "test_dispatcher_document_routing.py",
        "test_semantic_document_integration.py",
        "test_document_storage.py",
        
        # Feature tests
        "test_natural_language_queries.py",
        "test_document_structure_extraction.py",
        "test_cross_document_search.py",
        "test_metadata_search.py",
        "test_section_search.py",
        
        # Performance tests
        "test_document_indexing_performance.py",
        "test_document_search_performance.py",
        "test_document_memory_usage.py",
        
        # Edge cases
        "test_malformed_documents.py",
        "test_document_edge_cases.py",
        "test_unicode_documents.py",
        "test_document_error_recovery.py"
    ]
    
    # Filter to only existing files
    existing_files = [f for f in test_files if Path(f).exists()]
    
    if not existing_files:
        print("❌ No test files found!")
        sys.exit(1)
    
    print(f"Found {len(existing_files)} test files")
    
    # Create results directory
    Path("test_results").mkdir(exist_ok=True)
    
    # Run tests
    runner = SimpleTestRunner()
    await runner.run_tests_parallel(existing_files, max_workers=4)
    
    # Print summary
    all_passed = runner.print_summary()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())