#!/usr/bin/env python3
"""
Re-run failed native tests with corrected source code paths.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Mapping of old paths to new paths
PATH_CORRECTIONS = {
    "go_gin": {
        "old": "PathUtils.get_workspace_root()/test_indexes/go_gin",
        "new": "PathUtils.get_workspace_root()/test_repos/modern/go/gin"
    },
    "python_django": {
        "old": "PathUtils.get_workspace_root()/test_indexes/python_django",
        "new": "PathUtils.get_workspace_root()/test_repos/web/python/django"
    },
    "javascript_react": {
        "old": "PathUtils.get_workspace_root()/test_indexes/javascript_react",
        "new": "PathUtils.get_workspace_root()/test_repos/web/javascript/react"
    },
    "rust_tokio": {
        "old": "PathUtils.get_workspace_root()/test_indexes/rust_tokio",
        "new": "PathUtils.get_workspace_root()/test_repos/systems/rust/tokio"
    }
}

def find_failed_native_tests():
    """Find all native tests that failed due to path issues."""
    results_dir = Path("test_results/performance_tests/results")
    failed_tests = []
    
    for result_file in results_dir.glob("result_*_native_*.json"):
        with open(result_file, 'r') as f:
            result = json.load(f)
            
        # Check if it failed due to no source files
        if not result.get('success', True):
            error = result.get('error', '')
            if 'No source code files' in error or 'only index' in error.lower():
                failed_tests.append({
                    'file': result_file,
                    'result': result
                })
                
    return failed_tests

def generate_corrected_prompts(failed_tests):
    """Generate corrected prompts for failed tests."""
    corrected_tests = []
    
    for test_info in failed_tests:
        result = test_info['result']
        test_id = result.get('test_id', '')
        batch_name = result.get('batch_name', '')
        query = result.get('query', '')
        
        # Find the correct path
        new_path = None
        for repo_name, paths in PATH_CORRECTIONS.items():
            if repo_name in batch_name:
                new_path = paths['new']
                break
                
        if new_path:
            # Create corrected prompt
            prompt = f"""You are testing native tools for performance analysis.

Repository: {batch_name} ({get_language(batch_name)})
Working Directory: {new_path}
Query: {query}
Category: symbol

Instructions:
1. Use ONLY native tools (grep, find, glob, ls, read)
2. NO MCP tools allowed
3. Time your query execution
4. Count results found
5. Track tool calls made
6. Estimate tokens used

Output JSON only:
```json
{{
  "query": "{query}",
  "mode": "native",
  "tools_used": ["list", "of", "tools"],
  "tool_calls": {{"tool_name": count}},
  "results_found": number,
  "execution_time_ms": milliseconds,
  "token_estimate": number,
  "success": true/false,
  "error": null_or_string
}}
```"""
            
            corrected_tests.append({
                'test_id': test_id + '_corrected',
                'original_file': str(test_info['file']),
                'prompt': prompt,
                'batch_name': batch_name,
                'query': query
            })
            
    return corrected_tests

def get_language(batch_name):
    """Get language from batch name."""
    if 'go' in batch_name:
        return 'go'
    elif 'python' in batch_name:
        return 'python'
    elif 'javascript' in batch_name:
        return 'javascript'
    elif 'rust' in batch_name:
        return 'rust'
    return 'unknown'

def save_corrected_tests(corrected_tests):
    """Save corrected test configurations."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(f"test_results/performance_tests/corrected_native_tests_{timestamp}.json")
    
    with open(output_file, 'w') as f:
        json.dump(corrected_tests, f, indent=2)
        
    return output_file

def main():
    print("🔧 Re-run Failed Native Tests with Corrected Paths")
    print("=" * 60)
    
    # Find failed tests
    print("\n📋 Finding failed native tests...")
    failed_tests = find_failed_native_tests()
    print(f"Found {len(failed_tests)} failed native tests")
    
    if not failed_tests:
        print("No failed native tests found!")
        return
        
    # Show failed tests
    print("\nFailed tests:")
    for test in failed_tests:
        result = test['result']
        print(f"  - {result.get('test_id', 'unknown')}: {result.get('query', 'unknown query')}")
        
    # Generate corrected prompts
    print("\n🔄 Generating corrected prompts...")
    corrected_tests = generate_corrected_prompts(failed_tests)
    
    # Save corrected tests
    output_file = save_corrected_tests(corrected_tests)
    print(f"\n💾 Saved {len(corrected_tests)} corrected test configurations to:")
    print(f"   {output_file}")
    
    # Show next steps
    print("\n📋 Next Steps:")
    print("1. Use the Task tool to execute each corrected test")
    print("2. Save results with the corrected test ID")
    print("3. Run analysis to compare MCP vs Native performance")
    
    # Print first corrected test as example
    if corrected_tests:
        print(f"\n🔍 Example - First corrected test:")
        print(f"Test ID: {corrected_tests[0]['test_id']}")
        print(f"Query: {corrected_tests[0]['query']}")
        print("\nPrompt to use with Task tool:")
        print("-" * 60)
        print(corrected_tests[0]['prompt'])
        print("-" * 60)

if __name__ == "__main__":
    main()