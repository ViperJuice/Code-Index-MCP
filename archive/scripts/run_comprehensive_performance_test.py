#!/usr/bin/env python3
"""
Comprehensive Performance Test Orchestrator for MCP vs Native Retrieval

This script orchestrates the full testing process including:
1. Repository validation
2. Query generation 
3. Test execution using Task agents
4. Result collection and analysis
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import argparse
import random

# Import test suite components
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.standardized_query_test_suite import StandardizedQueryTestSuite, QueryCategory

# Test repositories that passed validation
VALID_TEST_REPOS = {
    "go_gin": {
        "path": "/workspaces/Code-Index-MCP/test_indexes/go_gin",
        "language": "go",
        "file_count": 93,
        "main_class": "Engine",
        "main_function": "New",
        "config_variable": "defaultTrustedProxies"
    },
    "python_django": {
        "path": "/workspaces/Code-Index-MCP/test_indexes/python_django", 
        "language": "python",
        "file_count": 5497,
        "main_class": "Model",
        "main_function": "save",
        "config_variable": "SECRET_KEY"
    },
    "javascript_react": {
        "path": "/workspaces/Code-Index-MCP/test_indexes/javascript_react",
        "language": "javascript",
        "file_count": 2405,
        "main_class": "Component",
        "main_function": "render",
        "config_variable": "PropTypes"
    },
    "rust_tokio": {
        "path": "/workspaces/Code-Index-MCP/test_indexes/rust_tokio",
        "language": "rust",
        "file_count": 759,
        "main_class": "Runtime",
        "main_function": "spawn",
        "config_variable": "TOKIO_WORKER_THREADS"
    }
}

class PerformanceTestOrchestrator:
    """Orchestrates the full performance testing process"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_suite = StandardizedQueryTestSuite()
        self.results = []
        self.start_time = None
        
    def generate_test_queries(self, repo_name: str, repo_info: Dict, 
                            categories: List[QueryCategory], 
                            queries_per_category: int = 3) -> List[Dict]:
        """Generate test queries for a repository"""
        queries = []
        
        # Get queries from test suite
        query_counts = {cat.value: queries_per_category for cat in categories}
        
        test_queries = self.test_suite.get_queries_for_repository(
            repo_name, 
            repo_info["language"],
            query_counts
        )
        
        # Convert to our format
        for query_text, category in test_queries:
            # Only include queries from requested categories
            if category in [cat.value for cat in categories]:
                queries.append({
                    "query": query_text,
                    "category": category,
                    "complexity": "medium",  # Default since we don't have this info
                    "expected_result_type": "location",  # Default
                    "repository": repo_name,
                    "language": repo_info["language"]
                })
        
        return queries
    
    def create_mcp_test_prompt(self, query_info: Dict) -> str:
        """Create prompt for MCP-enabled agent"""
        return f"""You are testing MCP tools for performance analysis.

Repository: {query_info['repository']} ({query_info['language']})
Query: {query_info['query']}
Category: {query_info['category']}

Instructions:
1. Use ONLY MCP tools (mcp__code-index-mcp__symbol_lookup, mcp__code-index-mcp__search_code)
2. Time your query execution
3. Count results found
4. Track tool calls made
5. Estimate tokens used

Output JSON only:
```json
{{
  "query": "{query_info['query']}",
  "mode": "mcp",
  "tools_used": ["list", "of", "tools"],
  "tool_calls": {{"tool_name": count}},
  "results_found": number,
  "execution_time_ms": milliseconds,
  "token_estimate": number,
  "success": true/false,
  "error": null_or_string
}}
```"""

    def create_native_test_prompt(self, query_info: Dict) -> str:
        """Create prompt for native-only agent"""
        return f"""You are testing native tools for performance analysis.

Repository: {query_info['repository']} ({query_info['language']})
Working Directory: {VALID_TEST_REPOS[query_info['repository']]['path']}
Query: {query_info['query']}
Category: {query_info['category']}

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
  "query": "{query_info['query']}",
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
    
    def save_test_batch(self, batch_name: str, queries: List[Dict]):
        """Save a batch of test queries"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create test configurations
        test_configs = []
        for i, query_info in enumerate(queries):
            # MCP test
            test_configs.append({
                "test_id": f"{batch_name}_{i}_mcp",
                "mode": "mcp",
                "query_info": query_info,
                "prompt": self.create_mcp_test_prompt(query_info)
            })
            
            # Native test
            test_configs.append({
                "test_id": f"{batch_name}_{i}_native",
                "mode": "native", 
                "query_info": query_info,
                "prompt": self.create_native_test_prompt(query_info)
            })
        
        # Save configurations
        config_file = self.output_dir / f"test_batch_{batch_name}_{timestamp}.json"
        with open(config_file, 'w') as f:
            json.dump({
                "batch_name": batch_name,
                "timestamp": timestamp,
                "test_count": len(test_configs),
                "tests": test_configs
            }, f, indent=2)
        
        print(f"Saved {len(test_configs)} test configurations to: {config_file}")
        return config_file
    
    def run_validation(self) -> bool:
        """Run repository validation"""
        print("\n=== Running Repository Validation ===")
        result = subprocess.run(
            [sys.executable, "scripts/validate_test_repositories.py"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
    
    def generate_all_tests(self) -> List[Path]:
        """Generate all test configurations"""
        print("\n=== Generating Test Configurations ===")
        
        test_files = []
        categories = [QueryCategory.SYMBOL, QueryCategory.CONTENT, QueryCategory.NAVIGATION]
        
        for repo_name, repo_info in VALID_TEST_REPOS.items():
            print(f"\nGenerating tests for {repo_name}...")
            queries = self.generate_test_queries(
                repo_name, repo_info, categories, queries_per_category=2
            )
            
            config_file = self.save_test_batch(repo_name, queries)
            test_files.append(config_file)
        
        return test_files
    
    def create_analysis_prompt(self, results: List[Dict]) -> str:
        """Create prompt for analyzing results"""
        return f"""Analyze these MCP vs Native performance test results:

```json
{json.dumps(results, indent=2)}
```

Provide a comprehensive analysis including:
1. Performance comparison (speed, tokens, accuracy)
2. Success rates by category and mode
3. Tool usage patterns
4. Recommendations for each use case
5. Statistical summary

Format as a detailed report with clear sections and data tables."""
    
    def generate_summary_report(self):
        """Generate summary report from all results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Collect all result files
        result_files = list(self.output_dir.glob("test_results_*.json"))
        all_results = []
        
        for result_file in result_files:
            with open(result_file) as f:
                data = json.load(f)
                all_results.extend(data.get("results", []))
        
        # Calculate statistics
        stats = {
            "total_tests": len(all_results),
            "by_mode": {
                "mcp": len([r for r in all_results if r.get("mode") == "mcp"]),
                "native": len([r for r in all_results if r.get("mode") == "native"])
            },
            "success_rates": {
                "mcp": sum(1 for r in all_results if r.get("mode") == "mcp" and r.get("success", False)) / max(1, sum(1 for r in all_results if r.get("mode") == "mcp")),
                "native": sum(1 for r in all_results if r.get("mode") == "native" and r.get("success", False)) / max(1, sum(1 for r in all_results if r.get("mode") == "native"))
            },
            "avg_execution_time_ms": {
                "mcp": sum(r.get("execution_time_ms", 0) for r in all_results if r.get("mode") == "mcp") / max(1, sum(1 for r in all_results if r.get("mode") == "mcp")),
                "native": sum(r.get("execution_time_ms", 0) for r in all_results if r.get("mode") == "native") / max(1, sum(1 for r in all_results if r.get("mode") == "native"))
            },
            "avg_tokens": {
                "mcp": sum(r.get("token_estimate", 0) for r in all_results if r.get("mode") == "mcp") / max(1, sum(1 for r in all_results if r.get("mode") == "mcp")),
                "native": sum(r.get("token_estimate", 0) for r in all_results if r.get("mode") == "native") / max(1, sum(1 for r in all_results if r.get("mode") == "native"))
            }
        }
        
        # Save summary
        summary_file = self.output_dir / f"performance_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "statistics": stats,
                "test_files": [str(f) for f in result_files],
                "repositories_tested": list(VALID_TEST_REPOS.keys())
            }, f, indent=2)
        
        print(f"\nSummary saved to: {summary_file}")
        print(f"\nTest Statistics:")
        print(f"  Total tests: {stats['total_tests']}")
        print(f"  MCP success rate: {stats['success_rates']['mcp']:.1%}")
        print(f"  Native success rate: {stats['success_rates']['native']:.1%}")
        print(f"  MCP avg time: {stats['avg_execution_time_ms']['mcp']:.0f}ms")
        print(f"  Native avg time: {stats['avg_execution_time_ms']['native']:.0f}ms")
        
        return summary_file
    
    def run_full_test(self):
        """Run the complete test orchestration"""
        self.start_time = time.time()
        
        print("=== MCP vs Native Performance Test Orchestrator ===")
        print(f"Output directory: {self.output_dir}")
        
        # Step 1: Validate repositories
        # if not self.run_validation():
        #     print("\n❌ Repository validation failed. Please fix issues before continuing.")
        #     return False
        
        # Step 2: Generate test configurations
        test_files = self.generate_all_tests()
        print(f"\n✅ Generated {len(test_files)} test batch files")
        
        # Step 3: Display test execution instructions
        print("\n=== Test Execution Instructions ===")
        print("\n1. For each test batch file, run the tests using the Task tool:")
        print("   - Copy each prompt from the test configuration")
        print("   - Use the Task tool to execute it")
        print("   - Collect the JSON output")
        
        print("\n2. Save results to files named:")
        for i, test_file in enumerate(test_files):
            result_file = test_file.name.replace("test_batch_", "test_results_")
            print(f"   - {result_file}")
        
        print("\n3. After collecting all results, run:")
        print(f"   python {__file__} --analyze")
        
        # Save instructions
        instructions_file = self.output_dir / "test_execution_instructions.txt"
        with open(instructions_file, 'w') as f:
            f.write("MCP vs Native Performance Test Instructions\n")
            f.write("==========================================\n\n")
            for test_file in test_files:
                f.write(f"Test batch: {test_file.name}\n")
                f.write(f"Execute each test prompt using the Task tool\n")
                f.write(f"Save results to: {test_file.name.replace('test_batch_', 'test_results_')}\n\n")
        
        print(f"\nInstructions saved to: {instructions_file}")
        
        elapsed = time.time() - self.start_time
        print(f"\nTest generation completed in {elapsed:.1f} seconds")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='MCP vs Native Performance Test Orchestrator')
    parser.add_argument('--output', type=Path, 
                       default=Path('/workspaces/Code-Index-MCP/test_results/performance_tests'),
                       help='Output directory for test results')
    parser.add_argument('--analyze', action='store_true',
                       help='Analyze existing results instead of generating new tests')
    
    args = parser.parse_args()
    
    orchestrator = PerformanceTestOrchestrator(args.output)
    
    if args.analyze:
        print("=== Analyzing Test Results ===")
        summary_file = orchestrator.generate_summary_report()
        print(f"\n✅ Analysis complete!")
    else:
        success = orchestrator.run_full_test()
        if success:
            print("\n✅ Test orchestration complete!")
        else:
            print("\n❌ Test orchestration failed")
            sys.exit(1)

if __name__ == "__main__":
    main()