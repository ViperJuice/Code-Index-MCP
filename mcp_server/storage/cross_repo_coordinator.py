"""
Cross-Repository Search Coordinator

This module provides unified search capabilities across multiple repositories,
with intelligent result aggregation, deduplication, and ranking.
"""

import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# Temporarily remove dependencies until imports are fixed
# from mcp_server.plugins.memory_aware_manager import get_memory_aware_manager
# from mcp_server.plugins.repository_plugin_loader import RepositoryPluginLoader
from mcp_server.storage.multi_repo_manager import (
    CrossRepoSearchResult,
    MultiRepositoryManager,
    RepositoryInfo,
)
from mcp_server.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


@dataclass
class SearchScope:
    """Defines the scope for cross-repository search."""

    repositories: Optional[List[str]] = None  # Specific repo IDs, None = all
    languages: Optional[List[str]] = None  # Filter by languages
    file_types: Optional[List[str]] = None  # Filter by file extensions
    max_repositories: int = 10  # Limit number of repos searched
    priority_order: bool = True  # Use repository priority ordering


@dataclass
class AggregatedResult:
    """Aggregated search result from multiple repositories."""

    query: str
    total_results: int
    repositories_searched: int
    search_time: float
    results: List[Dict[str, Any]]
    repository_stats: Dict[str, int]  # repo_id -> result count
    deduplication_stats: Dict[str, int]  # Stats on duplicate removal


class CrossRepositorySearchCoordinator:
    """
    Coordinates search operations across multiple repositories.

    Features:
    - Unified search interface for multiple repositories
    - Intelligent result aggregation and deduplication
    - Repository priority and filtering
    - Parallel search execution for performance
    - Result ranking across repositories
    """

    def __init__(
        self,
        multi_repo_manager: Optional[MultiRepositoryManager] = None,
        max_workers: int = 4,
        default_result_limit: int = 100,
    ):
        """
        Initialize cross-repository search coordinator.

        Args:
            multi_repo_manager: Repository manager instance
            max_workers: Maximum parallel workers for search
            default_result_limit: Default limit for search results
        """
        self.multi_repo_manager = multi_repo_manager or MultiRepositoryManager()
        self.max_workers = max_workers
        self.default_result_limit = default_result_limit
        # Temporarily disable until imports are fixed
        # self.memory_manager = get_memory_aware_manager()
        # self.plugin_loader = RepositoryPluginLoader()

        # Cache for repository search capabilities
        self._repo_capabilities_cache: Dict[str, Set[str]] = {}
        self._last_cache_update = datetime.now()

        logger.info(f"CrossRepositorySearchCoordinator initialized with {max_workers} workers")

    async def search_symbol(
        self, symbol: str, scope: Optional[SearchScope] = None
    ) -> AggregatedResult:
        """
        Search for a symbol across multiple repositories.

        Args:
            symbol: Symbol name to search for
            scope: Search scope configuration

        Returns:
            Aggregated search results
        """
        start_time = time.time()
        scope = scope or SearchScope()

        logger.info(f"Starting cross-repo symbol search for: {symbol}")

        # Get target repositories
        target_repos = await self._get_target_repositories(scope)
        if not target_repos:
            return AggregatedResult(
                query=symbol,
                total_results=0,
                repositories_searched=0,
                search_time=time.time() - start_time,
                results=[],
                repository_stats={},
                deduplication_stats={},
            )

        # Execute parallel searches
        search_results = await self._execute_parallel_symbol_search(symbol, target_repos, scope)

        # Aggregate and deduplicate results
        aggregated = await self._aggregate_symbol_results(symbol, search_results, start_time)

        logger.info(
            f"Cross-repo symbol search completed: {aggregated.total_results} results from {aggregated.repositories_searched} repositories"
        )
        return aggregated

    async def search_code(
        self,
        query: str,
        scope: Optional[SearchScope] = None,
        semantic: bool = False,
        limit: int = None,
    ) -> AggregatedResult:
        """
        Search for code patterns across multiple repositories.

        Args:
            query: Search query/pattern
            scope: Search scope configuration
            semantic: Whether to use semantic search
            limit: Maximum results to return

        Returns:
            Aggregated search results
        """
        start_time = time.time()
        scope = scope or SearchScope()
        limit = limit or self.default_result_limit

        logger.info(f"Starting cross-repo code search for: {query} (semantic={semantic})")

        # Get target repositories
        target_repos = await self._get_target_repositories(scope)
        if not target_repos:
            return AggregatedResult(
                query=query,
                total_results=0,
                repositories_searched=0,
                search_time=time.time() - start_time,
                results=[],
                repository_stats={},
                deduplication_stats={},
            )

        # Execute parallel searches
        search_results = await self._execute_parallel_code_search(
            query, target_repos, scope, semantic, limit
        )

        # Aggregate and deduplicate results
        aggregated = await self._aggregate_code_results(query, search_results, start_time, limit)

        logger.info(
            f"Cross-repo code search completed: {aggregated.total_results} results from {aggregated.repositories_searched} repositories"
        )
        return aggregated

    async def _get_target_repositories(self, scope: SearchScope) -> List[RepositoryInfo]:
        """Get list of repositories to search based on scope."""
        all_repos = self.multi_repo_manager.list_repositories(active_only=True)

        # Filter by specific repositories if specified
        if scope.repositories:
            all_repos = [repo for repo in all_repos if repo.repository_id in scope.repositories]

        # Filter by languages if specified
        if scope.languages:
            filtered_repos = []
            for repo in all_repos:
                repo_languages = set(repo.language_stats.keys())
                if any(lang in repo_languages for lang in scope.languages):
                    filtered_repos.append(repo)
            all_repos = filtered_repos

        # Sort by priority if enabled
        if scope.priority_order:
            all_repos.sort(key=lambda r: r.priority, reverse=True)

        # Limit number of repositories
        if scope.max_repositories:
            all_repos = all_repos[: scope.max_repositories]

        logger.debug(f"Target repositories: {len(all_repos)} repos selected")
        return all_repos

    async def _execute_parallel_symbol_search(
        self, symbol: str, repositories: List[RepositoryInfo], scope: SearchScope
    ) -> List[CrossRepoSearchResult]:
        """Execute symbol searches across repositories in parallel."""
        _ = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for repo in repositories:
                future = executor.submit(self._search_symbol_in_repository, symbol, repo, scope)
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30 second timeout per repo
                    if result and result.results:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Symbol search failed for repository: {e}")

            return results

    async def _execute_parallel_code_search(
        self,
        query: str,
        repositories: List[RepositoryInfo],
        scope: SearchScope,
        semantic: bool,
        limit: int,
    ) -> List[CrossRepoSearchResult]:
        """Execute code searches across repositories in parallel."""
        per_repo_limit = max(10, limit // len(repositories)) if repositories else limit

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for repo in repositories:
                future = executor.submit(
                    self._search_code_in_repository, query, repo, scope, semantic, per_repo_limit
                )
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)  # 60 second timeout per repo
                    if result and result.results:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Code search failed for repository: {e}")

            return results

    def _search_symbol_in_repository(
        self, symbol: str, repo: RepositoryInfo, scope: SearchScope
    ) -> Optional[CrossRepoSearchResult]:
        """Search for symbol in a single repository."""
        start_time = time.time()

        try:
            # Load repository store
            store = SQLiteStore(str(repo.index_path))

            # Execute symbol search
            results = store.search_symbols(symbol, limit=50)

            search_time = time.time() - start_time

            return CrossRepoSearchResult(
                repository_id=repo.repository_id,
                repository_name=repo.name,
                results=results,
                search_time=search_time,
            )

        except Exception as e:
            logger.error(f"Symbol search failed in {repo.name}: {e}")
            return CrossRepoSearchResult(
                repository_id=repo.repository_id,
                repository_name=repo.name,
                results=[],
                search_time=time.time() - start_time,
                error=str(e),
            )

    def _search_code_in_repository(
        self, query: str, repo: RepositoryInfo, scope: SearchScope, semantic: bool, limit: int
    ) -> Optional[CrossRepoSearchResult]:
        """Search for code in a single repository."""
        start_time = time.time()

        try:
            # Load repository store
            store = SQLiteStore(str(repo.index_path))

            # Execute code search
            if semantic:
                results = store.semantic_search(query, limit=limit)
            else:
                results = store.search_content(query, limit=limit)

            # Apply file type filters if specified
            if scope.file_types:
                filtered_results = []
                for result in results:
                    file_path = result.get("file_path", "")
                    if any(file_path.endswith(ext) for ext in scope.file_types):
                        filtered_results.append(result)
                results = filtered_results

            search_time = time.time() - start_time

            return CrossRepoSearchResult(
                repository_id=repo.repository_id,
                repository_name=repo.name,
                results=results,
                search_time=search_time,
            )

        except Exception as e:
            logger.error(f"Code search failed in {repo.name}: {e}")
            return CrossRepoSearchResult(
                repository_id=repo.repository_id,
                repository_name=repo.name,
                results=[],
                search_time=time.time() - start_time,
                error=str(e),
            )

    async def _aggregate_symbol_results(
        self, symbol: str, search_results: List[CrossRepoSearchResult], start_time: float
    ) -> AggregatedResult:
        """Aggregate and deduplicate symbol search results."""
        all_results = []
        repository_stats = {}
        seen_signatures = set()
        dedup_stats = {"original_count": 0, "duplicates_removed": 0}

        for search_result in search_results:
            repository_stats[search_result.repository_id] = len(search_result.results)
            dedup_stats["original_count"] += len(search_result.results)

            for result in search_result.results:
                # Create signature for deduplication
                signature = self._create_symbol_signature(result)

                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    # Add repository context to result
                    result["repository_id"] = search_result.repository_id
                    result["repository_name"] = search_result.repository_name
                    all_results.append(result)
                else:
                    dedup_stats["duplicates_removed"] += 1

        # Sort by relevance (exact matches first, then by repository priority)
        all_results.sort(
            key=lambda r: (
                0 if r.get("symbol", "").lower() == symbol.lower() else 1,
                -repository_stats.get(r["repository_id"], 0),
            )
        )

        return AggregatedResult(
            query=symbol,
            total_results=len(all_results),
            repositories_searched=len(search_results),
            search_time=time.time() - start_time,
            results=all_results,
            repository_stats=repository_stats,
            deduplication_stats=dedup_stats,
        )

    async def _aggregate_code_results(
        self, query: str, search_results: List[CrossRepoSearchResult], start_time: float, limit: int
    ) -> AggregatedResult:
        """Aggregate and deduplicate code search results."""
        all_results = []
        repository_stats = {}
        seen_content_hashes = set()
        dedup_stats = {"original_count": 0, "duplicates_removed": 0}

        for search_result in search_results:
            repository_stats[search_result.repository_id] = len(search_result.results)
            dedup_stats["original_count"] += len(search_result.results)

            for result in search_result.results:
                # Create hash for deduplication based on content
                content_hash = self._create_content_hash(result)

                if content_hash not in seen_content_hashes:
                    seen_content_hashes.add(content_hash)
                    # Add repository context to result
                    result["repository_id"] = search_result.repository_id
                    result["repository_name"] = search_result.repository_name
                    all_results.append(result)
                else:
                    dedup_stats["duplicates_removed"] += 1

        # Sort by relevance score if available, otherwise by repository stats
        all_results.sort(
            key=lambda r: (-r.get("score", 0), -repository_stats.get(r["repository_id"], 0))
        )

        # Apply limit
        if limit and len(all_results) > limit:
            all_results = all_results[:limit]

        return AggregatedResult(
            query=query,
            total_results=len(all_results),
            repositories_searched=len(search_results),
            search_time=time.time() - start_time,
            results=all_results,
            repository_stats=repository_stats,
            deduplication_stats=dedup_stats,
        )

    def _create_symbol_signature(self, result: Dict[str, Any]) -> str:
        """Create a signature for symbol deduplication."""
        symbol = result.get("symbol", "")
        file_path = result.get("file_path", "")
        line_number = result.get("line_number", 0)

        # Create signature based on symbol name and relative file path
        # This allows same symbols in different repos but deduplicates identical files
        relative_path = file_path.split("/")[-3:] if "/" in file_path else [file_path]
        signature_data = f"{symbol}::{'/'.join(relative_path)}::{line_number}"

        return hashlib.md5(signature_data.encode()).hexdigest()

    def _create_content_hash(self, result: Dict[str, Any]) -> str:
        """Create a hash for content deduplication."""
        content = result.get("content", "")
        file_path = result.get("file_path", "")

        # Create hash based on content and relative file path
        relative_path = file_path.split("/")[-2:] if "/" in file_path else [file_path]
        hash_data = f"{content[:200]}::{'/'.join(relative_path)}"

        return hashlib.md5(hash_data.encode()).hexdigest()

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Get statistics about cross-repository search capabilities."""
        repos = self.multi_repo_manager.list_repositories(active_only=True)

        stats = {
            "total_repositories": len(repos),
            "total_files": sum(repo.total_files for repo in repos),
            "total_symbols": sum(repo.total_symbols for repo in repos),
            "languages": set(),
            "repository_details": [],
        }

        for repo in repos:
            stats["languages"].update(repo.language_stats.keys())
            stats["repository_details"].append(
                {
                    "id": repo.repository_id,
                    "name": repo.name,
                    "files": repo.total_files,
                    "symbols": repo.total_symbols,
                    "languages": list(repo.language_stats.keys()),
                    "priority": repo.priority,
                }
            )

        stats["languages"] = sorted(list(stats["languages"]))

        return stats


# Singleton instance
_coordinator_instance = None


def get_cross_repo_coordinator() -> CrossRepositorySearchCoordinator:
    """Get the global cross-repository search coordinator instance."""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = CrossRepositorySearchCoordinator()
    return _coordinator_instance
