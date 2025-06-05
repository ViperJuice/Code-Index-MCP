"""
OpenAI Embedding Provider

Implements embedding generation using OpenAI's text-embedding models.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    AsyncOpenAI = None
    OpenAI = None

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


class OpenAIProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider implementation"""
    
    # Supported models with their dimensions and limits
    SUPPORTED_MODELS = {
        "text-embedding-3-small": {
            "dimension": 1536,
            "max_tokens": 8191,
            "price_per_1k": 0.00002
        },
        "text-embedding-3-large": {
            "dimension": 3072, 
            "max_tokens": 8191,
            "price_per_1k": 0.00013
        },
        "text-embedding-ada-002": {
            "dimension": 1536,
            "max_tokens": 8191,
            "price_per_1k": 0.00010
        }
    }
    
    def __init__(self):
        super().__init__()
        self.client: Optional[AsyncOpenAI] = None
        self._sync_client: Optional[OpenAI] = None
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize OpenAI client"""
        if AsyncOpenAI is None:
            return Result.error(
                ProviderInitializationError(
                    "openai package not installed. Install with: pip install openai"
                )
            )
        
        # Get API key
        api_key = self.config.provider_config.get("api_key") or os.getenv("OPENAI_API_KEY")
        
        # Validate API key
        is_valid, error_msg = validate_api_key(
            api_key,
            "OpenAI",
            required_prefix="sk-",
            min_length=40
        )
        
        if not is_valid:
            return Result.error(APIKeyError(error_msg))
        
        try:
            # Initialize clients
            self.client = AsyncOpenAI(api_key=api_key)
            self._sync_client = OpenAI(api_key=api_key)
            
            logger.info("Initialized OpenAI provider")
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(f"Failed to initialize OpenAI client: {str(e)}")
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using OpenAI"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("OpenAI client not initialized")
            )
        
        try:
            # Check token limits
            estimated_tokens = await self.estimate_tokens(texts)
            model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
            max_tokens = model_info.get("max_tokens", 8191)
            
            if estimated_tokens > max_tokens * len(texts):
                return Result.error(
                    TokenLimitError(
                        f"Text exceeds token limit",
                        token_count=estimated_tokens,
                        limit=max_tokens * len(texts)
                    )
                )
            
            # Call OpenAI API
            response = await self.client.embeddings.create(
                model=self.config.model_name,
                input=texts,
                encoding_format="float"
            )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            # Handle dimension reduction if requested
            if self.config.dimension < len(embeddings[0]):
                embeddings = [emb[:self.config.dimension] for emb in embeddings]
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=response.model,
                token_count=response.usage.total_tokens,
                dimension=len(embeddings[0]),
                processing_time_ms=0,  # Will be set by base class
                provider="openai",
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "encoding_format": "float"
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            error_str = str(e)
            
            # Check for specific errors
            if "rate_limit_exceeded" in error_str:
                # Extract retry after if available
                retry_after = 60  # Default
                if "retry after" in error_str:
                    try:
                        retry_after = int(error_str.split("retry after")[1].split()[0])
                    except:
                        pass
                
                return Result.error(
                    RateLimitError("OpenAI rate limit exceeded", retry_after=retry_after)
                )
            
            if "maximum context length" in error_str:
                return Result.error(
                    TokenLimitError(
                        "Text exceeds model's maximum context length",
                        token_count=estimated_tokens,
                        limit=max_tokens
                    )
                )
            
            # Other errors
            return Result.error(
                EmbeddingGenerationError(f"OpenAI embedding generation failed: {error_str}")
            )
    
    async def validate_api_key(self) -> Result[bool]:
        """Validate OpenAI API key by making a test request"""
        if not self.client:
            return Result.error(
                ProviderInitializationError("Client not initialized")
            )
        
        try:
            # Make a minimal test request
            response = await self.client.embeddings.create(
                model=self.config.model_name,
                input=["test"],
                encoding_format="float"
            )
            
            return Result.success(True)
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return Result.success(False)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens using tiktoken for accurate OpenAI tokenization"""
        try:
            import tiktoken
            
            # Get encoding for the model
            if "ada" in self.config.model_name:
                encoding = tiktoken.get_encoding("cl100k_base")
            else:
                # For newer models
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            
            total_tokens = 0
            for text in texts:
                total_tokens += len(encoding.encode(text))
            
            return total_tokens
            
        except ImportError:
            # Fallback to character-based estimation
            # OpenAI models average ~4 characters per token
            total_chars = sum(len(text) for text in texts)
            return int(total_chars / 4)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI specific model information"""
        base_info = super().get_model_info()
        
        # Get model-specific info
        model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
        
        # Add OpenAI-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "encoding_formats": ["float", "base64"],
            "max_batch_size": 2048,
            "rate_limit": "10000 RPM, 10M TPM",
            "price_per_1k_tokens": model_info.get("price_per_1k", "unknown"),
            "dimension_flexibility": self.config.model_name.startswith("text-embedding-3")
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()