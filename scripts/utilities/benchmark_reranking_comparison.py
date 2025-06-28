#!/usr/bin/env python3
"""
Benchmark script for quick reranking performance comparison.
Focuses on measuring latency and throughput differences.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import statistics

from mcp_server.config.settings import RerankingSettings
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Stores benchmark execution results."""
    config_name: str
    query: str
    iteration: int
    search_time_ms: float
    results_count: int
    first_result: Optional[str] = None
    error: Optional[str] = None


class RerankingBenchmark:
    """Benchmarks different reranking configurations."""
    
    def __init__(self, iterations: int = 10, warmup_iterations: int = 2):
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.results: List[BenchmarkResult] = []
        self.search_configs: Dict[str, HybridSearch] = {}
        
    async def setup(self):
        """Initialize components for benchmarking."""
        logger.info("Setting up benchmark environment...")
        
        # Initialize storage
        db_path = Path("/app/code_index.db")
        self.storage = SQLiteStore(str(db_path))
        
        # Initialize indexers
        self.bm25_indexer = BM25Indexer(self.storage)
        self.fuzzy_indexer = FuzzyIndexer(self.storage)
        
        # Create configurations
        await self._create_configurations()
        
        logger.info(f"Created {len(self.search_configs)} configurations for benchmarking")
    
    async def _create_configurations(self):
        """Create different search configurations."""
        base_config = HybridSearchConfig(
            enable_bm25=True,
            enable_semantic=False,  # Disable semantic for pure performance testing
            enable_fuzzy=False,  # Disable fuzzy due to API mismatch
            bm25_weight=1.0,
            fuzzy_weight=0.0,
            individual_limit=50,
            final_limit=20,
            cache_results=False  # Disable caching for fair comparison
        )
        
        # 1. No reranking (baseline)
        self.search_configs['baseline'] = HybridSearch(
            storage=self.storage,
            bm25_indexer=self.bm25_indexer,
            fuzzy_indexer=self.fuzzy_indexer,
            config=base_config
        )
        
        # 2. TF-IDF reranking (fast)
        tfidf_settings = RerankingSettings(
            enabled=True,
            reranker_type='tfidf',
            top_k=20,
            cache_ttl=0  # Disable cache for benchmarking
        )
        
        self.search_configs['tfidf'] = HybridSearch(
            storage=self.storage,
            bm25_indexer=self.bm25_indexer,
            fuzzy_indexer=self.fuzzy_indexer,
            config=base_config,
            reranking_settings=tfidf_settings
        )
        
        # 3. Cross-encoder reranking (if available)
        try:
            cross_encoder_settings = RerankingSettings(
                enabled=True,
                reranker_type='cross-encoder',
                cross_encoder_model='cross-encoder/ms-marco-MiniLM-L-6-v2',
                cross_encoder_device='cpu',
                top_k=20,
                cache_ttl=0
            )
            
            self.search_configs['cross-encoder'] = HybridSearch(
                storage=self.storage,
                bm25_indexer=self.bm25_indexer,
                fuzzy_indexer=self.fuzzy_indexer,
                config=base_config,
                reranking_settings=cross_encoder_settings
            )
        except Exception as e:
            logger.warning(f"Cross-encoder not available: {e}")
    
    def get_benchmark_queries(self) -> List[str]:
        """Get a diverse set of benchmark queries."""
        return [
            # Simple queries
            "def __init__",
            "import asyncio",
            "class Plugin",
            
            # Pattern queries
            "async def.*search",
            "raise.*Error",
            "logger\\.(info|debug|error)",
            
            # Multi-term queries
            "plugin system architecture",
            "error handling exception",
            "cache storage backend",
            
            # Natural language-like
            "how to implement plugin",
            "authentication and security",
            "performance optimization"
        ]
    
    async def run_benchmark(self):
        """Execute the benchmark."""
        queries = self.get_benchmark_queries()
        
        logger.info(f"Running benchmark with {self.iterations} iterations per query")
        logger.info(f"Testing {len(self.search_configs)} configurations")
        logger.info(f"Using {len(queries)} different queries\n")
        
        for config_name, search_instance in self.search_configs.items():
            logger.info(f"\nBenchmarking: {config_name}")
            logger.info("-" * 50)
            
            for query in queries:
                # Warmup runs
                for _ in range(self.warmup_iterations):
                    await self._execute_search(search_instance, query, config_name, -1)
                
                # Actual benchmark runs
                for iteration in range(self.iterations):
                    result = await self._execute_search(
                        search_instance, query, config_name, iteration
                    )
                    self.results.append(result)
                
                # Log progress
                query_results = [r for r in self.results 
                               if r.config_name == config_name and r.query == query and r.iteration >= 0]
                if query_results:
                    avg_time = statistics.mean([r.search_time_ms for r in query_results])
                    logger.info(f"  Query: '{query[:30]}...' - Avg: {avg_time:.2f}ms")
    
    async def _execute_search(self, search_instance: HybridSearch, query: str, 
                            config_name: str, iteration: int) -> BenchmarkResult:
        """Execute a single search and measure performance."""
        start_time = time.perf_counter()
        
        try:
            results = await search_instance.search(query, limit=20)
            
            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            
            first_result = None
            if results and len(results) > 0:
                first_result = results[0].get('filepath', 'Unknown')
            
            return BenchmarkResult(
                config_name=config_name,
                query=query,
                iteration=iteration,
                search_time_ms=search_time_ms,
                results_count=len(results),
                first_result=first_result
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            
            return BenchmarkResult(
                config_name=config_name,
                query=query,
                iteration=iteration,
                search_time_ms=search_time_ms,
                results_count=0,
                error=str(e)
            )
    
    def generate_report(self):
        """Generate benchmark report with statistics."""
        logger.info("\n" + "="*70)
        logger.info("RERANKING BENCHMARK REPORT")
        logger.info("="*70)
        logger.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Iterations per query: {self.iterations}")
        
        # Group results by configuration
        config_stats = defaultdict(lambda: {
            'times': [],
            'errors': 0,
            'total_results': 0
        })
        
        for result in self.results:
            if result.iteration < 0:  # Skip warmup runs
                continue
            
            stats = config_stats[result.config_name]
            if result.error:
                stats['errors'] += 1
            else:
                stats['times'].append(result.search_time_ms)
                stats['total_results'] += result.results_count
        
        # Calculate statistics
        logger.info("\nPERFORMANCE SUMMARY")
        logger.info("-" * 50)
        logger.info(f"{'Configuration':<20} {'Avg (ms)':<10} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10}")
        logger.info("-" * 50)
        
        baseline_avg = None
        
        for config_name in self.search_configs.keys():
            stats = config_stats[config_name]
            times = stats['times']
            
            if not times:
                logger.info(f"{config_name:<20} {'ERROR':<10}")
                continue
            
            avg_time = statistics.mean(times)
            p50 = statistics.median(times)
            p95 = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
            p99 = statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
            
            if config_name == 'baseline':
                baseline_avg = avg_time
            
            logger.info(f"{config_name:<20} {avg_time:<10.2f} {p50:<10.2f} {p95:<10.2f} {p99:<10.2f}")
        
        # Performance overhead analysis
        if baseline_avg:
            logger.info("\nPERFORMANCE OVERHEAD vs BASELINE")
            logger.info("-" * 50)
            
            for config_name in self.search_configs.keys():
                if config_name == 'baseline':
                    continue
                    
                stats = config_stats[config_name]
                times = stats['times']
                
                if times:
                    avg_time = statistics.mean(times)
                    overhead_ms = avg_time - baseline_avg
                    overhead_pct = (overhead_ms / baseline_avg) * 100
                    
                    logger.info(f"{config_name:<20} +{overhead_ms:>6.2f}ms ({overhead_pct:>+6.1f}%)")
        
        # Query-specific analysis
        logger.info("\nQUERY TYPE ANALYSIS")
        logger.info("-" * 50)
        
        query_types = {
            'simple': ["def __init__", "import asyncio", "class Plugin"],
            'pattern': ["async def.*search", "raise.*Error", "logger\\.(info|debug|error)"],
            'complex': ["plugin system architecture", "error handling exception", "how to implement plugin"]
        }
        
        for query_type, queries in query_types.items():
            logger.info(f"\n{query_type.upper()} QUERIES:")
            
            for config_name in self.search_configs.keys():
                type_times = [r.search_time_ms for r in self.results 
                            if r.config_name == config_name and r.query in queries 
                            and r.iteration >= 0 and not r.error]
                
                if type_times:
                    avg_time = statistics.mean(type_times)
                    logger.info(f"  {config_name:<20} {avg_time:>8.2f}ms")
        
        # Save detailed results
        self._save_results()
    
    def _save_results(self):
        """Save detailed benchmark results to JSON."""
        output_data = {
            'benchmark_info': {
                'timestamp': datetime.now().isoformat(),
                'iterations': self.iterations,
                'warmup_iterations': self.warmup_iterations,
                'configurations': list(self.search_configs.keys())
            },
            'results': [
                {
                    'config': r.config_name,
                    'query': r.query,
                    'iteration': r.iteration,
                    'time_ms': r.search_time_ms,
                    'results_count': r.results_count,
                    'error': r.error
                }
                for r in self.results if r.iteration >= 0
            ]
        }
        
        output_path = Path('/app/test_results/reranking_benchmark.json')
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"\nDetailed results saved to: {output_path}")
    
    async def cleanup(self):
        """Clean up resources."""
        # SQLiteStore doesn't have a close method
        pass


async def main():
    """Main benchmark execution."""
    benchmark = RerankingBenchmark(iterations=5, warmup_iterations=1)
    
    try:
        await benchmark.setup()
        await benchmark.run_benchmark()
        benchmark.generate_report()
    except Exception as e:
        logger.error(f"Benchmark failed: {e}", exc_info=True)
    finally:
        await benchmark.cleanup()


if __name__ == "__main__":
    asyncio.run(main())