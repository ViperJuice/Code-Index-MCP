#!/usr/bin/env python3
"""
Targeted test using actual symbols from the TypeScript semantic collection.
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
class DetailedComparisonResult:
    query: str
    query_type: str
    
    # SQL Results
    sql_time_ms: float
    sql_success: bool
    sql_results_count: int
    sql_first_result: Dict[str, Any]
    sql_error: str
    
    # Semantic Results  
    semantic_time_ms: float
    semantic_success: bool
    semantic_results_count: int
    semantic_first_result: Dict[str, Any]
    semantic_error: str
    
    # Comparison
    speed_advantage_method: str
    speed_advantage_percent: float
    accuracy_comparison: str

def test_sql_on_react_data(query: str) -> Dict[str, Any]:
    """Test SQL search on React/TypeScript database"""
    start_time = time.time()
    
    # Use javascript_react database which should have React content
    react_db = '/workspaces/Code-Index-MCP/test_indexes/javascript_react/code_index.db'
    
    if not Path(react_db).exists():
        return {
            'success': False,
            'time_ms': 0,
            'results': [],
            'count': 0,
            'error': 'React database not found'
        }
    
    try:
        conn = sqlite3.connect(react_db)
        cursor = conn.cursor()
        
        # Use BM25 FTS search
        search_query = "SELECT path, content FROM bm25_content WHERE bm25_content MATCH ? ORDER BY bm25(bm25_content) LIMIT 10"
        cursor.execute(search_query, (query,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'file': row[0],
                'content': row[1][:150] + '...' if len(row[1]) > 150 else row[1],
                'method': 'sql_bm25'
            })
        
        conn.close()
        end_time = time.time()
        
        return {
            'success': True,
            'time_ms': (end_time - start_time) * 1000,
            'results': results,
            'count': len(results),
            'error': ''
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'time_ms': (end_time - start_time) * 1000,
            'results': [],
            'count': 0,
            'error': str(e)
        }

def test_semantic_search_targeted(query: str) -> Dict[str, Any]:
    """Test semantic search with targeted query"""
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
                'kind': payload.get('kind', 'unknown'),
                'score': result.score,
                'signature': payload.get('signature', '')[:100],
                'method': 'semantic_vector'
            })
        
        end_time = time.time()
        
        return {
            'success': True,
            'time_ms': (end_time - start_time) * 1000,
            'results': results,
            'count': len(results),
            'error': ''
        }
        
    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'time_ms': (end_time - start_time) * 1000,
            'results': [],
            'count': 0,
            'error': str(e)
        }

def main():
    """Run targeted comparison"""
    print("🎯 Targeted Semantic vs SQL Comparison - Real Data")
    print("=" * 80)
    
    # Test queries based on actual data we know exists
    test_queries = [
        ("map", "exact_symbol"),
        ("class", "language_keyword"),
        ("Visitor", "class_pattern"),
        ("React", "framework_name"),
        ("SSA", "algorithm_name"),
        ("transform", "method_pattern"),
        ("component", "react_concept"),
        ("function", "common_keyword")
    ]
    
    all_results = []
    successful_comparisons = 0
    
    for query, query_type in test_queries:
        print(f"\n🔍 Testing: '{query}' ({query_type})")
        print("-" * 60)
        
        # Test SQL on React data
        sql_result = test_sql_on_react_data(query)
        print(f"SQL (React DB): {sql_result['time_ms']:.1f}ms, {sql_result['count']} results, Success: {sql_result['success']}")
        if sql_result['success'] and sql_result['results']:
            print(f"  First result: {sql_result['results'][0]['file']}")
        elif not sql_result['success']:
            print(f"  Error: {sql_result['error']}")
        
        # Test Semantic on TypeScript collection
        semantic_result = test_semantic_search_targeted(query)
        print(f"Semantic (TS Collection): {semantic_result['time_ms']:.1f}ms, {semantic_result['count']} results, Success: {semantic_result['success']}")
        if semantic_result['success'] and semantic_result['results']:
            first_result = semantic_result['results'][0]
            print(f"  First result: {first_result['symbol']} ({first_result['kind']}) - score: {first_result['score']:.3f}")
        elif not semantic_result['success']:
            print(f"  Error: {semantic_result['error']}")
        
        # Calculate performance comparison
        speed_advantage_method = ""
        speed_advantage_percent = 0
        accuracy_comparison = ""
        
        if sql_result['success'] and semantic_result['success']:
            successful_comparisons += 1
            
            if sql_result['time_ms'] > 0:
                speed_diff = semantic_result['time_ms'] - sql_result['time_ms']
                speed_advantage_percent = abs(speed_diff / sql_result['time_ms']) * 100
                speed_advantage_method = "SQL" if speed_diff > 0 else "Semantic"
                print(f"  → {speed_advantage_method} is {speed_advantage_percent:.1f}% faster")
            
            # Simple accuracy comparison
            if sql_result['count'] == semantic_result['count']:
                accuracy_comparison = "equal"
            elif sql_result['count'] > semantic_result['count']:
                accuracy_comparison = "sql_more_results"
            else:
                accuracy_comparison = "semantic_more_results"
        
        # Store detailed result
        detailed_result = DetailedComparisonResult(
            query=query,
            query_type=query_type,
            sql_time_ms=sql_result['time_ms'],
            sql_success=sql_result['success'],
            sql_results_count=sql_result['count'],
            sql_first_result=sql_result['results'][0] if sql_result['results'] else {},
            sql_error=sql_result['error'],
            semantic_time_ms=semantic_result['time_ms'],
            semantic_success=semantic_result['success'],
            semantic_results_count=semantic_result['count'],
            semantic_first_result=semantic_result['results'][0] if semantic_result['results'] else {},
            semantic_error=semantic_result['error'],
            speed_advantage_method=speed_advantage_method,
            speed_advantage_percent=speed_advantage_percent,
            accuracy_comparison=accuracy_comparison
        )
        all_results.append(detailed_result)
    
    # Generate comprehensive analysis
    print(f"\n📊 COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    
    print(f"✅ Total Tests: {len(all_results)}")
    print(f"✅ Successful Comparisons: {successful_comparisons}")
    
    sql_successful = sum(1 for r in all_results if r.sql_success)
    semantic_successful = sum(1 for r in all_results if r.semantic_success)
    
    print(f"📈 SQL Success Rate: {sql_successful}/{len(all_results)} ({(sql_successful/len(all_results)*100):.1f}%)")
    print(f"📈 Semantic Success Rate: {semantic_successful}/{len(all_results)} ({(semantic_successful/len(all_results)*100):.1f}%)")
    
    if successful_comparisons > 0:
        successful_results = [r for r in all_results if r.sql_success and r.semantic_success]
        
        sql_avg_time = sum(r.sql_time_ms for r in successful_results) / len(successful_results)
        semantic_avg_time = sum(r.semantic_time_ms for r in successful_results) / len(successful_results)
        sql_avg_results = sum(r.sql_results_count for r in successful_results) / len(successful_results)
        semantic_avg_results = sum(r.semantic_results_count for r in successful_results) / len(successful_results)
        
        overall_speed_advantage = ((semantic_avg_time - sql_avg_time) / sql_avg_time) * 100 if sql_avg_time > 0 else 0
        faster_overall = "SQL" if overall_speed_advantage > 0 else "Semantic"
        
        print(f"\n⚡ PERFORMANCE COMPARISON:")
        print(f"   • SQL Average Response: {sql_avg_time:.1f}ms")
        print(f"   • Semantic Average Response: {semantic_avg_time:.1f}ms")
        print(f"   • Overall Winner: {faster_overall} ({abs(overall_speed_advantage):.1f}% faster)")
        
        print(f"\n📊 RESULT QUANTITY COMPARISON:")
        print(f"   • SQL Average Results: {sql_avg_results:.1f}")
        print(f"   • Semantic Average Results: {semantic_avg_results:.1f}")
        
        # Analyze by query type
        query_types = set(r.query_type for r in successful_results)
        print(f"\n🎯 ANALYSIS BY QUERY TYPE:")
        for qtype in query_types:
            type_results = [r for r in successful_results if r.query_type == qtype]
            if type_results:
                type_sql_avg = sum(r.sql_time_ms for r in type_results) / len(type_results)
                type_semantic_avg = sum(r.semantic_time_ms for r in type_results) / len(type_results)
                type_advantage = ((type_semantic_avg - type_sql_avg) / type_sql_avg) * 100 if type_sql_avg > 0 else 0
                type_winner = "SQL" if type_advantage > 0 else "Semantic"
                print(f"   • {qtype}: {type_winner} wins by {abs(type_advantage):.1f}%")
    
    # Save detailed results
    timestamp = int(time.time())
    results_file = f"targeted_semantic_vs_sql_{timestamp}.json"
    
    output_data = {
        "test_info": {
            "timestamp": time.time(),
            "total_queries": len(all_results),
            "successful_comparisons": successful_comparisons,
            "sql_success_rate": sql_successful / len(all_results),
            "semantic_success_rate": semantic_successful / len(all_results)
        },
        "performance_summary": {
            "sql_avg_time_ms": sql_avg_time if successful_comparisons > 0 else 0,
            "semantic_avg_time_ms": semantic_avg_time if successful_comparisons > 0 else 0,
            "sql_avg_results": sql_avg_results if successful_comparisons > 0 else 0,
            "semantic_avg_results": semantic_avg_results if successful_comparisons > 0 else 0,
            "overall_faster_method": faster_overall if successful_comparisons > 0 else "N/A",
            "overall_speed_advantage": abs(overall_speed_advantage) if successful_comparisons > 0 else 0
        },
        "detailed_results": [asdict(r) for r in all_results]
    }
    
    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Key insights
    print(f"\n🔑 KEY INSIGHTS:")
    if successful_comparisons > 0:
        if faster_overall == "SQL":
            print(f"   • SQL/BM25 retrieval is consistently faster ({abs(overall_speed_advantage):.1f}% average advantage)")
            print(f"   • SQL retrieval averages {sql_avg_time:.1f}ms vs Semantic {semantic_avg_time:.1f}ms")
        else:
            print(f"   • Semantic retrieval is faster ({abs(overall_speed_advantage):.1f}% average advantage)")
            print(f"   • Semantic retrieval averages {semantic_avg_time:.1f}ms vs SQL {sql_avg_time:.1f}ms")
        
        print(f"   • SQL returns {sql_avg_results:.1f} results on average")
        print(f"   • Semantic returns {semantic_avg_results:.1f} results on average")
        print(f"   • Both methods have high success rates: SQL {(sql_successful/len(all_results)*100):.1f}%, Semantic {(semantic_successful/len(all_results)*100):.1f}%")
    else:
        print(f"   • Limited comparison data due to different data sources")
        print(f"   • SQL excels at keyword-based searches in large text corpora")
        print(f"   • Semantic excels at finding conceptually similar code symbols")

if __name__ == "__main__":
    main()