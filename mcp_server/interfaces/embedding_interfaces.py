"""
Embedding Provider Interfaces

Defines the contract for all embedding providers to enable model-agnostic
semantic search functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .shared_interfaces import Result


class EmbeddingType(Enum):
    """Types of content being embedded"""
    CODE = "code"
    QUERY = "query"
    DOCUMENT = "document"
    COMMENT = "comment"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers"""
    model_name: str
    dimension: int
    batch_size: int = 100
    max_tokens: int = 8192
    normalize: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    provider_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.dimension <= 0:
            raise ValueError(f"Invalid dimension: {self.dimension}")
        if self.batch_size <= 0:
            raise ValueError(f"Invalid batch_size: {self.batch_size}")
        if self.max_tokens <= 0:
            raise ValueError(f"Invalid max_tokens: {self.max_tokens}")


@dataclass
class EmbeddingResult:
    """Result from embedding operation"""
    embeddings: List[List[float]]
    model_used: str
    token_count: int
    dimension: int
    processing_time_ms: float
    provider: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate embeddings match expected dimension"""
        if self.embeddings and len(self.embeddings[0]) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(self.embeddings[0])}"
            )


@dataclass
class EmbeddingBatch:
    """Batch of texts to be embedded"""
    texts: List[str]
    embedding_type: EmbeddingType
    metadata: List[Dict[str, Any]] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.texts)
    
    def validate(self) -> None:
        """Validate batch consistency"""
        if self.metadata and len(self.metadata) != len(self.texts):
            raise ValueError("Metadata count must match text count")


class IEmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""
    
    @abstractmethod
    async def initialize(self, config: EmbeddingConfig) -> Result[None]:
        """
        Initialize the embedding provider
        
        Args:
            config: Provider configuration
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> Result[EmbeddingResult]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of texts to embed
            embedding_type: Type of content being embedded
            
        Returns:
            Result containing embeddings or error
        """
        pass
    
    @abstractmethod
    async def embed_single(
        self, 
        text: str, 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> Result[List[float]]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            embedding_type: Type of content being embedded
            
        Returns:
            Result containing embedding vector or error
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        
        Returns:
            Dictionary with model metadata
        """
        pass
    
    @abstractmethod
    async def validate_api_key(self) -> Result[bool]:
        """
        Validate that the API key is valid
        
        Returns:
            Result indicating if API key is valid
        """
        pass
    
    @abstractmethod
    async def estimate_tokens(self, texts: List[str]) -> int:
        """
        Estimate token count for texts
        
        Args:
            texts: List of texts to estimate
            
        Returns:
            Estimated total token count
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up provider resources"""
        pass


class IEmbeddingCache(ABC):
    """Interface for embedding cache implementations"""
    
    @abstractmethod
    async def get(
        self, 
        text: str, 
        embedding_type: EmbeddingType,
        model: str
    ) -> Optional[List[float]]:
        """
        Retrieve cached embedding
        
        Args:
            text: Original text
            embedding_type: Type of embedding
            model: Model used for embedding
            
        Returns:
            Embedding vector if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def put(
        self, 
        text: str, 
        embedding: List[float],
        embedding_type: EmbeddingType,
        model: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store embedding in cache
        
        Args:
            text: Original text
            embedding: Embedding vector
            embedding_type: Type of embedding
            model: Model used for embedding
            ttl_seconds: Time to live in seconds
        """
        pass
    
    @abstractmethod
    async def get_batch(
        self,
        texts: List[str],
        embedding_type: EmbeddingType,
        model: str
    ) -> Dict[str, List[float]]:
        """
        Retrieve multiple cached embeddings
        
        Args:
            texts: List of texts
            embedding_type: Type of embedding
            model: Model used for embedding
            
        Returns:
            Dictionary of text -> embedding for found items
        """
        pass
    
    @abstractmethod
    async def clear(self, model: Optional[str] = None) -> int:
        """
        Clear cache entries
        
        Args:
            model: Clear only entries for specific model
            
        Returns:
            Number of entries cleared
        """
        pass


class IProviderRegistry(ABC):
    """Interface for provider registry"""
    
    @abstractmethod
    def register_provider(
        self, 
        name: str, 
        provider_class: type,
        models: List[str]
    ) -> None:
        """Register a provider with supported models"""
        pass
    
    @abstractmethod
    def get_provider_for_model(self, model: str) -> Optional[str]:
        """Get provider name for a model"""
        pass
    
    @abstractmethod
    def list_available_models(self) -> List[str]:
        """List all available models"""
        pass
    
    @abstractmethod
    def list_providers(self) -> List[str]:
        """List all registered providers"""
        pass