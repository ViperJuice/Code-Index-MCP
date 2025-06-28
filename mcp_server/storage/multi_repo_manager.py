"""
Multi-Repository Search Support System

This module manages multiple repository indexes and enables efficient
cross-repository code search operations.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.repository_registry import RepositoryRegistry

logger = logging.getLogger(__name__)


@dataclass
class RepositoryInfo:
    """Information about a registered repository."""
    repository_id: str
    name: str
    path: Path
    index_path: Path
    language_stats: Dict[str, int]
    total_files: int
    total_symbols: int
    indexed_at: datetime
    active: bool = True
    priority: int = 0  # Higher priority repos searched first


@dataclass
class CrossRepoSearchResult:
    """Result from cross-repository search."""
    repository_id: str
    repository_name: str
    results: List[Dict[str, Any]]
    search_time: float
    error: Optional[str] = None


class MultiRepositoryManager:
    """
    Manages multiple repository indexes for cross-repository search.
    
    Features:
    - Repository registration and discovery
    - Priority-based search ordering
    - Parallel search execution
    - Result aggregation and ranking
    - Repository health monitoring
    """
    
    def __init__(self,
                 central_index_path: Optional[Path] = None,
                 max_workers: int = 4):
        """
        Initialize the multi-repository manager.
        
        Args:
            central_index_path: Path to central repository registry
            max_workers: Maximum parallel search workers
        """
        self.central_index_path = central_index_path or self._get_default_registry_path()
        self.max_workers = max_workers
        
        # Repository registry
        self.registry = RepositoryRegistry(self.central_index_path)
        
        # Cached repository connections
        self._connections: Dict[str, SQLiteStore] = {}
        
        # Search statistics
        self._search_stats = {
            'total_searches': 0,
            'total_repositories_searched': 0,
            'average_search_time': 0.0,
            'cache_hits': 0
        }
        
        logger.info(
            f"Multi-repository manager initialized with "
            f"registry at {self.central_index_path}"
        )
        
    def _get_default_registry_path(self) -> Path:
        """Get default path for repository registry."""
        # Check environment variable
        env_path = os.environ.get('MCP_REPO_REGISTRY')
        if env_path:
            return Path(env_path)
            
        # Default to ~/.mcp/repository_registry.json
        home = Path.home()
        mcp_dir = home / '.mcp'
        mcp_dir.mkdir(exist_ok=True)
        
        return mcp_dir / 'repository_registry.json'
        
    def register_repository(self,
                          repository_path: Path,
                          name: Optional[str] = None,
                          priority: int = 0) -> RepositoryInfo:
        """
        Register a repository for multi-repository search.
        
        Args:
            repository_path: Path to repository
            name: Optional display name
            priority: Search priority (higher = searched first)
            
        Returns:
            RepositoryInfo for the registered repository
        """
        # Discover index
        discovery = IndexDiscovery(repository_path)
        index_path = discovery.get_local_index_path()
        
        if not index_path:
            raise ValueError(f"No index found for repository at {repository_path}")
            
        # Generate repository ID
        repo_id = self._generate_repository_id(repository_path)
        
        # Get repository statistics
        stats = self._analyze_repository(index_path)
        
        # Create repository info
        repo_info = RepositoryInfo(
            repository_id=repo_id,
            name=name or repository_path.name,
            path=repository_path,
            index_path=index_path,
            language_stats=stats['languages'],
            total_files=stats['total_files'],
            total_symbols=stats['total_symbols'],
            indexed_at=datetime.now(),
            priority=priority
        )
        
        # Register with registry
        self.registry.register(repo_info)
        
        logger.info(
            f"Registered repository '{repo_info.name}' "
            f"({repo_info.total_files} files, {repo_info.total_symbols} symbols)"
        )
        
        return repo_info
        
    def _generate_repository_id(self, repository_path: Path) -> str:
        """Generate unique ID for repository."""
        # Try to get git remote URL
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=repository_path,
                capture_output=True,
                text=True,
                check=True
            )
            url = result.stdout.strip()
            return hashlib.sha256(url.encode()).hexdigest()[:16]
        except:
            # Fall back to path hash
            path_str = str(repository_path.absolute())
            return hashlib.sha256(path_str.encode()).hexdigest()[:16]
            
    def _analyze_repository(self, index_path: Path) -> Dict[str, Any]:
        """Analyze repository index for statistics."""
        stats = {
            'languages': {},
            'total_files': 0,
            'total_symbols': 0
        }
        
        try:
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            
            # Count files by language
            cursor.execute("""
                SELECT language, COUNT(*) 
                FROM files 
                WHERE is_deleted = 0 OR is_deleted IS NULL
                GROUP BY language
            """)
            
            for language, count in cursor:
                if language:
                    stats['languages'][language] = count
                    stats['total_files'] += count
                    
            # Count symbols
            cursor.execute("""
                SELECT COUNT(*) FROM symbols
                WHERE is_deleted = 0 OR is_deleted IS NULL
            """)
            stats['total_symbols'] = cursor.fetchone()[0]
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            
        return stats
        
    def unregister_repository(self, repository_id: str):
        """
        Unregister a repository from multi-repository search.
        
        Args:
            repository_id: ID of repository to unregister
        """
        # Remove from registry
        self.registry.unregister(repository_id)
        
        # Close any cached connection
        if repository_id in self._connections:
            self._connections[repository_id].close()
            del self._connections[repository_id]
            
        logger.info(f"Unregistered repository {repository_id}")
        
    def list_repositories(self, active_only: bool = True) -> List[RepositoryInfo]:
        """
        List all registered repositories.
        
        Args:
            active_only: Only return active repositories
            
        Returns:
            List of repository information
        """
        repos = self.registry.list_all()
        
        if active_only:
            repos = [r for r in repos if r.active]
            
        # Sort by priority descending, then by name
        repos.sort(key=lambda r: (-r.priority, r.name))
        
        return repos
        
    def get_repository_info(self, repository_id: str) -> Optional[RepositoryInfo]:
        """Get information about a specific repository."""
        return self.registry.get(repository_id)
        
    def _get_connection(self, repository_id: str) -> Optional[SQLiteStore]:
        """Get cached connection to repository index."""
        if repository_id in self._connections:
            return self._connections[repository_id]
            
        # Get repository info
        repo_info = self.registry.get(repository_id)
        if not repo_info or not repo_info.active:
            return None
            
        # Create connection
        try:
            store = SQLiteStore(str(repo_info.index_path))
            self._connections[repository_id] = store
            return store
        except Exception as e:
            logger.error(f"Failed to connect to repository {repository_id}: {e}")
            return None
            
    async def search_symbol(self,
                          query: str,
                          repository_ids: Optional[List[str]] = None,
                          language: Optional[str] = None,
                          limit: int = 50) -> List[CrossRepoSearchResult]:
        """
        Search for symbols across multiple repositories.
        
        Args:
            query: Symbol name or pattern to search
            repository_ids: Specific repositories to search (None = all)
            language: Filter by programming language
            limit: Maximum results per repository
            
        Returns:
            List of cross-repository search results
        """
        start_time = datetime.now()
        
        # Get repositories to search
        if repository_ids:
            repos = [self.registry.get(rid) for rid in repository_ids]
            repos = [r for r in repos if r and r.active]
        else:
            repos = self.list_repositories(active_only=True)
            
        if not repos:
            logger.warning("No repositories to search")
            return []
            
        # Update statistics
        self._search_stats['total_searches'] += 1
        self._search_stats['total_repositories_searched'] += len(repos)
        
        # Execute searches in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit search tasks
            future_to_repo = {
                executor.submit(
                    self._search_repository,
                    repo.repository_id,
                    query,
                    language,
                    limit
                ): repo
                for repo in repos
            }
            
            # Collect results
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Search failed for {repo.name}: {e}")
                    results.append(CrossRepoSearchResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        results=[],
                        search_time=0.0,
                        error=str(e)
                    ))
                    
        # Update average search time
        total_time = (datetime.now() - start_time).total_seconds()
        self._update_search_stats(total_time)
        
        # Sort by repository priority
        repo_priority = {r.repository_id: r.priority for r in repos}
        results.sort(key=lambda r: -repo_priority.get(r.repository_id, 0))
        
        logger.info(
            f"Searched {len(repos)} repositories for '{query}' "
            f"in {total_time:.2f}s, found {sum(len(r.results) for r in results)} results"
        )
        
        return results
        
    def _search_repository(self,
                         repository_id: str,
                         query: str,
                         language: Optional[str],
                         limit: int) -> Optional[CrossRepoSearchResult]:
        """Search a single repository."""
        start_time = datetime.now()
        
        # Get connection
        store = self._get_connection(repository_id)
        if not store:
            return None
            
        # Get repository info
        repo_info = self.registry.get(repository_id)
        if not repo_info:
            return None
            
        try:
            # Build search query
            conditions = ["name LIKE ?"]
            params = [f"%{query}%"]
            
            if language:
                conditions.append("language = ?")
                params.append(language)
                
            where_clause = " AND ".join(conditions)
            
            # Execute search
            results = store.search_symbols(
                where_clause=where_clause,
                params=params,
                limit=limit
            )
            
            # Convert results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'symbol': result['name'],
                    'type': result['type'],
                    'language': result['language'],
                    'file': result['file_path'],
                    'line': result['line'],
                    'repository': repo_info.name,
                    'repository_id': repository_id
                })
                
            search_time = (datetime.now() - start_time).total_seconds()
            
            return CrossRepoSearchResult(
                repository_id=repository_id,
                repository_name=repo_info.name,
                results=formatted_results,
                search_time=search_time
            )
            
        except Exception as e:
            logger.error(f"Error searching repository {repository_id}: {e}")
            return CrossRepoSearchResult(
                repository_id=repository_id,
                repository_name=repo_info.name,
                results=[],
                search_time=0.0,
                error=str(e)
            )
            
    async def search_code(self,
                        query: str,
                        repository_ids: Optional[List[str]] = None,
                        file_pattern: Optional[str] = None,
                        limit: int = 50) -> List[CrossRepoSearchResult]:
        """
        Search for code content across repositories using BM25.
        
        Args:
            query: Code pattern to search
            repository_ids: Specific repositories to search
            file_pattern: File pattern filter (e.g., "*.py")
            limit: Maximum results per repository
            
        Returns:
            List of cross-repository search results
        """
        start_time = datetime.now()
        
        # Get repositories to search
        if repository_ids:
            repos = [self.registry.get(rid) for rid in repository_ids]
            repos = [r for r in repos if r and r.active]
        else:
            repos = self.list_repositories(active_only=True)
        
        if not repos:
            logger.warning("No repositories to search")
            return []
        
        logger.info(f"Code search for '{query}' across {len(repos)} repositories")
        
        # Update statistics
        self._search_stats['total_searches'] += 1
        self._search_stats['total_repositories_searched'] += len(repos)
        
        # Search in parallel using thread pool
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_repo = {
                executor.submit(
                    self._search_code_in_repository,
                    repo.repository_id,
                    query,
                    file_pattern,
                    limit
                ): repo
                for repo in repos
            }
            
            # Collect results
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Search failed in {repo.name}: {e}")
                    results.append(CrossRepoSearchResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        results=[],
                        search_time=0.0,
                        error=str(e)
                    ))
        
        # Sort by priority
        repo_priority = {r.repository_id: r.priority for r in repos}
        results.sort(key=lambda r: -repo_priority.get(r.repository_id, 0))
        
        total_time = (datetime.now() - start_time).total_seconds()
        self._update_search_stats(total_time)
        
        logger.info(
            f"Code search completed in {total_time:.2f}s, "
            f"found {sum(len(r.results) for r in results)} results"
        )
        
        return results
        
    def _search_code_in_repository(self,
                                  repository_id: str,
                                  query: str,
                                  file_pattern: Optional[str],
                                  limit: int) -> Optional[CrossRepoSearchResult]:
        """Search code content in a single repository using BM25."""
        start_time = datetime.now()
        
        store = self._get_connection(repository_id)
        if not store:
            return None
        
        repo_info = self.registry.get(repository_id)
        if not repo_info:
            return None
        
        try:
            # Use BM25 search on the appropriate table
            # Try both bm25_content and fts_code tables
            bm25_results = []
            
            # First try bm25_content table
            try:
                bm25_results = store.search_bm25(query, table='bm25_content', limit=limit)
            except Exception as e:
                logger.debug(f"bm25_content search failed, trying fts_code: {e}")
                # Fall back to fts_code table
                try:
                    bm25_results = store.search_bm25(query, table='fts_code', limit=limit)
                except Exception as e2:
                    logger.warning(f"Both BM25 tables failed for {repository_id}: {e2}")
            
            # Format results
            formatted_results = []
            for result in bm25_results:
                formatted_results.append({
                    'file': result.get('filepath', result.get('file_path', '')),
                    'line': result.get('line', 0),
                    'snippet': result.get('snippet', ''),
                    'score': result.get('score', 0.0),
                    'repository': repo_info.name,
                    'repository_id': repository_id
                })
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            return CrossRepoSearchResult(
                repository_id=repository_id,
                repository_name=repo_info.name,
                results=formatted_results,
                search_time=search_time
            )
            
        except Exception as e:
            logger.error(f"BM25 search failed in {repository_id}: {e}")
            return CrossRepoSearchResult(
                repository_id=repository_id,
                repository_name=repo_info.name,
                results=[],
                search_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    def _update_search_stats(self, search_time: float):
        """Update search statistics."""
        stats = self._search_stats
        
        # Update average search time
        total_searches = stats['total_searches']
        current_avg = stats['average_search_time']
        
        # Incremental average calculation
        new_avg = ((current_avg * (total_searches - 1)) + search_time) / total_searches
        stats['average_search_time'] = new_avg
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get multi-repository search statistics."""
        repos = self.list_repositories()
        
        # Aggregate repository statistics
        total_files = sum(r.total_files for r in repos)
        total_symbols = sum(r.total_symbols for r in repos)
        
        # Language distribution
        all_languages = {}
        for repo in repos:
            for lang, count in repo.language_stats.items():
                all_languages[lang] = all_languages.get(lang, 0) + count
                
        return {
            'repositories': {
                'total': len(repos),
                'active': len([r for r in repos if r.active]),
                'total_files': total_files,
                'total_symbols': total_symbols
            },
            'languages': all_languages,
            'search_stats': self._search_stats.copy(),
            'cache': {
                'connections': len(self._connections)
            }
        }
        
    def health_check(self) -> Dict[str, Any]:
        """Check health of all registered repositories."""
        health_status = {
            'healthy': 0,
            'unhealthy': 0,
            'repositories': []
        }
        
        for repo in self.list_repositories():
            repo_health = {
                'repository_id': repo.repository_id,
                'name': repo.name,
                'status': 'healthy',
                'issues': []
            }
            
            # Check index file exists
            if not repo.index_path.exists():
                repo_health['status'] = 'unhealthy'
                repo_health['issues'].append('Index file not found')
                
            # Check repository path exists
            if not repo.path.exists():
                repo_health['status'] = 'unhealthy'
                repo_health['issues'].append('Repository path not found')
                
            # Try to connect
            try:
                conn = self._get_connection(repo.repository_id)
                if not conn:
                    repo_health['status'] = 'unhealthy'
                    repo_health['issues'].append('Cannot connect to index')
            except Exception as e:
                repo_health['status'] = 'unhealthy'
                repo_health['issues'].append(f'Connection error: {str(e)}')
                
            # Update counters
            if repo_health['status'] == 'healthy':
                health_status['healthy'] += 1
            else:
                health_status['unhealthy'] += 1
                
            health_status['repositories'].append(repo_health)
            
        return health_status
        
    def optimize_indexes(self):
        """Optimize all repository indexes for better performance."""
        optimized = 0
        
        for repo in self.list_repositories():
            try:
                conn = sqlite3.connect(str(repo.index_path))
                cursor = conn.cursor()
                
                # Run VACUUM to optimize
                cursor.execute("VACUUM")
                
                # Analyze for query optimization
                cursor.execute("ANALYZE")
                
                conn.close()
                optimized += 1
                
                logger.info(f"Optimized index for {repo.name}")
                
            except Exception as e:
                logger.error(f"Failed to optimize {repo.name}: {e}")
                
        logger.info(f"Optimized {optimized} repository indexes")
        
    def close(self):
        """Close all connections and save registry."""
        # Close all cached connections
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
        
        # Save registry
        self.registry.save()
        
        logger.info("Multi-repository manager closed")


# Singleton instance
_manager_instance: Optional[MultiRepositoryManager] = None


def get_multi_repo_manager(
    central_index_path: Optional[Path] = None
) -> MultiRepositoryManager:
    """
    Get the singleton multi-repository manager.
    
    Args:
        central_index_path: Optional path to registry
        
    Returns:
        MultiRepositoryManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = MultiRepositoryManager(central_index_path)
        
    return _manager_instance