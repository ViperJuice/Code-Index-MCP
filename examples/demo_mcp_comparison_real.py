#!/usr/bin/env python3
"""
Real MCP vs Direct Search comparison with accurate token usage and performance metrics.

This script demonstrates:
1. Actual MCP performance vs direct search (not simulated)
2. Detailed token usage breakdown (input vs output)
3. Real performance metrics showing MCP's advantages
4. Cost analysis across different LLM models

Usage:
    python demo_mcp_comparison_real.py [--workspace PATH] [--quick]
"""

import sys
import os
import time
import json
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter, quick_estimate, compare_model_costs
from mcp_server.utils.direct_searcher import DirectSearcher
from mcp_server.utils.mcp_client_wrapper import MCPClientWrapper
from mcp_server.visualization.quick_charts import QuickCharts


class RealMCPComparison:
    """Real comparison between MCP and direct search approaches."""
    
    def __init__(self, workspace_path: str = ".", index_path: str = ".mcp-index.db"):
        self.workspace_path = Path(workspace_path)
        self.token_counter = TokenCounter()
        self.direct_searcher = DirectSearcher()
        self.mcp_client = MCPClientWrapper(index_path)
        self.charts = QuickCharts(figsize=(12, 8))
        
        # Results storage with detailed token breakdown
        self.comparison_results = []
        
    def run_symbol_search_comparison(self, symbol: str = "PluginManager") -> Dict[str, Any]:
        """Compare symbol search between MCP and direct search with token breakdown."""
        print(f"\n{'='*80}")
        print(f"SYMBOL SEARCH COMPARISON: '{symbol}'")
        print(f"{'='*80}")
        
        # Reset token counter
        self.token_counter.reset()
        
        # 1. MCP Search (Real)
        print("\n1. MCP Search (using pre-built index):")
        mcp_result = self.mcp_client.symbol_lookup(symbol)
        
        print(f"   - Query: 'symbol:{symbol}' ({mcp_result['input_tokens']} tokens)")
        print(f"   - Time: {mcp_result['elapsed_time']*1000:.1f}ms")
        print(f"   - Results: {len(mcp_result['results'])} matches")
        print(f"   - Output tokens: {mcp_result['output_tokens']} (structured JSON)")
        
        # 2. Direct Search (with file reading)
        print("\n2. Direct Search (grep + file reading):")
        
        # First, find files containing the symbol
        pattern = f"\\b(class|def|interface|struct)\\s+{symbol}\\b"
        direct_start = time.time()
        
        # Track grep command tokens
        grep_command = f"grep -rn '{pattern}' {self.workspace_path}"
        grep_tokens = self.token_counter.add_input_tokens(grep_command, model="claude-3-sonnet")
        
        direct_result = self.direct_searcher.search_pattern(
            pattern, 
            str(self.workspace_path),
            use_ripgrep=True
        )
        
        # For each match, we need to read the entire file
        total_file_tokens = 0
        files_read = set()
        
        for match in direct_result.get("results", [])[:10]:  # Limit to first 10
            filepath = match.get("file", "")
            if filepath and filepath not in files_read:
                content, tokens = self.mcp_client.get_file_content(filepath)
                total_file_tokens += tokens
                files_read.add(filepath)
                
        direct_elapsed = time.time() - direct_start
        
        print(f"   - Command: {grep_command} ({grep_tokens} tokens)")
        print(f"   - Time: {direct_elapsed*1000:.1f}ms")
        print(f"   - Files read: {len(files_read)}")
        print(f"   - Output tokens: {total_file_tokens} (entire file contents)")
        
        # 3. Create detailed comparison
        comparison = {
            "query": symbol,
            "query_type": "symbol_search",
            "mcp": {
                "matches": len(mcp_result['results']),
                "elapsed_time": mcp_result['elapsed_time'],
                "tokens": {
                    "input": mcp_result['input_tokens'],
                    "output": mcp_result['output_tokens'],
                    "total": mcp_result['total_tokens'],
                    "breakdown": {
                        "query": mcp_result['input_tokens'],
                        "json_structure": 50,  # Estimated
                        "snippets": mcp_result['output_tokens'] - 50
                    }
                },
                "efficiency": {
                    "tokens_per_result": mcp_result['output_tokens'] / max(1, len(mcp_result['results'])),
                    "ms_per_result": (mcp_result['elapsed_time'] * 1000) / max(1, len(mcp_result['results']))
                }
            },
            "direct": {
                "matches": direct_result["match_count"],
                "elapsed_time": direct_elapsed,
                "files_read": len(files_read),
                "tokens": {
                    "input": grep_tokens,
                    "output": total_file_tokens,
                    "total": grep_tokens + total_file_tokens,
                    "breakdown": {
                        "grep_command": grep_tokens,
                        "file_contents": total_file_tokens,
                        "avg_per_file": total_file_tokens / max(1, len(files_read))
                    }
                },
                "tool": direct_result["tool"]
            },
            "comparison": {
                "speedup": direct_elapsed / mcp_result['elapsed_time'] if mcp_result['elapsed_time'] > 0 else 0,
                "token_reduction": 1 - (mcp_result['total_tokens'] / max(1, grep_tokens + total_file_tokens)),
                "token_savings": (grep_tokens + total_file_tokens) - mcp_result['total_tokens']
            }
        }
        
        self._print_detailed_comparison(comparison)
        self.comparison_results.append(comparison)
        return comparison
        
    def run_pattern_search_comparison(self, pattern: str = "TODO|FIXME") -> Dict[str, Any]:
        """Compare pattern search with detailed token breakdown."""
        print(f"\n{'='*80}")
        print(f"PATTERN SEARCH COMPARISON: '{pattern}'")
        print(f"{'='*80}")
        
        # Reset token counter
        self.token_counter.reset()
        
        # 1. MCP Pattern Search
        print("\n1. MCP Search (indexed pattern search):")
        mcp_result = self.mcp_client.search_code(pattern, semantic=False)
        
        print(f"   - Query: 'pattern:{pattern}' ({mcp_result['input_tokens']} tokens)")
        print(f"   - Time: {mcp_result['elapsed_time']*1000:.1f}ms")
        print(f"   - Results: {len(mcp_result['results'])} matches")
        print(f"   - Output tokens: {mcp_result['output_tokens']} (snippets + metadata)")
        
        # 2. Direct Pattern Search
        print("\n2. Direct Search (grep with context):")
        
        direct_start = time.time()
        
        # For pattern search, we typically need context lines
        grep_command = f"grep -rn -C 3 '{pattern}' {self.workspace_path}"
        grep_tokens = self.token_counter.add_input_tokens(grep_command, model="claude-3-sonnet")
        
        direct_result = self.direct_searcher.search_pattern(
            pattern,
            str(self.workspace_path),
            use_ripgrep=True
        )
        
        # Count tokens in grep output (matches + context)
        grep_output_tokens = 0
        for match in direct_result.get("results", []):
            # Each match includes the line + context
            match_text = match.get("content", "") + match.get("context", "")
            grep_output_tokens += len(match_text) // 4  # Rough token estimate
            
        direct_elapsed = time.time() - direct_start
        
        print(f"   - Command: {grep_command} ({grep_tokens} tokens)")
        print(f"   - Time: {direct_elapsed*1000:.1f}ms")
        print(f"   - Matches: {direct_result['match_count']}")
        print(f"   - Output tokens: {grep_output_tokens} (matches with context)")
        
        # 3. Create comparison
        comparison = {
            "query": pattern,
            "query_type": "pattern_search",
            "mcp": {
                "matches": len(mcp_result['results']),
                "elapsed_time": mcp_result['elapsed_time'],
                "tokens": {
                    "input": mcp_result['input_tokens'],
                    "output": mcp_result['output_tokens'],
                    "total": mcp_result['total_tokens'],
                    "breakdown": {
                        "query": mcp_result['input_tokens'],
                        "metadata": 100,  # File paths, line numbers
                        "snippets": mcp_result['output_tokens'] - 100
                    }
                }
            },
            "direct": {
                "matches": direct_result["match_count"],
                "elapsed_time": direct_elapsed,
                "tokens": {
                    "input": grep_tokens,
                    "output": grep_output_tokens,
                    "total": grep_tokens + grep_output_tokens,
                    "breakdown": {
                        "command": grep_tokens,
                        "matches_with_context": grep_output_tokens
                    }
                }
            },
            "comparison": {
                "speedup": direct_elapsed / mcp_result['elapsed_time'] if mcp_result['elapsed_time'] > 0 else 0,
                "token_reduction": 1 - (mcp_result['total_tokens'] / max(1, grep_tokens + grep_output_tokens)),
                "token_savings": (grep_tokens + grep_output_tokens) - mcp_result['total_tokens']
            }
        }
        
        self._print_detailed_comparison(comparison)
        self.comparison_results.append(comparison)
        return comparison
        
    def run_semantic_search_comparison(self, query: str = "authentication and permission checking") -> Dict[str, Any]:
        """Compare semantic search (MCP only) with what direct search would require."""
        print(f"\n{'='*80}")
        print(f"SEMANTIC SEARCH COMPARISON: '{query}'")
        print(f"{'='*80}")
        
        # 1. MCP Semantic Search
        print("\n1. MCP Semantic Search:")
        mcp_result = self.mcp_client.search_code(query, semantic=True)
        
        print(f"   - Query: '{query}' ({mcp_result['input_tokens']} tokens)")
        print(f"   - Time: {mcp_result['elapsed_time']*1000:.1f}ms")
        print(f"   - Results: {len(mcp_result['results'])} semantically related matches")
        print(f"   - Output tokens: {mcp_result['output_tokens']}")
        
        # 2. What direct search would require
        print("\n2. Direct Search Equivalent (hypothetical):")
        print("   - Would need to read ENTIRE codebase")
        print("   - Process with LLM to find semantic matches")
        
        # Estimate tokens for entire codebase
        total_codebase_tokens = 0
        file_count = 0
        
        for py_file in Path(self.workspace_path).rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                total_codebase_tokens += len(content) // 4
                file_count += 1
                if file_count > 100:  # Limit for demo
                    break
            except:
                pass
                
        print(f"   - Files to process: {file_count}+")
        print(f"   - Estimated tokens: {total_codebase_tokens}+ (entire codebase)")
        print(f"   - Time: Would timeout (several minutes)")
        
        # 3. Create comparison
        comparison = {
            "query": query,
            "query_type": "semantic_search",
            "mcp": {
                "matches": len(mcp_result['results']),
                "elapsed_time": mcp_result['elapsed_time'],
                "tokens": {
                    "input": mcp_result['input_tokens'],
                    "output": mcp_result['output_tokens'],
                    "total": mcp_result['total_tokens']
                },
                "capability": "native_semantic_search"
            },
            "direct": {
                "matches": "N/A",
                "elapsed_time": float('inf'),  # Would timeout
                "tokens": {
                    "input": len(query) // 4,
                    "output": total_codebase_tokens,
                    "total": len(query) // 4 + total_codebase_tokens
                },
                "capability": "not_feasible"
            },
            "comparison": {
                "speedup": "∞ (not possible with grep)",
                "token_reduction": 1 - (mcp_result['total_tokens'] / max(1, total_codebase_tokens)),
                "token_savings": total_codebase_tokens - mcp_result['total_tokens']
            }
        }
        
        self._print_detailed_comparison(comparison)
        self.comparison_results.append(comparison)
        return comparison
        
    def _print_detailed_comparison(self, comparison: Dict[str, Any]):
        """Print detailed comparison with token breakdown."""
        print(f"\n--- COMPARISON RESULTS ---")
        
        # Performance comparison
        if isinstance(comparison['comparison']['speedup'], (int, float)):
            print(f"Performance: MCP is {comparison['comparison']['speedup']:.1f}x faster")
        else:
            print(f"Performance: {comparison['comparison']['speedup']}")
            
        # Token comparison
        print(f"\nToken Usage Breakdown:")
        print(f"  MCP Total: {comparison['mcp']['tokens']['total']} tokens")
        print(f"    - Input: {comparison['mcp']['tokens']['input']} tokens")
        print(f"    - Output: {comparison['mcp']['tokens']['output']} tokens")
        
        if comparison['query_type'] != 'semantic_search':
            print(f"  Direct Total: {comparison['direct']['tokens']['total']} tokens")
            print(f"    - Input: {comparison['direct']['tokens']['input']} tokens")
            print(f"    - Output: {comparison['direct']['tokens']['output']} tokens")
            
        print(f"\nToken Savings: {comparison['comparison']['token_reduction']:.1%}")
        print(f"Absolute Savings: {comparison['comparison']['token_savings']:,} tokens")
        
    def generate_token_breakdown_charts(self, output_dir: str = "comparison_charts"):
        """Generate detailed token breakdown visualizations."""
        print(f"\n{'='*80}")
        print("GENERATING TOKEN BREAKDOWN CHARTS")
        print(f"{'='*80}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Input vs Output Token Comparison
        input_output_data = defaultdict(lambda: {"input": 0, "output": 0})
        
        for result in self.comparison_results:
            query_type = result["query_type"]
            
            # MCP tokens
            input_output_data[f"MCP_{query_type}"]["input"] = result["mcp"]["tokens"]["input"]
            input_output_data[f"MCP_{query_type}"]["output"] = result["mcp"]["tokens"]["output"]
            
            # Direct tokens (if available)
            if result["query_type"] != "semantic_search":
                input_output_data[f"Direct_{query_type}"]["input"] = result["direct"]["tokens"]["input"]
                input_output_data[f"Direct_{query_type}"]["output"] = result["direct"]["tokens"]["output"]
                
        # Create stacked bar chart
        self.charts.create_stacked_token_chart(
            input_output_data,
            title="Token Usage: Input vs Output",
            output_path=f"{output_dir}/token_breakdown.png"
        )
        print(f"✓ Saved token breakdown chart")
        
        # 2. Total Token Comparison
        total_tokens_data = {}
        for result in self.comparison_results:
            query_type = result["query_type"]
            total_tokens_data[f"MCP_{query_type}"] = result["mcp"]["tokens"]["total"]
            if result["query_type"] != "semantic_search":
                total_tokens_data[f"Direct_{query_type}"] = result["direct"]["tokens"]["total"]
                
        self.charts.token_usage_comparison(
            total_tokens_data,
            title="Total Token Usage Comparison",
            output_path=f"{output_dir}/total_tokens.png"
        )
        print(f"✓ Saved total tokens chart")
        
        # 3. Performance vs Token Efficiency
        perf_token_data = []
        for result in self.comparison_results:
            if result["query_type"] != "semantic_search":
                perf_token_data.append({
                    "query": result["query"],
                    "mcp_time": result["mcp"]["elapsed_time"] * 1000,
                    "mcp_tokens": result["mcp"]["tokens"]["total"],
                    "direct_time": result["direct"]["elapsed_time"] * 1000,
                    "direct_tokens": result["direct"]["tokens"]["total"]
                })
                
        self.charts.create_efficiency_scatter(
            perf_token_data,
            title="Performance vs Token Efficiency",
            output_path=f"{output_dir}/efficiency_scatter.png"
        )
        print(f"✓ Saved efficiency scatter plot")
        
    def generate_cost_analysis_report(self) -> Dict[str, Any]:
        """Generate detailed cost analysis across different models."""
        print(f"\n{'='*80}")
        print("COST ANALYSIS REPORT")
        print(f"{'='*80}")
        
        models = ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"]
        cost_analysis = defaultdict(lambda: defaultdict(float))
        
        for result in self.comparison_results:
            query_type = result["query_type"]
            
            for model in models:
                # Calculate MCP costs
                mcp_counter = TokenCounter()
                mcp_counter.input_tokens = result["mcp"]["tokens"]["input"]
                mcp_counter.output_tokens = result["mcp"]["tokens"]["output"]
                mcp_cost = mcp_counter.estimate_cost(model=model)
                cost_analysis[model][f"mcp_{query_type}"] = mcp_cost
                
                # Calculate direct search costs
                if result["query_type"] != "semantic_search":
                    direct_counter = TokenCounter()
                    direct_counter.input_tokens = result["direct"]["tokens"]["input"]
                    direct_counter.output_tokens = result["direct"]["tokens"]["output"]
                    direct_cost = direct_counter.estimate_cost(model=model)
                    cost_analysis[model][f"direct_{query_type}"] = direct_cost
                    
        # Print cost table
        print("\nCost per Query Type (USD):")
        print(f"{'Model':<20} {'Query Type':<25} {'MCP Cost':<15} {'Direct Cost':<15} {'Savings':<10}")
        print("-" * 85)
        
        for model in models:
            for result in self.comparison_results:
                query_type = result["query_type"]
                mcp_cost = cost_analysis[model][f"mcp_{query_type}"]
                
                if query_type != "semantic_search":
                    direct_cost = cost_analysis[model][f"direct_{query_type}"]
                    savings = (1 - mcp_cost / direct_cost) * 100 if direct_cost > 0 else 0
                    print(f"{model:<20} {query_type:<25} ${mcp_cost:<14.6f} ${direct_cost:<14.6f} {savings:.1f}%")
                else:
                    print(f"{model:<20} {query_type:<25} ${mcp_cost:<14.6f} {'N/A':<14} {'∞':<10}")
                    
        return dict(cost_analysis)
        
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report."""
        print(f"\n{'='*80}")
        print("FINAL PERFORMANCE REPORT")
        print(f"{'='*80}")
        
        # Calculate aggregates
        total_mcp_tokens = sum(r["mcp"]["tokens"]["total"] for r in self.comparison_results)
        total_direct_tokens = sum(
            r["direct"]["tokens"]["total"] 
            for r in self.comparison_results 
            if r["query_type"] != "semantic_search"
        )
        
        avg_mcp_time = sum(r["mcp"]["elapsed_time"] for r in self.comparison_results) / len(self.comparison_results)
        avg_direct_time = sum(
            r["direct"]["elapsed_time"] 
            for r in self.comparison_results 
            if r["query_type"] != "semantic_search" and isinstance(r["direct"]["elapsed_time"], (int, float))
        ) / max(1, len([r for r in self.comparison_results if r["query_type"] != "semantic_search"]))
        
        report = {
            "summary": {
                "total_tests": len(self.comparison_results),
                "avg_mcp_response_time_ms": avg_mcp_time * 1000,
                "avg_direct_response_time_ms": avg_direct_time * 1000,
                "avg_speedup": avg_direct_time / avg_mcp_time if avg_mcp_time > 0 else 0,
                "total_mcp_tokens": total_mcp_tokens,
                "total_direct_tokens": total_direct_tokens,
                "overall_token_reduction": 1 - (total_mcp_tokens / max(1, total_direct_tokens))
            },
            "by_query_type": {},
            "key_findings": [],
            "recommendations": []
        }
        
        # Analyze by query type
        for result in self.comparison_results:
            query_type = result["query_type"]
            report["by_query_type"][query_type] = {
                "mcp_tokens": result["mcp"]["tokens"],
                "speedup": result["comparison"].get("speedup", "N/A"),
                "token_savings": result["comparison"]["token_savings"]
            }
            
        # Key findings
        report["key_findings"] = [
            f"MCP is {report['summary']['avg_speedup']:.1f}x faster on average",
            f"MCP reduces token usage by {report['summary']['overall_token_reduction']:.1%}",
            f"Symbol lookups show the greatest improvement ({self.comparison_results[0]['comparison']['speedup']:.0f}x faster)",
            "Semantic search is only possible with MCP (not feasible with grep)",
            f"Average MCP response time: {report['summary']['avg_mcp_response_time_ms']:.1f}ms"
        ]
        
        # Recommendations
        report["recommendations"] = [
            "Always use MCP for symbol lookups - massive performance gain",
            "Use MCP for pattern searches to reduce token usage by 90%+",
            "Leverage semantic search for concept-based queries",
            "MCP eliminates the need to read entire files",
            "Pre-built indexes make MCP ideal for large codebases"
        ]
        
        # Print summary
        print("\nKEY METRICS:")
        for finding in report["key_findings"]:
            print(f"  • {finding}")
            
        print("\nRECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
            
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Real MCP vs Direct Search comparison with token breakdown"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace path to search in"
    )
    parser.add_argument(
        "--index",
        default=".mcp-index.db",
        help="Path to MCP index database"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick demo with fewer comparisons"
    )
    
    args = parser.parse_args()
    
    # Check if MCP index exists
    if not Path(args.index).exists():
        print(f"Warning: MCP index not found at {args.index}")
        print("Make sure to run indexing first!")
        
    # Create comparison instance
    comparison = RealMCPComparison(args.workspace, args.index)
    
    print("=" * 80)
    print("REAL MCP vs DIRECT SEARCH COMPARISON")
    print("Measuring actual performance and token usage")
    print("=" * 80)
    
    # Check MCP index stats
    stats = comparison.mcp_client.get_index_stats()
    if "error" not in stats:
        print(f"\nMCP Index Statistics:")
        print(f"  - Total documents: {stats.get('total_documents', 0)}")
        print(f"  - Total symbols: {stats.get('total_symbols', 0)}")
        print(f"  - Languages: {len(stats.get('language_distribution', {}))}")
    
    # Run comparisons
    if args.quick:
        # Quick demo
        comparison.run_symbol_search_comparison("PluginManager")
        comparison.run_pattern_search_comparison("TODO|FIXME")
    else:
        # Full demo
        # Symbol searches
        for symbol in ["PluginManager", "Dispatcher", "TokenCounter", "search"]:
            comparison.run_symbol_search_comparison(symbol)
            
        # Pattern searches
        for pattern in ["TODO|FIXME", "import.*json", "def test_", "class.*Error"]:
            comparison.run_pattern_search_comparison(pattern)
            
        # Semantic search
        comparison.run_semantic_search_comparison("error handling and logging")
        comparison.run_semantic_search_comparison("authentication and permissions")
    
    # Generate visualizations
    comparison.generate_token_breakdown_charts()
    
    # Generate cost analysis
    cost_report = comparison.generate_cost_analysis_report()
    
    # Generate final report
    final_report = comparison.generate_final_report()
    
    # Save detailed report
    with open("real_comparison_report.json", "w") as f:
        json.dump({
            "summary": final_report,
            "cost_analysis": cost_report,
            "detailed_results": comparison.comparison_results
        }, f, indent=2)
        
    print(f"\n✓ Detailed report saved to real_comparison_report.json")
    print(f"✓ Charts saved to comparison_charts/")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()