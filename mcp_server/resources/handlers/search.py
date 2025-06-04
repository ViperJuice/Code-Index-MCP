"""
Search resource handler for code://search URIs.

Provides dynamic search results as resources with support for:
- Text search (exact, fuzzy, phrase, boolean)
- Semantic search using embeddings
- Regex pattern matching
- Result ranking and scoring
- Pagination for large result sets
- Query result caching

URI Format:
- code://search?q=<query>&type=<search_type>&page=<page>&size=<page_size>
- code://search/<search_id> for cached search results

Search Types:
- text: Full-text search (default)
- fuzzy: Fuzzy string matching
- semantic: Vector-based semantic search
- regex: Regular expression pattern matching
- symbol: Symbol-specific search
"""

import json
import logging
import re
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from ...interfaces.mcp_interfaces import IMCPResource
from ...interfaces.dispatcher_interfaces import IDispatcher, DispatchRequest
from ...interfaces.storage_interfaces import IStorageEngine, ITextSearcher
from ...interfaces.cache_interfaces import ICacheManager, CacheKey
from ...interfaces.plugin_interfaces import SearchResult, SymbolDefinition
from ...interfaces.shared_interfaces import Result, Error
from ..registry import ResourceHandler, ResourceFilter, PaginationOptions

logger = logging.getLogger(__name__)


@dataclass
class SearchOptions:
    """Search configuration options."""
    search_type: str = "text"  # text, fuzzy, semantic, regex, symbol
    case_sensitive: bool = False
    whole_words: bool = False
    include_files: Optional[List[str]] = None
    exclude_files: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    max_results: int = 1000
    min_score: float = 0.0
    context_lines: int = 2
    highlight_matches: bool = True


@dataclass
class SearchMetadata:
    """Metadata for search results."""
    query: str
    search_type: str
    total_results: int
    execution_time: float
    timestamp: datetime
    options: SearchOptions
    page: int = 1
    page_size: int = 50


@dataclass 
class PaginatedSearchResults:
    """Paginated search results with metadata."""
    results: List[SearchResult]
    metadata: SearchMetadata
    total_pages: int
    has_next: bool
    has_previous: bool


class SearchResource(IMCPResource):
    """Resource representing search results."""
    
    def __init__(self, uri: str, results: PaginatedSearchResults):
        self.uri = uri
        self.results = results
    
    def get_uri(self) -> str:
        """Get the resource URI."""
        return self.uri
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get resource metadata."""
        return {
            "query": self.results.metadata.query,
            "search_type": self.results.metadata.search_type,
            "total_results": self.results.metadata.total_results,
            "execution_time": self.results.metadata.execution_time,
            "timestamp": self.results.metadata.timestamp.isoformat(),
            "page": self.results.metadata.page,
            "page_size": self.results.metadata.page_size,
            "total_pages": self.results.total_pages,
            "has_next": self.results.has_next,
            "has_previous": self.results.has_previous,
            "options": asdict(self.results.metadata.options)
        }


class SearchResourceHandler(ResourceHandler):
    """Handler for search-related resources."""
    
    def __init__(self, 
                 dispatcher: IDispatcher,
                 storage: IStorageEngine,
                 cache_manager: Optional[ICacheManager] = None):
        """
        Initialize search resource handler.
        
        Args:
            dispatcher: Dispatcher for plugin coordination
            storage: Storage engine for data access
            cache_manager: Optional cache for search results
        """
        super().__init__("code://search")
        self.dispatcher = dispatcher
        self.storage = storage
        self.cache = cache_manager
        self.search_cache_ttl = 3600  # 1 hour default TTL
        
    async def can_handle(self, uri: str) -> bool:
        """Check if this handler can handle the given URI."""
        return uri.startswith("code://search")
    
    async def get_resource(self, uri: str) -> Optional[IMCPResource]:
        """Get search resource for the given URI."""
        try:
            parsed = urlparse(uri)
            
            # Handle cached search results by ID
            if len(parsed.path) > 1:  # /search_id format
                search_id = parsed.path[1:]  # Remove leading /
                return await self._get_cached_search(search_id)
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            query = query_params.get('q', [''])[0]
            
            if not query:
                return None
            
            # Extract search options
            options = self._parse_search_options(query_params)
            page = int(query_params.get('page', ['1'])[0])
            page_size = int(query_params.get('size', ['50'])[0])
            
            # Check cache first
            if self.cache:
                cached_results = await self._get_cached_results(query, options, page, page_size)
                if cached_results:
                    return SearchResource(uri, cached_results)
            
            # Perform search
            search_results = await self._perform_search(query, options)
            
            # Apply pagination
            paginated_results = self._paginate_results(search_results, query, options, page, page_size)
            
            # Cache results
            if self.cache:
                await self._cache_results(query, options, page, page_size, paginated_results)
            
            return SearchResource(uri, paginated_results)
            
        except Exception as e:
            logger.error(f"Error handling search resource {uri}: {e}")
            return None
    
    async def list_resources(self, filter_options: Optional[ResourceFilter] = None) -> List[IMCPResource]:
        """List available search resources (recent searches)."""
        if not self.cache:
            return []
        
        try:
            # Get recent search IDs from cache
            recent_searches = await self._get_recent_searches()
            resources = []
            
            for search_id in recent_searches:
                cached_result = await self._get_cached_search(search_id)
                if cached_result:
                    uri = f"code://search/{search_id}"
                    resources.append(SearchResource(uri, cached_result))
            
            return resources
            
        except Exception as e:
            logger.error(f"Error listing search resources: {e}")
            return []
    
    def _parse_search_options(self, query_params: Dict[str, List[str]]) -> SearchOptions:
        """Parse search options from query parameters."""
        return SearchOptions(
            search_type=query_params.get('type', ['text'])[0],
            case_sensitive=query_params.get('case', ['false'])[0].lower() == 'true',
            whole_words=query_params.get('words', ['false'])[0].lower() == 'true',
            include_files=query_params.get('include', [None])[0].split(',') if query_params.get('include') else None,
            exclude_files=query_params.get('exclude', [None])[0].split(',') if query_params.get('exclude') else None,
            languages=query_params.get('lang', [None])[0].split(',') if query_params.get('lang') else None,
            max_results=int(query_params.get('max', ['1000'])[0]),
            min_score=float(query_params.get('min_score', ['0.0'])[0]),
            context_lines=int(query_params.get('context', ['2'])[0]),
            highlight_matches=query_params.get('highlight', ['true'])[0].lower() == 'true'
        )

    
    async def _perform_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform the actual search using appropriate strategy."""
        start_time = datetime.now()
        
        try:
            if options.search_type == "text":
                results = await self._text_search(query, options)
            elif options.search_type == "fuzzy":
                results = await self._fuzzy_search(query, options)
            elif options.search_type == "semantic":
                results = await self._semantic_search(query, options)
            elif options.search_type == "regex":
                results = await self._regex_search(query, options)
            elif options.search_type == "symbol":
                results = await self._symbol_search(query, options)
            else:
                # Default to text search
                results = await self._text_search(query, options)
            
            # Apply filtering and ranking
            results = self._filter_results(results, options)
            results = self._rank_results(results, query, options)
            
            # Limit results
            if len(results) > options.max_results:
                results = results[:options.max_results]
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing search '{query}': {e}")
            return []
    
    async def _text_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform text-based search."""
        try:
            # Create dispatch request for text search
            request = DispatchRequest(
                operation="search",
                file_path=None,
                content=None,
                query=query,
                symbol=None,
                context={
                    "search_type": "text",
                    "case_sensitive": options.case_sensitive,
                    "whole_words": options.whole_words,
                    "include_files": options.include_files,
                    "exclude_files": options.exclude_files,
                    "languages": options.languages,
                    "context_lines": options.context_lines
                },
                options=asdict(options)
            )
            
            # Dispatch to plugins
            result = await self.dispatcher.dispatch(request)
            
            if result.success and result.data:
                aggregated_result = result.data
                return aggregated_result.merged_result or []
            
            return []
            
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return []
    
    async def _fuzzy_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform fuzzy search."""
        try:
            # Create dispatch request for fuzzy search
            request = DispatchRequest(
                operation="fuzzy_search",
                file_path=None,
                content=None,
                query=query,
                symbol=None,
                context={
                    "search_type": "fuzzy",
                    "threshold": 0.6,  # Default fuzzy threshold
                    "include_files": options.include_files,
                    "exclude_files": options.exclude_files,
                    "languages": options.languages,
                    "context_lines": options.context_lines
                },
                options=asdict(options)
            )
            
            # Dispatch to plugins
            result = await self.dispatcher.dispatch(request)
            
            if result.success and result.data:
                aggregated_result = result.data
                return aggregated_result.merged_result or []
            
            return []
            
        except Exception as e:
            logger.error(f"Error in fuzzy search: {e}")
            return []
    
    async def _semantic_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        try:
            # Create dispatch request for semantic search
            request = DispatchRequest(
                operation="semantic_search",
                file_path=None,
                content=None,
                query=query,
                symbol=None,
                context={
                    "search_type": "semantic",
                    "embedding_model": "voyage-ai",  # Default model
                    "similarity_threshold": options.min_score,
                    "include_files": options.include_files,
                    "exclude_files": options.exclude_files,
                    "languages": options.languages,
                    "top_k": options.max_results
                },
                options=asdict(options)
            )
            
            # Dispatch to plugins
            result = await self.dispatcher.dispatch(request)
            
            if result.success and result.data:
                aggregated_result = result.data
                return aggregated_result.merged_result or []
            
            return []
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def _regex_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform regex pattern search."""
        try:
            # Validate regex pattern
            try:
                pattern = re.compile(query, 0 if options.case_sensitive else re.IGNORECASE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{query}': {e}")
                return []
            
            # Create dispatch request for regex search
            request = DispatchRequest(
                operation="regex_search",
                file_path=None,
                content=None,
                query=query,
                symbol=None,
                context={
                    "search_type": "regex",
                    "case_sensitive": options.case_sensitive,
                    "include_files": options.include_files,
                    "exclude_files": options.exclude_files,
                    "languages": options.languages,
                    "context_lines": options.context_lines
                },
                options=asdict(options)
            )
            
            # Dispatch to plugins
            result = await self.dispatcher.dispatch(request)
            
            if result.success and result.data:
                aggregated_result = result.data
                return aggregated_result.merged_result or []
            
            return []
            
        except Exception as e:
            logger.error(f"Error in regex search: {e}")
            return []
    
    async def _symbol_search(self, query: str, options: SearchOptions) -> List[SearchResult]:
        """Perform symbol-specific search."""
        try:
            # Create dispatch request for symbol search
            request = DispatchRequest(
                operation="search_symbols",
                file_path=None,
                content=None,
                query=None,
                symbol=query,
                context={
                    "search_type": "symbol",
                    "case_sensitive": options.case_sensitive,
                    "whole_words": options.whole_words,
                    "include_files": options.include_files,
                    "exclude_files": options.exclude_files,
                    "languages": options.languages,
                    "symbol_types": ["function", "class", "variable", "constant", "interface"]
                },
                options=asdict(options)
            )
            
            # Dispatch to plugins
            result = await self.dispatcher.dispatch(request)
            
            if result.success and result.data:
                aggregated_result = result.data
                # Convert symbol definitions to search results
                symbols = aggregated_result.merged_result or []
                return self._symbols_to_search_results(symbols, query)
            
            return []
            
        except Exception as e:
            logger.error(f"Error in symbol search: {e}")
            return []

    
    def _symbols_to_search_results(self, symbols: List[SymbolDefinition], query: str) -> List[SearchResult]:
        """Convert symbol definitions to search results."""
        results = []
        
        for symbol in symbols:
            # Calculate relevance score based on name match
            score = self._calculate_symbol_score(symbol.symbol, query)
            
            # Create snippet from symbol signature or docstring
            snippet = symbol.signature or symbol.symbol
            if symbol.docstring:
                snippet += f" - {symbol.docstring[:100]}..."
            
            result = SearchResult(
                file_path=symbol.file_path,
                line=symbol.line,
                column=symbol.column,
                snippet=snippet,
                match_type="symbol",
                score=score,
                context=symbol.scope
            )
            results.append(result)
        
        return results
    
    def _calculate_symbol_score(self, symbol_name: str, query: str) -> float:
        """Calculate relevance score for symbol match."""
        symbol_lower = symbol_name.lower()
        query_lower = query.lower()
        
        # Exact match gets highest score
        if symbol_lower == query_lower:
            return 1.0
        
        # Prefix match gets high score
        if symbol_lower.startswith(query_lower):
            return 0.9
        
        # Substring match gets medium score
        if query_lower in symbol_lower:
            return 0.7
        
        # Fuzzy match using simple similarity
        similarity = self._calculate_string_similarity(symbol_name, query)
        return similarity * 0.6
    
    def _calculate_string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        if not s1 or not s2:
            return 0.0
        
        # Simple Levenshtein-based similarity
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        
        # This is a simplified version - in production use a proper algorithm
        common_chars = sum(1 for c1, c2 in zip(s1.lower(), s2.lower()) if c1 == c2)
        return common_chars / max_len
    
    def _filter_results(self, results: List[SearchResult], options: SearchOptions) -> List[SearchResult]:
        """Filter search results based on options."""
        filtered = []
        
        for result in results:
            # Filter by minimum score
            if result.score < options.min_score:
                continue
            
            # Filter by file inclusion/exclusion
            if options.include_files:
                if not any(pattern in result.file_path for pattern in options.include_files):
                    continue
            
            if options.exclude_files:
                if any(pattern in result.file_path for pattern in options.exclude_files):
                    continue
            
            # Filter by languages (if we can determine file language)
            if options.languages:
                file_ext = Path(result.file_path).suffix.lower()
                # This would need a proper language detection mapping
                # For now, just check basic extensions
                language_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.java': 'java',
                    '.cpp': 'cpp',
                    '.c': 'c',
                    '.go': 'go',
                    '.rs': 'rust'
                }
                
                file_language = language_map.get(file_ext)
                if file_language and file_language not in options.languages:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _rank_results(self, results: List[SearchResult], query: str, options: SearchOptions) -> List[SearchResult]:
        """Rank search results by relevance."""
        # Sort by score (descending) and then by file path for consistency
        return sorted(results, key=lambda r: (-r.score, r.file_path, r.line))
    
    def _paginate_results(self, 
                         results: List[SearchResult], 
                         query: str, 
                         options: SearchOptions,
                         page: int, 
                         page_size: int) -> PaginatedSearchResults:
        """Paginate search results."""
        total_results = len(results)
        total_pages = (total_results + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]
        
        metadata = SearchMetadata(
            query=query,
            search_type=options.search_type,
            total_results=total_results,
            execution_time=0.0,  # Would be calculated in real implementation
            timestamp=datetime.now(),
            options=options,
            page=page,
            page_size=page_size
        )
        
        return PaginatedSearchResults(
            results=page_results,
            metadata=metadata,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )

    
    async def _get_cached_results(self, 
                                 query: str, 
                                 options: SearchOptions, 
                                 page: int, 
                                 page_size: int) -> Optional[PaginatedSearchResults]:
        """Get cached search results."""
        if not self.cache:
            return None
        
        try:
            cache_key = self._generate_cache_key(query, options, page, page_size)
            cached_data = await self.cache.get(cache_key.to_string())
            
            if cached_data:
                return PaginatedSearchResults(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached results: {e}")
            return None
    
    async def _cache_results(self, 
                           query: str, 
                           options: SearchOptions, 
                           page: int, 
                           page_size: int,
                           results: PaginatedSearchResults) -> None:
        """Cache search results."""
        if not self.cache:
            return
        
        try:
            cache_key = self._generate_cache_key(query, options, page, page_size)
            
            # Convert to dictionary for JSON serialization
            cache_data = {
                "results": [asdict(r) for r in results.results],
                "metadata": asdict(results.metadata),
                "total_pages": results.total_pages,
                "has_next": results.has_next,
                "has_previous": results.has_previous
            }
            
            await self.cache.set_with_options(
                cache_key.to_string(),
                cache_data,
                ttl=self.search_cache_ttl,
                tags=["search", f"query:{query}", f"type:{options.search_type}"]
            )
            
        except Exception as e:
            logger.error(f"Error caching results: {e}")
    
    def _generate_cache_key(self, 
                           query: str, 
                           options: SearchOptions, 
                           page: int, 
                           page_size: int) -> CacheKey:
        """Generate cache key for search results."""
        # Create deterministic parameters dict
        params = {
            "query": query,
            "search_type": options.search_type,
            "case_sensitive": options.case_sensitive,
            "whole_words": options.whole_words,
            "include_files": " < /dev/null | ".join(options.include_files or []),
            "exclude_files": "|".join(options.exclude_files or []),
            "languages": "|".join(options.languages or []),
            "min_score": options.min_score,
            "page": page,
            "page_size": page_size
        }
        
        return CacheKey(
            namespace="search",
            operation="query",
            parameters=params,
            version="v1"
        )
    
    async def _get_cached_search(self, search_id: str) -> Optional[PaginatedSearchResults]:
        """Get cached search by ID."""
        if not self.cache:
            return None
        
        try:
            cached_data = await self.cache.get(f"search:id:{search_id}")
            
            if cached_data:
                return PaginatedSearchResults(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached search {search_id}: {e}")
            return None
    
    async def _get_recent_searches(self) -> List[str]:
        """Get list of recent search IDs."""
        if not self.cache:
            return []
        
        try:
            # This would need to be implemented in the cache system
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent searches: {e}")
            return []


# Helper functions for search result processing

def highlight_matches(text: str, query: str, case_sensitive: bool = False) -> str:
    """Highlight search matches in text."""
    if not query or not text:
        return text
    
    flags = 0 if case_sensitive else re.IGNORECASE
    
    # Escape special regex characters in query
    escaped_query = re.escape(query)
    
    try:
        # Simple highlighting with <mark> tags
        highlighted = re.sub(
            f"({escaped_query})",
            r"<mark></mark>",
            text,
            flags=flags
        )
        return highlighted
    except Exception:
        return text


def extract_context_lines(file_content: str, line_number: int, context_lines: int = 2) -> str:
    """Extract context lines around a match."""
    lines = file_content.split('\n')
    start_line = max(0, line_number - context_lines - 1)
    start_line = max(0, line_number - context_lines - 1)
    end_line = min(len(lines), line_number + context_lines)
    
    context = lines[start_line:end_line]
    return '\n'
    return '\n'.join(f"{start_line + i + 1}: {line}" for i, line in enumerate(context))


def deduplicate_search_results(results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicate search results."""
    seen = set()
    deduped = []
    
    for result in results:
        # Create unique key based on file, line, and column
        key = (result.file_path, result.line, result.column)
        
        if key not in seen:
            seen.add(key)
            deduped.append(result)
    
    return deduped
