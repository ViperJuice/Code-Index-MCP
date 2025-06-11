# Performance Requirements

## Overview
This document defines the performance requirements and targets for Code-Index-MCP with 48-language support, including SQLite-based indexing, Qdrant vector search, and multi-language plugin management.

## Response Time Requirements

### API Endpoints
- **Symbol Lookup**: < 100ms (p95)
- **Semantic Search**: < 500ms (p95)
- **Code Search**: < 200ms (p95)
- **Index Status**: < 50ms (p95)
- **Context Analysis**: < 300ms (p95)
- **Dependency Graph**: < 500ms (p95)
- **Impact Analysis**: < 400ms (p95)

### Background Operations
- **File Indexing**: 10,000 files/minute
- **Incremental Update**: < 100ms per file
- **Embedding Generation**: < 1s per file
- **Cache Hit Ratio**: > 80%

## Scalability Requirements

### Capacity
- **Maximum Files**: 1M+ files per repository
- **Maximum File Size**: 10MB per file
- **Concurrent Users**: 100+ simultaneous queries
- **Language Support**: 48 languages (6 enhanced + 42 generic)
- **Plugin Instances**: Lazy-loaded, cached per language

### Resource Limits
- **Memory Usage**: < 2GB for 100K files
- **CPU Usage**: < 50% during idle
- **Disk I/O**: Optimized with memory-mapped files
- **Network**: Minimal, local-first design

## Reliability Requirements

### Availability
- **Uptime Target**: 99.9% (local service)
- **Recovery Time**: < 5 seconds
- **Data Durability**: No data loss on crash
- **Graceful Degradation**: Fallback to fuzzy search

### Error Handling
- **Timeout Policy**: 30s max for any operation
- **Retry Logic**: 3 attempts with exponential backoff
- **Circuit Breaker**: Disable failing plugins
- **Error Rate**: < 0.1% of requests

## Optimization Strategies

### Caching
- **Query Cache**: LRU with 10K entries
- **Embedding Cache**: Persistent, versioned
- **Parse Cache**: AST cache for unchanged files
- **Result Cache**: 5-minute TTL
- **Context Cache**: Language-specific context cached per file
  - Type information cache: 1-hour TTL
  - Import graph cache: Until file change
  - Framework pattern cache: Per-project basis

### Indexing
- **Incremental Updates**: Only changed files
- **Parallel Processing**: Multi-threaded indexing
- **Batch Operations**: Group small files
- **Progressive Loading**: Stream large results
- **Context-Aware Indexing**: 
  - Prioritize files with rich type information
  - Index import hubs first for better context
  - Cache cross-file relationships

### Search Optimization
- **Query Planning**: Cost-based optimization
- **Index Pruning**: Remove outdated entries
- **Fuzzy Matching**: Trigram indexes
- **Semantic Search**: Approximate nearest neighbor
- **Contextual Ranking**: 
  - Boost results with matching type context
  - Prioritize results within same import graph
  - Framework-specific result ordering
  - Cross-file relationship scoring

## Monitoring and Alerting

### Key Metrics
- Response time percentiles (p50, p95, p99)
- Request rate and error rate
- Cache hit/miss ratios
- Indexing throughput
- Memory and CPU usage

### SLOs (Service Level Objectives)
- 95% of symbol lookups < 100ms
- 95% of searches < 500ms
- 99.9% availability
- < 0.1% error rate

### Benchmarks
- Regular performance testing
- Load testing with realistic workloads
- Regression detection
- Capacity planning

## Performance Budget

### Frontend (API)
- Authentication: 10ms
- Validation: 5ms
- Routing: 5ms
- Business Logic: 50-400ms
- Serialization: 10ms

### Backend (Processing)
- Plugin Factory: 5ms (cached), 50ms (first load)
- Tree-sitter Parsing: 30-100ms/file (varies by language)
- Index Update: 20ms/file
- Embedding Generation: 200-500ms/file (Voyage AI)
- Contextual Embedding Enhancement: +50-100ms/file (specialized plugins)
  - Type context extraction: 20ms
  - Import graph analysis: 30ms
  - Framework pattern detection: 20ms
  - Cross-file relationship mapping: 30ms
- Vector Search: 50ms (Qdrant ANN)
- Hybrid Search: 150ms (FTS5 + Vector)
- Contextual Search Boost: +20ms (ranking adjustment)
- Query Cache Lookup: < 1ms
- Language Detection: < 5ms

## 48-Language Optimization Strategies

### Plugin Management
- **Lazy Loading**: Load language parsers only when needed
- **Instance Pooling**: Reuse parser instances across requests
- **Query Caching**: Cache tree-sitter queries per language
- **Memory Limits**: Unload unused parsers after 5 minutes

### Multi-Language Performance
- **Parallel Indexing**: Process different languages concurrently
- **Language-Specific Indices**: Separate FTS5 tables per language
- **Batch Processing**: Group files by language for efficiency
- **Smart Routing**: Direct queries to relevant language indices

## Contextual Embeddings Performance

### Performance Targets
- **Context Extraction**: < 50ms per file
- **Enhanced Embedding**: < 600ms total (base + context)
- **Context Cache Hit**: > 90% for unchanged files
- **Memory Overhead**: < 10% increase with context

### Optimization Strategies
1. **Lazy Context Loading**: Extract context only when needed
2. **Incremental Context Updates**: Update only changed relationships
3. **Batch Context Processing**: Process related files together
4. **Context Pruning**: Limit context depth to maintain performance

## Implementation Guidelines

1. **Profile First**: Measure before optimizing
2. **Cache Aggressively**: Plugin instances, queries, results, and context
3. **Parallelize**: Use all cores for multi-language processing
4. **Stream Results**: Don't load everything in memory
5. **Index Smartly**: Language-specific optimization strategies
6. **Monitor Continuously**: Track per-language performance metrics
7. **Context-Aware Design**: Balance context richness with performance
8. **Progressive Enhancement**: Add context layers based on query needs