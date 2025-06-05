"""Example usage of the advanced multi-tier cache system."""
import asyncio
import logging
import tempfile
from typing import Dict, List, Any
from pathlib import Path

# Import the advanced cache components
from .tiered_cache import TieredCache, CacheTier
from .cache_warming import (
    CacheWarmingManager, 
    WarmingRule, 
    WarmingStrategy,
    create_symbol_warming_rule,
    create_file_invalidation_rule
)
from .decorators import (
    set_global_cache,
    cache_symbol_lookup,
    cache_search_results,
    cache_file_analysis,
    cached,
    CacheKeyStrategy
)
from .performance_monitor import PerformanceMonitor, PerformanceThreshold, AlertLevel
from .gpu_acceleration import get_gpu_accelerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockMCPService:
    """Mock MCP service to demonstrate cache usage."""
    
    def __init__(self):
        self.symbol_lookup_count = 0
        self.search_count = 0
        self.analysis_count = 0
    
    @cache_symbol_lookup(ttl=1800)  # 30 minutes
    async def lookup_symbol(self, symbol_name: str, file_path: str) -> Dict[str, Any]:
        """Look up symbol information with caching."""
        self.symbol_lookup_count += 1
        logger.info(f"Looking up symbol: {symbol_name} (call #{self.symbol_lookup_count})")
        
        # Simulate expensive symbol lookup
        await asyncio.sleep(0.1)
        
        return {
            "name": symbol_name,
            "file": file_path,
            "type": "function",
            "line": 42,
            "signature": f"def {symbol_name}(args):",
            "doc": f"Documentation for {symbol_name}",
            "references": [f"ref_{i}" for i in range(5)]
        }
    
    @cache_search_results(ttl=600)  # 10 minutes
    async def search_code(self, query: str, file_patterns: List[str] = None) -> List[Dict[str, Any]]:
        """Search code with result caching."""
        self.search_count += 1
        logger.info(f"Searching for: {query} (call #{self.search_count})")
        
        # Simulate expensive search
        await asyncio.sleep(0.2)
        
        return [
            {
                "file": f"src/file_{i}.py",
                "line": i * 10,
                "content": f"Line containing {query}",
                "score": 0.9 - (i * 0.1)
            }
            for i in range(10)
        ]
    
    @cache_file_analysis(ttl=3600)  # 1 hour
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze file with caching for large results."""
        self.analysis_count += 1
        logger.info(f"Analyzing file: {file_path} (call #{self.analysis_count})")
        
        # Simulate expensive file analysis
        await asyncio.sleep(0.3)
        
        return {
            "file": file_path,
            "lines": 500,
            "functions": [f"func_{i}" for i in range(20)],
            "classes": [f"Class_{i}" for i in range(5)],
            "imports": [f"import_{i}" for i in range(10)],
            "complexity": 15.7,
            "ast": {"type": "Module", "children": [f"node_{i}" for i in range(100)]}
        }
    
    @cached(
        ttl=300,  # 5 minutes
        key_strategy=CacheKeyStrategy.ALL_PARAMS,
        tier_hint=CacheTier.L1,  # Fast access needed
        skip_kwargs={"_internal"}  # Skip internal parameters
    )
    async def get_project_info(self, project_path: str, include_stats: bool = True, _internal: str = None) -> Dict[str, Any]:
        """Get project information with custom caching."""
        logger.info(f"Getting project info for: {project_path}")
        
        # Simulate project analysis
        await asyncio.sleep(0.15)
        
        info = {
            "path": project_path,
            "name": Path(project_path).name,
            "files_count": 150,
            "total_lines": 15000
        }
        
        if include_stats:
            info["stats"] = {
                "functions": 200,
                "classes": 50,
                "complexity": 8.5
            }
        
        return info


async def setup_cache_system():
    """Setup the complete cache system."""
    # Create temporary directory for L3 cache
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Using cache directory: {temp_dir}")
    
    # Initialize tiered cache
    cache = TieredCache(
        redis_url="redis://localhost:6379",  # Make sure Redis is running
        l1_max_size=1000,
        l1_max_memory_mb=100,
        l2_default_ttl=3600,
        l3_cache_dir=temp_dir,
        enable_stats=True
    )
    
    # Setup cache warming manager
    warming_manager = CacheWarmingManager(cache)
    
    # Setup performance monitoring
    monitor = PerformanceMonitor(cache, report_interval=30)  # Monitor every 30 seconds
    
    # Add custom performance thresholds
    custom_threshold = PerformanceThreshold(
        metric_name="hit_rate",
        warning_threshold=0.85,  # 85%
        critical_threshold=0.75,  # 75%
        comparison="less"
    )
    monitor.add_custom_threshold(custom_threshold)
    
    # Setup global cache for decorators
    set_global_cache(cache, warming_manager)
    
    # Setup GPU acceleration (optional)
    gpu_accelerator = get_gpu_accelerator(use_gpu=True)
    logger.info(f"GPU acceleration: {gpu_accelerator.get_gpu_stats()}")
    
    return cache, warming_manager, monitor


async def setup_warming_rules(warming_manager: CacheWarmingManager, service: MockMCPService):
    """Setup cache warming rules for common operations."""
    
    # Symbol lookup warming
    async def symbol_factory(key: str) -> Dict[str, Any]:
        # Extract symbol and file from key
        parts = key.replace("symbol:", "").split("|")
        if len(parts) >= 2:
            symbol_name, file_path = parts[0], parts[1]
            return await service.lookup_symbol(symbol_name, file_path)
        return None
    
    symbol_rule = WarmingRule(
        key_pattern="symbol:*",
        factory_func=symbol_factory,
        strategy=WarmingStrategy.PREDICTIVE,
        priority=3,
        max_age_seconds=1800
    )
    warming_manager.add_warming_rule("symbol:*", symbol_rule)
    
    # Search results warming
    async def search_factory(key: str) -> List[Dict[str, Any]]:
        query = key.replace("search:", "").split("|")[0]
        return await service.search_code(query)
    
    search_rule = WarmingRule(
        key_pattern="search:*",
        factory_func=search_factory,
        strategy=WarmingStrategy.LAZY,
        priority=2,
        max_age_seconds=600
    )
    warming_manager.add_warming_rule("search:*", search_rule)
    
    # File invalidation rule
    file_invalidation = create_file_invalidation_rule()
    warming_manager.add_invalidation_rule("file_changed:*", file_invalidation)
    
    logger.info("Cache warming rules configured")


async def demonstrate_cache_performance():
    """Demonstrate cache performance improvements."""
    logger.info("=== Cache Performance Demonstration ===")
    
    # Setup cache system
    cache, warming_manager, monitor = await setup_cache_system()
    service = MockMCPService()
    
    try:
        # Setup warming rules
        await setup_warming_rules(warming_manager, service)
        
        # === Demonstrate Symbol Lookup Caching ===
        logger.info("\\n--- Symbol Lookup Performance ---")
        
        # First lookup (cache miss)
        start_time = asyncio.get_event_loop().time()
        result1 = await service.lookup_symbol("test_function", "src/test.py")
        first_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"First lookup: {first_time*1000:.2f}ms (cache miss)")
        
        # Second lookup (cache hit)
        start_time = asyncio.get_event_loop().time()
        result2 = await service.lookup_symbol("test_function", "src/test.py")
        second_time = asyncio.get_event_loop().time() - start_time
        logger.info(f"Second lookup: {second_time*1000:.2f}ms (cache hit)")
        
        assert result1 == result2
        assert service.symbol_lookup_count == 1  # Only called once
        logger.info(f"Performance improvement: {(first_time/second_time):.1f}x faster")
        
        # === Demonstrate Search Caching ===
        logger.info("\\n--- Search Results Caching ---")
        
        # Multiple searches
        queries = ["function", "class", "import", "test"]
        
        # First round (cache misses)
        start_time = asyncio.get_event_loop().time()
        first_results = []
        for query in queries:
            result = await service.search_code(query)
            first_results.append(result)
        first_round_time = asyncio.get_event_loop().time() - start_time
        
        # Second round (cache hits)
        start_time = asyncio.get_event_loop().time()
        second_results = []
        for query in queries:
            result = await service.search_code(query)
            second_results.append(result)
        second_round_time = asyncio.get_event_loop().time() - start_time
        
        assert first_results == second_results
        assert service.search_count == len(queries)  # Only called once per query
        logger.info(f"Search performance improvement: {(first_round_time/second_round_time):.1f}x faster")
        
        # === Demonstrate File Analysis Caching ===
        logger.info("\\n--- File Analysis Caching ---")
        
        file_paths = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        
        # Analyze files (cache misses)
        start_time = asyncio.get_event_loop().time()
        analyses = []
        for file_path in file_paths:
            analysis = await service.analyze_file(file_path)
            analyses.append(analysis)
        analysis_time = asyncio.get_event_loop().time() - start_time
        
        # Re-analyze same files (cache hits)
        start_time = asyncio.get_event_loop().time()
        cached_analyses = []
        for file_path in file_paths:
            analysis = await service.analyze_file(file_path)
            cached_analyses.append(analysis)
        cached_analysis_time = asyncio.get_event_loop().time() - start_time
        
        assert analyses == cached_analyses
        assert service.analysis_count == len(file_paths)
        logger.info(f"Analysis performance improvement: {(analysis_time/cached_analysis_time):.1f}x faster")
        
        # === Demonstrate Cache Warming ===
        logger.info("\\n--- Cache Warming ---")
        
        # Warm cache for common symbols
        symbol_keys = [f"symbol:common_func_{i}|src/common.py" for i in range(5)]
        warm_results = await warming_manager.warm_cache(symbol_keys, WarmingStrategy.EAGER)
        logger.info(f"Warmed {sum(warm_results.values())} symbol cache entries")
        
        # === Cache Statistics ===
        logger.info("\\n--- Cache Statistics ---")
        
        # Wait a moment for statistics to be collected
        await asyncio.sleep(2)
        
        # Get cache statistics
        cache_stats = await cache.get_stats()
        logger.info(f"Overall hit rate: {cache_stats['overall']['hit_rate']:.2%}")
        logger.info(f"Total requests: {cache_stats['overall']['total_requests']}")
        logger.info(f"Average response time: {cache_stats['overall']['avg_access_time_ms']:.2f}ms")
        
        # Get performance summary
        perf_summary = monitor.get_performance_summary(time_window=300)
        logger.info(f"Performance metrics collected: {len(perf_summary['metrics'])}")
        
        if perf_summary['recommendations']:
            logger.info("Performance recommendations:")
            for rec in perf_summary['recommendations']:
                logger.info(f"  - {rec}")
        
        # === Test Cache Invalidation ===
        logger.info("\n--- Cache Invalidation ---")
        
        # Trigger file change invalidation
        invalidated = await warming_manager.invalidate("file_changed:src/test.py")
        logger.info(f"Invalidated {invalidated} cache entries due to file change")
        
        # === GPU Acceleration Demo ===
        logger.info("\n--- GPU Acceleration ---")
        
        gpu_accelerator = get_gpu_accelerator()
        gpu_stats = gpu_accelerator.get_gpu_stats()
        
        if gpu_stats['gpu_available']:
            # Test batch operations
            test_keys = [f"gpu_test_key_{i}" for i in range(1000)]
            
            start_time = asyncio.get_event_loop().time()
            hashed_keys = await gpu_accelerator.batch_hash_keys(test_keys)
            gpu_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"GPU batch hashing: {len(hashed_keys)} keys in {gpu_time*1000:.2f}ms")
        else:
            logger.info("GPU acceleration not available")
        
        # Final statistics
        final_stats = await cache.get_stats()
        logger.info(f"\nFinal cache hit rate: {final_stats['overall']['hit_rate']:.2%}")
        logger.info(f"Target hit rate: {final_stats['overall']['target_hit_rate']:.0%}")
        
        if final_stats['overall']['hit_rate'] >= final_stats['overall']['target_hit_rate']:
            logger.info("✅ Cache performance target achieved!")
        else:
            logger.info("⚠️  Cache performance below target")
    
    finally:
        # Cleanup
        await monitor.shutdown()
        await warming_manager.shutdown()
        await cache.shutdown()
        logger.info("Cache system shut down")


async def benchmark_cache_performance():
    """Benchmark cache performance under load."""
    logger.info("\n=== Cache Performance Benchmark ===")
    
    cache, warming_manager, monitor = await setup_cache_system()
    
    try:
        # Benchmark parameters
        num_operations = 10000
        num_keys = 1000
        
        logger.info(f"Benchmarking {num_operations} operations on {num_keys} unique keys")
        
        # Generate test data
        test_keys = [f"benchmark_key_{i}" for i in range(num_keys)]
        test_values = [f"benchmark_value_{i}" * 10 for i in range(num_keys)]
        
        # === Set Operations Benchmark ===
        logger.info("\nBenchmarking SET operations...")
        start_time = asyncio.get_event_loop().time()
        
        set_tasks = []
        for i in range(num_operations):
            key_idx = i % num_keys
            task = cache.set(test_keys[key_idx], test_values[key_idx], ttl=300)
            set_tasks.append(task)
        
        await asyncio.gather(*set_tasks)
        set_time = asyncio.get_event_loop().time() - start_time
        
        set_ops_per_sec = num_operations / set_time
        logger.info(f"SET: {set_ops_per_sec:.0f} ops/sec ({set_time:.2f}s total)")
        
        # === Get Operations Benchmark ===
        logger.info("\nBenchmarking GET operations...")
        start_time = asyncio.get_event_loop().time()
        
        get_tasks = []
        for i in range(num_operations):
            key_idx = i % num_keys
            task = cache.get(test_keys[key_idx])
            get_tasks.append(task)
        
        results = await asyncio.gather(*get_tasks)
        get_time = asyncio.get_event_loop().time() - start_time
        
        get_ops_per_sec = num_operations / get_time
        hit_rate = sum(1 for r in results if r is not None) / len(results)
        
        logger.info(f"GET: {get_ops_per_sec:.0f} ops/sec ({get_time:.2f}s total)")
        logger.info(f"Hit rate: {hit_rate:.2%}")
        
        # === Mixed Operations Benchmark ===
        logger.info("\nBenchmarking mixed operations...")
        start_time = asyncio.get_event_loop().time()
        
        mixed_tasks = []
        for i in range(num_operations):
            key_idx = i % num_keys
            if i % 3 == 0:  # 33% writes
                task = cache.set(test_keys[key_idx], f"updated_{test_values[key_idx]}", ttl=300)
            else:  # 67% reads
                task = cache.get(test_keys[key_idx])
            mixed_tasks.append(task)
        
        await asyncio.gather(*mixed_tasks)
        mixed_time = asyncio.get_event_loop().time() - start_time
        
        mixed_ops_per_sec = num_operations / mixed_time
        logger.info(f"Mixed: {mixed_ops_per_sec:.0f} ops/sec ({mixed_time:.2f}s total)")
        
        # Final performance summary
        final_stats = await cache.get_stats()
        logger.info(f"\nFinal benchmark statistics:")
        logger.info(f"  Total requests: {final_stats['overall']['total_requests']}")
        logger.info(f"  Hit rate: {final_stats['overall']['hit_rate']:.2%}")
        logger.info(f"  Avg response time: {final_stats['overall']['avg_access_time_ms']:.2f}ms")
        
        # Check if performance targets are met
        target_hit_rate = 0.9  # 90%
        target_response_time = 10  # 10ms
        
        performance_ok = (
            final_stats['overall']['hit_rate'] >= target_hit_rate and
            final_stats['overall']['avg_access_time_ms'] <= target_response_time
        )
        
        if performance_ok:
            logger.info("✅ Performance targets achieved!")
        else:
            logger.info("⚠️  Performance targets not met")
    
    finally:
        await monitor.shutdown()
        await warming_manager.shutdown()
        await cache.shutdown()


if __name__ == "__main__":
    # Run the demonstration
    async def main():
        await demonstrate_cache_performance()
        await benchmark_cache_performance()
    
    asyncio.run(main())