#!/usr/bin/env python3
"""
Real MCP vs Native Analysis - Authentic Data Only

This script executes real MCP tool calls and native tool operations to gather
genuine performance data, token usage, and edit behavior patterns.

NO SIMULATION OR MOCKING - ALL DATA MUST BE REAL
"""

import asyncio
import json
import time
import sqlite3
import subprocess
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import re
from mcp_server.core.path_utils import PathUtils

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RealPerformanceMetrics:
    """Real performance metrics from actual tool execution"""
    query_id: str
    method: str  # 'mcp_semantic', 'mcp_sql_fts', 'mcp_sql_bm25', 'native_grep', 'native_read'
    query_text: str
    
    # Real timing data
    start_time: float
    end_time: float
    response_time_ms: float
    
    # Real database performance
    db_query_time_ms: Optional[float] = None
    db_schema_used: Optional[str] = None
    results_count: int = 0
    
    # Real metadata quality
    has_line_numbers: bool = False
    has_usage_hints: bool = False
    has_code_snippets: bool = False
    metadata_quality_score: float = 0.0
    
    # Real success metrics
    success: bool = False
    error_message: Optional[str] = None
    
    # Real token estimation (we'll improve this)
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


@dataclass  
class RealEditBehavior:
    """Real edit behavior from actual operations"""
    query_id: str
    edit_type: str  # 'targeted', 'multi_edit', 'full_rewrite', 'read_only'
    files_accessed: List[str]
    context_reads: int
    lines_changed: int
    total_file_lines: int
    edit_precision: float
    edit_success: bool


class RealMCPAnalyzer:
    """Analyzes real MCP performance using actual tool execution"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.mcp_server_script = workspace_path / 'scripts/cli/mcp_server_cli.py'
        self.db_path = self._get_real_db_path()
        self.results_dir = workspace_path / 'real_analysis_results'
        self.results_dir.mkdir(exist_ok=True)
        
        # Results storage
        self.performance_results: List[RealPerformanceMetrics] = []
        self.edit_behaviors: List[RealEditBehavior] = []
        
    def _get_real_db_path(self) -> Path:
        """Get the actual database path from index discovery"""
        from mcp_server.utils.index_discovery import IndexDiscovery
        
        discovery = IndexDiscovery(self.workspace_path, enable_multi_path=True)
        db_path = discovery.get_local_index_path()
        if not db_path:
            raise RuntimeError("No real index found - cannot proceed with authentic analysis")
        logger.info(f"Using real database: {db_path}")
        return Path(db_path)
    
    async def execute_real_mcp_query(self, query: str, method: str = "search_code") -> RealPerformanceMetrics:
        """Execute actual MCP tool call and measure real performance"""
        query_id = f"mcp_{method}_{int(time.time())}"
        start_time = time.time()
        
        logger.info(f"Executing real MCP query: {query} (method: {method})")
        
        try:
            # Start real MCP server process
            mcp_process = subprocess.Popen(
                [sys.executable, str(self.mcp_server_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.workspace_path)
            )
            
            # Prepare real MCP JSON-RPC request
            if method == "symbol_lookup":
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "symbol_lookup",
                        "arguments": {"symbol": self._extract_symbol_from_query(query)}
                    }
                }
            else:  # search_code
                request = {
                    "jsonrpc": "2.0", 
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "search_code",
                        "arguments": {
                            "query": query,
                            "semantic": "semantic" in method,
                            "limit": 20
                        }
                    }
                }
            
            # Send real request
            request_str = json.dumps(request) + "\n"
            stdout, stderr = mcp_process.communicate(input=request_str, timeout=30)
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Parse real response
            success = False
            results_count = 0
            metadata_quality = 0.0
            error_msg = None
            
            try:
                response = json.loads(stdout)
                if "result" in response:
                    success = True
                    result_data = response["result"]
                    if isinstance(result_data, list) and len(result_data) > 0:
                        content = result_data[0].get("text", "")
                        if content:
                            # Parse the actual MCP response content
                            results_count = self._count_results_in_response(content)
                            metadata_quality = self._assess_real_metadata_quality(content)
                else:
                    error_msg = response.get("error", {}).get("message", "Unknown error")
            except json.JSONDecodeError:
                error_msg = f"Invalid JSON response: {stdout[:200]}"
            
            # Measure real database performance
            db_query_time = self._measure_real_db_performance(query, method)
            
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"mcp_{method}",
                query_text=query,
                start_time=start_time,
                end_time=end_time,
                response_time_ms=response_time_ms,
                db_query_time_ms=db_query_time,
                db_schema_used=self._detect_schema_used(method),
                results_count=results_count,
                has_line_numbers="line" in stdout.lower(),
                has_usage_hints="usage_hint" in stdout.lower(),
                has_code_snippets="snippet" in stdout.lower(),
                metadata_quality_score=metadata_quality,
                success=success,
                error_message=error_msg,
                estimated_input_tokens=self._estimate_tokens(request_str),
                estimated_output_tokens=self._estimate_tokens(stdout)
            )
            
        except subprocess.TimeoutExpired:
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"mcp_{method}",
                query_text=query,
                start_time=start_time,
                end_time=time.time(),
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message="MCP request timeout"
            )
        except Exception as e:
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"mcp_{method}",
                query_text=query,
                start_time=start_time,
                end_time=time.time(),
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    def execute_real_native_query(self, query: str, method: str = "grep") -> RealPerformanceMetrics:
        """Execute actual native tool operations and measure real performance"""
        query_id = f"native_{method}_{int(time.time())}"
        start_time = time.time()
        
        logger.info(f"Executing real native query: {query} (method: {method})")
        
        try:
            if method == "grep":
                # Use actual ripgrep for real performance
                result = subprocess.run(
                    ["rg", "-n", "--type", "py", query, str(self.workspace_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                stdout = result.stdout
                success = result.returncode == 0
                results_count = len(stdout.strip().split('\n')) if stdout.strip() else 0
                
            elif method == "find_and_read":
                # Real file finding and reading
                find_result = subprocess.run(
                    ["find", str(self.workspace_path), "-name", "*.py", "-exec", "grep", "-l", query, "{}", ";"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                stdout = find_result.stdout
                success = find_result.returncode == 0
                results_count = len(stdout.strip().split('\n')) if stdout.strip() else 0
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Assess real metadata quality for native tools
            metadata_quality = 0.2 if ":line" in stdout else 0.1  # Native tools provide minimal metadata
            
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"native_{method}",
                query_text=query,
                start_time=start_time,
                end_time=end_time,
                response_time_ms=response_time_ms,
                results_count=results_count,
                has_line_numbers=":" in stdout,
                has_usage_hints=False,  # Native tools don't provide usage hints
                has_code_snippets=True,  # Grep provides content snippets
                metadata_quality_score=metadata_quality,
                success=success,
                estimated_input_tokens=self._estimate_tokens(query),
                estimated_output_tokens=self._estimate_tokens(stdout)
            )
            
        except subprocess.TimeoutExpired:
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"native_{method}",
                query_text=query,
                start_time=start_time,
                end_time=time.time(),
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message="Native tool timeout"
            )
        except Exception as e:
            return RealPerformanceMetrics(
                query_id=query_id,
                method=f"native_{method}",
                query_text=query,
                start_time=start_time,
                end_time=time.time(),
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    def _measure_real_db_performance(self, query: str, method: str) -> float:
        """Measure actual database query performance"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            start_time = time.time()
            
            if method == "symbol_lookup":
                # Real symbol lookup query
                symbol = self._extract_symbol_from_query(query)
                cursor.execute("SELECT * FROM symbols WHERE symbol = ? LIMIT 10", (symbol,))
            elif "semantic" in method:
                # For semantic, we'd query the vector embeddings (simplified here)
                cursor.execute("SELECT COUNT(*) FROM bm25_content WHERE content MATCH ?", (query,))
            else:
                # Real FTS query
                cursor.execute("SELECT * FROM fts_code WHERE content MATCH ? LIMIT 20", (query,))
            
            results = cursor.fetchall()
            end_time = time.time()
            
            conn.close()
            return (end_time - start_time) * 1000
            
        except Exception as e:
            logger.warning(f"Database performance measurement failed: {e}")
            return 0.0
    
    def _detect_schema_used(self, method: str) -> str:
        """Detect which database schema is actually being used"""
        if "symbol" in method:
            return "symbols"
        elif "semantic" in method:
            return "vector_embeddings"
        elif "fts" in method:
            return "fts_code"
        else:
            return "bm25_content"
    
    def _assess_real_metadata_quality(self, response_content: str) -> float:
        """Assess actual metadata quality from real MCP response"""
        score = 0.0
        
        # Check for line numbers
        if re.search(r'"line":\s*\d+', response_content):
            score += 0.3
        
        # Check for usage hints
        if "usage_hint" in response_content:
            score += 0.3
        
        # Check for code snippets
        if "snippet" in response_content or "code" in response_content:
            score += 0.2
        
        # Check for file paths
        if re.search(r'\.py"', response_content):
            score += 0.2
        
        return min(score, 1.0)
    
    def _count_results_in_response(self, response_content: str) -> int:
        """Count actual results in MCP response"""
        # Look for JSON array patterns or line-based results
        try:
            data = json.loads(response_content)
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and "results" in data:
                return len(data["results"])
        except:
            pass
        
        # Fallback to counting lines or patterns
        lines = response_content.strip().split('\n')
        return len([line for line in lines if line.strip()])
    
    def _extract_symbol_from_query(self, query: str) -> str:
        """Extract symbol name from query text"""
        # Look for class/function patterns
        match = re.search(r'\b([A-Z][a-zA-Z0-9_]+)\b', query)
        if match:
            return match.group(1)
        
        # Look for quoted strings
        match = re.search(r'"([^"]+)"', query)
        if match:
            return match.group(1)
        
        # Fallback to first word
        words = query.split()
        return words[0] if words else "Unknown"
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation - will be improved with real data)"""
        # Rough estimate: ~4 characters per token for code/technical text
        return max(1, len(text) // 4)
    
    async def run_real_analysis(self, test_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute comprehensive real analysis across all queries and methods"""
        logger.info(f"Starting real analysis with {len(test_queries)} queries")
        
        results = {
            "analysis_metadata": {
                "start_time": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "database_size_mb": self.db_path.stat().st_size / (1024 * 1024),
                "total_queries": len(test_queries)
            },
            "performance_results": [],
            "schema_comparison": {},
            "method_comparison": {},
            "edit_behavior_analysis": {}
        }
        
        for query_data in test_queries:
            query = query_data["text"]
            logger.info(f"Processing query: {query}")
            
            # Test MCP methods
            mcp_results = []
            
            # Symbol lookup if appropriate
            if "symbol" in query_data.get("expected_approach", ""):
                result = await self.execute_real_mcp_query(query, "symbol_lookup")
                mcp_results.append(result)
                self.performance_results.append(result)
            
            # Search code
            result = await self.execute_real_mcp_query(query, "search_code")
            mcp_results.append(result)
            self.performance_results.append(result)
            
            # Test native methods
            native_results = []
            
            # Grep
            result = self.execute_real_native_query(query, "grep")
            native_results.append(result)
            self.performance_results.append(result)
            
            # Find and read
            result = self.execute_real_native_query(query, "find_and_read")
            native_results.append(result)
            self.performance_results.append(result)
            
            results["performance_results"].extend([
                asdict(r) for r in mcp_results + native_results
            ])
        
        # Generate real comparative analysis
        results["method_comparison"] = self._analyze_method_performance()
        results["schema_comparison"] = self._analyze_schema_performance()
        
        # Save results
        results_file = self.results_dir / f"real_analysis_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Real analysis complete. Results saved to: {results_file}")
        return results
    
    def _analyze_method_performance(self) -> Dict[str, Any]:
        """Analyze real performance data by method"""
        method_stats = {}
        
        for method in ['mcp_search_code', 'mcp_symbol_lookup', 'native_grep', 'native_find_and_read']:
            method_results = [r for r in self.performance_results if r.method == method]
            
            if method_results:
                response_times = [r.response_time_ms for r in method_results if r.success]
                success_count = len([r for r in method_results if r.success])
                
                method_stats[method] = {
                    "total_queries": len(method_results),
                    "successful_queries": success_count,
                    "success_rate": success_count / len(method_results) if method_results else 0,
                    "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                    "min_response_time_ms": min(response_times) if response_times else 0,
                    "max_response_time_ms": max(response_times) if response_times else 0,
                    "avg_results_count": sum(r.results_count for r in method_results) / len(method_results),
                    "avg_metadata_quality": sum(r.metadata_quality_score for r in method_results) / len(method_results)
                }
        
        return method_stats
    
    def _analyze_schema_performance(self) -> Dict[str, Any]:
        """Analyze real database schema performance"""
        schema_stats = {}
        
        for schema in ['symbols', 'fts_code', 'bm25_content']:
            schema_results = [r for r in self.performance_results if r.db_schema_used == schema]
            
            if schema_results:
                db_times = [r.db_query_time_ms for r in schema_results if r.db_query_time_ms is not None]
                
                schema_stats[schema] = {
                    "query_count": len(schema_results),
                    "avg_db_query_time_ms": sum(db_times) / len(db_times) if db_times else 0,
                    "avg_metadata_quality": sum(r.metadata_quality_score for r in schema_results) / len(schema_results),
                    "success_rate": len([r for r in schema_results if r.success]) / len(schema_results)
                }
        
        return schema_stats


async def main():
    """Main entry point for real MCP analysis"""
    workspace_path = Path("PathUtils.get_workspace_root()")
    
    # Load test queries
    with open(workspace_path / "test_queries.json") as f:
        test_data = json.load(f)
    
    # Extract all queries
    all_queries = []
    for category in test_data["query_categories"].values():
        all_queries.extend(category["queries"])
    
    # Limit to first 5 queries for initial real testing
    test_queries = all_queries[:5]
    
    # Create analyzer and run real analysis
    analyzer = RealMCPAnalyzer(workspace_path)
    results = await analyzer.run_real_analysis(test_queries)
    
    # Print summary
    print("\n=== REAL MCP vs NATIVE ANALYSIS RESULTS ===")
    print(f"Database: {results['analysis_metadata']['database_path']}")
    print(f"Database Size: {results['analysis_metadata']['database_size_mb']:.1f} MB")
    print(f"Total Queries Tested: {results['analysis_metadata']['total_queries']}")
    
    for method, stats in results["method_comparison"].items():
        print(f"\n{method.upper()}:")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Avg Response Time: {stats['avg_response_time_ms']:.1f} ms")
        print(f"  Avg Results: {stats['avg_results_count']:.1f}")
        print(f"  Metadata Quality: {stats['avg_metadata_quality']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())