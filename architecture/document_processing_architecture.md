# Document Processing Architecture

## Overview

The Document Processing subsystem extends the MCP server to handle natural language documents (Markdown, plain text, documentation) with the same sophistication as code files. This architecture provides intelligent chunking, structure-aware indexing, and natural language search capabilities.

## Core Components

### 1. Base Document Plugin

The `BaseDocumentPlugin` extends `SpecializedPluginBase` to provide common functionality for all document-oriented plugins:

```python
class BaseDocumentPlugin(SpecializedPluginBase):
    - Smart chunking algorithms
    - Document structure extraction
    - Metadata parsing
    - Section hierarchy management
    - Natural language processing utilities
```

### 2. Markdown Plugin

Specialized plugin for Markdown documents with full CommonMark/GFM support:

**Key Features:**
- Hierarchical heading extraction (#, ##, ###)
- Code block preservation with language detection
- Table and list structure parsing
- Frontmatter extraction (YAML/TOML)
- Link and reference tracking
- Smart chunking respecting Markdown structure

**Components:**
- `MarkdownParser`: AST-based Markdown parsing
- `SectionExtractor`: Hierarchical section detection
- `ChunkStrategy`: Document-aware chunking
- `FrontmatterParser`: Metadata extraction
- `CodeBlockHandler`: Preserve code examples

### 3. Plain Text Plugin

Specialized plugin for unstructured text with NLP capabilities:

**Key Features:**
- Paragraph boundary detection
- Sentence segmentation
- Topic modeling and extraction
- Semantic coherence analysis
- Metadata inference from formatting

**Components:**
- `NLPProcessor`: Natural language processing
- `ParagraphDetector`: Text structure analysis
- `TopicExtractor`: Key theme identification
- `SentenceSplitter`: Boundary detection
- `SemanticChunker`: Coherence-based chunking

## Data Flow

```
Document Input → Plugin Detection → Structure Extraction → Smart Chunking → 
→ Symbol Creation → Semantic Embedding → Index Storage → Search Interface
```

### 1. Document Ingestion
- File type detection (.md, .txt, .markdown)
- Plugin selection based on extension
- Content loading and preprocessing

### 2. Structure Extraction
- **Markdown**: Parse AST, extract headings, identify sections
- **Plain Text**: Detect paragraphs, infer structure from formatting
- Build hierarchical document model

### 3. Smart Chunking
- Respect document boundaries (don't split sentences/paragraphs)
- Maintain semantic coherence
- Include context metadata with each chunk
- Optimize chunk size for embedding quality

### 4. Symbol Generation
- Create symbols for document sections
- Preserve hierarchy in symbol relationships
- Generate rich metadata (title, level, parent, context)

### 5. Semantic Embedding
- Generate embeddings for each chunk
- Include structural context in embedding text
- Store with document-specific metadata

## Search Capabilities

### 1. Hybrid Search System

The system now combines multiple search strategies for optimal results:

```python
class HybridSearchEngine:
    def search(self, query: str) -> List[SearchResult]:
        # 1. BM25 full-text search
        bm25_results = self.bm25_index.search(query, limit=50)
        
        # 2. Semantic vector search
        query_embedding = self.embed_query(query)
        vector_results = self.vector_store.search(query_embedding, limit=50)
        
        # 3. Combine and rerank
        combined = self.merge_results(bm25_results, vector_results)
        reranked = self.reranker.rerank(query, combined, limit=20)
        
        return reranked
```

### 2. BM25 Integration

Full-text search using BM25 algorithm for keyword matching:

```sql
-- SQLite FTS5 with BM25 ranking
CREATE VIRTUAL TABLE document_fts USING fts5(
    content,
    section_path,
    document_title,
    tokenize='porter unicode61',
    content=document_chunks,
    content_rowid=id
);

-- Search with BM25 ranking
SELECT *, bm25(document_fts) as rank
FROM document_fts
WHERE document_fts MATCH ?
ORDER BY rank DESC;
```

### 3. Contextual Embeddings Search

Enhanced semantic search with context-aware embeddings:

```python
def create_contextual_embedding(chunk: DocumentChunk):
    # Build context-enriched text
    context_text = f"""
    Document: {chunk.document_title}
    Path: {' > '.join(chunk.section_hierarchy)}
    Previous: {chunk.context_before[:100]}
    
    {chunk.content}
    
    Next: {chunk.context_after[:100]}
    """
    
    # Generate embedding with context
    return self.embedder.embed(context_text)
```

### 4. Reranking System

Cross-encoder based reranking for improved relevance:

```python
class DocumentReranker:
    def rerank(self, query: str, candidates: List[SearchResult], limit: int):
        # Score each candidate with cross-encoder
        scores = []
        for candidate in candidates:
            score = self.cross_encoder.predict([
                query,
                candidate.get_full_context()
            ])
            scores.append((score, candidate))
        
        # Sort by relevance score
        scores.sort(key=lambda x: x[0], reverse=True)
        return [result for _, result in scores[:limit]]
```

### 5. Structure-Aware Search
- Return specific sections, not just files
- Maintain document hierarchy in results
- Provide breadcrumb navigation
- Include relevance explanations

### 6. Natural Language Queries
- "How to install X" → Installation sections with context
- "API documentation for Y" → API reference with examples
- "Examples of Z" → Code snippets with explanations
- Query understanding with intent detection

### 7. Contextual Results
- Include parent section information
- Show surrounding context
- Highlight relevant portions
- Provide navigation to related sections

## Chunking Strategies

### 1. Adaptive Chunking System

The system now implements adaptive chunking based on document characteristics:

```python
def determine_chunk_strategy(document):
    size = len(document.content)
    structure_complexity = analyze_structure(document)
    
    if size < 5000:  # Small documents
        return SimpleChunkStrategy(chunk_size=1000, overlap=200)
    elif size < 50000:  # Medium documents
        return HierarchicalChunkStrategy(chunk_size=1500, overlap=300)
    else:  # Large documents
        return SemanticChunkStrategy(chunk_size=2000, overlap=400)
```

### 2. Markdown Chunking
```
1. Analyze document size and structure
2. Apply adaptive chunking:
   - Small docs: Simple section-based splitting
   - Medium docs: Hierarchical with subsection awareness
   - Large docs: Semantic clustering with topic modeling
3. For each chunk:
   - Preserve complete sections when possible
   - Maintain code blocks intact
   - Keep lists and tables together
   - Add contextual overlap (20% of chunk size)
4. Generate contextual metadata for each chunk
```

### 3. Plain Text Chunking
```
1. Detect natural boundaries (paragraphs, topics)
2. Apply size-aware chunking:
   - Small: Paragraph-based with minimal overlap
   - Medium: Topic-clustered with semantic coherence
   - Large: Sliding window with dynamic boundaries
3. Use NLP for boundary detection:
   - Sentence segmentation
   - Topic shift detection
   - Semantic similarity measurement
4. Preserve context with adaptive overlap
```

### 4. Contextual Embeddings

Each chunk now includes contextual information for better semantic search:

```python
class ContextualChunk:
    content: str  # The actual chunk text
    context_before: str  # Previous chunk summary (100 chars)
    context_after: str  # Next chunk summary (100 chars)
    section_path: List[str]  # ["Installation", "Requirements"]
    document_summary: str  # Brief document description
    
    def to_embedding_text(self):
        return f"""
        Document: {self.document_summary}
        Section: {' > '.join(self.section_path)}
        Context: {self.context_before}
        Content: {self.content}
        Following: {self.context_after}
        """
```

## Integration Points

### 1. Plugin Factory
- Register Markdown and PlainText plugins
- Auto-detect based on file extensions
- Provide fallback for unknown text formats

### 2. Enhanced Dispatcher
- Route document files to appropriate plugins
- Handle document-specific search queries
- Optimize for document retrieval patterns

### 3. Semantic Indexer
- Document-aware embedding generation
- Section-based similarity search
- Natural language query processing

### 4. Storage Layer
- Store document structure metadata
- Maintain section hierarchies
- Enable efficient section retrieval

## Performance Considerations

### 1. Chunking Optimization
- Cache document structure analysis
- Reuse chunks for unchanged sections
- Parallelize chunk generation
- Adaptive chunk sizing based on document length
- Smart boundary detection to minimize splits

### 2. Search Optimization
- Dual-index strategy (BM25 + Vector)
- Pre-compute document hierarchies
- Cache frequently accessed sections
- Batch embedding generation
- Incremental index updates

### 3. Memory Management
- Stream large documents (>10MB)
- Limit chunk size to prevent memory bloat
- Use lazy loading for document trees
- Efficient context window management
- Pooled embedding generation

### 4. Embedding Optimization
```python
class EmbeddingOptimizer:
    def __init__(self):
        self.batch_size = 32
        self.context_cache = LRUCache(maxsize=1000)
    
    def batch_embed_chunks(self, chunks: List[DocumentChunk]):
        # Group chunks for batch processing
        batches = [chunks[i:i+self.batch_size] 
                   for i in range(0, len(chunks), self.batch_size)]
        
        embeddings = []
        for batch in batches:
            # Check cache first
            texts = []
            cached_indices = []
            for i, chunk in enumerate(batch):
                cache_key = hash(chunk.to_embedding_text())
                if cache_key in self.context_cache:
                    embeddings.append(self.context_cache[cache_key])
                    cached_indices.append(i)
                else:
                    texts.append(chunk.to_embedding_text())
            
            # Batch embed uncached chunks
            if texts:
                new_embeddings = self.embedder.embed_batch(texts)
                # Update cache
                for text, emb in zip(texts, new_embeddings):
                    self.context_cache[hash(text)] = emb
                embeddings.extend(new_embeddings)
        
        return embeddings
```

### 5. Index Management
- Incremental updates for modified documents
- Background reindexing for large changes
- Separate indices per document type
- Compression for vector storage

## API Extensions

### 1. Document-Specific Endpoints
```
GET /api/v1/document/<path>/structure - Get document outline
GET /api/v1/document/<path>/section/<id> - Get specific section
POST /api/v1/search/documents - Natural language document search
GET /api/v1/search/sections - Search within sections
```

### 2. Enhanced Search API
```json
{
  "query": "how to install",
  "type": "natural_language",
  "filters": {
    "document_type": ["markdown", "readme"],
    "section_level": [1, 2],
    "has_code_examples": true
  }
}
```

## Error Handling

### 1. Parsing Errors
- Graceful degradation for malformed Markdown
- Fallback to plain text processing
- Log parsing issues without failing

### 2. Chunking Errors
- Handle extremely large sections
- Deal with deeply nested structures
- Manage memory constraints

### 3. Search Errors
- Provide meaningful messages for no results
- Suggest alternative queries
- Handle natural language ambiguity

## Future Enhancements

1. **Multi-format Support**: RST, AsciiDoc, Wiki formats
2. **Advanced NLP**: Named entity recognition, sentiment analysis
3. **Cross-Document Linking**: Automatic reference detection
4. **Documentation Generation**: Auto-generate from code
5. **Collaborative Features**: Shared document annotations

## Success Metrics

1. **Accuracy**: 95%+ correct section extraction
2. **Performance**: <100ms document indexing
3. **Relevance**: 90%+ user satisfaction with search results
4. **Coverage**: Support all common documentation formats