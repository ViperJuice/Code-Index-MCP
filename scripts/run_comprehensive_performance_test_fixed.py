#!/usr/bin/env python3
"""
Comprehensive Performance Test Orchestrator for MCP vs Native Retrieval
WITH FIXED PATHS for native source code access

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
from mcp_server.core.path_utils import PathUtils

# Import test suite components
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.standardized_query_test_suite import StandardizedQueryTestSuite, QueryCategory

# Test repositories with CORRECTED paths for native tool access
VALID_TEST_REPOS = {
    "go_gin": {
        "path": "PathUtils.get_workspace_root()/test_repos/modern/go/gin",
        "language": "go",
        "file_count": 93,
        "main_class": "Engine",
        "main_function": "New",
        "config_variable": "defaultTrustedProxies"
    },
    "python_django": {
        "path": "PathUtils.get_workspace_root()/test_repos/web/python/django", 
        "language": "python",
        "file_count": 5497,
        "main_class": "Model",
        "main_function": "save",
        "config_variable": "SECRET_KEY"
    },
    "javascript_react": {
        "path": "PathUtils.get_workspace_root()/test_repos/web/javascript/react",
        "language": "javascript",
        "file_count": 2405,
        "main_class": "Component",
        "main_function": "render",
        "config_variable": "PropTypes"
    },
    "rust_tokio": {
        "path": "PathUtils.get_workspace_root()/test_repos/systems/rust/tokio",
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
        config_file = self.output_dir / f"test_batch_{batch_name}_{timestamp}_fixed.json"
        with open(config_file, 'w') as f:
            json.dump({
                "batch_name": batch_name,
                "timestamp": timestamp,
                "test_count": len(test_configs),
                "tests": test_configs
            }, f, indent=2)
        
        print(f"Saved {len(test_configs)} test configurations to: {config_file}")
        return config_file
        
    def validate_repositories(self):
        """Validate that test repositories exist and have content"""
        valid_repos = {}
        
        for repo_name, repo_info in VALID_TEST_REPOS.items():
            repo_path = Path(repo_info["path"])
            
            if not repo_path.exists():
                print(f"❌ {repo_name}: Directory not found at {repo_path}")
                continue
                
            # Count source files
            file_patterns = {
                "go": "*.go",
                "python": "*.py", 
                "javascript": "*.js",
                "rust": "*.rs"
            }
            
            pattern = file_patterns.get(repo_info["language"], "*")
            files = list(repo_path.rglob(pattern))
            
            if len(files) > 0:
                print(f"✅ {repo_name}: Found {len(files)} {repo_info['language']} files")
                valid_repos[repo_name] = repo_info
            else:
                print(f"❌ {repo_name}: No {repo_info['language']} files found")
                
        return valid_repos
        
    def run(self, repositories: List[str] = None, categories: List[str] = None,
            queries_per_category: int = 2, validate_only: bool = False):
        """Run the performance test orchestration"""
        
        print("🚀 MCP vs Native Performance Test Orchestrator (FIXED PATHS)")
        print("=" * 70)
        
        # Validate repositories
        print("\n📁 Validating Test Repositories...")
        valid_repos = self.validate_repositories()
        
        if not valid_repos:
            print("\n❌ No valid repositories found!")
            return
            
        if validate_only:
            print("\n✅ Validation complete!")
            return
            
        # Filter repositories if specified
        if repositories:
            valid_repos = {k: v for k, v in valid_repos.items() if k in repositories}
            
        # Convert category strings to enums
        if categories:
            category_enums = [QueryCategory(cat) for cat in categories]
        else:
            category_enums = list(QueryCategory)
            
        # Generate test batches
        print(f"\n🧪 Generating Test Configurations...")
        print(f"   Repositories: {list(valid_repos.keys())}")
        print(f"   Categories: {[c.value for c in category_enums]}")
        print(f"   Queries per category: {queries_per_category}")
        
        for repo_name, repo_info in valid_repos.items():
            print(f"\n📝 Processing {repo_name}...")
            
            # Generate queries
            queries = self.generate_test_queries(
                repo_name, repo_info, category_enums, queries_per_category
            )
            
            if queries:
                # Save test batch
                config_file = self.save_test_batch(repo_name, queries)
            else:
                print(f"   ⚠️  No queries generated for {repo_name}")
                
        print("\n✅ Test generation complete!")
        print("\n📋 Next Steps:")
        print("1. Execute tests using: python scripts/execute_performance_tests.py <batch_file>")
        print("2. Monitor progress: python scripts/test_progress_dashboard.py")
        print("3. Analyze results: python scripts/run_comprehensive_performance_test_fixed.py --analyze")
        
    def analyze_results(self, results_dir: Path = None):
        """Analyze collected test results"""
        if results_dir is None:
            results_dir = self.output_dir / "results"
            
        print("📊 Analyzing Test Results...")
        print("=" * 70)
        
        # Load all results
        all_results = []
        for result_file in results_dir.glob("result_*.json"):
            with open(result_file, 'r') as f:
                all_results.append(json.load(f))
                
        if not all_results:
            print("❌ No results found!")
            return
            
        print(f"Found {len(all_results)} test results")
        
        # Group by repository and mode
        by_repo_mode = {}
        for result in all_results:
            repo = result.get('batch_name', 'unknown')
            mode = result.get('mode', 'unknown')
            key = f"{repo}_{mode}"
            
            if key not in by_repo_mode:
                by_repo_mode[key] = []
            by_repo_mode[key].append(result)
            
        # Generate analysis
        print("\n🔍 Performance Analysis by Repository:\n")
        
        for repo_name in VALID_TEST_REPOS.keys():
            mcp_key = f"{repo_name}_mcp"
            native_key = f"{repo_name}_native"
            
            mcp_results = by_repo_mode.get(mcp_key, [])
            native_results = by_repo_mode.get(native_key, [])
            
            if not mcp_results and not native_results:
                continue
                
            print(f"\n{repo_name.upper()}")
            print("-" * 50)
            
            # MCP Stats
            if mcp_results:
                mcp_times = [r['execution_time_ms'] for r in mcp_results if 'execution_time_ms' in r]
                mcp_tokens = [r['token_estimate'] for r in mcp_results if 'token_estimate' in r]
                mcp_success = sum(1 for r in mcp_results if r.get('success', False))
                
                print(f"\n  MCP Mode ({len(mcp_results)} tests):")
                if mcp_times:
                    print(f"    Average time: {sum(mcp_times)/len(mcp_times):.0f}ms")
                if mcp_tokens:
                    print(f"    Average tokens: {sum(mcp_tokens)/len(mcp_tokens):.0f}")
                print(f"    Success rate: {mcp_success}/{len(mcp_results)} ({mcp_success/len(mcp_results)*100:.0f}%)")
                
            # Native Stats
            if native_results:
                native_times = [r['execution_time_ms'] for r in native_results if 'execution_time_ms' in r]
                native_tokens = [r['token_estimate'] for r in native_results if 'token_estimate' in r]
                native_success = sum(1 for r in native_results if r.get('success', False))
                
                print(f"\n  Native Mode ({len(native_results)} tests):")
                if native_times:
                    print(f"    Average time: {sum(native_times)/len(native_times):.0f}ms")
                if native_tokens:
                    print(f"    Average tokens: {sum(native_tokens)/len(native_tokens):.0f}")
                print(f"    Success rate: {native_success}/{len(native_results)} ({native_success/len(native_results)*100:.0f}%)")
                
            # Comparison
            if mcp_times and native_times:
                avg_mcp_time = sum(mcp_times)/len(mcp_times)
                avg_native_time = sum(native_times)/len(native_times)
                
                print(f"\n  Speed Comparison:")
                if avg_mcp_time < avg_native_time:
                    print(f"    MCP is {avg_native_time/avg_mcp_time:.1f}x faster")
                else:
                    print(f"    Native is {avg_mcp_time/avg_native_time:.1f}x faster")
                    
        # Overall summary
        print("\n\n🏆 OVERALL SUMMARY")
        print("=" * 70)
        
        all_mcp = [r for r in all_results if r.get('mode') == 'mcp']
        all_native = [r for r in all_results if r.get('mode') == 'native']
        
        if all_mcp:
            avg_mcp_time = sum(r.get('execution_time_ms', 0) for r in all_mcp) / len(all_mcp)
            avg_mcp_tokens = sum(r.get('token_estimate', 0) for r in all_mcp) / len(all_mcp)
            mcp_success_rate = sum(1 for r in all_mcp if r.get('success', False)) / len(all_mcp) * 100
            
            print(f"\nMCP Performance (n={len(all_mcp)}):")
            print(f"  Average time: {avg_mcp_time:.0f}ms")
            print(f"  Average tokens: {avg_mcp_tokens:.0f}")
            print(f"  Success rate: {mcp_success_rate:.0f}%")
            
        if all_native:
            avg_native_time = sum(r.get('execution_time_ms', 0) for r in all_native) / len(all_native)
            avg_native_tokens = sum(r.get('token_estimate', 0) for r in all_native) / len(all_native)
            native_success_rate = sum(1 for r in all_native if r.get('success', False)) / len(all_native) * 100
            
            print(f"\nNative Performance (n={len(all_native)}):")
            print(f"  Average time: {avg_native_time:.0f}ms")
            print(f"  Average tokens: {avg_native_tokens:.0f}")
            print(f"  Success rate: {native_success_rate:.0f}%")
            
        if all_mcp and all_native:
            print(f"\n📈 Key Findings:")
            if avg_mcp_time < avg_native_time:
                print(f"  • MCP is {avg_native_time/avg_mcp_time:.1f}x faster on average")
            else:
                print(f"  • Native is {avg_mcp_time/avg_native_time:.1f}x faster on average")
                
            if avg_mcp_tokens > avg_native_tokens:
                print(f"  • Native uses {(1-avg_native_tokens/avg_mcp_tokens)*100:.0f}% fewer tokens")
            else:
                print(f"  • MCP uses {(1-avg_mcp_tokens/avg_native_tokens)*100:.0f}% fewer tokens")
                
            print(f"  • MCP success rate: {mcp_success_rate:.0f}%")
            print(f"  • Native success rate: {native_success_rate:.0f}%")
            
        # Save summary
        summary_file = self.output_dir / f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "mcp_tests": len(all_mcp),
            "native_tests": len(all_native),
            "repositories": list(VALID_TEST_REPOS.keys()),
            "mcp_metrics": {
                "avg_time_ms": avg_mcp_time if all_mcp else 0,
                "avg_tokens": avg_mcp_tokens if all_mcp else 0,
                "success_rate": mcp_success_rate if all_mcp else 0
            },
            "native_metrics": {
                "avg_time_ms": avg_native_time if all_native else 0,
                "avg_tokens": avg_native_tokens if all_native else 0,
                "success_rate": native_success_rate if all_native else 0
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
            
        print(f"\n💾 Analysis saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description='MCP vs Native Performance Test Orchestrator')
    parser.add_argument('--analyze', action='store_true', 
                       help='Analyze existing results instead of generating tests')
    parser.add_argument('--validate', action='store_true',
                       help='Only validate repositories')
    parser.add_argument('--repos', nargs='+', choices=list(VALID_TEST_REPOS.keys()),
                       help='Specific repositories to test')
    parser.add_argument('--categories', nargs='+', 
                       choices=[c.value for c in QueryCategory],
                       help='Specific query categories to test')
    parser.add_argument('--queries-per-category', type=int, default=2,
                       help='Number of queries per category (default: 2)')
    parser.add_argument('--output-dir', type=Path, 
                       default=Path('test_results/performance_tests'),
                       help='Output directory for test configurations')
    
    args = parser.parse_args()
    
    orchestrator = PerformanceTestOrchestrator(args.output_dir)
    
    if args.analyze:
        orchestrator.analyze_results()
    else:
        orchestrator.run(
            repositories=args.repos,
            categories=args.categories,
            queries_per_category=args.queries_per_category,
            validate_only=args.validate
        )


if __name__ == "__main__":
    main()