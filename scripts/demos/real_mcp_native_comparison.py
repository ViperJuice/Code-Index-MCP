#!/usr/bin/env python3
"""
Real MCP vs Native Performance Comparison using Claude Code SDK

This script uses the actual Claude Code SDK to launch agents and collect
real performance metrics comparing MCP and native retrieval methods.
"""

import json
import time
import os
import sys
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import shutil
from mcp_server.core.path_utils import PathUtils

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RealQueryMetrics:
    """Metrics from actual Claude Code execution"""
    query: str
    query_type: str
    repository: str
    mode: str  # 'mcp' or 'native'
    
    # Real timing from SDK
    total_time: float
    time_to_first_tool: float
    
    # Real token counts from API
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # Actual tool usage
    tool_calls: List[Dict[str, Any]]
    mcp_tools_used: int
    native_tools_used: int
    
    # File operations
    files_read: int
    partial_reads: int
    full_reads: int
    
    # Results
    results_found: int
    success: bool
    
    # Raw data
    transcript_path: str
    timestamp: str
    error: Optional[str] = None


class ClaudeCodeSDKLauncher:
    """Launches real Claude Code agents using the SDK"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.results_dir = workspace_path / 'test_results' / 'real_mcp_comparison'
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    async def execute_with_mcp(self, query: str, query_type: str, 
                              repo_path: Path, index_path: Path) -> RealQueryMetrics:
        """Execute query using Claude Code with MCP enabled"""
        start_time = time.time()
        session_id = f"mcp_{repo_path.name}_{int(time.time())}"
        
        # Create MCP configuration
        mcp_config = self._create_mcp_config(index_path)
        config_path = self.results_dir / f"{session_id}_mcp.json"
        with open(config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        # Prepare command
        cmd = [
            'claude', '-p',
            f'You have MCP tools available. Use them to answer: {query}',
            '--output-format', 'json',
            '--mcp-config', str(config_path)
        ]
        
        # Execute Claude Code
        try:
            result = await self._run_claude_command(cmd, repo_path)
            metrics = self._parse_claude_output(result, query, query_type, 
                                              repo_path.name, 'mcp', start_time)
            return metrics
        except Exception as e:
            logger.error(f"Error executing MCP query: {e}")
            return self._create_error_metrics(query, query_type, repo_path.name, 
                                            'mcp', str(e), start_time)
    
    async def execute_without_mcp(self, query: str, query_type: str, 
                                 repo_path: Path) -> RealQueryMetrics:
        """Execute query using Claude Code without MCP (native tools only)"""
        start_time = time.time()
        
        # Prepare command - no MCP config means native tools only
        cmd = [
            'claude', '-p',
            f'Use grep, find, and read tools to answer: {query}',
            '--output-format', 'json'
        ]
        
        # Execute Claude Code
        try:
            result = await self._run_claude_command(cmd, repo_path)
            metrics = self._parse_claude_output(result, query, query_type, 
                                              repo_path.name, 'native', start_time)
            return metrics
        except Exception as e:
            logger.error(f"Error executing native query: {e}")
            return self._create_error_metrics(query, query_type, repo_path.name, 
                                            'native', str(e), start_time)
    
    def _create_mcp_config(self, index_path: Path) -> Dict[str, Any]:
        """Create MCP configuration for Claude Code"""
        return {
            "mcpServers": {
                "code-index-mcp": {
                    "command": "python",
                    "args": [
                        str(self.workspace_path / "scripts/cli/mcp_server_cli.py")
                    ],
                    "env": {
                        "PYTHONPATH": str(self.workspace_path),
                        "MCP_INDEX_STORAGE_PATH": str(index_path.parent),
                        "MCP_USE_SIMPLE_DISPATCHER": "false"
                    }
                }
            }
        }
    
    async def _run_claude_command(self, cmd: List[str], cwd: Path) -> Dict[str, Any]:
        """Run Claude Code command and capture output"""
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse JSON output
            if process.returncode == 0:
                output = json.loads(stdout.decode())
                # Save full output
                with open(output_file, 'w') as f:
                    json.dump(output, f, indent=2)
                return {
                    'success': True,
                    'output': output,
                    'transcript_path': output_file
                }
            else:
                return {
                    'success': False,
                    'error': stderr.decode(),
                    'transcript_path': output_file
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transcript_path': output_file
            }
    
    def _parse_claude_output(self, result: Dict[str, Any], query: str, 
                           query_type: str, repo_name: str, mode: str, 
                           start_time: float) -> RealQueryMetrics:
        """Parse real Claude Code output to extract metrics"""
        if not result['success']:
            return self._create_error_metrics(query, query_type, repo_name, 
                                            mode, result['error'], start_time)
        
        output = result['output']
        
        # Extract metrics from actual Claude Code output
        tool_calls = []
        mcp_tools = 0
        native_tools = 0
        files_read = 0
        partial_reads = 0
        full_reads = 0
        time_to_first_tool = None
        
        # Parse messages for tool usage
        for message in output.get('messages', []):
            if 'tool_calls' in message:
                for tool_call in message['tool_calls']:
                    tool_name = tool_call.get('tool', '')
                    tool_calls.append(tool_call)
                    
                    if tool_name.startswith('mcp__'):
                        mcp_tools += 1
                    else:
                        native_tools += 1
                    
                    if time_to_first_tool is None:
                        time_to_first_tool = time.time() - start_time
                    
                    # Count file operations
                    if tool_name == 'Read':
                        files_read += 1
                        args = tool_call.get('arguments', {})
                        if 'offset' in args or 'limit' in args:
                            partial_reads += 1
                        else:
                            full_reads += 1
        
        # Extract token counts from metadata
        metadata = output.get('metadata', {})
        input_tokens = metadata.get('input_tokens', 0)
        output_tokens = metadata.get('output_tokens', 0)
        
        return RealQueryMetrics(
            query=query,
            query_type=query_type,
            repository=repo_name,
            mode=mode,
            total_time=time.time() - start_time,
            time_to_first_tool=time_to_first_tool or 0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            tool_calls=tool_calls,
            mcp_tools_used=mcp_tools,
            native_tools_used=native_tools,
            files_read=files_read,
            partial_reads=partial_reads,
            full_reads=full_reads,
            results_found=len(tool_calls),  # Simplified metric
            success=True,
            transcript_path=result['transcript_path'],
            timestamp=datetime.now().isoformat()
        )
    
    def _create_error_metrics(self, query: str, query_type: str, 
                            repo_name: str, mode: str, error: str, 
                            start_time: float) -> RealQueryMetrics:
        """Create metrics for failed execution"""
        return RealQueryMetrics(
            query=query,
            query_type=query_type,
            repository=repo_name,
            mode=mode,
            total_time=time.time() - start_time,
            time_to_first_tool=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            tool_calls=[],
            mcp_tools_used=0,
            native_tools_used=0,
            files_read=0,
            partial_reads=0,
            full_reads=0,
            results_found=0,
            success=False,
            transcript_path="",
            timestamp=datetime.now().isoformat(),
            error=error
        )


class RealTestOrchestrator:
    """Orchestrates real test execution using Claude Code SDK"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.test_indexes_path = workspace_path / 'test_indexes'
        self.launcher = ClaudeCodeSDKLauncher(workspace_path)
        self.results = []
        
    async def run_comparison_test(self, query: str, query_type: str, 
                                repo_name: str) -> Dict[str, RealQueryMetrics]:
        """Run the same query with both MCP and native modes"""
        repo_path = self.test_indexes_path / repo_name
        
        # Find index file
        index_path = None
        for db_file in repo_path.glob('*.db'):
            if 'bm25' in db_file.name or 'code_index' in db_file.name:
                index_path = db_file
                break
        
        if not index_path:
            logger.error(f"No index found for {repo_name}")
            return {}
        
        results = {}
        
        # Run with MCP
        logger.info(f"Running MCP test: {query}")
        mcp_metrics = await self.launcher.execute_with_mcp(
            query, query_type, repo_path, index_path
        )
        results['mcp'] = mcp_metrics
        self.results.append(mcp_metrics)
        
        # Run without MCP (native)
        logger.info(f"Running native test: {query}")
        native_metrics = await self.launcher.execute_without_mcp(
            query, query_type, repo_path
        )
        results['native'] = native_metrics
        self.results.append(native_metrics)
        
        # Log comparison
        if mcp_metrics.success and native_metrics.success:
            logger.info(f"Performance comparison for '{query}':")
            logger.info(f"  MCP: {mcp_metrics.total_time:.2f}s, "
                       f"{mcp_metrics.total_tokens} tokens")
            logger.info(f"  Native: {native_metrics.total_time:.2f}s, "
                       f"{native_metrics.total_tokens} tokens")
            logger.info(f"  Speed improvement: "
                       f"{native_metrics.total_time / mcp_metrics.total_time:.1f}x")
            logger.info(f"  Token reduction: "
                       f"{(1 - mcp_metrics.total_tokens / native_metrics.total_tokens) * 100:.1f}%")
        
        return results
    
    async def run_test_suite(self, queries: List[Tuple[str, str]], 
                           repo_name: str):
        """Run a suite of queries on a repository"""
        logger.info(f"Starting test suite for {repo_name} with {len(queries)} queries")
        
        for query, query_type in queries:
            try:
                await self.run_comparison_test(query, query_type, repo_name)
                # Add delay to avoid overwhelming the API
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error running query '{query}': {e}")
        
        # Save results
        self.save_results()
    
    def save_results(self):
        """Save all results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = self.launcher.results_dir / f"results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate summary statistics from results"""
        mcp_results = [r for r in self.results if r.mode == 'mcp' and r.success]
        native_results = [r for r in self.results if r.mode == 'native' and r.success]
        
        if not mcp_results or not native_results:
            logger.warning("Insufficient results for summary")
            return
        
        summary = {
            'total_queries': len(self.results) // 2,
            'successful_mcp': len(mcp_results),
            'successful_native': len(native_results),
            'avg_mcp_time': sum(r.total_time for r in mcp_results) / len(mcp_results),
            'avg_native_time': sum(r.total_time for r in native_results) / len(native_results),
            'avg_mcp_tokens': sum(r.total_tokens for r in mcp_results) / len(mcp_results),
            'avg_native_tokens': sum(r.total_tokens for r in native_results) / len(native_results),
            'mcp_tool_usage': sum(r.mcp_tools_used for r in mcp_results),
            'native_tool_usage': sum(r.native_tools_used for r in native_results)
        }
        
        # Calculate improvements
        if summary['avg_native_time'] > 0:
            summary['speed_improvement'] = summary['avg_native_time'] / summary['avg_mcp_time']
        
        if summary['avg_native_tokens'] > 0:
            summary['token_reduction'] = (1 - summary['avg_mcp_tokens'] / summary['avg_native_tokens']) * 100
        
        # Save summary
        summary_file = self.launcher.results_dir / 'summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n=== Test Summary ===")
        print(f"Total queries tested: {summary['total_queries']}")
        print(f"Average MCP time: {summary['avg_mcp_time']:.2f}s")
        print(f"Average Native time: {summary['avg_native_time']:.2f}s")
        print(f"Speed improvement: {summary.get('speed_improvement', 0):.1f}x")
        print(f"Token reduction: {summary.get('token_reduction', 0):.1f}%")


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Real MCP vs Native Performance Comparison')
    parser.add_argument('--repo', type=str, required=True,
                       help='Repository to test (e.g., gin, django)')
    parser.add_argument('--queries', type=int, default=5,
                       help='Number of queries to test')
    parser.add_argument('--workspace', type=Path,
                       default=Path('PathUtils.get_workspace_root()'),
                       help='Workspace path')
    
    args = parser.parse_args()
    
    # Create test queries
    test_queries = [
        ("Find the main class definition", "symbol"),
        ("Search for TODO comments", "content"),
        ("Find all test files", "navigation"),
        ("Show error handling code", "content"),
        ("Find the entry point", "understanding")
    ][:args.queries]
    
    # Run tests
    orchestrator = RealTestOrchestrator(args.workspace)
    await orchestrator.run_test_suite(test_queries, args.repo)


if __name__ == '__main__':
    # Check if Claude Code is available
    try:
        subprocess.run(['claude', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Claude Code CLI not found. Please install it first.")
        print("Visit: https://docs.anthropic.com/en/docs/claude-code/overview")
        sys.exit(1)
    
    asyncio.run(main())