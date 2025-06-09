"""Enhanced dispatcher with dynamic plugin loading via PluginFactory."""
from pathlib import Path
from typing import Iterable, Dict, List, Optional, Tuple, Any, Union
import logging
import hashlib
import time
import re
from datetime import datetime

from ..plugin_base import IPlugin, SymbolDef, SearchResult, Reference
from ..plugins.plugin_factory import PluginFactory
from ..plugins.language_registry import get_language_by_extension
from ..storage.sqlite_store import SQLiteStore
from .plugin_router import PluginRouter, FileTypeMatcher, PluginCapability
from .result_aggregator import ResultAggregator, AggregatedResult, AggregationStats, RankingCriteria

logger = logging.getLogger(__name__)


class EnhancedDispatcher:
    """Enhanced dispatcher with dynamic plugin loading and advanced routing capabilities."""
    
    # Document query patterns - common documentation search terms
    DOCUMENT_QUERY_PATTERNS = [
        r'\b(how\s+to|howto)\b',
        r'\b(getting\s+started|get\s+started)\b',
        r'\b(installation|install|setup)\b',
        r'\b(configuration|configure|config)\b',
        r'\b(api\s+doc|api\s+documentation|api\s+reference)\b',
        r'\b(tutorial|guide|walkthrough)\b',
        r'\b(example|sample|snippet)\b',
        r'\b(readme|documentation|docs)\b',
        r'\b(usage|use\s+case|using)\b',
        r'\b(reference|manual)\b',
        r'\b(faq|frequently\s+asked)\b',
        r'\b(troubleshoot|troubleshooting|debug|debugging|error|errors|issue|issues)\b',
        r'\b(best\s+practice|best\s+practices|convention|conventions)\b',
        r'\b(architecture|design|overview)\b',
        r'\b(changelog|release\s+notes|migration)\b'
    ]
    
    # Documentation file patterns
    DOCUMENTATION_FILE_PATTERNS = [
        r'readme(\.\w+)?$',
        r'changelog(\.\w+)?$',
        r'contributing(\.\w+)?$',
        r'license(\.\w+)?$',
        r'install(\.\w+)?$',
        r'setup(\.\w+)?$',
        r'guide(\.\w+)?$',
        r'tutorial(\.\w+)?$',
        r'\.md$',
        r'\.rst$',
        r'\.txt$',
        r'docs?/',
        r'documentation/'
    ]
    
    def __init__(self, 
                 plugins: Optional[List[IPlugin]] = None,
                 sqlite_store: Optional[SQLiteStore] = None,
                 enable_advanced_features: bool = True,
                 use_plugin_factory: bool = True,
                 lazy_load: bool = True,
                 semantic_search_enabled: bool = True):
        """Initialize the enhanced dispatcher.
        
        Args:
            plugins: Optional list of pre-instantiated plugins (for backward compatibility)
            sqlite_store: SQLite store for plugin persistence
            enable_advanced_features: Whether to enable advanced routing and aggregation
            use_plugin_factory: Whether to use PluginFactory for dynamic loading
            lazy_load: Whether to lazy-load plugins on demand
            semantic_search_enabled: Whether to enable semantic search in plugins
        """
        self._sqlite_store = sqlite_store
        self._enable_advanced = enable_advanced_features
        self._use_factory = use_plugin_factory
        self._lazy_load = lazy_load
        self._semantic_enabled = semantic_search_enabled
        
        # Plugin storage
        self._plugins: List[IPlugin] = []
        self._by_lang: Dict[str, IPlugin] = {}
        self._loaded_languages: set[str] = set()
        
        # Cache for file hashes to avoid re-indexing unchanged files
        self._file_cache = {}  # path -> (mtime, size, content_hash)
        
        # Advanced components
        if self._enable_advanced:
            self._file_matcher = FileTypeMatcher()
            self._router = PluginRouter(self._file_matcher)
            self._aggregator = ResultAggregator()
        
        # Performance tracking
        self._operation_stats = {
            'searches': 0,
            'lookups': 0,
            'indexings': 0,
            'total_time': 0.0,
            'plugins_loaded': 0
        }
        
        # Initialize plugins
        if plugins:
            # Use provided plugins (backward compatibility)
            self._plugins = plugins
            self._by_lang = {p.lang: p for p in plugins}
            for plugin in plugins:
                self._loaded_languages.add(getattr(plugin, 'lang', 'unknown'))
            if self._enable_advanced:
                self._register_plugins_with_router()
        elif use_plugin_factory and not lazy_load:
            # Load all plugins immediately
            self._load_all_plugins()
        # If lazy_load is True, plugins will be loaded on demand
        
        # Compile document query patterns for performance
        self._compiled_doc_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DOCUMENT_QUERY_PATTERNS]
        self._compiled_file_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DOCUMENTATION_FILE_PATTERNS]
        
        logger.info(f"Enhanced dispatcher initialized with {len(self._plugins)} plugins")
    
    def _load_all_plugins(self):
        """Load all available plugins using PluginFactory."""
        logger.info("Loading all available plugins...")
        
        all_plugins = PluginFactory.create_all_plugins(
            sqlite_store=self._sqlite_store,
            enable_semantic=self._semantic_enabled
        )
        
        for lang, plugin in all_plugins.items():
            self._plugins.append(plugin)
            self._by_lang[lang] = plugin
            self._loaded_languages.add(lang)
            self._operation_stats['plugins_loaded'] += 1
        
        if self._enable_advanced:
            self._register_plugins_with_router()
        
        logger.info(f"Loaded {len(all_plugins)} plugins: {', '.join(sorted(all_plugins.keys()))}")
    
    def _ensure_plugin_loaded(self, language: str) -> Optional[IPlugin]:
        """Ensure a plugin for the given language is loaded.
        
        Args:
            language: Language code (e.g., 'python', 'go')
            
        Returns:
            Plugin instance or None if not available
        """
        # Normalize language
        language = language.lower().replace('-', '_')
        
        # Check if already loaded
        if language in self._by_lang:
            return self._by_lang[language]
        
        # If not using factory or already tried to load, return None
        if not self._use_factory or language in self._loaded_languages:
            return None
        
        # Try to load the plugin
        try:
            logger.info(f"Lazy loading plugin for {language}")
            plugin = PluginFactory.create_plugin(
                language,
                sqlite_store=self._sqlite_store,
                enable_semantic=self._semantic_enabled
            )
            
            # Add to collections
            self._plugins.append(plugin)
            self._by_lang[language] = plugin
            self._loaded_languages.add(language)
            self._operation_stats['plugins_loaded'] += 1
            
            # Register with router if needed
            if self._enable_advanced:
                capabilities = self._detect_plugin_capabilities(plugin)
                self._router.register_plugin(plugin, capabilities)
            
            logger.info(f"Successfully loaded {language} plugin")
            return plugin
            
        except ValueError as e:
            logger.warning(f"No plugin available for {language}: {e}")
            self._loaded_languages.add(language)  # Mark as attempted
            return None
        except Exception as e:
            logger.error(f"Error loading plugin for {language}: {e}")
            self._loaded_languages.add(language)  # Mark as attempted
            return None
    
    def _ensure_plugin_for_file(self, path: Path) -> Optional[IPlugin]:
        """Ensure a plugin is loaded for the given file.
        
        Args:
            path: File path
            
        Returns:
            Plugin instance or None if not available
        """
        # Get language from file extension
        extension = path.suffix.lower()
        language = get_language_by_extension(extension)
        
        if language:
            return self._ensure_plugin_loaded(language)
        
        # Fallback: try all loaded plugins
        for plugin in self._plugins:
            if plugin.supports(path):
                return plugin
        
        return None
    
    def _register_plugins_with_router(self):
        """Register plugins with the router and assign capabilities."""
        for plugin in self._plugins:
            # Determine capabilities based on plugin type/language
            capabilities = self._detect_plugin_capabilities(plugin)
            self._router.register_plugin(plugin, capabilities)
    
    def _detect_plugin_capabilities(self, plugin: IPlugin) -> List[PluginCapability]:
        """Detect capabilities for a plugin based on its language and features."""
        capabilities = []
        lang = getattr(plugin, 'lang', 'unknown')
        
        # Base capabilities all plugins have
        capabilities.append(PluginCapability(
            'syntax_analysis', '1.0', f'{lang} syntax analysis', 
            priority=70, metadata={'language': lang}
        ))
        
        capabilities.append(PluginCapability(
            'code_search', '1.0', f'{lang} code search', 
            priority=80, metadata={'language': lang}
        ))
        
        # Check for semantic search capability
        if hasattr(plugin, '_enable_semantic') and plugin._enable_semantic:
            capabilities.append(PluginCapability(
                'semantic_search', '1.0', f'{lang} semantic search', 
                priority=90, metadata={'language': lang}
            ))
        
        # Language-specific capabilities
        if lang == 'python':
            capabilities.extend([
                PluginCapability('refactoring', '1.0', 'Python refactoring support', 75),
                PluginCapability('type_analysis', '1.0', 'Python type analysis', 85)
            ])
        elif lang in ['javascript', 'typescript']:
            capabilities.extend([
                PluginCapability('linting', '1.0', 'JavaScript/TypeScript linting', 85),
                PluginCapability('bundling_analysis', '1.0', 'Module bundling analysis', 70),
                PluginCapability('framework_support', '1.0', 'Framework-specific support', 75)
            ])
        elif lang in ['c', 'cpp']:
            capabilities.extend([
                PluginCapability('compilation_analysis', '1.0', 'Compilation analysis', 80),
                PluginCapability('memory_analysis', '1.0', 'Memory usage analysis', 70),
                PluginCapability('performance_profiling', '1.0', 'Performance profiling', 75)
            ])
        elif lang in ['go', 'rust']:
            capabilities.extend([
                PluginCapability('package_analysis', '1.0', f'{lang} package analysis', 80),
                PluginCapability('concurrency_analysis', '1.0', f'{lang} concurrency analysis', 75)
            ])
        elif lang in ['java', 'kotlin', 'scala']:
            capabilities.extend([
                PluginCapability('jvm_analysis', '1.0', 'JVM bytecode analysis', 75),
                PluginCapability('build_tool_integration', '1.0', 'Build tool integration', 70)
            ])
        
        return capabilities
    
    @property
    def plugins(self):
        """Get the dictionary of loaded plugins by language."""
        return self._by_lang
    
    @property
    def supported_languages(self) -> List[str]:
        """Get list of all supported languages (loaded and available)."""
        if self._use_factory:
            return PluginFactory.get_supported_languages()
        else:
            return list(self._by_lang.keys())
    
    def _match_plugin(self, path: Path) -> IPlugin:
        """Match a plugin for the given file path."""
        # Ensure plugin is loaded if using lazy loading
        if self._lazy_load and self._use_factory:
            plugin = self._ensure_plugin_for_file(path)
            if plugin:
                return plugin
        
        # Use advanced routing if available
        if self._enable_advanced and self._router:
            route_result = self._router.get_best_plugin(path)
            if route_result:
                return route_result.plugin
        
        # Fallback to basic matching
        for p in self._plugins:
            if p.supports(path):
                return p
        
        raise RuntimeError(f"No plugin found for {path}")
    
    def get_plugins_for_file(self, path: Path) -> List[Tuple[IPlugin, float]]:
        """Get all plugins that can handle a file with confidence scores."""
        # Ensure plugin is loaded if using lazy loading
        if self._lazy_load and self._use_factory:
            self._ensure_plugin_for_file(path)
        
        if self._enable_advanced and self._router:
            route_results = self._router.route_file(path)
            return [(result.plugin, result.confidence) for result in route_results]
        else:
            # Basic fallback
            matching_plugins = []
            for plugin in self._plugins:
                if plugin.supports(path):
                    matching_plugins.append((plugin, 1.0))
            return matching_plugins
    
    def lookup(self, symbol: str) -> SymbolDef | None:
        """Look up symbol definition across all plugins."""
        start_time = time.time()
        
        try:
            # For symbol lookup, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()
            
            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                definitions_by_plugin = {}
                for plugin in self._plugins:
                    try:
                        definition = plugin.getDefinition(symbol)
                        definitions_by_plugin[plugin] = definition
                    except Exception as e:
                        logger.warning(f"Plugin {plugin.lang} failed to get definition for {symbol}: {e}")
                        definitions_by_plugin[plugin] = None
                
                result = self._aggregator.aggregate_symbol_definitions(definitions_by_plugin)
                
                self._operation_stats['lookups'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
                return result
            else:
                # Fallback to basic lookup
                for p in self._plugins:
                    res = p.getDefinition(symbol)
                    if res:
                        self._operation_stats['lookups'] += 1
                        self._operation_stats['total_time'] += time.time() - start_time
                        return res
                return None
                
        except Exception as e:
            logger.error(f"Error in symbol lookup for {symbol}: {e}", exc_info=True)
            return None
    
    def _is_document_query(self, query: str) -> bool:
        """Check if the query is looking for documentation.
        
        Args:
            query: Search query string
            
        Returns:
            True if this appears to be a documentation query
        """
        query_lower = query.lower()
        
        # Check against document query patterns
        for pattern in self._compiled_doc_patterns:
            if pattern.search(query_lower):
                return True
        
        # Check for question words at the beginning
        question_starters = ['how', 'what', 'where', 'when', 'why', 'can', 'is', 'does', 'should']
        first_word = query_lower.split()[0] if query_lower.split() else ''
        if first_word in question_starters:
            return True
        
        return False
    
    def _expand_document_query(self, query: str) -> List[str]:
        """Expand a document query with related terms for better search coverage.
        
        Args:
            query: Original search query
            
        Returns:
            List of expanded query variations
        """
        expanded_queries = [query]  # Always include original
        query_lower = query.lower()
        
        # Common expansions for documentation queries
        expansions = {
            'install': ['installation', 'setup', 'getting started', 'requirements'],
            'config': ['configuration', 'configure', 'settings', 'options', 'parameters'],
            'api': ['api documentation', 'api reference', 'endpoint', 'method'],
            'how to': ['tutorial', 'guide', 'example', 'usage'],
            'example': ['sample', 'snippet', 'demo', 'code example'],
            'error': ['troubleshoot', 'debug', 'issue', 'problem', 'fix'],
            'getting started': ['quickstart', 'tutorial', 'introduction', 'setup'],
            'guide': ['tutorial', 'documentation', 'walkthrough', 'how to'],
            'usage': ['how to use', 'example', 'api', 'reference']
        }
        
        # Apply expansions
        for term, related_terms in expansions.items():
            if term in query_lower:
                for related in related_terms:
                    # Replace the term with related term
                    expanded = query_lower.replace(term, related)
                    if expanded != query_lower and expanded not in expanded_queries:
                        expanded_queries.append(expanded)
                
                # Also add queries with additional terms
                for related in related_terms[:2]:  # Limit to avoid too many queries
                    expanded = f"{query} {related}"
                    if expanded not in expanded_queries:
                        expanded_queries.append(expanded)
        
        # Add file-specific searches for common documentation files
        if self._is_document_query(query):
            # Extract the main topic from the query
            topic_words = []
            for word in query.lower().split():
                if word not in ['how', 'to', 'the', 'a', 'an', 'is', 'are', 'what', 'where', 'when']:
                    topic_words.append(word)
            
            if topic_words:
                topic = ' '.join(topic_words[:2])  # Use first two topic words
                expanded_queries.extend([
                    f"README {topic}",
                    f"{topic} documentation",
                    f"{topic} docs",
                    f"{topic} guide"
                ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in expanded_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:10]  # Limit to 10 queries max
    
    def _is_documentation_file(self, file_path: str) -> bool:
        """Check if a file path is likely a documentation file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if this appears to be a documentation file
        """
        path_lower = file_path.lower()
        
        for pattern in self._compiled_file_patterns:
            if pattern.search(path_lower):
                return True
        
        return False
    
    def _adjust_ranking_for_documents(self, query: str, results: List[AggregatedResult]) -> List[AggregatedResult]:
        """Adjust ranking to prioritize documentation files for document queries.
        
        Args:
            query: Original search query
            results: List of aggregated results
            
        Returns:
            Re-ranked results with documentation prioritized
        """
        if not self._is_document_query(query):
            return results
        
        # Separate documentation and code results
        doc_results = []
        code_results = []
        
        for result in results:
            if self._is_documentation_file(result.primary_result.get('file', '')):
                # Boost documentation files for document queries
                result.rank_score *= 1.5
                result.metadata['doc_boost'] = True
                doc_results.append(result)
            else:
                code_results.append(result)
        
        # Sort each group by rank score
        doc_results.sort(key=lambda r: r.rank_score, reverse=True)
        code_results.sort(key=lambda r: r.rank_score, reverse=True)
        
        # Combine with documentation files first
        return doc_results + code_results
    
    def search(self, query: str, semantic=False, limit=20) -> Iterable[SearchResult]:
        """Search for code and documentation across all plugins."""
        start_time = time.time()
        
        try:
            # For search, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()
            
            # Detect if this is a document query
            is_doc_query = self._is_document_query(query)
            
            # Expand query if it's a document query
            queries = [query]
            if is_doc_query:
                queries = self._expand_document_query(query)
                logger.info(f"Expanded document query '{query}' to {len(queries)} variations")
                # Force semantic search for natural language queries
                semantic = True
            
            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                all_results_by_plugin = {}
                opts = {"semantic": semantic, "limit": limit * 2 if is_doc_query else limit}
                
                # Search with all query variations
                for search_query in queries:
                    for plugin in self._plugins:
                        try:
                            results = list(plugin.search(search_query, opts))
                            if results:
                                if plugin not in all_results_by_plugin:
                                    all_results_by_plugin[plugin] = []
                                all_results_by_plugin[plugin].extend(results)
                        except Exception as e:
                            logger.warning(f"Plugin {plugin.lang} failed to search for {search_query}: {e}")
                
                # Deduplicate results per plugin
                for plugin, results in all_results_by_plugin.items():
                    seen = set()
                    unique_results = []
                    for result in results:
                        key = f"{result['file']}:{result['line']}"
                        if key not in seen:
                            seen.add(key)
                            unique_results.append(result)
                    all_results_by_plugin[plugin] = unique_results
                
                # Configure aggregator for document queries
                if is_doc_query and self._enable_advanced:
                    # Adjust ranking criteria for documentation
                    doc_criteria = RankingCriteria(
                        relevance_weight=0.5,      # Increase relevance weight
                        confidence_weight=0.2,     # Reduce confidence weight
                        frequency_weight=0.2,      # Keep frequency weight
                        recency_weight=0.1,        # Keep recency weight
                        prefer_exact_matches=False,  # Natural language doesn't need exact matches
                        boost_multiple_sources=True,
                        boost_common_extensions=True
                    )
                    self._aggregator.configure(ranking_criteria=doc_criteria)
                
                aggregated_results, stats = self._aggregator.aggregate_search_results(
                    all_results_by_plugin, limit=limit * 2 if is_doc_query else limit
                )
                
                # Adjust ranking for document queries
                if is_doc_query:
                    aggregated_results = self._adjust_ranking_for_documents(query, aggregated_results)
                
                # Apply final limit
                if limit and len(aggregated_results) > limit:
                    aggregated_results = aggregated_results[:limit]
                
                logger.debug(f"Search aggregation stats: {stats.total_results} total, "
                           f"{stats.unique_results} unique, {stats.plugins_used} plugins used, "
                           f"document_query={is_doc_query}")
                
                self._operation_stats['searches'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
                # Yield primary results from aggregated results
                for aggregated in aggregated_results:
                    yield aggregated.primary_result
            else:
                # Fallback to basic search
                # Detect if this is a document query
                is_doc_query = self._is_document_query(query)
                
                # Expand query if it's a document query
                queries = [query]
                if is_doc_query:
                    queries = self._expand_document_query(query)
                    semantic = True  # Force semantic search for natural language
                
                opts = {"semantic": semantic, "limit": limit}
                all_results = []
                
                # Search with all query variations
                for search_query in queries:
                    for p in self._plugins:
                        try:
                            for result in p.search(search_query, opts):
                                all_results.append(result)
                        except Exception as e:
                            logger.warning(f"Plugin {p.lang} failed to search for {search_query}: {e}")
                
                # Deduplicate results
                seen = set()
                unique_results = []
                for result in all_results:
                    key = f"{result['file']}:{result['line']}"
                    if key not in seen:
                        seen.add(key)
                        unique_results.append(result)
                
                # Sort by score if available
                unique_results.sort(key=lambda r: r.get('score', 0.5) or 0.5, reverse=True)
                
                # Prioritize documentation files for document queries
                if is_doc_query:
                    doc_results = []
                    code_results = []
                    for result in unique_results:
                        if self._is_documentation_file(result.get('file', '')):
                            doc_results.append(result)
                        else:
                            code_results.append(result)
                    unique_results = doc_results + code_results
                
                # Apply limit
                count = 0
                for result in unique_results:
                    if limit and count >= limit:
                        break
                    yield result
                    count += 1
                
                self._operation_stats['searches'] += 1
                self._operation_stats['total_time'] += time.time() - start_time
                
        except Exception as e:
            logger.error(f"Error in search for {query}: {e}", exc_info=True)
    
    def index_file(self, path: Path) -> None:
        """Index a single file if it has changed."""
        try:
            # Ensure path is absolute to avoid relative/absolute path issues
            path = path.resolve()
            
            # Find the appropriate plugin
            plugin = self._match_plugin(path)
            
            # Read file content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                try:
                    content = path.read_text(encoding='latin-1')
                except Exception as e:
                    logger.error(f"Failed to read {path}: {e}")
                    return
            
            # Check if we need to re-index (simplified for now)
            # TODO: Implement proper caching logic
            
            # Index the file
            start_time = time.time()
            logger.info(f"Indexing {path} with {plugin.lang} plugin")
            shard = plugin.indexFile(path, content)
            
            # Record performance if advanced features enabled
            if self._enable_advanced and self._router:
                execution_time = time.time() - start_time
                self._router.record_performance(plugin, execution_time)
            
            self._operation_stats['indexings'] += 1
            self._operation_stats['total_time'] += time.time() - start_time
            
            logger.info(f"Successfully indexed {path}: {len(shard.get('symbols', []))} symbols found")
            
        except RuntimeError as e:
            # No plugin found for this file type
            logger.debug(f"No plugin for {path}: {e}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """Get comprehensive statistics across all plugins and components."""
        stats = {
            "total_plugins": len(self._plugins),
            "loaded_languages": sorted(list(self._loaded_languages)),
            "supported_languages": len(self.supported_languages),
            "operations": self._operation_stats.copy()
        }
        
        # Add language breakdown
        stats["by_language"] = {}
        for lang, plugin in self._by_lang.items():
            plugin_info = {
                "loaded": True,
                "class": plugin.__class__.__name__
            }
            if hasattr(plugin, 'get_indexed_count'):
                plugin_info["indexed_files"] = plugin.get_indexed_count()
            stats["by_language"][lang] = plugin_info
        
        return stats
    
    def search_documentation(self, topic: str, doc_types: Optional[List[str]] = None, limit: int = 20) -> Iterable[SearchResult]:
        """Search specifically across documentation files.
        
        Args:
            topic: Topic to search for (e.g., "installation", "configuration")
            doc_types: Optional list of document types to search (e.g., ["readme", "guide", "api"])
            limit: Maximum number of results
            
        Returns:
            Search results from documentation files
        """
        # Default document types if not specified
        if doc_types is None:
            doc_types = ["readme", "documentation", "guide", "tutorial", "api", "changelog", "contributing"]
        
        # Build search queries for different document types
        queries = []
        for doc_type in doc_types:
            queries.extend([
                f"{doc_type} {topic}",
                f"{topic} {doc_type}",
                f"{topic} in {doc_type}"
            ])
        
        # Also search for the topic in common doc filenames
        queries.extend([
            f"README {topic}",
            f"CONTRIBUTING {topic}",
            f"docs {topic}",
            f"documentation {topic}"
        ])
        
        # Deduplicate queries
        queries = list(dict.fromkeys(queries))
        
        logger.info(f"Cross-document search for '{topic}' with {len(queries)} query variations")
        
        # Use the enhanced search with document-specific handling
        all_results = []
        seen = set()
        
        for query in queries[:10]:  # Limit to 10 queries to avoid too many searches
            for result in self.search(query, semantic=True, limit=limit):
                # Only include documentation files
                if self._is_documentation_file(result.get('file', '')):
                    key = f"{result['file']}:{result['line']}"
                    if key not in seen:
                        seen.add(key)
                        all_results.append(result)
        
        # Sort by relevance (score) and return top results
        all_results.sort(key=lambda r: r.get('score', 0.5) or 0.5, reverse=True)
        
        count = 0
        for result in all_results:
            if count >= limit:
                break
            yield result
            count += 1
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on all components."""
        health = {
            'status': 'healthy',
            'components': {
                'dispatcher': {
                    'status': 'healthy',
                    'plugins_loaded': len(self._plugins),
                    'languages_supported': len(self.supported_languages),
                    'factory_enabled': self._use_factory,
                    'lazy_loading': self._lazy_load
                }
            },
            'plugins': {},
            'errors': []
        }
        
        # Check plugin health
        for lang, plugin in self._by_lang.items():
            try:
                plugin_health = {
                    'status': 'healthy',
                    'class': plugin.__class__.__name__,
                    'semantic_enabled': getattr(plugin, '_enable_semantic', False)
                }
                if hasattr(plugin, 'get_indexed_count'):
                    plugin_health['indexed_files'] = plugin.get_indexed_count()
            except Exception as e:
                plugin_health = {
                    'status': 'error',
                    'error': str(e)
                }
                health['errors'].append(f"Plugin {lang}: {str(e)}")
            
            health['plugins'][lang] = plugin_health
        
        # Determine overall health
        if len(health['errors']) > 0:
            health['status'] = 'degraded' if len(health['errors']) < 3 else 'unhealthy'
        
        return health