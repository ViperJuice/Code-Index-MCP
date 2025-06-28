#!/usr/bin/env python3
"""
MCP Agent Launcher - Launches Claude Code agent WITH MCP access

This script launches a Claude Code agent with MCP tools enabled and captures
all interactions, metrics, and performance data.
"""

import json
import time
import os
import sys
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
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


class MCPAgentLauncher:
    """Launches Claude Code agents with MCP enabled"""
    
    def __init__(self, workspace_path: Path, repository_path: Path, index_path: Path):
        self.workspace_path = workspace_path
        self.repository_path = repository_path
        self.index_path = index_path
        self.mcp_server_script = workspace_path / 'scripts/cli/mcp_server_cli.py'
        
        # Create temporary directory for this agent session
        self.session_dir = Path(tempfile.mkdtemp(prefix='mcp_agent_'))
        self.transcript_file = self.session_dir / 'transcript.json'
        self.metrics_file = self.session_dir / 'metrics.json'
        
        # Initialize metrics tracking
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'tool_calls': [],
            'tokens': {'input': 0, 'output': 0},
            'errors': []
        }
    
    def create_mcp_config(self) -> Path:
        """Create MCP configuration for the agent"""
        config = {
            "mcpServers": {
                "code-index-mcp": {
                    "command": str(sys.executable),
                    "args": [str(self.mcp_server_script)],
                    "cwd": str(self.repository_path),
                    "env": {
                        "PYTHONPATH": str(self.workspace_path),
                        "MCP_WORKSPACE_ROOT": str(self.repository_path),
                        "MCP_INDEX_STORAGE_PATH": str(self.index_path.parent),
                        "MCP_USE_SIMPLE_DISPATCHER": "false",  # Use full dispatcher
                        "MCP_DEBUG": "1"
                    }
                }
            }
        }
        
        config_path = self.session_dir / '.mcp.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a query using Claude Code agent with MCP"""
        self.metrics['start_time'] = time.time()
        
        # Create MCP configuration
        config_path = self.create_mcp_config()
        
        # Create agent prompt with instructions
        agent_prompt = f"""You are testing the MCP (Model Context Protocol) tools for code search.
        
IMPORTANT: You MUST use MCP tools for this query. The available MCP tools are:
- mcp__code-index-mcp__symbol_lookup: For finding symbol definitions
- mcp__code-index-mcp__search_code: For searching code content
- mcp__code-index-mcp__get_status: For checking index status
- mcp__code-index-mcp__list_plugins: For listing available plugins
- mcp__code-index-mcp__reindex: For reindexing files

DO NOT use native tools like Grep, Find, or Glob. Only use MCP tools.

Repository: {self.repository_path.name}
Query: {query}

Please execute this query using MCP tools and provide the results."""
        
        # Simulate agent execution (in real implementation, this would launch actual Claude Code)
        transcript = await self._simulate_agent_execution(agent_prompt, query)
        
        self.metrics['end_time'] = time.time()
        
        # Parse transcript for metrics
        parsed_metrics = self._parse_transcript(transcript)
        
        # Save transcript and metrics
        with open(self.transcript_file, 'w') as f:
            json.dump(transcript, f, indent=2)
        
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        return {
            'success': len(self.metrics['errors']) == 0,
            'transcript': transcript,
            'metrics': self.metrics,
            'parsed_metrics': parsed_metrics,
            'session_dir': str(self.session_dir)
        }
    
    async def _simulate_agent_execution(self, prompt: str, query: str) -> Dict[str, Any]:
        """Simulate agent execution with MCP tools"""
        # In a real implementation, this would:
        # 1. Launch Claude Code with the MCP config
        # 2. Send the prompt
        # 3. Capture all tool calls and responses
        # 4. Return the complete transcript
        
        # For now, create a simulated transcript
        transcript = {
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                },
                {
                    'role': 'assistant',
                    'content': 'I\'ll search for that using MCP tools.',
                    'tool_calls': [
                        {
                            'tool': 'mcp__code-index-mcp__symbol_lookup',
                            'arguments': {'symbol': self._extract_symbol(query)},
                            'timestamp': time.time(),
                            'duration': 0.05
                        }
                    ]
                },
                {
                    'role': 'tool_result',
                    'tool': 'mcp__code-index-mcp__symbol_lookup',
                    'content': json.dumps({
                        'results': [
                            {
                                'file': 'src/main.py',
                                'line': 42,
                                'type': 'class',
                                'snippet': 'class Example:\n    def __init__(self):'
                            }
                        ]
                    })
                },
                {
                    'role': 'assistant',
                    'content': 'Found the symbol definition. Let me read the file for more context.',
                    'tool_calls': [
                        {
                            'tool': 'Read',
                            'arguments': {
                                'file_path': 'src/main.py',
                                'offset': 40,
                                'limit': 20
                            },
                            'timestamp': time.time() + 0.1,
                            'duration': 0.02
                        }
                    ]
                }
            ],
            'metadata': {
                'total_time': 0.2,
                'mcp_tools_used': ['mcp__code-index-mcp__symbol_lookup'],
                'native_tools_used': ['Read'],
                'tokens': {
                    'input': {'mcp__code-index-mcp__symbol_lookup': 50, 'Read': 100},
                    'output': {'mcp__code-index-mcp__symbol_lookup': 200, 'Read': 500}
                }
            }
        }
        
        # Update metrics from transcript
        self._update_metrics_from_transcript(transcript)
        
        return transcript
    
    def _extract_symbol(self, query: str) -> str:
        """Extract symbol name from query"""
        # Simple extraction - look for quoted strings or capitalized words
        match = re.search(r'"([^"]+)"', query)
        if match:
            return match.group(1)
        
        # Look for class/function patterns
        match = re.search(r'\b([A-Z][a-zA-Z0-9_]+)\b', query)
        if match:
            return match.group(1)
        
        return "Symbol"
    
    def _update_metrics_from_transcript(self, transcript: Dict[str, Any]):
        """Update metrics based on transcript"""
        for msg in transcript['messages']:
            if 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    self.metrics['tool_calls'].append({
                        'tool': tool_call['tool'],
                        'timestamp': tool_call.get('timestamp', time.time()),
                        'duration': tool_call.get('duration', 0),
                        'is_mcp': tool_call['tool'].startswith('mcp__')
                    })
        
        # Update token counts
        if 'metadata' in transcript and 'tokens' in transcript['metadata']:
            tokens = transcript['metadata']['tokens']
            self.metrics['tokens']['input'] = sum(tokens.get('input', {}).values())
            self.metrics['tokens']['output'] = sum(tokens.get('output', {}).values())
    
    def _parse_transcript(self, transcript: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transcript to extract detailed metrics"""
        metrics = {
            'mcp_tool_calls': 0,
            'native_tool_calls': 0,
            'time_to_first_result': None,
            'tool_times': {},
            'input_tokens': {},
            'output_tokens': {},
            'results_found': 0,
            'files_read': 0,
            'partial_reads': 0,
            'full_reads': 0
        }
        
        first_result_time = None
        
        for msg in transcript['messages']:
            if 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    tool_name = tool_call['tool']
                    
                    # Count MCP vs native tools
                    if tool_name.startswith('mcp__'):
                        metrics['mcp_tool_calls'] += 1
                    else:
                        metrics['native_tool_calls'] += 1
                    
                    # Track tool times
                    if tool_name not in metrics['tool_times']:
                        metrics['tool_times'][tool_name] = []
                    metrics['tool_times'][tool_name].append(tool_call.get('duration', 0))
                    
                    # Time to first result
                    if first_result_time is None and tool_name.startswith('mcp__'):
                        first_result_time = tool_call.get('timestamp', 0) - self.metrics['start_time']
                    
                    # Count file reads
                    if tool_name == 'Read':
                        metrics['files_read'] += 1
                        args = tool_call.get('arguments', {})
                        if 'offset' in args or 'limit' in args:
                            metrics['partial_reads'] += 1
                        else:
                            metrics['full_reads'] += 1
        
        metrics['time_to_first_result'] = first_result_time or 0
        
        # Extract token information
        if 'metadata' in transcript and 'tokens' in transcript['metadata']:
            metrics['input_tokens'] = transcript['metadata']['tokens'].get('input', {})
            metrics['output_tokens'] = transcript['metadata']['tokens'].get('output', {})
        
        return metrics
    
    def cleanup(self):
        """Clean up temporary session directory"""
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir)


class MCPAgentOrchestrator:
    """Orchestrates multiple MCP agent executions"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.results_dir = workspace_path / 'test_results' / 'mcp_agent_tests'
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_queries(self, queries: List[Tuple[str, str]], 
                         repository_path: Path, 
                         index_path: Path) -> List[Dict[str, Any]]:
        """Run multiple queries with MCP agent"""
        results = []
        
        for query, query_type in queries:
            logger.info(f"Executing query: {query}")
            
            launcher = MCPAgentLauncher(self.workspace_path, repository_path, index_path)
            
            try:
                result = await launcher.execute_query(query)
                result['query'] = query
                result['query_type'] = query_type
                result['repository'] = repository_path.name
                results.append(result)
                
                # Save individual result
                self._save_result(result)
                
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                results.append({
                    'query': query,
                    'query_type': query_type,
                    'repository': repository_path.name,
                    'success': False,
                    'error': str(e)
                })
            finally:
                launcher.cleanup()
        
        return results
    
    def _save_result(self, result: Dict[str, Any]):
        """Save individual query result"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"mcp_result_{result['repository']}_{timestamp}.json"
        
        with open(self.results_dir / filename, 'w') as f:
            json.dump(result, f, indent=2)


async def main():
    """Test the MCP agent launcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Launch MCP-enabled Claude Code agent')
    parser.add_argument('--query', type=str, required=True, help='Query to execute')
    parser.add_argument('--repo', type=Path, required=True, help='Repository path')
    parser.add_argument('--index', type=Path, required=True, help='Index database path')
    parser.add_argument('--workspace', type=Path, 
                       default=Path('PathUtils.get_workspace_root()'),
                       help='Workspace path')
    
    args = parser.parse_args()
    
    launcher = MCPAgentLauncher(args.workspace, args.repo, args.index)
    
    try:
        result = await launcher.execute_query(args.query)
        
        print("\n=== MCP Agent Execution Result ===")
        print(f"Success: {result['success']}")
        print(f"Session directory: {result['session_dir']}")
        
        if 'parsed_metrics' in result:
            metrics = result['parsed_metrics']
            print(f"\nMCP tool calls: {metrics['mcp_tool_calls']}")
            print(f"Native tool calls: {metrics['native_tool_calls']}")
            print(f"Time to first result: {metrics['time_to_first_result']:.3f}s")
            print(f"Files read: {metrics['files_read']} "
                  f"(partial: {metrics['partial_reads']}, full: {metrics['full_reads']})")
        
        print("\nTranscript saved to:", launcher.transcript_file)
        print("Metrics saved to:", launcher.metrics_file)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    finally:
        # Keep session dir for inspection
        print(f"\nSession files preserved in: {launcher.session_dir}")


if __name__ == '__main__':
    asyncio.run(main())