# Contextual Embeddings Architecture Update Summary

## Overview
This document summarizes the architectural updates made to incorporate contextual embeddings, adaptive chunking, hybrid search with BM25, and reranking support into the MCP server's document processing system.

## Files Updated

### 1. `/app/architecture/document_processing_architecture.md`
**Major Changes:**
- Added **Adaptive Chunking System** that selects chunk strategies based on document size:
  - Small documents (<5KB): Simple chunking with 1000 char chunks
  - Medium documents (5-50KB): Hierarchical chunking with 1500 char chunks  
  - Large documents (>50KB): Semantic chunking with 2000 char chunks
- Introduced **Contextual Embeddings** with the `ContextualChunk` class that includes:
  - Context before/after (100 char summaries)
  - Section path hierarchy
  - Document summary
  - Enhanced embedding text generation
- Added **Hybrid Search System** combining:
  - BM25 full-text search
  - Semantic vector search
  - Result merging and reranking
- Implemented **Reranking System** using cross-encoder models
- Enhanced **Performance Considerations** with:
  - Batch embedding optimization
  - Context caching with LRU cache
  - Incremental index updates

### 2. `/app/architecture/data_model.md`
**Major Changes:**
- Added new `document_chunks` table with fields for:
  - `context_before` and `context_after` for chunk context
  - `section_path` for hierarchical navigation
  - Chunk indexing metadata
- Enhanced FTS5 tables with BM25 support:
  - New `fts_documents` table for document search
  - Porter stemming tokenizer
  - BM25 ranking queries with snippets
- Updated vector storage schema to include:
  - Contextual embedding metadata
  - Section hierarchy tracking
  - Chunk metadata (index, size, overlap)
- Added hybrid search collection schema with:
  - Dense vectors for semantic search
  - Sparse vectors for BM25
- New document-specific metadata schemas

### 3. `/app/architecture/level4/contextual_embeddings.puml` (NEW)
**Created comprehensive PlantUML diagram showing:**
- `ContextualEmbeddingEngine` with caching and batch processing
- `ContextBuilder` for generating contextual text
- Adaptive chunking strategies (Simple, Hierarchical, Semantic)
- `HybridSearchEngine` combining BM25 and vector search
- `CrossEncoderReranker` for result reranking
- Full integration with existing components

### 4. `/app/architecture/level4/markdown_plugin.puml`
**Enhanced with:**
- Adaptive mode in `ChunkStrategy`
- Context window generation
- Dynamic chunk size selection
- Extended `Chunk` class with context fields
- Enriched `ChunkMetadata` with:
  - Section path arrays
  - Chunk indexing info
  - Strategy tracking

### 5. `/app/architecture/level4/document_processing.puml`
**Updated to include:**
- BM25 terms and contextual embeddings in `DocumentChunk`
- New `AdaptiveIndexer` component for:
  - Strategy selection
  - Contextual embedding generation
  - BM25 index updates
- Enhanced search strategy selection in dispatcher
- Hybrid search support in search enhancer

## Key Architectural Improvements

### 1. Contextual Understanding
- Each chunk now includes surrounding context for better semantic understanding
- Section hierarchy preservation enables navigation-aware search
- Document-level context improves relevance for ambiguous queries

### 2. Adaptive Processing
- Document size-aware chunking prevents over/under-segmentation
- Strategy selection optimizes for document characteristics
- Dynamic overlap sizing maintains coherence

### 3. Hybrid Search
- BM25 handles exact keyword matching effectively
- Vector search captures semantic similarity
- Reranking combines both signals for optimal results

### 4. Performance Optimization
- Batch embedding processing reduces API calls
- LRU caching prevents redundant computations
- Incremental updates minimize reindexing overhead

## Implementation Considerations

### 1. Database Schema
- Run migrations to add new tables and columns
- Create FTS5 virtual tables with proper tokenizers
- Set up indexes for efficient querying

### 2. Configuration
- Configure embedding batch sizes based on memory
- Set cache sizes for optimal performance
- Tune chunk sizes for your document corpus

### 3. Integration Points
- Update plugins to generate contextual chunks
- Modify search endpoints to use hybrid approach
- Implement reranking in the search pipeline

## Next Steps

1. Implement the `ContextualEmbeddingEngine` class
2. Update document plugins to use adaptive chunking
3. Create BM25 index management utilities
4. Integrate cross-encoder reranking model
5. Update search APIs to support hybrid queries
6. Add monitoring for embedding generation performance
7. Create migration scripts for database updates

## Benefits

1. **Better Search Relevance**: Context-aware embeddings improve semantic understanding
2. **Flexible Processing**: Adaptive chunking handles diverse document sizes effectively
3. **Robust Retrieval**: Hybrid search combines strengths of keyword and semantic search
4. **Improved Ranking**: Reranking ensures most relevant results appear first
5. **Performance**: Caching and batching optimize resource usage