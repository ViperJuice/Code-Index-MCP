# Embedding Provider Migration Guide

## Overview
This guide helps migrate from the hardcoded Voyage AI implementation to the new model-agnostic embedding provider system.

## Quick Migration

### Before (Hardcoded Voyage AI)
```python
import voyageai

client = voyageai.Client()
embeddings = client.embed(
    texts=["code snippet"],
    model="voyage-code-3",
    input_type="document"
).embeddings
```

### After (Model-Agnostic)
```python
from mcp_server.semantic.providers import EmbeddingProviderFactory
from mcp_server.interfaces.embedding_interfaces import EmbeddingConfig, EmbeddingType

# Create provider using factory
factory = EmbeddingProviderFactory()
config = EmbeddingConfig(
    model_name="voyage-code-3",
    dimension=1024
)
provider = factory.create_provider("voyage-code-3", config)

# Initialize and use
await provider.initialize(config)
result = await provider.embed_batch(
    texts=["code snippet"],
    embedding_type=EmbeddingType.DOCUMENT
)
embeddings = result.value.embeddings
```

## Supported Models

### Voyage AI (Original)
- voyage-code-3 (1024d) - Optimized for code
- voyage-code-2 (1536d) - Previous code model
- voyage-2 (1024d) - General purpose
- voyage-large-2 (1536d) - High quality

### OpenAI
- text-embedding-3-small (1536d) - Fast and efficient
- text-embedding-3-large (3072d) - High quality
- text-embedding-ada-002 (1536d) - Legacy model

### Cohere
- embed-english-v3.0 (1024d) - English optimized
- embed-multilingual-v3.0 (1024d) - Multi-language

### Local (No API Required)
- all-MiniLM-L6-v2 (384d) - Fast, general purpose
- all-mpnet-base-v2 (768d) - High quality
- microsoft/codebert-base (768d) - Code optimized

### Google
- text-embedding-004 (768d) - Latest Google model
- embedding-001 (768d) - Previous generation
- textembedding-gecko@003 (768d) - Gecko v3

## Environment Variables

### Before
```bash
VOYAGE_API_KEY=your-key
```

### After (Multiple Options)
```bash
# Choose one or more providers
VOYAGE_API_KEY=your-voyage-key
OPENAI_API_KEY=your-openai-key
COHERE_API_KEY=your-cohere-key
GOOGLE_API_KEY=your-google-key
# Local models don't need API keys
```

## Configuration Examples

### Using Settings
```python
from mcp_server.config.semantic_settings import SemanticSearchSettings

settings = SemanticSearchSettings(
    embedding_model="text-embedding-3-small",  # OpenAI model
    embedding_provider="openai",
    embedding_dimension=1536
)

provider = EmbeddingProviderFactory.create_from_settings(settings)
```

### Direct Factory Usage
```python
# Use any supported model
factory = EmbeddingProviderFactory()

# Option 1: Create by model name (auto-detects provider)
provider = factory.create_provider("all-MiniLM-L6-v2")

# Option 2: Create by provider name
config = EmbeddingConfig(
    model_name="embed-english-v3.0",
    dimension=1024
)
provider = factory.create_provider_by_name("cohere", config)
```

## Backward Compatibility

The system maintains backward compatibility:
- Default model is still `voyage-code-3`
- Existing `VOYAGE_API_KEY` environment variable works
- API structure remains similar

## Testing Your Migration

```python
# Use mock provider for testing
from mcp_server.semantic.providers import MockProvider

config = EmbeddingConfig(
    model_name="mock-embedding",
    dimension=384,
    provider_config={"deterministic": True}
)

mock_provider = MockProvider()
await mock_provider.initialize(config)

# Test with deterministic embeddings
result = await mock_provider.embed_batch(
    ["test text"],
    EmbeddingType.DOCUMENT
)
```

## Performance Considerations

1. **Caching**: All providers support the same caching infrastructure
2. **Batch Processing**: Batch size recommendations:
   - Voyage AI: 100-128 texts
   - OpenAI: 200+ texts
   - Cohere: 96 texts
   - Local: Depends on GPU memory

3. **Dimensions**: Lower dimensions = faster search
   - 384d: Fast, good for general search
   - 768d: Balanced quality/speed
   - 1024d+: High quality, slower

## Common Issues

### Missing API Key
```python
# Error: APIKeyError: OpenAI API key not found
# Solution: Set OPENAI_API_KEY environment variable
```

### Wrong Model Name
```python
# Error: ModelNotSupportedError: Model 'gpt-3' is not supported
# Solution: Use embedding model names, not LLM names
```

### Package Not Installed
```python
# Error: ProviderInitializationError: openai package not installed
# Solution: pip install openai
```

## Full Example: Migrating SemanticIndexer

```python
# Old implementation
class SemanticIndexer:
    def __init__(self):
        self.voyage = voyageai.Client()
    
    def index_file(self, content):
        embeddings = self.voyage.embed(texts, model="voyage-code-3")

# New implementation
class SemanticIndexer:
    def __init__(self, model_name="voyage-code-3"):
        self.factory = EmbeddingProviderFactory()
        self.provider = None
        self.model_name = model_name
    
    async def initialize(self):
        config = EmbeddingConfig(
            model_name=self.model_name,
            dimension=1024
        )
        self.provider = self.factory.create_provider(self.model_name, config)
        await self.provider.initialize(config)
    
    async def index_file(self, content):
        result = await self.provider.embed_batch(
            texts,
            EmbeddingType.CODE
        )
        embeddings = result.value.embeddings
```