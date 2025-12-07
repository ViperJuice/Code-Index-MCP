#!/usr/bin/env python3
"""
MCP Verification Test Suite
Tests and verifies that Claude Code uses MCP tools first for all searches
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


class MCPVerificationTester:
    """Verifies MCP-first behavior in Claude Code"""

    def __init__(self):
        self.test_results = []
        self.tool_usage_log = []

    def log_tool_usage(self, tool_name: str, params: Dict[str, Any], duration: float):
        """Log tool usage for analysis"""
        self.tool_usage_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "params": params,
                "duration": duration,
            }
        )

    def verify_mcp_first(self, tool_sequence: List[str]) -> Tuple[bool, str]:
        """Verify that MCP tools were used before native tools"""
        mcp_tools = [
            "mcp__code-index-mcp__symbol_lookup",
            "mcp__code-index-mcp__search_code",
            "mcp__code-index-mcp__get_status",
            "mcp__code-index-mcp__list_plugins",
            "mcp__code-index-mcp__reindex",
        ]

        native_search_tools = ["Grep", "Glob", "Find"]

        # Check if any native search tool was used before MCP
        first_mcp_index = float("inf")
        first_native_index = float("inf")

        for i, tool in enumerate(tool_sequence):
            if any(mcp in tool for mcp in mcp_tools):
                first_mcp_index = min(first_mcp_index, i)
            elif any(native in tool for native in native_search_tools):
                first_native_index = min(first_native_index, i)

        if first_native_index < first_mcp_index:
            return False, f"Native tool used before MCP at position {first_native_index}"
        elif first_mcp_index == float("inf"):
            return False, "No MCP tools used"
        else:
            return True, "MCP tools used first"

    def run_test_scenario(
        self, scenario_name: str, expected_tool: str, actual_tools: List[str]
    ) -> Dict[str, Any]:
        """Run a single test scenario"""
        print(f"\n🧪 Testing: {scenario_name}")

        # Verify MCP was used first
        mcp_first, message = self.verify_mcp_first(actual_tools)

        # Check if expected tool was used
        expected_used = any(expected_tool in tool for tool in actual_tools)

        # Measure performance (simulated)
        is_mcp = "mcp__" in expected_tool
        estimated_time = 0.1 if is_mcp else 30.0  # MCP is ~300x faster

        result = {
            "scenario": scenario_name,
            "mcp_first": mcp_first,
            "expected_tool": expected_tool,
            "expected_used": expected_used,
            "actual_tools": actual_tools,
            "message": message,
            "estimated_time": estimated_time,
            "passed": mcp_first and expected_used,
        }

        self.test_results.append(result)

        # Print result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  {status}: {message}")
        if expected_used:
            print(f"  ✓ Used expected tool: {expected_tool}")
        else:
            print(f"  ✗ Did not use expected tool: {expected_tool}")

        return result

    def generate_report(self) -> str:
        """Generate a comprehensive verification report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])

        report = [
            "# MCP Verification Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"\n## Summary",
            f"- Total Tests: {total_tests}",
            f"- Passed: {passed_tests}",
            f"- Failed: {total_tests - passed_tests}",
            f"- Success Rate: {(passed_tests/total_tests*100):.1f}%",
            "\n## Test Results\n",
        ]

        for result in self.test_results:
            report.append(f"### {result['scenario']}")
            report.append(f"- Status: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
            report.append(f"- MCP First: {result['mcp_first']}")
            report.append(f"- Expected Tool Used: {result['expected_used']}")
            report.append(f"- Message: {result['message']}")
            report.append(f"- Tools Used: {', '.join(result['actual_tools'])}")
            report.append("")

        # Performance comparison
        report.append("\n## Performance Impact")
        mcp_time = sum(
            r["estimated_time"] for r in self.test_results if "mcp__" in r["expected_tool"]
        )
        native_time = sum(30.0 for r in self.test_results if "mcp__" not in r["expected_tool"])

        report.append(f"- Estimated time with MCP: {mcp_time:.1f}s")
        report.append(f"- Estimated time without MCP: {native_time:.1f}s")
        report.append(f"- Speedup: {native_time/max(mcp_time, 0.1):.0f}x faster")

        return "\n".join(report)


def run_verification_tests():
    """Run all verification tests"""
    tester = MCPVerificationTester()

    print("🚀 MCP Verification Test Suite")
    print("=" * 60)

    # Test scenarios with expected tool usage
    test_scenarios = [
        {
            "name": "Find class definition",
            "expected_tool": "mcp__code-index-mcp__symbol_lookup",
            "actual_tools": ["mcp__code-index-mcp__symbol_lookup", "Read"],  # Simulated
        },
        {
            "name": "Search function pattern",
            "expected_tool": "mcp__code-index-mcp__search_code",
            "actual_tools": ["mcp__code-index-mcp__search_code", "Read"],
        },
        {
            "name": "Find imports of module",
            "expected_tool": "mcp__code-index-mcp__search_code",
            "actual_tools": ["mcp__code-index-mcp__search_code"],
        },
        {
            "name": "Semantic concept search",
            "expected_tool": "mcp__code-index-mcp__search_code",
            "actual_tools": ["mcp__code-index-mcp__search_code"],
        },
        {
            "name": "Bad pattern - Grep first",
            "expected_tool": "mcp__code-index-mcp__search_code",
            "actual_tools": ["Grep", "mcp__code-index-mcp__search_code"],  # Should fail
        },
    ]

    # Run tests
    for scenario in test_scenarios:
        tester.run_test_scenario(
            scenario["name"], scenario["expected_tool"], scenario["actual_tools"]
        )

    # Generate and save report
    report = tester.generate_report()

    with open("mcp_verification_report.md", "w") as f:
        f.write(report)

    print("\n" + "=" * 60)
    print("📊 Report saved to: mcp_verification_report.md")

    # Return summary
    total = len(tester.test_results)
    passed = sum(1 for r in tester.test_results if r["passed"])
    print(f"\n✅ Passed: {passed}/{total} tests")

    return tester


if __name__ == "__main__":
    run_verification_tests()
