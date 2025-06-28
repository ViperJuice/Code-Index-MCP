#!/usr/bin/env python3
"""
Batch execution helper for performance tests.
Streamlines the process of running multiple tests.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import subprocess
import time


class BatchTestRunner:
    def __init__(self):
        self.test_dir = Path("test_results/performance_tests")
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def list_batches(self):
        """List all available test batches."""
        batch_files = list(self.test_dir.glob("test_batch_*.json"))
        
        if not batch_files:
            print("No test batches found!")
            return
            
        print("\nAvailable test batches:")
        print("-" * 50)
        
        for batch_file in sorted(batch_files):
            with open(batch_file, 'r') as f:
                data = json.load(f)
                
            # Check progress
            checkpoint_file = self.results_dir / f"checkpoint_{data['batch_name']}.json"
            completed = 0
            
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                    completed = len(checkpoint.get('completed', []))
                    
            total = data['test_count']
            progress = completed / total * 100 if total > 0 else 0
            
            print(f"\n{data['batch_name']}:")
            print(f"  File: {batch_file.name}")
            print(f"  Tests: {total}")
            print(f"  Progress: {completed}/{total} ({progress:.1f}%)")
            
    def get_batch_status(self, batch_name: str):
        """Get detailed status for a specific batch."""
        batch_file = self.test_dir / f"test_batch_{batch_name}_*.json"
        batch_files = list(self.test_dir.glob(f"test_batch_{batch_name}_*.json"))
        
        if not batch_files:
            print(f"No batch found for: {batch_name}")
            return
            
        batch_file = batch_files[0]
        
        cmd = ["python", "scripts/execute_performance_tests.py", str(batch_file), "--status"]
        subprocess.run(cmd)
        
    def get_next_test(self, batch_name: str):
        """Get next test prompt for a batch."""
        batch_files = list(self.test_dir.glob(f"test_batch_{batch_name}_*.json"))
        
        if not batch_files:
            print(f"No batch found for: {batch_name}")
            return None
            
        batch_file = batch_files[0]
        
        # Get next test
        cmd = ["python", "scripts/execute_performance_tests.py", str(batch_file), "--next"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
            
            # Extract test ID from output
            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith("Test ID:"):
                    return line.split(":")[1].strip()
                    
        return None
        
    def generate_summary_report(self):
        """Generate summary report of all completed tests."""
        all_results = []
        
        # Collect all results
        for result_file in self.results_dir.glob("result_*.json"):
            with open(result_file, 'r') as f:
                all_results.append(json.load(f))
                
        if not all_results:
            print("No results found yet!")
            return
            
        # Group by repository
        by_repo = {}
        for result in all_results:
            repo = result.get('batch_name', 'unknown')
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append(result)
            
        # Generate report
        print("\n" + "="*70)
        print("PERFORMANCE TEST SUMMARY REPORT")
        print("="*70)
        print(f"Total tests completed: {len(all_results)}")
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for repo, results in sorted(by_repo.items()):
            print(f"\n\n{repo.upper()} Repository")
            print("-" * 50)
            
            # Separate by mode
            mcp_results = [r for r in results if r['mode'] == 'mcp']
            native_results = [r for r in results if r['mode'] == 'native']
            
            # Calculate averages
            if mcp_results:
                avg_mcp_time = sum(r['execution_time_ms'] for r in mcp_results) / len(mcp_results)
                avg_mcp_tokens = sum(r['token_estimate'] for r in mcp_results) / len(mcp_results)
                mcp_success_rate = sum(1 for r in mcp_results if r['success']) / len(mcp_results) * 100
            else:
                avg_mcp_time = avg_mcp_tokens = mcp_success_rate = 0
                
            if native_results:
                avg_native_time = sum(r['execution_time_ms'] for r in native_results) / len(native_results)
                avg_native_tokens = sum(r['token_estimate'] for r in native_results) / len(native_results)
                native_success_rate = sum(1 for r in native_results if r['success']) / len(native_results) * 100
            else:
                avg_native_time = avg_native_tokens = native_success_rate = 0
                
            print(f"\nMCP Mode ({len(mcp_results)} tests):")
            print(f"  Average time: {avg_mcp_time:.0f}ms")
            print(f"  Average tokens: {avg_mcp_tokens:.0f}")
            print(f"  Success rate: {mcp_success_rate:.1f}%")
            
            print(f"\nNative Mode ({len(native_results)} tests):")
            print(f"  Average time: {avg_native_time:.0f}ms")
            print(f"  Average tokens: {avg_native_tokens:.0f}")
            print(f"  Success rate: {native_success_rate:.1f}%")
            
            # Show individual test results
            print(f"\nDetailed Results:")
            for result in sorted(results, key=lambda x: x['test_id']):
                status = "✓" if result['success'] else "✗"
                print(f"  [{status}] {result['test_id']}: {result['query']}")
                print(f"      Time: {result['execution_time_ms']}ms, Tokens: {result['token_estimate']}")
                if result.get('error'):
                    print(f"      Error: {result['error']}")
                    
    def save_summary_report(self, output_file: str = None):
        """Save summary report to file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_results/performance_tests/summary_report_{timestamp}.txt"
            
        # Redirect stdout to capture report
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            self.generate_summary_report()
            
        report_content = f.getvalue()
        
        with open(output_file, 'w') as f:
            f.write(report_content)
            
        print(f"\nReport saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Batch test execution helper")
    parser.add_argument("--list", action="store_true", help="List all test batches")
    parser.add_argument("--status", help="Show status for specific batch")
    parser.add_argument("--next", help="Get next test for specific batch")
    parser.add_argument("--summary", action="store_true", help="Generate summary report")
    parser.add_argument("--save-summary", help="Save summary report to file")
    
    args = parser.parse_args()
    
    runner = BatchTestRunner()
    
    if args.list:
        runner.list_batches()
    elif args.status:
        runner.get_batch_status(args.status)
    elif args.next:
        runner.get_next_test(args.next)
    elif args.summary:
        runner.generate_summary_report()
    elif args.save_summary:
        runner.save_summary_report(args.save_summary)
    else:
        print("\nBatch Test Runner")
        print("-" * 50)
        print("\nUsage:")
        print("  python run_test_batch.py --list           # List all batches")
        print("  python run_test_batch.py --status go_gin  # Check batch status")
        print("  python run_test_batch.py --next go_gin    # Get next test")
        print("  python run_test_batch.py --summary        # Generate report")
        print("  python run_test_batch.py --save-summary   # Save report to file")
        print("\nWorkflow:")
        print("  1. Use --list to see available batches")
        print("  2. Use --next <batch> to get test prompt")
        print("  3. Execute test with Task tool")
        print("  4. Save result with save_test_result.py")
        print("  5. Repeat until batch is complete")
        print("  6. Use --summary to view results")


if __name__ == "__main__":
    main()