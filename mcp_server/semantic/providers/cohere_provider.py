"""
Cohere Embedding Provider

Implements embedding generation using Cohere's embedding models.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging

try:
    import cohere
except ImportError:
    cohere = None

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
    RateLimitError,
    TokenLimitError
)
from .validators import validate_api_key

logger = logging.getLogger(__name__)


class CohereProvider(BaseEmbeddingProvider):
    """Cohere embedding provider implementation"""
    
    # Supported models with their configurations
    SUPPORTED_MODELS = {
        "embed-english-v3.0": {
            "dimension": 1024,
            "max_tokens": 512,
            "languages": ["en"]
        },
        "embed-multilingual-v3.0": {
            "dimension": 1024,
            "max_tokens": 512,
            "languages": ["multilingual"]
        },
        "embed-english-light-v3.0": {
            "dimension": 384,
            "max_tokens": 512,
            "languages": ["en"]
        },
        "embed-multilingual-light-v3.0": {
            "dimension": 384,
            "max_tokens": 512,
            "languages": ["multilingual"]
        },
        "embed-english-v2.0": {
            "dimension": 4096,
            "max_tokens": 512,
            "languages": ["en"]
        },
        "embed-multilingual-v2.0": {
            "dimension": 768,
            "max_tokens": 256,
            "languages": ["multilingual"]
        }
    }
    
    # Cohere input types
    INPUT_TYPES = {
        EmbeddingType.QUERY: "search_query",
        EmbeddingType.DOCUMENT: "search_document",
        EmbeddingType.CODE: "search_document",
        EmbeddingType.COMMENT: "search_document"
    }
    
    def __init__(self):
        super().__init__()
        self.client: Optional[cohere.AsyncClient] = None
        self._sync_client: Optional[cohere.Client] = None
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize Cohere client"""
        if cohere is None:
            return Result.error(
                ProviderInitializationError(
                    "cohere package not installed. Install with: pip install cohere"
                )
            )
        
        # Get API key
        api_key = self.config.provider_config.get("api_key") or os.getenv("COHERE_API_KEY")
        
        # Validate API key
        is_valid, error_msg = validate_api_key(
            api_key,
            "Cohere",
            min_length=30
        )
        
        if not is_valid:
            return Result.error(APIKeyError(error_msg))
        
        try:
            # Initialize clients
            self.client = cohere.AsyncClient(api_key)
            self._sync_client = cohere.Client(api_key)
            
            logger.info("Initialized Cohere provider")
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(f"Failed to initialize Cohere client: {str(e)}")
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using Cohere"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("Cohere client not initialized")
            )
        
        # Get input type for Cohere
        input_type = self.INPUT_TYPES.get(embedding_type, "search_document")
        
        try:
            # Truncate texts if needed
            model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
            max_tokens = model_info.get("max_tokens", 512)
            
            # Cohere has character limits, roughly 4 chars per token
            max_chars = max_tokens * 4
            truncated_texts = [
                text[:max_chars] if len(text) > max_chars else text
                for text in texts
            ]
            
            # Call Cohere API
            response = await self.client.embed(
                texts=truncated_texts,
                model=self.config.model_name,
                input_type=input_type,
                truncate="NONE"  # We handle truncation ourselves
            )
            
            # Extract embeddings
            embeddings = response.embeddings
            
            # Handle dimension adjustment if needed
            if self.config.dimension < len(embeddings[0]):
                embeddings = [emb[:self.config.dimension] for emb in embeddings]
            
            # Estimate tokens (Cohere doesn't provide token count)
            estimated_tokens = sum(len(text) // 4 for text in truncated_texts)
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=estimated_tokens,
                dimension=len(embeddings[0]),
                processing_time_ms=0,  # Will be set by base class
                provider="cohere",
                metadata={
                    "input_type": input_type,
                    "truncated": any(len(t) < len(o) for t, o in zip(truncated_texts, texts))
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limiting
            if "rate limit" in error_str.lower() or "429" in error_str:
                return Result.error(
                    RateLimitError("Cohere rate limit exceeded", retry_after=60)
                )
            
            # Check for token limit
            if "too many tokens" in error_str.lower():
                return Result.error(
                    TokenLimitError(
                        "Text exceeds Cohere's token limit",
                        token_count=estimated_tokens,
                        limit=max_tokens * len(texts)
                    )
                )
            
            # Other errors
            return Result.error(
                EmbeddingGenerationError(f"Cohere embedding generation failed: {error_str}")
            )
    
    async def validate_api_key(self) -> Result[bool]:
        """Validate Cohere API key by making a test request"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("Client not initialized")
            )
        
        try:
            # Make a minimal test request
            response = await self.client.embed(
                texts=["test"],
                model=self.config.model_name,
                input_type="search_document"
            )
            
            return Result.success(True)
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return Result.success(False)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens for Cohere models"""
        # Cohere uses roughly 4 characters per token
        total_chars = sum(len(text) for text in texts)
        return int(total_chars / 4)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Cohere specific model information"""
        base_info = super().get_model_info()
        
        # Get model-specific info
        model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
        
        # Add Cohere-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "input_types": list(set(self.INPUT_TYPES.values())),
            "max_batch_size": 96,
            "rate_limit": "10000 calls/minute",
            "languages": model_info.get("languages", ["en"]),
            "truncate_options": ["NONE", "START", "END"]
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()