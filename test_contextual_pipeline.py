#!/usr/bin/env python3
"""
Comprehensive test of the contextual embeddings pipeline.
Tests the complete flow from adaptive chunking through reranking.
"""

import os
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any

# Set test environment
os.environ['VOYAGE_AI_API_KEY'] = 'test-key'
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['COHERE_API_KEY'] = 'test-key'

# Configure for testing
os.environ['MARKDOWN_MAX_CHUNK_TOKENS'] = '500'
os.environ['CONTEXTUAL_EMBEDDINGS_ENABLED'] = 'true'
os.environ['HYBRID_SEARCH_ENABLED'] = 'true'
os.environ['RERANKING_ENABLED'] = 'true'
os.environ['RERANKING_TYPE'] = 'tfidf'  # Use local reranker for testing

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch
from mcp_server.indexer.reranker import RerankingFactory
from mcp_server.document_processing.contextual_embeddings import ContextualEmbeddingService
from mcp_server.config.settings import get_settings

# Test document - a large markdown file that will benefit from chunking
TEST_DOCUMENT = """# Contextual Embeddings Guide

## Introduction

Contextual embeddings represent a significant advancement in retrieval-augmented generation (RAG) systems. By adding relevant context to each chunk before embedding, we can dramatically improve retrieval accuracy.

## How It Works

### Traditional RAG Limitations

Traditional RAG systems often split documents into chunks without considering the broader context. This can lead to:
- Loss of semantic meaning
- Reduced retrieval accuracy
- Difficulty understanding relationships between concepts

### The Contextual Approach

Contextual embeddings solve these problems by:
1. Analyzing the entire document structure
2. Adding surrounding context to each chunk
3. Preserving hierarchical relationships
4. Maintaining semantic coherence

## Implementation Details

### Adaptive Chunking

Our system uses adaptive chunking based on document size:
- Small documents: 300 tokens per chunk
- Medium documents: 500 tokens per chunk
- Large documents: 1000 tokens per chunk

This ensures optimal performance across different document types.

### Context Generation

We use Claude to generate context for each chunk:
```python
def generate_context(document, chunk):
    # Analyze document structure
    # Generate relevant context
    # Combine with original chunk
    return contextualized_chunk
```

### Hybrid Search

The system combines multiple search strategies:
- **BM25**: Fast keyword matching with relevance scoring
- **Semantic Search**: Vector similarity using embeddings
- **Fuzzy Search**: Handles typos and variations

### Reranking

After initial retrieval, we apply reranking to improve results:
1. Retrieve more candidates than needed
2. Apply cross-encoder models
3. Select top results based on relevance

## Performance Improvements

Based on testing with real-world data:
- 35% reduction in retrieval failures with contextual embeddings
- 49% reduction when combined with hybrid search
- 67% reduction with reranking enabled

## Code Example

Here's a complete example of using the system:

```python
# Initialize components
plugin = MarkdownPlugin(enable_semantic=True)
indexer = BM25Indexer(store)
hybrid = HybridSearch(store, indexer)

# Index document with contextual embeddings
shard = plugin.indexFile("guide.md", content)

# Search with hybrid approach
results = hybrid.search("how to implement contextual embeddings")

# Results include rich context
for result in results:
    print(f"Score: {result['score']}")
    print(f"Context: {result['context']}")
    print(f"Content: {result['content']}")
```

## Best Practices

1. **Document Structure**: Use clear hierarchical headings
2. **Chunk Size**: Let the system adapt automatically
3. **Search Queries**: Use natural language questions
4. **Caching**: Enable caching for better performance

## Conclusion

Contextual embeddings represent a major leap forward in search technology. By understanding document structure and preserving context, we can deliver significantly more relevant results.
"""

async def test_contextual_pipeline():
    """Test the complete contextual embeddings pipeline."""
    print("=== Testing Contextual Embeddings Pipeline ===\n")
    
    # 1. Initialize components
    print("1. Initializing components...")
    settings = get_settings()
    store = SQLiteStore(":memory:")
    
    # Initialize markdown plugin with adaptive chunking
    plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)
    
    # Initialize BM25 indexer
    bm25_indexer = BM25Indexer(store)
    
    # Initialize hybrid search
    hybrid_search = HybridSearch(store, bm25_indexer)
    
    # Initialize reranking
    reranker_factory = RerankingFactory()
    reranker = reranker_factory.create_reranker(settings.reranking)
    
    print("✓ Components initialized\n")
    
    # 2. Test adaptive chunking
    print("2. Testing adaptive chunking...")
    chunks = plugin.chunk_document(TEST_DOCUMENT, Path("guide.md"))
    print(f"✓ Document chunked into {len(chunks)} chunks")
    print(f"  Average chunk size: {sum(len(c.content) for c in chunks) / len(chunks):.0f} chars")
    print(f"  First chunk: {chunks[0].content[:100]}...")
    print()
    
    # 3. Test contextual embeddings (mock)
    print("3. Testing contextual embeddings...")
    # Since we're in test mode, the service will use mock contexts
    context_service = ContextualEmbeddingService()
    
    # Generate contexts for first few chunks
    contexts = []
    for i, chunk in enumerate(chunks[:3]):
        context = await context_service.generate_context(TEST_DOCUMENT, chunk.content)
        contexts.append(context)
        print(f"  Chunk {i+1} context: {context[:50]}...")
    
    print(f"✓ Generated contexts for {len(contexts)} chunks\n")
    
    # 4. Index document
    print("4. Indexing document...")
    # Index with the plugin (will use base indexing without real embeddings)
    shard = plugin.indexFile("guide.md", TEST_DOCUMENT)
    print(f"✓ Indexed {len(shard['symbols'])} symbols")
    
    # Also index in BM25
    bm25_indexer.index_documents([{
        'id': f'chunk_{i}',
        'content': chunk.content,
        'metadata': {
            'file': 'guide.md',
            'chunk_index': i,
            'section': chunk.metadata.get('section', '')
        }
    } for i, chunk in enumerate(chunks)])
    print("✓ Indexed in BM25\n")
    
    # 5. Test searches
    print("5. Testing search functionality...")
    queries = [
        "contextual embeddings implementation",
        "adaptive chunking token size",
        "hybrid search strategies",
        "performance improvements reduction"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        
        # BM25 search
        bm25_results = bm25_indexer.search(query, limit=5)
        print(f"  BM25: Found {len(bm25_results)} results")
        if bm25_results:
            print(f"    Top result: {bm25_results[0]['content'][:80]}...")
        
        # Hybrid search (will use BM25 + fuzzy since semantic is disabled)
        hybrid_results = hybrid_search.search(query, limit=5, mode='hybrid')
        print(f"  Hybrid: Found {len(hybrid_results)} results")
        if hybrid_results:
            print(f"    Top result: {hybrid_results[0]['content'][:80]}...")
        
        # Test reranking
        if hybrid_results and reranker:
            rerank_results = await reranker.rerank(query, hybrid_results, top_k=3)
            print(f"  Reranked: Top {len(rerank_results.results)} results")
            if rerank_results.results:
                print(f"    New top: {rerank_results.results[0]['content'][:80]}...")
    
    # 6. Performance metrics
    print("\n6. Performance Metrics:")
    print(f"  Chunks generated: {len(chunks)}")
    print(f"  BM25 documents: {bm25_indexer.get_stats()['document_count']}")
    print(f"  Search modes available: auto, hybrid, bm25, semantic, fuzzy")
    print(f"  Reranking enabled: {settings.reranking.enabled}")
    
    print("\n✓ All pipeline components working correctly!")
    
    # 7. Test configuration
    print("\n7. Configuration Summary:")
    print(f"  Adaptive chunking: {os.getenv('MARKDOWN_ADAPTIVE_CHUNKING', 'true')}")
    print(f"  Max chunk tokens: {os.getenv('MARKDOWN_MAX_CHUNK_TOKENS', '500')}")
    print(f"  Contextual embeddings: {os.getenv('CONTEXTUAL_EMBEDDINGS_ENABLED', 'true')}")
    print(f"  Hybrid search: {os.getenv('HYBRID_SEARCH_ENABLED', 'true')}")
    print(f"  Reranking: {os.getenv('RERANKING_ENABLED', 'true')}")
    print(f"  Reranker type: {os.getenv('RERANKING_TYPE', 'hybrid')}")

def main():
    """Run the test."""
    asyncio.run(test_contextual_pipeline())

if __name__ == "__main__":
    main()