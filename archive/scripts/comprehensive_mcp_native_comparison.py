#!/usr/bin/env python3
"""
Comprehensive MCP vs Native Performance Comparison Framework

This script provides a systematic approach to measure and analyze the performance
differences between MCP-based retrieval and native Claude Code retrieval.
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
import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.utils.index_discovery import IndexDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query: str
    query_type: str
    repository: str
    mode: str  # 'mcp' or 'native'
    
    # Timing metrics
    total_time: float
    time_to_first_result: float
    tool_times: Dict[str, List[float]]
    
    # Token metrics
    input_tokens: Dict[str, int]
    output_tokens: Dict[str, int]
    total_input_tokens: int
    total_output_tokens: int
    
    # Tool usage metrics
    tool_calls: Dict[str, int]
    total_tool_calls: int
    
    # Accuracy metrics
    results_found: int
    correct_results: int
    false_positives: int
    missed_results: int
    
    # Behavioral metrics
    files_read: int
    partial_reads: int
    full_reads: int
    search_refinements: int
    
    # Error tracking
    errors: List[str]
    success: bool
    
    # Raw data
    transcript: str
    timestamp: str


@dataclass
class RepositoryInfo:
    """Information about a test repository"""
    name: str
    path: Path
    language: str
    file_count: int
    total_size_mb: float
    has_mcp_index: bool
    index_path: Optional[Path]


class TestQueryGenerator:
    """Generates standardized test queries for repositories"""
    
    def __init__(self):
        self.query_templates = {
            'symbol': [
                "Find the definition of class {class_name}",
                "Where is function {function_name} implemented?",
                "Locate the {variable_name} variable declaration",
                "Find all methods in class {class_name}",
                "Show me the constructor for {class_name}",
                "Where is interface {interface_name} defined?",
                "Find the enum {enum_name}",
                "Locate constant {constant_name}",
                "Find type definition {type_name}",
                "Where is module {module_name} defined?"
            ],
            'content': [
                "Search for pattern {pattern}",
                "Find all TODO comments",
                "Show error handling code",
                "Find database queries",
                "Search for API endpoints",
                "Find configuration loading code",
                "Show authentication logic",
                "Find logging statements",
                "Search for test assertions",
                "Find deprecation warnings"
            ],
            'navigation': [
                "Find all files importing {module}",
                "Show test files for {component}",
                "Find configuration files",
                "List all markdown documentation",
                "Find build configuration files",
                "Show all Python files in {directory}",
                "Find files modified recently",
                "List all interfaces",
                "Find example usage of {function}",
                "Show related files to {file}"
            ],
            'refactoring': [
                "Find all usages of {symbol}",
                "Show impact of renaming {old_name} to {new_name}",
                "Find all subclasses of {class_name}",
                "List all implementations of {interface}",
                "Find all calls to {method}",
                "Show dependencies of {module}",
                "Find circular imports",
                "List unused imports",
                "Find duplicate code patterns",
                "Show coupling between {module1} and {module2}"
            ],
            'understanding': [
                "Explain how {feature} works",
                "Show the flow of {process}",
                "Find the entry point for {command}",
                "Explain the purpose of {class}",
                "Show initialization sequence",
                "Find error handling for {operation}",
                "Explain the architecture of {component}",
                "Show data flow for {feature}",
                "Find security measures for {operation}",
                "Explain the algorithm in {function}"
            ]
        }
    
    def generate_queries(self, repo_info: RepositoryInfo, 
                        query_counts: Dict[str, int]) -> List[Tuple[str, str]]:
        """Generate queries for a specific repository"""
        queries = []
        
        # Extract common symbols from the repository
        # This would ideally analyze the actual code, but for now we'll use placeholders
        placeholders = self._get_repo_placeholders(repo_info)
        
        for query_type, count in query_counts.items():
            templates = self.query_templates.get(query_type, [])
            for i in range(min(count, len(templates))):
                query = self._fill_template(templates[i], placeholders)
                queries.append((query, query_type))
        
        return queries
    
    def _get_repo_placeholders(self, repo_info: RepositoryInfo) -> Dict[str, str]:
        """Get repository-specific placeholders for query templates"""
        # This is simplified - in reality would analyze the repo
        language_defaults = {
            'python': {
                'class_name': 'BaseClass',
                'function_name': '__init__',
                'variable_name': 'config',
                'module': 'utils',
                'component': 'auth',
                'directory': 'src'
            },
            'javascript': {
                'class_name': 'Component',
                'function_name': 'render',
                'variable_name': 'state',
                'module': 'react',
                'component': 'Button',
                'directory': 'components'
            },
            'go': {
                'class_name': 'Server',
                'function_name': 'HandleRequest',
                'variable_name': 'ctx',
                'module': 'handler',
                'component': 'router',
                'directory': 'pkg'
            }
        }
        
        return language_defaults.get(repo_info.language, {
            'class_name': 'MainClass',
            'function_name': 'process',
            'variable_name': 'data',
            'module': 'core',
            'component': 'main',
            'directory': 'src'
        })
    
    def _fill_template(self, template: str, placeholders: Dict[str, str]) -> str:
        """Fill a query template with placeholders"""
        query = template
        for key, value in placeholders.items():
            query = query.replace(f"{{{key}}}", value)
        return query


class ClaudeAgentLauncher:
    """Launches Claude Code agents and captures their interactions"""
    
    def __init__(self, mode: str, workspace_path: Path):
        self.mode = mode  # 'mcp' or 'native'
        self.workspace_path = workspace_path
        self.metrics_collector = MetricsCollector()
    
    async def execute_query(self, query: str, query_type: str, 
                          repo_info: RepositoryInfo) -> QueryMetrics:
        """Execute a single query and collect metrics"""
        start_time = time.time()
        
        # Launch agent with appropriate configuration
        if self.mode == 'mcp':
            agent_config = self._get_mcp_config(repo_info)
        else:
            agent_config = self._get_native_config()
        
        # Execute query (this would interface with actual Claude Code)
        # For now, this is a placeholder
        transcript, metrics = await self._execute_with_agent(query, agent_config)
        
        # Parse metrics from transcript
        parsed_metrics = self.metrics_collector.parse_transcript(transcript)
        
        # Create QueryMetrics object
        return QueryMetrics(
            query=query,
            query_type=query_type,
            repository=repo_info.name,
            mode=self.mode,
            total_time=time.time() - start_time,
            time_to_first_result=parsed_metrics.get('time_to_first_result', 0),
            tool_times=parsed_metrics.get('tool_times', {}),
            input_tokens=parsed_metrics.get('input_tokens', {}),
            output_tokens=parsed_metrics.get('output_tokens', {}),
            total_input_tokens=sum(parsed_metrics.get('input_tokens', {}).values()),
            total_output_tokens=sum(parsed_metrics.get('output_tokens', {}).values()),
            tool_calls=parsed_metrics.get('tool_calls', {}),
            total_tool_calls=sum(parsed_metrics.get('tool_calls', {}).values()),
            results_found=parsed_metrics.get('results_found', 0),
            correct_results=parsed_metrics.get('correct_results', 0),
            false_positives=parsed_metrics.get('false_positives', 0),
            missed_results=parsed_metrics.get('missed_results', 0),
            files_read=parsed_metrics.get('files_read', 0),
            partial_reads=parsed_metrics.get('partial_reads', 0),
            full_reads=parsed_metrics.get('full_reads', 0),
            search_refinements=parsed_metrics.get('search_refinements', 0),
            errors=parsed_metrics.get('errors', []),
            success=not parsed_metrics.get('errors', []),
            transcript=transcript,
            timestamp=datetime.now().isoformat()
        )
    
    def _get_mcp_config(self, repo_info: RepositoryInfo) -> Dict[str, Any]:
        """Get MCP configuration for the agent"""
        return {
            'mcp_enabled': True,
            'mcp_server_path': str(self.workspace_path / 'scripts/cli/mcp_server_cli.py'),
            'index_path': str(repo_info.index_path) if repo_info.index_path else None,
            'tools_priority': ['mcp__code-index-mcp__symbol_lookup', 
                              'mcp__code-index-mcp__search_code']
        }
    
    def _get_native_config(self) -> Dict[str, Any]:
        """Get native configuration (no MCP)"""
        return {
            'mcp_enabled': False,
            'allowed_tools': ['Grep', 'Find', 'Read', 'Glob', 'Edit']
        }
    
    async def _execute_with_agent(self, query: str, 
                                config: Dict[str, Any]) -> Tuple[str, Dict]:
        """Execute query with Claude Code agent (placeholder)"""
        # This would interface with actual Claude Code
        # For now, return mock data
        transcript = f"Executing query: {query}\nWith config: {config}\n"
        metrics = {
            'time_to_first_result': 0.1,
            'tool_times': {'search': [0.05, 0.03]},
            'input_tokens': {'search': 100, 'read': 200},
            'output_tokens': {'search': 500, 'read': 1000},
            'tool_calls': {'search': 2, 'read': 3},
            'results_found': 5,
            'correct_results': 4,
            'false_positives': 1,
            'missed_results': 0,
            'files_read': 3,
            'partial_reads': 2,
            'full_reads': 1,
            'search_refinements': 1,
            'errors': []
        }
        return transcript, metrics


class MetricsCollector:
    """Collects and parses metrics from agent transcripts"""
    
    def parse_transcript(self, transcript: str) -> Dict[str, Any]:
        """Parse metrics from agent transcript"""
        # This would parse actual transcript format
        # For now, return placeholder metrics
        return {
            'time_to_first_result': 0.1,
            'tool_times': {'search': [0.05, 0.03]},
            'input_tokens': {'search': 100, 'read': 200},
            'output_tokens': {'search': 500, 'read': 1000},
            'tool_calls': {'search': 2, 'read': 3},
            'results_found': 5,
            'correct_results': 4,
            'false_positives': 1,
            'missed_results': 0,
            'files_read': 3,
            'partial_reads': 2,
            'full_reads': 1,
            'search_refinements': 1,
            'errors': []
        }


class TestOrchestrator:
    """Orchestrates the entire test execution"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.test_repos_path = workspace_path / 'test_indexes'
        self.results_path = workspace_path / 'test_results' / 'mcp_native_comparison'
        self.results_path.mkdir(parents=True, exist_ok=True)
        
        self.query_generator = TestQueryGenerator()
        self.test_repos = self._discover_test_repos()
    
    def _discover_test_repos(self) -> List[RepositoryInfo]:
        """Discover available test repositories"""
        repos = []
        
        # Check test_indexes directory
        if self.test_repos_path.exists():
            for repo_dir in self.test_repos_path.iterdir():
                if repo_dir.is_dir() and (repo_dir / '.mcp-index.json').exists():
                    config = json.loads((repo_dir / '.mcp-index.json').read_text())
                    
                    # Find index file
                    index_path = None
                    for db_file in repo_dir.glob('*.db'):
                        if 'bm25' in db_file.name or 'code_index' in db_file.name:
                            index_path = db_file
                            break
                    
                    repos.append(RepositoryInfo(
                        name=repo_dir.name,
                        path=repo_dir,
                        language=config.get('language', 'unknown'),
                        file_count=config.get('file_count', 0),
                        total_size_mb=config.get('total_size_mb', 0),
                        has_mcp_index=index_path is not None,
                        index_path=index_path
                    ))
        
        return repos
    
    async def run_tier_tests(self, tier: int, query_counts: Dict[str, int]):
        """Run tests for a specific tier of repositories"""
        # Define repository tiers
        tier_repos = {
            1: ['gin', 'Alamofire', 'tokio'],  # Small/medium repos
            2: ['django', 'react', 'redis', 'spring-boot', 'rails'],  # Standard
            3: ['TypeScript', 'sdk', 'aspnetcore']  # Large repos
        }
        
        selected_repos = [r for r in self.test_repos 
                         if r.name in tier_repos.get(tier, [])]
        
        if not selected_repos:
            logger.warning(f"No repositories found for tier {tier}")
            return
        
        logger.info(f"Running tier {tier} tests on {len(selected_repos)} repositories")
        
        all_results = []
        
        for repo in selected_repos:
            logger.info(f"Testing repository: {repo.name}")
            
            # Generate queries for this repo
            queries = self.query_generator.generate_queries(repo, query_counts)
            
            # Run tests with both MCP and native modes
            for mode in ['mcp', 'native']:
                launcher = ClaudeAgentLauncher(mode, self.workspace_path)
                
                for query, query_type in queries:
                    try:
                        metrics = await launcher.execute_query(query, query_type, repo)
                        all_results.append(metrics)
                        
                        # Save intermediate results
                        self._save_intermediate_results(metrics)
                        
                    except Exception as e:
                        logger.error(f"Error executing query: {query}, error: {e}")
                        # Record failed query
                        all_results.append(QueryMetrics(
                            query=query,
                            query_type=query_type,
                            repository=repo.name,
                            mode=mode,
                            total_time=0,
                            time_to_first_result=0,
                            tool_times={},
                            input_tokens={},
                            output_tokens={},
                            total_input_tokens=0,
                            total_output_tokens=0,
                            tool_calls={},
                            total_tool_calls=0,
                            results_found=0,
                            correct_results=0,
                            false_positives=0,
                            missed_results=0,
                            files_read=0,
                            partial_reads=0,
                            full_reads=0,
                            search_refinements=0,
                            errors=[str(e)],
                            success=False,
                            transcript="",
                            timestamp=datetime.now().isoformat()
                        ))
        
        # Save tier results
        self._save_tier_results(tier, all_results)
        
        return all_results
    
    def _save_intermediate_results(self, metrics: QueryMetrics):
        """Save results as we go for safety"""
        results_file = self.results_path / f"intermediate_{metrics.mode}_{metrics.repository}.jsonl"
        with open(results_file, 'a') as f:
            f.write(json.dumps(asdict(metrics)) + '\n')
    
    def _save_tier_results(self, tier: int, results: List[QueryMetrics]):
        """Save complete tier results"""
        results_file = self.results_path / f"tier_{tier}_results.json"
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        # Also save as CSV for easy analysis
        df = pd.DataFrame([asdict(r) for r in results])
        df.to_csv(self.results_path / f"tier_{tier}_results.csv", index=False)


class ResultsAnalyzer:
    """Analyzes test results and generates reports"""
    
    def __init__(self, results_path: Path):
        self.results_path = results_path
    
    def analyze_all_results(self):
        """Analyze all test results and generate comprehensive report"""
        # Load all results
        all_results = []
        for results_file in self.results_path.glob("tier_*_results.json"):
            with open(results_file) as f:
                all_results.extend(json.load(f))
        
        df = pd.DataFrame(all_results)
        
        # Generate various analyses
        report = {
            'summary': self._generate_summary(df),
            'by_query_type': self._analyze_by_query_type(df),
            'by_repository': self._analyze_by_repository(df),
            'by_mode': self._analyze_by_mode(df),
            'performance_comparison': self._compare_performance(df),
            'token_analysis': self._analyze_tokens(df),
            'behavioral_patterns': self._analyze_behavior(df),
            'recommendations': self._generate_recommendations(df)
        }
        
        # Save comprehensive report
        report_path = self.results_path / 'comprehensive_analysis_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self._generate_markdown_report(report)
        
        return report
    
    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate overall summary statistics"""
        return {
            'total_queries': len(df),
            'successful_queries': len(df[df['success']]),
            'failed_queries': len(df[~df['success']]),
            'repositories_tested': df['repository'].nunique(),
            'average_time_mcp': df[df['mode'] == 'mcp']['total_time'].mean(),
            'average_time_native': df[df['mode'] == 'native']['total_time'].mean(),
            'average_tokens_mcp': df[df['mode'] == 'mcp']['total_input_tokens'].mean() + 
                                 df[df['mode'] == 'mcp']['total_output_tokens'].mean(),
            'average_tokens_native': df[df['mode'] == 'native']['total_input_tokens'].mean() + 
                                    df[df['mode'] == 'native']['total_output_tokens'].mean()
        }
    
    def _analyze_by_query_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by query type"""
        results = {}
        for query_type in df['query_type'].unique():
            type_df = df[df['query_type'] == query_type]
            results[query_type] = {
                'count': len(type_df),
                'mcp_avg_time': type_df[type_df['mode'] == 'mcp']['total_time'].mean(),
                'native_avg_time': type_df[type_df['mode'] == 'native']['total_time'].mean(),
                'mcp_avg_tokens': (type_df[type_df['mode'] == 'mcp']['total_input_tokens'].mean() + 
                                  type_df[type_df['mode'] == 'mcp']['total_output_tokens'].mean()),
                'native_avg_tokens': (type_df[type_df['mode'] == 'native']['total_input_tokens'].mean() + 
                                     type_df[type_df['mode'] == 'native']['total_output_tokens'].mean()),
                'mcp_success_rate': len(type_df[(type_df['mode'] == 'mcp') & type_df['success']]) / 
                                   len(type_df[type_df['mode'] == 'mcp']) if len(type_df[type_df['mode'] == 'mcp']) > 0 else 0,
                'native_success_rate': len(type_df[(type_df['mode'] == 'native') & type_df['success']]) / 
                                      len(type_df[type_df['mode'] == 'native']) if len(type_df[type_df['mode'] == 'native']) > 0 else 0
            }
        return results
    
    def _analyze_by_repository(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by repository"""
        results = {}
        for repo in df['repository'].unique():
            repo_df = df[df['repository'] == repo]
            results[repo] = {
                'queries_tested': len(repo_df) // 2,  # Divide by 2 for MCP and native
                'mcp_avg_time': repo_df[repo_df['mode'] == 'mcp']['total_time'].mean(),
                'native_avg_time': repo_df[repo_df['mode'] == 'native']['total_time'].mean(),
                'time_improvement': (repo_df[repo_df['mode'] == 'native']['total_time'].mean() / 
                                   repo_df[repo_df['mode'] == 'mcp']['total_time'].mean() 
                                   if repo_df[repo_df['mode'] == 'mcp']['total_time'].mean() > 0 else 1),
                'token_reduction': 1 - ((repo_df[repo_df['mode'] == 'mcp']['total_input_tokens'].mean() + 
                                       repo_df[repo_df['mode'] == 'mcp']['total_output_tokens'].mean()) /
                                      (repo_df[repo_df['mode'] == 'native']['total_input_tokens'].mean() + 
                                       repo_df[repo_df['mode'] == 'native']['total_output_tokens'].mean())
                                      if (repo_df[repo_df['mode'] == 'native']['total_input_tokens'].mean() + 
                                          repo_df[repo_df['mode'] == 'native']['total_output_tokens'].mean()) > 0 else 1)
            }
        return results
    
    def _analyze_by_mode(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compare MCP vs Native modes"""
        mcp_df = df[df['mode'] == 'mcp']
        native_df = df[df['mode'] == 'native']
        
        return {
            'mcp': {
                'total_queries': len(mcp_df),
                'success_rate': len(mcp_df[mcp_df['success']]) / len(mcp_df) if len(mcp_df) > 0 else 0,
                'avg_time': mcp_df['total_time'].mean(),
                'avg_tool_calls': mcp_df['total_tool_calls'].mean(),
                'avg_files_read': mcp_df['files_read'].mean(),
                'partial_read_ratio': mcp_df['partial_reads'].sum() / 
                                     (mcp_df['partial_reads'].sum() + mcp_df['full_reads'].sum())
                                     if (mcp_df['partial_reads'].sum() + mcp_df['full_reads'].sum()) > 0 else 0
            },
            'native': {
                'total_queries': len(native_df),
                'success_rate': len(native_df[native_df['success']]) / len(native_df) if len(native_df) > 0 else 0,
                'avg_time': native_df['total_time'].mean(),
                'avg_tool_calls': native_df['total_tool_calls'].mean(),
                'avg_files_read': native_df['files_read'].mean(),
                'partial_read_ratio': native_df['partial_reads'].sum() / 
                                     (native_df['partial_reads'].sum() + native_df['full_reads'].sum())
                                     if (native_df['partial_reads'].sum() + native_df['full_reads'].sum()) > 0 else 0
            }
        }
    
    def _compare_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate performance comparison metrics"""
        # Calculate paired comparisons (same query in both modes)
        paired_metrics = []
        
        for _, row in df[df['mode'] == 'mcp'].iterrows():
            # Find matching native query
            native_match = df[(df['mode'] == 'native') & 
                            (df['query'] == row['query']) & 
                            (df['repository'] == row['repository'])]
            
            if not native_match.empty:
                native_row = native_match.iloc[0]
                paired_metrics.append({
                    'query': row['query'],
                    'repository': row['repository'],
                    'query_type': row['query_type'],
                    'time_ratio': native_row['total_time'] / row['total_time'] if row['total_time'] > 0 else 1,
                    'token_ratio': ((native_row['total_input_tokens'] + native_row['total_output_tokens']) /
                                   (row['total_input_tokens'] + row['total_output_tokens'])
                                   if (row['total_input_tokens'] + row['total_output_tokens']) > 0 else 1),
                    'tool_calls_ratio': native_row['total_tool_calls'] / row['total_tool_calls'] if row['total_tool_calls'] > 0 else 1
                })
        
        paired_df = pd.DataFrame(paired_metrics)
        
        return {
            'overall_time_improvement': paired_df['time_ratio'].mean(),
            'overall_token_reduction': 1 - (1 / paired_df['token_ratio'].mean()) if paired_df['token_ratio'].mean() > 0 else 0,
            'time_improvement_by_type': {
                qt: paired_df[paired_df['query_type'] == qt]['time_ratio'].mean()
                for qt in paired_df['query_type'].unique()
            },
            'token_reduction_by_type': {
                qt: 1 - (1 / paired_df[paired_df['query_type'] == qt]['token_ratio'].mean())
                if paired_df[paired_df['query_type'] == qt]['token_ratio'].mean() > 0 else 0
                for qt in paired_df['query_type'].unique()
            }
        }
    
    def _analyze_tokens(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detailed token usage analysis"""
        return {
            'mcp_token_distribution': {
                'input': {
                    'mean': df[df['mode'] == 'mcp']['total_input_tokens'].mean(),
                    'median': df[df['mode'] == 'mcp']['total_input_tokens'].median(),
                    'std': df[df['mode'] == 'mcp']['total_input_tokens'].std(),
                    'min': df[df['mode'] == 'mcp']['total_input_tokens'].min(),
                    'max': df[df['mode'] == 'mcp']['total_input_tokens'].max()
                },
                'output': {
                    'mean': df[df['mode'] == 'mcp']['total_output_tokens'].mean(),
                    'median': df[df['mode'] == 'mcp']['total_output_tokens'].median(),
                    'std': df[df['mode'] == 'mcp']['total_output_tokens'].std(),
                    'min': df[df['mode'] == 'mcp']['total_output_tokens'].min(),
                    'max': df[df['mode'] == 'mcp']['total_output_tokens'].max()
                }
            },
            'native_token_distribution': {
                'input': {
                    'mean': df[df['mode'] == 'native']['total_input_tokens'].mean(),
                    'median': df[df['mode'] == 'native']['total_input_tokens'].median(),
                    'std': df[df['mode'] == 'native']['total_input_tokens'].std(),
                    'min': df[df['mode'] == 'native']['total_input_tokens'].min(),
                    'max': df[df['mode'] == 'native']['total_input_tokens'].max()
                },
                'output': {
                    'mean': df[df['mode'] == 'native']['total_output_tokens'].mean(),
                    'median': df[df['mode'] == 'native']['total_output_tokens'].median(),
                    'std': df[df['mode'] == 'native']['total_output_tokens'].std(),
                    'min': df[df['mode'] == 'native']['total_output_tokens'].min(),
                    'max': df[df['mode'] == 'native']['total_output_tokens'].max()
                }
            }
        }
    
    def _analyze_behavior(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze behavioral patterns"""
        return {
            'search_patterns': {
                'mcp_avg_refinements': df[df['mode'] == 'mcp']['search_refinements'].mean(),
                'native_avg_refinements': df[df['mode'] == 'native']['search_refinements'].mean()
            },
            'reading_patterns': {
                'mcp_partial_read_preference': (df[df['mode'] == 'mcp']['partial_reads'].sum() /
                                               df[df['mode'] == 'mcp']['files_read'].sum()
                                               if df[df['mode'] == 'mcp']['files_read'].sum() > 0 else 0),
                'native_partial_read_preference': (df[df['mode'] == 'native']['partial_reads'].sum() /
                                                  df[df['mode'] == 'native']['files_read'].sum()
                                                  if df[df['mode'] == 'native']['files_read'].sum() > 0 else 0)
            },
            'accuracy_patterns': {
                'mcp_precision': (df[df['mode'] == 'mcp']['correct_results'].sum() /
                                 df[df['mode'] == 'mcp']['results_found'].sum()
                                 if df[df['mode'] == 'mcp']['results_found'].sum() > 0 else 0),
                'native_precision': (df[df['mode'] == 'native']['correct_results'].sum() /
                                    df[df['mode'] == 'native']['results_found'].sum()
                                    if df[df['mode'] == 'native']['results_found'].sum() > 0 else 0)
            }
        }
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Calculate key metrics
        perf_comparison = self._compare_performance(df)
        token_analysis = self._analyze_tokens(df)
        
        # Performance-based recommendations
        if perf_comparison['overall_time_improvement'] > 2:
            recommendations.append(
                f"MCP provides {perf_comparison['overall_time_improvement']:.1f}x speed improvement. "
                "Strongly recommend using MCP for all code search operations."
            )
        
        # Token-based recommendations
        if perf_comparison['overall_token_reduction'] > 0.5:
            recommendations.append(
                f"MCP reduces token usage by {perf_comparison['overall_token_reduction']*100:.1f}%. "
                "This allows handling more complex queries within context limits."
            )
        
        # Query-type specific recommendations
        for qt, improvement in perf_comparison['time_improvement_by_type'].items():
            if improvement > 3:
                recommendations.append(
                    f"'{qt}' queries show {improvement:.1f}x speed improvement with MCP. "
                    f"Always use MCP for {qt} operations."
                )
        
        # Repository-size based recommendations
        repo_analysis = self._analyze_by_repository(df)
        large_repos = [r for r, data in repo_analysis.items() 
                      if data['time_improvement'] > 5]
        if large_repos:
            recommendations.append(
                f"Large repositories ({', '.join(large_repos)}) benefit most from MCP "
                f"with >5x performance gains."
            )
        
        return recommendations
    
    def _generate_markdown_report(self, report: Dict[str, Any]):
        """Generate a human-readable markdown report"""
        markdown = f"""# MCP vs Native Performance Comparison Report

Generated: {datetime.now().isoformat()}

## Executive Summary

- **Total Queries Tested**: {report['summary']['total_queries']}
- **Repositories Tested**: {report['summary']['repositories_tested']}
- **Average MCP Time**: {report['summary']['average_time_mcp']:.3f}s
- **Average Native Time**: {report['summary']['average_time_native']:.3f}s
- **Speed Improvement**: {report['summary']['average_time_native'] / report['summary']['average_time_mcp']:.1f}x
- **Token Reduction**: {(1 - report['summary']['average_tokens_mcp'] / report['summary']['average_tokens_native']) * 100:.1f}%

## Performance Comparison

### Overall Metrics
- **Time Improvement**: {report['performance_comparison']['overall_time_improvement']:.1f}x faster with MCP
- **Token Reduction**: {report['performance_comparison']['overall_token_reduction'] * 100:.1f}% fewer tokens with MCP

### By Query Type
"""
        
        for qt, improvement in report['performance_comparison']['time_improvement_by_type'].items():
            token_reduction = report['performance_comparison']['token_reduction_by_type'][qt]
            markdown += f"- **{qt}**: {improvement:.1f}x faster, {token_reduction*100:.1f}% fewer tokens\n"
        
        markdown += "\n## Repository Analysis\n\n"
        markdown += "| Repository | Queries | MCP Time | Native Time | Improvement | Token Reduction |\n"
        markdown += "|------------|---------|----------|-------------|-------------|----------------|\n"
        
        for repo, data in report['by_repository'].items():
            markdown += f"| {repo} | {data['queries_tested']} | "
            markdown += f"{data['mcp_avg_time']:.3f}s | {data['native_avg_time']:.3f}s | "
            markdown += f"{data['time_improvement']:.1f}x | {data['token_reduction']*100:.1f}% |\n"
        
        markdown += "\n## Behavioral Patterns\n\n"
        behavior = report['behavioral_patterns']
        markdown += f"- **Search Refinements**: MCP {behavior['search_patterns']['mcp_avg_refinements']:.1f} vs Native {behavior['search_patterns']['native_avg_refinements']:.1f}\n"
        markdown += f"- **Partial Read Preference**: MCP {behavior['reading_patterns']['mcp_partial_read_preference']*100:.1f}% vs Native {behavior['reading_patterns']['native_partial_read_preference']*100:.1f}%\n"
        markdown += f"- **Result Precision**: MCP {behavior['accuracy_patterns']['mcp_precision']*100:.1f}% vs Native {behavior['accuracy_patterns']['native_precision']*100:.1f}%\n"
        
        markdown += "\n## Recommendations\n\n"
        for i, rec in enumerate(report['recommendations'], 1):
            markdown += f"{i}. {rec}\n"
        
        # Save markdown report
        report_path = self.results_path / 'performance_comparison_report.md'
        with open(report_path, 'w') as f:
            f.write(markdown)
        
        logger.info(f"Markdown report saved to {report_path}")


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='MCP vs Native Performance Comparison')
    parser.add_argument('--tier', type=int, choices=[1, 2, 3],
                       help='Run specific tier tests (1=small, 2=medium, 3=large)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze existing results')
    parser.add_argument('--workspace', type=Path, 
                       default=Path('/workspaces/Code-Index-MCP'),
                       help='Workspace path')
    
    args = parser.parse_args()
    
    orchestrator = TestOrchestrator(args.workspace)
    
    if args.analyze_only:
        # Just analyze existing results
        analyzer = ResultsAnalyzer(orchestrator.results_path)
        report = analyzer.analyze_all_results()
        logger.info("Analysis complete. Report generated.")
    else:
        # Define query counts for each type
        query_counts = {
            'symbol': 20,
            'content': 20,
            'navigation': 20,
            'refactoring': 10,
            'understanding': 10
        }
        
        if args.tier:
            # Run specific tier
            await orchestrator.run_tier_tests(args.tier, query_counts)
        else:
            # Run all tiers
            for tier in [1, 2, 3]:
                logger.info(f"Starting tier {tier} tests")
                await orchestrator.run_tier_tests(tier, query_counts)
        
        # Analyze results after tests
        analyzer = ResultsAnalyzer(orchestrator.results_path)
        report = analyzer.analyze_all_results()
        logger.info("Testing and analysis complete. Report generated.")


if __name__ == '__main__':
    asyncio.run(main())