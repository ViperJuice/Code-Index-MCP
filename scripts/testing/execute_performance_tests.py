#!/usr/bin/env python3
"""
Execute MCP vs Native performance tests using Task tool.
Processes test configurations and saves results.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import time
import argparse

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExecutor:
    def __init__(self, batch_file: str, output_dir: str = "test_results/performance_tests/results"):
        self.batch_file = Path(batch_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load test batch
        with open(self.batch_file, 'r') as f:
            self.batch_data = json.load(f)
            
        # Create checkpoint file to track progress
        self.checkpoint_file = self.output_dir / f"checkpoint_{self.batch_data['batch_name']}.json"
        self.completed_tests = self.load_checkpoint()
        
    def load_checkpoint(self) -> set:
        """Load completed test IDs from checkpoint."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return set(json.load(f).get('completed', []))
        return set()
        
    def save_checkpoint(self):
        """Save progress to checkpoint file."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                'completed': list(self.completed_tests),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
            
    def save_result(self, test_id: str, result: Dict[str, Any]):
        """Save individual test result."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.output_dir / f"result_{test_id}_{timestamp}.json"
        
        # Add metadata
        result['test_id'] = test_id
        result['timestamp'] = datetime.now().isoformat()
        result['batch_name'] = self.batch_data['batch_name']
        
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
            
        print(f"Saved result to {result_file}")
        
    def execute_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test and return results."""
        test_id = test_config['test_id']
        prompt = test_config['prompt']
        
        print(f"\n{'='*70}")
        print(f"Executing test: {test_id}")
        print(f"Mode: {test_config['mode']}")
        print(f"Query: {test_config['query_info']['query']}")
        print(f"{'='*70}\n")
        
        # For now, return a placeholder result
        # In actual execution, this would use the Task tool
        result = {
            "query": test_config['query_info']['query'],
            "mode": test_config['mode'],
            "tools_used": [],
            "tool_calls": {},
            "results_found": 0,
            "execution_time_ms": 0,
            "token_estimate": 0,
            "success": False,
            "error": "Manual execution required - use Task tool with provided prompt"
        }
        
        return result
        
    def run_all_tests(self, start_from: int = 0):
        """Run all tests in the batch."""
        tests = self.batch_data['tests']
        total_tests = len(tests)
        
        print(f"\nProcessing batch: {self.batch_data['batch_name']}")
        print(f"Total tests: {total_tests}")
        print(f"Already completed: {len(self.completed_tests)}")
        
        for i, test_config in enumerate(tests[start_from:], start=start_from):
            test_id = test_config['test_id']
            
            # Skip if already completed
            if test_id in self.completed_tests:
                print(f"Skipping completed test: {test_id}")
                continue
                
            print(f"\n[{i+1}/{total_tests}] Processing {test_id}")
            
            try:
                # Execute test
                result = self.execute_test(test_config)
                
                # Save result
                self.save_result(test_id, result)
                
                # Update checkpoint
                self.completed_tests.add(test_id)
                self.save_checkpoint()
                
                # Small delay between tests
                time.sleep(1)
                
            except Exception as e:
                print(f"Error executing test {test_id}: {e}")
                continue
                
        print(f"\nBatch complete! Processed {len(self.completed_tests)} tests")
        
    def get_next_test_prompt(self) -> Dict[str, Any]:
        """Get the next test that needs to be executed."""
        for test_config in self.batch_data['tests']:
            if test_config['test_id'] not in self.completed_tests:
                return test_config
        return None
        
    def print_test_prompt(self, test_id: str = None):
        """Print the prompt for a specific test or the next pending test."""
        if test_id:
            # Find specific test
            for test_config in self.batch_data['tests']:
                if test_config['test_id'] == test_id:
                    print(f"\n{'='*70}")
                    print(f"Test ID: {test_id}")
                    print(f"Mode: {test_config['mode']}")
                    print(f"Query: {test_config['query_info']['query']}")
                    print(f"{'='*70}\n")
                    print("PROMPT TO USE WITH TASK TOOL:")
                    print("-" * 70)
                    print(test_config['prompt'])
                    print("-" * 70)
                    return
            print(f"Test {test_id} not found")
        else:
            # Get next pending test
            next_test = self.get_next_test_prompt()
            if next_test:
                self.print_test_prompt(next_test['test_id'])
            else:
                print("All tests completed!")


def main():
    parser = argparse.ArgumentParser(description="Execute performance tests")
    parser.add_argument("batch_file", help="Path to test batch JSON file")
    parser.add_argument("--test-id", help="Print prompt for specific test ID")
    parser.add_argument("--next", action="store_true", help="Print prompt for next pending test")
    parser.add_argument("--status", action="store_true", help="Show batch completion status")
    
    args = parser.parse_args()
    
    executor = TestExecutor(args.batch_file)
    
    if args.status:
        total = len(executor.batch_data['tests'])
        completed = len(executor.completed_tests)
        pending = total - completed
        print(f"\nBatch: {executor.batch_data['batch_name']}")
        print(f"Total tests: {total}")
        print(f"Completed: {completed}")
        print(f"Pending: {pending}")
        print(f"Progress: {completed/total*100:.1f}%")
        
        if pending > 0:
            print("\nPending tests:")
            for test in executor.batch_data['tests']:
                if test['test_id'] not in executor.completed_tests:
                    print(f"  - {test['test_id']}: {test['query_info']['query']}")
                    
    elif args.test_id:
        executor.print_test_prompt(args.test_id)
        
    elif args.next:
        executor.print_test_prompt()
        
    else:
        print("\nThis script helps manage test execution.")
        print("\nUsage:")
        print("  python execute_performance_tests.py <batch_file> --next")
        print("  python execute_performance_tests.py <batch_file> --status")
        print("  python execute_performance_tests.py <batch_file> --test-id <id>")
        print("\nTo execute tests:")
        print("  1. Run with --next to get the next test prompt")
        print("  2. Use the Task tool with the provided prompt")
        print("  3. Save the JSON result using the save_test_result.py script")
        print("  4. Repeat until all tests are complete")


if __name__ == "__main__":
    main()