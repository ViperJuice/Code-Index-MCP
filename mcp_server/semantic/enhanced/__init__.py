"""Enhanced vector search system for Phase 5.

This module provides comprehensive vector search enhancements including:
- Batch processing for 50% faster embedding generation
- Qdrant sharding for 1M+ symbol scaling  
- Flexible dimensions (256, 512, 1024, 2048)
- Query/document type optimization
- Advanced Redis caching with 90% hit rate target
- Performance monitoring and benchmarks

"""

from .batch_indexer import (
    EnhancedVectorSearcher,
    BatchSemanticIndexer,
    VectorSearchConfig,
    EmbeddingMetrics
)

from .qdrant_optimizer import (
    QdrantOptimizer,
    ShardingStrategy, 
    ShardMetrics
)

from .benchmarks import (
    VectorSearchBenchmarks,
    BenchmarkConfig,
    BenchmarkResult
)

__all__ = [
    "EnhancedVectorSearcher",
    "BatchSemanticIndexer",
    "VectorSearchConfig", 
    "EmbeddingMetrics",
    "QdrantOptimizer",
    "ShardingStrategy",
    "ShardMetrics", 
    "VectorSearchBenchmarks",
    "BenchmarkConfig",
    "BenchmarkResult"
]