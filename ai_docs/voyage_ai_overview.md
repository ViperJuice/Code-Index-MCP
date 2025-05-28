# Voyage AI Documentation Overview

## Introduction
Voyage AI provides state-of-the-art embedding and reranking models designed to transform unstructured data into semantic vector representations. Their services enable advanced search, retrieval-augmented generation (RAG), and domain-specific AI applications.

## Core Services

### 1. Text Embeddings
Voyage AI's embedding models convert text into dense numerical vectors that capture semantic meaning. These embeddings power:
- Semantic search applications
- Retrieval-augmented generation (RAG)
- Domain-specific chatbots
- Knowledge base systems

### 2. Multimodal Embeddings
The `voyage-multimodal-3` model extends capabilities beyond text to handle:
- Documents
- Images
- Audio
- Video
- Tabular data

### 3. Reranking Models
Neural networks that score relevance between queries and documents, improving search accuracy by reordering initial results.

## Available Models

### General-Purpose Models
- **voyage-3-large**: Best quality, multilingual support (1024D default, 256-2048D flexible)
- **voyage-3.5**: Optimized for general use, multilingual
- **voyage-3.5-lite**: Optimized for latency and cost efficiency

### Specialized Models
- **voyage-code-3**: Optimized for code retrieval and understanding
- **voyage-finance-2**: Finance domain specialist with regulatory knowledge
- **voyage-law-2**: Legal domain specialist for case law and contracts
- **voyage-multimodal-3**: Handles text and image embeddings

### Reranking Models
- **rerank-2**: Best quality cross-encoder (16K token context)
- **rerank-2-lite**: Faster alternative (8K token context)

## Technical Specifications

### Model Capabilities
- **Context Length**: 32,000 tokens for most models
- **Output Dimensions**: Flexible (256, 512, 1024, 2048)
- **Output Formats**: float, int8, binary
- **Input Types**: Supports query/document type specification

### Rate Limits
- Basic tier: 3-16M tokens per minute (TPM)
- 2000 requests per minute (RPM)
- Limits increase with usage tiers

## API Usage

### Installation
```bash
pip install -U voyageai
export VOYAGE_API_KEY="<your-api-key>"
```

### Basic Embedding Example
```python
import voyageai

vo = voyageai.Client()

# Text embedding
embeddings = vo.embed(
    texts=["Query text", "Document text"],
    model="voyage-3",
    input_type="document"  # or "query"
)

# Access embeddings
vectors = embeddings.embeddings
```

### Reranking Example
```python
# Rerank documents based on query
results = vo.rerank(
    query="What is machine learning?",
    documents=[doc1, doc2, doc3],
    model="rerank-2",
    top_k=3
)

# Results include relevance scores
for result in results.results:
    print(f"Index: {result.index}, Score: {result.relevance_score}")
```

### Multimodal Example
```python
# Embed text and images together
result = vo.multimodal_embed(
    inputs=[
        {"content": "A beautiful sunset", "content_type": "text"},
        {"content": base64_image, "content_type": "image"}
    ],
    model="voyage-multimodal-3"
)
```

## Pricing

### Free Tier
- **General models**: 200M tokens
- **Specialized models**: 50M tokens
- **Multimodal**: 200M text tokens + 150B pixels

### Paid Usage (per 1M tokens)
- **Text embeddings**: $0.02 - $0.18
- **Multimodal text**: $0.12
- **Multimodal images**: $0.60 per 1B pixels
- **Rerankers**: $0.02 - $0.05

## Best Practices

1. **Model Selection**
   - Use general-purpose models for broad applications
   - Choose specialized models for domain-specific tasks
   - Consider lite versions for latency-sensitive applications

2. **Optimization Strategies**
   - Adjust output dimensions based on accuracy/cost tradeoffs
   - Use query/document input types for better retrieval
   - Implement reranking after initial search for improved relevance

3. **Integration Patterns**
   - Combine with vector databases for scalable search
   - Use in RAG pipelines with LLMs
   - Implement caching for frequently accessed embeddings

4. **Security**
   - Store API keys as environment variables
   - Use async clients for high-throughput applications
   - Monitor usage to stay within rate limits

## Use Cases

1. **Semantic Search**: Find relevant documents based on meaning rather than keywords
2. **RAG Applications**: Enhance LLM responses with retrieved context
3. **Document Classification**: Organize content based on semantic similarity
4. **Cross-Modal Search**: Find images using text queries or vice versa
5. **Domain-Specific Applications**: Legal research, financial analysis, code search

## Integration with MCP Server

Voyage AI's embedding models could enhance the MCP Server's code indexing capabilities by:
- Providing semantic search across codebases
- Enabling natural language queries for code discovery
- Supporting cross-language code similarity detection
- Improving symbol resolution through semantic understanding

The models' flexible dimensions and specialized code model (`voyage-code-3`) make them particularly suitable for integration with the MCP Server's plugin architecture.