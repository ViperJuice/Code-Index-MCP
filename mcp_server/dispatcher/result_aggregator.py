"""Result aggregator for combining and ranking search results from multiple plugins.

This module provides advanced result aggregation capabilities including:
- Result ranking and scoring across multiple plugins
- Context merging for search results
- Duplicate detection and removal
- Performance optimizations with caching
- Configurable aggregation strategies
"""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..plugin_base import IPlugin, Reference, SearchResult, SymbolDef

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResult:
    """An aggregated result from multiple plugins."""

    primary_result: SearchResult
    sources: List[IPlugin]
    confidence: float
    rank_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    duplicate_count: int = 1
    context_lines: List[str] = field(default_factory=list)


@dataclass
class AggregationStats:
    """Statistics about aggregation operation."""

    total_results: int
    unique_results: int
    duplicates_removed: int
    plugins_used: int
    execution_time: float
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class RankingCriteria:
    """Criteria for ranking aggregated results."""

    # Weights for different ranking factors (sum should be 1.0)
    relevance_weight: float = 0.4  # Plugin-provided relevance score
    confidence_weight: float = 0.3  # Aggregation confidence
    frequency_weight: float = 0.2  # How many plugins found this result
    recency_weight: float = 0.1  # File modification time

    # Additional ranking factors
    prefer_exact_matches: bool = True
    boost_multiple_sources: bool = True
    penalize_long_files: bool = False
    boost_common_extensions: bool = True

    # Score normalization parameters for different search backends
    # BM25 scores are logarithmic and can range from ~0.1 to 20+
    bm25_score_max: float = 15.0  # Typical max BM25 score for normalization
    bm25_score_min: float = 0.0  # Min BM25 score

    # Semantic scores are cosine similarity (0-1)
    semantic_score_max: float = 1.0
    semantic_score_min: float = 0.0

    # Fuzzy scores are match ratios (0-1)
    fuzzy_score_max: float = 1.0
    fuzzy_score_min: float = 0.0

    # Default score when score is missing
    default_score: float = 0.5


class IAggregationStrategy(ABC):
    """Interface for different result aggregation strategies."""

    @abstractmethod
    def aggregate(
        self,
        results_by_plugin: Dict[IPlugin, List[SearchResult]],
        criteria: RankingCriteria,
    ) -> List[AggregatedResult]:
        """Aggregate results using this strategy.

        Args:
            results_by_plugin: Results grouped by plugin
            criteria: Ranking criteria to use

        Returns:
            List of aggregated results
        """


# Score normalization helper functions
def _normalize_score(score: float, min_val: float, max_val: float) -> float:
    """Normalize a score to 0-1 range using min-max normalization.

    Args:
        score: Raw score to normalize
        min_val: Minimum expected score value
        max_val: Maximum expected score value

    Returns:
        Normalized score in 0-1 range
    """
    if max_val <= min_val:
        return 0.5  # Fallback if range is invalid

    # Clamp score to valid range
    clamped_score = max(min_val, min(max_val, score))

    # Min-max normalization
    normalized = (clamped_score - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def _detect_score_source(result: SearchResult, plugin: IPlugin) -> str:
    """Detect the source type of a search result score.

    Args:
        result: Search result with potential metadata
        plugin: Plugin that generated the result

    Returns:
        Source type: 'bm25', 'semantic', 'fuzzy', or 'unknown'
    """
    # Check plugin type/name
    plugin_lang = getattr(plugin, "lang", "").lower()
    plugin_name = type(plugin).__name__.lower()

    # BM25 adapter or FTS5-based results
    if "bm25" in plugin_name or plugin_lang == "all":
        return "bm25"

    # Semantic search results (usually have 'semantic' in class name or metadata)
    if "semantic" in plugin_name or result.get("semantic"):
        return "semantic"

    # Check result metadata for hints
    metadata = result.get("metadata", {})
    if isinstance(metadata, dict):
        if "bm25" in str(metadata).lower():
            return "bm25"
        if "semantic" in str(metadata).lower() or "embedding" in str(metadata).lower():
            return "semantic"
        if "fuzzy" in str(metadata).lower() or "trigram" in str(metadata).lower():
            return "fuzzy"

    # Check score magnitude to infer type
    score = result.get("score")
    if score is not None:
        # BM25 scores are typically > 1.0
        if score > 1.5:
            return "bm25"
        # Semantic/fuzzy scores are typically 0-1
        elif 0 <= score <= 1.0:
            # Can't distinguish between semantic and fuzzy without more context
            return "semantic"  # Default to semantic for 0-1 range

    return "unknown"


def _normalize_result_score(
    result: SearchResult, plugin: IPlugin, criteria: RankingCriteria
) -> Tuple[float, str, Dict[str, Any]]:
    """Normalize a result's score based on its source type.

    Args:
        result: Search result with score
        plugin: Plugin that generated the result
        criteria: Ranking criteria with normalization parameters

    Returns:
        Tuple of (normalized_score, source_type, normalization_metadata)
    """
    raw_score = result.get("score")

    # Handle missing scores
    if raw_score is None:
        return (
            criteria.default_score,
            "unknown",
            {"normalized": True, "reason": "missing_score", "default": True},
        )

    # Detect source type
    source_type = _detect_score_source(result, plugin)

    # Normalize based on source type
    if source_type == "bm25":
        normalized = _normalize_score(raw_score, criteria.bm25_score_min, criteria.bm25_score_max)
    elif source_type == "semantic":
        normalized = _normalize_score(
            raw_score, criteria.semantic_score_min, criteria.semantic_score_max
        )
    elif source_type == "fuzzy":
        normalized = _normalize_score(raw_score, criteria.fuzzy_score_min, criteria.fuzzy_score_max)
    else:
        # Unknown source - try to normalize assuming 0-1 range
        # If score is > 1, assume it's BM25-like
        if raw_score > 1.5:
            normalized = _normalize_score(
                raw_score, criteria.bm25_score_min, criteria.bm25_score_max
            )
            source_type = "bm25_inferred"
        else:
            normalized = _normalize_score(raw_score, 0.0, 1.0)
            source_type = "semantic_inferred"

    metadata = {
        "normalized": True,
        "raw_score": raw_score,
        "normalized_score": normalized,
        "source_type": source_type,
        "default": False,
    }

    return normalized, source_type, metadata


class IResultAggregator(ABC):
    """Interface for result aggregation and ranking."""

    @abstractmethod
    def aggregate_search_results(
        self,
        results_by_plugin: Dict[IPlugin, List[SearchResult]],
        limit: Optional[int] = None,
    ) -> Tuple[List[AggregatedResult], AggregationStats]:
        """Aggregate search results from multiple plugins.

        Args:
            results_by_plugin: Search results grouped by plugin
            limit: Maximum number of results to return

        Returns:
            Tuple of (aggregated results, aggregation statistics)
        """

    @abstractmethod
    def aggregate_symbol_definitions(
        self, definitions_by_plugin: Dict[IPlugin, Optional[SymbolDef]]
    ) -> Optional[SymbolDef]:
        """Aggregate symbol definitions from multiple plugins.

        Args:
            definitions_by_plugin: Symbol definitions by plugin

        Returns:
            Best symbol definition or None
        """

    @abstractmethod
    def aggregate_references(
        self, references_by_plugin: Dict[IPlugin, List[Reference]]
    ) -> List[Reference]:
        """Aggregate references from multiple plugins.

        Args:
            references_by_plugin: References grouped by plugin

        Returns:
            Deduplicated and ranked list of references
        """


class SimpleAggregationStrategy(IAggregationStrategy):
    """Simple aggregation strategy that merges results and ranks by score."""

    def aggregate(
        self,
        results_by_plugin: Dict[IPlugin, List[SearchResult]],
        criteria: RankingCriteria,
    ) -> List[AggregatedResult]:
        """Aggregate results using simple strategy."""

        # Group results by file+line
        result_groups: Dict[str, List[Tuple[IPlugin, SearchResult]]] = defaultdict(list)

        for plugin, results in results_by_plugin.items():
            for result in results:
                key = f"{result['file']}:{result['line']}"
                result_groups[key].append((plugin, result))

        # Create aggregated results
        aggregated = []
        for key, group in result_groups.items():
            if not group:
                continue

            # Use first result as primary
            primary_plugin, primary_result = group[0]
            sources = [plugin for plugin, _ in group]

            # Calculate confidence based on number of sources
            confidence = min(1.0, len(sources) / 3.0)  # Max confidence with 3+ sources

            # Calculate rank score
            rank_score = self._calculate_rank_score(group, criteria)

            # Extract ranking metadata from primary result if available
            ranking_metadata = primary_result.get("ranking_metadata", {})

            aggregated_result = AggregatedResult(
                primary_result=primary_result,
                sources=sources,
                confidence=confidence,
                rank_score=rank_score,
                duplicate_count=len(group),
                metadata={
                    "key": key,
                    "source_count": len(sources),
                    "all_results": [result for _, result in group],
                    "ranking": ranking_metadata,  # Include ranking explanation
                },
            )
            aggregated.append(aggregated_result)

        # Sort by rank score
        aggregated.sort(key=lambda r: r.rank_score, reverse=True)

        return aggregated

    def _calculate_rank_score(
        self, group: List[Tuple[IPlugin, SearchResult]], criteria: RankingCriteria
    ) -> float:
        """Calculate rank score for a group of results with score normalization."""
        if not group:
            return 0.0

        # Get primary result and plugin
        primary_plugin, primary_result = group[0]

        # Normalize the relevance score based on source type
        relevance_score, source_type, norm_metadata = _normalize_result_score(
            primary_result, primary_plugin, criteria
        )

        # Confidence based on number of sources (0-1)
        confidence_score = min(1.0, len(group) / 3.0)

        # Frequency score (0-1)
        frequency_score = min(1.0, len(group) / 5.0)

        # Recency score (simplified - would need file stats)
        recency_score = criteria.default_score  # Use configurable default

        # Calculate weighted score
        rank_score = (
            relevance_score * criteria.relevance_weight
            + confidence_score * criteria.confidence_weight
            + frequency_score * criteria.frequency_weight
            + recency_score * criteria.recency_weight
        )

        # Apply boosts
        boost_factor = 1.0
        boost_reasons = []

        if criteria.boost_multiple_sources and len(group) > 1:
            boost_factor *= 1.1
            boost_reasons.append("multiple_sources")

        # Boost exact matches from BM25
        if source_type == "bm25" and criteria.prefer_exact_matches:
            raw_score = primary_result.get("score", 0)
            if raw_score > 10.0:  # High BM25 score indicates strong match
                boost_factor *= 1.05
                boost_reasons.append("high_bm25_score")

        rank_score *= boost_factor

        # Store ranking metadata in primary result for debugging
        ranking_metadata = {
            "relevance_score": relevance_score,
            "confidence_score": confidence_score,
            "frequency_score": frequency_score,
            "recency_score": recency_score,
            "boost_factor": boost_factor,
            "boost_reasons": boost_reasons,
            "source_type": source_type,
            "normalization": norm_metadata,
            "final_rank_score": min(1.0, rank_score),
        }

        # Store metadata back in result
        if "ranking_metadata" not in primary_result:
            primary_result["ranking_metadata"] = ranking_metadata

        return min(1.0, rank_score)


class SmartAggregationStrategy(IAggregationStrategy):
    """Smart aggregation strategy with semantic similarity and context merging."""

    def __init__(self, similarity_threshold: float = 0.8, enable_document_chunking: bool = True):
        """Initialize smart aggregation strategy.

        Args:
            similarity_threshold: Threshold for considering results similar
            enable_document_chunking: Enable special handling for document chunks
        """
        self.similarity_threshold = similarity_threshold
        self.enable_document_chunking = enable_document_chunking

    def aggregate(
        self,
        results_by_plugin: Dict[IPlugin, List[SearchResult]],
        criteria: RankingCriteria,
    ) -> List[AggregatedResult]:
        """Aggregate results using smart strategy with similarity detection."""

        # Collect all results with metadata
        all_results = []
        for plugin, results in results_by_plugin.items():
            for result in results:
                all_results.append((plugin, result))

        if not all_results:
            return []

        # Group similar results
        grouped_results = self._group_similar_results(all_results)

        # Create aggregated results
        aggregated = []
        for group in grouped_results:
            if not group:
                continue

            # Select best primary result
            primary_plugin, primary_result = self._select_primary_result(group)
            sources = [plugin for plugin, _ in group]

            # Calculate confidence with similarity bonus
            base_confidence = min(1.0, len(sources) / 3.0)
            similarity_bonus = 0.1 if len(group) > 1 else 0.0
            confidence = min(1.0, base_confidence + similarity_bonus)

            # Calculate enhanced rank score
            rank_score = self._calculate_enhanced_rank_score(group, criteria)

            # Merge context from similar results
            context_lines = self._merge_context(group)

            # Extract ranking metadata from primary result if available
            ranking_metadata = primary_result.get("ranking_metadata", {})

            aggregated_result = AggregatedResult(
                primary_result=primary_result,
                sources=sources,
                confidence=confidence,
                rank_score=rank_score,
                duplicate_count=len(group),
                context_lines=context_lines,
                metadata={
                    "similarity_group": True,
                    "source_count": len(sources),
                    "unique_files": len(set(result["file"] for _, result in group)),
                    "avg_similarity": self._calculate_avg_similarity(group),
                    "ranking": ranking_metadata,  # Include ranking explanation
                },
            )
            aggregated.append(aggregated_result)

        # Sort by enhanced rank score
        aggregated.sort(key=lambda r: r.rank_score, reverse=True)

        return aggregated

    def _group_similar_results(
        self, all_results: List[Tuple[IPlugin, SearchResult]]
    ) -> List[List[Tuple[IPlugin, SearchResult]]]:
        """Group similar results together."""
        groups = []
        used_indices = set()

        for i, (plugin1, result1) in enumerate(all_results):
            if i in used_indices:
                continue

            # Start new group
            group = [(plugin1, result1)]
            used_indices.add(i)

            # Find similar results
            for j, (plugin2, result2) in enumerate(all_results):
                if j in used_indices or j <= i:
                    continue

                if self._are_results_similar(result1, result2):
                    group.append((plugin2, result2))
                    used_indices.add(j)

            groups.append(group)

        return groups

    def _are_results_similar(self, result1: SearchResult, result2: SearchResult) -> bool:
        """Check if two results are similar enough to group."""
        # Same file and close line numbers
        if result1["file"] == result2["file"]:
            line_diff = abs(result1["line"] - result2["line"])

            # Special handling for documentation files - larger chunks
            if self.enable_document_chunking and self._is_documentation_file(result1["file"]):
                if line_diff <= 10:  # Within 10 lines for docs
                    return True
            elif line_diff <= 2:  # Within 2 lines for code
                return True

        # Similar snippets
        snippet_similarity = SequenceMatcher(None, result1["snippet"], result2["snippet"]).ratio()
        if snippet_similarity >= self.similarity_threshold:
            return True

        return False

    def _is_documentation_file(self, file_path: str) -> bool:
        """Check if a file is a documentation file."""
        doc_extensions = {".md", ".rst", ".txt", ".adoc", ".textile"}
        doc_names = {
            "readme",
            "changelog",
            "contributing",
            "license",
            "install",
            "setup",
            "guide",
            "tutorial",
        }

        path_lower = file_path.lower()

        # Check extension
        for ext in doc_extensions:
            if path_lower.endswith(ext):
                return True

        # Check filename
        filename = Path(file_path).stem.lower()
        for doc_name in doc_names:
            if doc_name in filename:
                return True

        # Check if in docs directory
        if "/docs/" in path_lower or "/documentation/" in path_lower:
            return True

        return False

    def _select_primary_result(
        self, group: List[Tuple[IPlugin, SearchResult]]
    ) -> Tuple[IPlugin, SearchResult]:
        """Select the best result as primary from a group."""
        if len(group) == 1:
            return group[0]

        # Prefer result with highest score
        best_plugin, best_result = group[0]
        best_score = best_result.get("score", 0.0) or 0.0

        for plugin, result in group[1:]:
            score = result.get("score", 0.0) or 0.0
            if score > best_score:
                best_plugin, best_result = plugin, result
                best_score = score

        return best_plugin, best_result

    def _calculate_enhanced_rank_score(
        self, group: List[Tuple[IPlugin, SearchResult]], criteria: RankingCriteria
    ) -> float:
        """Calculate enhanced rank score with normalization and additional factors."""
        if not group:
            return 0.0

        # Get primary result and plugin
        primary_plugin, primary_result = group[0]

        # Normalize the relevance score based on source type
        relevance_score, source_type, norm_metadata = _normalize_result_score(
            primary_result, primary_plugin, criteria
        )

        # Enhanced confidence with similarity consideration
        base_confidence = min(1.0, len(group) / 3.0)
        similarity_boost = 0.1 if len(group) > 1 else 0.0
        confidence_score = min(1.0, base_confidence + similarity_boost)

        # Frequency score with file diversity bonus
        unique_files = len(set(result["file"] for _, result in group))
        frequency_score = min(1.0, len(group) / 5.0)
        diversity_bonus = 1.0
        if unique_files > 1:
            diversity_bonus = 1.2  # Boost for cross-file matches
            frequency_score *= diversity_bonus

        # Recency score (simplified)
        recency_score = criteria.default_score

        # Calculate line proximity score for grouped results
        proximity_score = 1.0
        if len(group) > 1 and unique_files == 1:
            # Check if results are close together in the same file
            lines = [result["line"] for _, result in group]
            line_span = max(lines) - min(lines)
            if line_span <= 5:
                proximity_score = 1.1  # Boost for results close together
            elif line_span <= 10:
                proximity_score = 1.05

        # Calculate weighted score
        rank_score = (
            relevance_score * criteria.relevance_weight
            + confidence_score * criteria.confidence_weight
            + frequency_score * criteria.frequency_weight
            + recency_score * criteria.recency_weight
        )

        # Apply additional boosts
        boost_factor = 1.0
        boost_reasons = []

        if criteria.boost_multiple_sources and len(group) > 1:
            boost_factor *= 1.1
            boost_reasons.append("multiple_sources")

        # Apply proximity boost
        if proximity_score > 1.0:
            boost_factor *= proximity_score
            boost_reasons.append(f"proximity_boost_{proximity_score:.2f}")

        # Boost exact matches
        if criteria.prefer_exact_matches:
            # Check for short, single-line results (likely exact matches)
            for _, result in group:
                if len(result["snippet"]) < 100 and "\n" not in result["snippet"]:
                    boost_factor *= 1.05
                    boost_reasons.append("exact_match_snippet")
                    break

            # Additional boost for high-scoring BM25 results
            if source_type == "bm25":
                raw_score = primary_result.get("score", 0)
                if raw_score > 10.0:
                    boost_factor *= 1.05
                    boost_reasons.append("high_bm25_exact")

        # Source-specific adjustments
        if source_type == "semantic" and relevance_score > 0.9:
            # High semantic similarity indicates very relevant result
            boost_factor *= 1.03
            boost_reasons.append("high_semantic_similarity")

        rank_score *= boost_factor

        # Store comprehensive ranking metadata
        ranking_metadata = {
            "relevance_score": relevance_score,
            "confidence_score": confidence_score,
            "frequency_score": frequency_score,
            "recency_score": recency_score,
            "boost_factor": boost_factor,
            "boost_reasons": boost_reasons,
            "source_type": source_type,
            "normalization": norm_metadata,
            "unique_files": unique_files,
            "diversity_bonus": diversity_bonus,
            "proximity_score": proximity_score,
            "group_size": len(group),
            "final_rank_score": min(1.0, rank_score),
        }

        # Store metadata back in result
        if "ranking_metadata" not in primary_result:
            primary_result["ranking_metadata"] = ranking_metadata

        return min(1.0, rank_score)

    def _merge_context(self, group: List[Tuple[IPlugin, SearchResult]]) -> List[str]:
        """Merge context lines from similar results."""
        if not group:
            return []

        _, primary_result = group[0]

        # Check if this is a documentation file
        if self.enable_document_chunking and self._is_documentation_file(primary_result["file"]):
            # For documentation, merge snippets into larger context
            snippets_by_line = {}
            for _, result in group:
                snippets_by_line[result["line"]] = result["snippet"]

            # Sort by line number and merge adjacent snippets
            sorted_lines = sorted(snippets_by_line.keys())
            merged_snippets = []
            current_snippet = []
            last_line = -100

            for line in sorted_lines:
                if line - last_line <= 3:  # Adjacent or close lines
                    current_snippet.append(snippets_by_line[line])
                else:
                    # Start new snippet group
                    if current_snippet:
                        merged_snippets.append("\n".join(current_snippet))
                    current_snippet = [snippets_by_line[line]]
                last_line = line

            # Add final snippet group
            if current_snippet:
                merged_snippets.append("\n".join(current_snippet))

            return merged_snippets[:5]  # Limit to 5 merged contexts
        else:
            # For code files, return unique snippets
            all_snippets = [result["snippet"] for _, result in group]
            return list(dict.fromkeys(all_snippets))[:5]  # Preserve order, limit to 5

    def _calculate_avg_similarity(self, group: List[Tuple[IPlugin, SearchResult]]) -> float:
        """Calculate average similarity within a group."""
        if len(group) <= 1:
            return 1.0

        similarities = []
        results = [result for _, result in group]

        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                similarity = SequenceMatcher(
                    None, results[i]["snippet"], results[j]["snippet"]
                ).ratio()
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 1.0


class ResultAggregator(IResultAggregator):
    """Advanced result aggregator with multiple strategies and caching."""

    def __init__(
        self,
        strategy: Optional[IAggregationStrategy] = None,
        ranking_criteria: Optional[RankingCriteria] = None,
        cache_enabled: bool = True,
        cache_timeout: float = 300.0,
    ):
        """Initialize result aggregator.

        Args:
            strategy: Aggregation strategy to use
            ranking_criteria: Criteria for ranking results
            cache_enabled: Whether to enable result caching
            cache_timeout: Cache timeout in seconds
        """
        self.strategy = strategy or SmartAggregationStrategy()
        self.ranking_criteria = ranking_criteria or RankingCriteria()
        self.cache_enabled = cache_enabled
        self.cache_timeout = cache_timeout

        # Caching
        self._result_cache: Dict[str, Tuple[List[AggregatedResult], float]] = {}
        self._stats_cache: Dict[str, Tuple[AggregationStats, float]] = {}

        # Statistics
        self._total_aggregations = 0
        self._cache_hits = 0
        self._cache_misses = 0

    def aggregate_search_results(
        self,
        results_by_plugin: Dict[IPlugin, List[SearchResult]],
        limit: Optional[int] = None,
    ) -> Tuple[List[AggregatedResult], AggregationStats]:
        """Aggregate search results from multiple plugins."""
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(results_by_plugin, limit)

        # Check cache
        if self.cache_enabled:
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                self._cache_hits += 1
                results, stats = cached_result
                stats.cache_hits = self._cache_hits
                stats.cache_misses = self._cache_misses
                return results, stats

        self._cache_misses += 1
        self._total_aggregations += 1

        # Count input statistics
        total_results = sum(len(results) for results in results_by_plugin.values())
        plugins_used = len([plugin for plugin, results in results_by_plugin.items() if results])

        # Perform aggregation
        try:
            aggregated_results = self.strategy.aggregate(results_by_plugin, self.ranking_criteria)

            # Apply limit
            if limit is not None and limit > 0:
                aggregated_results = aggregated_results[:limit]

            # Calculate statistics
            unique_results = len(aggregated_results)
            duplicates_removed = total_results - unique_results
            execution_time = time.time() - start_time

            stats = AggregationStats(
                total_results=total_results,
                unique_results=unique_results,
                duplicates_removed=max(0, duplicates_removed),
                plugins_used=plugins_used,
                execution_time=execution_time,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
            )

            # Cache result
            if self.cache_enabled:
                self._cache_result(cache_key, aggregated_results, stats)

            return aggregated_results, stats

        except Exception as e:
            logger.error(f"Error aggregating search results: {e}", exc_info=True)

            # Return basic aggregation on error
            basic_results = self._basic_aggregation(results_by_plugin, limit)
            execution_time = time.time() - start_time

            stats = AggregationStats(
                total_results=total_results,
                unique_results=len(basic_results),
                duplicates_removed=total_results - len(basic_results),
                plugins_used=plugins_used,
                execution_time=execution_time,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
            )

            return basic_results, stats

    def aggregate_symbol_definitions(
        self, definitions_by_plugin: Dict[IPlugin, Optional[SymbolDef]]
    ) -> Optional[SymbolDef]:
        """Aggregate symbol definitions from multiple plugins."""
        # Filter out None definitions
        valid_definitions = [
            (plugin, defn) for plugin, defn in definitions_by_plugin.items() if defn is not None
        ]

        if not valid_definitions:
            return None

        if len(valid_definitions) == 1:
            return valid_definitions[0][1]

        # For multiple definitions, prefer the one with most complete information
        best_plugin, best_definition = valid_definitions[0]
        best_score = self._score_symbol_definition(best_definition)

        for plugin, definition in valid_definitions[1:]:
            score = self._score_symbol_definition(definition)
            if score > best_score:
                best_plugin, best_definition = plugin, definition
                best_score = score

        logger.debug(
            f"Aggregated symbol definition from {len(valid_definitions)} sources, "
            f"selected from {getattr(best_plugin, 'lang', 'unknown')} plugin"
        )

        return best_definition

    def aggregate_references(
        self, references_by_plugin: Dict[IPlugin, List[Reference]]
    ) -> List[Reference]:
        """Aggregate references from multiple plugins."""
        all_references = []

        # Collect all references
        for plugin, references in references_by_plugin.items():
            all_references.extend(references)

        if not all_references:
            return []

        # Deduplicate by file and line
        seen = set()
        unique_references = []

        for ref in all_references:
            key = (ref.file, ref.line)
            if key not in seen:
                seen.add(key)
                unique_references.append(ref)

        # Sort by file and line
        unique_references.sort(key=lambda r: (r.file, r.line))

        logger.debug(
            f"Aggregated {len(unique_references)} unique references from "
            f"{len(all_references)} total references across "
            f"{len(references_by_plugin)} plugins"
        )

        return unique_references

    def _generate_cache_key(
        self, results_by_plugin: Dict[IPlugin, List[SearchResult]], limit: Optional[int]
    ) -> str:
        """Generate cache key for results."""
        # Create a deterministic hash of the input
        key_parts = []

        # Sort plugins by name for consistency
        sorted_plugins = sorted(
            results_by_plugin.items(), key=lambda x: getattr(x[0], "lang", str(x[0]))
        )

        for plugin, results in sorted_plugins:
            plugin_key = getattr(plugin, "lang", str(plugin))
            results_hash = hashlib.md5(str(results).encode()).hexdigest()[:8]
            key_parts.append(f"{plugin_key}:{results_hash}")

        key_parts.append(f"limit:{limit}")
        key_parts.append(f"strategy:{type(self.strategy).__name__}")

        cache_key = "|".join(key_parts)
        return hashlib.md5(cache_key.encode()).hexdigest()

    def _get_cached_result(
        self, cache_key: str
    ) -> Optional[Tuple[List[AggregatedResult], AggregationStats]]:
        """Get cached result if still valid."""
        if cache_key in self._result_cache and cache_key in self._stats_cache:
            results, result_timestamp = self._result_cache[cache_key]
            stats, stats_timestamp = self._stats_cache[cache_key]

            current_time = time.time()
            if (
                current_time - result_timestamp < self.cache_timeout
                and current_time - stats_timestamp < self.cache_timeout
            ):
                return results, stats

        return None

    def _cache_result(
        self, cache_key: str, results: List[AggregatedResult], stats: AggregationStats
    ) -> None:
        """Cache aggregation result."""
        current_time = time.time()
        self._result_cache[cache_key] = (results, current_time)
        self._stats_cache[cache_key] = (stats, current_time)

        # Clean old cache entries if too many
        if len(self._result_cache) > 1000:
            self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """Clean up old cache entries."""
        current_time = time.time()

        # Remove expired entries
        expired_keys = [
            key
            for key, (_, timestamp) in self._result_cache.items()
            if current_time - timestamp > self.cache_timeout
        ]

        for key in expired_keys:
            self._result_cache.pop(key, None)
            self._stats_cache.pop(key, None)

    def _basic_aggregation(
        self, results_by_plugin: Dict[IPlugin, List[SearchResult]], limit: Optional[int]
    ) -> List[AggregatedResult]:
        """Basic aggregation fallback."""
        all_results = []

        for plugin, results in results_by_plugin.items():
            for result in results:
                aggregated = AggregatedResult(
                    primary_result=result,
                    sources=[plugin],
                    confidence=0.5,
                    rank_score=result.get("score", 0.5) or 0.5,
                    duplicate_count=1,
                    metadata={"fallback": True},
                )
                all_results.append(aggregated)

        # Sort by score
        all_results.sort(key=lambda r: r.rank_score, reverse=True)

        if limit is not None and limit > 0:
            all_results = all_results[:limit]

        return all_results

    def _score_symbol_definition(self, definition: SymbolDef) -> float:
        """Score a symbol definition for selection."""
        score = 0.0

        # Points for having documentation
        if definition.get("doc"):
            score += 0.3

        # Points for having signature
        if definition.get("signature"):
            score += 0.2

        # Points for having kind
        if definition.get("kind"):
            score += 0.1

        # Points for having span information
        if definition.get("span"):
            score += 0.1

        # Points for having language
        if definition.get("language"):
            score += 0.1

        # Base points for existence
        score += 0.2

        return score

    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        return {
            "total_aggregations": self._total_aggregations,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0
            ),
            "cached_results": len(self._result_cache),
            "cache_enabled": self.cache_enabled,
            "strategy": type(self.strategy).__name__,
            "ranking_criteria": self.ranking_criteria,
        }

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._result_cache.clear()
        self._stats_cache.clear()

    def configure(
        self,
        strategy: Optional[IAggregationStrategy] = None,
        ranking_criteria: Optional[RankingCriteria] = None,
        cache_enabled: Optional[bool] = None,
        cache_timeout: Optional[float] = None,
    ) -> None:
        """Configure aggregator settings.

        Args:
            strategy: New aggregation strategy
            ranking_criteria: New ranking criteria
            cache_enabled: Enable/disable caching
            cache_timeout: New cache timeout
        """
        if strategy is not None:
            self.strategy = strategy
            self.clear_cache()  # Clear cache when strategy changes

        if ranking_criteria is not None:
            self.ranking_criteria = ranking_criteria
            self.clear_cache()  # Clear cache when criteria changes

        if cache_enabled is not None:
            self.cache_enabled = cache_enabled
            if not cache_enabled:
                self.clear_cache()

        if cache_timeout is not None:
            self.cache_timeout = cache_timeout
