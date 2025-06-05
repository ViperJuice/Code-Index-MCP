"""
Base implementation for embedding providers

Provides common functionality that all providers can inherit.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from abc import ABC
import logging

from mcp_server.interfaces.embedding_interfaces import (
    IEmbeddingProvider,
    EmbeddingConfig,
    EmbeddingResult,
    EmbeddingType,
    EmbeddingBatch
)
from .result import Result
from .exceptions import EmbeddingGenerationError, ProviderInitializationError

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(IEmbeddingProvider, ABC):
    """Base implementation with common functionality for all providers"""
    
    def __init__(self):
        self.config: Optional[EmbeddingConfig] = None
        self.initialized: bool = False
        self._retry_count: int = 0
        
    async def initialize(self, config: EmbeddingConfig) -> Result[None]:
        """Base initialization with validation"""
        try:
            # Log initialization attempt
            logger.info(f"Initializing {self.__class__.__name__} with model '{config.model_name}'")
            logger.debug(f"Config: dimension={config.dimension}, batch_size={config.batch_size}, "
                        f"normalize={config.normalize}, provider_config={config.provider_config}")
            
            # Validate config
            try:
                config.__post_init__()  # Triggers validation
            except ValueError as e:
                error_msg = f"Invalid configuration: {str(e)}"
                logger.error(f"{self.__class__.__name__}: {error_msg}")
                return Result.error(ProviderInitializationError(error_msg))
            
            self.config = config
            
            # Call provider-specific initialization
            result = await self._initialize_provider()
            if result.is_error():
                logger.error(f"{self.__class__.__name__} initialization failed: {result.error_value}")
                return result
                
            self.initialized = True
            logger.info(f"✅ Successfully initialized {self.__class__.__name__} with model {config.model_name}")
            return Result.success(None)
            
        except Exception as e:
            error = ProviderInitializationError(f"Failed to initialize provider: {str(e)}")
            logger.error(f"{self.__class__.__name__}: {error}")
            logger.debug(f"Stack trace:", exc_info=True)
            return Result.error(error)
    
    async def _initialize_provider(self) -> Result[None]:
        """Provider-specific initialization - override in subclasses"""
        return Result.success(None)
    
    async def embed_single(
        self, 
        text: str, 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> Result[List[float]]:
        """Embed single text by delegating to batch method"""
        if not self.initialized:
            return Result.error(
                ProviderInitializationError("Provider not initialized")
            )
            
        # Delegate to batch method
        result = await self.embed_batch([text], embedding_type)
        
        if result.is_error:
            return Result.error(result.error)
            
        # Extract single embedding
        embedding_result = result.value
        if not embedding_result.embeddings:
            return Result.error(
                EmbeddingGenerationError("No embeddings generated")
            )
            
        return Result.success(embedding_result.embeddings[0])
    
    async def embed_batch(
        self, 
        texts: List[str], 
        embedding_type: EmbeddingType = EmbeddingType.CODE
    ) -> Result[EmbeddingResult]:
        """Embed batch with retry logic and timing"""
        if not self.initialized:
            return Result.error(
                ProviderInitializationError("Provider not initialized")
            )
            
        start_time = time.time()
        
        # Split into smaller batches if needed
        batches = self._split_into_batches(texts)
        all_embeddings = []
        total_tokens = 0
        
        for batch in batches:
            # Retry logic
            for attempt in range(self.config.max_retries):
                try:
                    result = await self._embed_batch_impl(batch, embedding_type)
                    
                    if result.is_error():
                        if attempt < self.config.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return result
                    
                    # Success
                    embedding_result = result.value
                    all_embeddings.extend(embedding_result.embeddings)
                    total_tokens += embedding_result.token_count
                    break
                    
                except Exception as e:
                    if attempt < self.config.max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    
                    error = EmbeddingGenerationError(f"Failed after {attempt + 1} attempts: {str(e)}")
                    logger.error(error)
                    return Result.error(error)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Create result
        result = EmbeddingResult(
            embeddings=all_embeddings,
            model_used=self.config.model_name,
            token_count=total_tokens,
            dimension=self.config.dimension,
            processing_time_ms=processing_time_ms,
            provider=self.__class__.__name__.replace("Provider", "").lower(),
            metadata={
                "batch_count": len(batches),
                "embedding_type": embedding_type.value
            }
        )
        
        return Result.success(result)
    
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        """Provider-specific batch embedding - override in subclasses"""
        raise NotImplementedError("Subclasses must implement _embed_batch_impl")
    
    def _split_into_batches(self, texts: List[str]) -> List[List[str]]:
        """Split texts into batches based on configured batch size"""
        batch_size = self.config.batch_size
        return [
            texts[i:i + batch_size] 
            for i in range(0, len(texts), batch_size)
        ]
    
    async def estimate_tokens(self, texts: List[str]) -> int:
        """Estimate token count - override for provider-specific tokenization"""
        # Default estimation: ~4 characters per token
        total_chars = sum(len(text) for text in texts)
        return int(total_chars / 4)
    
    async def close(self) -> None:
        """Clean up resources"""
        self.initialized = False
        self.config = None
        logger.info(f"Closed {self.__class__.__name__}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        if not self.config:
            return {
                "error": "Provider not initialized",
                "provider": self.__class__.__name__
            }
            
        return {
            "provider": self.__class__.__name__.replace("Provider", "").lower(),
            "model": self.config.model_name,
            "dimension": self.config.dimension,
            "max_tokens": self.config.max_tokens,
            "batch_size": self.config.batch_size,
            "normalize": self.config.normalize
        }