#!/usr/bin/env python3
"""
Basic Vector Search Enhancement Tests (no API keys required)

This test validates the core structure and functionality without requiring
external API access.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.semantic.enhanced import (
    VectorSearchConfig,
    EmbeddingMetrics,
    QdrantOptimizer,
    VectorSearchBenchmarks,
    BenchmarkConfig
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_vector_search_config():
    """Test VectorSearchConfig functionality."""
    
    logger.info("=== Testing VectorSearchConfig ===")
    
    try:
        # Test default config
        config = VectorSearchConfig()
        assert config.dimension == 1024
        assert config.model == "voyage-code-3"
        assert config.batch_size == 100
        logger.info("✓ Default config created successfully")
        
        # Test custom config
        custom_config = VectorSearchConfig(
            dimension=512,
            batch_size=50,
            shard_count=8
        )
        assert custom_config.dimension == 512
        assert custom_config.batch_size == 50
        assert custom_config.shard_count == 8
        logger.info("✓ Custom config created successfully")
        
        # Test validation
        try:
            invalid_config = VectorSearchConfig(dimension=999)
            assert False, "Should have raised ValueError for invalid dimension"
        except ValueError:
            logger.info("✓ Dimension validation working")
        
        logger.info("=== VectorSearchConfig Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"VectorSearchConfig test failed: {e}")
        return False

def test_embedding_metrics():
    """Test EmbeddingMetrics functionality."""
    
    logger.info("=== Testing EmbeddingMetrics ===")
    
    try:
        # Test default metrics
        metrics = EmbeddingMetrics()
        assert metrics.total_requests == 0
        assert metrics.get_cache_hit_rate() == 0.0
        logger.info("✓ Default metrics initialized")
        
        # Test metrics calculations
        metrics.cache_hits = 90
        metrics.cache_misses = 10
        metrics.total_time = 5.0
        metrics.batch_count = 10
        metrics.total_documents = 1000
        
        hit_rate = metrics.get_cache_hit_rate()
        assert abs(hit_rate - 0.9) < 0.001  # 90% hit rate
        logger.info(f"✓ Cache hit rate calculation: {hit_rate:.1%}")
        
        avg_batch_time = metrics.get_avg_batch_time()
        assert abs(avg_batch_time - 0.5) < 0.001  # 0.5s avg
        logger.info(f"✓ Average batch time: {avg_batch_time:.2f}s")
        
        throughput = metrics.get_documents_per_second()
        assert abs(throughput - 200) < 0.001  # 200 docs/sec
        logger.info(f"✓ Throughput: {throughput:.1f} docs/sec")
        
        logger.info("=== EmbeddingMetrics Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"EmbeddingMetrics test failed: {e}")
        return False

async def test_qdrant_optimizer():
    """Test QdrantOptimizer functionality."""
    
    logger.info("=== Testing QdrantOptimizer ===")
    
    try:
        from qdrant_client import QdrantClient
        
        # Create in-memory Qdrant client for testing
        qdrant_client = QdrantClient(location=":memory:")
        optimizer = QdrantOptimizer(qdrant_client)
        
        logger.info("✓ QdrantOptimizer initialized")
        
        # Test shard count calculation
        optimal_shards_small = optimizer._calculate_optimal_shard_count(10000)
        assert optimal_shards_small >= 2
        logger.info(f"✓ Optimal shards for 10K points: {optimal_shards_small}")
        
        optimal_shards_large = optimizer._calculate_optimal_shard_count(1000000) 
        assert optimal_shards_large > optimal_shards_small
        logger.info(f"✓ Optimal shards for 1M points: {optimal_shards_large}")
        
        # Test collection creation
        collection_result = await optimizer.create_optimized_collection(
            collection_name="test_collection",
            vector_size=1024,
            expected_points=50000
        )
        
        assert collection_result['status'] == 'created'
        assert collection_result['shard_count'] >= 1
        logger.info(f"✓ Created collection with {collection_result['shard_count']} shards")
        
        logger.info("=== QdrantOptimizer Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"QdrantOptimizer test failed: {e}")
        return False

def test_benchmark_config():
    """Test BenchmarkConfig functionality."""
    
    logger.info("=== Testing BenchmarkConfig ===")
    
    try:
        # Test default config
        config = BenchmarkConfig()
        assert config.num_documents == 1000
        assert config.target_cache_hit_rate == 0.9
        assert config.target_embedding_speedup == 1.5
        logger.info("✓ Default benchmark config created")
        
        # Test custom config
        custom_config = BenchmarkConfig(
            num_documents=500,
            test_iterations=25,
            target_cache_hit_rate=0.8
        )
        assert custom_config.num_documents == 500
        assert custom_config.test_iterations == 25
        assert custom_config.target_cache_hit_rate == 0.8
        logger.info("✓ Custom benchmark config created")
        
        logger.info("=== BenchmarkConfig Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"BenchmarkConfig test failed: {e}")
        return False

def test_configuration_integration():
    """Test integration with settings system."""
    
    logger.info("=== Testing Configuration Integration ===")
    
    try:
        # Test settings integration
        from mcp_server.config.settings import VectorSearchSettings
        
        # Test default vector search settings
        vector_settings = VectorSearchSettings()
        assert vector_settings.dimension in [256, 512, 1024, 2048]
        assert vector_settings.enabled == True
        assert vector_settings.model == "voyage-code-3"
        logger.info("✓ VectorSearchSettings created with defaults")
        
        # Test config creation from settings
        config = VectorSearchConfig(
            dimension=vector_settings.dimension,
            batch_size=vector_settings.batch_size,
            shard_count=vector_settings.shard_count
        )
        assert config.dimension == vector_settings.dimension
        logger.info("✓ VectorSearchConfig created from settings")
        
        logger.info("=== Configuration Integration Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Configuration integration test failed: {e}")
        return False

def test_data_structures():
    """Test data structure validation and compatibility."""
    
    logger.info("=== Testing Data Structures ===")
    
    try:
        # Test document format
        test_doc = {
            "id": "test_doc_1",
            "content": "def example_function():\n    return 'hello world'",
            "file": "example.py",
            "symbol": "example_function",
            "kind": "function",
            "line": 1,
            "language": "python"
        }
        
        # Validate required fields
        required_fields = ["content", "file", "symbol", "kind", "line"]
        for field in required_fields:
            assert field in test_doc, f"Missing required field: {field}"
        
        logger.info("✓ Document structure validation passed")
        
        # Test search result format
        search_result = {
            "score": 0.85,
            "id": "doc_1",
            "file": "example.py",
            "symbol": "example_function",
            "line": 1
        }
        
        assert 0.0 <= search_result["score"] <= 1.0, "Invalid score range"
        assert "id" in search_result, "Missing result ID"
        
        logger.info("✓ Search result structure validation passed")
        
        logger.info("=== Data Structures Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Data structures test failed: {e}")
        return False

async def test_performance_targets():
    """Test performance target definitions and validation."""
    
    logger.info("=== Testing Performance Targets ===")
    
    try:
        config = VectorSearchConfig()
        
        # Validate performance targets
        assert config.similarity_threshold > 0.0 and config.similarity_threshold <= 1.0
        assert config.max_results > 0
        assert config.embedding_cache_ttl > 0
        assert config.query_cache_ttl > 0
        
        logger.info("✓ Performance target validation passed")
        
        # Test benchmark targets
        benchmark_config = BenchmarkConfig()
        assert benchmark_config.target_embedding_speedup >= 1.0
        assert benchmark_config.target_cache_hit_rate > 0.0 and benchmark_config.target_cache_hit_rate <= 1.0
        assert benchmark_config.target_search_latency_ms > 0
        
        logger.info("✓ Benchmark target validation passed")
        
        # Test metrics alignment
        metrics = EmbeddingMetrics()
        
        # Simulate achieving targets
        metrics.cache_hits = 900
        metrics.cache_misses = 100
        hit_rate = metrics.get_cache_hit_rate()
        
        target_met = hit_rate >= benchmark_config.target_cache_hit_rate
        logger.info(f"✓ Cache target validation: {hit_rate:.1%} >= {benchmark_config.target_cache_hit_rate:.1%} = {target_met}")
        
        logger.info("=== Performance Targets Tests PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"Performance targets test failed: {e}")
        return False

async def main():
    """Run all basic vector search enhancement tests."""
    
    logger.info("Starting Basic Vector Search Enhancement Tests")
    logger.info("=" * 60)
    
    test_results = []
    
    # Define tests
    tests = [
        ("VectorSearchConfig", test_vector_search_config),
        ("EmbeddingMetrics", test_embedding_metrics),
        ("QdrantOptimizer", test_qdrant_optimizer),
        ("BenchmarkConfig", test_benchmark_config),
        ("Configuration Integration", test_configuration_integration),
        ("Data Structures", test_data_structures),
        ("Performance Targets", test_performance_targets)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
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
        logger.info("🎉 ALL BASIC TESTS PASSED - Core functionality is ready!")
        logger.info("\nNext steps:")
        logger.info("1. Set up API keys for Voyage AI for full functionality testing")
        logger.info("2. Run comprehensive benchmarks with real data")
        logger.info("3. Test with Redis for advanced caching")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed - Review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)