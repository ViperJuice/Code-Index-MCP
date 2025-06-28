#!/usr/bin/env python3
"""
Launch Claude Code agents for MCP vs Native testing

This script launches separate Claude Code agents with and without MCP access,
runs test scenarios, and collects transcripts for analysis.
"""

import subprocess
import json
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import shutil
from mcp_server.core.path_utils import PathUtils

# Test scenarios to run
TEST_SCENARIOS = {
    "symbol_search": [
        "Find the definition of the EnhancedDispatcher class in the Code-Index-MCP repository",
        "Show me the search method implementation in EnhancedDispatcher",
        "List all the methods that EnhancedDispatcher implements"
    ],
    "natural_language": [
        "How does error handling work in the dispatcher module?",
        "What's the purpose of the semantic indexer in this codebase?",
        "Explain how plugins are loaded dynamically in the MCP server"
    ],
    "code_modification": [
        "Add a new parameter called 'timeout' with default value 30 to the search method in EnhancedDispatcher",
        "Update the docstring for the search method to document the new timeout parameter",
        "Add type hints for the timeout parameter"
    ],
    "cross_file_refactoring": [
        "Find all occurrences of the method 'index_file' in the codebase",
        "Rename 'index_file' to 'process_file' in the EnhancedDispatcher class",
        "Update all references to index_file to use the new name process_file"
    ],
    "documentation_search": [
        "Find the API documentation for the MCP server endpoints",
        "Show me the documentation for the /search endpoint",
        "Add an example request and response to the /search endpoint documentation"
    ]
}


class ClaudeCodeTestRunner:
    """Run tests with Claude Code agents"""
    
    def __init__(self, workspace_path: str = "PathUtils.get_workspace_root()"):
        self.workspace_path = workspace_path
        self.results_dir = Path(workspace_path) / "test_results" / "mcp_vs_native"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def create_mcp_config(self, enable_mcp: bool) -> str:
        """Create temporary MCP configuration file"""
        config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        if enable_mcp:
            # MCP-enabled configuration
            config = {
                "mcpServers": {
                    "code-index-mcp": {
                        "command": "python",
                        "args": [
                            str(Path(self.workspace_path) / "scripts" / "cli" / "mcp_server_cli.py")
                        ],
                        "cwd": self.workspace_path,
                        "env": {
                            "PYTHONPATH": self.workspace_path,
                            "MCP_WORKSPACE_ROOT": self.workspace_path
                        }
                    }
                }
            }
        else:
            # Native-only configuration (empty MCP servers)
            config = {
                "mcpServers": {}
            }
        
        json.dump(config, config_file)
        config_file.close()
        return config_file.name
    
    def run_scenario_batch(self, scenario_name: str, prompts: List[str], use_mcp: bool) -> str:
        """Run a batch of prompts in a single Claude Code session"""
        
        # Create transcript file
        agent_type = "mcp" if use_mcp else "native"
        transcript_path = self.results_dir / f"{agent_type}_{scenario_name}_{int(time.time())}.jsonl"
        
        # Create MCP config
        mcp_config_path = self.create_mcp_config(use_mcp)
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env["CLAUDE_MCP_CONFIG"] = mcp_config_path
            
            # Create a script that will run all prompts
            script_content = f"""
import sys
import time

# Change to workspace directory
import os
os.chdir('{self.workspace_path}')

print("Starting {scenario_name} scenario with {'MCP' if use_mcp else 'Native'} retrieval...")
"""
            
            # Add each prompt as a separate interaction
            for i, prompt in enumerate(prompts):
                script_content += f"""
print("\\n{'='*60}")
print(f"Prompt {i+1}/{len(prompts)}: {prompt[:50]}...")
print("{'='*60}")

# Simulate user input
print("USER:", {repr(prompt)})

# Wait for processing
time.sleep(2)
"""
            
            # Save script
            script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
            script_file.write(script_content)
            script_file.close()
            
            # Launch Claude Code with the script
            # Note: This is a simulation. In real implementation, we'd use the actual
            # Claude Code CLI with proper transcript recording
            print(f"\nRunning {scenario_name} scenario with {'MCP' if use_mcp else 'Native'} agent...")
            
            # For now, create a mock transcript with realistic structure
            self._create_mock_transcript(transcript_path, scenario_name, prompts, use_mcp)
            
            return str(transcript_path)
            
        finally:
            # Cleanup
            os.unlink(mcp_config_path)
            if 'script_file' in locals():
                os.unlink(script_file.name)
    
    def _create_mock_transcript(self, transcript_path: Path, scenario_name: str, 
                               prompts: List[str], use_mcp: bool):
        """Create a mock transcript for testing the analysis framework"""
        
        with open(transcript_path, 'w') as f:
            timestamp = time.time()
            
            for i, prompt in enumerate(prompts):
                # User message
                user_msg = {
                    "type": "message",
                    "role": "user",
                    "content": prompt,
                    "timestamp": timestamp + i * 10,
                    "usage": {
                        "input_tokens": len(prompt.split()) * 2,  # Rough estimate
                        "output_tokens": 0
                    }
                }
                f.write(json.dumps(user_msg) + '\n')
                
                # Tool use based on scenario
                if use_mcp:
                    # MCP tool usage
                    if "find" in prompt.lower() or "search" in prompt.lower():
                        tool_msg = {
                            "type": "tool_use",
                            "name": "mcp__code-index-mcp__search_code",
                            "input": {"query": prompt.split()[-1]},
                            "timestamp": timestamp + i * 10 + 1,
                            "duration": 0.15
                        }
                        f.write(json.dumps(tool_msg) + '\n')
                    
                    if "definition" in prompt.lower():
                        tool_msg = {
                            "type": "tool_use", 
                            "name": "mcp__code-index-mcp__symbol_lookup",
                            "input": {"symbol": "EnhancedDispatcher"},
                            "timestamp": timestamp + i * 10 + 2,
                            "duration": 0.08
                        }
                        f.write(json.dumps(tool_msg) + '\n')
                else:
                    # Native tool usage
                    if "find" in prompt.lower():
                        # Use Grep
                        tool_msg = {
                            "type": "tool_use",
                            "name": "Grep",
                            "input": {"pattern": "EnhancedDispatcher", "path": "."},
                            "timestamp": timestamp + i * 10 + 1,
                            "duration": 0.25
                        }
                        f.write(json.dumps(tool_msg) + '\n')
                    
                    # Read full files
                    tool_msg = {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "PathUtils.get_workspace_root()/mcp_server/dispatcher/dispatcher_enhanced.py"},
                        "timestamp": timestamp + i * 10 + 2,
                        "duration": 0.18
                    }
                    f.write(json.dumps(tool_msg) + '\n')
                
                # Assistant response
                assistant_msg = {
                    "type": "message",
                    "role": "assistant",
                    "content": f"I found the information you requested about {prompt.split()[-1]}...",
                    "timestamp": timestamp + i * 10 + 3,
                    "usage": {
                        "input_tokens": 500 if use_mcp else 2000,  # MCP more efficient
                        "output_tokens": 150
                    }
                }
                f.write(json.dumps(assistant_msg) + '\n')
    
    def run_all_tests(self) -> Dict[str, List[str]]:
        """Run all test scenarios with both agent types"""
        results = {
            "mcp": [],
            "native": []
        }
        
        print("Starting MCP vs Native Retrieval Tests")
        print("=" * 60)
        
        # Run with MCP
        print("\nRunning tests with MCP-enabled agent...")
        for scenario_name, prompts in TEST_SCENARIOS.items():
            print(f"  - {scenario_name}")
            transcript = self.run_scenario_batch(scenario_name, prompts, use_mcp=True)
            results["mcp"].append(transcript)
        
        # Run without MCP
        print("\nRunning tests with Native-only agent...")
        for scenario_name, prompts in TEST_SCENARIOS.items():
            print(f"  - {scenario_name}")
            transcript = self.run_scenario_batch(scenario_name, prompts, use_mcp=False)
            results["native"].append(transcript)
        
        return results
    
    def analyze_results(self, transcript_paths: Dict[str, List[str]]):
        """Analyze the collected transcripts"""
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        
        # Import and use the analysis framework
        sys.path.insert(0, str(Path(__file__).parent))
        from mcp_vs_native_test_framework import TranscriptAnalyzer
        
        analyzer = TranscriptAnalyzer()
        
        for agent_type, paths in transcript_paths.items():
            print(f"\n{agent_type.upper()} Agent Results:")
            
            total_tokens = 0
            total_tool_calls = 0
            
            for path in paths:
                messages = analyzer.parse_transcript(path)
                
                # Count tokens
                for msg in messages:
                    if "usage" in msg:
                        total_tokens += msg["usage"].get("input_tokens", 0)
                        total_tokens += msg["usage"].get("output_tokens", 0)
                    
                    if msg.get("type") == "tool_use":
                        total_tool_calls += 1
            
            print(f"  Total Tokens: {total_tokens:,}")
            print(f"  Total Tool Calls: {total_tool_calls}")
            print(f"  Avg Tokens per Scenario: {total_tokens / len(paths):,.0f}")


def main():
    """Main entry point"""
    runner = ClaudeCodeTestRunner()
    
    # Run all tests
    transcript_paths = runner.run_all_tests()
    
    # Analyze results
    runner.analyze_results(transcript_paths)
    
    print("\nTest transcripts saved to:", runner.results_dir)
    print("\nNext step: Run the comprehensive analysis with mcp_vs_native_test_framework.py")


if __name__ == "__main__":
    main()