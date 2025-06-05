"""
HuggingFace API Embedding Provider

Implements embedding generation using HuggingFace's Inference API.
Supports any model available on HuggingFace Hub with feature-extraction pipeline.
Default model is NV-Embed-v2 from NVIDIA.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import logging
import aiohttp
import json
import time

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
    ModelNotSupportedError
)
from .validators import validate_api_key

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseEmbeddingProvider):
    """HuggingFace API embedding provider implementation"""
    
    # Popular embedding models on HuggingFace
    SUPPORTED_MODELS = {
        # NVIDIA models
        "nvidia/NV-Embed-v2": {
            "dimension": 4096,
            "max_tokens": 32768,
            "description": "NVIDIA's state-of-the-art embedding model",
            "license": "cc-by-nc-4.0"
        },
        "nvidia/NV-Embed-v1": {
            "dimension": 4096,
            "max_tokens": 32768,
            "description": "Previous version of NVIDIA embeddings",
            "license": "cc-by-nc-4.0"
        },
        
        # Sentence Transformers models
        "sentence-transformers/all-MiniLM-L6-v2": {
            "dimension": 384,
            "max_tokens": 256,
            "description": "Fast, lightweight general-purpose embeddings"
        },
        "sentence-transformers/all-mpnet-base-v2": {
            "dimension": 768,
            "max_tokens": 384,
            "description": "High-quality general-purpose embeddings"
        },
        "sentence-transformers/all-distilroberta-v1": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Good balance of speed and quality"
        },
        
        # Multilingual models
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": {
            "dimension": 768,
            "max_tokens": 128,
            "description": "Multilingual embeddings for 50+ languages"
        },
        "intfloat/multilingual-e5-large": {
            "dimension": 1024,
            "max_tokens": 512,
            "description": "State-of-the-art multilingual embeddings"
        },
        
        # Specialized models
        "BAAI/bge-large-en-v1.5": {
            "dimension": 1024,
            "max_tokens": 512,
            "description": "Beijing Academy's English embeddings"
        },
        "BAAI/bge-m3": {
            "dimension": 1024,
            "max_tokens": 8192,
            "description": "Multi-lingual, multi-functional, multi-granular"
        },
        "thenlper/gte-large": {
            "dimension": 1024,
            "max_tokens": 512,
            "description": "General Text Embeddings"
        },
        "jinaai/jina-embeddings-v2-base-en": {
            "dimension": 768,
            "max_tokens": 8192,
            "description": "Jina AI's long-context embeddings"
        },
        
        # Code-specific models
        "microsoft/unixcoder-base": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Code understanding across languages"
        },
        "microsoft/codebert-base": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Pre-trained model for programming languages"
        }
    }
    
    # HuggingFace API endpoint
    API_BASE_URL = "https://api-inference.huggingface.co"
    
    def __init__(self):
        super().__init__()
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_token: Optional[str] = None
        self.headers: Dict[str, str] = {}
    
    async def get_model_info_from_hub(self, model_name: str) -> Dict[str, Any]:
        """Query HuggingFace Hub API to get model information including dimensions."""
        try:
            url = f"https://huggingface.co/api/models/{model_name}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        config = data.get("config", {})
                        
                        # Try to find dimension info from various fields
                        dimension = None
                        for key in ["hidden_size", "dim", "d_model", "n_embd", "embed_dim"]:
                            if key in config:
                                dimension = config[key]
                                break
                        
                        return {
                            "pipeline_tag": data.get("pipeline_tag"),
                            "dimension": dimension,
                            "library_name": data.get("library_name"),
                            "config": config
                        }
                    else:
                        logger.warning(f"Could not fetch model info for {model_name}: {response.status}")
                        return {}
        except Exception as e:
            logger.warning(f"Error fetching model info: {e}")
            return {}
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize HuggingFace API client"""
        # Get API token
        self.api_token = (
            self.config.provider_config.get("api_token") or 
            self.config.provider_config.get("api_key") or 
            os.getenv("HUGGINGFACE_API_TOKEN") or
            os.getenv("HF_TOKEN") or
            os.getenv("HUGGIINGFACE_API_TOKEN")  # Also check for typo version
        )
        
        # Validate API token
        is_valid, error_msg = validate_api_key(
            self.api_token,
            "HuggingFace",
            required_prefix="hf_",
            min_length=30
        )
        
        if not is_valid:
            return Result.error(APIKeyError(error_msg))
        
        try:
            # Set up headers
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession(headers=self.headers)
            
            # Try to get model info if dimension is 0 (auto-detect)
            if self.config.dimension == 0:
                logger.info(f"Auto-detecting dimension for {self.config.model_name}...")
                model_info = await self.get_model_info_from_hub(self.config.model_name)
                if model_info.get("dimension"):
                    self.config.dimension = model_info["dimension"]
                    logger.info(f"Detected dimension: {self.config.dimension}")
                else:
                    logger.warning(
                        f"Could not auto-detect dimension for {self.config.model_name}. "
                        f"Please specify dimension manually."
                    )
            
            # Check if model supports embeddings
            model_info = await self.get_model_info_from_hub(self.config.model_name)
            pipeline_tag = model_info.get("pipeline_tag")
            if pipeline_tag and pipeline_tag not in ["feature-extraction", "sentence-similarity"]:
                logger.warning(
                    f"Model {self.config.model_name} has pipeline_tag '{pipeline_tag}' "
                    f"which may not support embeddings. Expected 'feature-extraction' or 'sentence-similarity'."
                )
            
            # Log initialization
            logger.info(
                f"Initialized HuggingFace provider with model {self.config.model_name} "
                f"(dimension: {self.config.dimension}). "
                f"Note: First request may take ~20s for model loading."
            )
            
            # Warn about non-commercial license for NV-Embed models
            if "NV-Embed" in self.config.model_name:
                logger.warning(
                    "NV-Embed models have a non-commercial license (CC-BY-NC-4.0). "
                    "Ensure your use case complies with the license terms."
                )
            
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(f"Failed to initialize HuggingFace client: {str(e)}")
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using HuggingFace API"""
        if not self.session:
            return Result.error(
                ProviderInitializationError("HuggingFace client not initialized")
            )
        
        try:
            # Build API URL
            # HuggingFace uses models/ prefix in the URL
            url = f"{self.API_BASE_URL}/models/{self.config.model_name}"
            
            # Check token limits
            model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
            max_tokens = model_info.get("max_tokens", 512)
            
            # Prepare request payload
            payload = {
                "inputs": texts,
                "options": {
                    "wait_for_model": True,  # Wait if model needs to be loaded
                    "use_cache": True
                }
            }
            
            # Track timing
            start_time = time.time()
            
            # Make request with retries for model loading
            max_retries = 3
            retry_delay = 20  # seconds
            
            for attempt in range(max_retries):
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        break
                    elif response.status == 503:  # Model loading
                        if attempt < max_retries - 1:
                            wait_time = response.headers.get("Retry-After", retry_delay)
                            logger.info(f"Model loading, waiting {wait_time}s...")
                            await asyncio.sleep(float(wait_time))
                            continue
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get("Retry-After", 3600))
                        return Result.error(
                            RateLimitError(
                                "HuggingFace API rate limit exceeded",
                                retry_after=retry_after
                            )
                        )
                    else:
                        error_text = await response.text()
                        return Result.error(
                            EmbeddingGenerationError(
                                f"HuggingFace API error ({response.status}): {error_text}"
                            )
                        )
            else:
                return Result.error(
                    EmbeddingGenerationError("Failed to load model after retries")
                )
            
            # Process embeddings
            # HuggingFace returns nested list structure
            embeddings = []
            for item in data:
                if isinstance(item, list) and len(item) > 0:
                    # Some models return [CLS] token embedding as first element
                    # We'll use mean pooling for better representation
                    if isinstance(item[0], list):
                        # Token-level embeddings, apply mean pooling
                        import numpy as np
                        pooled = np.mean(item, axis=0).tolist()
                        embeddings.append(pooled)
                    else:
                        # Already pooled
                        embeddings.append(item)
                else:
                    # Fallback to zeros
                    embeddings.append([0.0] * self.config.dimension)
            
            # Handle dimension adjustment if needed
            actual_dim = len(embeddings[0]) if embeddings else self.config.dimension
            if self.config.dimension != actual_dim:
                logger.warning(
                    f"Dimension mismatch: expected {self.config.dimension}, "
                    f"got {actual_dim}. Adjusting..."
                )
                if self.config.dimension < actual_dim:
                    embeddings = [emb[:self.config.dimension] for emb in embeddings]
                else:
                    # Pad with zeros
                    embeddings = [
                        emb + [0.0] * (self.config.dimension - actual_dim) 
                        for emb in embeddings
                    ]
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Estimate tokens
            estimated_tokens = sum(len(text.split()) for text in texts)
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=estimated_tokens,
                dimension=self.config.dimension,
                processing_time_ms=processing_time_ms,
                provider="huggingface",
                metadata={
                    "actual_dimension": actual_dim,
                    "model_loaded": processing_time_ms > 1000,  # Likely had to load
                    "embedding_type": embedding_type.value,
                    "pooling_method": "mean" if actual_dim != self.config.dimension else "model_default"
                }
            )
            
            return Result.success(result)
            
        except aiohttp.ClientError as e:
            return Result.error(
                EmbeddingGenerationError(f"HuggingFace network error: {str(e)}")
            )
        except Exception as e:
            return Result.error(
                EmbeddingGenerationError(f"HuggingFace embedding generation failed: {str(e)}")
            )
    
    async def validate_api_key(self) -> Result[bool]:
        """Validate HuggingFace API token by making a test request"""
        if not self.session:
            return Result.error(
                ProviderInitializationError("Client not initialized")
            )
        
        try:
            # Test with a simple model
            test_model = "sentence-transformers/all-MiniLM-L6-v2"
            url = f"{self.API_BASE_URL}/pipeline/feature-extraction/{test_model}"
            
            payload = {
                "inputs": ["test"],
                "options": {"wait_for_model": False}
            }
            
            async with self.session.post(url, json=payload) as response:
                return Result.success(response.status in [200, 503])  # 503 = model loading
            
        except Exception as e:
            logger.error(f"API token validation failed: {e}")
            return Result.success(False)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens for HuggingFace models"""
        # Most HuggingFace models use WordPiece or similar tokenization
        # Rough estimate: 1 token per 3.5 characters
        total_chars = sum(len(text) for text in texts)
        return int(total_chars / 3.5)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get HuggingFace specific model information"""
        base_info = super().get_model_info()
        
        # Get model-specific info
        model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
        
        # Add HuggingFace-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "default_model": "nvidia/NV-Embed-v2",
            "api_endpoint": self.API_BASE_URL,
            "supports_custom_models": True,
            "rate_limit": "Free tier: 30k requests/month",
            "model_description": model_info.get("description", "Custom HuggingFace model"),
            "license": model_info.get("license", "Check model card"),
            "note": "Any model with feature-extraction pipeline can be used"
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()
    
    async def close(self) -> None:
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
        super().close()