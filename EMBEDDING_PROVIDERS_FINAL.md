# Final Embedding Providers Implementation

## Overview
The Code-Index-MCP now supports 7 embedding providers with 40+ models, providing flexible options for semantic search across different use cases, budgets, and deployment scenarios. Voyage AI remains the default provider, with HuggingFace offering access to thousands of additional models.

## Supported Providers

### 1. Voyage AI ✅
- **Models**: voyage-code-3, voyage-code-2, voyage-2, voyage-large-2
- **Best For**: Code embeddings and technical content
- **Dimensions**: 1024-1536
- **Status**: Fully working

### 2. OpenAI ✅
- **Models**: text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
- **Best For**: General-purpose text embeddings
- **Dimensions**: 1536-3072
- **Status**: Working (check API key)

### 3. Google ✅
- **Models**: text-embedding-004, embedding-001, textembedding-gecko@001/002/003
- **Best For**: General text with free tier available
- **Dimensions**: 768
- **Status**: Fully implemented

### 4. Cohere ✅
- **Models**: embed-english-v3.0, embed-multilingual-v3.0, embed-english-light-v3.0
- **Best For**: Multilingual content
- **Dimensions**: 384-1024
- **Status**: Working (requires `pip install cohere`)

### 5. Local (Sentence Transformers) ✅
- **Models**: all-MiniLM-L6-v2, all-mpnet-base-v2, microsoft/codebert-base, e5-large-v2, and more
- **Best For**: Privacy-conscious deployments, offline usage
- **Dimensions**: 384-1024
- **Status**: Fully working

### 6. Mock ✅
- **Models**: mock-embedding, mock-embedding-small/base/large
- **Best For**: Testing and development
- **Dimensions**: Configurable
- **Status**: Fully working

### 7. HuggingFace ✅
- **Models**: nvidia/NV-Embed-v2 (default), 13+ predefined models, unlimited custom models
- **Best For**: Access to cutting-edge models, experimentation
- **Dimensions**: Varies by model (384-4096)
- **Status**: Fully implemented

## Quick Start

### Installation
```bash
# Core dependencies (already installed)
pip install voyageai

# Optional providers
pip install openai          # For OpenAI
pip install google-generativeai  # For Google
pip install cohere          # For Cohere
pip install sentence-transformers  # For local models
```

### Environment Variables
```bash
# Add to .env file
VOYAGE_API_KEY=your-voyage-key      # For Voyage AI (DEFAULT)
OPENAI_API_KEY=your-openai-key      # For OpenAI
GOOGLE_API_KEY=your-google-key      # For Google
COHERE_API_KEY=your-cohere-key      # For Cohere
HUGGINGFACE_API_TOKEN=hf_xxx        # For HuggingFace
# Local and Mock providers don't need API keys
```

### Usage Example
```python
from mcp_server.semantic.providers import EmbeddingProviderFactory
from mcp_server.interfaces.embedding_interfaces import EmbeddingConfig, EmbeddingType

# Create factory
factory = EmbeddingProviderFactory()

# Option 1: Auto-detect provider from model name
provider = factory.create_provider("text-embedding-004")  # Uses Google

# Option 2: Create with custom config
config = EmbeddingConfig(
    model_name="voyage-code-3",
    dimension=1024,
    batch_size=100
)
provider = factory.create_provider("voyage-code-3", config)

# Initialize and use
await provider.initialize(config)
result = await provider.embed_batch(
    ["def hello(): print('Hello')"],
    EmbeddingType.CODE
)
embeddings = result.value.embeddings
```

## Provider Selection Guide

| Use Case | Recommended Provider | Model | Why |
|----------|---------------------|-------|-----|
| Code Search | Voyage AI | voyage-code-3 | Optimized for code understanding |
| General Text | OpenAI | text-embedding-3-small | High quality, good balance |
| State-of-the-art | HuggingFace | nvidia/NV-Embed-v2 | #1 on MTEB leaderboard |
| Budget Conscious | Google | text-embedding-004 | Free tier available |
| Multilingual | Cohere | embed-multilingual-v3.0 | Best multilingual support |
| Privacy/Offline | Local | all-MiniLM-L6-v2 | No API calls needed |
| Development | Mock | mock-embedding | Deterministic, no API needed |

## Performance Comparison

| Provider | Speed | Quality | Cost | Privacy |
|----------|-------|---------|------|----------|
| Voyage | Fast | Excellent (code) | $$ | API-based |
| OpenAI | Fast | Excellent | $$$ | API-based |
| Google | Fast | Good | $ | API-based |
| Cohere | Medium | Good | $$ | API-based |
| Local | Slow* | Good | Free | Full privacy |
| Mock | Instant | N/A | Free | Full privacy |

*Local speed depends on hardware (GPU vs CPU)

## Model Dimensions

- **384d**: Fast search, lower quality (local models)
- **768d**: Good balance (Google, some local models)
- **1024d**: High quality (Voyage, Cohere)
- **1536d+**: Highest quality, slower (OpenAI large models)

## Migration from Hardcoded Voyage

The system maintains backward compatibility:
- Default model is still `voyage-code-3`
- `VOYAGE_API_KEY` environment variable still works
- Existing code continues to function

## Testing Providers

```bash
# Run provider tests
python -m mcp_server.semantic.providers.provider_tests
```

## Common Issues

1. **Missing API Key**
   - Solution: Set appropriate environment variable
   - Example: `export OPENAI_API_KEY=your-key`

2. **Package Not Installed**
   - Solution: Install provider package
   - Example: `pip install cohere`

3. **Invalid Model Name**
   - Solution: Check supported models list
   - Use `factory.list_available_models()`

4. **Rate Limits**
   - Solution: Implement caching (Phase 3)
   - Use batch processing
   - Consider local models for high volume

## What's Next (Phase 3)

1. **Caching Layer**
   - Redis integration
   - Persistent embeddings
   - Cache warming

2. **Performance Monitoring**
   - Track generation times
   - Cost tracking
   - Usage analytics

3. **Advanced Features**
   - Automatic failover
   - Load balancing
   - A/B testing

## Summary

The embedding provider system is now:
- ✅ Model-agnostic with 6 providers
- ✅ Supporting 25+ embedding models
- ✅ Maintaining backward compatibility
- ✅ Providing clear error messages
- ✅ Ready for production use

The system intelligently handles provider selection, error cases, and provides flexibility for different deployment scenarios while maintaining the simplicity of the original Voyage-only implementation.