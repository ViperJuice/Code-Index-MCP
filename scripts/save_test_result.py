#!/usr/bin/env python3
"""
Save test results from Task tool execution.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse


def save_result(test_id: str, result_json: str, batch_name: str = None):
    """Save test result to the results directory."""
    output_dir = Path("test_results/performance_tests/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse result
    try:
        result = json.loads(result_json)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Please provide valid JSON")
        return False
        
    # Add metadata
    result['test_id'] = test_id
    result['timestamp'] = datetime.now().isoformat()
    if batch_name:
        result['batch_name'] = batch_name
        
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = output_dir / f"result_{test_id}_{timestamp}.json"
    
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
        
    print(f"Result saved to: {result_file}")
    
    # Update checkpoint
    checkpoint_file = output_dir / f"checkpoint_{batch_name or 'manual'}.json"
    completed = set()
    
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
            completed = set(checkpoint_data.get('completed', []))
            
    completed.add(test_id)
    
    with open(checkpoint_file, 'w') as f:
        json.dump({
            'completed': list(completed),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)
        
    return True


def main():
    parser = argparse.ArgumentParser(description="Save test results from Task execution")
    parser.add_argument("test_id", help="Test ID (e.g., go_gin_0_mcp)")
    parser.add_argument("--batch", help="Batch name (e.g., go_gin)")
    parser.add_argument("--json", help="Result JSON (if not provided, reads from stdin)")
    parser.add_argument("--file", help="Read result from JSON file")
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, 'r') as f:
            result_json = f.read()
    elif args.json:
        result_json = args.json
    else:
        print("Enter JSON result (Ctrl+D when done):")
        result_json = sys.stdin.read()
        
    save_result(args.test_id, result_json, args.batch)


if __name__ == "__main__":
    main()