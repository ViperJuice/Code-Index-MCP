#!/usr/bin/env python3
"""
Enhanced Agent Launcher with Granular Token Tracking
Supports both MCP and Native Claude Code agents with detailed token analysis.
"""

import json
import time
import os
import sys
import asyncio
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import tempfile
import shutil
from dataclasses import dataclass, asdict
import uuid

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TokenBreakdown:
    """Detailed token breakdown for a single interaction"""
    interaction_id: str
    timestamp: datetime
    
    # Input tokens
    user_prompt: int
    context_history: int
    tool_results: int
    file_content: int
    total_input: int
    
    # Output tokens
    reasoning: int
    tool_calls: int
    code_generation: int
    explanations: int
    total_output: int
    
    # Efficiency metrics
    tokens_per_result: float
    context_utilization: float
    generation_efficiency: float


@dataclass
class QueryMetrics:
    """Comprehensive metrics for a single query execution"""
    query_id: str
    query_text: str
    approach: str  # 'mcp' or 'native'
    start_time: datetime
    end_time: datetime
    success: bool
    
    # Token tracking
    token_breakdown: TokenBreakdown
    
    # Tool usage
    tools_used: List[str]
    tool_call_count: int
    file_reads: List[str]
    file_writes: List[str]
    
    # Performance
    response_time_ms: float
    accuracy_score: Optional[float] = None
    

class EnhancedAgentLauncher:
    """Enhanced launcher for Claude Code agents with comprehensive token tracking"""
    
    def __init__(self, agent_type: str, workspace_path: Path, test_session_id: str):
        """
        Initialize the enhanced agent launcher.
        
        Args:
            agent_type: 'mcp' or 'native'
            workspace_path: Path to the workspace (worktree)
            test_session_id: Unique identifier for this test session
        """
        self.agent_type = agent_type
        self.workspace_path = workspace_path
        self.test_session_id = test_session_id
        
        # Create session directory
        self.session_dir = Path(tempfile.mkdtemp(prefix=f'{agent_type}_agent_{test_session_id}_'))
        self.transcript_dir = self.session_dir / 'transcripts'
        self.transcript_dir.mkdir(exist_ok=True)
        
        # File paths
        self.metrics_file = self.session_dir / 'metrics.jsonl'
        self.token_analysis_file = self.session_dir / 'token_analysis.jsonl'
        self.session_summary_file = self.session_dir / 'session_summary.json'
        
        # Initialize tracking
        self.query_metrics: List[QueryMetrics] = []
        self.total_tokens = {'input': 0, 'output': 0}
        self.interaction_count = 0
        
        logger.info(f"Initialized {agent_type} agent launcher for session {test_session_id}")
        logger.info(f"Session directory: {self.session_dir}")
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text using simple heuristic.
        More accurate methods would use tiktoken or similar.
        """
        # Rough estimate: ~4 characters per token for code/technical text
        return max(1, len(text) // 4)
    
    def analyze_claude_transcript(self, transcript_content: str) -> List[TokenBreakdown]:
        """
        Analyze Claude Code transcript to extract granular token usage.
        
        Args:
            transcript_content: Raw transcript content
            
        Returns:
            List of TokenBreakdown objects for each interaction
        """
        breakdowns = []
        
        # Parse the transcript (assuming JSONL format)
        lines = transcript_content.strip().split('\n')
        
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
                
                if entry.get('type') == 'message':
                    interaction_id = str(uuid.uuid4())
                    timestamp = datetime.fromisoformat(entry.get('timestamp', datetime.now().isoformat()))
                    
                    # Extract content
                    content = entry.get('content', {})
                    
                    # Analyze input tokens
                    user_prompt = self.estimate_token_count(content.get('prompt', ''))
                    context_history = self.estimate_token_count(content.get('context', ''))
                    tool_results = self.estimate_token_count(str(content.get('tool_results', [])))
                    file_content = self.estimate_token_count(content.get('file_content', ''))
                    
                    total_input = user_prompt + context_history + tool_results + file_content
                    
                    # Analyze output tokens
                    response = content.get('response', {})
                    reasoning = self.estimate_token_count(response.get('reasoning', ''))
                    tool_calls = self.estimate_token_count(str(response.get('tool_calls', [])))
                    code_generation = self.estimate_token_count(response.get('code', ''))
                    explanations = self.estimate_token_count(response.get('explanation', ''))
                    
                    total_output = reasoning + tool_calls + code_generation + explanations
                    
                    # Calculate efficiency metrics
                    tokens_per_result = total_input + total_output
                    context_utilization = context_history / max(1, total_input)
                    generation_efficiency = total_output / max(1, total_input)
                    
                    breakdown = TokenBreakdown(
                        interaction_id=interaction_id,
                        timestamp=timestamp,
                        user_prompt=user_prompt,
                        context_history=context_history,
                        tool_results=tool_results,
                        file_content=file_content,
                        total_input=total_input,
                        reasoning=reasoning,
                        tool_calls=tool_calls,
                        code_generation=code_generation,
                        explanations=explanations,
                        total_output=total_output,
                        tokens_per_result=tokens_per_result,
                        context_utilization=context_utilization,
                        generation_efficiency=generation_efficiency
                    )
                    
                    breakdowns.append(breakdown)
                    
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse transcript line {i}: {line[:100]}...")
                continue
        
        return breakdowns
    
    def execute_query(self, query: str, query_id: str, timeout: int = 120) -> QueryMetrics:
        """
        Execute a single query using Claude Code and capture detailed metrics.
        
        Args:
            query: The query to execute
            query_id: Unique identifier for this query
            timeout: Timeout in seconds
            
        Returns:
            QueryMetrics object with comprehensive analysis
        """
        start_time = datetime.now()
        logger.info(f"Executing query {query_id}: {query[:100]}...")
        
        # Prepare Claude Code command
        if self.agent_type == 'mcp':
            # Use MCP-enabled worktree
            cwd = self.workspace_path
            cmd = ['claude', '--', query]
        else:
            # Use native-only worktree
            cwd = self.workspace_path
            cmd = ['claude', '--', query]
        
        # Execute query
        success = False
        tools_used = []
        tool_call_count = 0
        file_reads = []
        file_writes = []
        transcript_content = ""
        
        try:
            # Run Claude Code with the query
            result = subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
                env={**os.environ, 'CLAUDE_PROJECT_DIR': str(self.transcript_dir)}
            )
            
            success = result.returncode == 0
            
            # Extract transcript content (this would need to be adapted based on actual Claude Code behavior)
            transcript_content = result.stdout + result.stderr
            
            # Analyze tools used (simplified analysis)
            if 'mcp__code-index-mcp__search_code' in transcript_content:
                tools_used.append('mcp_search_code')
                tool_call_count += transcript_content.count('mcp__code-index-mcp__search_code')
            
            if 'mcp__code-index-mcp__symbol_lookup' in transcript_content:
                tools_used.append('mcp_symbol_lookup')
                tool_call_count += transcript_content.count('mcp__code-index-mcp__symbol_lookup')
            
            if 'Read(' in transcript_content:
                tools_used.append('read')
                file_reads = re.findall(r'Read\(["\']([^"\']+)["\']', transcript_content)
                tool_call_count += len(file_reads)
            
            if 'Grep(' in transcript_content:
                tools_used.append('grep')
                tool_call_count += transcript_content.count('Grep(')
            
            if 'Edit(' in transcript_content:
                tools_used.append('edit')
                file_writes = re.findall(r'Edit\(["\']([^"\']+)["\']', transcript_content)
                tool_call_count += len(file_writes)
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Query {query_id} timed out after {timeout}s")
            success = False
        except Exception as e:
            logger.error(f"Query {query_id} failed: {e}")
            success = False
        
        end_time = datetime.now()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Analyze token breakdown
        token_breakdowns = self.analyze_claude_transcript(transcript_content)
        
        # Use the first breakdown or create a default one
        if token_breakdowns:
            token_breakdown = token_breakdowns[0]
        else:
            # Create default breakdown
            estimated_tokens = self.estimate_token_count(transcript_content)
            token_breakdown = TokenBreakdown(
                interaction_id=str(uuid.uuid4()),
                timestamp=start_time,
                user_prompt=self.estimate_token_count(query),
                context_history=0,
                tool_results=estimated_tokens // 4,
                file_content=estimated_tokens // 2,
                total_input=estimated_tokens,
                reasoning=estimated_tokens // 8,
                tool_calls=estimated_tokens // 10,
                code_generation=estimated_tokens // 6,
                explanations=estimated_tokens // 8,
                total_output=estimated_tokens // 4,
                tokens_per_result=estimated_tokens * 1.25,
                context_utilization=0.5,
                generation_efficiency=0.25
            )
        
        # Create QueryMetrics
        metrics = QueryMetrics(
            query_id=query_id,
            query_text=query,
            approach=self.agent_type,
            start_time=start_time,
            end_time=end_time,
            success=success,
            token_breakdown=token_breakdown,
            tools_used=tools_used,
            tool_call_count=tool_call_count,
            file_reads=file_reads,
            file_writes=file_writes,
            response_time_ms=response_time_ms
        )
        
        # Save metrics
        self.query_metrics.append(metrics)
        self.total_tokens['input'] += token_breakdown.total_input
        self.total_tokens['output'] += token_breakdown.total_output
        self.interaction_count += 1
        
        # Write to JSONL files
        self._save_metrics(metrics)
        
        logger.info(f"Query {query_id} completed: {success}, {response_time_ms:.0f}ms, "
                   f"{token_breakdown.total_input + token_breakdown.total_output} tokens")
        
        return metrics
    
    def _save_metrics(self, metrics: QueryMetrics):
        """Save metrics to JSONL files"""
        # Save query metrics
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(asdict(metrics), default=str) + '\n')
        
        # Save token analysis
        with open(self.token_analysis_file, 'a') as f:
            f.write(json.dumps(asdict(metrics.token_breakdown), default=str) + '\n')
    
    def generate_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session summary"""
        if not self.query_metrics:
            return {}
        
        total_queries = len(self.query_metrics)
        successful_queries = sum(1 for m in self.query_metrics if m.success)
        success_rate = successful_queries / total_queries if total_queries > 0 else 0
        
        avg_response_time = sum(m.response_time_ms for m in self.query_metrics) / total_queries
        avg_input_tokens = sum(m.token_breakdown.total_input for m in self.query_metrics) / total_queries
        avg_output_tokens = sum(m.token_breakdown.total_output for m in self.query_metrics) / total_queries
        
        # Tool usage analysis
        all_tools = []
        for m in self.query_metrics:
            all_tools.extend(m.tools_used)
        
        tool_usage = {}
        for tool in set(all_tools):
            tool_usage[tool] = all_tools.count(tool)
        
        summary = {
            'session_id': self.test_session_id,
            'agent_type': self.agent_type,
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'success_rate': success_rate,
            'avg_response_time_ms': avg_response_time,
            'total_tokens': self.total_tokens,
            'avg_input_tokens': avg_input_tokens,
            'avg_output_tokens': avg_output_tokens,
            'tool_usage': tool_usage,
            'queries': [asdict(m) for m in self.query_metrics]
        }
        
        # Save summary
        with open(self.session_summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return summary
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.session_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup session directory: {e}")


def main():
    """Main entry point for testing the enhanced launcher"""
    if len(sys.argv) < 3:
        print("Usage: python enhanced_agent_launcher.py <agent_type> <workspace_path> [test_session_id]")
        print("agent_type: 'mcp' or 'native'")
        sys.exit(1)
    
    agent_type = sys.argv[1]
    workspace_path = Path(sys.argv[2])
    test_session_id = sys.argv[3] if len(sys.argv) > 3 else f"test_{int(time.time())}"
    
    launcher = EnhancedAgentLauncher(agent_type, workspace_path, test_session_id)
    
    # Example test queries
    test_queries = [
        "Find the BM25Indexer class definition",
        "Search for all functions containing 'search' in their name",
        "Look for error handling patterns in the dispatcher",
    ]
    
    try:
        for i, query in enumerate(test_queries):
            query_id = f"test_query_{i+1:03d}"
            metrics = launcher.execute_query(query, query_id)
            print(f"Query {query_id}: {metrics.success}, {metrics.response_time_ms:.0f}ms")
        
        summary = launcher.generate_session_summary()
        print(f"\nSession Summary:")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Avg Response Time: {summary['avg_response_time_ms']:.0f}ms")
        print(f"Total Tokens: {summary['total_tokens']}")
        
    finally:
        launcher.cleanup()


if __name__ == "__main__":
    main()