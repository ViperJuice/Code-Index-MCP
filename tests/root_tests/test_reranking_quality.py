#!/usr/bin/env python3
"""
Focused test to verify reranking is working and measure quality improvements.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

from mcp_server.config.settings import RerankingSettings
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.reranker import RerankerFactory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RerankingQualityTester:
    """Tests reranking quality improvements."""
    
    def __init__(self):
        self.storage = None
        self.results = {}
    
    async def setup(self):
        """Initialize test environment."""
        logger.info("Setting up quality test environment...")
        
        # Initialize storage
        db_path = Path("/app/code_index.db")
        self.storage = SQLiteStore(str(db_path))
        
        # Initialize BM25 indexer
        self.bm25_indexer = BM25Indexer(self.storage)
        
        # Base search config (BM25 only for simplicity)
        self.base_config = HybridSearchConfig(
            enable_bm25=True,
            enable_semantic=False,
            enable_fuzzy=False,
            bm25_weight=1.0,
            semantic_weight=0.0,
            fuzzy_weight=0.0,
            individual_limit=50,
            final_limit=20,
            cache_results=False
        )
        
        logger.info("Setup complete")
    
    async def test_reranking_effect(self):
        """Test the actual effect of reranking on search results."""
        test_queries = [
            {
                'query': 'authentication user login',
                'expected_files': [
                    'auth_manager.py',
                    'security_middleware.py',
                    'gateway.py'
                ]
            },
            {
                'query': 'plugin system architecture',
                'expected_files': [
                    'plugin_manager.py',
                    'plugin_registry.py',
                    'plugin_base.py'
                ]
            },
            {
                'query': 'error handling exception',
                'expected_files': [
                    'errors.py',
                    'dispatcher.py'
                ]
            }
        ]
        
        for test_case in test_queries:
            query = test_case['query']
            expected = test_case['expected_files']
            
            logger.info(f"\nTesting query: '{query}'")
            logger.info(f"Expected files containing: {expected}")
            
            # Test without reranking
            no_rerank_search = HybridSearch(
                storage=self.storage,
                bm25_indexer=self.bm25_indexer,
                config=self.base_config,
                reranking_settings=None
            )
            
            start_time = time.time()
            no_rerank_results = await no_rerank_search.search(query, limit=10)
            no_rerank_time = (time.time() - start_time) * 1000
            
            logger.info(f"\nWithout reranking ({no_rerank_time:.2f}ms):")
            self._log_results(no_rerank_results[:5], expected)
            
            # Test with TF-IDF reranking
            tfidf_settings = RerankingSettings(
                enabled=True,
                reranker_type='tfidf',
                top_k=10,
                cache_ttl=0
            )
            
            tfidf_search = HybridSearch(
                storage=self.storage,
                bm25_indexer=self.bm25_indexer,
                config=self.base_config,
                reranking_settings=tfidf_settings
            )
            
            start_time = time.time()
            tfidf_results = await tfidf_search.search(query, limit=10)
            tfidf_time = (time.time() - start_time) * 1000
            
            logger.info(f"\nWith TF-IDF reranking ({tfidf_time:.2f}ms, +{tfidf_time - no_rerank_time:.2f}ms):")
            self._log_results(tfidf_results[:5], expected)
            
            # Compare result order
            self._compare_rankings(no_rerank_results, tfidf_results, expected)
    
    def _log_results(self, results: List[Dict[str, Any]], expected: List[str]):
        """Log search results with relevance indicators."""
        for i, result in enumerate(results):
            filepath = result.get('filepath', '')
            score = result.get('score', 0)
            filename = Path(filepath).name if filepath else 'Unknown'
            
            # Check if this is an expected result
            is_expected = any(exp in filename for exp in expected)
            marker = "✓" if is_expected else " "
            
            logger.info(f"  {i+1}. [{marker}] {filename} (score: {score:.4f})")
            if result.get('snippet'):
                snippet = result['snippet'][:80].replace('\n', ' ')
                logger.info(f"      {snippet}...")
    
    def _compare_rankings(self, original: List[Dict], reranked: List[Dict], expected: List[str]):
        """Compare rankings to see if reranking improved results."""
        def calculate_score(results: List[Dict], expected: List[str]) -> float:
            """Calculate a relevance score based on positions of expected files."""
            score = 0.0
            for i, result in enumerate(results[:10]):
                filepath = result.get('filepath', '')
                filename = Path(filepath).name if filepath else ''
                
                for exp in expected:
                    if exp in filename:
                        # Higher score for results appearing earlier
                        score += 1.0 / (i + 1)
                        break
            return score
        
        original_score = calculate_score(original, expected)
        reranked_score = calculate_score(reranked, expected)
        
        improvement = ((reranked_score - original_score) / original_score * 100) if original_score > 0 else 0
        
        logger.info(f"\nRelevance scores:")
        logger.info(f"  Original: {original_score:.3f}")
        logger.info(f"  Reranked: {reranked_score:.3f}")
        logger.info(f"  Improvement: {improvement:+.1f}%")
    
    async def test_reranker_initialization(self):
        """Test that rerankers are actually initializing and working."""
        logger.info("\n" + "="*60)
        logger.info("Testing reranker initialization")
        logger.info("="*60)
        
        factory = RerankerFactory()
        
        # Test TF-IDF
        try:
            tfidf = factory.create_reranker('tfidf', {})
            result = await tfidf.initialize({})
            logger.info(f"TF-IDF initialization: {'SUCCESS' if result.is_success else 'FAILED'}")
            if not result.is_success:
                logger.error(f"  Error: {result.error}")
            else:
                logger.info(f"  Capabilities: {tfidf.get_capabilities()}")
        except Exception as e:
            logger.error(f"TF-IDF creation failed: {e}")
        
        # Test Cross-Encoder
        try:
            cross_encoder = factory.create_reranker('cross-encoder', {
                'model': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'device': 'cpu'
            })
            result = await cross_encoder.initialize({})
            logger.info(f"Cross-Encoder initialization: {'SUCCESS' if result.is_success else 'FAILED'}")
            if not result.is_success:
                logger.error(f"  Error: {result.error}")
            else:
                logger.info(f"  Capabilities: {cross_encoder.get_capabilities()}")
        except Exception as e:
            logger.error(f"Cross-Encoder creation failed: {e}")
    
    async def test_actual_reranking(self):
        """Test that reranking actually changes result order."""
        logger.info("\n" + "="*60)
        logger.info("Testing actual reranking behavior")
        logger.info("="*60)
        
        # Create a simple test with known results
        query = "def search"
        
        # Get baseline results
        baseline_search = HybridSearch(
            storage=self.storage,
            bm25_indexer=self.bm25_indexer,
            config=self.base_config
        )
        
        baseline_results = await baseline_search.search(query, limit=10)
        
        # Create TF-IDF reranker and test directly
        factory = RerankerFactory()
        tfidf_reranker = factory.create_reranker('tfidf', {'cache_ttl': 0})
        await tfidf_reranker.initialize({})
        
        # Convert results to format expected by reranker
        from mcp_server.interfaces.plugin_interfaces import SearchResult as ISearchResult
        
        search_results = []
        for r in baseline_results[:10]:
            search_results.append(ISearchResult(
                file_path=r.get('filepath', ''),
                line=r.get('metadata', {}).get('line', 1),
                column=0,
                snippet=r.get('snippet', '')[:200],
                match_type='bm25',
                score=r.get('score', 0),
                context=''
            ))
        
        # Test reranking
        rerank_result = await tfidf_reranker.rerank(query, search_results, top_k=10)
        
        if rerank_result.is_success:
            logger.info("Reranking successful!")
            logger.info(f"Original order:")
            for i, r in enumerate(search_results[:5]):
                logger.info(f"  {i+1}. {Path(r.file_path).name} (score: {r.score:.4f})")
            
            logger.info(f"\nReranked order:")
            for rr in rerank_result.data[:5]:
                orig_idx = rr.original_rank
                new_idx = rr.new_rank
                score = rr.rerank_score
                filepath = rr.original_result.file_path
                logger.info(f"  {new_idx+1}. {Path(filepath).name} (score: {score:.4f}, was #{orig_idx+1})")
        else:
            logger.error(f"Reranking failed: {rerank_result.error}")


async def main():
    """Run quality tests."""
    tester = RerankingQualityTester()
    
    try:
        await tester.setup()
        await tester.test_reranker_initialization()
        await tester.test_actual_reranking()
        await tester.test_reranking_effect()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())