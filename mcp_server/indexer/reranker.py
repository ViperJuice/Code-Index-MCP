"""
Reranking Module for Search Result Optimization

This module provides implementations for reranking search results to improve relevance.
It supports both Cohere's reranking API and local cross-encoder models as fallback.
"""

import asyncio
import logging
import os

# Define interfaces inline for now
from abc import ABC, abstractmethod
from dataclasses import dataclass as dc
from typing import Any, Dict, List, Optional


# Define SearchResult inline
@dc
class SearchResult:
    """Search result information"""

    file_path: str
    line: int
    column: int
    snippet: str
    match_type: str  # exact, fuzzy, semantic
    score: float
    context: Optional[str] = None


# Define RerankItem to wrap original SearchResult
@dc
class RerankItem:
    """A single reranked item that preserves the complete original SearchResult"""

    original_result: SearchResult  # Complete original SearchResult
    rerank_score: float  # The reranking score
    original_rank: int  # Original position in results
    new_rank: int  # New position after reranking
    explanation: Optional[str] = None  # Optional explanation for the ranking


# Define RerankResult with proper structure
@dc
class RerankResult:
    """Result from reranking operation"""

    results: List[RerankItem]  # List of reranked items
    metadata: Dict[str, Any]  # Metadata about the reranking operation


# Define IReranker interface
class IReranker(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, results: List[SearchResult], top_k: int = 10
    ) -> RerankResult:
        pass


# Define IRerankerFactory interface
class IRerankerFactory(ABC):
    @abstractmethod
    def create_reranker(self, config: Any) -> Optional[IReranker]:
        pass


class MCPError(Exception):
    """Base exception for MCP errors."""


# Simple Result class for this module
class Result:
    def __init__(self, success: bool, data=None, error=None):
        self.is_success = success
        self.data = data
        self.error = error

    @classmethod
    def ok(cls, data=None):
        return cls(True, data)

    @classmethod
    def error(cls, error):
        return cls(False, None, error)


logger = logging.getLogger(__name__)


class BaseReranker(IReranker, ABC):
    """Base class for all reranker implementations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._cache: Dict[str, Any] = {}  # Simple in-memory cache
        self.cache_ttl = config.get("cache_ttl", 3600)  # 1 hour default
        self.initialized = False

    async def _get_cache_key(self, query: str, results: List[SearchResult]) -> str:
        """Generate cache key for reranking results"""
        # Create a deterministic key based on query and result IDs
        result_ids = [f"{r.file_path}:{r.line}" for r in results[:10]]  # Use top 10 for key
        return f"rerank:{self.__class__.__name__}:{hash(query)}:{hash(tuple(result_ids))}"

    async def _get_cached_results(
        self, query: str, results: List[SearchResult]
    ) -> Optional[List[RerankItem]]:
        """Get cached reranking results if available"""
        cache_key = await self._get_cache_key(query, results)

        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            # Check if cache is still valid (simple time-based check)
            import time

            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                logger.debug(f"Cache hit for reranking query: {query}")
                return cached_data["results"]
            else:
                # Cache expired
                del self._cache[cache_key]

        return None

    async def _cache_results(
        self, query: str, results: List[SearchResult], reranked: List[RerankItem]
    ):
        """Cache reranking results"""
        import time

        cache_key = await self._get_cache_key(query, results)
        self._cache[cache_key] = {"results": reranked, "timestamp": time.time()}

        # Simple cache size limit
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            for key in sorted_keys[:100]:  # Remove oldest 100
                del self._cache[key]


class CohereReranker(BaseReranker):
    """Reranker using Cohere's reranking API"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("cohere_api_key") or os.getenv("COHERE_API_KEY")
        self.model = config.get("model", "rerank-english-v2.0")
        self.client = None

    async def initialize(self, config: Dict[str, Any]) -> Result:
        """Initialize Cohere client"""
        try:
            if not self.api_key:
                return Result.error("Cohere API key not configured")

            # Lazy import to avoid dependency if not used
            try:
                import cohere

                self.client = cohere.Client(self.api_key)
                self.initialized = True
                logger.info(f"Initialized Cohere reranker with model: {self.model}")
                return Result.ok(None)
            except ImportError:
                return Result.error(
                    "Cohere library not installed. Install with: pip install cohere"
                )
        except Exception as e:
            logger.error(f"Failed to initialize Cohere reranker: {e}")
            return Result.error(f"Initialization failed: {str(e)}")

    async def shutdown(self) -> Result:
        """Shutdown Cohere client"""
        self.client = None
        self.initialized = False
        return Result.ok(None)

    async def rerank(
        self, query: str, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Result:
        """Rerank results using Cohere API"""
        if not self.initialized:
            return Result.error("Cohere reranker not initialized")

        # Check cache first
        cached = await self._get_cached_results(query, results)
        if cached:
            rerank_result = RerankResult(
                results=cached[:top_k] if top_k else cached,
                metadata={
                    "reranker": "cohere",
                    "model": self.model,
                    "from_cache": True,
                    "total_results": len(results),
                    "returned_results": len(cached[:top_k]) if top_k else len(cached),
                },
            )
            return Result.ok(rerank_result)

        try:
            # Prepare documents for reranking
            documents = []
            for result in results:
                # Combine relevant information for reranking
                doc_text = f"{result.snippet}"
                if result.context:
                    doc_text = f"{doc_text} {result.context}"
                documents.append(doc_text)

            # Call Cohere rerank API
            response = await asyncio.to_thread(
                self.client.rerank,
                model=self.model,
                query=query,
                documents=documents,
                top_n=top_k or len(results),
            )

            # Build reranked results
            reranked_items = []
            for idx, result in enumerate(response.results):
                original_idx = result.index
                original_result = results[original_idx]

                rerank_item = RerankItem(
                    original_result=original_result,
                    rerank_score=result.relevance_score,
                    original_rank=original_idx,
                    new_rank=idx,
                )
                reranked_items.append(rerank_item)

            # Cache results
            await self._cache_results(query, results, reranked_items)

            # Create RerankResult with metadata
            rerank_result = RerankResult(
                results=reranked_items,
                metadata={
                    "reranker": "cohere",
                    "model": self.model,
                    "from_cache": False,
                    "total_results": len(results),
                    "returned_results": len(reranked_items),
                },
            )

            return Result.ok(rerank_result)

        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}")
            return Result.error(f"Reranking failed: {str(e)}")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get Cohere reranker capabilities"""
        return {
            "name": "Cohere Reranker",
            "model": self.model,
            "supports_multilingual": self.model.startswith("rerank-multilingual"),
            "max_documents": 1000,
            "requires_api_key": True,
            "initialized": self.initialized,
        }


class LocalCrossEncoderReranker(BaseReranker):
    """Local reranker using cross-encoder models"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.device = config.get("device", "cpu")
        self.model = None
        self.tokenizer = None

    async def initialize(self, config: Dict[str, Any]) -> Result:
        """Initialize cross-encoder model"""
        try:
            # Lazy import to avoid dependency if not used
            try:
                from sentence_transformers import CrossEncoder

                logger.info(f"Loading cross-encoder model: {self.model_name}")
                self.model = CrossEncoder(self.model_name, device=self.device)
                self.initialized = True
                logger.info(f"Initialized local cross-encoder reranker on {self.device}")
                return Result.ok(None)

            except ImportError:
                return Result.error(
                    "Sentence-transformers library not installed. "
                    "Install with: pip install sentence-transformers"
                )
        except Exception as e:
            logger.error(f"Failed to initialize cross-encoder: {e}")
            return Result.error(f"Initialization failed: {str(e)}")

    async def shutdown(self) -> Result:
        """Shutdown cross-encoder model"""
        self.model = None
        self.initialized = False
        return Result.ok(None)

    async def rerank(
        self, query: str, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Result:
        """Rerank results using cross-encoder model"""
        if not self.initialized:
            return Result.error("Cross-encoder reranker not initialized")

        # Check cache first
        cached = await self._get_cached_results(query, results)
        if cached:
            rerank_result = RerankResult(
                results=cached[:top_k] if top_k else cached,
                metadata={
                    "reranker": "cross-encoder",
                    "model": self.model_name,
                    "device": self.device,
                    "from_cache": True,
                    "total_results": len(results),
                    "returned_results": len(cached[:top_k]) if top_k else len(cached),
                },
            )
            return Result.ok(rerank_result)

        try:
            # Prepare query-document pairs
            pairs = []
            for result in results:
                # Combine relevant information for reranking
                doc_text = f"{result.snippet}"
                if result.context:
                    doc_text = f"{doc_text} {result.context}"
                pairs.append([query, doc_text])

            # Get scores from cross-encoder
            scores = await asyncio.to_thread(self.model.predict, pairs)

            # Create indexed scores for sorting
            indexed_scores = [(score, idx) for idx, score in enumerate(scores)]
            indexed_scores.sort(reverse=True, key=lambda x: x[0])

            # Build reranked results
            reranked_items = []
            for new_rank, (score, original_idx) in enumerate(indexed_scores):
                if top_k and new_rank >= top_k:
                    break

                rerank_item = RerankItem(
                    original_result=results[original_idx],
                    rerank_score=float(score),
                    original_rank=original_idx,
                    new_rank=new_rank,
                )
                reranked_items.append(rerank_item)

            # Cache results
            await self._cache_results(query, results, reranked_items)

            # Create RerankResult with metadata
            rerank_result = RerankResult(
                results=reranked_items,
                metadata={
                    "reranker": "cross-encoder",
                    "model": self.model_name,
                    "device": self.device,
                    "from_cache": False,
                    "total_results": len(results),
                    "returned_results": len(reranked_items),
                },
            )

            return Result.ok(rerank_result)

        except Exception as e:
            logger.error(f"Cross-encoder reranking failed: {e}")
            return Result.error(f"Reranking failed: {str(e)}")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get cross-encoder reranker capabilities"""
        return {
            "name": "Local Cross-Encoder Reranker",
            "model": self.model_name,
            "device": self.device,
            "supports_multilingual": "multilingual" in self.model_name.lower(),
            "max_documents": 10000,  # Limited by memory
            "requires_api_key": False,
            "initialized": self.initialized,
        }


class TFIDFReranker(BaseReranker):
    """Simple TF-IDF based reranker as lightweight fallback"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vectorizer = None

    async def initialize(self, config: Dict[str, Any]) -> Result:
        """Initialize TF-IDF vectorizer"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            self.vectorizer = TfidfVectorizer(
                max_features=config.get("max_features", 5000),
                ngram_range=(1, 2),
                stop_words="english",
            )
            self.cosine_similarity = cosine_similarity
            self.initialized = True
            logger.info("Initialized TF-IDF reranker")
            return Result.ok(None)

        except ImportError:
            return Result.error(
                "Scikit-learn not installed. Install with: pip install scikit-learn"
            )
        except Exception as e:
            logger.error(f"Failed to initialize TF-IDF reranker: {e}")
            return Result.error(f"Initialization failed: {str(e)}")

    async def shutdown(self) -> Result:
        """Shutdown TF-IDF reranker"""
        self.vectorizer = None
        self.initialized = False
        return Result.ok(None)

    async def rerank(
        self, query: str, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Result:
        """Rerank results using TF-IDF similarity"""
        if not self.initialized:
            return Result.error("TF-IDF reranker not initialized")

        # Check cache first
        cached = await self._get_cached_results(query, results)
        if cached:
            rerank_result = RerankResult(
                results=cached[:top_k] if top_k else cached,
                metadata={
                    "reranker": "tfidf",
                    "max_features": self.config.get("max_features", 5000),
                    "from_cache": True,
                    "total_results": len(results),
                    "returned_results": len(cached[:top_k]) if top_k else len(cached),
                },
            )
            return Result.ok(rerank_result)

        try:
            # Prepare documents
            documents = []
            for result in results:
                doc_text = f"{result.snippet}"
                if result.context:
                    doc_text = f"{doc_text} {result.context}"
                documents.append(doc_text)

            # Add query to documents for vectorization
            all_texts = [query] + documents

            # Vectorize texts
            tfidf_matrix = await asyncio.to_thread(self.vectorizer.fit_transform, all_texts)

            # Calculate similarities
            query_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]
            similarities = self.cosine_similarity(query_vector, doc_vectors)[0]

            # Create indexed scores for sorting
            indexed_scores = [(score, idx) for idx, score in enumerate(similarities)]
            indexed_scores.sort(reverse=True, key=lambda x: x[0])

            # Build reranked results
            reranked_items = []
            for new_rank, (score, original_idx) in enumerate(indexed_scores):
                if top_k and new_rank >= top_k:
                    break

                rerank_item = RerankItem(
                    original_result=results[original_idx],
                    rerank_score=float(score),
                    original_rank=original_idx,
                    new_rank=new_rank,
                )
                reranked_items.append(rerank_item)

            # Cache results
            await self._cache_results(query, results, reranked_items)

            # Create RerankResult with metadata
            rerank_result = RerankResult(
                results=reranked_items,
                metadata={
                    "reranker": "tfidf",
                    "max_features": self.config.get("max_features", 5000),
                    "from_cache": False,
                    "total_results": len(results),
                    "returned_results": len(reranked_items),
                },
            )

            return Result.ok(rerank_result)

        except Exception as e:
            logger.error(f"TF-IDF reranking failed: {e}")
            return Result.error(f"Reranking failed: {str(e)}")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get TF-IDF reranker capabilities"""
        return {
            "name": "TF-IDF Reranker",
            "algorithm": "TF-IDF with cosine similarity",
            "supports_multilingual": False,
            "max_documents": 100000,
            "requires_api_key": False,
            "initialized": self.initialized,
        }


class HybridReranker(BaseReranker):
    """Hybrid reranker that combines multiple reranking strategies"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.primary_reranker: Optional[IReranker] = None
        self.fallback_reranker: Optional[IReranker] = None
        self.weight_primary = config.get("weight_primary", 0.7)
        self.weight_fallback = config.get("weight_fallback", 0.3)

    def set_rerankers(self, primary: IReranker, fallback: Optional[IReranker] = None):
        """Set primary and fallback rerankers"""
        self.primary_reranker = primary
        self.fallback_reranker = fallback

    async def initialize(self, config: Dict[str, Any]) -> Result:
        """Initialize hybrid reranker"""
        if not self.primary_reranker:
            return Result.error("Primary reranker not set")

        # Initialize primary reranker
        primary_result = await self.primary_reranker.initialize(config)
        if not primary_result.is_success:
            return primary_result

        # Initialize fallback if available
        if self.fallback_reranker:
            fallback_result = await self.fallback_reranker.initialize(config)
            if not fallback_result.is_success:
                logger.warning(f"Fallback reranker initialization failed: {fallback_result.error}")

        self.initialized = True
        return Result.ok(None)

    async def shutdown(self) -> Result:
        """Shutdown hybrid reranker"""
        if self.primary_reranker:
            await self.primary_reranker.shutdown()
        if self.fallback_reranker:
            await self.fallback_reranker.shutdown()
        self.initialized = False
        return Result.ok(None)

    async def rerank(
        self, query: str, results: List[SearchResult], top_k: Optional[int] = None
    ) -> Result:
        """Rerank using hybrid approach"""
        if not self.initialized:
            return Result.error("Hybrid reranker not initialized")

        # Try primary reranker first
        primary_result = await self.primary_reranker.rerank(query, results, top_k)

        if primary_result.is_success:
            # Update metadata to indicate hybrid reranker was used
            if isinstance(primary_result.data, RerankResult):
                primary_result.data.metadata["hybrid"] = True
                primary_result.data.metadata["primary_succeeded"] = True
            return primary_result

        # If primary fails and we have fallback, use it
        if self.fallback_reranker:
            logger.warning(f"Primary reranker failed: {primary_result.error}, using fallback")
            fallback_result = await self.fallback_reranker.rerank(query, results, top_k)
            if fallback_result.is_success and isinstance(fallback_result.data, RerankResult):
                fallback_result.data.metadata["hybrid"] = True
                fallback_result.data.metadata["primary_succeeded"] = False
                fallback_result.data.metadata["fallback_reason"] = str(primary_result.error)
            return fallback_result

        return primary_result

    def get_capabilities(self) -> Dict[str, Any]:
        """Get hybrid reranker capabilities"""
        capabilities = {
            "name": "Hybrid Reranker",
            "primary": (
                self.primary_reranker.get_capabilities() if self.primary_reranker else None
            ),
            "fallback": (
                self.fallback_reranker.get_capabilities() if self.fallback_reranker else None
            ),
            "weight_primary": self.weight_primary,
            "weight_fallback": self.weight_fallback,
            "initialized": self.initialized,
        }
        return capabilities


class RerankerFactory(IRerankerFactory):
    """Factory for creating reranker instances"""

    def __init__(self):
        self.reranker_types = {
            "cohere": CohereReranker,
            "cross-encoder": LocalCrossEncoderReranker,
            "tfidf": TFIDFReranker,
            "hybrid": HybridReranker,
        }

    def create_reranker(self, reranker_type: str, config: Dict[str, Any]) -> IReranker:
        """Create a reranker instance"""
        if reranker_type not in self.reranker_types:
            raise ValueError(f"Unknown reranker type: {reranker_type}")

        reranker_class = self.reranker_types[reranker_type]
        reranker = reranker_class(config)

        # Special handling for hybrid reranker
        if reranker_type == "hybrid":
            primary_type = config.get("primary_type", "cohere")
            fallback_type = config.get("fallback_type", "tfidf")

            primary = self.create_reranker(primary_type, config)
            fallback = self.create_reranker(fallback_type, config) if fallback_type else None

            reranker.set_rerankers(primary, fallback)

        return reranker

    def get_available_rerankers(self) -> List[str]:
        """Get list of available reranker types"""
        return list(self.reranker_types.keys())

    def register_reranker(self, name: str, reranker_class: type):
        """Register a custom reranker type"""
        if not issubclass(reranker_class, IReranker):
            raise ValueError(f"{reranker_class} must implement IReranker interface")
        self.reranker_types[name] = reranker_class


# Default factory instance
default_reranker_factory = RerankerFactory()
