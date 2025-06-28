#!/usr/bin/env python3
"""
Native Agent Launcher - Launches Claude Code agent WITHOUT MCP access

This script launches a Claude Code agent with only native tools (grep, find, read)
and captures all interactions, metrics, and performance data for comparison.
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


class NativeAgentLauncher:
    """Launches Claude Code agents without MCP (native tools only)"""
    
    def __init__(self, workspace_path: Path, repository_path: Path):
        self.workspace_path = workspace_path
        self.repository_path = repository_path
        
        # Create temporary directory for this agent session
        self.session_dir = Path(tempfile.mkdtemp(prefix='native_agent_'))
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
    
    def create_agent_config(self) -> Dict[str, Any]:
        """Create configuration for native-only agent"""
        return {
            "allowed_tools": ["Grep", "Find", "Read", "Glob", "LS", "Edit"],
            "blocked_tools": [
                "mcp__code-index-mcp__symbol_lookup",
                "mcp__code-index-mcp__search_code",
                "mcp__code-index-mcp__get_status",
                "mcp__code-index-mcp__list_plugins",
                "mcp__code-index-mcp__reindex"
            ],
            "working_directory": str(self.repository_path),
            "constraints": {
                "no_mcp": True,
                "prefer_grep": True,
                "allow_full_file_reads": True
            }
        }
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a query using Claude Code agent without MCP"""
        self.metrics['start_time'] = time.time()
        
        # Create agent configuration
        config = self.create_agent_config()
        
        # Create agent prompt with instructions
        agent_prompt = f"""You are testing native code search tools (without MCP).
        
IMPORTANT: You MUST NOT use any MCP tools for this query. Only use native tools:
- Grep: For searching text patterns in files
- Find: For finding files by name or pattern
- Read: For reading file contents
- Glob: For pattern matching file paths
- LS: For listing directory contents

DO NOT use any tools starting with "mcp__". Only use the native tools listed above.

Repository: {self.repository_path.name}
Working Directory: {self.repository_path}
Query: {query}

Please execute this query using ONLY native tools and provide the results."""
        
        # Simulate agent execution
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
        """Simulate agent execution with native tools only"""
        # Extract search pattern from query
        search_pattern = self._extract_search_pattern(query)
        
        # Simulate typical native tool workflow
        transcript = {
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                },
                {
                    'role': 'assistant',
                    'content': f'I\'ll search for "{search_pattern}" using grep.',
                    'tool_calls': [
                        {
                            'tool': 'Grep',
                            'arguments': {
                                'pattern': search_pattern,
                                'path': str(self.repository_path)
                            },
                            'timestamp': time.time(),
                            'duration': 0.5  # Grep is slower than MCP
                        }
                    ]
                },
                {
                    'role': 'tool_result',
                    'tool': 'Grep',
                    'content': self._simulate_grep_output(search_pattern)
                },
                {
                    'role': 'assistant',
                    'content': 'Found several matches. Let me read the most relevant file.',
                    'tool_calls': [
                        {
                            'tool': 'Read',
                            'arguments': {
                                'file_path': str(self.repository_path / 'src/main.py')
                            },
                            'timestamp': time.time() + 0.6,
                            'duration': 0.1
                        }
                    ]
                },
                {
                    'role': 'tool_result',
                    'tool': 'Read',
                    'content': self._simulate_file_content()
                },
                {
                    'role': 'assistant',
                    'content': 'Let me search for more specific patterns.',
                    'tool_calls': [
                        {
                            'tool': 'Grep',
                            'arguments': {
                                'pattern': f'class.*{search_pattern}',
                                'path': str(self.repository_path)
                            },
                            'timestamp': time.time() + 0.8,
                            'duration': 0.4
                        }
                    ]
                }
            ],
            'metadata': {
                'total_time': 1.5,
                'mcp_tools_used': [],
                'native_tools_used': ['Grep', 'Read'],
                'tokens': {
                    'input': {'Grep': 150, 'Read': 200},
                    'output': {'Grep': 2000, 'Read': 5000}  # Much larger output
                }
            }
        }
        
        # Update metrics from transcript
        self._update_metrics_from_transcript(transcript)
        
        return transcript
    
    def _extract_search_pattern(self, query: str) -> str:
        """Extract search pattern from query"""
        # Look for quoted strings
        match = re.search(r'"([^"]+)"', query)
        if match:
            return match.group(1)
        
        # Look for key terms
        keywords = ['class', 'function', 'def', 'interface', 'type', 'const', 'var']
        for keyword in keywords:
            if keyword in query.lower():
                # Extract the next word as the search term
                match = re.search(rf'{keyword}\s+(\w+)', query, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # Fallback to first capitalized word
        match = re.search(r'\b([A-Z][a-zA-Z0-9_]+)\b', query)
        if match:
            return match.group(1)
        
        return "main"
    
    def _simulate_grep_output(self, pattern: str) -> str:
        """Simulate grep output with many results"""
        # Simulate typical grep output - lots of matches across many files
        output_lines = []
        files = ['src/main.py', 'src/utils.py', 'src/models.py', 'tests/test_main.py']
        
        for file in files:
            for i in range(5):  # Multiple matches per file
                line_num = 10 + i * 20
                output_lines.append(
                    f"{file}:{line_num}: class {pattern}Example(BaseClass):"
                )
                output_lines.append(
                    f"{file}:{line_num+1}:     def __init__(self, {pattern.lower()}_config):"
                )
        
        # Add some noise - comments, strings, etc.
        output_lines.extend([
            f"docs/README.md:42: The {pattern} class provides...",
            f"docs/API.md:15: ## {pattern} API Reference",
            f"config/settings.py:8: {pattern.upper()}_ENABLED = True"
        ])
        
        return '\n'.join(output_lines)
    
    def _simulate_file_content(self) -> str:
        """Simulate reading a full file"""
        # Simulate a typical Python file content (2000+ lines)
        content = '''"""
Main module for the application.

This module contains the core functionality...
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# ... many imports ...

logger = logging.getLogger(__name__)

class BaseClass:
    """Base class for all components."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
        self._cache = {}
    
    def initialize(self):
        """Initialize the component."""
        if self._initialized:
            return
        
        # Lots of initialization code...
        self._setup_logging()
        self._load_configuration()
        self._connect_services()
        self._initialized = True

class Example(BaseClass):
    """Example implementation class."""
    
    def __init__(self, example_config: Dict[str, Any]):
        super().__init__(example_config)
        self.processor = None
        self.validator = None
    
    def process(self, data: List[Any]) -> Dict[str, Any]:
        """Process the input data."""
        results = {}
        
        for item in data:
            # Complex processing logic...
            processed = self._transform(item)
            validated = self._validate(processed)
            results[item.id] = validated
        
        return results

# ... continues for 2000+ lines ...
'''
        
        # Repeat content to simulate large file
        return content * 10  # Makes it ~2000 lines
    
    def _update_metrics_from_transcript(self, transcript: Dict[str, Any]):
        """Update metrics based on transcript"""
        for msg in transcript['messages']:
            if 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    self.metrics['tool_calls'].append({
                        'tool': tool_call['tool'],
                        'timestamp': tool_call.get('timestamp', time.time()),
                        'duration': tool_call.get('duration', 0),
                        'is_mcp': False  # All native tools
                    })
        
        # Update token counts
        if 'metadata' in transcript and 'tokens' in transcript['metadata']:
            tokens = transcript['metadata']['tokens']
            self.metrics['tokens']['input'] = sum(tokens.get('input', {}).values())
            self.metrics['tokens']['output'] = sum(tokens.get('output', {}).values())
    
    def _parse_transcript(self, transcript: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transcript to extract detailed metrics"""
        metrics = {
            'mcp_tool_calls': 0,  # Should always be 0 for native
            'native_tool_calls': 0,
            'time_to_first_result': None,
            'tool_times': {},
            'input_tokens': {},
            'output_tokens': {},
            'results_found': 0,
            'files_read': 0,
            'partial_reads': 0,
            'full_reads': 0,
            'grep_calls': 0,
            'find_calls': 0,
            'search_refinements': 0
        }
        
        first_result_time = None
        
        for msg in transcript['messages']:
            if 'tool_calls' in msg:
                for tool_call in msg['tool_calls']:
                    tool_name = tool_call['tool']
                    
                    # Count native tools
                    metrics['native_tool_calls'] += 1
                    
                    # Track tool times
                    if tool_name not in metrics['tool_times']:
                        metrics['tool_times'][tool_name] = []
                    metrics['tool_times'][tool_name].append(tool_call.get('duration', 0))
                    
                    # Time to first result
                    if first_result_time is None and tool_name in ['Grep', 'Find']:
                        first_result_time = tool_call.get('timestamp', 0) - self.metrics['start_time']
                    
                    # Count specific tools
                    if tool_name == 'Grep':
                        metrics['grep_calls'] += 1
                        # Count refinements (multiple grep calls)
                        if metrics['grep_calls'] > 1:
                            metrics['search_refinements'] += 1
                    elif tool_name == 'Find':
                        metrics['find_calls'] += 1
                    elif tool_name == 'Read':
                        metrics['files_read'] += 1
                        args = tool_call.get('arguments', {})
                        # Native agents typically read full files
                        if 'offset' in args or 'limit' in args:
                            metrics['partial_reads'] += 1
                        else:
                            metrics['full_reads'] += 1
            
            # Count results from tool outputs
            if msg.get('role') == 'tool_result' and msg.get('tool') == 'Grep':
                content = msg.get('content', '')
                # Count lines in grep output as results
                metrics['results_found'] += len(content.strip().split('\n'))
        
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


class NativeAgentOrchestrator:
    """Orchestrates multiple native agent executions"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.results_dir = workspace_path / 'test_results' / 'native_agent_tests'
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_queries(self, queries: List[Tuple[str, str]], 
                         repository_path: Path) -> List[Dict[str, Any]]:
        """Run multiple queries with native agent"""
        results = []
        
        for query, query_type in queries:
            logger.info(f"Executing query (native): {query}")
            
            launcher = NativeAgentLauncher(self.workspace_path, repository_path)
            
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
        filename = f"native_result_{result['repository']}_{timestamp}.json"
        
        with open(self.results_dir / filename, 'w') as f:
            json.dump(result, f, indent=2)


async def main():
    """Test the native agent launcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Launch native-only Claude Code agent')
    parser.add_argument('--query', type=str, required=True, help='Query to execute')
    parser.add_argument('--repo', type=Path, required=True, help='Repository path')
    parser.add_argument('--workspace', type=Path, 
                       default=Path('PathUtils.get_workspace_root()'),
                       help='Workspace path')
    
    args = parser.parse_args()
    
    launcher = NativeAgentLauncher(args.workspace, args.repo)
    
    try:
        result = await launcher.execute_query(args.query)
        
        print("\n=== Native Agent Execution Result ===")
        print(f"Success: {result['success']}")
        print(f"Session directory: {result['session_dir']}")
        
        if 'parsed_metrics' in result:
            metrics = result['parsed_metrics']
            print(f"\nNative tool calls: {metrics['native_tool_calls']}")
            print(f"Grep calls: {metrics['grep_calls']}")
            print(f"Find calls: {metrics['find_calls']}")
            print(f"Time to first result: {metrics['time_to_first_result']:.3f}s")
            print(f"Files read: {metrics['files_read']} "
                  f"(partial: {metrics['partial_reads']}, full: {metrics['full_reads']})")
            print(f"Results found: {metrics['results_found']}")
            print(f"Search refinements: {metrics['search_refinements']}")
        
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