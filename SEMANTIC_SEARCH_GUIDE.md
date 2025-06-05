# Semantic Code Search Implementation Guide

## Overview
This guide demonstrates how semantic search enhances code retrieval beyond simple keyword matching, using embeddings to understand the conceptual meaning of queries and code.

## How It Works

### 1. Code Indexing
When indexing code, each symbol is converted into a rich text representation:
```
Symbol: authenticate (function in javascript)
File: express-api/src/middleware/auth.js
Signature: function authenticate(req, res, next)
Context: 
  function authenticate(req, res, next) {
    const token = req.headers.authorization;
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }
```

### 2. Embedding Generation
This text is converted into a high-dimensional vector (embedding) that captures its semantic meaning:
- With **Voyage AI**: Uses the `voyage-code-3` model specifically trained on code (currently the only supported provider)
- With **Mock Embeddings**: Uses concept-based features for demonstration/testing

**Note on API Keys**: 
- Only the Voyage AI API key is needed, and only if you enable semantic search
- The system is currently hardcoded to use Voyage AI, but could be extended to support other providers
- All other core functionality works without any API keys

### 3. Query Processing
Natural language queries are converted to embeddings using the same process:
- "How do I handle user authentication?" → embedding vector
- "Functions that validate input" → embedding vector
- "Database connection code" → embedding vector

### 4. Similarity Search
Code is retrieved by finding the most similar embeddings using cosine similarity:
```
similarity = dot_product(query_embedding, code_embedding)
```

## Key Advantages

### Natural Language Understanding
**Query**: "How do I handle user authentication?"
- **Keyword Search**: Would only find code with "handle", "user", "authentication"
- **Semantic Search**: Finds `authenticate()`, `login()`, `checkPermissions()` functions

### Cross-Language Pattern Recognition
**Query**: "API endpoints that return data"
- Finds similar patterns across languages:
  - Python: `@app.route('/users')` 
  - JavaScript: `router.get('/api/users')`
  - Java: `@GetMapping("/users")`
  - Go: `func HandleUsers(w, r)`

### Conceptual Matching
**Query**: "error handling logic"
- Matches various implementations:
  - `try/catch` blocks
  - `if err != nil` patterns
  - Exception handlers
  - Error middleware

## Implementation with Voyage AI

### 1. Install Dependencies
```bash
pip install voyageai qdrant-client
```

### 2. Set Up Environment
```bash
export VOYAGE_API_KEY="your-api-key"
export QDRANT_URL="http://localhost:6333"  # or cloud URL
```

### 3. Initialize Semantic Indexer
```python
from mcp_server.utils.semantic_indexer import SemanticIndexer

semantic_indexer = SemanticIndexer(
    voyage_api_key=os.getenv("VOYAGE_API_KEY"),
    qdrant_url=os.getenv("QDRANT_URL"),
    collection_name="code_index"
)
```

### 4. Index Code
```python
# Create embeddings for code
texts = []
metadata = []

for symbol in code_symbols:
    # Create rich text representation
    text = f"{symbol.name} ({symbol.kind} in {symbol.language})\n"
    text += f"Signature: {symbol.signature}\n"
    text += f"Context: {symbol.context}"
    
    texts.append(text)
    metadata.append({
        "file": symbol.file,
        "symbol": symbol.name,
        "kind": symbol.kind,
        "line": symbol.line
    })

# Batch embed and store
semantic_indexer.index_batch(texts, metadata)
```

### 5. Search Code
```python
# Natural language query
query = "functions that handle HTTP requests and return JSON"

# Semantic search
results = semantic_indexer.search(query, limit=10)

for text, metadata, score in results:
    print(f"{metadata['symbol']} - Score: {score:.3f}")
    print(f"  File: {metadata['file']}:{metadata['line']}")
```

## Performance Comparison

### Test Results from Demo

#### Query: "authentication and user login functionality"
**Semantic Search Results**:
1. `authenticate()` function - Score: 0.856
2. `login()` function - Score: 0.782
3. `getUsers()` function - Score: 0.337

**Keyword Search Results**:
- Only found files containing exact words "authentication" or "login"
- Missed conceptually related code like `checkPermissions()` or `validateToken()`

#### Query: "validate user input and check email format"
**Semantic Search** found:
- `validateEmail()` method
- Form validation functions
- Input sanitization code

**Keyword Search** missed:
- Functions named `checkInput()` or `sanitize()`
- Validation logic without the word "validate"

## Best Practices

### 1. Rich Context
Include surrounding code context when creating embeddings:
```python
# Good: Includes context
text = f"{symbol} with context:\n{code_snippet}"

# Less effective: Just the symbol name
text = symbol_name
```

### 2. Metadata Enrichment
Store additional metadata for filtering:
```python
metadata = {
    "symbol": "validateUser",
    "kind": "function",
    "language": "python",
    "file": "auth.py",
    "line": 45,
    "tags": ["validation", "security", "auth"]
}
```

### 3. Hybrid Search
Combine semantic and keyword search for best results:
```python
# Get semantic results
semantic_results = semantic_search(query)

# Get keyword results for exact matches
keyword_results = keyword_search(query)

# Merge and re-rank
combined_results = merge_results(semantic_results, keyword_results)
```

## Cost Considerations

### Voyage AI Pricing (as of 2024)
- Embedding generation: ~$0.10 per 1M tokens
- Storage: Depends on vector database choice

### Optimization Tips
1. **Batch Operations**: Embed multiple texts in one API call
2. **Caching**: Store embeddings to avoid re-computation
3. **Selective Indexing**: Only embed important symbols
4. **Dimension Reduction**: Use smaller models for less critical searches

## Running Qdrant Locally

### Docker Setup
```bash
# Run Qdrant vector database
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

### Cloud Alternative
Use Qdrant Cloud for production:
```python
qdrant_url = "https://your-cluster.qdrant.io"
qdrant_api_key = "your-api-key"
```

## Conclusion

Semantic search transforms code retrieval from pattern matching to understanding:
- **Natural language queries** → Find code by describing what it does
- **Cross-language search** → Find similar patterns in any language
- **Conceptual understanding** → Match by meaning, not just keywords

The combination of Voyage AI's code-specific embeddings and Qdrant's vector search provides a powerful foundation for intelligent code retrieval at scale.