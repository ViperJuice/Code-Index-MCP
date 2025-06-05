"""
Semantic Search Configuration Settings

Centralizes all configuration for semantic search and embedding providers.
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SemanticSearchSettings:
    """Configuration for semantic search functionality"""
    
    # Core settings
    enabled: bool = False
    embedding_model: str = "voyage-code-3"  # Default model
    embedding_dimension: int = 1024
    batch_size: int = 100
    
    # Provider settings
    embedding_provider: Optional[str] = None  # Auto-detected from model
    
    # API Keys (provider-specific)
    voyage_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None  # For future use
    
    # Local model settings
    local_model_cache_dir: str = "./models"
    local_model_device: str = "cpu"  # cpu, cuda, mps
    
    # Performance settings
    max_retries: int = 3
    timeout_seconds: int = 30
    normalize_embeddings: bool = True
    embedding_cache_enabled: bool = True
    embedding_cache_ttl: int = 3600  # 1 hour
    max_concurrent_requests: int = 5
    
    # Vector store settings
    vector_store_type: str = "qdrant"  # qdrant, pinecone, weaviate, chromadb
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "code-index"
    
    # Search settings
    similarity_threshold: float = 0.7
    max_results: int = 50
    include_metadata: bool = True
    rerank_results: bool = False
    
    # Advanced settings
    chunk_size: int = 512  # For splitting large texts
    chunk_overlap: int = 50
    preprocessing_enabled: bool = True
    
    # Model-specific configurations
    model_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "voyage-code-3": {
            "dimension": 1024,
            "max_tokens": 16000,
            "provider": "voyage"
        },
        "voyage-code-2": {
            "dimension": 1536,
            "max_tokens": 4000,
            "provider": "voyage"
        },
        "text-embedding-3-small": {
            "dimension": 1536,
            "max_tokens": 8191,
            "provider": "openai"
        },
        "text-embedding-3-large": {
            "dimension": 3072,
            "max_tokens": 8191,
            "provider": "openai"
        },
        "text-embedding-ada-002": {
            "dimension": 1536,
            "max_tokens": 8191,
            "provider": "openai"
        },
        "embed-english-v3.0": {
            "dimension": 1024,
            "max_tokens": 512,
            "provider": "cohere"
        },
        "all-MiniLM-L6-v2": {
            "dimension": 384,
            "max_tokens": 256,
            "provider": "local"
        },
        "all-mpnet-base-v2": {
            "dimension": 768,
            "max_tokens": 384,
            "provider": "local"
        },
        "instructor-base": {
            "dimension": 768,
            "max_tokens": 512,
            "provider": "local"
        }
    })
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Auto-detect provider from model if not specified
        if not self.embedding_provider and self.embedding_model in self.model_configs:
            self.embedding_provider = self.model_configs[self.embedding_model]["provider"]
            
        # Update dimension based on model
        if self.embedding_model in self.model_configs:
            model_config = self.model_configs[self.embedding_model]
            self.embedding_dimension = model_config["dimension"]
        
        # Ensure local model cache directory exists
        if self.embedding_provider == "local":
            Path(self.local_model_cache_dir).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_environment(cls) -> "SemanticSearchSettings":
        """Create settings from environment variables"""
        # Helper to parse boolean
        def parse_bool(value: str) -> bool:
            return value.lower() in ("true", "1", "yes", "on")
        
        return cls(
            # Core settings
            enabled=parse_bool(os.getenv("ENABLE_SEMANTIC_SEARCH", "false")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "voyage-code-3"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
            
            # Provider settings
            embedding_provider=os.getenv("EMBEDDING_PROVIDER"),
            
            # API Keys
            voyage_api_key=os.getenv("VOYAGE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            cohere_api_key=os.getenv("COHERE_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            
            # Local model settings
            local_model_cache_dir=os.getenv("LOCAL_MODEL_CACHE_DIR", "./models"),
            local_model_device=os.getenv("LOCAL_MODEL_DEVICE", "cpu"),
            
            # Performance settings
            max_retries=int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
            timeout_seconds=int(os.getenv("EMBEDDING_TIMEOUT", "30")),
            normalize_embeddings=parse_bool(os.getenv("NORMALIZE_EMBEDDINGS", "true")),
            embedding_cache_enabled=parse_bool(os.getenv("EMBEDDING_CACHE_ENABLED", "true")),
            embedding_cache_ttl=int(os.getenv("EMBEDDING_CACHE_TTL", "3600")),
            
            # Vector store settings
            vector_store_type=os.getenv("VECTOR_STORE_TYPE", "qdrant"),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            collection_name=os.getenv("COLLECTION_NAME", "code-index"),
            
            # Search settings
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
            max_results=int(os.getenv("MAX_SEARCH_RESULTS", "50")),
            include_metadata=parse_bool(os.getenv("INCLUDE_METADATA", "true")),
            rerank_results=parse_bool(os.getenv("RERANK_RESULTS", "false")),
            
            # Advanced settings
            chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            preprocessing_enabled=parse_bool(os.getenv("PREPROCESSING_ENABLED", "true"))
        )
    
    def get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Get the appropriate API key for a provider"""
        key_mapping = {
            "voyage": self.voyage_api_key,
            "openai": self.openai_api_key,
            "cohere": self.cohere_api_key,
            "anthropic": self.anthropic_api_key,
            "local": None  # No API key needed
        }
        return key_mapping.get(provider)
    
    def get_model_config(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        model = model or self.embedding_model
        return self.model_configs.get(model, {})
    
    def list_available_models(self) -> List[str]:
        """List all available embedding models"""
        return list(self.model_configs.keys())
    
    def validate(self) -> List[str]:
        """Validate settings and return list of issues"""
        issues = []
        
        # Check if enabled
        if not self.enabled:
            return ["Semantic search is disabled"]
        
        # Check model exists
        if self.embedding_model not in self.model_configs:
            issues.append(f"Unknown embedding model: {self.embedding_model}")
        
        # Check API key for non-local providers
        if self.embedding_provider != "local":
            api_key = self.get_api_key_for_provider(self.embedding_provider)
            if not api_key:
                issues.append(f"Missing API key for provider: {self.embedding_provider}")
        
        # Check vector store
        if self.vector_store_type == "qdrant":
            # Could add connection check here
            pass
        
        # Check dimensions
        if self.embedding_dimension <= 0:
            issues.append(f"Invalid embedding dimension: {self.embedding_dimension}")
        
        # Check batch size
        if self.batch_size <= 0:
            issues.append(f"Invalid batch size: {self.batch_size}")
        
        return issues