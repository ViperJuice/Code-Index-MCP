"""
Mock Embedding Provider

Provides deterministic embeddings for testing without requiring external APIs
or model downloads. Useful for unit tests and development.
"""

import hashlib
import asyncio
from typing import List, Dict, Any, Optional
import logging
import numpy as np

from mcp_server.interfaces.embedding_interfaces import (
    EmbeddingConfig,
    EmbeddingResult,
    EmbeddingType
)
from .result import Result
from .base import BaseEmbeddingProvider
from .exceptions import EmbeddingGenerationError

logger = logging.getLogger(__name__)


class MockProvider(BaseEmbeddingProvider):
    """Mock embedding provider for testing"""
    
    # Mock models with different dimensions for testing
    SUPPORTED_MODELS = {
        "mock-embedding-small": {
            "dimension": 384,
            "max_tokens": 1000,
            "description": "Small mock model for fast tests"
        },
        "mock-embedding-base": {
            "dimension": 768,
            "max_tokens": 2000,
            "description": "Base mock model"
        },
        "mock-embedding-large": {
            "dimension": 1024,
            "max_tokens": 4000,
            "description": "Large mock model"
        },
        "mock-embedding-xlarge": {
            "dimension": 1536,
            "max_tokens": 8000,
            "description": "Extra large mock model"
        },
        "mock-embedding": {
            "dimension": 384,
            "max_tokens": 1000,
            "description": "Default mock model"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.embedding_cache: Dict[str, List[float]] = {}
        self.call_count = 0
        self.delay_ms = 0  # Configurable delay for testing
        self._initialized = False
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize mock provider"""
        # Get test configuration
        self.delay_ms = self.config.provider_config.get("delay_ms", 0)
        self.deterministic = self.config.provider_config.get("deterministic", True)
        self.fail_rate = self.config.provider_config.get("fail_rate", 0.0)
        
        # Validate model
        if self.config.model_name not in self.SUPPORTED_MODELS:
            # Allow any model name for flexibility in testing
            logger.warning(
                f"Model '{self.config.model_name}' not in predefined list, "
                f"using dimension {self.config.dimension}"
            )
        
        self._initialized = True
        logger.info(
            f"Initialized mock provider with model '{self.config.model_name}' "
            f"(dim={self.config.dimension}, delay={self.delay_ms}ms)"
        )
        
        return Result.success(None)
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate mock embeddings"""
        if not self._initialized:
            return Result.error(
                EmbeddingGenerationError("Mock provider not initialized")
            )
        
        # Simulate failure for testing error handling
        if self.fail_rate > 0 and np.random.random() < self.fail_rate:
            return Result.error(
                EmbeddingGenerationError("Simulated embedding failure")
            )
        
        # Add configurable delay
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)
        
        self.call_count += 1
        
        try:
            embeddings = []
            
            for text in texts:
                # Generate deterministic embedding based on text content
                if self.deterministic:
                    embedding = self._generate_deterministic_embedding(
                        text,
                        embedding_type
                    )
                else:
                    # Random embeddings for non-deterministic mode
                    embedding = np.random.randn(self.config.dimension).tolist()
                    if self.config.normalize:
                        # Normalize to unit vector
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = (np.array(embedding) / norm).tolist()
                
                embeddings.append(embedding)
            
            # Mock token count
            token_count = sum(len(text.split()) for text in texts)
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=token_count,
                dimension=self.config.dimension,
                processing_time_ms=self.delay_ms,
                provider="mock",
                metadata={
                    "call_count": self.call_count,
                    "deterministic": self.deterministic,
                    "embedding_type": embedding_type.value,
                    "mock": True
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            return Result.error(
                EmbeddingGenerationError(f"Mock embedding generation failed: {str(e)}")
            )
    
    def _generate_deterministic_embedding(
        self,
        text: str,
        embedding_type: EmbeddingType
    ) -> List[float]:
        """Generate deterministic embedding from text"""
        # Create a unique seed from text and embedding type
        seed_str = f"{embedding_type.value}:{text}"
        seed_bytes = seed_str.encode('utf-8')
        
        # Use SHA256 to generate deterministic values
        hash_hex = hashlib.sha256(seed_bytes).hexdigest()
        
        # Convert hex to floats
        embedding = []
        
        # Each hex pair gives us a value 0-255, normalize to [-1, 1]
        for i in range(0, min(len(hash_hex) // 2, self.config.dimension)):
            hex_pair = hash_hex[i*2:(i+1)*2]
            value = int(hex_pair, 16) / 127.5 - 1.0  # Normalize to [-1, 1]
            embedding.append(value)
        
        # If we need more dimensions, cycle through the hash
        while len(embedding) < self.config.dimension:
            # Create additional hash for more values
            hash_hex = hashlib.sha256(hash_hex.encode()).hexdigest()
            for i in range(0, min(len(hash_hex) // 2, self.config.dimension - len(embedding))):
                hex_pair = hash_hex[i*2:(i+1)*2]
                value = int(hex_pair, 16) / 127.5 - 1.0
                embedding.append(value)
        
        # Ensure exact dimension
        embedding = embedding[:self.config.dimension]
        
        # Normalize if requested
        if self.config.normalize:
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (np.array(embedding) / norm).tolist()
        
        return embedding
    
    async def validate_api_key(self) -> Result[bool]:
        """Mock provider doesn't need API key"""
        # Can simulate API key validation failure for testing
        if self.config.provider_config.get("simulate_invalid_key", False):
            return Result.success(False)
        return Result.success(True)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Simple token estimation for mock provider"""
        # Simple word count estimation
        return sum(len(text.split()) for text in texts)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get mock provider information"""
        base_info = super().get_model_info()
        
        # Add mock-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "call_count": self.call_count,
            "delay_ms": self.delay_ms,
            "deterministic": self.deterministic,
            "fail_rate": self.fail_rate,
            "is_mock": True,
            "purpose": "Testing and development"
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()
    
    def reset_stats(self) -> None:
        """Reset call statistics (useful for testing)"""
        self.call_count = 0
        self.embedding_cache.clear()
    
    async def cleanup(self) -> None:
        """Clean up mock provider"""
        self.reset_stats()
        # Base class doesn't have cleanup, just reset state
        self.initialized = False