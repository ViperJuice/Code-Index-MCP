#!/usr/bin/env python3
"""
Comprehensive MCP vs Native Comparison Test Runner
Executes parallel Claude Code agents with identical queries and compares token efficiency.
"""

import json
import asyncio
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging
import concurrent.futures
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.enhanced_agent_launcher import EnhancedAgentLauncher, QueryMetrics
from scripts.analyze_real_claude_transcripts import RealTranscriptAnalyzer, generate_comprehensive_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspaces/Code-Index-MCP/mcp_vs_native_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MCPVsNativeTestRunner:
    """Orchestrates comprehensive MCP vs Native performance testing."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.mcp_worktree = workspace_root / "testing-env/worktree-mcp"
        self.native_worktree = workspace_root / "testing-env/worktree-native"
        self.test_queries_file = workspace_root / "test_queries.json"
        self.results_dir = workspace_root / "comprehensive_test_results"
        
        # Create results directory
        self.results_dir.mkdir(exist_ok=True)
        
        # Test session ID
        self.session_id = f"mcp_vs_native_{int(time.time())}"
        
        # Initialize analyzers
        self.transcript_analyzer = RealTranscriptAnalyzer()
        
        # Results storage
        self.mcp_results: List[QueryMetrics] = []
        self.native_results: List[QueryMetrics] = []
        
        logger.info(f"Initialized test runner for session {self.session_id}")
        logger.info(f"MCP Worktree: {self.mcp_worktree}")
        logger.info(f"Native Worktree: {self.native_worktree}")
    
    def validate_setup(self) -> bool:
        """Validate that all required components are set up correctly."""
        logger.info("Validating test setup...")
        
        errors = []
        
        # Check worktrees exist
        if not self.mcp_worktree.exists():
            errors.append(f"MCP worktree not found: {self.mcp_worktree}")
        
        if not self.native_worktree.exists():
            errors.append(f"Native worktree not found: {self.native_worktree}")
        
        # Check MCP configuration
        mcp_config = self.mcp_worktree / ".mcp.json"
        if not mcp_config.exists():
            errors.append(f"MCP configuration not found: {mcp_config}")
        
        # Check native worktree has no MCP config
        native_config = self.native_worktree / ".mcp.json"
        if native_config.exists():
            logger.warning(f"Native worktree has MCP config: {native_config}")
            # Rename it to disable MCP
            native_config.rename(native_config.with_suffix('.json.disabled'))
        
        # Check test queries file
        if not self.test_queries_file.exists():
            errors.append(f"Test queries file not found: {self.test_queries_file}")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        logger.info("Test setup validation passed")
        return True
    
    def load_test_queries(self) -> Dict[str, Any]:
        """Load test queries from file."""
        with open(self.test_queries_file, 'r') as f:
            return json.load(f)
    
    async def execute_query_pair(self, query_data: Dict[str, Any], category: str) -> Tuple[QueryMetrics, QueryMetrics]:
        """Execute a query on both MCP and Native agents in parallel."""
        query_id = query_data['id']
        query_text = query_data['text']
        
        logger.info(f"Executing query pair {query_id}: {query_text[:100]}...")
        
        # Create agent launchers
        mcp_launcher = EnhancedAgentLauncher(
            agent_type="mcp",
            workspace_path=self.mcp_worktree,
            test_session_id=f"{self.session_id}_{query_id}_mcp"
        )
        
        native_launcher = EnhancedAgentLauncher(
            agent_type="native",
            workspace_path=self.native_worktree,
            test_session_id=f"{self.session_id}_{query_id}_native"
        )
        
        # Execute queries concurrently
        try:
            # Use asyncio.gather for true parallel execution
            mcp_task = asyncio.create_task(self._execute_single_query(mcp_launcher, query_text, f"{query_id}_mcp"))
            native_task = asyncio.create_task(self._execute_single_query(native_launcher, query_text, f"{query_id}_native"))
            
            mcp_result, native_result = await asyncio.gather(mcp_task, native_task)
            
            # Add category and complexity metadata
            mcp_result.query_id = f"{category}_{mcp_result.query_id}"
            native_result.query_id = f"{category}_{native_result.query_id}"
            
            logger.info(f"Query {query_id} completed - MCP: {mcp_result.success}, Native: {native_result.success}")
            
            return mcp_result, native_result
            
        except Exception as e:
            logger.error(f"Error executing query pair {query_id}: {e}")
            raise
        finally:
            # Clean up launchers
            mcp_launcher.cleanup()
            native_launcher.cleanup()
    
    async def _execute_single_query(self, launcher: EnhancedAgentLauncher, query: str, query_id: str) -> QueryMetrics:
        """Execute a single query using the enhanced agent launcher."""
        return await asyncio.to_thread(launcher.execute_query, query, query_id, timeout=120)
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the comprehensive MCP vs Native comparison test."""
        logger.info("Starting comprehensive MCP vs Native test...")
        
        # Validate setup
        if not self.validate_setup():
            raise RuntimeError("Test setup validation failed")
        
        # Load queries
        test_data = self.load_test_queries()
        query_categories = test_data['query_categories']
        
        # Execute all query pairs
        all_results = []
        
        for category_name, category_data in query_categories.items():
            logger.info(f"Testing category: {category_name}")
            
            for query_data in category_data['queries']:
                try:
                    mcp_result, native_result = await self.execute_query_pair(query_data, category_name)
                    
                    # Store results
                    self.mcp_results.append(mcp_result)
                    self.native_results.append(native_result)
                    
                    all_results.append({
                        'query_id': query_data['id'],
                        'category': category_name,
                        'query_text': query_data['text'],
                        'complexity': query_data.get('complexity', 'unknown'),
                        'mcp_result': mcp_result,
                        'native_result': native_result
                    })
                    
                    # Save intermediate results
                    self._save_intermediate_results(all_results)
                    
                except Exception as e:
                    logger.error(f"Failed to execute query {query_data['id']}: {e}")
                    continue
        
        # Generate comprehensive analysis
        analysis_results = self._analyze_results(all_results)
        
        # Save final results
        self._save_final_results(analysis_results)
        
        logger.info("Comprehensive test completed successfully")
        return analysis_results
    
    def _save_intermediate_results(self, results: List[Dict[str, Any]]):
        """Save intermediate results during testing."""
        intermediate_path = self.results_dir / f"intermediate_results_{self.session_id}.json"
        
        # Convert QueryMetrics to dict for JSON serialization
        serializable_results = []
        for result in results:
            serializable_result = result.copy()
            if hasattr(result['mcp_result'], '__dict__'):
                serializable_result['mcp_result'] = self._metrics_to_dict(result['mcp_result'])
            if hasattr(result['native_result'], '__dict__'):
                serializable_result['native_result'] = self._metrics_to_dict(result['native_result'])
            serializable_results.append(serializable_result)
        
        with open(intermediate_path, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
    
    def _metrics_to_dict(self, metrics: QueryMetrics) -> Dict[str, Any]:
        """Convert QueryMetrics to dictionary."""
        return {
            'query_id': metrics.query_id,
            'query_text': metrics.query_text,
            'approach': metrics.approach,
            'start_time': metrics.start_time.isoformat(),
            'end_time': metrics.end_time.isoformat(),
            'success': metrics.success,
            'token_breakdown': {
                'interaction_id': metrics.token_breakdown.interaction_id,
                'timestamp': metrics.token_breakdown.timestamp.isoformat(),
                'user_prompt': metrics.token_breakdown.user_prompt,
                'context_history': metrics.token_breakdown.context_history,
                'tool_results': metrics.token_breakdown.tool_results,
                'file_content': metrics.token_breakdown.file_content,
                'total_input': metrics.token_breakdown.total_input,
                'reasoning': metrics.token_breakdown.reasoning,
                'tool_calls': metrics.token_breakdown.tool_calls,
                'code_generation': metrics.token_breakdown.code_generation,
                'explanations': metrics.token_breakdown.explanations,
                'total_output': metrics.token_breakdown.total_output,
                'tokens_per_result': metrics.token_breakdown.tokens_per_result,
                'context_utilization': metrics.token_breakdown.context_utilization,
                'generation_efficiency': metrics.token_breakdown.generation_efficiency
            },
            'tools_used': metrics.tools_used,
            'tool_call_count': metrics.tool_call_count,
            'file_reads': metrics.file_reads,
            'file_writes': metrics.file_writes,
            'response_time_ms': metrics.response_time_ms,
            'accuracy_score': metrics.accuracy_score
        }
    
    def _analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the comprehensive test results."""
        logger.info("Analyzing comprehensive test results...")
        
        analysis = {
            'test_session_id': self.session_id,
            'test_timestamp': datetime.now().isoformat(),
            'total_queries': len(results),
            'summary': {
                'mcp_success_rate': 0,
                'native_success_rate': 0,
                'mcp_avg_response_time': 0,
                'native_avg_response_time': 0,
                'mcp_total_tokens': 0,
                'native_total_tokens': 0,
                'mcp_avg_input_tokens': 0,
                'native_avg_input_tokens': 0,
                'mcp_avg_output_tokens': 0,
                'native_avg_output_tokens': 0,
                'token_efficiency_comparison': 0,
                'response_time_comparison': 0
            },
            'category_analysis': {},
            'tool_usage_comparison': {
                'mcp_tools': {},
                'native_tools': {},
                'tool_overlap': []
            },
            'detailed_metrics': {
                'mcp_metrics': [],
                'native_metrics': []
            },
            'efficiency_analysis': {
                'queries_where_mcp_more_efficient': [],
                'queries_where_native_more_efficient': [],
                'efficiency_by_complexity': {},
                'efficiency_by_category': {}
            }
        }
        
        # Process results
        mcp_successes = 0
        native_successes = 0
        mcp_response_times = []
        native_response_times = []
        mcp_total_tokens = []
        native_total_tokens = []
        mcp_input_tokens = []
        native_input_tokens = []
        mcp_output_tokens = []
        native_output_tokens = []
        
        for result in results:
            mcp_result = result['mcp_result']
            native_result = result['native_result']
            
            # Convert to dict if needed
            if hasattr(mcp_result, '__dict__'):
                mcp_result = self._metrics_to_dict(mcp_result)
            if hasattr(native_result, '__dict__'):
                native_result = self._metrics_to_dict(native_result)
            
            # Success rates
            if mcp_result['success']:
                mcp_successes += 1
            if native_result['success']:
                native_successes += 1
            
            # Response times
            mcp_response_times.append(mcp_result['response_time_ms'])
            native_response_times.append(native_result['response_time_ms'])
            
            # Token counts
            mcp_input = mcp_result['token_breakdown']['total_input']
            mcp_output = mcp_result['token_breakdown']['total_output']
            native_input = native_result['token_breakdown']['total_input']
            native_output = native_result['token_breakdown']['total_output']
            
            mcp_input_tokens.append(mcp_input)
            mcp_output_tokens.append(mcp_output)
            native_input_tokens.append(native_input)
            native_output_tokens.append(native_output)
            mcp_total_tokens.append(mcp_input + mcp_output)
            native_total_tokens.append(native_input + native_output)
            
            # Store detailed metrics
            analysis['detailed_metrics']['mcp_metrics'].append(mcp_result)
            analysis['detailed_metrics']['native_metrics'].append(native_result)
            
            # Efficiency comparison for this query
            mcp_efficiency = mcp_output / max(1, mcp_input) if mcp_input > 0 else 0
            native_efficiency = native_output / max(1, native_input) if native_input > 0 else 0
            
            if mcp_efficiency > 0 and native_efficiency > 0:
                if mcp_efficiency < native_efficiency:  # Lower is better (less output for same input)
                    analysis['efficiency_analysis']['queries_where_mcp_more_efficient'].append({
                        'query_id': result['query_id'],
                        'mcp_efficiency': mcp_efficiency,
                        'native_efficiency': native_efficiency,
                        'efficiency_gain': (native_efficiency - mcp_efficiency) / native_efficiency if native_efficiency > 0 else 0
                    })
                else:
                    analysis['efficiency_analysis']['queries_where_native_more_efficient'].append({
                        'query_id': result['query_id'],
                        'mcp_efficiency': mcp_efficiency,
                        'native_efficiency': native_efficiency,
                        'efficiency_gain': (mcp_efficiency - native_efficiency) / mcp_efficiency if mcp_efficiency > 0 else 0
                    })
        
        # Calculate summary statistics
        total_queries = len(results)
        if total_queries > 0:
            analysis['summary']['mcp_success_rate'] = mcp_successes / total_queries
            analysis['summary']['native_success_rate'] = native_successes / total_queries
            analysis['summary']['mcp_avg_response_time'] = sum(mcp_response_times) / len(mcp_response_times) if mcp_response_times else 0
            analysis['summary']['native_avg_response_time'] = sum(native_response_times) / len(native_response_times) if native_response_times else 0
            analysis['summary']['mcp_total_tokens'] = sum(mcp_total_tokens) if mcp_total_tokens else 0
            analysis['summary']['native_total_tokens'] = sum(native_total_tokens) if native_total_tokens else 0
            analysis['summary']['mcp_avg_input_tokens'] = sum(mcp_input_tokens) / len(mcp_input_tokens) if mcp_input_tokens else 0
            analysis['summary']['native_avg_input_tokens'] = sum(native_input_tokens) / len(native_input_tokens) if native_input_tokens else 0
            analysis['summary']['mcp_avg_output_tokens'] = sum(mcp_output_tokens) / len(mcp_output_tokens) if mcp_output_tokens else 0
            analysis['summary']['native_avg_output_tokens'] = sum(native_output_tokens) / len(native_output_tokens) if native_output_tokens else 0
            
            # Overall efficiency comparison
            if mcp_total_tokens and native_total_tokens:
                mcp_avg_total = sum(mcp_total_tokens) / len(mcp_total_tokens)
                native_avg_total = sum(native_total_tokens) / len(native_total_tokens)
                analysis['summary']['token_efficiency_comparison'] = (native_avg_total - mcp_avg_total) / native_avg_total if native_avg_total > 0 else 0
            else:
                analysis['summary']['token_efficiency_comparison'] = 0
            
            # Response time comparison
            mcp_avg_time = analysis['summary']['mcp_avg_response_time']
            native_avg_time = analysis['summary']['native_avg_response_time']
            if mcp_avg_time > 0 and native_avg_time > 0:
                analysis['summary']['response_time_comparison'] = (native_avg_time - mcp_avg_time) / native_avg_time
            else:
                analysis['summary']['response_time_comparison'] = 0
        
        return analysis
    
    def _save_final_results(self, analysis: Dict[str, Any]):
        """Save final comprehensive analysis results."""
        # Save JSON results
        json_path = self.results_dir / f"comprehensive_analysis_{self.session_id}.json"
        with open(json_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        # Generate markdown report
        self._generate_markdown_report(analysis)
        
        logger.info(f"Final results saved to: {json_path}")
    
    def _generate_markdown_report(self, analysis: Dict[str, Any]):
        """Generate a comprehensive markdown report."""
        report_path = self.results_dir / f"comprehensive_report_{self.session_id}.md"
        
        with open(report_path, 'w') as f:
            f.write("# Comprehensive MCP vs Native Performance Analysis\n\n")
            f.write(f"**Test Session:** {analysis['test_session_id']}\n")
            f.write(f"**Test Date:** {analysis['test_timestamp']}\n")
            f.write(f"**Total Queries:** {analysis['total_queries']}\n\n")
            
            summary = analysis['summary']
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **MCP Success Rate:** {summary['mcp_success_rate']:.1%}\n")
            f.write(f"- **Native Success Rate:** {summary['native_success_rate']:.1%}\n")
            f.write(f"- **MCP Average Response Time:** {summary['mcp_avg_response_time']:.0f}ms\n")
            f.write(f"- **Native Average Response Time:** {summary['native_avg_response_time']:.0f}ms\n")
            f.write(f"- **Response Time Improvement:** {summary['response_time_comparison']:.1%}\n")
            f.write(f"- **Token Efficiency Improvement:** {summary['token_efficiency_comparison']:.1%}\n\n")
            
            f.write("## Token Usage Analysis\n\n")
            f.write(f"### Total Tokens\n")
            f.write(f"- **MCP Total:** {summary['mcp_total_tokens']:,}\n")
            f.write(f"- **Native Total:** {summary['native_total_tokens']:,}\n")
            f.write(f"- **Difference:** {summary['mcp_total_tokens'] - summary['native_total_tokens']:+,}\n\n")
            
            f.write(f"### Average Input Tokens\n")
            f.write(f"- **MCP Average:** {summary['mcp_avg_input_tokens']:.0f}\n")
            f.write(f"- **Native Average:** {summary['native_avg_input_tokens']:.0f}\n\n")
            
            f.write(f"### Average Output Tokens\n")
            f.write(f"- **MCP Average:** {summary['mcp_avg_output_tokens']:.0f}\n")
            f.write(f"- **Native Average:** {summary['native_avg_output_tokens']:.0f}\n\n")
            
            # Efficiency analysis
            efficiency = analysis['efficiency_analysis']
            f.write("## Efficiency Analysis\n\n")
            f.write(f"- **Queries where MCP more efficient:** {len(efficiency['queries_where_mcp_more_efficient'])}\n")
            f.write(f"- **Queries where Native more efficient:** {len(efficiency['queries_where_native_more_efficient'])}\n\n")
            
            if efficiency['queries_where_mcp_more_efficient']:
                f.write("### Top MCP Efficiency Gains\n")
                sorted_mcp = sorted(efficiency['queries_where_mcp_more_efficient'], 
                                  key=lambda x: x['efficiency_gain'], reverse=True)[:5]
                for item in sorted_mcp:
                    f.write(f"- **{item['query_id']}:** {item['efficiency_gain']:.1%} improvement\n")
                f.write("\n")
            
            if efficiency['queries_where_native_more_efficient']:
                f.write("### Top Native Efficiency Gains\n")
                sorted_native = sorted(efficiency['queries_where_native_more_efficient'], 
                                     key=lambda x: x['efficiency_gain'], reverse=True)[:5]
                for item in sorted_native:
                    f.write(f"- **{item['query_id']}:** {item['efficiency_gain']:.1%} improvement\n")
        
        logger.info(f"Markdown report saved to: {report_path}")


async def main():
    """Main entry point for comprehensive testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive MCP vs Native comparison test')
    parser.add_argument('--workspace', type=Path, 
                       default=Path('/workspaces/Code-Index-MCP'),
                       help='Workspace root directory')
    parser.add_argument('--timeout', type=int, default=3600,
                       help='Total test timeout in seconds')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = MCPVsNativeTestRunner(args.workspace)
    
    try:
        # Run comprehensive test with timeout
        results = await asyncio.wait_for(runner.run_comprehensive_test(), timeout=args.timeout)
        
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        
        summary = results['summary']
        print(f"Total Queries: {results['total_queries']}")
        print(f"MCP Success Rate: {summary['mcp_success_rate']:.1%}")
        print(f"Native Success Rate: {summary['native_success_rate']:.1%}")
        print(f"Token Efficiency Improvement: {summary['token_efficiency_comparison']:.1%}")
        print(f"Response Time Improvement: {summary['response_time_comparison']:.1%}")
        
        print(f"\nResults saved to: {runner.results_dir}")
        
    except asyncio.TimeoutError:
        logger.error(f"Test timed out after {args.timeout} seconds")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())