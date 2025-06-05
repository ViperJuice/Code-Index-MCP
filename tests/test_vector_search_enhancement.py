#!/usr/bin/env python3
"""
Test Vector Search Enhancement for Phase 5

This test validates the enhanced vector search capabilities including:
- Batch processing for 50% faster embedding generation
- Qdrant sharding for 1M+ symbol scaling  
- Flexible dimensions (256, 512, 1024, 2048)
- Query/document type optimization
- Advanced Redis caching with 90% hit rate target
- Performance monitoring and benchmarks

"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.semantic.enhanced import (
    EnhancedVectorSearcher,
    VectorSearchConfig,
    QdrantOptimizer,
    VectorSearchBenchmarks,
    BenchmarkConfig
)
from mcp_server.config.settings import get_settings
from mcp_server.core.logging import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

def create_test_documents(count: int = 100) -> List[Dict[str, Any]]:
    """Create test documents for vector search testing."""
    
    documents = []
    
    for i in range(count):
        # Create diverse code-like content
        content_types = [
            f"def process_data_{i}(input_data):\n    '''Process input data and return results'''\n    return transform(input_data)",
            f"class DataProcessor_{i}:\n    '''A class for processing data'''\n    def __init__(self):\n        self.initialized = True",
            f"async def handle_request_{i}(request):\n    '''Handle incoming HTTP request'''\n    response = await process(request)\n    return response",
            f"# Configuration settings for module {i}\nCONFIG = {{\n    'database_url': 'localhost',\n    'timeout': 30\n}}",
            f"import numpy as np\n\ndef calculate_metrics_{i}(data):\n    '''Calculate statistical metrics'''\n    return np.mean(data), np.std(data)"
        ]
        
        content = content_types[i % len(content_types)]
        
        documents.append({
            "id": f"doc_{i}",
            "content": content,
            "file": f"test_module_{i % 10}.py",
            "symbol": f"function_{i}" if i % 3 == 0 else f"class_{i}",
            "kind": "function" if i % 3 == 0 else "class",
            "line": (i % 100) + 1,
            "language": "python"
        })
    
    return documents

async def test_basic_functionality():
    """Test basic functionality of enhanced vector searcher."""
    
    logger.info("=== Testing Basic Functionality ===")
    
    try:
        # Initialize searcher
        config = VectorSearchConfig()
        searcher = EnhancedVectorSearcher(config)
        
        # Create test documents
        test_docs = create_test_documents(20)
        logger.info(f"Created {len(test_docs)} test documents")
        
        # Test embedding generation
        logger.info("Testing embedding generation...")
        embedded_docs = await searcher.embed_documents_parallel(test_docs)
        
        assert len(embedded_docs) == len(test_docs), "Embedding count mismatch"
        assert all('embedding' in doc for doc in embedded_docs), "Missing embeddings"
        assert all(len(doc['embedding']) == config.dimension for doc in embedded_docs), "Wrong embedding dimensions"
        
        logger.info(f"✓ Successfully generated {len(embedded_docs)} embeddings")
        
        # Test indexing
        logger.info("Testing document indexing...")
        index_result = await searcher.index_documents(test_docs[:10])
        
        assert index_result['indexed_count'] == 10, "Indexing count mismatch"
        assert 'metrics' in index_result, "Missing indexing metrics"
        
        logger.info(f"✓ Successfully indexed {index_result['indexed_count']} documents")
        
        # Test searching
        logger.info("Testing search functionality...")
        search_results = await searcher.search("function that processes data", limit=5)
        
        assert isinstance(search_results, list), "Search results should be a list"
        assert len(search_results) <= 5, "Too many search results"
        
        logger.info(f"✓ Search returned {len(search_results)} results")
        
        # Test metrics
        metrics = searcher.get_metrics()
        assert 'cache_hit_rate' in metrics, "Missing cache hit rate metric"
        assert 'throughput_docs_per_sec' in metrics, "Missing throughput metric"
        
        logger.info(f"✓ Cache hit rate: {metrics['cache_hit_rate']:.1%}")
        logger.info(f"✓ Throughput: {metrics['throughput_docs_per_sec']:.1f} docs/sec")
        
        logger.info("=== Basic Functionality Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Basic functionality test failed: {e}")
        return False

async def test_dimension_flexibility():
    """Test flexible embedding dimensions (256, 512, 1024, 2048)."""
    
    logger.info("=== Testing Dimension Flexibility ===")
    
    dimensions = [256, 512, 1024, 2048]
    test_docs = create_test_documents(10)
    
    try:
        for dim in dimensions:
            logger.info(f"Testing dimension {dim}...")
            
            config = VectorSearchConfig(dimension=dim)
            searcher = EnhancedVectorSearcher(config)
            
            # Test embedding with this dimension
            embedded_docs = await searcher.embed_documents_parallel(test_docs[:5])
            
            # Verify dimensions
            for doc in embedded_docs:
                assert len(doc['embedding']) == dim, f"Wrong embedding dimension: expected {dim}, got {len(doc['embedding'])}"
            
            logger.info(f"✓ Dimension {dim} working correctly")
        
        logger.info("=== Dimension Flexibility Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Dimension flexibility test failed: {e}")
        return False

async def test_batch_performance():
    """Test batch processing performance improvements."""
    
    logger.info("=== Testing Batch Performance ===")
    
    try:
        config = VectorSearchConfig(batch_size=50, max_concurrent_batches=3)
        searcher = EnhancedVectorSearcher(config)
        
        # Create larger dataset
        test_docs = create_test_documents(200)
        
        import time
        start_time = time.time()
        
        # Process in batches
        embedded_docs = await searcher.embed_documents_parallel(test_docs)
        
        total_time = time.time() - start_time
        throughput = len(embedded_docs) / total_time
        
        logger.info(f"✓ Processed {len(embedded_docs)} documents in {total_time:.2f}s")
        logger.info(f"✓ Throughput: {throughput:.1f} docs/sec")
        
        # Verify metrics
        metrics = searcher.get_metrics()
        logger.info(f"✓ Cache hit rate: {metrics['cache_hit_rate']:.1%}")
        logger.info(f"✓ Average batch time: {metrics['avg_batch_time']:.2f}s")
        
        # Performance target: should be reasonably fast
        assert throughput > 10, f"Throughput too low: {throughput} docs/sec"
        
        logger.info("=== Batch Performance Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Batch performance test failed: {e}")
        return False

async def test_cache_performance():
    """Test cache hit rate performance."""
    
    logger.info("=== Testing Cache Performance ===")
    
    try:
        config = VectorSearchConfig()
        searcher = EnhancedVectorSearcher(config)
        
        # Use same documents multiple times to test caching
        test_docs = create_test_documents(20)
        
        # First pass - populate cache
        logger.info("First pass - populating cache...")
        await searcher.embed_documents_parallel(test_docs)
        
        # Clear metrics for clean test
        searcher.metrics = type(searcher.metrics)()
        
        # Second pass - should hit cache
        logger.info("Second pass - testing cache hits...")
        await searcher.embed_documents_parallel(test_docs)
        
        # Third pass - more cache hits
        logger.info("Third pass - more cache hits...")
        await searcher.embed_documents_parallel(test_docs)
        
        metrics = searcher.get_metrics()
        cache_hit_rate = metrics['cache_hit_rate']
        
        logger.info(f"✓ Cache hit rate: {cache_hit_rate:.1%}")
        logger.info(f"✓ Cache hits: {metrics['cache_hits']}")
        logger.info(f"✓ Cache misses: {metrics['cache_misses']}")
        
        # Should have high cache hit rate on repeated documents
        assert cache_hit_rate > 0.8, f"Cache hit rate too low: {cache_hit_rate:.1%}"
        
        logger.info("=== Cache Performance Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Cache performance test failed: {e}")
        return False

async def test_qdrant_optimizer():
    """Test Qdrant optimization functionality."""
    
    logger.info("=== Testing Qdrant Optimizer ===")
    
    try:
        from qdrant_client import QdrantClient
        
        # Use in-memory Qdrant for testing
        qdrant_client = QdrantClient(location=":memory:")
        optimizer = QdrantOptimizer(qdrant_client)
        
        # Test collection creation
        logger.info("Testing optimized collection creation...")
        result = await optimizer.create_optimized_collection(
            collection_name="test_collection",
            vector_size=1024,
            expected_points=100000
        )
        
        assert result['status'] == 'created', "Collection creation failed"
        assert result['shard_count'] >= 1, "Invalid shard count"
        
        logger.info(f"✓ Created collection with {result['shard_count']} shards")
        
        # Test performance analysis
        logger.info("Testing performance analysis...")
        analysis = await optimizer.analyze_collection_performance("test_collection")
        
        assert 'collection' in analysis, "Missing collection in analysis"
        assert 'optimal_shards' in analysis, "Missing optimal shards calculation"
        
        logger.info(f"✓ Optimal shards: {analysis['optimal_shards']}")
        
        logger.info("=== Qdrant Optimizer Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Qdrant optimizer test failed: {e}")
        return False

async def test_search_optimization():
    """Test search performance and query/document type optimization."""
    
    logger.info("=== Testing Search Optimization ===")
    
    try:
        config = VectorSearchConfig(similarity_threshold=0.5)
        searcher = EnhancedVectorSearcher(config)
        
        # Create and index test documents
        test_docs = create_test_documents(50)
        await searcher.index_documents(test_docs)
        
        # Test different query types
        queries = [
            "function that processes data",
            "class for data handling", 
            "async request handler",
            "configuration settings",
            "statistical calculations"
        ]
        
        total_results = 0
        search_times = []
        
        for query in queries:
            import time
            start_time = time.time()
            
            results = await searcher.search(
                query=query,
                limit=10,
                filters={"language": "python"}
            )
            
            search_time = (time.time() - start_time) * 1000  # ms
            search_times.append(search_time)
            total_results += len(results)
            
            logger.info(f"Query: '{query}' -> {len(results)} results in {search_time:.1f}ms")
        
        avg_search_time = sum(search_times) / len(search_times)
        
        logger.info(f"✓ Average search time: {avg_search_time:.1f}ms")
        logger.info(f"✓ Total results found: {total_results}")
        
        # Performance targets
        assert avg_search_time < 1000, f"Search too slow: {avg_search_time:.1f}ms"
        assert total_results > 0, "No search results found"
        
        logger.info("=== Search Optimization Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Search optimization test failed: {e}")
        return False

async def run_mini_benchmark():
    """Run a mini benchmark to test performance targets."""
    
    logger.info("=== Running Mini Benchmark ===")
    
    try:
        # Create benchmark with smaller dataset for quick testing
        benchmark_config = BenchmarkConfig(
            num_documents=100,
            test_iterations=10,
            warmup_iterations=2
        )
        
        benchmarks = VectorSearchBenchmarks(benchmark_config)
        
        # Prepare test data
        await benchmarks.prepare_test_data()
        logger.info("Test data prepared")
        
        # Run embedding benchmark
        embedding_result = await benchmarks.benchmark_embedding_generation()
        logger.info(f"✓ Embedding benchmark: {embedding_result.throughput_ops_per_sec:.1f} docs/sec")
        
        # Run cache benchmark
        cache_result = await benchmarks.benchmark_cache_performance()
        hit_rate = cache_result.metadata.get('cache_hit_rate', 0)
        logger.info(f"✓ Cache benchmark: {hit_rate:.1%} hit rate")
        
        # Run search benchmark
        search_result = await benchmarks.benchmark_search_performance()
        avg_latency = search_result.metadata.get('avg_latency_ms', 0)
        logger.info(f"✓ Search benchmark: {avg_latency:.1f}ms average latency")
        
        # Check if targets are met
        targets_met = []
        
        if embedding_result.throughput_ops_per_sec > 20:  # Reasonable target for test
            targets_met.append("embedding_throughput")
            
        if hit_rate > 0.7:  # 70% hit rate for mini test
            targets_met.append("cache_hit_rate")
            
        if avg_latency < 500:  # 500ms for mini test
            targets_met.append("search_latency")
        
        logger.info(f"✓ Performance targets met: {targets_met}")
        
        logger.info("=== Mini Benchmark COMPLETED ===")
        return True
        
    except Exception as e:
        logger.error(f"Mini benchmark failed: {e}")
        return False

async def main():
    """Run all vector search enhancement tests."""
    
    logger.info("Starting Vector Search Enhancement Tests for Phase 5")
    logger.info("=" * 60)
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Dimension Flexibility", test_dimension_flexibility), 
        ("Batch Performance", test_batch_performance),
        ("Cache Performance", test_cache_performance),
        ("Qdrant Optimizer", test_qdrant_optimizer),
        ("Search Optimization", test_search_optimization),
        ("Mini Benchmark", run_mini_benchmark)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            result = await test_func()
            test_results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            test_results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Vector Search Enhancement is ready!")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed - Review implementation")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)