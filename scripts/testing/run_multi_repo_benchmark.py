#!/usr/bin/env python3
"""
Run comprehensive benchmarks comparing grep vs MCP across all fetched repositories.

This script performs real-world searches and measures:
- Token usage (input and output)
- Search time
- Result quality
- Cost implications
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import random

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch
from mcp_server.utils.token_counter import TokenCounter, quick_estimate


# Model pricing (June 2025)
MODEL_PRICING = {
    "Claude 4 Opus": {"input": 15.00, "output": 75.00},
    "GPT-4.1": {"input": 2.00, "output": 8.00},
    "DeepSeek-V3": {"input": 0.27, "output": 1.10},
}


class MultiRepoBenchmark:
    """Benchmark grep vs MCP across multiple repositories."""
    
    def __init__(self):
        self.repos_dir = Path("test_repos")
        self.index_dir = Path("test_indexes")
        self.results_file = Path("test_results/multi_repo_benchmark.json")
        self.results = []
        self.token_counter = TokenCounter()
        
    def load_repository_info(self) -> List[Dict]:
        """Load repository information."""
        stats_file = Path("test_results/repository_stats.json")
        if not stats_file.exists():
            print("ERROR: Repository stats not found. Run fetch_diverse_repos.py first!")
            sys.exit(1)
            
        with open(stats_file) as f:
            data = json.load(f)
        return data["repositories"]
        
    def get_language_specific_queries(self, language: str) -> List[Tuple[str, str]]:
        """Get queries appropriate for each language."""
        # Common queries that work across languages
        common = [
            ("find_main_function", "main function entry point"),
            ("find_tests", "test"),
            ("find_errors", "error handling exception"),
            ("find_config", "configuration settings"),
        ]
        
        # Language-specific queries
        specific = {
            "python": [
                ("find_class_init", "__init__ method"),
                ("find_decorators", "@property @staticmethod"),
                ("find_imports", "import from"),
            ],
            "javascript": [
                ("find_async", "async function await"),
                ("find_exports", "export default module.exports"),
                ("find_react", "React Component useState"),
            ],
            "go": [
                ("find_goroutines", "go func goroutine"),
                ("find_interfaces", "interface{} type interface"),
                ("find_channels", "chan channel"),
            ],
            "rust": [
                ("find_traits", "trait impl for"),
                ("find_unsafe", "unsafe fn"),
                ("find_lifetimes", "lifetime 'a &'a"),
            ],
            "java": [
                ("find_annotations", "@Override @Autowired"),
                ("find_generics", "List<T> Map<K,V>"),
                ("find_spring", "Spring Bean Component"),
            ],
            "c": [
                ("find_malloc", "malloc free memory"),
                ("find_pointers", "pointer * ->"),
                ("find_structs", "struct typedef"),
            ],
            "cpp": [
                ("find_templates", "template<typename T>"),
                ("find_namespaces", "namespace std"),
                ("find_smart_pointers", "unique_ptr shared_ptr"),
            ],
        }
        
        queries = common.copy()
        if language in specific:
            queries.extend(specific[language])
        return queries
        
    def run_grep_search(self, repo_path: Path, query: str) -> Dict:
        """Run grep search and measure tokens."""
        start_time = time.time()
        
        # Split query into terms for grep
        terms = query.split()
        grep_pattern = "|".join(terms)
        
        # Run grep to find files
        cmd = ["grep", "-r", "-l", "-E", grep_pattern, str(repo_path)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            grep_time = time.time() - start_time
            
            if result.returncode != 0 or not result.stdout:
                return {
                    "files_found": 0,
                    "input_tokens": self.token_counter.count_tokens(f"grep -r -l -E '{grep_pattern}' {repo_path}"),
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "time_seconds": grep_time,
                    "error": "No matches found"
                }
                
            # Parse file list
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            
            # Calculate tokens for grep command
            input_tokens = self.token_counter.count_tokens(f"grep -r -l -E '{grep_pattern}' {repo_path}")
            
            # Read all files (this is what you'd need to do for LLM)
            total_content = ""
            files_read = 0
            
            for file_path in files[:20]:  # Limit to 20 files to avoid huge token counts
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        total_content += f"\n\n=== {file_path} ===\n{content}"
                        files_read += 1
                except:
                    pass
                    
            output_tokens = self.token_counter.count_tokens(total_content)
            
            return {
                "files_found": len(files),
                "files_read": files_read,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "time_seconds": time.time() - start_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                "files_found": 0,
                "input_tokens": self.token_counter.count_tokens(f"grep -r -l -E '{grep_pattern}' {repo_path}"),
                "output_tokens": 0,
                "total_tokens": 0,
                "time_seconds": 30.0,
                "error": "Timeout"
            }
            
    def run_mcp_search(self, index_path: Path, query: str) -> Dict:
        """Run MCP search and measure tokens."""
        start_time = time.time()
        
        db_path = index_path / "bm25_index.db"
        if not db_path.exists():
            return {
                "results_found": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "time_seconds": 0,
                "error": "No index found"
            }
            
        try:
            # Initialize search components
            storage = SQLiteStore(str(db_path))
            bm25_indexer = BM25Indexer(storage)
            
            # Count input tokens (just the query)
            input_tokens = self.token_counter.count_tokens(f"search: {query}")
            
            # Perform search
            results = bm25_indexer.search(query, limit=20)
            
            # Format results as they would be sent to LLM
            output_content = ""
            for i, result in enumerate(results, 1):
                output_content += f"\n{i}. {result.get('file_path', 'unknown')}\n"
                output_content += f"   Score: {result.get('score', 0):.3f}\n"
                output_content += f"   Snippet: {result.get('snippet', '')[:200]}...\n"
                
            output_tokens = self.token_counter.count_tokens(output_content)
            
            return {
                "results_found": len(results),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "time_seconds": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "results_found": 0,
                "input_tokens": self.token_counter.count_tokens(f"search: {query}"),
                "output_tokens": 0,
                "total_tokens": 0,
                "time_seconds": time.time() - start_time,
                "error": str(e)
            }
            
    def benchmark_repository(self, repo_info: Dict) -> Dict:
        """Benchmark a single repository."""
        repo_name = repo_info["repository"]
        language = repo_info["language"]
        repo_path = Path(repo_info["path"])
        
        print(f"\nBenchmarking {repo_name} ({language})...")
        
        # Get appropriate queries for this language
        queries = self.get_language_specific_queries(language)
        
        # Prepare index path
        safe_name = repo_name.replace("/", "_")
        index_path = self.index_dir / safe_name
        
        results = {
            "repository": repo_name,
            "language": language,
            "repo_metrics": repo_info["metrics"],
            "queries": []
        }
        
        # Run each query
        for query_name, query_text in queries[:5]:  # Limit to 5 queries per repo
            print(f"  Query: {query_name} - '{query_text}'")
            
            # Run grep search
            grep_result = self.run_grep_search(repo_path, query_text)
            
            # Run MCP search
            mcp_result = self.run_mcp_search(index_path, query_text)
            
            # Calculate token reduction
            if grep_result["total_tokens"] > 0:
                reduction = (1 - mcp_result["total_tokens"] / grep_result["total_tokens"]) * 100
            else:
                reduction = 0
                
            # Calculate costs
            costs = {}
            for model, pricing in MODEL_PRICING.items():
                grep_cost = (
                    (grep_result["input_tokens"] / 1_000_000) * pricing["input"] +
                    (grep_result["output_tokens"] / 1_000_000) * pricing["output"]
                )
                mcp_cost = (
                    (mcp_result["input_tokens"] / 1_000_000) * pricing["input"] +
                    (mcp_result["output_tokens"] / 1_000_000) * pricing["output"]
                )
                costs[model] = {
                    "grep_cost": grep_cost,
                    "mcp_cost": mcp_cost,
                    "savings": grep_cost - mcp_cost,
                    "savings_percent": ((grep_cost - mcp_cost) / grep_cost * 100) if grep_cost > 0 else 0
                }
                
            results["queries"].append({
                "query_name": query_name,
                "query_text": query_text,
                "grep": grep_result,
                "mcp": mcp_result,
                "token_reduction_percent": reduction,
                "costs": costs
            })
            
        return results
        
    def run_all_benchmarks(self):
        """Run benchmarks on all repositories."""
        # Load repository information
        repos = self.load_repository_info()
        
        print(f"Running benchmarks on {len(repos)} repositories...")
        
        # Run benchmarks
        for i, repo_info in enumerate(repos, 1):
            print(f"\n[{i}/{len(repos)}]", end="")
            
            try:
                result = self.benchmark_repository(repo_info)
                self.results.append(result)
                
                # Save incrementally
                self._save_results()
                
            except Exception as e:
                print(f"\nERROR benchmarking {repo_info['repository']}: {e}")
                self.results.append({
                    "repository": repo_info["repository"],
                    "language": repo_info["language"],
                    "error": str(e)
                })
                
        # Print summary
        self._print_summary()
        
    def _save_results(self):
        """Save current results to file."""
        self.results_file.parent.mkdir(exist_ok=True)
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        
        with open(self.results_file, 'w') as f:
            json.dump({
                "benchmark_date": datetime.now().isoformat(),
                "summary": summary,
                "repositories": self.results
            }, f, indent=2)
            
    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics across all repositories."""
        if not self.results:
            return {}
            
        # Aggregate statistics
        total_queries = 0
        total_grep_tokens = 0
        total_mcp_tokens = 0
        reductions = []
        costs_by_model = {model: {"grep": 0, "mcp": 0} for model in MODEL_PRICING}
        
        by_language = {}
        
        for repo_result in self.results:
            if "error" in repo_result:
                continue
                
            language = repo_result["language"]
            if language not in by_language:
                by_language[language] = {
                    "repo_count": 0,
                    "query_count": 0,
                    "avg_reduction": 0,
                    "total_grep_tokens": 0,
                    "total_mcp_tokens": 0
                }
                
            by_language[language]["repo_count"] += 1
            
            for query_result in repo_result.get("queries", []):
                total_queries += 1
                by_language[language]["query_count"] += 1
                
                grep_tokens = query_result["grep"]["total_tokens"]
                mcp_tokens = query_result["mcp"]["total_tokens"]
                
                total_grep_tokens += grep_tokens
                total_mcp_tokens += mcp_tokens
                
                by_language[language]["total_grep_tokens"] += grep_tokens
                by_language[language]["total_mcp_tokens"] += mcp_tokens
                
                if query_result["token_reduction_percent"] > 0:
                    reductions.append(query_result["token_reduction_percent"])
                    
                # Aggregate costs
                for model, cost_data in query_result["costs"].items():
                    costs_by_model[model]["grep"] += cost_data["grep_cost"]
                    costs_by_model[model]["mcp"] += cost_data["mcp_cost"]
                    
        # Calculate averages
        avg_reduction = sum(reductions) / len(reductions) if reductions else 0
        
        for lang_data in by_language.values():
            if lang_data["total_grep_tokens"] > 0:
                lang_data["avg_reduction"] = (
                    1 - lang_data["total_mcp_tokens"] / lang_data["total_grep_tokens"]
                ) * 100
                
        return {
            "total_repositories": len(self.results),
            "total_queries": total_queries,
            "total_grep_tokens": total_grep_tokens,
            "total_mcp_tokens": total_mcp_tokens,
            "average_token_reduction": avg_reduction,
            "total_costs": costs_by_model,
            "by_language": by_language
        }
        
    def _print_summary(self):
        """Print benchmark summary."""
        summary = self._calculate_summary()
        
        print(f"\n{'='*60}")
        print(f"BENCHMARK COMPLETE")
        print(f"{'='*60}")
        print(f"Total repositories: {summary['total_repositories']}")
        print(f"Total queries: {summary['total_queries']}")
        print(f"Average token reduction: {summary['average_token_reduction']:.1f}%")
        
        print(f"\nToken Usage:")
        print(f"  Grep total: {summary['total_grep_tokens']:,} tokens")
        print(f"  MCP total: {summary['total_mcp_tokens']:,} tokens")
        print(f"  Reduction: {(1 - summary['total_mcp_tokens']/summary['total_grep_tokens'])*100:.1f}%")
        
        print(f"\nCost Analysis (for all {summary['total_queries']} queries):")
        for model, costs in summary["total_costs"].items():
            print(f"  {model}:")
            print(f"    Grep: ${costs['grep']:.2f}")
            print(f"    MCP: ${costs['mcp']:.2f}")
            print(f"    Savings: ${costs['grep'] - costs['mcp']:.2f}")
            
        print(f"\nBy Language:")
        for lang, data in sorted(summary["by_language"].items()):
            print(f"  {lang}:")
            print(f"    Repositories: {data['repo_count']}")
            print(f"    Queries: {data['query_count']}")
            print(f"    Avg reduction: {data['avg_reduction']:.1f}%")
            
        print(f"\nResults saved to: {self.results_file}")


def main():
    """Main entry point."""
    benchmark = MultiRepoBenchmark()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        # Just show summary of existing results
        if benchmark.results_file.exists():
            with open(benchmark.results_file) as f:
                data = json.load(f)
            print(json.dumps(data["summary"], indent=2))
        else:
            print("No benchmark results found. Run without --summary to start benchmarking.")
    else:
        benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()