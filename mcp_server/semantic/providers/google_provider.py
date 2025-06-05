"""
Google Cloud Embedding Provider

Implements embedding generation using Google's Vertex AI text embedding models.
Supports the latest text-embedding-004 model and previous versions.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging
import json

try:
    import google.generativeai as genai
except ImportError:
    genai = None

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


class GoogleProvider(BaseEmbeddingProvider):
    """Google Cloud embedding provider implementation"""
    
    # Supported models with their configurations
    SUPPORTED_MODELS = {
        "text-embedding-004": {
            "dimension": 768,
            "max_tokens": 2048,
            "task_types": [
                "RETRIEVAL_QUERY",
                "RETRIEVAL_DOCUMENT",
                "SEMANTIC_SIMILARITY",
                "CLASSIFICATION",
                "CLUSTERING"
            ],
            "description": "Latest Google embedding model"
        },
        "embedding-001": {
            "dimension": 768,
            "max_tokens": 2048,
            "task_types": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
            "description": "Previous generation embedding model"
        },
        "text-embedding-preview-0409": {
            "dimension": 768,
            "max_tokens": 2048,
            "task_types": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
            "description": "Preview embedding model"
        },
        "textembedding-gecko@003": {
            "dimension": 768,
            "max_tokens": 3072,
            "task_types": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
            "description": "Gecko embedding model v3"
        },
        "textembedding-gecko@002": {
            "dimension": 768,
            "max_tokens": 3072,
            "task_types": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
            "description": "Gecko embedding model v2"
        },
        "textembedding-gecko@001": {
            "dimension": 768,
            "max_tokens": 3072,
            "task_types": ["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"],
            "description": "Gecko embedding model v1"
        }
    }
    
    # Map embedding types to Google task types
    TASK_TYPE_MAP = {
        EmbeddingType.QUERY: "RETRIEVAL_QUERY",
        EmbeddingType.DOCUMENT: "RETRIEVAL_DOCUMENT",
        EmbeddingType.CODE: "RETRIEVAL_DOCUMENT",
        EmbeddingType.COMMENT: "RETRIEVAL_DOCUMENT"
    }
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.model = None
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize Google Generative AI client"""
        if genai is None:
            return Result.error(
                ProviderInitializationError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai"
                )
            )
        
        # Get API key
        api_key = self.config.provider_config.get("api_key") or os.getenv("GOOGLE_API_KEY")
        
        # Validate API key
        is_valid, error_msg = validate_api_key(
            api_key,
            "Google",
            min_length=30
        )
        
        if not is_valid:
            return Result.error(APIKeyError(error_msg))
        
        try:
            # Configure the client
            genai.configure(api_key=api_key)
            
            # Initialize the model for embeddings
            # For newer models, use the generative model approach
            if self.config.model_name in ["text-embedding-004", "embedding-001"]:
                self.model = genai.GenerativeModel(f"models/{self.config.model_name}")
            else:
                # For gecko models, we might need different initialization
                # but for now, we'll use the same approach
                self.model = genai.GenerativeModel(f"models/{self.config.model_name}")
            
            logger.info(f"Initialized Google provider with model {self.config.model_name}")
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(f"Failed to initialize Google client: {str(e)}")
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using Google's API"""
        if not self.model:
            return Result.error(
                ProviderInitializationError("Google client not initialized")
            )
        
        try:
            # Get task type
            task_type = self.TASK_TYPE_MAP.get(embedding_type, "RETRIEVAL_DOCUMENT")
            
            # Check token limits
            model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
            max_tokens = model_info.get("max_tokens", 2048)
            
            # Truncate texts if needed (rough estimation)
            truncated_texts = []
            for text in texts:
                if len(text) > max_tokens * 4:  # Rough char to token ratio
                    truncated_texts.append(text[:max_tokens * 4])
                else:
                    truncated_texts.append(text)
            
            # Generate embeddings
            embeddings = []
            
            # Process texts one by one or in batch depending on the API
            # Google's API typically processes one at a time
            for text in truncated_texts:
                try:
                    # Use the embed_content method
                    result = genai.embed_content(
                        model=f"models/{self.config.model_name}",
                        content=text,
                        task_type=task_type
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.warning(f"Failed to embed text: {str(e)[:100]}")
                    # Use a zero vector as fallback
                    embeddings.append([0.0] * self.config.dimension)
            
            # Handle dimension adjustment if needed
            if self.config.dimension < len(embeddings[0]):
                embeddings = [emb[:self.config.dimension] for emb in embeddings]
            
            # Estimate tokens
            estimated_tokens = sum(len(text) // 4 for text in truncated_texts)
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=estimated_tokens,
                dimension=len(embeddings[0]) if embeddings else self.config.dimension,
                processing_time_ms=0,  # Will be set by base class
                provider="google",
                metadata={
                    "task_type": task_type,
                    "truncated": any(len(t) < len(o) for t, o in zip(truncated_texts, texts)),
                    "batch_size": len(texts)
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            error_str = str(e)
            
            # Check for rate limiting
            if "quota" in error_str.lower() or "rate" in error_str.lower():
                return Result.error(
                    RateLimitError("Google API rate limit exceeded", retry_after=60)
                )
            
            # Check for token limit
            if "token" in error_str.lower() or "length" in error_str.lower():
                return Result.error(
                    TokenLimitError(
                        "Text exceeds Google's token limit",
                        token_count=estimated_tokens if 'estimated_tokens' in locals() else 0,
                        limit=max_tokens * len(texts)
                    )
                )
            
            # Other errors
            return Result.error(
                EmbeddingGenerationError(f"Google embedding generation failed: {error_str}")
            )
    
    async def validate_api_key(self) -> Result[bool]:
        """Validate Google API key by making a test request"""
        if not self.model:
            return Result.error(
                ProviderInitializationError("Client not initialized")
            )
        
        try:
            # Make a minimal test request
            result = genai.embed_content(
                model=f"models/{self.config.model_name}",
                content="test",
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            return Result.success(True)
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return Result.success(False)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens for Google models"""
        # Google uses roughly 4 characters per token
        total_chars = sum(len(text) for text in texts)
        return int(total_chars / 4)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Google specific model information"""
        base_info = super().get_model_info()
        
        # Get model-specific info
        model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
        
        # Add Google-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "task_types": model_info.get("task_types", []),
            "max_batch_size": 100,  # Google typically supports batching
            "rate_limit": "60 RPM, 1M TPM",  # Typical limits
            "dimension_flexibility": False,  # Fixed dimensions
            "free_tier_available": True
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()