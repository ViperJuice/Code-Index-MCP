#!/usr/bin/env python3
"""
Quick MCP vs Native Validation Test
Tests a small subset of queries to validate the setup.
"""

import asyncio
import json
import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.comprehensive_mcp_vs_native_test import MCPVsNativeTestRunner


async def main():
    """Run quick validation test."""
    workspace = Path('PathUtils.get_workspace_root()')
    
    # Override test queries file to use the small test set
    runner = MCPVsNativeTestRunner(workspace)
    runner.test_queries_file = workspace / "test_queries_small.json"
    
    try:
        print("Running Quick MCP vs Native Validation Test")
        print("=" * 60)
        
        results = await asyncio.wait_for(runner.run_comprehensive_test(), timeout=600)
        
        print("\n" + "="*60)
        print("QUICK VALIDATION TEST COMPLETED")
        print("="*60)
        
        summary = results['summary']
        print(f"Total Queries: {results['total_queries']}")
        print(f"MCP Success Rate: {summary['mcp_success_rate']:.1%}")
        print(f"Native Success Rate: {summary['native_success_rate']:.1%}")
        print(f"MCP Avg Response Time: {summary['mcp_avg_response_time']:.0f}ms")
        print(f"Native Avg Response Time: {summary['native_avg_response_time']:.0f}ms")
        print(f"Token Efficiency Improvement: {summary['token_efficiency_comparison']:.1%}")
        print(f"Response Time Improvement: {summary['response_time_comparison']:.1%}")
        
        print(f"\nResults saved to: {runner.results_dir}")
        
        # Show some detailed metrics
        if results['total_queries'] > 0:
            print(f"\nDetailed Token Metrics:")
            print(f"MCP Total Tokens: {summary['mcp_total_tokens']:,}")
            print(f"Native Total Tokens: {summary['native_total_tokens']:,}")
            print(f"MCP Avg Input: {summary['mcp_avg_input_tokens']:.0f}")
            print(f"Native Avg Input: {summary['native_avg_input_tokens']:.0f}")
            print(f"MCP Avg Output: {summary['mcp_avg_output_tokens']:.0f}")
            print(f"Native Avg Output: {summary['native_avg_output_tokens']:.0f}")
        
        # Check if validation was successful
        if (summary['mcp_success_rate'] >= 0.5 and summary['native_success_rate'] >= 0.5 and 
            results['total_queries'] >= 2):
            print("\n✅ VALIDATION SUCCESSFUL - Ready for full comprehensive test")
            return True
        else:
            print("\n❌ VALIDATION FAILED - Check configuration and setup")
            return False
            
    except Exception as e:
        import traceback
        print(f"\n❌ VALIDATION ERROR: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)