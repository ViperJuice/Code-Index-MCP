# Embedding Provider Refactoring Plan

## Overview
This plan outlines how to refactor the Code-Index-MCP embedding system from being hardcoded to Voyage AI to supporting multiple embedding providers through a model-agnostic interface.

## Current State Analysis

### Files Using Voyage AI Directly
1. `mcp_server/semantic/enhanced/batch_indexer.py` - Main implementation
2. `mcp_server/utils/semantic_indexer.py` - Utility implementation
3. `mcp_server/config/settings.py` - Configuration

### Current Implementation
```python
# Hardcoded in batch_indexer.py
self.voyage = voyageai.AsyncClient()

# Hardcoded in semantic_indexer.py
self.voyage = voyageai.Client()
embeds = self.voyage.embed(
    texts,
    model="voyage-code-3",
    input_type="document",
    output_dimension=1024,
    output_dtype="float",
).embeddings
```

## Proposed Architecture

### 1. Abstract Base Interface
Create `mcp_server/interfaces/embedding_interfaces.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

class EmbeddingType(Enum):
    """Types of content being embedded"""
    CODE = "code"
    QUERY = "query"
    DOCUMENT = "document"

@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers"""
    model_name: str
    dimension: int
    batch_size: int = 100
    max_tokens: int = 8192
    provider_config: Dict[str, Any] = None

@dataclass
class EmbeddingResult:
    """Result from embedding operation"""
    embeddings: List[List[float]]
    model_used: str
    token_count: int
    metadata: Dict[str, Any] = None

class IEmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""
    
    @abstractmethod
    async def initialize(self, config: EmbeddingConfig) -> None:
        """Initialize the embedding provider"""
        pass
    
    @abstractmethod
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> EmbeddingResult:
        """Generate embeddings for a batch of texts"""
        pass
    
    @abstractmethod
    async def embed_single(
        self, 
        text: str, 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> List[float]:
        """Generate embedding for a single text"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass
    
    @abstractmethod
    async def validate_api_key(self) -> bool:
        """Validate that the API key is valid"""
        pass
```

### 2. Provider Implementations

#### Voyage AI Provider
`mcp_server/semantic/providers/voyage_provider.py`:

```python
import os
import voyageai
from typing import List, Dict, Any, Optional
from ..interfaces.embedding_interfaces import (
    IEmbeddingProvider, EmbeddingConfig, EmbeddingResult, EmbeddingType
)

class VoyageAIProvider(IEmbeddingProvider):
    """Voyage AI embedding provider implementation"""
    
    def __init__(self):
        self.client: Optional[voyageai.AsyncClient] = None
        self.config: Optional[EmbeddingConfig] = None
        
    async def initialize(self, config: EmbeddingConfig) -> None:
        """Initialize Voyage AI client"""
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY environment variable not set")
            
        self.client = voyageai.AsyncClient(api_key=api_key)
        self.config = config
        
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> EmbeddingResult:
        """Generate embeddings using Voyage AI"""
        # Map embedding type to Voyage AI input_type
        input_type_map = {
            EmbeddingType.CODE: "document",
            EmbeddingType.QUERY: "query",
            EmbeddingType.DOCUMENT: "document"
        }
        
        response = await self.client.embed(
            texts,
            model=self.config.model_name,
            input_type=input_type_map[embedding_type],
            output_dimension=self.config.dimension,
            output_dtype="float"
        )
        
        return EmbeddingResult(
            embeddings=response.embeddings,
            model_used=self.config.model_name,
            token_count=response.total_tokens,
            metadata={"provider": "voyage-ai"}
        )
```

#### OpenAI Provider
`mcp_server/semantic/providers/openai_provider.py`:

```python
import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from ..interfaces.embedding_interfaces import (
    IEmbeddingProvider, EmbeddingConfig, EmbeddingResult, EmbeddingType
)

class OpenAIProvider(IEmbeddingProvider):
    """OpenAI embedding provider implementation"""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.config: Optional[EmbeddingConfig] = None
        
    async def initialize(self, config: EmbeddingConfig) -> None:
        """Initialize OpenAI client"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        self.client = AsyncOpenAI(api_key=api_key)
        self.config = config
        
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> EmbeddingResult:
        """Generate embeddings using OpenAI"""
        response = await self.client.embeddings.create(
            model=self.config.model_name,
            input=texts,
            encoding_format="float"
        )
        
        embeddings = [item.embedding for item in response.data]
        
        return EmbeddingResult(
            embeddings=embeddings,
            model_used=response.model,
            token_count=response.usage.total_tokens,
            metadata={"provider": "openai"}
        )
```

#### Local Provider (Sentence Transformers)
`mcp_server/semantic/providers/local_provider.py`:

```python
from sentence_transformers import SentenceTransformer
import torch
from typing import List, Dict, Any, Optional
import numpy as np
from ..interfaces.embedding_interfaces import (
    IEmbeddingProvider, EmbeddingConfig, EmbeddingResult, EmbeddingType
)

class LocalProvider(IEmbeddingProvider):
    """Local embedding provider using Sentence Transformers"""
    
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.config: Optional[EmbeddingConfig] = None
        
    async def initialize(self, config: EmbeddingConfig) -> None:
        """Initialize local model"""
        self.model = SentenceTransformer(config.model_name)
        self.config = config
        
        # Optionally move to GPU if available
        if torch.cuda.is_available():
            self.model = self.model.to('cuda')
            
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> EmbeddingResult:
        """Generate embeddings using local model"""
        # Run in thread pool to avoid blocking
        embeddings = await asyncio.to_thread(
            self.model.encode,
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=True
        )
        
        # Convert to list format
        embeddings_list = embeddings.tolist()
        
        # Estimate token count (rough approximation)
        estimated_tokens = sum(len(text.split()) * 1.3 for text in texts)
        
        return EmbeddingResult(
            embeddings=embeddings_list,
            model_used=self.config.model_name,
            token_count=int(estimated_tokens),
            metadata={"provider": "local", "device": str(self.model.device)}
        )
```

### 3. Provider Factory
`mcp_server/semantic/providers/factory.py`:

```python
from typing import Dict, Type, Optional
from .voyage_provider import VoyageAIProvider
from .openai_provider import OpenAIProvider
from .local_provider import LocalProvider
from .mock_provider import MockProvider
from ..interfaces.embedding_interfaces import IEmbeddingProvider, EmbeddingConfig

class EmbeddingProviderFactory:
    """Factory for creating embedding providers"""
    
    _providers: Dict[str, Type[IEmbeddingProvider]] = {
        "voyage": VoyageAIProvider,
        "openai": OpenAIProvider,
        "local": LocalProvider,
        "mock": MockProvider,  # For testing
    }
    
    _model_mappings = {
        # Voyage AI models
        "voyage-code-3": ("voyage", {"dimension": 1024}),
        "voyage-code-2": ("voyage", {"dimension": 1536}),
        
        # OpenAI models
        "text-embedding-3-small": ("openai", {"dimension": 1536}),
        "text-embedding-3-large": ("openai", {"dimension": 3072}),
        "text-embedding-ada-002": ("openai", {"dimension": 1536}),
        
        # Local models
        "all-MiniLM-L6-v2": ("local", {"dimension": 384}),
        "all-mpnet-base-v2": ("local", {"dimension": 768}),
        "instructor-base": ("local", {"dimension": 768}),
    }
    
    @classmethod
    def create_provider(
        cls, 
        model_name: str,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> IEmbeddingProvider:
        """Create an embedding provider based on model name"""
        
        if model_name not in cls._model_mappings:
            raise ValueError(f"Unknown model: {model_name}")
            
        provider_name, default_config = cls._model_mappings[model_name]
        
        # Merge custom config with defaults
        config_dict = {**default_config, **(custom_config or {})}
        config_dict["model_name"] = model_name
        
        config = EmbeddingConfig(**config_dict)
        
        # Create provider instance
        provider_class = cls._providers[provider_name]
        return provider_class()
    
    @classmethod
    def register_provider(
        cls, 
        name: str, 
        provider_class: Type[IEmbeddingProvider]
    ) -> None:
        """Register a custom provider"""
        cls._providers[name] = provider_class
```

### 4. Configuration Updates
Update `mcp_server/config/settings.py`:

```python
@dataclass
class SemanticSearchSettings:
    """Semantic search configuration"""
    enabled: bool = False
    embedding_model: str = "voyage-code-3"  # Default model
    embedding_dimension: int = 1024
    batch_size: int = 100
    
    # Provider-specific settings
    voyage_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    local_model_cache_dir: str = "./models"
    
    # Advanced settings
    max_retries: int = 3
    timeout_seconds: int = 30
    normalize_embeddings: bool = True
    
    @classmethod
    def from_environment(cls) -> "SemanticSearchSettings":
        """Create settings from environment variables"""
        return cls(
            enabled=os.getenv("ENABLE_SEMANTIC_SEARCH", "false").lower() == "true",
            embedding_model=os.getenv("EMBEDDING_MODEL", "voyage-code-3"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
            voyage_api_key=os.getenv("VOYAGE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            local_model_cache_dir=os.getenv("LOCAL_MODEL_CACHE_DIR", "./models")
        )
```

### 5. Refactored EnhancedVectorSearcher
Update `mcp_server/semantic/enhanced/batch_indexer.py`:

```python
from ..providers.factory import EmbeddingProviderFactory
from ..interfaces.embedding_interfaces import IEmbeddingProvider, EmbeddingType

class EnhancedVectorSearcher:
    """Enhanced vector search system with model-agnostic embeddings"""
    
    def __init__(
        self, 
        config: Optional[VectorSearchConfig] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.config = config or VectorSearchConfig.from_settings()
        self.embedding_provider: Optional[IEmbeddingProvider] = None
        self.qdrant = QdrantClient(location=":memory:")
        self.redis = redis_client
        self.metrics = EmbeddingMetrics()
        
        # Initialize collections for different dimensions
        self._collections: Dict[int, str] = {}
        self._initialize_collections()
        
        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
        
        logger.info(f"Initialized EnhancedVectorSearcher with config: {self.config}")
    
    async def initialize_embedding_provider(self):
        """Initialize the embedding provider"""
        settings = get_settings().semantic_search
        
        # Create provider using factory
        self.embedding_provider = EmbeddingProviderFactory.create_provider(
            model_name=settings.embedding_model,
            custom_config={
                "dimension": settings.embedding_dimension,
                "batch_size": settings.batch_size
            }
        )
        
        # Initialize the provider
        await self.embedding_provider.initialize(
            EmbeddingConfig(
                model_name=settings.embedding_model,
                dimension=settings.embedding_dimension,
                batch_size=settings.batch_size
            )
        )
        
        logger.info(f"Initialized embedding provider: {settings.embedding_model}")
    
    async def generate_embeddings(
        self,
        texts: List[str],
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> List[List[float]]:
        """Generate embeddings using configured provider"""
        if not self.embedding_provider:
            await self.initialize_embedding_provider()
            
        # Check cache first
        uncached_texts = []
        cached_embeddings = {}
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text, embedding_type)
            if cache_key in self._embedding_cache:
                cached_embeddings[i] = self._embedding_cache[cache_key]
                self.metrics.cache_hits += 1
            else:
                uncached_texts.append((i, text))
                self.metrics.cache_misses += 1
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            indices, texts_to_embed = zip(*uncached_texts)
            
            result = await self.embedding_provider.embed_batch(
                texts_to_embed,
                embedding_type
            )
            
            # Update cache
            for idx, embedding in zip(indices, result.embeddings):
                original_text = texts[idx]
                cache_key = self._get_cache_key(original_text, embedding_type)
                self._embedding_cache[cache_key] = embedding
        
        # Combine cached and new embeddings in correct order
        final_embeddings = []
        for i in range(len(texts)):
            if i in cached_embeddings:
                final_embeddings.append(cached_embeddings[i])
            else:
                # Find in newly generated embeddings
                idx_in_uncached = next(j for j, (idx, _) in enumerate(uncached_texts) if idx == i)
                final_embeddings.append(result.embeddings[idx_in_uncached])
        
        return final_embeddings
```

## Implementation Steps

### Phase 1: Core Infrastructure (2-3 days)
1. Create `embedding_interfaces.py` with abstract base classes
2. Create `providers/` directory structure
3. Implement `EmbeddingProviderFactory`
4. Update configuration settings

### Phase 2: Provider Implementations (3-4 days)
1. Implement `VoyageAIProvider` (refactor existing code)
2. Implement `OpenAIProvider`
3. Implement `LocalProvider` for sentence-transformers
4. Create `MockProvider` for testing

### Phase 3: Integration (2-3 days)
1. Refactor `EnhancedVectorSearcher` to use providers
2. Refactor `SemanticIndexer` to use providers
3. Update all embedding generation calls
4. Add provider initialization to startup

### Phase 4: Testing & Documentation (2 days)
1. Create unit tests for each provider
2. Create integration tests for provider switching
3. Update documentation with provider configuration
4. Add provider comparison benchmarks

## Configuration Examples

### Using OpenAI
```bash
export ENABLE_SEMANTIC_SEARCH=true
export EMBEDDING_MODEL=text-embedding-3-small
export OPENAI_API_KEY=sk-...
```

### Using Local Model
```bash
export ENABLE_SEMANTIC_SEARCH=true
export EMBEDDING_MODEL=all-MiniLM-L6-v2
# No API key needed!
```

### Using Voyage AI (current default)
```bash
export ENABLE_SEMANTIC_SEARCH=true
export EMBEDDING_MODEL=voyage-code-3
export VOYAGE_API_KEY=pa-...
```

## Benefits

1. **Flexibility**: Users can choose providers based on:
   - Cost (local models are free)
   - Quality (Voyage AI specializes in code)
   - Privacy (local models keep data on-premise)
   - Speed (local models have no network latency)

2. **Future-Proof**: Easy to add new providers:
   - Cohere
   - Anthropic (when available)
   - Custom enterprise models

3. **Testing**: Mock provider enables testing without API calls

4. **Fallback**: Can implement fallback chains (e.g., try OpenAI, fall back to local)

## Migration Guide

For existing users:
1. No breaking changes - Voyage AI remains the default
2. Existing `VOYAGE_API_KEY` continues to work
3. New `EMBEDDING_MODEL` variable is optional (defaults to voyage-code-3)

## Performance Considerations

1. **Dimension Compatibility**: Different models have different dimensions
   - Need to handle dimension mismatches gracefully
   - May need separate collections per model

2. **Batch Size Optimization**: Different providers have different optimal batch sizes
   - OpenAI: 2048 embeddings per request
   - Voyage AI: 100-1000 per request
   - Local: Limited by GPU memory

3. **Caching Strategy**: Cache embeddings regardless of provider

## Security Considerations

1. **API Key Management**: Each provider uses its own environment variable
2. **Local Model Security**: Ensure model files are from trusted sources
3. **Rate Limiting**: Implement per-provider rate limits

## Conclusion

This refactoring will make Code-Index-MCP's semantic search feature truly flexible, allowing users to choose the embedding provider that best fits their needs while maintaining backward compatibility with the current Voyage AI implementation.