#!/usr/bin/env python3
"""
Focused test comparing semantic vs SQL retrieval on TypeScript collection.
"""

import os
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# Set API key
os.environ['VOYAGE_AI_API_KEY'] = 'pa-Fdhj97wixjABvuP4oGuOgNTgjoPM3-ovbmg-4VktTnL'

from qdrant_client import QdrantClient
import voyageai

@dataclass
class TestQuery:
    query: str
    category: str

@dataclass
class ComparisonResult:
    query: str
    sql_time_ms: float
    semantic_time_ms: float
    sql_results: int
    semantic_results: int
    sql_success: bool
    semantic_success: bool
    sql_sample: str
    semantic_sample: str

def test_sql_search(query: str) -> Dict[str, Any]:
    """Test SQL search on TypeScript database"""
    start_time = time.time()
    
    # Find TypeScript database
    ts_db = None
    for db_path in [
        '/workspaces/Code-Index-MCP/test_indexes/typescript_TypeScript/code_index.db',
        '/workspaces/Code-Index-MCP/test_indexes/microsoft_TypeScript/code_index.db'
    ]:
        if Path(db_path).exists():
            ts_db = db_path
            break
    
    if not ts_db:
        return {
            'success': False,
            'time_ms': 0,
            'results': [],
            'error': 'TypeScript database not found'
        }
    
    try:
        conn = sqlite3.connect(ts_db)
        cursor = conn.cursor()
        
        # Use BM25 FTS search
        search_query = "SELECT path, content FROM bm25_content WHERE bm25_content MATCH ? ORDER BY bm25(bm25_content) LIMIT 10"
        cursor.execute(search_query, (query,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'file': row[0],
                'content': row[1][:100] + '...' if len(row[1]) > 100 else row[1]
            })
        
        conn.close()
        end_time = time.time()
        
        return {
            'success': True,
            'time_ms': (end_time - start_time) * 1000,
            'results': results,
            'count': len(results)
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'time_ms': (end_time - start_time) * 1000,
            'results': [],
            'error': str(e)
        }

def test_semantic_search(query: str) -> Dict[str, Any]:
    """Test semantic search on TypeScript collection"""
    start_time = time.time()
    
    try:
        # Initialize clients
        qdrant_client = QdrantClient(path='/workspaces/Code-Index-MCP/vector_index.qdrant')
        voyage_client = voyageai.Client()
        
        # Generate embedding
        embedding = voyage_client.embed(
            [query],
            model="voyage-code-3",
            input_type="query",
            output_dimension=1024,
            output_dtype="float"
        ).embeddings[0]
        
        # Search TypeScript collection
        collection_name = "typescript-139900648006880"
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=10
        )
        
        results = []
        for result in search_results:
            payload = result.payload or {}
            results.append({
                'file': payload.get('relative_path', payload.get('file', 'unknown')),
                'symbol': payload.get('symbol', 'unknown'),
                'score': result.score,
                'content': payload.get('signature', '')[:100]
            })
        
        end_time = time.time()
        
        return {
            'success': True,
            'time_ms': (end_time - start_time) * 1000,
            'results': results,
            'count': len(results)
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'time_ms': (end_time - start_time) * 1000,
            'results': [],
            'error': str(e)
        }

def main():
    """Run focused comparison"""
    print("🔬 Focused Semantic vs SQL Comparison - TypeScript Dataset")
    print("=" * 80)
    
    # Test queries relevant to TypeScript
    test_queries = [
        TestQuery("function", "keyword"),
        TestQuery("class", "keyword"), 
        TestQuery("interface", "typescript_specific"),
        TestQuery("type", "typescript_specific"),
        TestQuery("async", "async_pattern"),
        TestQuery("export", "module_system"),
        TestQuery("import", "module_system")
    ]
    
    results = []
    
    for test_query in test_queries:
        print(f"\n🔍 Testing query: '{test_query.query}' ({test_query.category})")
        print("-" * 60)
        
        # Test SQL
        sql_result = test_sql_search(test_query.query)
        print(f"SQL: {sql_result['time_ms']:.1f}ms, {sql_result.get('count', 0)} results, Success: {sql_result['success']}")
        if sql_result['success'] and sql_result['results']:
            print(f"  Sample: {sql_result['results'][0]['file']}")
        
        # Test Semantic
        semantic_result = test_semantic_search(test_query.query)
        print(f"Semantic: {semantic_result['time_ms']:.1f}ms, {semantic_result.get('count', 0)} results, Success: {semantic_result['success']}")
        if semantic_result['success'] and semantic_result['results']:
            print(f"  Sample: {semantic_result['results'][0]['file']} (score: {semantic_result['results'][0]['score']:.3f})")
        
        # Calculate comparison
        if sql_result['success'] and semantic_result['success']:
            if sql_result['time_ms'] > 0:
                speed_diff = ((semantic_result['time_ms'] - sql_result['time_ms']) / sql_result['time_ms']) * 100
                faster = "SQL" if speed_diff > 0 else "Semantic"
                print(f"  → {faster} is {abs(speed_diff):.1f}% faster")
        
        # Store result
        comparison = ComparisonResult(
            query=test_query.query,
            sql_time_ms=sql_result['time_ms'],
            semantic_time_ms=semantic_result['time_ms'],
            sql_results=sql_result.get('count', 0),
            semantic_results=semantic_result.get('count', 0),
            sql_success=sql_result['success'],
            semantic_success=semantic_result['success'],
            sql_sample=str(sql_result['results'][0] if sql_result.get('results') else {}),
            semantic_sample=str(semantic_result['results'][0] if semantic_result.get('results') else {})
        )
        results.append(comparison)
    
    # Generate summary
    print(f"\n📈 SUMMARY ANALYSIS")
    print("=" * 80)
    
    successful_comparisons = [r for r in results if r.sql_success and r.semantic_success]
    
    if successful_comparisons:
        sql_avg_time = sum(r.sql_time_ms for r in successful_comparisons) / len(successful_comparisons)
        semantic_avg_time = sum(r.semantic_time_ms for r in successful_comparisons) / len(successful_comparisons)
        sql_avg_results = sum(r.sql_results for r in successful_comparisons) / len(successful_comparisons)
        semantic_avg_results = sum(r.semantic_results for r in successful_comparisons) / len(successful_comparisons)
        
        speed_advantage = ((semantic_avg_time - sql_avg_time) / sql_avg_time) * 100 if sql_avg_time > 0 else 0
        faster_method = "SQL" if speed_advantage > 0 else "Semantic"
        
        print(f"✅ Successful Comparisons: {len(successful_comparisons)}/{len(results)}")
        print(f"⚡ SQL Average Response: {sql_avg_time:.1f}ms")
        print(f"⚡ Semantic Average Response: {semantic_avg_time:.1f}ms") 
        print(f"📊 SQL Average Results: {sql_avg_results:.1f}")
        print(f"📊 Semantic Average Results: {semantic_avg_results:.1f}")
        print(f"🏆 {faster_method} is {abs(speed_advantage):.1f}% faster on average")
        
        # Save detailed results
        timestamp = int(time.time())
        results_file = f"focused_semantic_vs_sql_{timestamp}.json"
        
        output_data = {
            "test_info": {
                "timestamp": time.time(),
                "dataset": "TypeScript",
                "total_queries": len(results),
                "successful_comparisons": len(successful_comparisons)
            },
            "summary": {
                "sql_avg_time_ms": sql_avg_time,
                "semantic_avg_time_ms": semantic_avg_time,
                "sql_avg_results": sql_avg_results,
                "semantic_avg_results": semantic_avg_results,
                "speed_advantage": speed_advantage,
                "faster_method": faster_method
            },
            "detailed_results": [asdict(r) for r in results]
        }
        
        with open(results_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 Detailed results saved to: {results_file}")
    else:
        print("❌ No successful comparisons to analyze")

if __name__ == "__main__":
    main()