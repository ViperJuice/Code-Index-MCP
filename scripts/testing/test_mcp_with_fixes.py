#!/usr/bin/env python3
"""
Test MCP features with proper database connections and fixes.
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def test_existing_qdrant():
    """Test connection to existing Qdrant database with embeddings"""
    logger.info("Testing existing Qdrant database connection...")
    
    try:
        from qdrant_client import QdrantClient
        
        # Connect to the existing Qdrant database
        qdrant_path = "/workspaces/Code-Index-MCP/.indexes/qdrant/main.qdrant"
        
        # Remove lock file if it exists
        lock_file = Path(qdrant_path) / ".lock"
        if lock_file.exists():
            logger.info(f"Removing lock file: {lock_file}")
            lock_file.unlink()
        
        client = QdrantClient(path=qdrant_path)
        
        # List collections
        collections = client.get_collections()
        logger.info(f"Found {len(collections.collections)} collections:")
        
        for collection in collections.collections:
            logger.info(f"  - {collection.name} (vectors: {collection.vectors_count}, size: {collection.config.params.vectors.size})")
            
            # Test search on code-embeddings collection
            if collection.name == "code-embeddings":
                logger.info(f"\nTesting search on {collection.name}...")
                
                # Get a sample point to use as query
                points = client.scroll(
                    collection_name=collection.name,
                    limit=1
                )[0]
                
                if points:
                    query_vector = points[0].vector
                    
                    # Search for similar vectors
                    results = client.search(
                        collection_name=collection.name,
                        query_vector=query_vector,
                        limit=5
                    )
                    
                    logger.info(f"  Search returned {len(results)} results")
                    for i, result in enumerate(results[:3]):
                        logger.info(f"    {i+1}. Score: {result.score:.3f}, ID: {result.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Qdrant test failed: {e}")
        return False


def test_mcp_semantic_with_existing_embeddings():
    """Test MCP semantic search using existing Qdrant embeddings"""
    logger.info("\nTesting MCP semantic search with existing embeddings...")
    
    try:
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        # Point to the existing Qdrant database
        qdrant_path = "/workspaces/Code-Index-MCP/.indexes/qdrant/main.qdrant"
        
        # Create indexer connected to existing collection
        indexer = SemanticIndexer(
            collection="code-embeddings",  # Use existing collection
            qdrant_path=qdrant_path
        )
        
        # Test semantic search
        test_queries = [
            "error handling implementation",
            "authentication logic", 
            "database connection code"
        ]
        
        for query in test_queries:
            logger.info(f"\nSearching for: '{query}'")
            results = indexer.search(query, limit=3)
            
            if results:
                logger.info(f"  Found {len(results)} results")
                for i, result in enumerate(results):
                    logger.info(f"    {i+1}. {result.get('symbol', 'unknown')} (score: {result.get('score', 0):.3f})")
            else:
                logger.info("  No results found")
        
        return True
        
    except Exception as e:
        logger.error(f"Semantic search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fixed_symbol_lookup():
    """Test symbol lookup with correct column names"""
    logger.info("\nTesting symbol lookup with correct columns...")
    
    db_path = "/workspaces/Code-Index-MCP/.indexes/844145265d7a/code_index.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First check if we need to join with files table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
        has_files_table = cursor.fetchone() is not None
        
        test_symbols = ["EnhancedDispatcher", "SQLiteStore", "search"]
        
        for symbol in test_symbols:
            start_time = time.perf_counter()
            
            if has_files_table:
                # Join with files table to get file paths
                cursor.execute("""
                    SELECT 
                        s.name,
                        s.kind,
                        f.path as file_path,
                        s.line_start,
                        s.signature
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    WHERE s.name = ?
                    LIMIT 5
                """, (symbol,))
            else:
                # Direct query without file path
                cursor.execute("""
                    SELECT 
                        name,
                        kind,
                        file_id,
                        line_start,
                        signature
                    FROM symbols
                    WHERE name = ?
                    LIMIT 5
                """, (symbol,))
            
            results = cursor.fetchall()
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"\nSymbol: '{symbol}' ({duration_ms:.2f}ms)")
            if results:
                logger.info(f"  Found {len(results)} definitions")
                for result in results[:2]:
                    logger.info(f"    - {result[1]} at line {result[3]}")
            else:
                logger.info("  Not found")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Symbol lookup test failed: {e}")
        return False


def create_mcp_config_with_qdrant():
    """Create MCP configuration that uses existing Qdrant database"""
    
    config = {
        "env": {
            "SEMANTIC_SEARCH_ENABLED": "true",
            "VOYAGE_AI_API_KEY": os.getenv("VOYAGE_AI_API_KEY", ""),
            "QDRANT_PATH": "/workspaces/Code-Index-MCP/.indexes/qdrant/main.qdrant",
            "SEMANTIC_COLLECTION_NAME": "code-embeddings",
            "MCP_INDEX_PATH": "/workspaces/Code-Index-MCP/.indexes/844145265d7a/code_index.db"
        }
    }
    
    config_path = Path("/tmp/mcp_config_fixed.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created MCP config at: {config_path}")
    return str(config_path)


def main():
    """Run all tests"""
    logger.info("Starting MCP feature tests with fixes...")
    
    # Test 1: Check existing Qdrant database
    qdrant_ok = test_existing_qdrant()
    
    # Test 2: Test semantic search with existing embeddings
    semantic_ok = test_mcp_semantic_with_existing_embeddings()
    
    # Test 3: Test fixed symbol lookup
    symbol_ok = test_fixed_symbol_lookup()
    
    # Create proper MCP configuration
    config_path = create_mcp_config_with_qdrant()
    
    # Summary
    print("\n" + "="*60)
    print("MCP FEATURE TEST RESULTS")
    print("="*60)
    print(f"Qdrant Connection: {'✓' if qdrant_ok else '✗'}")
    print(f"Semantic Search: {'✓' if semantic_ok else '✗'}")
    print(f"Symbol Lookup: {'✓' if symbol_ok else '✗'}")
    print(f"\nMCP Config: {config_path}")
    print("="*60)
    
    if all([qdrant_ok, semantic_ok, symbol_ok]):
        logger.info("\nAll tests passed! Ready for comprehensive testing.")
        return 0
    else:
        logger.warning("\nSome tests failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())