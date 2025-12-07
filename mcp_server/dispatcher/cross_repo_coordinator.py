"""
Cross-Repository Search Coordinator

This module coordinates search operations across multiple repositories,
providing intelligent result ranking, deduplication, and aggregation.
"""

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from mcp_server.indexer.reranker import Reranker
from mcp_server.plugins.repository_plugin_loader import get_repository_plugin_loader
from mcp_server.storage.multi_repo_manager import (
    CrossRepoSearchResult,
    MultiRepositoryManager,
    get_multi_repo_manager,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchContext:
    """Context for cross-repository search operations."""

    query: str
    search_type: str  # 'symbol', 'code', 'semantic'
    repositories: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    file_patterns: Optional[List[str]] = None
    max_results: int = 100
    deduplicate: bool = True
    rerank: bool = True
    include_dependencies: bool = False
    search_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResult:
    """Aggregated search result across repositories."""

    content: Dict[str, Any]
    score: float
    repositories: List[str]  # Repos where this result appears
    primary_repository: str  # Best match repository
    occurrences: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchStrategy:
    """Strategy for cross-repository search."""

    name: str
    scorer: Callable[[Dict[str, Any], SearchContext], float]
    filter: Optional[Callable[[Dict[str, Any], SearchContext], bool]] = None
    post_processor: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None


class CrossRepositoryCoordinator:
    """
    Coordinates cross-repository search with intelligent result processing.

    Features:
    - Multiple search strategies (symbol, code, semantic)
    - Result deduplication across repositories
    - Intelligent ranking based on relevance and repository priority
    - Dependency-aware search
    - Result aggregation and grouping
    """

    def __init__(
        self,
        multi_repo_manager: Optional[MultiRepositoryManager] = None,
        enable_semantic: bool = True,
        enable_reranking: bool = True,
    ):
        """
        Initialize the cross-repository coordinator.

        Args:
            multi_repo_manager: Multi-repository manager instance
            enable_semantic: Enable semantic search features
            enable_reranking: Enable result reranking
        """
        self.multi_repo_manager = multi_repo_manager or get_multi_repo_manager()
        self.plugin_loader = get_repository_plugin_loader()
        self.enable_semantic = enable_semantic
        self.enable_reranking = enable_reranking

        # Initialize reranker if enabled
        self.reranker = Reranker() if enable_reranking else None

        # Search strategies
        self._strategies: Dict[str, SearchStrategy] = self._init_strategies()

        # Cache for repository relationships
        self._repo_dependencies: Dict[str, Set[str]] = {}

        logger.info(
            f"Cross-repository coordinator initialized "
            f"(semantic={enable_semantic}, reranking={enable_reranking})"
        )

    def _init_strategies(self) -> Dict[str, SearchStrategy]:
        """Initialize search strategies."""
        return {
            "symbol": SearchStrategy(
                name="symbol", scorer=self._score_symbol_result, filter=self._filter_symbol_result
            ),
            "code": SearchStrategy(
                name="code", scorer=self._score_code_result, filter=self._filter_code_result
            ),
            "semantic": SearchStrategy(
                name="semantic",
                scorer=self._score_semantic_result,
                post_processor=self._post_process_semantic,
            ),
        }

    async def search(self, context: SearchContext) -> List[AggregatedResult]:
        """
        Perform coordinated search across repositories.

        Args:
            context: Search context with query and parameters

        Returns:
            List of aggregated results
        """
        start_time = datetime.now()
        logger.info(f"Starting cross-repository search: {context.query}")

        # Get search strategy
        strategy = self._strategies.get(context.search_type, self._strategies["symbol"])

        # Perform base search
        raw_results = await self._execute_search(context)

        # Apply strategy filter
        if strategy.filter:
            filtered_results = self._apply_filter(raw_results, strategy.filter, context)
        else:
            filtered_results = raw_results

        # Aggregate and deduplicate
        if context.deduplicate:
            aggregated = self._aggregate_results(filtered_results, context)
        else:
            aggregated = self._convert_to_aggregated(filtered_results)

        # Score results
        scored = self._score_results(aggregated, strategy.scorer, context)

        # Rerank if enabled
        if context.rerank and self.reranker:
            reranked = await self._rerank_results(scored, context)
        else:
            reranked = scored

        # Apply post-processing
        if strategy.post_processor:
            final_results = strategy.post_processor(reranked)
        else:
            final_results = reranked

        # Limit results
        limited = final_results[: context.max_results]

        # Log statistics
        search_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Search completed in {search_time:.2f}s: "
            f"{len(raw_results)} raw -> {len(limited)} final results"
        )

        return limited

    async def _execute_search(self, context: SearchContext) -> List[CrossRepoSearchResult]:
        """Execute search across repositories."""
        if context.search_type == "symbol":
            return await self.multi_repo_manager.search_symbol(
                query=context.query,
                repository_ids=context.repositories,
                language=context.languages[0] if context.languages else None,
                limit=context.max_results * 2,  # Get extra for filtering
            )
        elif context.search_type == "code":
            return await self.multi_repo_manager.search_code(
                query=context.query,
                repository_ids=context.repositories,
                file_pattern=context.file_patterns[0] if context.file_patterns else None,
                limit=context.max_results * 2,
            )
        else:
            # Semantic search would go here
            return await self.multi_repo_manager.search_symbol(
                query=context.query,
                repository_ids=context.repositories,
                limit=context.max_results * 2,
            )

    def _apply_filter(
        self, results: List[CrossRepoSearchResult], filter_func: Callable, context: SearchContext
    ) -> List[CrossRepoSearchResult]:
        """Apply filter to search results."""
        filtered_results = []

        for repo_result in results:
            if repo_result.error:
                continue

            filtered_items = []
            for item in repo_result.results:
                if filter_func(item, context):
                    filtered_items.append(item)

            if filtered_items:
                filtered_result = CrossRepoSearchResult(
                    repository_id=repo_result.repository_id,
                    repository_name=repo_result.repository_name,
                    results=filtered_items,
                    search_time=repo_result.search_time,
                )
                filtered_results.append(filtered_result)

        return filtered_results

    def _aggregate_results(
        self, results: List[CrossRepoSearchResult], context: SearchContext
    ) -> List[AggregatedResult]:
        """Aggregate and deduplicate results across repositories."""
        # Group by content hash
        grouped: Dict[str, List[Tuple[Dict[str, Any], str, str]]] = defaultdict(list)

        for repo_result in results:
            if repo_result.error:
                continue

            for item in repo_result.results:
                # Create content hash for deduplication
                content_hash = self._hash_result(item, context.search_type)
                grouped[content_hash].append(
                    (item, repo_result.repository_id, repo_result.repository_name)
                )

        # Create aggregated results
        aggregated = []
        for content_hash, occurrences in grouped.items():
            # Choose primary result (from highest priority repo)
            primary_item, primary_repo_id, primary_repo_name = occurrences[0]

            # Get all repository IDs
            repo_ids = [repo_id for _, repo_id, _ in occurrences]

            aggregated_result = AggregatedResult(
                content=primary_item,
                score=0.0,  # Will be set by scorer
                repositories=repo_ids,
                primary_repository=primary_repo_id,
                occurrences=len(occurrences),
                metadata={"content_hash": content_hash, "primary_repo_name": primary_repo_name},
            )
            aggregated.append(aggregated_result)

        return aggregated

    def _convert_to_aggregated(
        self, results: List[CrossRepoSearchResult]
    ) -> List[AggregatedResult]:
        """Convert raw results to aggregated format without deduplication."""
        aggregated = []

        for repo_result in results:
            if repo_result.error:
                continue

            for item in repo_result.results:
                aggregated_result = AggregatedResult(
                    content=item,
                    score=0.0,
                    repositories=[repo_result.repository_id],
                    primary_repository=repo_result.repository_id,
                    occurrences=1,
                    metadata={"repository_name": repo_result.repository_name},
                )
                aggregated.append(aggregated_result)

        return aggregated

    def _hash_result(self, result: Dict[str, Any], search_type: str) -> str:
        """Create hash for result deduplication."""
        if search_type == "symbol":
            # Hash based on symbol name and type
            key = f"{result.get('symbol', '')}:{result.get('type', '')}"
        elif search_type == "code":
            # Hash based on file and line range
            key = f"{result.get('file', '')}:{result.get('line', '')}"
        else:
            # Generic hash
            key = str(result)

        return hashlib.md5(key.encode()).hexdigest()

    def _score_results(
        self, results: List[AggregatedResult], scorer: Callable, context: SearchContext
    ) -> List[AggregatedResult]:
        """Score and sort results."""
        for result in results:
            result.score = scorer(result.content, context)

            # Boost score based on occurrences
            if result.occurrences > 1:
                result.score *= 1 + 0.1 * (result.occurrences - 1)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results

    async def _rerank_results(
        self, results: List[AggregatedResult], context: SearchContext
    ) -> List[AggregatedResult]:
        """Rerank results using semantic reranker."""
        if not results:
            return results

        # Prepare documents for reranking
        documents = []
        for result in results:
            # Create document representation
            doc = self._create_document_repr(result.content, context.search_type)
            documents.append(doc)

        # Perform reranking
        reranked_indices = await self.reranker.rerank(
            query=context.query, documents=documents, top_k=min(len(results), context.max_results)
        )

        # Reorder results
        reranked_results = []
        for idx in reranked_indices:
            if idx < len(results):
                reranked_results.append(results[idx])

        return reranked_results

    def _create_document_repr(self, result: Dict[str, Any], search_type: str) -> str:
        """Create document representation for reranking."""
        if search_type == "symbol":
            return (
                f"{result.get('symbol', '')} "
                f"{result.get('type', '')} "
                f"in {result.get('file', '')}"
            )
        elif search_type == "code":
            return (
                f"{result.get('code', '')} "
                f"in {result.get('file', '')} "
                f"line {result.get('line', '')}"
            )
        else:
            return str(result)

    # Scoring functions
    def _score_symbol_result(self, result: Dict[str, Any], context: SearchContext) -> float:
        """Score symbol search result."""
        score = 0.0
        query_lower = context.query.lower()
        symbol_lower = result.get("symbol", "").lower()

        # Exact match
        if symbol_lower == query_lower:
            score += 10.0
        # Prefix match
        elif symbol_lower.startswith(query_lower):
            score += 7.0
        # Contains match
        elif query_lower in symbol_lower:
            score += 5.0

        # Type boost
        symbol_type = result.get("type", "").lower()
        if symbol_type in ["class", "interface"]:
            score += 2.0
        elif symbol_type in ["function", "method"]:
            score += 1.5

        # Language preference
        if context.languages and result.get("language") in context.languages:
            score += 1.0

        return score

    def _score_code_result(self, result: Dict[str, Any], context: SearchContext) -> float:
        """Score code search result."""
        score = 0.0
        query_lower = context.query.lower()

        # Code content matching
        code = result.get("code", "").lower()
        matches = code.count(query_lower)
        score += matches * 2.0

        # File pattern matching
        if context.file_patterns:
            file_path = result.get("file", "")
            for pattern in context.file_patterns:
                if self._match_pattern(file_path, pattern):
                    score += 3.0
                    break

        return score

    def _score_semantic_result(self, result: Dict[str, Any], context: SearchContext) -> float:
        """Score semantic search result."""
        # Semantic scoring would use embeddings
        # For now, fall back to symbol scoring
        return self._score_symbol_result(result, context)

    # Filter functions
    def _filter_symbol_result(self, result: Dict[str, Any], context: SearchContext) -> bool:
        """Filter symbol results."""
        # Language filter
        if context.languages and result.get("language") not in context.languages:
            return False

        # File pattern filter
        if context.file_patterns:
            file_path = result.get("file", "")
            if not any(self._match_pattern(file_path, p) for p in context.file_patterns):
                return False

        return True

    def _filter_code_result(self, result: Dict[str, Any], context: SearchContext) -> bool:
        """Filter code results."""
        return self._filter_symbol_result(result, context)

    def _match_pattern(self, file_path: str, pattern: str) -> bool:
        """Match file path against pattern."""
        # Convert glob to regex
        pattern = pattern.replace("*", ".*").replace("?", ".")
        return bool(re.match(pattern, file_path))

    def _post_process_semantic(self, results: List[AggregatedResult]) -> List[AggregatedResult]:
        """Post-process semantic search results."""
        # Group related results
        # This would use semantic similarity
        return results

    async def search_with_dependencies(self, context: SearchContext) -> List[AggregatedResult]:
        """
        Search including dependency repositories.

        Args:
            context: Search context

        Returns:
            Results including dependencies
        """
        if not context.include_dependencies:
            return await self.search(context)

        # Get dependency repositories
        all_repos = set(context.repositories or [])

        for repo_id in list(all_repos):
            deps = await self._get_repository_dependencies(repo_id)
            all_repos.update(deps)

        # Update context with all repositories
        context.repositories = list(all_repos)

        # Perform search
        results = await self.search(context)

        # Mark results from dependencies
        for result in results:
            if result.primary_repository not in (context.repositories or []):
                result.metadata["from_dependency"] = True

        return results

    async def _get_repository_dependencies(self, repository_id: str) -> Set[str]:
        """Get dependency repositories."""
        if repository_id in self._repo_dependencies:
            return self._repo_dependencies[repository_id]

        # Would analyze package.json, pom.xml, etc.
        # For now, return empty set
        deps = set()
        self._repo_dependencies[repository_id] = deps

        return deps

    def get_search_strategies(self) -> List[str]:
        """Get available search strategies."""
        return list(self._strategies.keys())

    def register_strategy(self, name: str, strategy: SearchStrategy):
        """Register a custom search strategy."""
        self._strategies[name] = strategy
        logger.info(f"Registered search strategy: {name}")

    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine best search strategy.

        Args:
            query: Search query

        Returns:
            Analysis results with recommended strategy
        """
        analysis = {
            "query": query,
            "recommended_strategy": "symbol",
            "detected_patterns": [],
            "suggested_filters": {},
        }

        # Check for code patterns
        if any(char in query for char in ["{", "}", "(", ")", ";"]):
            analysis["recommended_strategy"] = "code"
            analysis["detected_patterns"].append("code_syntax")

        # Check for semantic indicators
        semantic_keywords = ["how to", "example", "implement", "usage"]
        if any(keyword in query.lower() for keyword in semantic_keywords):
            analysis["recommended_strategy"] = "semantic"
            analysis["detected_patterns"].append("natural_language")

        # Check for language hints
        language_pattern = r"\b(python|java|javascript|go|rust)\b"
        lang_match = re.search(language_pattern, query.lower())
        if lang_match:
            analysis["suggested_filters"]["languages"] = [lang_match.group()]
            analysis["detected_patterns"].append("language_specific")

        # Check for file patterns
        file_pattern = r"\*\.\w+|\w+\.\w+"
        if re.search(file_pattern, query):
            analysis["detected_patterns"].append("file_pattern")

        return analysis


# Singleton instance
_coordinator_instance: Optional[CrossRepositoryCoordinator] = None


def get_cross_repo_coordinator(
    enable_semantic: bool = True, enable_reranking: bool = True
) -> CrossRepositoryCoordinator:
    """
    Get the singleton cross-repository coordinator.

    Args:
        enable_semantic: Enable semantic search
        enable_reranking: Enable result reranking

    Returns:
        CrossRepositoryCoordinator instance
    """
    global _coordinator_instance

    if _coordinator_instance is None:
        _coordinator_instance = CrossRepositoryCoordinator(
            enable_semantic=enable_semantic, enable_reranking=enable_reranking
        )

    return _coordinator_instance
