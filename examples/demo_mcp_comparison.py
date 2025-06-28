#!/usr/bin/env python3
"""
Demo script showing MCP vs Direct Search comparison with token usage and performance metrics.

This script demonstrates:
1. Token usage differences between MCP and direct search
2. Performance comparisons for different query types
3. Cost analysis across different LLM models
4. Visual comparison charts

Usage:
    python demo_mcp_comparison.py [--workspace PATH] [--quick]
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter, quick_estimate, compare_model_costs
from mcp_server.utils.direct_searcher import DirectSearcher, quick_search
from mcp_server.visualization.quick_charts import QuickCharts
from tests.comparison.test_data import TestDataGenerator, QueryType


class MCPComparisonDemo:
    """Demo class for comparing MCP vs direct search approaches."""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path)
        self.token_counter = TokenCounter()
        self.direct_searcher = DirectSearcher()
        self.charts = QuickCharts(figsize=(12, 6))
        
        # Results storage
        self.comparison_results = []
        
    def run_symbol_search_comparison(self, symbol: str = "main") -> Dict[str, Any]:
        """Compare symbol search between MCP and direct search."""
        print(f"\n=== Symbol Search Comparison: '{symbol}' ===")
        
        # Direct search using ripgrep
        direct_pattern = f"\\b{symbol}\\b"
        print(f"Running ripgrep search for pattern: {direct_pattern}")
        direct_result = self.direct_searcher.search_pattern(
            direct_pattern, 
            str(self.workspace_path),
            use_ripgrep=True
        )
        
        # Simulate MCP search (in a real scenario, this would use the MCP client)
        print("Simulating MCP symbol search...")
        mcp_start = time.time()
        
        # MCP would return structured results - simulate this
        mcp_query = f"symbol:{symbol}"
        self.token_counter.add_input_tokens(mcp_query, model="claude-3-sonnet")
        
        # Simulate MCP response (structured JSON)
        mcp_response = {
            "results": [
                {
                    "symbol": symbol,
                    "file": f"src/{symbol}.py",
                    "line": 10,
                    "kind": "function",
                    "signature": f"def {symbol}():"
                }
                for _ in range(min(len(direct_result.get("results", [])), 10))
            ],
            "total_matches": len(direct_result.get("results", [])),
            "search_time_ms": 25
        }
        mcp_response_text = json.dumps(mcp_response, indent=2)
        self.token_counter.add_output_tokens(mcp_response_text, model="claude-3-sonnet")
        
        mcp_elapsed = time.time() - mcp_start
        
        # Compare results
        comparison = {
            "query": symbol,
            "query_type": "symbol_search",
            "mcp": {
                "matches": len(mcp_response["results"]),
                "elapsed_time": mcp_elapsed,
                "tokens": {
                    "input": self.token_counter.input_tokens,
                    "output": self.token_counter.output_tokens,
                    "total": self.token_counter.total_tokens
                }
            },
            "direct": {
                "matches": direct_result["match_count"],
                "elapsed_time": direct_result["elapsed_time"],
                "tool": direct_result["tool"]
            }
        }
        
        self._print_comparison(comparison)
        self.comparison_results.append(comparison)
        return comparison
        
    def run_pattern_search_comparison(self, pattern: str = "TODO|FIXME") -> Dict[str, Any]:
        """Compare pattern search between approaches."""
        print(f"\n=== Pattern Search Comparison: '{pattern}' ===")
        
        # Reset token counter for this comparison
        self.token_counter.reset()
        
        # Direct search
        print(f"Running direct search for pattern: {pattern}")
        direct_result = self.direct_searcher.search_pattern(
            pattern,
            str(self.workspace_path),
            use_ripgrep=True
        )
        
        # Simulate MCP pattern search
        print("Simulating MCP pattern search...")
        mcp_start = time.time()
        
        mcp_query = f"pattern:{pattern}"
        self.token_counter.add_input_tokens(mcp_query, model="claude-3-sonnet")
        
        # MCP would return matches with context
        mcp_response = {
            "results": [
                {
                    "file": match["file"],
                    "line": match["line"],
                    "content": match["content"],
                    "context": {
                        "before": "...",
                        "after": "..."
                    }
                }
                for match in direct_result.get("results", [])[:20]
            ],
            "total_matches": direct_result["match_count"],
            "pattern": pattern
        }
        mcp_response_text = json.dumps(mcp_response, indent=2)
        self.token_counter.add_output_tokens(mcp_response_text, model="claude-3-sonnet")
        
        mcp_elapsed = time.time() - mcp_start
        
        # Compare results
        comparison = {
            "query": pattern,
            "query_type": "pattern_search",
            "mcp": {
                "matches": len(mcp_response["results"]),
                "elapsed_time": mcp_elapsed,
                "tokens": {
                    "input": self.token_counter.input_tokens,
                    "output": self.token_counter.output_tokens,
                    "total": self.token_counter.total_tokens
                }
            },
            "direct": {
                "matches": direct_result["match_count"],
                "elapsed_time": direct_result["elapsed_time"],
                "tool": direct_result["tool"]
            }
        }
        
        self._print_comparison(comparison)
        self.comparison_results.append(comparison)
        return comparison
        
    def demonstrate_token_counting(self):
        """Show token counting across different models."""
        print("\n=== Token Counting Demonstration ===")
        
        sample_query = "Find all Python classes that inherit from BaseModel"
        sample_response = """Found 5 classes:
1. UserModel in models/user.py:15
2. ProductModel in models/product.py:8
3. OrderModel in models/order.py:22
4. ConfigModel in core/config.py:10
5. ValidationModel in utils/validation.py:45"""
        
        print(f"Query: {sample_query}")
        print(f"Response preview: {sample_response[:100]}...")
        
        # Compare costs across models
        print("\nToken counts and costs for this query:")
        costs = compare_model_costs(sample_query + sample_response, is_output=True)
        
        for model, (tokens, cost) in costs.items():
            print(f"  {model}: {tokens} tokens, ${cost:.4f}")
            
    def generate_comparison_charts(self, output_dir: str = "comparison_charts"):
        """Generate visualization charts from comparison results."""
        print(f"\n=== Generating Comparison Charts ===")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Token usage comparison
        token_data = {}
        for result in self.comparison_results:
            query_type = result["query_type"]
            token_data[query_type] = result["mcp"]["tokens"]["total"]
            
        if token_data:
            self.charts.token_usage_comparison(
                token_data,
                title="Token Usage by Query Type",
                output_path=f"{output_dir}/token_usage.png"
            )
            print(f"Saved token usage chart to {output_dir}/token_usage.png")
        
        # Latency comparison
        latency_data = {
            "MCP": sum(r["mcp"]["elapsed_time"] for r in self.comparison_results) * 1000,
            "Direct Search": sum(r["direct"]["elapsed_time"] for r in self.comparison_results) * 1000
        }
        
        self.charts.latency_comparison(
            latency_data,
            title="Total Search Latency Comparison",
            unit="ms",
            output_path=f"{output_dir}/latency_comparison.png"
        )
        print(f"Saved latency chart to {output_dir}/latency_comparison.png")
        
        # Multi-metric comparison
        if self.comparison_results:
            metrics = {
                "Queries": {},
                "Matches": {},
                "Time (ms)": {}
            }
            
            for result in self.comparison_results:
                query = result["query"][:20] + "..." if len(result["query"]) > 20 else result["query"]
                metrics["Queries"][query] = 1
                metrics["Matches"][query] = result["mcp"]["matches"]
                metrics["Time (ms)"][query] = result["mcp"]["elapsed_time"] * 1000
                
            self.charts.multi_metric_comparison(
                metrics,
                "MCP Performance Metrics",
                output_path=f"{output_dir}/multi_metrics.png"
            )
            print(f"Saved multi-metric chart to {output_dir}/multi_metrics.png")
            
    def generate_report(self) -> Dict[str, Any]:
        """Generate final comparison report."""
        total_mcp_tokens = sum(r["mcp"]["tokens"]["total"] for r in self.comparison_results)
        total_mcp_time = sum(r["mcp"]["elapsed_time"] for r in self.comparison_results)
        total_direct_time = sum(r["direct"]["elapsed_time"] for r in self.comparison_results)
        
        # Calculate costs for different models
        model_costs = {}
        for model in ["gpt-4", "claude-3-sonnet", "gpt-3.5-turbo"]:
            counter = TokenCounter()
            for result in self.comparison_results:
                # Rough estimation based on our token counts
                counter.input_tokens = result["mcp"]["tokens"]["input"]
                counter.output_tokens = result["mcp"]["tokens"]["output"]
                cost = counter.estimate_cost(model=model)
                model_costs[model] = model_costs.get(model, 0) + cost
                
        report = {
            "summary": {
                "total_comparisons": len(self.comparison_results),
                "total_mcp_tokens": total_mcp_tokens,
                "total_mcp_time_seconds": total_mcp_time,
                "total_direct_time_seconds": total_direct_time,
                "speedup_factor": total_direct_time / total_mcp_time if total_mcp_time > 0 else 0
            },
            "cost_analysis": model_costs,
            "recommendations": self._generate_recommendations(),
            "detailed_results": self.comparison_results
        }
        
        return report
        
    def _print_comparison(self, comparison: Dict[str, Any]):
        """Print formatted comparison results."""
        print(f"\nResults for '{comparison['query']}':")
        print(f"  MCP: {comparison['mcp']['matches']} matches in {comparison['mcp']['elapsed_time']:.3f}s")
        print(f"       Tokens: {comparison['mcp']['tokens']['total']} "
              f"(input: {comparison['mcp']['tokens']['input']}, "
              f"output: {comparison['mcp']['tokens']['output']})")
        print(f"  Direct ({comparison['direct']['tool']}): "
              f"{comparison['direct']['matches']} matches in {comparison['direct']['elapsed_time']:.3f}s")
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on comparison results."""
        recommendations = []
        
        if not self.comparison_results:
            return ["No comparison data available"]
            
        avg_speedup = sum(
            r["direct"]["elapsed_time"] / r["mcp"]["elapsed_time"] 
            for r in self.comparison_results if r["mcp"]["elapsed_time"] > 0
        ) / len(self.comparison_results)
        
        total_tokens = sum(r["mcp"]["tokens"]["total"] for r in self.comparison_results)
        
        if avg_speedup < 1:
            recommendations.append(
                "MCP is faster on average for these queries - benefits from pre-indexing"
            )
        else:
            recommendations.append(
                f"Direct search is {avg_speedup:.1f}x faster for these simple queries"
            )
            
        if total_tokens > 1000:
            recommendations.append(
                f"High token usage ({total_tokens} tokens) - consider direct search for cost savings"
            )
        else:
            recommendations.append(
                f"Moderate token usage ({total_tokens} tokens) - acceptable for enhanced features"
            )
            
        recommendations.extend([
            "Use MCP for: semantic search, cross-file references, type information",
            "Use direct search for: simple pattern matching, one-off searches, small codebases"
        ])
        
        return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="Demo MCP vs Direct Search comparison"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace path to search in"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick demo with fewer comparisons"
    )
    
    args = parser.parse_args()
    
    # Create demo instance
    demo = MCPComparisonDemo(args.workspace)
    
    print("=== MCP vs Direct Search Comparison Demo ===")
    print(f"Workspace: {os.path.abspath(args.workspace)}")
    
    # Demonstrate token counting
    demo.demonstrate_token_counting()
    
    # Run comparisons
    if args.quick:
        # Quick demo - just two comparisons
        demo.run_symbol_search_comparison("main")
        demo.run_pattern_search_comparison("TODO")
    else:
        # Full demo
        symbols = ["main", "test", "init", "config"]
        patterns = ["TODO|FIXME", "import.*os", "class.*:"]
        
        for symbol in symbols:
            demo.run_symbol_search_comparison(symbol)
            
        for pattern in patterns:
            demo.run_pattern_search_comparison(pattern)
    
    # Generate charts
    demo.generate_comparison_charts()
    
    # Generate and print report
    report = demo.generate_report()
    
    print("\n=== FINAL REPORT ===")
    print(f"Total comparisons: {report['summary']['total_comparisons']}")
    print(f"Total MCP tokens used: {report['summary']['total_mcp_tokens']}")
    print(f"Average speedup factor: {report['summary']['speedup_factor']:.2f}x")
    
    print("\nEstimated costs per search:")
    for model, cost in report['cost_analysis'].items():
        print(f"  {model}: ${cost:.4f}")
        
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
        
    # Save detailed report
    with open("comparison_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nDetailed report saved to comparison_report.json")


if __name__ == "__main__":
    main()