#!/usr/bin/env python3
"""
Claude Code Behavior Analyzer - Comprehensive MCP vs Non-MCP Analysis

This script analyzes how Claude Code uses MCP tools vs traditional retrieval methods,
focusing on end-to-end behavior, context usage patterns, and real token/time consumption.
"""

import time
import json
import subprocess
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import sys
from mcp_server.core.path_utils import PathUtils

sys.path.insert(0, "PathUtils.get_workspace_root()/scripts")
from fix_mcp_bm25_integration import BM25DirectDispatcher


@dataclass
class QueryResult:
    """Result from a search query."""
    query: str
    query_type: str
    method: str  # 'mcp' or 'grep'
    results: List[Dict[str, Any]]
    response_time: float
    token_count: int
    error: Optional[str] = None


@dataclass
class TaskWorkflow:
    """Complete task workflow from search to action."""
    task_description: str
    initial_query: QueryResult
    follow_up_reads: List[Dict[str, Any]] = field(default_factory=list)
    edits_made: List[Dict[str, Any]] = field(default_factory=list)
    total_time: float = 0.0
    total_tokens: int = 0
    tool_calls: int = 0


class ClaudeCodeBehaviorAnalyzer:
    """Analyze Claude Code's behavior with different search methods."""
    
    def __init__(self):
        self.mcp_dispatcher = BM25DirectDispatcher()
        self.results = []
        self.workflows = []
        
        # Token estimation constants (based on typical Claude Code responses)
        self.TOKEN_ESTIMATES = {
            'mcp_result': 150,  # Structured JSON response
            'grep_result': 250,  # Raw text output
            'file_read': 2000,  # Average file content
            'edit_diff': 500,   # Edit operation
            'error': 100        # Error message
        }
    
    def estimate_tokens(self, content: Any) -> int:
        """Estimate token count for content."""
        if isinstance(content, str):
            # Rough estimate: 1 token per 4 characters
            return len(content) // 4
        elif isinstance(content, dict):
            return self.estimate_tokens(json.dumps(content))
        elif isinstance(content, list):
            return sum(self.estimate_tokens(item) for item in content)
        return 100  # Default
    
    def run_mcp_query(self, query: str, query_type: str) -> QueryResult:
        """Run a query using MCP."""
        start_time = time.time()
        
        try:
            if query_type == "symbol":
                # Try symbol lookup first
                result = self.mcp_dispatcher.lookup(query)
                if result:
                    results = [result]
                else:
                    results = []
            else:
                # Use search for other types
                results = list(self.mcp_dispatcher.search(query, limit=20))
            
            response_time = time.time() - start_time
            
            # Estimate tokens for MCP response
            token_count = self.TOKEN_ESTIMATES['mcp_result'] * len(results)
            
            return QueryResult(
                query=query,
                query_type=query_type,
                method='mcp',
                results=results,
                response_time=response_time,
                token_count=token_count
            )
            
        except Exception as e:
            return QueryResult(
                query=query,
                query_type=query_type,
                method='mcp',
                results=[],
                response_time=time.time() - start_time,
                token_count=self.TOKEN_ESTIMATES['error'],
                error=str(e)
            )
    
    def run_grep_query(self, query: str, query_type: str) -> QueryResult:
        """Run a query using grep (ripgrep)."""
        start_time = time.time()
        
        try:
            # Use ripgrep for better performance
            cmd = ['rg', '--json', '--max-count', '20']
            
            if query_type == "symbol":
                # For symbols, use word boundaries
                cmd.extend(['-w', query])
            else:
                # For content, use as-is
                cmd.append(query)
            
            # Add path to search
            cmd.append('PathUtils.get_workspace_root()')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            response_time = time.time() - start_time
            
            # Parse ripgrep JSON output
            results = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get('type') == 'match':
                                match_data = data['data']
                                results.append({
                                    'file': match_data['path']['text'],
                                    'line': match_data['line_number'],
                                    'snippet': match_data['lines']['text'].strip(),
                                    'score': 1.0
                                })
                        except:
                            pass
            
            # Estimate tokens for grep output
            token_count = self.TOKEN_ESTIMATES['grep_result'] * len(results)
            
            return QueryResult(
                query=query,
                query_type=query_type,
                method='grep',
                results=results[:20],  # Limit to 20 results
                response_time=response_time,
                token_count=token_count
            )
            
        except subprocess.TimeoutExpired:
            return QueryResult(
                query=query,
                query_type=query_type,
                method='grep',
                results=[],
                response_time=10.0,
                token_count=self.TOKEN_ESTIMATES['error'],
                error='Timeout'
            )
        except Exception as e:
            return QueryResult(
                query=query,
                query_type=query_type,
                method='grep',
                results=[],
                response_time=time.time() - start_time,
                token_count=self.TOKEN_ESTIMATES['error'],
                error=str(e)
            )
    
    def simulate_file_read(self, file_path: str, line_number: int, use_offset: bool = True) -> Dict[str, Any]:
        """Simulate Claude Code reading a file."""
        start_time = time.time()
        
        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    'action': 'read',
                    'file': file_path,
                    'error': 'File not found',
                    'time': time.time() - start_time,
                    'tokens': self.TOKEN_ESTIMATES['error']
                }
            
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if use_offset and line_number > 0:
                # Claude Code uses offset/limit
                offset = max(0, line_number - 10)
                limit = 50
                content = lines[offset:offset + limit]
                read_type = 'partial'
            else:
                # Full file read
                content = lines
                read_type = 'full'
            
            tokens = self.estimate_tokens(''.join(content))
            
            return {
                'action': 'read',
                'file': file_path,
                'line': line_number,
                'read_type': read_type,
                'lines_read': len(content),
                'total_lines': len(lines),
                'time': time.time() - start_time,
                'tokens': tokens
            }
            
        except Exception as e:
            return {
                'action': 'read',
                'file': file_path,
                'error': str(e),
                'time': time.time() - start_time,
                'tokens': self.TOKEN_ESTIMATES['error']
            }
    
    def simulate_edit(self, file_path: str, line_number: int, edit_size: str = 'small') -> Dict[str, Any]:
        """Simulate Claude Code making an edit."""
        edit_sizes = {
            'small': 5,    # Change a few lines
            'medium': 20,  # Change a method
            'large': 100   # Change multiple methods
        }
        
        lines_changed = edit_sizes.get(edit_size, 5)
        
        return {
            'action': 'edit',
            'file': file_path,
            'line': line_number,
            'edit_size': edit_size,
            'lines_changed': lines_changed,
            'tokens': lines_changed * 50  # Rough estimate
        }
    
    def analyze_workflow(self, task: str, query: str, query_type: str) -> Tuple[TaskWorkflow, TaskWorkflow]:
        """Analyze a complete workflow for both MCP and grep."""
        
        # Run initial queries
        mcp_result = self.run_mcp_query(query, query_type)
        grep_result = self.run_grep_query(query, query_type)
        
        # Create workflows
        mcp_workflow = TaskWorkflow(task_description=task, initial_query=mcp_result)
        grep_workflow = TaskWorkflow(task_description=task, initial_query=grep_result)
        
        # Simulate follow-up actions based on results
        for workflow, method in [(mcp_workflow, 'mcp'), (grep_workflow, 'grep')]:
            if workflow.initial_query.results:
                # Take first 3 results for follow-up
                for i, result in enumerate(workflow.initial_query.results[:3]):
                    file_path = result.get('file', result.get('defined_in', ''))
                    line_num = result.get('line', 1)
                    
                    if file_path:
                        # Simulate file read
                        # MCP provides line numbers, so Claude Code can use offset
                        # Grep also provides line numbers in our simulation
                        use_offset = method == 'mcp' or 'line' in result
                        read_action = self.simulate_file_read(file_path, line_num, use_offset)
                        workflow.follow_up_reads.append(read_action)
                        
                        # Simulate edit (only on first result)
                        if i == 0:
                            edit_action = self.simulate_edit(file_path, line_num, 'small')
                            workflow.edits_made.append(edit_action)
            
            # Calculate totals
            workflow.total_time = workflow.initial_query.response_time + \
                                 sum(r.get('time', 0) for r in workflow.follow_up_reads)
            
            workflow.total_tokens = workflow.initial_query.token_count + \
                                   sum(r.get('tokens', 0) for r in workflow.follow_up_reads) + \
                                   sum(e.get('tokens', 0) for e in workflow.edits_made)
            
            workflow.tool_calls = 1 + len(workflow.follow_up_reads) + len(workflow.edits_made)
        
        return mcp_workflow, grep_workflow
    
    def generate_test_queries(self) -> List[Tuple[str, str, str]]:
        """Generate balanced test queries (20 per category)."""
        queries = []
        
        # Symbol Queries (20)
        symbol_queries = [
            ("Find BM25Indexer class", "BM25Indexer", "symbol"),
            ("Locate SQLiteStore definition", "SQLiteStore", "symbol"),
            ("Find EnhancedDispatcher", "EnhancedDispatcher", "symbol"),
            ("Search for PluginManager", "PluginManager", "symbol"),
            ("Find PathResolver class", "PathResolver", "symbol"),
            ("Locate TokenCounter", "TokenCounter", "symbol"),
            ("Find SemanticIndexer", "SemanticIndexer", "symbol"),
            ("Search IndexDiscovery", "IndexDiscovery", "symbol"),
            ("Find DocumentPlugin", "DocumentPlugin", "symbol"),
            ("Locate BasePlugin", "BasePlugin", "symbol"),
            ("Find initialize_services", "initialize_services", "symbol"),
            ("Search index_repository", "index_repository", "symbol"),
            ("Find search_code function", "search_code", "symbol"),
            ("Locate lookup_symbol", "lookup_symbol", "symbol"),
            ("Find get_statistics", "get_statistics", "symbol"),
            ("Search health_check", "health_check", "symbol"),
            ("Find load_plugins", "load_plugins", "symbol"),
            ("Locate create_dispatcher", "create_dispatcher", "symbol"),
            ("Find validate_config", "validate_config", "symbol"),
            ("Search run_benchmarks", "run_benchmarks", "symbol")
        ]
        
        # Content Pattern Queries (20)
        content_queries = [
            ("Find error handling", "try except", "content"),
            ("Search async functions", "async def", "content"),
            ("Find file operations", "with open", "content"),
            ("Search imports", "from pathlib import", "content"),
            ("Find class definitions", "class.*__init__", "content"),
            ("Search method definitions", "def.*self", "content"),
            ("Find return statements", "return None", "content"),
            ("Search exceptions", "raise.*Error", "content"),
            ("Find logging calls", "logger.info", "content"),
            ("Search database queries", "cursor.execute", "content"),
            ("Find JSON operations", "json.dumps", "content"),
            ("Search path operations", "Path.*exists", "content"),
            ("Find list comprehensions", "for.*in.*]", "content"),
            ("Search decorators", "@.*property", "content"),
            ("Find type hints", "-> Dict", "content"),
            ("Search context managers", "__enter__", "content"),
            ("Find lambda functions", "lambda", "content"),
            ("Search string formatting", "f-string", "content"),
            ("Find regex patterns", "re.compile", "content"),
            ("Search assertions", "assert", "content")
        ]
        
        # Navigation Queries (20)  
        navigation_queries = [
            ("Find storage imports", "from .storage import", "navigation"),
            ("Search plugin imports", "from .plugins import", "navigation"),
            ("Find test files", "test_.*\\.py", "navigation"),
            ("Search config files", "config.*\\.py", "navigation"),
            ("Find who calls lookup", "dispatcher.lookup", "navigation"),
            ("Search dispatcher usage", "self.dispatcher", "navigation"),
            ("Find index references", "index_path", "navigation"),
            ("Search database connections", "sqlite3.connect", "navigation"),
            ("Find plugin loading", "load_plugin", "navigation"),
            ("Search cache usage", "cache", "navigation"),
            ("Find metric collection", "metrics", "navigation"),
            ("Search error handlers", "error_handler", "navigation"),
            ("Find API endpoints", "api", "navigation"),
            ("Search middleware", "middleware", "navigation"),
            ("Find validators", "validator", "navigation"),
            ("Search utilities", "utils", "navigation"),
            ("Find constants", "constants", "navigation"),
            ("Search interfaces", "interface", "navigation"),
            ("Find base classes", "base.*class", "navigation"),
            ("Search mixins", "mixin", "navigation")
        ]
        
        # Documentation Queries (20)
        doc_queries = [
            ("Find installation docs", "installation", "documentation"),
            ("Search setup instructions", "setup", "documentation"),
            ("Find README content", "README", "documentation"),
            ("Search API documentation", "API", "documentation"),
            ("Find usage examples", "example", "documentation"),
            ("Search configuration docs", "configuration", "documentation"),
            ("Find troubleshooting", "troubleshoot", "documentation"),
            ("Search changelog", "changelog", "documentation"),
            ("Find contributing guide", "contributing", "documentation"),
            ("Search license info", "license", "documentation"),
            ("Find TODO comments", "TODO", "documentation"),
            ("Search FIXME notes", "FIXME", "documentation"),
            ("Find docstrings", "Args:", "documentation"),
            ("Search return docs", "Returns:", "documentation"),
            ("Find parameter docs", "Parameters:", "documentation"),
            ("Search examples in docs", "Example:", "documentation"),
            ("Find notes", "Note:", "documentation"),
            ("Search warnings", "Warning:", "documentation"),
            ("Find deprecated", "deprecated", "documentation"),
            ("Search references", "See also:", "documentation")
        ]
        
        # Natural Language Queries (20)
        natural_queries = [
            ("How to index a repository", "index repository", "natural"),
            ("What does reranking do", "reranking", "natural"),
            ("Where is authentication", "authentication", "natural"),
            ("How to configure plugins", "plugin config", "natural"),
            ("What is BM25 scoring", "BM25 scoring", "natural"),
            ("Where are tests located", "test", "natural"),
            ("How to handle errors", "error handling", "natural"),
            ("What is semantic search", "semantic search", "natural"),
            ("Where is logging configured", "logging config", "natural"),
            ("How to add new plugin", "new plugin", "natural"),
            ("What does dispatcher do", "dispatcher", "natural"),
            ("Where is cache stored", "cache storage", "natural"),
            ("How to run benchmarks", "benchmark", "natural"),
            ("What is path resolution", "path resolution", "natural"),
            ("Where are metrics collected", "metrics", "natural"),
            ("How to debug searches", "debug search", "natural"),
            ("What is token counting", "token count", "natural"),
            ("Where is security handled", "security", "natural"),
            ("How to optimize performance", "performance", "natural"),
            ("What are indexes used for", "index", "natural")
        ]
        
        # Combine all queries
        queries.extend(symbol_queries)
        queries.extend(content_queries)
        queries.extend(navigation_queries)
        queries.extend(doc_queries)
        queries.extend(natural_queries)
        
        return queries
    
    def run_comprehensive_analysis(self):
        """Run the complete analysis."""
        print("Claude Code Behavior Analysis")
        print("=" * 80)
        
        # Check MCP health
        health = self.mcp_dispatcher.health_check()
        print(f"\nMCP Status: {health['status']}")
        print(f"Index: {health.get('index', 'None')}")
        
        if health['status'] != 'operational':
            print("ERROR: MCP is not operational!")
            return
        
        # Generate test queries
        queries = self.generate_test_queries()
        print(f"\nRunning {len(queries)} test queries...")
        
        # Track results by category
        results_by_category = {
            'symbol': [],
            'content': [],
            'navigation': [],
            'documentation': [],
            'natural': []
        }
        
        # Run queries
        for i, (task, query, query_type) in enumerate(queries):
            if i % 20 == 0:
                print(f"\nProgress: {i}/{len(queries)}")
            
            # Analyze workflow
            mcp_workflow, grep_workflow = self.analyze_workflow(task, query, query_type)
            
            # Store results
            results_by_category[query_type].append({
                'task': task,
                'query': query,
                'mcp': mcp_workflow,
                'grep': grep_workflow
            })
        
        # Calculate statistics
        print("\n\nAnalysis Complete!")
        print("=" * 80)
        
        # Save raw results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"claude_code_behavior_analysis_{timestamp}.json"
        
        # Convert dataclasses to dicts for JSON serialization
        serializable_results = {}
        for category, results in results_by_category.items():
            serializable_results[category] = []
            for r in results:
                serializable_results[category].append({
                    'task': r['task'],
                    'query': r['query'],
                    'mcp': {
                        'initial_query': r['mcp'].initial_query.__dict__,
                        'follow_up_reads': r['mcp'].follow_up_reads,
                        'edits_made': r['mcp'].edits_made,
                        'total_time': r['mcp'].total_time,
                        'total_tokens': r['mcp'].total_tokens,
                        'tool_calls': r['mcp'].tool_calls
                    },
                    'grep': {
                        'initial_query': r['grep'].initial_query.__dict__,
                        'follow_up_reads': r['grep'].follow_up_reads,
                        'edits_made': r['grep'].edits_made,
                        'total_time': r['grep'].total_time,
                        'total_tokens': r['grep'].total_tokens,
                        'tool_calls': r['grep'].tool_calls
                    }
                })
        
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {results_file}")
        
        # Print summary statistics
        self.print_summary_statistics(results_by_category)
    
    def print_summary_statistics(self, results_by_category: Dict):
        """Print summary statistics from the analysis."""
        print("\n\nSummary Statistics")
        print("=" * 80)
        
        for category, results in results_by_category.items():
            print(f"\n{category.upper()} Queries ({len(results)} queries):")
            print("-" * 60)
            
            # Calculate averages
            mcp_times = [r['mcp'].total_time for r in results]
            grep_times = [r['grep'].total_time for r in results]
            mcp_tokens = [r['mcp'].total_tokens for r in results]
            grep_tokens = [r['grep'].total_tokens for r in results]
            mcp_calls = [r['mcp'].tool_calls for r in results]
            grep_calls = [r['grep'].tool_calls for r in results]
            
            avg_mcp_time = sum(mcp_times) / len(mcp_times) if mcp_times else 0
            avg_grep_time = sum(grep_times) / len(grep_times) if grep_times else 0
            avg_mcp_tokens = sum(mcp_tokens) / len(mcp_tokens) if mcp_tokens else 0
            avg_grep_tokens = sum(grep_tokens) / len(grep_tokens) if grep_tokens else 0
            avg_mcp_calls = sum(mcp_calls) / len(mcp_calls) if mcp_calls else 0
            avg_grep_calls = sum(grep_calls) / len(grep_calls) if grep_calls else 0
            
            print(f"  Average Time:")
            print(f"    MCP:  {avg_mcp_time:.3f}s")
            print(f"    Grep: {avg_grep_time:.3f}s")
            print(f"    Speedup: {avg_grep_time/avg_mcp_time:.1f}x" if avg_mcp_time > 0 else "N/A")
            
            print(f"  Average Tokens:")
            print(f"    MCP:  {avg_mcp_tokens:.0f}")
            print(f"    Grep: {avg_grep_tokens:.0f}")
            print(f"    Reduction: {(1 - avg_mcp_tokens/avg_grep_tokens)*100:.1f}%" if avg_grep_tokens > 0 else "N/A")
            
            print(f"  Average Tool Calls:")
            print(f"    MCP:  {avg_mcp_calls:.1f}")
            print(f"    Grep: {avg_grep_calls:.1f}")


if __name__ == "__main__":
    analyzer = ClaudeCodeBehaviorAnalyzer()
    analyzer.run_comprehensive_analysis()