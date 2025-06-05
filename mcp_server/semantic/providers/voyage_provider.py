"""
Voyage AI Embedding Provider

Implements embedding generation using Voyage AI's models, which are specifically
optimized for code understanding and retrieval.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging

try:
    import voyageai
except ImportError:
    voyageai = None

from mcp_server.interfaces.embedding_interfaces import (
    EmbeddingConfig,
    EmbeddingResult,
    EmbeddingType
)
from .result import Result
from .base import BaseEmbeddingProvider
from .exceptions import (
    APIKeyError,
    EmbeddingGenerationError,
    ProviderInitializationError,
    RateLimitError
)
from .validators import validate_api_key

logger = logging.getLogger(__name__)


class VoyageProvider(BaseEmbeddingProvider):
    """Voyage AI embedding provider implementation"""
    
    # Supported models with their dimensions
    SUPPORTED_MODELS = {
        "voyage-code-3": 1024,
        "voyage-code-2": 1536,
        "voyage-3": 1024,
        "voyage-2": 1024,
        "voyage-large-2": 1536,
        "voyage-3-lite": 512,
        "voyage-finance-2": 1024,
        "voyage-law-2": 1024,
        "voyage-multilingual-2": 1024,
    }
    
    def __init__(self):
        super().__init__()
        self.client: Optional[voyageai.AsyncClient] = None
        self._sync_client: Optional[voyageai.Client] = None
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize Voyage AI client"""
        if voyageai is None:
            return Result.error(
                ProviderInitializationError(
                    "voyageai package not installed. Install with: pip install voyageai"
                )
            )
        
        # Get API key
        api_key = self.config.provider_config.get("api_key") or os.getenv("VOYAGE_API_KEY")
        
        # Validate API key
        is_valid, error_msg = validate_api_key(
            api_key,
            "Voyage AI",
            required_prefix="pa-",
            min_length=30
        )
        
        if not is_valid:
            return Result.error(APIKeyError(error_msg))
        
        try:
            # Initialize clients
            self.client = voyageai.AsyncClient(api_key=api_key)
            self._sync_client = voyageai.Client(api_key=api_key)
            
            logger.info("Initialized Voyage AI provider")
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(f"Failed to initialize Voyage AI client: {str(e)}")
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using Voyage AI"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("Voyage AI client not initialized")
            )
        
        # Map embedding type to Voyage AI input_type
        input_type_map = {
            EmbeddingType.CODE: "document",
            EmbeddingType.QUERY: "query",
            EmbeddingType.DOCUMENT: "document",
            EmbeddingType.COMMENT: "document"
        }
        
        voyage_input_type = input_type_map.get(embedding_type, "document")
        
        try:
            # Call Voyage AI API
            response = await self.client.embed(
                texts,
                model=self.config.model_name,
                input_type=voyage_input_type,
                output_dimension=self.config.dimension,
                output_dtype="float"
            )
            
            # Extract embeddings
            embeddings = response.embeddings
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=getattr(response, 'total_tokens', len(texts) * 100),  # Estimate if not provided
                dimension=self.config.dimension,
                processing_time_ms=0,  # Will be set by base class
                provider="voyage",
                metadata={
                    "input_type": voyage_input_type,
                    "output_dtype": "float"
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limiting
            if "rate limit" in error_str.lower():
                return Result.error(
                    RateLimitError("Voyage AI rate limit exceeded", retry_after=60)
                )
            
            # Other errors
            return Result.error(
                EmbeddingGenerationError(f"Voyage AI embedding generation failed: {error_str}")
            )
    
    async def validate_api_key(self) -> Result[bool]:
        """Validate Voyage AI API key by making a test request"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("Client not initialized")
            )
        
        try:
            # Make a minimal test request
            response = await self.client.embed(
                ["test"],
                model=self.config.model_name,
                input_type="document",
                output_dimension=self.config.dimension
            )
            
            return Result.success(True)
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return Result.success(False)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens for Voyage AI models"""
        # Voyage AI uses a similar tokenization to GPT models
        # Rough estimate: 1 token per 3.5 characters for code
        total_chars = sum(len(text) for text in texts)
        return int(total_chars / 3.5)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Voyage AI specific model information"""
        base_info = super().get_model_info()
        
        # Add Voyage-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "input_types": ["document", "query"],
            "max_batch_size": 128,
            "rate_limit": "10000 tokens/minute",
            "specialization": "code embeddings"
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, int]:
        """Get supported models and their dimensions"""
        return cls.SUPPORTED_MODELS.copy()