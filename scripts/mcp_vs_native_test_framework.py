#!/usr/bin/env python3
"""
Comprehensive MCP vs Native Retrieval Performance Test Framework

This framework tests Claude Code's usage of MCP tools vs native retrieval,
tracking token usage, performance metrics, and behavioral patterns.
"""

import json
import time
import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio
import tempfile
import shutil
from mcp_server.core.path_utils import PathUtils

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TokenMetrics:
    """Track token usage for LLM calls"""
    input_tokens: Dict[str, int] = field(default_factory=lambda: {
        "user_prompts": 0,
        "tool_responses": 0,
        "system_messages": 0,
        "context": 0
    })
    output_tokens: Dict[str, int] = field(default_factory=lambda: {
        "assistant_responses": 0,
        "tool_invocations": 0,
        "reasoning": 0
    })
    
    @property
    def total_input(self) -> int:
        return sum(self.input_tokens.values())
    
    @property
    def total_output(self) -> int:
        return sum(self.output_tokens.values())
    
    @property
    def total_tokens(self) -> int:
        return self.total_input + self.total_output
    
    @property
    def efficiency_ratio(self) -> float:
        """Output tokens per input token"""
        return self.total_output / max(self.total_input, 1)


@dataclass
class RetrievalMetrics:
    """Track retrieval-specific metrics"""
    search_queries: int = 0
    read_operations: int = 0
    reads_with_offset: int = 0
    reads_with_limit: int = 0
    grep_operations: int = 0
    glob_operations: int = 0
    mcp_symbol_lookups: int = 0
    mcp_searches: int = 0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def avg_response_time(self) -> float:
        return sum(self.response_times) / max(len(self.response_times), 1)


@dataclass
class EditMetrics:
    """Track edit pattern metrics"""
    single_edits: int = 0
    multi_edits: int = 0
    full_writes: int = 0
    edit_sizes: List[int] = field(default_factory=list)
    line_specific_edits: int = 0
    
    @property
    def avg_edit_size(self) -> float:
        return sum(self.edit_sizes) / max(len(self.edit_sizes), 1)


@dataclass
class ScenarioResult:
    """Results for a single test scenario"""
    scenario_name: str
    agent_type: str  # "mcp" or "native"
    start_time: datetime
    end_time: Optional[datetime] = None
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    retrieval_metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    edit_metrics: EditMetrics = field(default_factory=EditMetrics)
    success: bool = False
    error_message: Optional[str] = None
    transcript_path: Optional[str] = None
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class TestScenario:
    """Base class for test scenarios"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.prompts: List[str] = []
    
    def get_prompts(self) -> List[str]:
        """Get the prompts to send to the agent"""
        return self.prompts


class SymbolSearchScenario(TestScenario):
    """Test scenario for symbol search and navigation"""
    
    def __init__(self):
        super().__init__(
            "Symbol Search & Navigation",
            "Find specific class definitions and navigate to methods"
        )
        self.prompts = [
            "Find the definition of the EnhancedDispatcher class",
            "Navigate to the search method in EnhancedDispatcher",
            "Show me all methods that EnhancedDispatcher implements"
        ]


class NaturalLanguageQueryScenario(TestScenario):
    """Test scenario for natural language queries"""
    
    def __init__(self):
        super().__init__(
            "Natural Language Query",
            "Test semantic search capabilities with natural language"
        )
        self.prompts = [
            "How does error handling work in the dispatcher?",
            "What's the purpose of the semantic indexer in this codebase?",
            "Explain how plugins are loaded dynamically"
        ]


class CodeModificationScenario(TestScenario):
    """Test scenario for code modifications"""
    
    def __init__(self):
        super().__init__(
            "Code Modification",
            "Add parameters and modify existing functions"
        )
        self.prompts = [
            "Add a new parameter called 'timeout' with default value 30 to the search method in EnhancedDispatcher",
            "Update all calls to the search method to include the new timeout parameter",
            "Add appropriate documentation for the new parameter"
        ]


class CrossFileRefactoringScenario(TestScenario):
    """Test scenario for cross-file refactoring"""
    
    def __init__(self):
        super().__init__(
            "Cross-File Refactoring",
            "Rename functions across multiple files"
        )
        self.prompts = [
            "Rename the 'index_file' method to 'process_file' across the entire codebase",
            "Update all references and documentation to use the new name",
            "Ensure all tests still pass with the new naming"
        ]


class DocumentationSearchScenario(TestScenario):
    """Test scenario for documentation search and updates"""
    
    def __init__(self):
        super().__init__(
            "Documentation Search",
            "Find and update API documentation"
        )
        self.prompts = [
            "Find the API documentation for the MCP server endpoints",
            "Update the documentation to include examples for each endpoint",
            "Add information about error responses and status codes"
        ]


class TranscriptAnalyzer:
    """Analyze Claude Code JSONL transcripts for metrics"""
    
    @staticmethod
    def parse_transcript(transcript_path: str) -> List[Dict[str, Any]]:
        """Parse JSONL transcript file"""
        messages = []
        with open(transcript_path, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages
    
    @staticmethod
    def extract_metrics(messages: List[Dict[str, Any]], scenario: TestScenario) -> ScenarioResult:
        """Extract metrics from transcript messages"""
        result = ScenarioResult(
            scenario_name=scenario.name,
            agent_type="unknown",
            start_time=datetime.now()
        )
        
        for msg in messages:
            # Track token usage
            if "usage" in msg:
                usage = msg["usage"]
                if "input_tokens" in usage:
                    # Categorize input tokens based on content
                    if msg.get("role") == "user":
                        result.token_metrics.input_tokens["user_prompts"] += usage["input_tokens"]
                    elif msg.get("role") == "tool":
                        result.token_metrics.input_tokens["tool_responses"] += usage["input_tokens"]
                    else:
                        result.token_metrics.input_tokens["context"] += usage["input_tokens"]
                
                if "output_tokens" in usage:
                    # Categorize output tokens
                    if "tool_use" in msg.get("content", ""):
                        result.token_metrics.output_tokens["tool_invocations"] += usage["output_tokens"]
                    else:
                        result.token_metrics.output_tokens["assistant_responses"] += usage["output_tokens"]
            
            # Track tool usage
            if msg.get("type") == "tool_use":
                tool_name = msg.get("name", "")
                
                # Retrieval tools
                if tool_name == "Read":
                    result.retrieval_metrics.read_operations += 1
                    params = msg.get("input", {})
                    if "offset" in params:
                        result.retrieval_metrics.reads_with_offset += 1
                    if "limit" in params:
                        result.retrieval_metrics.reads_with_limit += 1
                elif tool_name == "Grep":
                    result.retrieval_metrics.grep_operations += 1
                elif tool_name == "Glob":
                    result.retrieval_metrics.glob_operations += 1
                elif tool_name == "mcp__code-index-mcp__symbol_lookup":
                    result.retrieval_metrics.mcp_symbol_lookups += 1
                elif tool_name == "mcp__code-index-mcp__search_code":
                    result.retrieval_metrics.mcp_searches += 1
                
                # Edit tools
                elif tool_name == "Edit":
                    result.edit_metrics.single_edits += 1
                    params = msg.get("input", {})
                    if "old_string" in params:
                        result.edit_metrics.edit_sizes.append(len(params["old_string"]))
                elif tool_name == "MultiEdit":
                    result.edit_metrics.multi_edits += 1
                    params = msg.get("input", {})
                    if "edits" in params:
                        for edit in params["edits"]:
                            if "old_string" in edit:
                                result.edit_metrics.edit_sizes.append(len(edit["old_string"]))
                elif tool_name == "Write":
                    result.edit_metrics.full_writes += 1
                
                # Track response time if available
                if "duration" in msg:
                    result.retrieval_metrics.response_times.append(msg["duration"])
        
        return result


class MCPTestFramework:
    """Main test framework for MCP vs Native comparison"""
    
    def __init__(self, test_repo_path: Optional[str] = None):
        self.test_repo_path = test_repo_path or self._create_test_repo()
        self.scenarios = [
            SymbolSearchScenario(),
            NaturalLanguageQueryScenario(),
            CodeModificationScenario(),
            CrossFileRefactoringScenario(),
            DocumentationSearchScenario()
        ]
        self.results: Dict[str, List[ScenarioResult]] = {
            "mcp": [],
            "native": []
        }
    
    def _create_test_repo(self) -> str:
        """Create a test repository with known code patterns"""
        # For now, we'll use the current Code-Index-MCP repo
        # In a real test, we'd create a controlled test repo
        return "PathUtils.get_workspace_root()"
    
    async def run_scenario_with_agent(
        self, 
        scenario: TestScenario, 
        agent_type: str,
        transcript_path: str
    ) -> ScenarioResult:
        """Run a single scenario with an agent"""
        result = ScenarioResult(
            scenario_name=scenario.name,
            agent_type=agent_type,
            start_time=datetime.now(),
            transcript_path=transcript_path
        )
        
        try:
            # TODO: Actually launch Claude Code agent and run scenario
            # For now, we'll simulate with existing transcripts
            
            # In real implementation:
            # 1. Launch claude-code with appropriate flags
            # 2. Send prompts from scenario
            # 3. Wait for completion
            # 4. Parse resulting transcript
            
            result.end_time = datetime.now()
            result.success = True
            
        except Exception as e:
            result.error_message = str(e)
            result.success = False
        
        return result
    
    async def run_all_tests(self):
        """Run all test scenarios with both agent types"""
        print("Starting MCP vs Native Retrieval Performance Tests")
        print("=" * 60)
        
        # Run tests with MCP-enabled agent
        print("\nRunning tests with MCP-enabled agent...")
        for scenario in self.scenarios:
            print(f"  - {scenario.name}")
            transcript_path = f"PathUtils.get_temp_path() / "mcp_test_{scenario.name.replace(' ', '_')}.jsonl"
            result = await self.run_scenario_with_agent(scenario, "mcp", transcript_path)
            self.results["mcp"].append(result)
        
        # Run tests with native-only agent
        print("\nRunning tests with native-only agent...")
        for scenario in self.scenarios:
            print(f"  - {scenario.name}")
            transcript_path = f"/tmp/native_test_{scenario.name.replace(' ', '_')}.jsonl"
            result = await self.run_scenario_with_agent(scenario, "native", transcript_path)
            self.results["native"].append(result)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance comparison report"""
        report = {
            "test_date": datetime.now().isoformat(),
            "scenarios": [],
            "summary": {
                "mcp": {},
                "native": {}
            }
        }
        
        # Compare results for each scenario
        for i, scenario in enumerate(self.scenarios):
            mcp_result = self.results["mcp"][i] if i < len(self.results["mcp"]) else None
            native_result = self.results["native"][i] if i < len(self.results["native"]) else None
            
            scenario_comparison = {
                "name": scenario.name,
                "description": scenario.description,
                "mcp": asdict(mcp_result) if mcp_result else None,
                "native": asdict(native_result) if native_result else None,
                "comparison": {}
            }
            
            if mcp_result and native_result:
                # Calculate comparisons
                scenario_comparison["comparison"] = {
                    "token_efficiency": {
                        "mcp_total": mcp_result.token_metrics.total_tokens,
                        "native_total": native_result.token_metrics.total_tokens,
                        "savings": native_result.token_metrics.total_tokens - mcp_result.token_metrics.total_tokens,
                        "savings_percent": (
                            (native_result.token_metrics.total_tokens - mcp_result.token_metrics.total_tokens) 
                            / native_result.token_metrics.total_tokens * 100
                        ) if native_result.token_metrics.total_tokens > 0 else 0
                    },
                    "retrieval_efficiency": {
                        "mcp_operations": (
                            mcp_result.retrieval_metrics.search_queries +
                            mcp_result.retrieval_metrics.read_operations +
                            mcp_result.retrieval_metrics.mcp_symbol_lookups +
                            mcp_result.retrieval_metrics.mcp_searches
                        ),
                        "native_operations": (
                            native_result.retrieval_metrics.search_queries +
                            native_result.retrieval_metrics.read_operations +
                            native_result.retrieval_metrics.grep_operations +
                            native_result.retrieval_metrics.glob_operations
                        )
                    },
                    "edit_patterns": {
                        "mcp_targeted_edits": mcp_result.edit_metrics.single_edits + mcp_result.edit_metrics.multi_edits,
                        "native_targeted_edits": native_result.edit_metrics.single_edits + native_result.edit_metrics.multi_edits,
                        "mcp_full_writes": mcp_result.edit_metrics.full_writes,
                        "native_full_writes": native_result.edit_metrics.full_writes
                    },
                    "performance": {
                        "mcp_duration": mcp_result.duration,
                        "native_duration": native_result.duration,
                        "speedup": native_result.duration / mcp_result.duration if mcp_result.duration > 0 else 0
                    }
                }
            
            report["scenarios"].append(scenario_comparison)
        
        # Calculate overall summary
        for agent_type in ["mcp", "native"]:
            results = self.results[agent_type]
            if results:
                report["summary"][agent_type] = {
                    "total_tokens": sum(r.token_metrics.total_tokens for r in results),
                    "avg_tokens_per_scenario": sum(r.token_metrics.total_tokens for r in results) / len(results),
                    "total_duration": sum(r.duration for r in results),
                    "success_rate": sum(1 for r in results if r.success) / len(results) * 100,
                    "avg_response_time": sum(r.retrieval_metrics.avg_response_time for r in results) / len(results)
                }
        
        return report
    
    def save_report(self, filepath: str):
        """Save the report to a file"""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {filepath}")


async def main():
    """Main entry point for the test framework"""
    framework = MCPTestFramework()
    
    # Run all tests
    await framework.run_all_tests()
    
    # Generate and save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"PathUtils.get_workspace_root()/mcp_vs_native_report_{timestamp}.json"
    framework.save_report(report_path)
    
    # Print summary
    report = framework.generate_report()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for agent_type in ["mcp", "native"]:
        if agent_type in report["summary"]:
            summary = report["summary"][agent_type]
            print(f"\n{agent_type.upper()} Agent:")
            print(f"  Total Tokens: {summary.get('total_tokens', 0):,}")
            print(f"  Avg Tokens/Scenario: {summary.get('avg_tokens_per_scenario', 0):,.0f}")
            print(f"  Total Duration: {summary.get('total_duration', 0):.2f}s")
            print(f"  Success Rate: {summary.get('success_rate', 0):.1f}%")


if __name__ == "__main__":
    asyncio.run(main())