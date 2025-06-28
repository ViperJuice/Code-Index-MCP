#!/usr/bin/env python3
"""
Verify MCP functionality with all retrieval methods.
Tests SQL BM25, SQL FTS, Semantic, and Hybrid search.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
import subprocess
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mcp_tool(tool_name: str, args: List[str]) -> Dict[str, Any]:
    """Test an MCP tool and return results."""
    start_time = time.time()
    
    try:
        # Build command
        cmd = [
            sys.executable,
            "scripts/cli/mcp_server_cli.py",
            tool_name
        ] + args
        
        # Set environment
        env = os.environ.copy()
        env['SEMANTIC_SEARCH_ENABLED'] = 'true'
        env['MCP_INDEX_STORAGE_PATH'] = 'PathUtils.get_workspace_root()/.indexes'
        
        logger.info(f"Testing {tool_name} with: {' '.join(args[:2])}...")
        
        # Run command
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        # Parse results
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        
        # Count results
        result_count = 0
        if success and output:
            # Count different result patterns
            result_count += output.count('\n---')  # Result separators
            result_count += output.count('File:')  # File results
            result_count += output.count('Symbol:')  # Symbol results
            
        return {
            'tool': tool_name,
            'args': args,
            'success': success,
            'time': elapsed,
            'result_count': result_count,
            'output_preview': output[:500] if output else '',
            'error': result.stderr if not success else None
        }
        
    except subprocess.TimeoutExpired:
        return {
            'tool': tool_name,
            'args': args,
            'success': False,
            'time': 30.0,
            'result_count': 0,
            'error': 'Timeout after 30 seconds'
        }
    except Exception as e:
        return {
            'tool': tool_name,
            'args': args,
            'success': False,
            'time': time.time() - start_time,
            'result_count': 0,
            'error': str(e)
        }


def verify_sql_search():
    """Verify SQL-based search methods."""
    logger.info("\n" + "="*60)
    logger.info("Testing SQL-based Search Methods")
    logger.info("="*60)
    
    results = []
    
    # Test queries
    test_queries = [
        ("symbol search", ["symbol_lookup", "useState"]),
        ("code search", ["search_code", "async function"]),
        ("file search", ["search_code", "README.md"]),
        ("bm25 search", ["search_code", "--semantic", "false", "authentication"]),
    ]
    
    for desc, args in test_queries:
        logger.info(f"\nTesting {desc}...")
        result = test_mcp_tool("search", args)
        results.append(result)
        
        if result['success']:
            logger.info(f"✅ {desc}: {result['result_count']} results in {result['time']:.2f}s")
        else:
            logger.error(f"❌ {desc} failed: {result['error']}")
    
    return results


def verify_semantic_search():
    """Verify semantic search functionality."""
    logger.info("\n" + "="*60)
    logger.info("Testing Semantic Search")
    logger.info("="*60)
    
    results = []
    
    # Test semantic queries
    test_queries = [
        ("semantic code", ["search_code", "--semantic", "true", "implement authentication"]),
        ("semantic concept", ["search_code", "--semantic", "true", "handle user login"]),
        ("semantic similar", ["search_code", "--semantic", "true", "process HTTP requests"]),
    ]
    
    for desc, args in test_queries:
        logger.info(f"\nTesting {desc}...")
        result = test_mcp_tool("search", args)
        results.append(result)
        
        if result['success']:
            logger.info(f"✅ {desc}: {result['result_count']} results in {result['time']:.2f}s")
            if result['output_preview']:
                logger.info(f"Preview: {result['output_preview'][:200]}...")
        else:
            logger.error(f"❌ {desc} failed: {result['error']}")
    
    return results


def verify_hybrid_search():
    """Verify hybrid search functionality."""
    logger.info("\n" + "="*60)
    logger.info("Testing Hybrid Search (BM25 + Semantic)")
    logger.info("="*60)
    
    results = []
    
    # Test hybrid queries
    test_queries = [
        ("hybrid search", ["search_code", "--hybrid", "true", "database connection"]),
        ("hybrid complex", ["search_code", "--hybrid", "true", "parse JSON data"]),
    ]
    
    for desc, args in test_queries:
        logger.info(f"\nTesting {desc}...")
        result = test_mcp_tool("search", args)
        results.append(result)
        
        if result['success']:
            logger.info(f"✅ {desc}: {result['result_count']} results in {result['time']:.2f}s")
        else:
            logger.error(f"❌ {desc} failed: {result['error']}")
    
    return results


def test_direct_mcp_api():
    """Test direct MCP API access."""
    logger.info("\n" + "="*60)
    logger.info("Testing Direct MCP API Access")
    logger.info("="*60)
    
    try:
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
        from mcp_server.plugin_system import PluginManager
        
        # Test SQL store
        logger.info("\nTesting SQLiteStore...")
        store = SQLiteStore(".indexes/d8df70cdcd6e/code_index.db")
        
        # Test BM25 search
        results = store.search_bm25("django", limit=5)
        logger.info(f"✅ BM25 search: {len(results)} results")
        
        # Test FTS search
        results = store.search_fts("class", limit=5)
        logger.info(f"✅ FTS search: {len(results)} results")
        
        # Test symbol search
        results = store.search_symbols("View", limit=5)
        logger.info(f"✅ Symbol search: {len(results)} results")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct API test failed: {e}")
        return False


def verify_index_availability():
    """Verify that indexes are available and accessible."""
    logger.info("\n" + "="*60)
    logger.info("Verifying Index Availability")
    logger.info("="*60)
    
    indexes_dir = Path(".indexes")
    sql_count = 0
    
    # Check SQL indexes
    for idx_dir in indexes_dir.iterdir():
        if idx_dir.is_dir() and idx_dir.name not in ['qdrant', 'artifacts']:
            db_files = list(idx_dir.glob("*.db"))
            if db_files:
                sql_count += 1
    
    logger.info(f"✅ Found {sql_count} SQL indexes")
    
    # Check Qdrant
    qdrant_path = indexes_dir / "qdrant" / "main.qdrant"
    if qdrant_path.exists():
        logger.info(f"✅ Qdrant database found at {qdrant_path}")
        
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(path=str(qdrant_path))
            collections = client.get_collections()
            logger.info(f"✅ Found {len(collections.collections)} Qdrant collections")
        except Exception as e:
            logger.error(f"❌ Failed to access Qdrant: {e}")
    else:
        logger.error("❌ Qdrant database not found")
    
    return sql_count > 0


def main():
    """Main verification function."""
    logger.info("MCP Retrieval Methods Verification")
    logger.info("="*80)
    logger.info("This will test all retrieval methods to ensure MCP is functioning correctly")
    
    all_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'tests': []
    }
    
    # 1. Verify indexes are available
    if not verify_index_availability():
        logger.error("Indexes not available. Please run indexing first.")
        return
    
    # 2. Test SQL-based search
    sql_results = verify_sql_search()
    all_results['tests'].extend(sql_results)
    
    # 3. Test semantic search
    semantic_results = verify_semantic_search()
    all_results['tests'].extend(semantic_results)
    
    # 4. Test hybrid search
    hybrid_results = verify_hybrid_search()
    all_results['tests'].extend(hybrid_results)
    
    # 5. Test direct API
    api_success = test_direct_mcp_api()
    all_results['direct_api_test'] = api_success
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("="*80)
    
    total_tests = len(all_results['tests'])
    successful = sum(1 for t in all_results['tests'] if t['success'])
    failed = total_tests - successful
    
    logger.info(f"Total tests: {total_tests}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Direct API: {'✅ Working' if api_success else '❌ Failed'}")
    
    # Breakdown by method
    methods = {
        'SQL BM25': 0,
        'SQL FTS': 0,
        'Semantic': 0,
        'Hybrid': 0
    }
    
    for test in all_results['tests']:
        if test['success']:
            if '--semantic' in test.get('args', []) and 'false' in test.get('args', []):
                methods['SQL BM25'] += 1
            elif '--semantic' in test.get('args', []) and 'true' in test.get('args', []):
                methods['Semantic'] += 1
            elif '--hybrid' in test.get('args', []):
                methods['Hybrid'] += 1
            else:
                methods['SQL FTS'] += 1
    
    logger.info("\nWorking retrieval methods:")
    for method, count in methods.items():
        status = "✅" if count > 0 else "❌"
        logger.info(f"  {status} {method}: {count} successful tests")
    
    # Save results
    with open('mcp_verification_results.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"\nDetailed results saved to: mcp_verification_results.json")
    
    # Return overall status
    if failed == 0 and api_success:
        logger.info("\n✅ All MCP retrieval methods are functioning correctly!")
        return True
    else:
        logger.warning("\n⚠️  Some MCP retrieval methods need attention")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)