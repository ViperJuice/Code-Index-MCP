# HuggingFace Embedding Provider Implementation

## Overview
Added HuggingFace API support to the embedding provider system, enabling access to thousands of embedding models hosted on HuggingFace Hub. NV-Embed-v2 is set as the default HuggingFace model, while Voyage AI remains the overall system default.

## Implementation Details

### HuggingFace Provider (`huggingface_provider.py`)
- **Default Model**: `nvidia/NV-Embed-v2` (4096 dimensions)
- **API Endpoint**: HuggingFace Inference API
- **Features**:
  - Supports any model with feature-extraction pipeline
  - Automatic model loading (first request may take ~20s)
  - Mean pooling for token-level embeddings
  - Dimension adjustment if needed

### Supported Models

#### NVIDIA Models (State-of-the-art)
- `nvidia/NV-Embed-v2` (4096d) - Default, #1 on MTEB leaderboard
- `nvidia/NV-Embed-v1` (4096d) - Previous version
- **Note**: Non-commercial license (CC-BY-NC-4.0)

#### Sentence Transformers
- `sentence-transformers/all-MiniLM-L6-v2` (384d) - Fast, lightweight
- `sentence-transformers/all-mpnet-base-v2` (768d) - High quality
- `sentence-transformers/all-distilroberta-v1` (768d) - Balanced

#### Multilingual Models
- `intfloat/multilingual-e5-large` (1024d) - SOTA multilingual
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768d)
- `BAAI/bge-m3` (1024d) - Multi-functional

#### Code-Specific Models
- `microsoft/codebert-base` (768d) - Programming languages
- `microsoft/unixcoder-base` (768d) - Cross-language code

### Configuration

#### Environment Variable
```bash
# Add to .env file
HUGGINGFACE_API_TOKEN=hf_your_token_here
# Also supports: HF_TOKEN
```

#### Usage Examples

##### Using NV-Embed-v2 (Default HF Model)
```python
from mcp_server.semantic.providers import EmbeddingProviderFactory
from mcp_server.interfaces.embedding_interfaces import EmbeddingConfig, EmbeddingType

factory = EmbeddingProviderFactory()
provider = factory.create_provider("nvidia/NV-Embed-v2")

config = EmbeddingConfig(
    model_name="nvidia/NV-Embed-v2",
    dimension=4096
)
await provider.initialize(config)

result = await provider.embed_batch(
    ["Your text here"],
    EmbeddingType.DOCUMENT
)
```

##### Using Custom HuggingFace Model
```python
# Any model with feature-extraction pipeline works
custom_model = "your-username/your-model"

config = EmbeddingConfig(
    model_name=custom_model,
    dimension=768,  # Set based on model
    provider_config={"api_token": "hf_..."}
)

provider = factory.create_provider_by_name("huggingface", config)
```

### System Defaults

1. **Overall Default**: `voyage-code-3` (Voyage AI) - Unchanged
2. **HuggingFace Default**: `nvidia/NV-Embed-v2`
3. **Backward Compatibility**: Fully maintained

### Key Benefits

1. **Model Variety**: Access to 10,000+ models on HuggingFace
2. **State-of-the-art**: NV-Embed-v2 is currently #1 on MTEB
3. **Flexibility**: Use any feature-extraction model
4. **No Infrastructure**: Managed API, no GPU needed

### Considerations

1. **API Limits**: Free tier has 30k requests/month
2. **First Request**: ~20s for model loading
3. **License**: NV-Embed models are non-commercial
4. **Dimension Variability**: Different models have different dimensions

### Performance Tips

1. **Batch Processing**: Send multiple texts in one request
2. **Model Selection**: Choose based on your needs:
   - Speed: `all-MiniLM-L6-v2` (384d)
   - Quality: `NV-Embed-v2` (4096d)
   - Multilingual: `multilingual-e5-large` (1024d)
3. **Caching**: Implement caching for repeated queries

### Current Provider Count

- **Total Providers**: 7 (Voyage, OpenAI, Google, Cohere, Local, Mock, HuggingFace)
- **Total Models**: 40+ across all providers
- **Default Provider**: Voyage AI (unchanged)
- **HuggingFace Models**: 13 predefined + unlimited custom

## Summary

The HuggingFace provider adds significant flexibility to the embedding system:
- ✅ Access to thousands of models
- ✅ State-of-the-art NV-Embed-v2 as HF default
- ✅ Voyage AI remains system default
- ✅ Support for custom models
- ✅ Fully integrated with factory pattern

The system now supports virtually any embedding use case while maintaining simplicity and backward compatibility.