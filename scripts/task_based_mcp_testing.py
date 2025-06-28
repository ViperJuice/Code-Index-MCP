#!/usr/bin/env python3
"""
Task-based MCP vs Native Testing using Claude Code agents

This script launches separate Claude Code agents using the Task tool to
perform real comparisons between MCP and native retrieval methods.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import argparse
from mcp_server.core.path_utils import PathUtils

# Test queries organized by category
TEST_QUERIES = {
    "symbol": [
        "Find the BM25Indexer class definition",
        "Where is the SQLiteStore class implemented?",
        "Locate the PluginManager class",
        "Find the EnhancedDispatcher class definition",
        "Show me the PathResolver implementation"
    ],
    "content": [
        "Search for TODO comments in the codebase",
        "Find all error handling code",
        "Search for database query implementations",
        "Find all API endpoint definitions",
        "Locate authentication logic"
    ],
    "navigation": [
        "Find all test files for the indexer module",
        "Show all Python files in the plugins directory",
        "List all configuration files",
        "Find files that import SQLiteStore",
        "Show all markdown documentation"
    ],
    "refactoring": [
        "Find all usages of the search method",
        "Show all subclasses of BasePlugin",
        "Find all calls to index_file",
        "List all implementations of the Plugin interface",
        "Show impact of renaming BM25Indexer"
    ],
    "understanding": [
        "Explain how the plugin system works",
        "Show the flow of the indexing process",
        "Find the entry point for the MCP server",
        "Explain the purpose of the dispatcher",
        "Show how file watching is implemented"
    ]
}

# Repository configurations
TEST_REPOS = {
    "gin": {
        "path": "PathUtils.get_workspace_root()/test_indexes/gin",
        "language": "go",
        "file_count": 112
    },
    "django": {
        "path": "PathUtils.get_workspace_root()/test_indexes/django",
        "language": "python", 
        "file_count": 5497
    },
    "react": {
        "path": "PathUtils.get_workspace_root()/test_indexes/react",
        "language": "javascript",
        "file_count": 6261
    }
}


def create_mcp_test_prompt(query: str, repo_name: str, repo_path: str) -> str:
    """Create prompt for MCP-enabled agent"""
    return f"""You are testing MCP tools for code search performance analysis.

IMPORTANT: You MUST use MCP tools for this test. Available MCP tools:
- mcp__code-index-mcp__symbol_lookup
- mcp__code-index-mcp__search_code
- mcp__code-index-mcp__get_status

Repository: {repo_name}
Working Directory: {repo_path}
Query: {query}

Instructions:
1. Use MCP tools to answer the query
2. Record the time taken and number of results
3. Note which MCP tools you used
4. Count the tokens in tool responses
5. Report your findings in a structured format

Output format:
```json
{{
  "query": "{query}",
  "mode": "mcp",
  "tools_used": ["tool1", "tool2"],
  "results_found": <number>,
  "execution_time": <seconds>,
  "token_estimate": <count>,
  "success": true/false
}}
```"""


def create_native_test_prompt(query: str, repo_name: str, repo_path: str) -> str:
    """Create prompt for native-only agent"""
    return f"""You are testing native code search tools for performance analysis.

IMPORTANT: You MUST NOT use any MCP tools. Only use:
- Grep
- Find  
- Read
- Glob
- LS

Repository: {repo_name}
Working Directory: {repo_path}
Query: {query}

Instructions:
1. Use ONLY native tools (grep, find, read) to answer the query
2. Record the time taken and number of results
3. Note which tools you used and how many times
4. Count approximate tokens in file contents read
5. Report your findings in a structured format

Output format:
```json
{{
  "query": "{query}",
  "mode": "native",
  "tools_used": ["tool1", "tool2"],
  "results_found": <number>,
  "execution_time": <seconds>,
  "token_estimate": <count>,
  "success": true/false
}}
```"""


def create_analysis_prompt(test_results: List[Dict]) -> str:
    """Create prompt for analyzing test results"""
    return f"""Analyze the following MCP vs Native performance test results:

Test Results:
```json
{json.dumps(test_results, indent=2)}
```

Please provide:
1. Performance comparison (speed, tokens, accuracy)
2. Tool usage patterns
3. Success rates
4. Recommendations for when to use each approach
5. Summary statistics

Format your response as a comprehensive analysis report."""


def save_results(results: List[Dict], output_dir: Path):
    """Save test results to file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save raw results
    results_file = output_dir / f"task_test_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate summary
    summary = {
        "timestamp": timestamp,
        "total_tests": len(results),
        "mcp_tests": len([r for r in results if r.get('mode') == 'mcp']),
        "native_tests": len([r for r in results if r.get('mode') == 'native']),
        "successful_tests": len([r for r in results if r.get('success', False)]),
        "repositories_tested": list(set(r.get('repository', '') for r in results))
    }
    
    summary_file = output_dir / f"task_test_summary_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Results saved to: {results_file}")
    print(f"Summary saved to: {summary_file}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Task-based MCP vs Native Testing')
    parser.add_argument('--repo', type=str, choices=list(TEST_REPOS.keys()),
                       default='gin', help='Repository to test')
    parser.add_argument('--category', type=str, choices=list(TEST_QUERIES.keys()),
                       default='symbol', help='Query category to test')
    parser.add_argument('--queries', type=int, default=3,
                       help='Number of queries to test per mode')
    parser.add_argument('--output', type=Path,
                       default=Path('PathUtils.get_workspace_root()/test_results/task_tests'),
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Get repository info
    repo_info = TEST_REPOS[args.repo]
    
    # Get queries for the category
    queries = TEST_QUERIES[args.category][:args.queries]
    
    print(f"=== Task-based MCP vs Native Testing ===")
    print(f"Repository: {args.repo} ({repo_info['file_count']} files)")
    print(f"Category: {args.category}")
    print(f"Queries: {len(queries)}")
    print()
    
    # Instructions for running the tests
    print("To run the tests, use the Task tool with these prompts:")
    print("\n" + "="*60 + "\n")
    
    test_configs = []
    
    # Generate test configurations
    for i, query in enumerate(queries, 1):
        # MCP test
        mcp_prompt = create_mcp_test_prompt(query, args.repo, repo_info['path'])
        print(f"Test {i}a (MCP) - Query: {query}")
        print(f"Prompt:\n{mcp_prompt}")
        print("\n" + "-"*60 + "\n")
        
        test_configs.append({
            "test_id": f"{i}a_mcp",
            "query": query,
            "mode": "mcp",
            "repository": args.repo,
            "prompt": mcp_prompt
        })
        
        # Native test  
        native_prompt = create_native_test_prompt(query, args.repo, repo_info['path'])
        print(f"Test {i}b (Native) - Query: {query}")
        print(f"Prompt:\n{native_prompt}")
        print("\n" + "="*60 + "\n")
        
        test_configs.append({
            "test_id": f"{i}b_native",
            "query": query,
            "mode": "native",
            "repository": args.repo,
            "prompt": native_prompt
        })
    
    # Save test configurations
    config_file = args.output / f"test_configs_{args.repo}_{args.category}.json"
    with open(config_file, 'w') as f:
        json.dump(test_configs, f, indent=2)
    
    print(f"Test configurations saved to: {config_file}")
    print("\nNext steps:")
    print("1. Use the Task tool to run each test prompt")
    print("2. Collect the JSON results from each agent")
    print("3. Run the analysis prompt to compare results")
    
    # Create analysis prompt template
    print("\n" + "="*60 + "\n")
    print("After collecting results, use this analysis prompt:")
    print(create_analysis_prompt([{"placeholder": "results will go here"}]))


if __name__ == '__main__':
    main()