"""
Local Embedding Provider

Implements embedding generation using Sentence Transformers for local model inference.
Supports CPU and GPU inference without requiring external API calls.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Union
import logging
import torch

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from mcp_server.interfaces.embedding_interfaces import (
    EmbeddingConfig,
    EmbeddingResult,
    EmbeddingType
)
from .result import Result
from .base import BaseEmbeddingProvider
from .exceptions import (
    EmbeddingGenerationError,
    ProviderInitializationError,
    ModelNotSupportedError
)

logger = logging.getLogger(__name__)


class LocalProvider(BaseEmbeddingProvider):
    """Local embedding provider using Sentence Transformers"""
    
    # Popular models with their properties
    SUPPORTED_MODELS = {
        # General purpose
        "all-MiniLM-L6-v2": {
            "dimension": 384,
            "max_tokens": 256,
            "description": "Fast, general purpose model"
        },
        "all-mpnet-base-v2": {
            "dimension": 768,
            "max_tokens": 384,
            "description": "High quality general embeddings"
        },
        "all-distilroberta-v1": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Good balance of speed and quality"
        },
        
        # Specialized for search
        "msmarco-distilbert-base-v4": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Optimized for semantic search"
        },
        "multi-qa-mpnet-base-dot-v1": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Question-answering optimized"
        },
        
        # Instruction-based models
        "instructor-base": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Follows task instructions"
        },
        "instructor-large": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Larger instruction model"
        },
        
        # E5 models
        "e5-base-v2": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Efficient embeddings"
        },
        "e5-large-v2": {
            "dimension": 1024,
            "max_tokens": 512,
            "description": "High quality E5 embeddings"
        },
        
        # Code-specific
        "microsoft/codebert-base": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Optimized for code understanding"
        },
        "microsoft/unixcoder-base": {
            "dimension": 768,
            "max_tokens": 512,
            "description": "Multi-language code embeddings"
        }
    }
    
    def __init__(self):
        super().__init__()
        self.model: Optional[SentenceTransformer] = None
        self.device: Optional[str] = None
        self.cache_dir: Optional[str] = None
    
    async def _initialize_provider(self) -> Result[None]:
        """Initialize Sentence Transformers model"""
        if SentenceTransformer is None:
            return Result.error(
                ProviderInitializationError(
                    "sentence-transformers package not installed. "
                    "Install with: pip install sentence-transformers"
                )
            )
        
        # Get device configuration
        self.device = self.config.provider_config.get("device", "auto")
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Get cache directory
        self.cache_dir = self.config.provider_config.get(
            "cache_dir",
            os.path.expanduser("~/.cache/sentence-transformers")
        )
        
        try:
            # Load model
            logger.info(f"Loading model {self.config.model_name} on {self.device}")
            
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.device,
                cache_folder=self.cache_dir
            )
            
            # Verify model dimension matches expected
            test_embedding = self.model.encode(["test"], convert_to_tensor=False)
            actual_dim = len(test_embedding[0])
            
            expected_dim = self.SUPPORTED_MODELS.get(
                self.config.model_name, {}
            ).get("dimension", self.config.dimension)
            
            if actual_dim != expected_dim:
                logger.warning(
                    f"Model dimension mismatch: expected {expected_dim}, got {actual_dim}"
                )
                # Update config with actual dimension
                self.config.dimension = actual_dim
            
            logger.info(
                f"Initialized local provider with {self.config.model_name} "
                f"(dim={actual_dim}) on {self.device}"
            )
            return Result.success(None)
            
        except Exception as e:
            return Result.error(
                ProviderInitializationError(
                    f"Failed to load model '{self.config.model_name}': {str(e)}"
                )
            )
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Generate embeddings using local model"""
        if not self.model:
            return Result.error(
                ProviderInitializationError("Model not initialized")
            )
        
        try:
            # Run model inference in executor to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self._encode_texts,
                texts,
                embedding_type
            )
            
            # Handle dimension adjustment if needed
            if self.config.dimension < len(embeddings[0]):
                embeddings = [emb[:self.config.dimension] for emb in embeddings]
            
            # Estimate tokens (rough approximation)
            estimated_tokens = sum(len(text.split()) * 1.3 for text in texts)
            
            # Create result
            result = EmbeddingResult(
                embeddings=embeddings,
                model_used=self.config.model_name,
                token_count=int(estimated_tokens),
                dimension=len(embeddings[0]),
                processing_time_ms=0,  # Will be set by base class
                provider="local",
                metadata={
                    "device": self.device,
                    "batch_size": len(texts),
                    "embedding_type": embedding_type.value
                }
            )
            
            return Result.success(result)
            
        except Exception as e:
            return Result.error(
                EmbeddingGenerationError(
                    f"Local embedding generation failed: {str(e)}"
                )
            )
    
    def _encode_texts(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> List[List[float]]:
        """Encode texts using the model (sync method for executor)"""
        # Add instruction prefix for instructor models
        if "instructor" in self.config.model_name.lower():
            instruction_map = {
                EmbeddingType.CODE: "Represent the code for retrieval: ",
                EmbeddingType.QUERY: "Represent the question for retrieving code: ",
                EmbeddingType.DOCUMENT: "Represent the document for retrieval: ",
                EmbeddingType.COMMENT: "Represent the comment for retrieval: "
            }
            instruction = instruction_map.get(embedding_type, "")
            if instruction:
                texts = [instruction + text for text in texts]
        
        # Encode with normalization
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=self.config.normalize,
            show_progress_bar=False
        )
        
        # Convert to list of lists
        return embeddings.tolist()
    
    async def validate_api_key(self) -> Result[bool]:
        """No API key needed for local models"""
        return Result.success(True)
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate tokens for local models"""
        # Simple word-based estimation
        # Most models use WordPiece or similar tokenization
        total_words = sum(len(text.split()) for text in texts)
        return int(total_words * 1.3)  # Rough approximation
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get local provider specific information"""
        base_info = super().get_model_info()
        
        # Get model-specific info
        model_info = self.SUPPORTED_MODELS.get(self.config.model_name, {})
        
        # Add local-specific info
        base_info.update({
            "supported_models": list(self.SUPPORTED_MODELS.keys()),
            "device": self.device or "not initialized",
            "cache_dir": self.cache_dir,
            "requires_gpu": self.device == "cuda",
            "model_description": model_info.get("description", "Local embedding model"),
            "no_api_key_required": True
        })
        
        return base_info
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get supported models and their configurations"""
        return cls.SUPPORTED_MODELS.copy()
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.model:
            # Clear model from memory
            del self.model
            self.model = None
            
            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        # Reset initialized state
        self.initialized = False