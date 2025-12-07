"""
Hybrid Search implementation combining BM25 and semantic search.

This module implements reciprocal rank fusion (RRF) to combine results from
multiple search methods, providing better overall search quality.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import only what we need to avoid circular dependencies
from ..config.settings import RerankingSettings
from ..storage.sqlite_store import SQLiteStore
from ..utils.semantic_indexer import SemanticIndexer
from .bm25_indexer import BM25Indexer
from .query_optimizer import QueryType
from .reranker import IReranker, RerankerFactory

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Individual search result from any search method."""

    doc_id: str
    filepath: str
    score: float
    snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # 'bm25', 'semantic', 'fuzzy', etc.


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search."""

    # Weight configuration
    bm25_weight: float = 0.5
    semantic_weight: float = 0.3
    fuzzy_weight: float = 0.2

    # RRF parameters
    rrf_k: int = 60  # Reciprocal Rank Fusion constant

    # Search parameters
    enable_bm25: bool = True
    enable_semantic: bool = True
    enable_fuzzy: bool = True

    # Result limits
    individual_limit: int = 50  # Results per search method
    final_limit: int = 20  # Final results after fusion

    # Optimization
    parallel_execution: bool = True
    cache_results: bool = True

    # Minimum scores
    min_bm25_score: float = -10.0
    min_semantic_score: float = 0.5
    min_fuzzy_score: float = 0.3


class HybridSearch:
    """
    Hybrid search combining multiple search methods with reciprocal rank fusion.

    This class orchestrates multiple search backends (BM25, semantic, fuzzy) and
    combines their results using configurable fusion strategies.
    """

    def __init__(
        self,
        storage: SQLiteStore,
        bm25_indexer: Optional[BM25Indexer] = None,
        semantic_indexer: Optional[SemanticIndexer] = None,
        fuzzy_indexer: Optional[Any] = None,
        config: Optional[HybridSearchConfig] = None,
        reranking_settings: Optional[RerankingSettings] = None,
    ):
        """
        Initialize hybrid search.

        Args:
            storage: SQLite storage backend
            bm25_indexer: BM25 full-text search indexer
            semantic_indexer: Semantic/vector search indexer
            fuzzy_indexer: Fuzzy search indexer
            config: Hybrid search configuration
            reranking_settings: Settings for result reranking
        """
        self.storage = storage
        self.bm25_indexer = bm25_indexer
        self.semantic_indexer = semantic_indexer
        self.fuzzy_indexer = fuzzy_indexer
        self.config = config or HybridSearchConfig()
        self.reranking_settings = reranking_settings

        # Initialize reranker if enabled
        self.reranker: Optional[IReranker] = None
        if reranking_settings and reranking_settings.enabled:
            self._initialize_reranker()

        # Result cache
        self._result_cache: Dict[str, List[SearchResult]] = {}

        # Statistics
        self._search_stats = defaultdict(int)

        # Track semantic search availability
        self._semantic_temporarily_disabled = False

        # Check semantic indexer availability on init
        if self.semantic_indexer and self.config.enable_semantic:
            if not self.semantic_indexer.is_available:
                logger.warning(
                    "Semantic search is enabled in config but Qdrant is not available. "
                    "Disabling semantic search. HybridSearch will use BM25 and fuzzy search only."
                )
                self.config.enable_semantic = False

    def _initialize_reranker(self):
        """Initialize the reranker based on settings."""
        try:
            factory = RerankerFactory()
            config = {
                "cohere_api_key": self.reranking_settings.cohere_api_key,
                "model": self.reranking_settings.cohere_model,
                "device": self.reranking_settings.cross_encoder_device,
                "primary_type": self.reranking_settings.hybrid_primary_type,
                "fallback_type": self.reranking_settings.hybrid_fallback_type,
                "weight_primary": self.reranking_settings.hybrid_primary_weight,
                "weight_fallback": self.reranking_settings.hybrid_fallback_weight,
                "cache_ttl": self.reranking_settings.cache_ttl,
            }

            self.reranker = factory.create_reranker(self.reranking_settings.reranker_type, config)

            # Initialize reranker asynchronously will be done on first use
            logger.info(f"Initialized {self.reranking_settings.reranker_type} reranker")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            self.reranker = None

    async def search(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining multiple search methods.

        Args:
            query: Search query
            query_type: Optional query type hint
            filters: Optional filters (language, file path, etc.)
            limit: Maximum number of results

        Returns:
            List of combined search results
        """
        limit = limit or self.config.final_limit

        # Check cache if enabled
        cache_key = self._get_cache_key(query, filters)
        if self.config.cache_results and cache_key in self._result_cache:
            self._search_stats["cache_hits"] += 1
            cached_results = self._result_cache[cache_key]
            return self._format_results(cached_results[:limit])

        # Collect results from different search methods
        all_results = []

        if self.config.parallel_execution:
            # Execute searches in parallel
            all_results = await self._parallel_search(query, query_type, filters)
        else:
            # Execute searches sequentially
            all_results = await self._sequential_search(query, query_type, filters)

        # Combine results using reciprocal rank fusion
        combined_results = self._reciprocal_rank_fusion(all_results)

        # Apply reranking if enabled
        if self.reranker and self.reranking_settings and self.reranking_settings.enabled:
            combined_results = await self._rerank_results(query, combined_results)

        # Apply post-processing
        final_results = self._post_process_results(combined_results, limit)

        # Cache results if enabled
        if self.config.cache_results:
            self._result_cache[cache_key] = final_results
            self._cleanup_cache()

        # Update statistics
        self._search_stats["total_searches"] += 1

        return self._format_results(final_results)

    async def _parallel_search(
        self,
        query: str,
        query_type: Optional[QueryType],
        filters: Optional[Dict[str, Any]],
    ) -> List[List[SearchResult]]:
        """Execute searches in parallel."""
        tasks = []

        if self.config.enable_bm25 and self.bm25_indexer:
            tasks.append(self._search_bm25(query, filters))

        if self.config.enable_semantic and self.semantic_indexer:
            tasks.append(self._search_semantic(query, filters))

        if self.config.enable_fuzzy and self.fuzzy_indexer:
            tasks.append(self._search_fuzzy(query, filters))

        # Execute all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and empty results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Search error in method {i}: {result}")
            elif result:
                valid_results.append(result)

        return valid_results

    async def _sequential_search(
        self,
        query: str,
        query_type: Optional[QueryType],
        filters: Optional[Dict[str, Any]],
    ) -> List[List[SearchResult]]:
        """Execute searches sequentially."""
        all_results = []

        if self.config.enable_bm25 and self.bm25_indexer:
            try:
                bm25_results = await self._search_bm25(query, filters)
                if bm25_results:
                    all_results.append(bm25_results)
            except Exception as e:
                logger.error(f"BM25 search error: {e}")

        if self.config.enable_semantic and self.semantic_indexer:
            try:
                semantic_results = await self._search_semantic(query, filters)
                if semantic_results:
                    all_results.append(semantic_results)
            except Exception as e:
                logger.error(f"Semantic search error: {e}")

        if self.config.enable_fuzzy and self.fuzzy_indexer:
            try:
                fuzzy_results = await self._search_fuzzy(query, filters)
                if fuzzy_results:
                    all_results.append(fuzzy_results)
            except Exception as e:
                logger.error(f"Fuzzy search error: {e}")

        return all_results

    async def _search_bm25(
        self, query: str, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Perform BM25 search."""
        # Run BM25 search in thread pool since it's synchronous
        loop = asyncio.get_event_loop()

        def run_search():
            kwargs = filters or {}
            results = self.bm25_indexer.search(query, limit=self.config.individual_limit, **kwargs)

            search_results = []
            for r in results:
                if r["score"] >= self.config.min_bm25_score:
                    search_results.append(
                        SearchResult(
                            doc_id=r.get("filepath", ""),
                            filepath=r.get("filepath", ""),
                            score=r["score"],
                            snippet=r.get("snippet", ""),
                            metadata=r,
                            source="bm25",
                        )
                    )
            return search_results

        results = await loop.run_in_executor(None, run_search)
        self._search_stats["bm25_searches"] += 1
        return results

    async def _search_semantic(
        self, query: str, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Perform semantic search with availability checks."""
        # Check if semantic search is temporarily disabled
        if self._semantic_temporarily_disabled:
            logger.debug("Semantic search is temporarily disabled due to previous errors")
            return []

        # Check if semantic indexer is available before attempting search
        if not self.semantic_indexer.is_available:
            logger.warning(
                "Semantic indexer is not available. Skipping semantic search. "
                f"Connection mode: {self.semantic_indexer.connection_mode}"
            )
            self._search_stats["semantic_unavailable"] += 1
            return []

        # Validate connection is still active
        if not self.semantic_indexer.validate_connection():
            logger.warning(
                "Semantic indexer connection validation failed. "
                "Temporarily disabling semantic search."
            )
            self._semantic_temporarily_disabled = True
            self._search_stats["semantic_connection_failures"] += 1
            return []

        # Run semantic search
        loop = asyncio.get_event_loop()

        def run_search():
            try:
                # Semantic search with filters
                kwargs = {
                    "k": self.config.individual_limit,
                    "threshold": self.config.min_semantic_score,
                }
                if filters:
                    kwargs.update(filters)

                results = self.semantic_indexer.search(query, **kwargs)

                search_results = []
                for r in results:
                    search_results.append(
                        SearchResult(
                            doc_id=r.get("filepath", ""),
                            filepath=r.get("filepath", ""),
                            score=r.get("score", 0.0),
                            snippet=r.get("content", "")[:200],
                            metadata=r,
                            source="semantic",
                        )
                    )
                return search_results
            except Exception as e:
                logger.error(
                    f"Semantic search failed with error: {e}. "
                    "Temporarily disabling semantic search."
                )
                self._semantic_temporarily_disabled = True
                self._search_stats["semantic_search_errors"] += 1
                return []

        results = await loop.run_in_executor(None, run_search)
        if results:  # Only count successful searches
            self._search_stats["semantic_searches"] += 1
        return results

    async def _search_fuzzy(
        self, query: str, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Perform fuzzy search."""
        loop = asyncio.get_event_loop()

        def run_search():
            # Fuzzy search
            results = self.fuzzy_indexer.search_fuzzy(
                query,
                max_results=self.config.individual_limit,
                threshold=self.config.min_fuzzy_score,
            )

            search_results = []
            for r in results:
                if r["score"] >= self.config.min_fuzzy_score:
                    search_results.append(
                        SearchResult(
                            doc_id=r.get("file_path", ""),
                            filepath=r.get("file_path", ""),
                            score=r["score"],
                            snippet=r.get("context", ""),
                            metadata=r,
                            source="fuzzy",
                        )
                    )
            return search_results

        results = await loop.run_in_executor(None, run_search)
        self._search_stats["fuzzy_searches"] += 1
        return results

    def _reciprocal_rank_fusion(self, result_lists: List[List[SearchResult]]) -> List[SearchResult]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).

        RRF score = Σ(1 / (k + rank_i)) for each result list
        where k is a constant (typically 60) and rank_i is the rank in list i
        """
        # Track scores for each document
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_info: Dict[str, SearchResult] = {}

        # Calculate RRF scores
        for result_list in result_lists:
            for rank, result in enumerate(result_list):
                doc_id = result.doc_id

                # RRF score for this ranking
                rrf_score = 1.0 / (self.config.rrf_k + rank + 1)

                # Apply source-specific weights
                if result.source == "bm25":
                    rrf_score *= self.config.bm25_weight
                elif result.source == "semantic":
                    rrf_score *= self.config.semantic_weight
                elif result.source == "fuzzy":
                    rrf_score *= self.config.fuzzy_weight

                doc_scores[doc_id] += rrf_score

                # Keep the result with the best individual score
                if doc_id not in doc_info or result.score > doc_info[doc_id].score:
                    doc_info[doc_id] = result

        # Create combined results
        combined = []
        for doc_id, combined_score in doc_scores.items():
            result = doc_info[doc_id]
            # Update score to combined RRF score
            result.score = combined_score
            combined.append(result)

        # Sort by combined score
        combined.sort(key=lambda x: x.score, reverse=True)

        return combined

    async def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank search results using the configured reranker."""
        if not self.reranker or not results:
            return results

        try:
            # Initialize reranker if not already done
            if not hasattr(self, "_reranker_initialized"):
                init_result = await self.reranker.initialize({})
                if not init_result.is_success:
                    logger.error(f"Failed to initialize reranker: {init_result.error}")
                    return results
                self._reranker_initialized = True

            # Import SearchResult from reranker module to avoid circular dependency
            from .reranker import SearchResult as RerankSearchResult

            # Convert our SearchResult to reranker's SearchResult format
            reranker_results = []
            for r in results:
                # Create a reranker-compatible search result
                reranker_result = RerankSearchResult(
                    file_path=r.filepath,
                    line=r.metadata.get("line", 1),
                    column=r.metadata.get("column", 0),
                    snippet=r.snippet,
                    match_type=r.source,  # Use source as match type
                    score=r.score,
                    context=r.metadata.get("context", ""),
                )
                reranker_results.append(reranker_result)

            # Perform reranking
            top_k = (
                self.reranking_settings.top_k if self.reranking_settings else len(reranker_results)
            )
            rerank_result = await self.reranker.rerank(query, reranker_results, top_k=top_k)

            if not rerank_result.is_success:
                logger.warning(f"Reranking failed: {rerank_result.error}")
                return results

            # Handle the new RerankResult structure
            # rerank_result.data is a RerankResult object with 'results' list and 'metadata' dict
            rerank_data = rerank_result.data
            if not rerank_data:
                logger.warning("Reranking returned no data")
                return results

            if not hasattr(rerank_data, "results"):
                logger.error("Unexpected rerank result structure")
                return results

            if not rerank_data.results:
                logger.warning("Reranking returned empty results")
                return results

            # Convert back to our SearchResult format, preserving all original metadata
            reranked_results = []
            for rerank_item in rerank_data.results:
                # Validate original_rank is within bounds
                if rerank_item.original_rank < 0 or rerank_item.original_rank >= len(results):
                    logger.warning(
                        f"Invalid original_rank {rerank_item.original_rank} for {len(results)} results"
                    )
                    continue

                # Get the original result using the original_rank
                original = results[rerank_item.original_rank]

                # Create a new SearchResult with updated score but preserved metadata
                updated_result = SearchResult(
                    doc_id=original.doc_id,
                    filepath=original.filepath,
                    score=rerank_item.rerank_score,  # Use the new rerank score
                    snippet=original.snippet,
                    metadata=original.metadata.copy(),  # Preserve all original metadata
                    source=original.source,
                )

                # Add reranking metadata
                updated_result.metadata["original_score"] = original.score
                updated_result.metadata["rerank_score"] = rerank_item.rerank_score
                updated_result.metadata["original_rank"] = rerank_item.original_rank
                updated_result.metadata["new_rank"] = rerank_item.new_rank
                if rerank_item.explanation:
                    updated_result.metadata["rerank_explanation"] = rerank_item.explanation

                reranked_results.append(updated_result)

            # Sort by new rank to ensure proper ordering
            reranked_results.sort(key=lambda x: x.metadata.get("new_rank", float("inf")))

            # Log reranking metadata if available
            if hasattr(rerank_data, "metadata") and rerank_data.metadata:
                logger.debug(
                    f"Reranked {len(reranked_results)} results using {rerank_data.metadata.get('reranker', 'unknown')} reranker"
                )
            else:
                logger.debug(f"Reranked {len(reranked_results)} results")

            return reranked_results

        except Exception as e:
            logger.error(f"Error during reranking: {e}", exc_info=True)
            return results

    def _post_process_results(self, results: List[SearchResult], limit: int) -> List[SearchResult]:
        """Apply post-processing to results."""
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in results:
            if result.filepath not in seen:
                seen.add(result.filepath)
                unique_results.append(result)

        # Apply limit
        unique_results = unique_results[:limit]

        # Enhance snippets if needed
        for result in unique_results:
            if not result.snippet and result.filepath:
                # Try to generate a snippet
                result.snippet = self._generate_snippet(result.filepath, result.metadata)

        return unique_results

    def _generate_snippet(self, filepath: str, metadata: Dict[str, Any]) -> str:
        """Generate a snippet for a result."""
        # This is a placeholder - in practice, you'd read the file
        # and extract relevant context
        return f"File: {filepath}"

    def _format_results(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Format results for output, including all metadata."""
        formatted = []
        for i, result in enumerate(results):
            # Ensure metadata exists
            metadata = result.metadata if result.metadata else {}

            # Build base result with all fields
            formatted_result = {
                "rank": i + 1,
                "filepath": result.filepath,
                "score": result.score,
                "snippet": result.snippet,
                "source": result.source,
                # Include all metadata fields
                "line": metadata.get("line", 1),
                "column": metadata.get("column", 0),
                "context": metadata.get("context", ""),
                "match_type": metadata.get("match_type", result.source),
                # Include language and symbol information if present
                "language": metadata.get("language", ""),
                "symbol": metadata.get("symbol", ""),
                "symbol_type": metadata.get("symbol_type", ""),
                # Include reranking information if present
                "original_score": metadata.get("original_score", result.score),
                "rerank_score": metadata.get("rerank_score"),
                "original_rank": metadata.get("original_rank"),
                "new_rank": metadata.get("new_rank"),
                "rerank_explanation": metadata.get("rerank_explanation"),
                # Include any additional metadata
                "metadata": metadata,
            }

            # Remove None values and empty strings for cleaner output
            formatted_result = {
                k: v
                for k, v in formatted_result.items()
                if v is not None and (not isinstance(v, str) or v != "")
            }

            formatted.append(formatted_result)
        return formatted

    def _get_cache_key(self, query: str, filters: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for a query."""
        import hashlib

        key_parts = [query]
        if filters:
            key_parts.extend(f"{k}:{v}" for k, v in sorted(filters.items()))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _cleanup_cache(self):
        """Clean up cache if it gets too large."""
        max_cache_size = 1000
        if len(self._result_cache) > max_cache_size:
            # Remove oldest entries (simple FIFO)
            entries_to_remove = len(self._result_cache) - max_cache_size // 2
            for key in list(self._result_cache.keys())[:entries_to_remove]:
                del self._result_cache[key]

    # Configuration methods

    def set_weights(self, bm25: float = None, semantic: float = None, fuzzy: float = None):
        """
        Update search method weights.

        Args:
            bm25: Weight for BM25 search (0-1)
            semantic: Weight for semantic search (0-1)
            fuzzy: Weight for fuzzy search (0-1)
        """
        if bm25 is not None:
            self.config.bm25_weight = max(0, min(1, bm25))
        if semantic is not None:
            self.config.semantic_weight = max(0, min(1, semantic))
        if fuzzy is not None:
            self.config.fuzzy_weight = max(0, min(1, fuzzy))

        # Normalize weights
        total = self.config.bm25_weight + self.config.semantic_weight + self.config.fuzzy_weight
        if total > 0:
            self.config.bm25_weight /= total
            self.config.semantic_weight /= total
            self.config.fuzzy_weight /= total

    def enable_methods(self, bm25: bool = None, semantic: bool = None, fuzzy: bool = None):
        """
        Enable or disable search methods.

        Args:
            bm25: Enable/disable BM25 search
            semantic: Enable/disable semantic search
            fuzzy: Enable/disable fuzzy search
        """
        if bm25 is not None:
            self.config.enable_bm25 = bm25
        if semantic is not None:
            self.config.enable_semantic = semantic
        if fuzzy is not None:
            self.config.enable_fuzzy = fuzzy

    def retry_semantic_search(self) -> bool:
        """
        Attempt to re-enable semantic search after it was temporarily disabled.

        This method checks if the semantic indexer is now available and
        re-enables semantic search if possible.

        Returns:
            True if semantic search was successfully re-enabled, False otherwise
        """
        if not self.semantic_indexer:
            logger.warning("Cannot retry semantic search: no semantic indexer configured")
            return False

        if not self._semantic_temporarily_disabled and self.config.enable_semantic:
            logger.info("Semantic search is already enabled")
            return True

        # Check if semantic indexer is now available
        if self.semantic_indexer.is_available and self.semantic_indexer.validate_connection():
            self._semantic_temporarily_disabled = False
            self.config.enable_semantic = True
            logger.info(
                f"Semantic search re-enabled successfully. "
                f"Connection mode: {self.semantic_indexer.connection_mode}"
            )
            self._search_stats["semantic_reactivations"] += 1
            return True
        else:
            logger.warning(
                "Cannot re-enable semantic search: Qdrant is still unavailable. "
                f"Connection mode: {self.semantic_indexer.connection_mode}"
            )
            return False

    def get_search_capabilities(self) -> Dict[str, Any]:
        """
        Get current search capabilities and availability status.

        Returns:
            Dictionary with detailed information about available search methods
        """
        capabilities = {
            "bm25": {
                "available": self.bm25_indexer is not None,
                "enabled": self.config.enable_bm25,
                "status": (
                    "operational" if (self.bm25_indexer and self.config.enable_bm25) else "disabled"
                ),
            },
            "semantic": {
                "available": False,
                "enabled": self.config.enable_semantic,
                "status": "not_configured",
            },
            "fuzzy": {
                "available": self.fuzzy_indexer is not None,
                "enabled": self.config.enable_fuzzy,
                "status": (
                    "operational"
                    if (self.fuzzy_indexer and self.config.enable_fuzzy)
                    else "disabled"
                ),
            },
        }

        # Add detailed semantic search status
        if self.semantic_indexer:
            is_available = self.semantic_indexer.is_available
            connection_mode = self.semantic_indexer.connection_mode

            capabilities["semantic"]["available"] = is_available
            capabilities["semantic"]["connection_mode"] = connection_mode
            capabilities["semantic"]["temporarily_disabled"] = self._semantic_temporarily_disabled

            if self._semantic_temporarily_disabled:
                capabilities["semantic"]["status"] = "temporarily_disabled"
            elif not is_available:
                capabilities["semantic"]["status"] = "unavailable"
            elif self.config.enable_semantic:
                capabilities["semantic"]["status"] = "operational"
            else:
                capabilities["semantic"]["status"] = "disabled_by_config"

        return capabilities

    def get_statistics(self) -> Dict[str, Any]:
        """Get search statistics including semantic availability."""
        stats = dict(self._search_stats)

        # Add cache statistics
        stats["cache_size"] = len(self._result_cache)
        cache_hit_rate = 0
        if stats.get("total_searches", 0) > 0:
            cache_hit_rate = stats.get("cache_hits", 0) / stats["total_searches"]
        stats["cache_hit_rate"] = cache_hit_rate

        # Add configuration info
        stats["config"] = {
            "weights": {
                "bm25": self.config.bm25_weight,
                "semantic": self.config.semantic_weight,
                "fuzzy": self.config.fuzzy_weight,
            },
            "enabled_methods": {
                "bm25": self.config.enable_bm25,
                "semantic": self.config.enable_semantic,
                "fuzzy": self.config.enable_fuzzy,
            },
            "rrf_k": self.config.rrf_k,
        }

        # Add semantic search availability status
        stats["semantic_status"] = {
            "configured": self.semantic_indexer is not None,
            "temporarily_disabled": self._semantic_temporarily_disabled,
        }

        if self.semantic_indexer:
            stats["semantic_status"].update(
                {
                    "available": self.semantic_indexer.is_available,
                    "connection_mode": self.semantic_indexer.connection_mode,
                }
            )

        return stats

    def clear_cache(self):
        """Clear the result cache."""
        self._result_cache.clear()
        logger.info("Hybrid search cache cleared")


class HybridSearchOptimizer:
    """
    Optimizer for hybrid search parameters based on user feedback and performance.
    """

    def __init__(self, hybrid_search: HybridSearch):
        """
        Initialize the optimizer.

        Args:
            hybrid_search: HybridSearch instance to optimize
        """
        self.hybrid_search = hybrid_search
        self.feedback_history: List[Dict[str, Any]] = []
        self.performance_history: List[Dict[str, Any]] = []

    def record_feedback(self, query: str, selected_result: int, results: List[Dict[str, Any]]):
        """
        Record user feedback on search results.

        Args:
            query: The search query
            selected_result: Index of the result the user selected
            results: The search results shown to the user
        """
        feedback = {
            "query": query,
            "selected_rank": selected_result + 1,
            "selected_source": (
                results[selected_result]["source"] if selected_result < len(results) else None
            ),
            "num_results": len(results),
            "timestamp": datetime.now(),
        }
        self.feedback_history.append(feedback)

        # Optimize weights after collecting enough feedback
        if len(self.feedback_history) % 10 == 0:
            self.optimize_weights()

    def record_performance(self, query: str, search_time_ms: float, num_results: int):
        """
        Record search performance metrics.

        Args:
            query: The search query
            search_time_ms: Time taken for search in milliseconds
            num_results: Number of results returned
        """
        self.performance_history.append(
            {
                "query": query,
                "search_time_ms": search_time_ms,
                "num_results": num_results,
                "timestamp": datetime.now(),
            }
        )

    def optimize_weights(self):
        """Optimize search weights based on feedback history."""
        if len(self.feedback_history) < 10:
            return

        # Count selections by source
        source_selections = defaultdict(int)
        source_ranks = defaultdict(list)

        for feedback in self.feedback_history[-100:]:  # Last 100 feedbacks
            source = feedback.get("selected_source")
            if source:
                source_selections[source] += 1
                source_ranks[source].append(feedback["selected_rank"])

        # Calculate average rank for each source
        avg_ranks = {}
        for source, ranks in source_ranks.items():
            avg_ranks[source] = sum(ranks) / len(ranks) if ranks else float("inf")

        # Update weights based on selection frequency and average rank
        total_selections = sum(source_selections.values())
        if total_selections > 0:
            # Base weights on selection frequency
            bm25_weight = source_selections.get("bm25", 0) / total_selections
            semantic_weight = source_selections.get("semantic", 0) / total_selections
            fuzzy_weight = source_selections.get("fuzzy", 0) / total_selections

            # Adjust based on average rank (lower is better)
            rank_factor = 0.2
            if "bm25" in avg_ranks:
                bm25_weight *= 1 + rank_factor * (1 / avg_ranks["bm25"])
            if "semantic" in avg_ranks:
                semantic_weight *= 1 + rank_factor * (1 / avg_ranks["semantic"])
            if "fuzzy" in avg_ranks:
                fuzzy_weight *= 1 + rank_factor * (1 / avg_ranks["fuzzy"])

            # Apply new weights
            self.hybrid_search.set_weights(bm25_weight, semantic_weight, fuzzy_weight)

            logger.info(
                f"Optimized weights - BM25: {bm25_weight:.3f}, "
                f"Semantic: {semantic_weight:.3f}, Fuzzy: {fuzzy_weight:.3f}"
            )

    def get_optimization_report(self) -> Dict[str, Any]:
        """Get a report on optimization performance."""
        if not self.feedback_history:
            return {"status": "no_data"}

        # Analyze feedback
        source_stats = defaultdict(lambda: {"count": 0, "avg_rank": 0})
        for feedback in self.feedback_history:
            source = feedback.get("selected_source")
            if source:
                stats = source_stats[source]
                stats["count"] += 1
                stats["avg_rank"] = (
                    stats["avg_rank"] * (stats["count"] - 1) + feedback["selected_rank"]
                ) / stats["count"]

        # Analyze performance
        avg_search_time = 0
        if self.performance_history:
            avg_search_time = sum(p["search_time_ms"] for p in self.performance_history) / len(
                self.performance_history
            )

        return {
            "feedback_count": len(self.feedback_history),
            "source_statistics": dict(source_stats),
            "average_search_time_ms": avg_search_time,
            "current_weights": {
                "bm25": self.hybrid_search.config.bm25_weight,
                "semantic": self.hybrid_search.config.semantic_weight,
                "fuzzy": self.hybrid_search.config.fuzzy_weight,
            },
        }
