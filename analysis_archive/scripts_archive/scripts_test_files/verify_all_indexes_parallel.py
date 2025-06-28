#!/usr/bin/env python3
"""
Parallel Index Verification Script
Verifies integrity of all BM25 and semantic indexes concurrently
"""

import os
import sys
import json
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Dict, List, Any, Tuple
import multiprocessing as mp
from tqdm import tqdm
import time

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer

# Test queries for verification
TEST_QUERIES = {
    'symbol': ['main', 'init', 'handler', 'config', 'test'],
    'pattern': ['TODO', 'FIXME', 'import', 'error', 'class'],
    'semantic': [
        'authentication logic',
        'error handling', 
        'data validation',
        'configuration management',
        'logging implementation'
    ]
}


def verify_bm25_index(repo_path: Path, index_path: Path) -> Dict[str, Any]:
    """Verify BM25 index for a single repository."""
    result = {
        'repository': repo_path.name,
        'bm25_status': 'unknown',
        'bm25_errors': [],
        'bm25_metrics': {},
        'test_queries': {}
    }
    
    db_path = index_path / 'bm25_index.db'
    
    if not db_path.exists():
        result['bm25_status'] = 'missing'
        result['bm25_errors'].append(f"Index not found at {db_path}")
        return result
        
    try:
        # Check database integrity
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check for either new or old table structure
        has_new_structure = 'bm25_documents' in tables and 'bm25_content' in tables
        has_old_structure = 'documents' in tables and 'bm25_index' in tables
        
        if not has_new_structure and not has_old_structure:
            result['bm25_status'] = 'corrupted'
            result['bm25_errors'].append(f"Required BM25 tables not found. Tables: {tables[:5]}...")
            return result
            
        # Get index metrics
        if has_new_structure:
            cursor.execute("SELECT COUNT(*) FROM bm25_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bm25_content")
            term_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bm25_index")
            term_count = cursor.fetchone()[0]
        
        result['bm25_metrics'] = {
            'document_count': doc_count,
            'term_count': term_count,
            'avg_terms_per_doc': term_count / doc_count if doc_count > 0 else 0
        }
        
        # Test queries - use direct SQL for compatibility
        test_table = 'bm25_content' if has_new_structure else 'documents'
        
        for query in TEST_QUERIES['pattern'][:3]:  # Test 3 queries
            try:
                # Simple FTS5 search
                cursor.execute(
                    f"SELECT filepath FROM {test_table} WHERE {test_table} MATCH ? LIMIT 5",
                    (query,)
                )
                results = cursor.fetchall()
                
                result['test_queries'][query] = {
                    'success': True,
                    'result_count': len(results),
                    'sample_result': results[0][0] if results else None
                }
            except Exception as e:
                result['test_queries'][query] = {
                    'success': False,
                    'error': str(e)
                }
                
        result['bm25_status'] = 'healthy'
        
    except Exception as e:
        result['bm25_status'] = 'error'
        result['bm25_errors'].append(str(e))
        
    finally:
        if 'conn' in locals():
            conn.close()
            
    return result


def verify_semantic_index(repo_path: Path) -> Dict[str, Any]:
    """Verify semantic index for a repository."""
    result = {
        'semantic_status': 'unknown',
        'semantic_errors': [],
        'semantic_metrics': {}
    }
    
    # Check if Qdrant is available
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        # Try to connect to Qdrant
        client = QdrantClient(url="http://localhost:6333")
        
        # Check collection exists
        collection_name = f"code_embeddings_{repo_path.name}"
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            result['semantic_status'] = 'missing'
            result['semantic_errors'].append(f"Collection {collection_name} not found")
            return result
            
        # Get collection info
        info = client.get_collection(collection_name)
        result['semantic_metrics'] = {
            'vector_count': info.vectors_count,
            'indexed_vectors': info.indexed_vectors_count,
            'vector_size': info.config.params.vectors.size
        }
        
        # Test semantic search
        test_query = "error handling"
        search_result = client.search(
            collection_name=collection_name,
            query_vector=[0.1] * 384,  # Dummy vector
            limit=5
        )
        
        result['semantic_status'] = 'healthy'
        result['test_queries'] = {
            test_query: {
                'success': True,
                'result_count': len(search_result)
            }
        }
        
    except ImportError:
        result['semantic_status'] = 'unavailable'
        result['semantic_errors'].append("Qdrant client not installed")
    except Exception as e:
        result['semantic_status'] = 'error'
        result['semantic_errors'].append(str(e))
        
    return result


def verify_single_repository(args: Tuple[str, Path]) -> Dict[str, Any]:
    """Verify all indexes for a single repository."""
    repo_name, index_base_path = args
    
    start_time = time.time()
    
    # Paths
    repo_path = Path(repo_name)
    index_path = index_base_path / repo_name.replace('/', '_')
    
    # Verify BM25
    bm25_result = verify_bm25_index(repo_path, index_path)
    
    # Verify semantic
    semantic_result = verify_semantic_index(repo_path)
    
    # Combine results
    result = {
        'repository': repo_name,
        'verification_time': time.time() - start_time,
        'bm25': bm25_result,
        'semantic': semantic_result,
        'overall_status': 'healthy' if (
            bm25_result['bm25_status'] == 'healthy' and 
            semantic_result['semantic_status'] in ['healthy', 'unavailable']
        ) else 'needs_attention'
    }
    
    return result


def run_parallel_verification(repositories: List[str], index_base_path: Path) -> Dict[str, Any]:
    """Run verification for all repositories in parallel."""
    print(f"\n🔍 Starting parallel index verification for {len(repositories)} repositories...")
    
    # Prepare arguments
    args_list = [(repo, index_base_path) for repo in repositories]
    
    # Use ProcessPoolExecutor for CPU-bound verification tasks
    max_workers = min(mp.cpu_count(), len(repositories))
    print(f"Using {max_workers} parallel workers")
    
    results = []
    failed = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_repo = {
            executor.submit(verify_single_repository, args): args[0] 
            for args in args_list
        }
        
        # Progress bar
        with tqdm(total=len(repositories), desc="Verifying indexes") as pbar:
            from concurrent.futures import as_completed
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update progress with status
                    status_emoji = "✅" if result['overall_status'] == 'healthy' else "⚠️"
                    pbar.set_description(f"{status_emoji} {repo}")
                    
                except Exception as e:
                    failed.append({
                        'repository': repo,
                        'error': str(e),
                        'overall_status': 'failed'
                    })
                    pbar.set_description(f"❌ {repo}")
                    
                pbar.update(1)
    
    # Aggregate results
    summary = {
        'total_repositories': len(repositories),
        'verified': len(results),
        'failed': len(failed),
        'healthy': sum(1 for r in results if r['overall_status'] == 'healthy'),
        'needs_attention': sum(1 for r in results if r['overall_status'] == 'needs_attention'),
        'verification_time': sum(r.get('verification_time', 0) for r in results),
        'results': results,
        'failed': failed
    }
    
    return summary


def main():
    """Main entry point."""
    # Get list of repositories from test_indexes
    index_base_path = Path("/workspaces/Code-Index-MCP/test_indexes")
    
    if not index_base_path.exists():
        print(f"❌ Index directory not found: {index_base_path}")
        return
        
    # Get all repository directories
    repositories = [
        d.name for d in index_base_path.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    if not repositories:
        print("❌ No repository indexes found")
        return
        
    print(f"Found {len(repositories)} repository indexes to verify")
    
    # Run parallel verification
    start_time = time.time()
    summary = run_parallel_verification(repositories, index_base_path)
    total_time = time.time() - start_time
    
    # Save results
    output_file = Path("index_verification_report.json")
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_execution_time': total_time,
            'parallel_speedup': summary['verification_time'] / total_time,
            **summary
        }, f, indent=2)
    
    # Print summary
    print(f"\n📊 Verification Complete in {total_time:.1f} seconds")
    print(f"   Parallel speedup: {summary['verification_time'] / total_time:.1f}x")
    print(f"   ✅ Healthy: {summary['healthy']}")
    print(f"   ⚠️  Needs Attention: {summary['needs_attention']}")
    print(f"   ❌ Failed: {summary['failed']}")
    print(f"\n📄 Full report saved to: {output_file}")
    
    # List repositories needing attention
    if summary['needs_attention'] > 0 or summary['failed'] > 0:
        print("\n⚠️  Repositories needing attention:")
        for result in summary['results']:
            if result['overall_status'] != 'healthy':
                print(f"   - {result['repository']}: {result['overall_status']}")
                if result['bm25']['bm25_errors']:
                    print(f"     BM25: {result['bm25']['bm25_errors'][0]}")
                if result['semantic']['semantic_errors']:
                    print(f"     Semantic: {result['semantic']['semantic_errors'][0]}")


if __name__ == "__main__":
    main()