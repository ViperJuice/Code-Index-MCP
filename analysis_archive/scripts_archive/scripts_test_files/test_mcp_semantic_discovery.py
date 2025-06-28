#!/usr/bin/env python3
"""
Test MCP semantic database discovery and compare with SQL retrieval.
"""

import os
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# Set API key from .env file
from dotenv import load_dotenv
load_dotenv()

try:
    from qdrant_client import QdrantClient
    import voyageai
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

@dataclass
class MCPComparisonResult:
    query: str
    
    # SQL BM25 Results (from main current.db)
    sql_time_ms: float
    sql_success: bool
    sql_results_count: int
    sql_first_result: str
    sql_error: str
    
    # Semantic Results (from .indexes/qdrant)
    semantic_time_ms: float
    semantic_success: bool
    semantic_results_count: int
    semantic_first_result: str
    semantic_error: str
    
    # Performance comparison
    speed_winner: str
    speed_advantage_percent: float

def test_current_codebase_sql(query: str) -> Dict[str, Any]:
    """Test SQL search on current codebase index"""
    start_time = time.time()
    
    # Use the main codebase index
    main_db = "/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/current.db"
    
    if not Path(main_db).exists():
        return {
            'success': False,
            'time_ms': 0,
            'results': [],
            'count': 0,
            'error': f'Main database not found: {main_db}'
        }
    
    try:
        conn = sqlite3.connect(main_db)
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        results = []
        
        if 'bm25_content' in tables:
            # Use BM25 FTS search
            search_query = "SELECT path, content FROM bm25_content WHERE bm25_content MATCH ? ORDER BY bm25(bm25_content) LIMIT 10"
            cursor.execute(search_query, (query,))
            
            for row in cursor.fetchall():
                results.append({
                    'file': row[0],
                    'content': row[1][:100] + '...' if len(row[1]) > 100 else row[1]
                })
        elif 'symbols' in tables:
            # Fallback to symbols table
            search_query = "SELECT name, kind, file_path, signature FROM symbols WHERE name LIKE ? OR signature LIKE ? LIMIT 10"
            search_term = f"%{query}%"
            cursor.execute(search_query, (search_term, search_term))
            
            for row in cursor.fetchall():
                results.append({
                    'symbol': row[0],
                    'kind': row[1],
                    'file': row[2],
                    'signature': row[3][:100] if row[3] else ''
                })
        else:
            raise Exception(f"No searchable tables found. Available: {tables}")
        
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

def test_current_codebase_semantic(query: str) -> Dict[str, Any]:
    """Test semantic search on current codebase"""
    start_time = time.time()
    
    if not SEMANTIC_AVAILABLE:
        return {
            'success': False,
            'time_ms': 0,
            'results': [],
            'count': 0,
            'error': 'Semantic search dependencies not available'
        }
    
    try:
        # Initialize clients with proper paths
        qdrant_path = "/workspaces/Code-Index-MCP/.indexes/qdrant/main.qdrant"
        
        if not Path(qdrant_path).exists():
            return {
                'success': False,
                'time_ms': 0,
                'results': [],
                'count': 0,
                'error': f'Qdrant index not found: {qdrant_path}'
            }
        
        qdrant_client = QdrantClient(path=qdrant_path)
        
        # Check what collections are available
        collections = qdrant_client.get_collections()
        if not collections.collections:
            return {
                'success': False,
                'time_ms': 0,
                'results': [],
                'count': 0,
                'error': 'No collections found in semantic index'
            }
        
        # Use the first available collection (should be code-embeddings or similar)
        collection_name = collections.collections[0].name
        collection_info = qdrant_client.get_collection(collection_name)
        
        if collection_info.points_count == 0:
            # Try other collections if first is empty
            for collection in collections.collections[1:]:
                collection_info = qdrant_client.get_collection(collection.name)
                if collection_info.points_count > 0:
                    collection_name = collection.name
                    break
        
        if collection_info.points_count == 0:
            return {
                'success': False,
                'time_ms': 0,
                'results': [],
                'count': 0,
                'error': f'All collections empty. Available: {[c.name for c in collections.collections]}'
            }
        
        # Initialize Voyage AI client
        voyage_client = voyageai.Client()
        
        # Generate embedding
        embedding = voyage_client.embed(
            [query],
            model="voyage-code-3",
            input_type="query",
            output_dimension=1024,
            output_dtype="float"
        ).embeddings[0]
        
        # Search the collection
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
                'symbol': payload.get('symbol', payload.get('title', 'unknown')),
                'kind': payload.get('kind', payload.get('type', 'unknown')),
                'score': result.score,
                'content': payload.get('signature', payload.get('content', ''))[:100]
            })
        
        end_time = time.time()
        
        return {
            'success': True,
            'time_ms': (end_time - start_time) * 1000,
            'results': results,
            'count': len(results),
            'error': '',
            'collection_used': collection_name,
            'collection_points': collection_info.points_count
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
    """Run MCP-aware semantic vs SQL comparison"""
    print("🧭 MCP Semantic Database Discovery & Comparison")
    print("=" * 80)
    
    # Test queries relevant to the current codebase
    test_queries = [
        "SemanticIndexer",
        "BM25Indexer", 
        "SQLiteStore",
        "EnhancedDispatcher",
        "PluginFactory",
        "function",
        "class",
        "index"
    ]
    
    all_results = []
    successful_comparisons = 0
    
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        print("-" * 60)
        
        # Test SQL on current codebase
        sql_result = test_current_codebase_sql(query)
        print(f"SQL (Current DB): {sql_result['time_ms']:.1f}ms, {sql_result['count']} results, Success: {sql_result['success']}")
        if sql_result['success'] and sql_result['results']:
            first_result = sql_result['results'][0]
            result_key = 'file' if 'file' in first_result else 'symbol'
            print(f"  First result: {first_result.get(result_key, 'unknown')}")
        elif not sql_result['success']:
            print(f"  Error: {sql_result['error']}")
        
        # Test semantic on current codebase
        semantic_result = test_current_codebase_semantic(query)
        print(f"Semantic (MCP Index): {semantic_result['time_ms']:.1f}ms, {semantic_result['count']} results, Success: {semantic_result['success']}")
        if semantic_result['success'] and semantic_result['results']:
            first_result = semantic_result['results'][0]
            print(f"  First result: {first_result['symbol']} in {first_result['file']} (score: {first_result['score']:.3f})")
            print(f"  Collection: {semantic_result.get('collection_used')} ({semantic_result.get('collection_points')} points)")
        elif not semantic_result['success']:
            print(f"  Error: {semantic_result['error']}")
        
        # Calculate comparison
        speed_winner = ""
        speed_advantage = 0
        
        if sql_result['success'] and semantic_result['success']:
            successful_comparisons += 1
            
            if sql_result['time_ms'] > 0:
                speed_diff = semantic_result['time_ms'] - sql_result['time_ms']
                speed_advantage = abs(speed_diff / sql_result['time_ms']) * 100
                speed_winner = "SQL" if speed_diff > 0 else "Semantic"
                print(f"  → {speed_winner} is {speed_advantage:.1f}% faster")
        
        # Store result
        comparison = MCPComparisonResult(
            query=query,
            sql_time_ms=sql_result['time_ms'],
            sql_success=sql_result['success'],
            sql_results_count=sql_result['count'],
            sql_first_result=str(sql_result['results'][0] if sql_result['results'] else {}),
            sql_error=sql_result['error'],
            semantic_time_ms=semantic_result['time_ms'],
            semantic_success=semantic_result['success'],
            semantic_results_count=semantic_result['count'],
            semantic_first_result=str(semantic_result['results'][0] if semantic_result['results'] else {}),
            semantic_error=semantic_result['error'],
            speed_winner=speed_winner,
            speed_advantage_percent=speed_advantage
        )
        all_results.append(comparison)
    
    # Generate analysis
    print(f"\n📊 FINAL ANALYSIS")
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
        
        print(f"\n⚡ PERFORMANCE SUMMARY:")
        print(f"   • SQL Average Response: {sql_avg_time:.1f}ms")
        print(f"   • Semantic Average Response: {semantic_avg_time:.1f}ms")
        print(f"   • Overall Faster Method: {faster_overall} ({abs(overall_speed_advantage):.1f}% advantage)")
        print(f"   • SQL Average Results: {sql_avg_results:.1f}")
        print(f"   • Semantic Average Results: {semantic_avg_results:.1f}")
        
        # Count wins
        semantic_wins = sum(1 for r in successful_results if r.speed_winner == "Semantic")
        sql_wins = sum(1 for r in successful_results if r.speed_winner == "SQL")
        
        print(f"\n🏆 HEAD-TO-HEAD RESULTS:")
        print(f"   • Semantic Wins: {semantic_wins}/{successful_comparisons}")
        print(f"   • SQL Wins: {sql_wins}/{successful_comparisons}")
    
    # Save results
    timestamp = int(time.time())
    results_file = f"mcp_semantic_vs_sql_{timestamp}.json"
    
    output_data = {
        "test_info": {
            "timestamp": time.time(),
            "total_queries": len(all_results),
            "successful_comparisons": successful_comparisons,
            "codebase": "/workspaces/Code-Index-MCP",
            "sql_database": ".indexes/f7b49f5d0ae0/current.db",
            "semantic_database": ".indexes/qdrant/main.qdrant"
        },
        "summary": {
            "sql_success_rate": sql_successful / len(all_results),
            "semantic_success_rate": semantic_successful / len(all_results),
            "sql_avg_time_ms": sql_avg_time if successful_comparisons > 0 else 0,
            "semantic_avg_time_ms": semantic_avg_time if successful_comparisons > 0 else 0,
            "overall_faster_method": faster_overall if successful_comparisons > 0 else "N/A",
            "overall_speed_advantage": abs(overall_speed_advantage) if successful_comparisons > 0 else 0
        },
        "detailed_results": [asdict(r) for r in all_results]
    }
    
    with open(results_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    main()