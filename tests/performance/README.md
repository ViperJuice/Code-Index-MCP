# Performance Tests

This directory contains comprehensive performance tests for the document processing system.

## Test Files

### test_document_indexing_performance.py
Tests document indexing speed and efficiency:
- **test_single_document_indexing_speed**: Measures indexing time for individual documents of various sizes
- **test_batch_indexing_throughput**: Tests throughput when processing multiple documents
- **test_concurrent_indexing_scalability**: Evaluates performance with concurrent indexing operations
- **test_large_file_indexing_performance**: Tests handling of large files (up to 10MB)
- **test_memory_usage_during_indexing**: Monitors memory consumption during indexing
- **test_incremental_update_performance**: Measures performance of document updates

Key metrics:
- Target: 10,000 files/minute (167 files/second)
- P95 indexing time: < 200ms per file
- Incremental updates: < 100ms per file

### test_document_search_performance.py
Tests search query performance and optimization:
- **test_search_query_latency**: Measures response times for various query types
- **test_query_optimization_effectiveness**: Evaluates query optimization techniques
- **test_cache_effectiveness**: Tests impact of caching on search performance
- **test_pagination_performance**: Measures performance with paginated results
- **test_concurrent_search_throughput**: Tests search under concurrent load
- **test_async_search_performance**: Evaluates asynchronous search operations

Key metrics:
- P95 search latency: < 500ms for semantic search
- Cache speedup: >= 5x
- Concurrent search efficiency: > 50%

### test_document_memory_usage.py
Tests memory usage patterns and resource management:
- **test_memory_profile_document_processing**: Profiles memory during document processing
- **test_memory_leak_detection**: Detects potential memory leaks in repeated operations
- **test_resource_cleanup_effectiveness**: Verifies proper resource cleanup
- **test_garbage_collection_impact**: Measures GC impact on performance
- **test_memory_usage_under_concurrent_load**: Tests memory with concurrent processing
- **test_memory_pressure_handling**: Evaluates behavior under memory constraints

Key metrics:
- Memory usage: < 2GB for 100K files
- Memory per document: < 20KB in index
- GC overhead: < 10%
- Memory recovery: > 50%

## Running Performance Tests

Run all performance tests:
```bash
pytest tests/performance/ -v -m performance
```

Run specific test file:
```bash
pytest tests/performance/test_document_indexing_performance.py -v
```

Run with detailed output:
```bash
pytest tests/performance/ -v -s -m performance
```

## Performance Requirements

The tests validate against these performance requirements:

1. **Indexing Speed**
   - 10,000 files per minute minimum
   - < 100ms per file for incremental updates
   - Sub-linear scaling with file size

2. **Search Latency**
   - < 500ms P95 for semantic search
   - < 300ms average latency
   - Efficient pagination and filtering

3. **Memory Usage**
   - < 2GB for 100K document index
   - Efficient garbage collection
   - No memory leaks

4. **Concurrency**
   - Linear or better scaling up to 8 workers
   - Minimal memory overhead per worker
   - Stable performance under load

## Benchmarking Tips

1. Run tests in isolation to avoid interference
2. Ensure sufficient system resources
3. Use release builds for accurate measurements
4. Consider system load when interpreting results
5. Run multiple iterations for statistical significance