# Semantic Indexer Enhancements

## Overview

The semantic indexer at `/app/mcp_server/utils/semantic_indexer.py` has been significantly enhanced with document-specific embedding generation, section-aware indexing, and improved natural language query support.

## Key Features Added

### 1. Document-Specific Embedding Generation

- **Context-aware embeddings**: Include document title and section hierarchy in embedding text
- **Metadata enrichment**: Support for tags, summaries, and additional metadata
- **Document type handling**: Special processing for different document types (markdown, README, API docs, etc.)

```python
def _create_document_embedding(
    self, 
    content: str, 
    title: Optional[str] = None, 
    section_context: Optional[str] = None,
    doc_type: str = "markdown",
    metadata: Optional[dict] = None
) -> list[float]:
```

### 2. Section-Aware Indexing

- **Hierarchical parsing**: Automatically parse markdown documents into sections
- **Parent-child relationships**: Maintain document structure and context
- **Section context preservation**: Each section knows its place in the document hierarchy

```python
@dataclass
class DocumentSection:
    title: str
    content: str
    level: int  # Heading level (1-6 for markdown)
    start_line: int
    end_line: int
    parent_section: Optional[str] = None
    subsections: list[str] = None
```

### 3. Natural Language Query Support

- **Query-optimized embeddings**: Use appropriate input types for different content
- **Document type weighting**: Prioritize documentation for doc-related queries
- **Filtered search**: Target specific document types

```python
# Document type weights for similarity calculations
DOCUMENT_TYPE_WEIGHTS = {
    "markdown": 1.2,      # Documentation gets higher weight
    "readme": 1.3,        # README files get highest weight
    "docstring": 1.1,     # Inline documentation
    "comment": 1.0,       # Regular comments
    "code": 0.9,          # Code slightly lower for doc searches
    "api": 1.15,          # API documentation
    "tutorial": 1.25,     # Tutorial content
    "guide": 1.2,         # Guide content
}
```

### 4. New Methods

#### Document Indexing
```python
def index_document(
    self, 
    path: Path, 
    doc_type: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict[str, Any]:
```

#### Natural Language Queries
```python
def query_natural_language(
    self, 
    query: str, 
    limit: int = 10,
    doc_types: Optional[list[str]] = None,
    include_code: bool = True
) -> list[dict[str, Any]]:
```

#### Bulk Documentation Indexing
```python
def index_documentation_directory(
    self, 
    directory: Path,
    recursive: bool = True,
    file_patterns: Optional[list[str]] = None
) -> dict[str, Any]:
```

## Implementation Details

### Document Structure Parsing

The indexer can parse markdown documents into hierarchical sections:

```
📁 API Documentation
  📁 Authentication
    📁 JWT Tokens
      📄 Token Format
    📄 API Keys
  📁 Endpoints
    📁 Search
      📄 Basic Search
      📄 Advanced Search
    📄 Index
```

### Context-Enriched Embeddings

For a section titled "Token Format" under "API Documentation > Authentication > JWT Tokens", the embedding text becomes:

```
Document: API Documentation

Section: API Documentation > Authentication > JWT Tokens > Token Format

Tokens should be in the format: Bearer <token>
```

### Weighted Search Results

Natural language queries return results with both original and weighted scores:

```python
{
    "file": "/path/to/doc.md",
    "title": "Token Format",
    "section_context": "API Documentation > Authentication > JWT Tokens > Token Format",
    "score": 0.85,
    "weighted_score": 0.98,  # score * weight_factor
    "weight_factor": 1.15,   # API documentation weight
    "doc_type": "api"
}
```

## Usage Examples

### Index Documentation
```python
indexer = SemanticIndexer()

# Index a single document
result = indexer.index_document(
    Path("README.md"),
    metadata={
        "tags": ["documentation", "readme", "main"],
        "summary": "Main project documentation"
    }
)

# Index entire documentation directory
result = indexer.index_documentation_directory(Path("docs/"))
```

### Natural Language Search
```python
# Search for authentication information
results = indexer.query_natural_language(
    "How do I authenticate API requests?",
    doc_types=["api", "markdown"],
    limit=5
)

# Search only in tutorials
results = indexer.query_natural_language(
    "Getting started guide",
    doc_types=["tutorial", "readme"]
)
```

## Benefits

1. **🎯 Context Preservation**: Section titles and hierarchy inform embeddings
2. **📚 Document Type Weighting**: Documentation gets priority for doc searches
3. **🔍 Natural Language Queries**: Optimized for human-readable questions
4. **🌳 Hierarchical Structure**: Parent-child relationships maintained
5. **🏷️ Metadata Enrichment**: Tags, summaries, and context included
6. **📊 Weighted Scoring**: Different content types have appropriate relevance

## Testing

The enhancements have been tested with:

- Document structure parsing (`test_document_structure.py`)
- Feature demonstration (`demo_enhanced_indexer.py`)
- Complete workflow testing (`test_document_indexing.py`)

## Files Modified

- `/app/mcp_server/utils/semantic_indexer.py` - Main implementation
- Test files created for validation

## Backward Compatibility

All existing functionality remains intact. The new features are additive and don't break existing code or symbol indexing capabilities.