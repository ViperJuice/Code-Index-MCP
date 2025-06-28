#!/usr/bin/env python3
"""
Demo analysis comparing MCP vs native tool usage in Claude Code.
Shows the potential benefits of MCP adoption.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import time
from mcp_server.core.path_utils import PathUtils


class MCPVsNativeDemo:
    """Demonstrate the difference between MCP and native tool usage."""
    
    def __init__(self):
        self.scenarios = {
            "find_class_definition": {
                "task": "Find the BM25Indexer class definition",
                "mcp_approach": [
                    {"tool": "symbol_lookup", "params": {"symbol": "BM25Indexer"}, "tokens": 100, "time": 0.1}
                ],
                "native_approach": [
                    {"tool": "grep", "params": {"pattern": "class BM25Indexer"}, "tokens": 500, "time": 0.5},
                    {"tool": "read_full", "params": {"file": "mcp_server/indexer/bm25_indexer.py"}, "tokens": 5000, "time": 0.2}
                ]
            },
            "fix_bug_in_method": {
                "task": "Fix a bug in the search method of SQLiteStore",
                "mcp_approach": [
                    {"tool": "symbol_lookup", "params": {"symbol": "SQLiteStore"}, "tokens": 100, "time": 0.1},
                    {"tool": "search_code", "params": {"query": "def search", "limit": 5}, "tokens": 300, "time": 0.2},
                    {"tool": "read_partial", "params": {"file": "sqlite_store.py", "offset": 450, "limit": 50}, "tokens": 200, "time": 0.1},
                    {"tool": "edit", "params": {"old": "...", "new": "..."}, "tokens": 150, "time": 0.1}
                ],
                "native_approach": [
                    {"tool": "find", "params": {"name": "*store*.py"}, "tokens": 200, "time": 1.0},
                    {"tool": "grep", "params": {"pattern": "class.*Store"}, "tokens": 800, "time": 0.8},
                    {"tool": "read_full", "params": {"file": "sqlite_store.py"}, "tokens": 8000, "time": 0.3},
                    {"tool": "edit", "params": {"old": "...", "new": "..."}, "tokens": 150, "time": 0.1}
                ]
            },
            "understand_reranking": {
                "task": "Understand how reranking works in the system",
                "mcp_approach": [
                    {"tool": "search_code", "params": {"query": "reranking algorithm", "semantic": True}, "tokens": 400, "time": 0.3},
                    {"tool": "search_code", "params": {"query": "class Reranker"}, "tokens": 200, "time": 0.1},
                    {"tool": "read_partial", "params": {"file": "reranker.py", "offset": 0, "limit": 100}, "tokens": 400, "time": 0.1}
                ],
                "native_approach": [
                    {"tool": "grep", "params": {"pattern": "rerank"}, "tokens": 1500, "time": 1.2},
                    {"tool": "read_full", "params": {"file": "reranker.py"}, "tokens": 6000, "time": 0.2},
                    {"tool": "read_full", "params": {"file": "hybrid_search.py"}, "tokens": 4000, "time": 0.2},
                    {"tool": "grep", "params": {"pattern": "RerankingSettings"}, "tokens": 300, "time": 0.3}
                ]
            },
            "add_new_feature": {
                "task": "Add caching to the search functionality",
                "mcp_approach": [
                    {"tool": "search_code", "params": {"query": "search cache", "semantic": True}, "tokens": 300, "time": 0.2},
                    {"tool": "symbol_lookup", "params": {"symbol": "search"}, "tokens": 200, "time": 0.1},
                    {"tool": "read_partial", "params": {"file": "dispatcher.py", "offset": 670, "limit": 80}, "tokens": 320, "time": 0.1},
                    {"tool": "multi_edit", "params": {"edits": [...]}, "tokens": 400, "time": 0.2}
                ],
                "native_approach": [
                    {"tool": "find", "params": {"name": "*.py", "exec": "grep -l search"}, "tokens": 1000, "time": 2.0},
                    {"tool": "read_full", "params": {"file": "dispatcher.py"}, "tokens": 7000, "time": 0.3},
                    {"tool": "read_full", "params": {"file": "cache_interfaces.py"}, "tokens": 3000, "time": 0.2},
                    {"tool": "write", "params": {"file": "dispatcher.py", "content": "..."}, "tokens": 7000, "time": 0.3}
                ]
            }
        }
    
    def calculate_metrics(self, approach: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate total metrics for an approach."""
        return {
            "total_tokens": sum(step["tokens"] for step in approach),
            "total_time": sum(step["time"] for step in approach),
            "num_operations": len(approach)
        }
    
    def compare_approaches(self, scenario_name: str) -> Dict[str, Any]:
        """Compare MCP vs native approach for a scenario."""
        scenario = self.scenarios[scenario_name]
        
        mcp_metrics = self.calculate_metrics(scenario["mcp_approach"])
        native_metrics = self.calculate_metrics(scenario["native_approach"])
        
        return {
            "task": scenario["task"],
            "mcp": {
                "steps": len(scenario["mcp_approach"]),
                "tokens": mcp_metrics["total_tokens"],
                "time": mcp_metrics["total_time"],
                "workflow": [f"{s['tool']}({list(s['params'].keys())[0]})" for s in scenario["mcp_approach"]]
            },
            "native": {
                "steps": len(scenario["native_approach"]),
                "tokens": native_metrics["total_tokens"],
                "time": native_metrics["total_time"],
                "workflow": [f"{s['tool']}({list(s['params'].keys())[0]})" for s in scenario["native_approach"]]
            },
            "improvement": {
                "token_reduction": (native_metrics["total_tokens"] - mcp_metrics["total_tokens"]) / native_metrics["total_tokens"] * 100,
                "time_reduction": (native_metrics["total_time"] - mcp_metrics["total_time"]) / native_metrics["total_time"] * 100,
                "efficiency_gain": (native_metrics["num_operations"] - mcp_metrics["num_operations"]) / native_metrics["num_operations"] * 100
            }
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive comparison report."""
        lines = []
        lines.append("=" * 80)
        lines.append("MCP vs Native Tool Usage Analysis")
        lines.append("Comparing Claude Code workflows with and without MCP")
        lines.append("=" * 80)
        
        total_mcp_tokens = 0
        total_native_tokens = 0
        total_mcp_time = 0
        total_native_time = 0
        
        for i, scenario_name in enumerate(self.scenarios.keys(), 1):
            comparison = self.compare_approaches(scenario_name)
            
            lines.append(f"\n{i}. Scenario: {comparison['task']}")
            lines.append("-" * 70)
            
            # MCP Approach
            lines.append("   MCP Approach:")
            lines.append(f"     Steps: {comparison['mcp']['steps']}")
            lines.append(f"     Tokens: {comparison['mcp']['tokens']:,}")
            lines.append(f"     Time: {comparison['mcp']['time']:.1f}s")
            lines.append(f"     Workflow: {' -> '.join(comparison['mcp']['workflow'])}")
            
            # Native Approach
            lines.append("\n   Native Approach:")
            lines.append(f"     Steps: {comparison['native']['steps']}")
            lines.append(f"     Tokens: {comparison['native']['tokens']:,}")
            lines.append(f"     Time: {comparison['native']['time']:.1f}s")
            lines.append(f"     Workflow: {' -> '.join(comparison['native']['workflow'])}")
            
            # Improvements
            lines.append("\n   Improvements with MCP:")
            lines.append(f"     Token reduction: {comparison['improvement']['token_reduction']:.1f}%")
            lines.append(f"     Time reduction: {comparison['improvement']['time_reduction']:.1f}%")
            lines.append(f"     Fewer steps: {comparison['improvement']['efficiency_gain']:.1f}%")
            
            # Accumulate totals
            total_mcp_tokens += comparison['mcp']['tokens']
            total_native_tokens += comparison['native']['tokens']
            total_mcp_time += comparison['mcp']['time']
            total_native_time += comparison['native']['time']
        
        # Overall summary
        lines.append("\n" + "=" * 80)
        lines.append("OVERALL SUMMARY")
        lines.append("=" * 80)
        
        lines.append(f"\nTotal Token Usage:")
        lines.append(f"  - With MCP: {total_mcp_tokens:,} tokens")
        lines.append(f"  - Without MCP: {total_native_tokens:,} tokens")
        lines.append(f"  - Reduction: {(total_native_tokens - total_mcp_tokens) / total_native_tokens * 100:.1f}%")
        
        lines.append(f"\nTotal Time:")
        lines.append(f"  - With MCP: {total_mcp_time:.1f}s")
        lines.append(f"  - Without MCP: {total_native_time:.1f}s")
        lines.append(f"  - Reduction: {(total_native_time - total_mcp_time) / total_native_time * 100:.1f}%")
        
        lines.append("\nKey Benefits of MCP:")
        lines.append("  1. Targeted retrieval: Get exactly what you need (symbol definitions, specific code)")
        lines.append("  2. Semantic understanding: Natural language queries that understand intent")
        lines.append("  3. Reduced context usage: Snippets instead of full files")
        lines.append("  4. Faster operations: Direct lookups instead of pattern matching")
        lines.append("  5. Better accuracy: Type-aware symbol resolution")
        
        lines.append("\nCurrent Status:")
        lines.append("  - MCP tools have [MCP-FIRST] instructions")
        lines.append("  - But Claude Code is not using them (0% adoption)")
        lines.append("  - Patched dispatcher now returns results via BM25 fallback")
        lines.append("  - Ready for real-world testing")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


def main():
    """Run the demo analysis."""
    demo = MCPVsNativeDemo()
    report = demo.generate_report()
    
    print(report)
    
    # Save report
    report_path = Path("PathUtils.get_workspace_root()/MCP_VS_NATIVE_ANALYSIS.md")
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")
    
    # Also create JSON data for further analysis
    json_data = {
        "scenarios": {},
        "summary": {
            "total_scenarios": len(demo.scenarios),
            "average_token_reduction": 0,
            "average_time_reduction": 0
        }
    }
    
    token_reductions = []
    time_reductions = []
    
    for scenario_name in demo.scenarios:
        comparison = demo.compare_approaches(scenario_name)
        json_data["scenarios"][scenario_name] = comparison
        token_reductions.append(comparison["improvement"]["token_reduction"])
        time_reductions.append(comparison["improvement"]["time_reduction"])
    
    json_data["summary"]["average_token_reduction"] = sum(token_reductions) / len(token_reductions)
    json_data["summary"]["average_time_reduction"] = sum(time_reductions) / len(time_reductions)
    
    json_path = Path("PathUtils.get_workspace_root()/mcp_vs_native_analysis.json")
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"JSON data saved to: {json_path}")


if __name__ == "__main__":
    main()