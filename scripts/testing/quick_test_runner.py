#!/usr/bin/env python3
"""
Quick test runner - Simplified interface for running the next test.
"""

import subprocess
import sys
import json
from pathlib import Path


def get_next_repo_with_tests():
    """Find the next repository that has pending tests."""
    repos = ['go_gin', 'python_django', 'javascript_react', 'rust_tokio']
    
    for repo in repos:
        # Check if repo has pending tests
        result = subprocess.run(
            ['python', 'scripts/run_test_batch.py', '--status', repo],
            capture_output=True,
            text=True
        )
        
        if "Pending: 0" not in result.stdout and "Progress: 100.0%" not in result.stdout:
            return repo
            
    return None


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        subprocess.run(['python', 'scripts/test_progress_dashboard.py'])
        return
        
    print("\n🚀 Quick Test Runner")
    print("=" * 50)
    
    # Find next repo with tests
    repo = get_next_repo_with_tests()
    
    if not repo:
        print("✅ All tests completed! Ready for analysis.")
        print("\nRun analysis with:")
        print("  python scripts/run_comprehensive_performance_test.py --analyze")
        return
        
    print(f"\n📁 Next repository: {repo}")
    print("-" * 50)
    
    # Get next test prompt
    result = subprocess.run(
        ['python', 'scripts/run_test_batch.py', '--next', repo],
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print(result.stdout)
        
        # Extract test ID from output
        lines = result.stdout.split('\n')
        test_id = None
        for line in lines:
            if line.startswith("Test ID:"):
                test_id = line.split(":")[1].strip()
                break
                
        if test_id:
            print("\n" + "="*50)
            print("📋 TO SAVE RESULT AFTER TASK EXECUTION:")
            print(f"python scripts/save_test_result.py {test_id} --batch {repo} --json '<RESULT_JSON>'")
            print("="*50)
            
            print("\n💡 TIPS:")
            print("- Copy the prompt above and use with Task tool")
            print("- Save the JSON result using the command shown")
            print("- Run 'python scripts/quick_test_runner.py' for next test")
            print("- Run 'python scripts/quick_test_runner.py --dashboard' to see progress")
    else:
        print("Error getting next test")


if __name__ == "__main__":
    main()