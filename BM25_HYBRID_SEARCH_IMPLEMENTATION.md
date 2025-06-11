# BM25 Hybrid Search Implementation Summary

## Overview

This document summarizes the implementation of Phase 4: BM25 hybrid search functionality for the MCP Server. The implementation adds advanced full-text search capabilities using SQLite FTS5's built-in BM25 ranking algorithm and combines it with existing search methods using reciprocal rank fusion.

## Components Implemented

### 1. BM25 Indexer (`mcp_server/indexer/bm25_indexer.py`)

A comprehensive BM25 indexer that leverages SQLite FTS5 for efficient full-text search:

**Key Features:**
- **FTS5 Virtual Tables**: Creates specialized tables for content, symbols, and documents
- **BM25 Ranking**: Uses SQLite's built-in BM25 algorithm for relevance scoring
- **Advanced Query Support**:
  - Phrase searches: `"exact phrase"`
  - Boolean operators: `AND`, `OR`, `NOT`
  - Prefix searches: `term*`
  - Proximity searches: `NEAR(term1 term2, distance)`
- **Snippet & Highlighting**: Automatic snippet extraction and term highlighting
- **Term Statistics**: IDF calculation and document frequency analysis
- **Index Optimization**: Built-in optimize and rebuild functions

**FTS5 Tables Created:**
- `bm25_content`: Main content index with file metadata
- `bm25_symbols`: Specialized index for code symbols
- `bm25_documents`: Document-level index for markdown/text files
- `bm25_index_status`: Tracking table for indexed files

### 2. Hybrid Search Engine (`mcp_server/indexer/hybrid_search.py`)

Combines multiple search methods using reciprocal rank fusion (RRF):

**Key Features:**
- **Multi-Method Search**: Combines BM25, semantic, and fuzzy search results
- **Reciprocal Rank Fusion**: Advanced ranking algorithm that merges results from different sources
- **Configurable Weights**: Adjustable weights for each search method
- **Parallel Execution**: Concurrent search execution for better performance
- **Result Caching**: Built-in cache for frequently accessed queries
- **Search Statistics**: Comprehensive metrics and performance tracking

**Configuration Options:**
```python
HybridSearchConfig(
    bm25_weight=0.5,        # Weight for BM25 results
    semantic_weight=0.3,    # Weight for semantic search
    fuzzy_weight=0.2,       # Weight for fuzzy search
    rrf_k=60,              # RRF constant
    enable_bm25=True,       # Enable/disable methods
    enable_semantic=True,
    enable_fuzzy=True,
    parallel_execution=True,
    cache_results=True
)
```

### 3. Enhanced SQLite Store (`mcp_server/storage/sqlite_store.py`)

Added enhanced FTS5 support methods:

**New Methods:**
- `search_bm25()`: Direct BM25 search with custom queries
- `search_bm25_with_snippets()`: Search with automatic snippet extraction
- `search_bm25_with_highlight()`: Search with term highlighting
- `get_bm25_term_statistics()`: Get term frequency and IDF scores
- `optimize_fts_tables()`: Optimize all FTS5 tables
- `rebuild_fts_tables()`: Rebuild FTS5 indexes

### 4. Updated API Gateway (`mcp_server/gateway.py`)

Enhanced search endpoints with hybrid search support:

**Updated Endpoints:**
- `GET /search`: Now supports multiple search modes
  - Parameters: `mode` (auto, hybrid, bm25, semantic, fuzzy, classic)
  - Filters: `language`, `file_filter`
  - Automatic mode selection based on available indexers

**New Endpoints:**
- `GET /search/config`: Get current hybrid search configuration
- `PUT /search/config/weights`: Update search method weights
- `PUT /search/config/methods`: Enable/disable search methods
- `GET /search/statistics`: Get search performance statistics
- `POST /search/optimize`: Optimize search indexes
- `GET /search/term/{term}/stats`: Get term statistics
- `POST /search/rebuild`: Rebuild search indexes

## Implementation Details

### Reciprocal Rank Fusion (RRF)

The RRF algorithm combines results from multiple search methods:

```python
RRF_score = Σ(weight_i / (k + rank_i))
```

Where:
- `weight_i`: Weight for search method i
- `k`: Constant (default 60)
- `rank_i`: Rank of result in method i

### BM25 Scoring

SQLite FTS5 implements the Okapi BM25 algorithm:

```
BM25(D,Q) = Σ(IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D|/avgdl)))
```

Where:
- `IDF(qi)`: Inverse document frequency of query term
- `f(qi,D)`: Frequency of term qi in document D
- `k1`, `b`: Tuning parameters (FTS5 defaults)
- `|D|`: Document length
- `avgdl`: Average document length

## Usage Examples

### Basic BM25 Search
```python
# Initialize
storage = SQLiteStore("code_index.db")
bm25_indexer = BM25Indexer(storage)

# Index a file
bm25_indexer.add_document(
    doc_id="path/to/file.py",
    content=file_content,
    metadata={'language': 'python', 'symbols': ['function1', 'class1']}
)

# Search
results = bm25_indexer.search("function implementation", limit=20)
```

### Hybrid Search
```python
# Initialize hybrid search
config = HybridSearchConfig(
    bm25_weight=0.5,
    semantic_weight=0.3,
    fuzzy_weight=0.2
)

hybrid_search = HybridSearch(
    storage=storage,
    bm25_indexer=bm25_indexer,
    semantic_indexer=semantic_indexer,
    fuzzy_indexer=fuzzy_indexer,
    config=config
)

# Perform hybrid search
results = await hybrid_search.search(
    query="calculate fibonacci",
    filters={'language': 'python'},
    limit=10
)
```

### API Usage
```bash
# Hybrid search
curl -X GET "http://localhost:8000/search?q=fibonacci&mode=hybrid&limit=10"

# BM25-only search
curl -X GET "http://localhost:8000/search?q=fibonacci&mode=bm25&language=python"

# Update weights
curl -X PUT "http://localhost:8000/search/config/weights?bm25=0.7&fuzzy=0.3"

# Get term statistics
curl -X GET "http://localhost:8000/search/term/fibonacci/stats"
```

## Performance Characteristics

### BM25 Performance
- **Index Time**: O(n) where n is document length
- **Search Time**: O(log N) where N is number of documents
- **Space Complexity**: ~30-50% of original text size
- **Optimization**: Periodic optimization merges segments for better performance

### Hybrid Search Performance
- **Parallel Execution**: Reduces latency by running searches concurrently
- **Result Caching**: Improves response time for frequent queries
- **RRF Fusion**: O(k*m) where k is result count, m is number of methods

## Configuration Options

### Environment Variables
```bash
# Hybrid search weights
HYBRID_BM25_WEIGHT=0.5
HYBRID_SEMANTIC_WEIGHT=0.3
HYBRID_FUZZY_WEIGHT=0.2

# Search limits
SEARCH_INDIVIDUAL_LIMIT=50
SEARCH_FINAL_LIMIT=20

# Performance tuning
SEARCH_PARALLEL_EXECUTION=true
SEARCH_CACHE_RESULTS=true
```

## Testing

### Unit Tests
- `test_bm25_hybrid_search.py`: Comprehensive test suite
  - BM25 indexer functionality
  - Hybrid search operations
  - Weight configuration
  - Cache behavior

### Demo Scripts
- `demo_hybrid_search.py`: Interactive demonstration
  - Index sample files
  - Perform various searches
  - Show statistics

## Future Enhancements

1. **Query Expansion**: Add synonym support and query rewriting
2. **Learning to Rank**: Use ML to optimize result ranking
3. **Faceted Search**: Add filtering by file type, date, author
4. **Custom Tokenizers**: Language-specific tokenization
5. **Index Sharding**: Support for very large codebases
6. **Real-time Updates**: Incremental index updates

## Conclusion

The BM25 hybrid search implementation provides a robust, scalable solution for code search that combines the strengths of multiple search algorithms. The use of SQLite FTS5 ensures excellent performance while maintaining simplicity, and the reciprocal rank fusion algorithm effectively merges results from different search methods to provide the best possible search experience.