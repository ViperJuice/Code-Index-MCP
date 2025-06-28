#!/usr/bin/env python3
"""
Test reranking using MCP server search directly.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

# Import the MCP server CLI components
import sys
sys.path.insert(0, '/app')

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system.plugin_registry import PluginRegistry
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.config.settings import Settings, RerankingSettings
from mcp_server.indexer.reranker import RerankerFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPRerankingTester:
    """Test reranking with MCP dispatcher."""
    
    def __init__(self):
        self.storage = None
        self.dispatcher = None
    
    async def setup(self):
        """Initialize MCP components."""
        logger.info("Setting up MCP reranking test...")
        
        # Initialize storage
        db_path = Path("/app/code_index.db")
        self.storage = SQLiteStore(str(db_path))
        
        # Initialize dispatcher
        self.dispatcher = EnhancedDispatcher(
            sqlite_store=self.storage,
            enable_advanced_features=True,
            use_plugin_factory=True,
            lazy_load=True,
            semantic_search_enabled=False
        )
        
        # Load some plugins
        plugin_files = ['python_plugin', 'js_plugin', 'markdown_plugin']
        for plugin_name in plugin_files:
            plugin_path = Path(f"/app/mcp_server/plugins/{plugin_name}/plugin.py")
            if plugin_path.exists():
                try:
                    await self.dispatcher._load_plugin(str(plugin_path))
                    logger.info(f"Loaded plugin: {plugin_name}")
                except Exception as e:
                    logger.warning(f"Failed to load {plugin_name}: {e}")
        
        logger.info("Setup complete")
    
    async def test_search_with_reranking(self):
        """Test search with and without reranking."""
        test_queries = [
            "def search",
            "class Plugin",
            "authentication",
            "error handling",
            "import asyncio"
        ]
        
        logger.info("\n" + "="*60)
        logger.info("Testing MCP Search with Reranking")
        logger.info("="*60)
        
        for query in test_queries:
            logger.info(f"\nQuery: '{query}'")
            
            # Search without semantic (basic search)
            start_time = time.time()
            results = list(self.dispatcher.search(query, semantic=False, limit=10))
            basic_time = (time.time() - start_time) * 1000
            
            logger.info(f"Basic search: {len(results)} results in {basic_time:.2f}ms")
            
            # Log top 3 results
            for i, result in enumerate(results[:3]):
                filepath = result.get('file', 'Unknown')
                line = result.get('line', 0)
                snippet = result.get('snippet', '')[:60].replace('\n', ' ')
                logger.info(f"  {i+1}. {Path(filepath).name}:{line} - {snippet}...")
            
            # Now test with a mock reranker
            await self._test_reranker_on_results(query, results)
    
    async def _test_reranker_on_results(self, query: str, results: List[Dict]):
        """Test reranking on actual search results."""
        if not results:
            logger.info("  No results to rerank")
            return
        
        # Create a TF-IDF reranker
        factory = RerankerFactory()
        reranker = factory.create_reranker('tfidf', {'cache_ttl': 0})
        
        # Initialize reranker
        init_result = await reranker.initialize({})
        if not init_result.is_success:
            logger.error(f"  Failed to initialize reranker: {init_result.error}")
            return
        
        # Convert MCP results to reranker format
        from mcp_server.interfaces.plugin_interfaces import SearchResult as ISearchResult
        
        search_results = []
        for r in results[:10]:  # Take top 10
            search_results.append(ISearchResult(
                file_path=r.get('file', ''),
                line=r.get('line', 1),
                column=0,
                snippet=r.get('snippet', ''),
                match_type='mcp',
                score=1.0,  # MCP doesn't return scores
                context=''
            ))
        
        # Perform reranking
        start_time = time.time()
        rerank_result = await reranker.rerank(query, search_results, top_k=10)
        rerank_time = (time.time() - start_time) * 1000
        
        if rerank_result.is_success and rerank_result.data:
            logger.info(f"\n  Reranking took {rerank_time:.2f}ms")
            logger.info("  Reranked top 3:")
            
            for i, rr in enumerate(rerank_result.data[:3]):
                filepath = Path(rr.original_result.file_path).name
                score = rr.rerank_score
                old_rank = rr.original_rank + 1
                new_rank = rr.new_rank + 1
                
                movement = ""
                if old_rank != new_rank:
                    if new_rank < old_rank:
                        movement = f" ↑{old_rank - new_rank}"
                    else:
                        movement = f" ↓{new_rank - old_rank}"
                
                logger.info(f"    {new_rank}. {filepath} (score: {score:.4f}, was #{old_rank}{movement})")
        else:
            logger.error(f"  Reranking failed: {rerank_result.error if rerank_result else 'Unknown error'}")
    
    async def benchmark_reranking_performance(self):
        """Benchmark reranking performance on different query types."""
        logger.info("\n" + "="*60)
        logger.info("Benchmarking Reranking Performance")
        logger.info("="*60)
        
        benchmark_queries = {
            'simple': ["def", "class", "import", "return"],
            'pattern': ["def.*init", "async.*await", "try.*except"],
            'semantic': ["authentication flow", "error handling", "data processing"]
        }
        
        for query_type, queries in benchmark_queries.items():
            logger.info(f"\n{query_type.upper()} queries:")
            
            total_search_time = 0
            total_rerank_time = 0
            total_queries = 0
            
            for query in queries:
                # Get results
                start = time.time()
                results = list(self.dispatcher.search(query, limit=20))
                search_time = (time.time() - start) * 1000
                
                if results:
                    # Rerank them
                    factory = RerankerFactory()
                    reranker = factory.create_reranker('tfidf', {'cache_ttl': 0})
                    await reranker.initialize({})
                    
                    # Convert to reranker format
                    search_results = []
                    for r in results:
                        from mcp_server.interfaces.plugin_interfaces import SearchResult as ISearchResult
                        search_results.append(ISearchResult(
                            file_path=r.get('file', ''),
                            line=r.get('line', 1),
                            column=0,
                            snippet=r.get('snippet', ''),
                            match_type='mcp',
                            score=1.0,
                            context=''
                        ))
                    
                    start = time.time()
                    rerank_result = await reranker.rerank(query, search_results, top_k=20)
                    rerank_time = (time.time() - start) * 1000
                    
                    if rerank_result.is_success:
                        total_search_time += search_time
                        total_rerank_time += rerank_time
                        total_queries += 1
                        
                        logger.info(f"  '{query}': {len(results)} results, "
                                  f"search: {search_time:.2f}ms, rerank: {rerank_time:.2f}ms")
            
            if total_queries > 0:
                avg_search = total_search_time / total_queries
                avg_rerank = total_rerank_time / total_queries
                overhead = (avg_rerank / avg_search) * 100
                
                logger.info(f"\n  Average for {query_type}:")
                logger.info(f"    Search: {avg_search:.2f}ms")
                logger.info(f"    Rerank: {avg_rerank:.2f}ms")
                logger.info(f"    Overhead: {overhead:.1f}%")


async def main():
    """Run MCP reranking tests."""
    tester = MCPRerankingTester()
    
    try:
        await tester.setup()
        await tester.test_search_with_reranking()
        await tester.benchmark_reranking_performance()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())