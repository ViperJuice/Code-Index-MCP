#!/usr/bin/env python3
"""
Comprehensive Semantic vs SQL Retrieval Performance Comparison

This script performs direct head-to-head testing between:
1. Semantic search (Qdrant + Voyage AI embeddings)
2. SQL/BM25 search (SQLite FTS5)

Using identical queries on the same datasets.
"""

import os
import sqlite3
import time
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback
from mcp_server.core.path_utils import PathUtils

# Try to import semantic indexer components
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️  Qdrant client not available - semantic search will be skipped")

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    print("⚠️  Voyage AI client not available - semantic search will be skipped")

@dataclass
class QueryTestCase:
    """Test case for retrieval comparison"""
    id: str
    query: str
    category: str  # symbol_search, content_search, natural_language
    expected_results: List[str]  # Expected symbols/content for validation
    complexity: str  # simple, medium, complex

@dataclass
class RetrievalResult:
    """Result from a retrieval method"""
    method: str  # 'semantic' or 'sql'
    query_id: str
    query_text: str
    success: bool
    response_time_ms: float
    results_count: int
    results: List[Dict[str, Any]]
    error_message: Optional[str] = None
    memory_usage_mb: Optional[float] = None

@dataclass
class ComparisonMetrics:
    """Comparison metrics between semantic and SQL"""
    query_id: str
    semantic_time: float
    sql_time: float
    semantic_results: int
    sql_results: int
    semantic_success: bool
    sql_success: bool
    speed_difference_percent: float
    accuracy_comparison: str
    
class SemanticVsSQLComparison:
    """Main comparison class"""
    
    def __init__(self, base_dir: str = "PathUtils.get_workspace_root()"):
        self.base_dir = Path(base_dir)
        self.test_indexes_dir = self.base_dir / "test_indexes"
        self.vector_index_dir = self.base_dir / "vector_index.qdrant"
        
        # Test queries covering different scenarios - updated for actual codebases
        self.test_queries = [
            QueryTestCase(
                id="license_simple_001",
                query="license",
                category="content_search",
                expected_results=["license"],
                complexity="simple"
            ),
            QueryTestCase(
                id="django_simple_002", 
                query="django",
                category="content_search",
                expected_results=["django"],
                complexity="simple"
            ),
            QueryTestCase(
                id="python_simple_003",
                query="python",
                category="content_search",
                expected_results=["python"],
                complexity="simple"
            ),
            QueryTestCase(
                id="function_medium_001",
                query="function",
                category="content_search", 
                expected_results=["function"],
                complexity="medium"
            ),
            QueryTestCase(
                id="class_medium_002",
                query="class",
                category="content_search",
                expected_results=["class"],
                complexity="medium"
            ),
            QueryTestCase(
                id="http_medium_003",
                query="http",
                category="content_search",
                expected_results=["http"],
                complexity="medium"
            ),
            QueryTestCase(
                id="error_complex_001",
                query="error handling exception",
                category="natural_language",
                expected_results=["error", "exception"],
                complexity="complex"
            ),
            QueryTestCase(
                id="database_complex_002",
                query="database connection configuration",
                category="natural_language",
                expected_results=["database", "connection"],
                complexity="complex"
            )
        ]
        
        # Initialize clients
        self.semantic_available = QDRANT_AVAILABLE and VOYAGE_AVAILABLE
        self.sql_available = True
        
        if self.semantic_available:
            self._init_semantic_client()
        
        self.results: List[RetrievalResult] = []
        
    def _init_semantic_client(self):
        """Initialize semantic search components"""
        try:
            # Initialize Qdrant client  
            if self.vector_index_dir.exists():
                self.qdrant_client = QdrantClient(path=str(self.vector_index_dir))
            else:
                print(f"⚠️  Vector index not found at {self.vector_index_dir}")
                self.semantic_available = False
                return
                
            # Initialize Voyage AI client
            api_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get("VOYAGE_AI_API_KEY")
            if api_key:
                self.voyage_client = voyageai.Client(api_key=api_key)
            else:
                try:
                    self.voyage_client = voyageai.Client()
                except Exception:
                    print("⚠️  Voyage AI API key not found - semantic search unavailable")
                    self.semantic_available = False
                    return
                    
            print("✅ Semantic search initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize semantic search: {e}")
            self.semantic_available = False
    
    def find_available_datasets(self) -> List[Tuple[str, Path, Optional[str]]]:
        """Find datasets that have both SQL and potentially semantic indexes"""
        datasets = []
        
        # Check test_indexes directory
        for item in self.test_indexes_dir.iterdir():
            if item.is_dir():
                sql_db = item / "code_index.db"
                if sql_db.exists():
                    # Check if we have Qdrant collections that might match
                    qdrant_collection = None
                    if self.semantic_available:
                        try:
                            collections = self.qdrant_client.get_collections().collections
                            for collection in collections:
                                collection_name = collection.name
                                if item.name.lower() in collection_name.lower():
                                    qdrant_collection = collection_name
                                    break
                        except Exception:
                            pass
                    
                    datasets.append((item.name, sql_db, qdrant_collection))
        
        return datasets
    
    def test_sql_retrieval(self, db_path: Path, query: QueryTestCase) -> RetrievalResult:
        """Test SQL/BM25 retrieval performance"""
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check if we have BM25 FTS tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            results = []
            
            if 'bm25_content' in tables:
                # Use BM25 FTS search with correct column names (path, content)
                try:
                    search_query = "SELECT path, content, highlight(bm25_content, 1, '<mark>', '</mark>') as highlighted FROM bm25_content WHERE bm25_content MATCH ? ORDER BY bm25(bm25_content) LIMIT 20"
                    cursor.execute(search_query, (query.query,))
                    
                    for row in cursor.fetchall():
                        results.append({
                            'file_path': row[0],
                            'content': row[1][:200] + '...' if len(row[1]) > 200 else row[1],
                            'highlighted': row[2],
                            'method': 'bm25_fts',
                            'score': None  # BM25 score not easily accessible
                        })
                except Exception as fts_error:
                    # Fallback to simple LIKE search if FTS fails
                    search_query = "SELECT path, content FROM bm25_content WHERE content LIKE ? LIMIT 20"
                    search_term = f"%{query.query}%"
                    cursor.execute(search_query, (search_term,))
                    
                    for row in cursor.fetchall():
                        results.append({
                            'file_path': row[0],
                            'content': row[1][:200] + '...' if len(row[1]) > 200 else row[1],
                            'highlighted': row[1],
                            'method': 'sql_like',
                            'score': None
                        })
            
            elif 'symbols' in tables:
                # Fallback to symbol table search
                search_query = "SELECT name, kind, file_path, line FROM symbols WHERE name LIKE ? OR signature LIKE ? LIMIT 20"
                search_term = f"%{query.query}%"
                cursor.execute(search_query, (search_term, search_term))
                
                for row in cursor.fetchall():
                    results.append({
                        'symbol': row[0],
                        'kind': row[1], 
                        'file_path': row[2],
                        'line': row[3],
                        'method': 'sql_symbols',
                        'score': None
                    })
            
            else:
                # No suitable tables found
                raise Exception(f"No searchable tables found in {db_path}")
            
            conn.close()
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return RetrievalResult(
                method='sql',
                query_id=query.id,
                query_text=query.query,
                success=True,
                response_time_ms=response_time,
                results_count=len(results),
                results=results
            )
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return RetrievalResult(
                method='sql',
                query_id=query.id,
                query_text=query.query,
                success=False,
                response_time_ms=response_time,
                results_count=0,
                results=[],
                error_message=str(e)
            )
    
    def test_semantic_retrieval(self, collection_name: str, query: QueryTestCase) -> RetrievalResult:
        """Test semantic retrieval performance"""
        if not self.semantic_available:
            return RetrievalResult(
                method='semantic',
                query_id=query.id,
                query_text=query.query,
                success=False,
                response_time_ms=0,
                results_count=0,
                results=[],
                error_message="Semantic search not available"
            )
        
        start_time = time.time()
        
        try:
            # Generate query embedding
            embedding = self.voyage_client.embed(
                [query.query],
                model="voyage-code-3",
                input_type="query",
                output_dimension=1024,
                output_dtype="float"
            ).embeddings[0]
            
            # Search Qdrant
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=20
            )
            
            results = []
            for result in search_results:
                payload = result.payload or {}
                results.append({
                    'score': result.score,
                    'file_path': payload.get('file', payload.get('relative_path', 'unknown')),
                    'symbol': payload.get('symbol', payload.get('title', 'unknown')),
                    'kind': payload.get('kind', payload.get('type', 'unknown')),
                    'content': payload.get('signature', payload.get('content', ''))[:200],
                    'line': payload.get('line', 0),
                    'method': 'semantic_vector'
                })
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return RetrievalResult(
                method='semantic',
                query_id=query.id,
                query_text=query.query,
                success=True,
                response_time_ms=response_time,
                results_count=len(results),
                results=results
            )
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return RetrievalResult(
                method='semantic',
                query_id=query.id,
                query_text=query.query,
                success=False,
                response_time_ms=response_time,
                results_count=0,
                results=[],
                error_message=str(e)
            )
    
    def run_comprehensive_comparison(self) -> Dict[str, Any]:
        """Run comprehensive comparison across available datasets"""
        print("🚀 Starting Semantic vs SQL Retrieval Comparison")
        print("=" * 80)
        
        # Find available datasets
        datasets = self.find_available_datasets()
        print(f"📁 Found {len(datasets)} datasets for testing")
        
        comparison_results = []
        all_results = []
        
        for dataset_name, sql_db, qdrant_collection in datasets:
            print(f"\n🔍 Testing dataset: {dataset_name}")
            print("-" * 60)
            
            dataset_results = []
            
            for query in self.test_queries:
                print(f"Query: {query.query}")
                
                # Test SQL retrieval
                sql_result = self.test_sql_retrieval(sql_db, query)
                dataset_results.append(sql_result)
                all_results.append(sql_result)
                print(f"  SQL: {sql_result.response_time_ms:.1f}ms, {sql_result.results_count} results, Success: {sql_result.success}")
                
                # Test semantic retrieval if available
                semantic_result = None
                if qdrant_collection and self.semantic_available:
                    semantic_result = self.test_semantic_retrieval(qdrant_collection, query)
                    dataset_results.append(semantic_result)
                    all_results.append(semantic_result)
                    print(f"  Semantic: {semantic_result.response_time_ms:.1f}ms, {semantic_result.results_count} results, Success: {semantic_result.success}")
                    
                    # Calculate comparison metrics
                    speed_diff = 0
                    if sql_result.success and semantic_result.success:
                        if sql_result.response_time_ms > 0:
                            speed_diff = ((semantic_result.response_time_ms - sql_result.response_time_ms) / sql_result.response_time_ms) * 100
                    
                    comparison = ComparisonMetrics(
                        query_id=query.id,
                        semantic_time=semantic_result.response_time_ms,
                        sql_time=sql_result.response_time_ms,
                        semantic_results=semantic_result.results_count,
                        sql_results=sql_result.results_count,
                        semantic_success=semantic_result.success,
                        sql_success=sql_result.success,
                        speed_difference_percent=speed_diff,
                        accuracy_comparison=self._compare_accuracy(sql_result, semantic_result, query)
                    )
                    comparison_results.append(comparison)
                    
                    if speed_diff != 0:
                        faster_method = "SQL" if speed_diff > 0 else "Semantic" 
                        print(f"  → {faster_method} is {abs(speed_diff):.1f}% faster")
                else:
                    print(f"  Semantic: Not available (collection: {qdrant_collection})")
        
        # Generate comprehensive analysis
        analysis = self._generate_analysis(all_results, comparison_results)
        
        # Save results
        timestamp = int(time.time())
        results_file = self.base_dir / f"semantic_vs_sql_comparison_{timestamp}.json"
        
        final_results = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "datasets_tested": len(datasets),
                "queries_per_dataset": len(self.test_queries),
                "total_tests": len(all_results)
            },
            "datasets": [{"name": name, "sql_db": str(sql_db), "qdrant_collection": collection} 
                        for name, sql_db, collection in datasets],
            "test_queries": [asdict(q) for q in self.test_queries],
            "individual_results": [asdict(r) for r in all_results],
            "comparison_metrics": [asdict(c) for c in comparison_results],
            "analysis": analysis
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        return final_results
    
    def _compare_accuracy(self, sql_result: RetrievalResult, semantic_result: RetrievalResult, query: QueryTestCase) -> str:
        """Compare accuracy of results"""
        if not sql_result.success and not semantic_result.success:
            return "both_failed"
        elif not sql_result.success:
            return "semantic_only"
        elif not semantic_result.success:
            return "sql_only"
        
        # Simple accuracy comparison based on expected results
        sql_score = 0
        semantic_score = 0
        
        for expected in query.expected_results:
            # Check SQL results
            for result in sql_result.results:
                result_text = json.dumps(result).lower()
                if expected.lower() in result_text:
                    sql_score += 1
                    break
            
            # Check semantic results
            for result in semantic_result.results:
                result_text = json.dumps(result).lower()
                if expected.lower() in result_text:
                    semantic_score += 1
                    break
        
        if sql_score > semantic_score:
            return "sql_better"
        elif semantic_score > sql_score:
            return "semantic_better"
        else:
            return "equivalent"
    
    def _generate_analysis(self, all_results: List[RetrievalResult], comparisons: List[ComparisonMetrics]) -> Dict[str, Any]:
        """Generate comprehensive analysis"""
        sql_results = [r for r in all_results if r.method == 'sql']
        semantic_results = [r for r in all_results if r.method == 'semantic']
        
        analysis = {
            "summary": {
                "total_sql_tests": len(sql_results),
                "total_semantic_tests": len(semantic_results),
                "sql_success_rate": sum(1 for r in sql_results if r.success) / len(sql_results) if sql_results else 0,
                "semantic_success_rate": sum(1 for r in semantic_results if r.success) / len(semantic_results) if semantic_results else 0
            },
            "performance": {
                "sql_avg_response_time": sum(r.response_time_ms for r in sql_results if r.success) / max(1, sum(1 for r in sql_results if r.success)),
                "semantic_avg_response_time": sum(r.response_time_ms for r in semantic_results if r.success) / max(1, sum(1 for r in semantic_results if r.success)),
                "sql_avg_results": sum(r.results_count for r in sql_results if r.success) / max(1, sum(1 for r in sql_results if r.success)),
                "semantic_avg_results": sum(r.results_count for r in semantic_results if r.success) / max(1, sum(1 for r in semantic_results if r.success))
            },
            "comparisons": {
                "total_comparisons": len(comparisons),
                "semantic_faster_count": sum(1 for c in comparisons if c.speed_difference_percent < 0),
                "sql_faster_count": sum(1 for c in comparisons if c.speed_difference_percent > 0),
                "semantic_better_accuracy": sum(1 for c in comparisons if c.accuracy_comparison == "semantic_better"),
                "sql_better_accuracy": sum(1 for c in comparisons if c.accuracy_comparison == "sql_better")
            }
        }
        
        if comparisons:
            analysis["performance"]["avg_speed_difference"] = sum(c.speed_difference_percent for c in comparisons) / len(comparisons)
        
        return analysis

def main():
    """Main execution function"""
    print("🔬 Semantic vs SQL Retrieval Performance Comparison")
    print("=" * 80)
    
    # Initialize comparison
    comparison = SemanticVsSQLComparison()
    
    # Check availability
    print(f"📊 Semantic Search Available: {comparison.semantic_available}")
    print(f"📊 SQL Search Available: {comparison.sql_available}")
    
    if not comparison.sql_available:
        print("❌ SQL search not available - cannot proceed")
        return
    
    # Run comprehensive comparison
    results = comparison.run_comprehensive_comparison()
    
    # Print summary
    print("\n📈 FINAL ANALYSIS")
    print("=" * 80)
    
    analysis = results["analysis"]
    summary = analysis["summary"]
    performance = analysis["performance"]
    comparisons = analysis["comparisons"]
    
    print(f"✅ Total Tests Completed: {results['test_info']['total_tests']}")
    print(f"📁 Datasets Tested: {results['test_info']['datasets_tested']}")
    print(f"🔍 Queries Per Dataset: {results['test_info']['queries_per_dataset']}")
    
    print(f"\n🎯 SUCCESS RATES:")
    print(f"   • SQL Success Rate: {summary['sql_success_rate']:.1%}")
    print(f"   • Semantic Success Rate: {summary['semantic_success_rate']:.1%}")
    
    print(f"\n⚡ PERFORMANCE AVERAGES:")
    print(f"   • SQL Average Response: {performance['sql_avg_response_time']:.1f}ms")
    print(f"   • Semantic Average Response: {performance['semantic_avg_response_time']:.1f}ms")
    print(f"   • SQL Average Results: {performance['sql_avg_results']:.1f}")
    print(f"   • Semantic Average Results: {performance['semantic_avg_results']:.1f}")
    
    if comparisons['total_comparisons'] > 0:
        print(f"\n🏆 HEAD-TO-HEAD COMPARISONS:")
        print(f"   • Total Comparisons: {comparisons['total_comparisons']}")
        print(f"   • Semantic Faster: {comparisons['semantic_faster_count']}")
        print(f"   • SQL Faster: {comparisons['sql_faster_count']}")
        print(f"   • Semantic Better Accuracy: {comparisons['semantic_better_accuracy']}")
        print(f"   • SQL Better Accuracy: {comparisons['sql_better_accuracy']}")
        
        if 'avg_speed_difference' in performance:
            avg_diff = performance['avg_speed_difference']
            faster_method = "Semantic" if avg_diff < 0 else "SQL"
            print(f"   • Average Speed Advantage: {faster_method} by {abs(avg_diff):.1f}%")
    
    print(f"\n✨ Analysis complete! Detailed results saved.")

if __name__ == "__main__":
    main()