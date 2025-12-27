"""Enhanced dispatcher with dynamic plugin loading via PluginFactory."""

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ..graph import (
    CHUNKER_AVAILABLE,
    ContextSelector,
    GraphAnalyzer,
    GraphCutResult,
    GraphNode,
    XRefAdapter,
)
from ..plugin_base import IPlugin, SearchResult, SymbolDef
from ..plugins.language_registry import get_all_extensions, get_language_by_extension
from ..plugins.memory_aware_manager import MemoryAwarePluginManager
from ..plugins.plugin_factory import PluginFactory
from ..plugins.repository_plugin_loader import RepositoryPluginLoader
from ..storage.cross_repo_coordinator import CrossRepositorySearchCoordinator, SearchScope
from ..storage.multi_repo_manager import MultiRepositoryManager
from ..storage.sqlite_store import SQLiteStore
from ..utils.semantic_indexer import SemanticIndexer
from .plugin_router import FileTypeMatcher, PluginCapability, PluginRouter
from .result_aggregator import (
    AggregatedResult,
    RankingCriteria,
    ResultAggregator,
)

# Note: We've removed ignore pattern checks to allow indexing ALL files
# Filtering happens only during export via SecureIndexExporter
# from ..core.ignore_patterns import get_ignore_manager

logger = logging.getLogger(__name__)


class EnhancedDispatcher:
    """Enhanced dispatcher with dynamic plugin loading and advanced routing capabilities."""

    # Document query patterns - common documentation search terms
    DOCUMENT_QUERY_PATTERNS = [
        r"\b(how\s+to|howto)\b",
        r"\b(getting\s+started|get\s+started)\b",
        r"\b(installation|install|setup)\b",
        r"\b(configuration|configure|config)\b",
        r"\b(api\s+doc|api\s+documentation|api\s+reference)\b",
        r"\b(tutorial|guide|walkthrough)\b",
        r"\b(example|sample|snippet)\b",
        r"\b(readme|documentation|docs)\b",
        r"\b(usage|use\s+case|using)\b",
        r"\b(reference|manual)\b",
        r"\b(faq|frequently\s+asked)\b",
        r"\b(troubleshoot|troubleshooting|debug|debugging|error|errors|issue|issues)\b",
        r"\b(best\s+practice|best\s+practices|convention|conventions)\b",
        r"\b(architecture|design|overview)\b",
        r"\b(changelog|release\s+notes|migration)\b",
    ]

    # Documentation file patterns
    DOCUMENTATION_FILE_PATTERNS = [
        r"readme(\.\w+)?$",
        r"changelog(\.\w+)?$",
        r"contributing(\.\w+)?$",
        r"license(\.\w+)?$",
        r"install(\.\w+)?$",
        r"setup(\.\w+)?$",
        r"guide(\.\w+)?$",
        r"tutorial(\.\w+)?$",
        r"\.md$",
        r"\.rst$",
        r"\.txt$",
        r"docs?/",
        r"documentation/",
    ]

    def __init__(
        self,
        plugins: Optional[List[IPlugin]] = None,
        sqlite_store: Optional[SQLiteStore] = None,
        enable_advanced_features: bool = True,
        use_plugin_factory: bool = True,
        lazy_load: bool = True,
        semantic_search_enabled: bool = True,
        memory_aware: bool = True,
        multi_repo_enabled: bool = None,
    ):
        """Initialize the enhanced dispatcher.

        Args:
            plugins: Optional list of pre-instantiated plugins (for backward compatibility)
            sqlite_store: SQLite store for plugin persistence
            enable_advanced_features: Whether to enable advanced routing and aggregation
            use_plugin_factory: Whether to use PluginFactory for dynamic loading
            lazy_load: Whether to lazy-load plugins on demand
            semantic_search_enabled: Whether to enable semantic search in plugins
            memory_aware: Whether to use memory-aware plugin management
            multi_repo_enabled: Whether to enable multi-repository support (None = auto from env)
        """
        self._sqlite_store = sqlite_store
        self._memory_aware = memory_aware
        self._multi_repo_enabled = multi_repo_enabled

        # Initialize repository-aware components if enabled
        if self._memory_aware and sqlite_store:
            self._repo_plugin_loader = RepositoryPluginLoader()
            self._memory_manager = MemoryAwarePluginManager()
        else:
            self._repo_plugin_loader = None
            self._memory_manager = None

        # Initialize multi-repo manager if enabled
        if multi_repo_enabled is None:
            multi_repo_enabled = os.getenv("MCP_ENABLE_MULTI_REPO", "false").lower() == "true"

        if multi_repo_enabled and sqlite_store:
            # Get current repo ID
            try:
                import subprocess

                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                remote_url = result.stdout.strip()
                _ = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
            except Exception:
                _ = hashlib.sha256(str(Path.cwd()).encode()).hexdigest()[:12]

            storage_path = os.getenv("MCP_INDEX_STORAGE_PATH", ".indexes")
            # Use the correct registry path
            registry_path = Path(storage_path) / "repository_registry.json"
            self._multi_repo_manager = MultiRepositoryManager(central_index_path=registry_path)
            self._cross_repo_coordinator = CrossRepositorySearchCoordinator(
                self._multi_repo_manager
            )
        else:
            self._multi_repo_manager = None
            self._cross_repo_coordinator = None
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
            "searches": 0,
            "lookups": 0,
            "indexings": 0,
            "total_time": 0.0,
            "plugins_loaded": 0,
        }

        # Initialize semantic indexer if enabled with auto-discovery
        self._semantic_indexer = None
        if self._semantic_enabled and self._sqlite_store:
            try:
                from ..utils.semantic_discovery import SemanticDatabaseDiscovery

                # Auto-discover the correct semantic collection for this codebase
                discovery = SemanticDatabaseDiscovery(Path.cwd())
                best_collection = discovery.get_best_collection()

                if best_collection:
                    qdrant_path, collection_name = best_collection
                    logger.info(
                        f"Auto-discovered semantic collection: {collection_name} at {qdrant_path}"
                    )
                else:
                    # No existing collection found, use default configuration
                    qdrant_path, collection_name = discovery.get_default_collection_config()
                    logger.info(
                        f"No existing collection found, using default: {collection_name} at {qdrant_path}"
                    )

                # Only initialize if the Qdrant path exists
                if Path(qdrant_path).exists():
                    self._semantic_indexer = SemanticIndexer(
                        qdrant_path=qdrant_path, collection=collection_name
                    )
                    logger.info(f"Semantic search initialized: {collection_name} at {qdrant_path}")
                else:
                    logger.warning(f"Qdrant path not found: {qdrant_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {e}")
                # Fall back to legacy behavior
                try:
                    qdrant_path = Path(".indexes/qdrant/main.qdrant")
                    if qdrant_path.exists():
                        self._semantic_indexer = SemanticIndexer(
                            qdrant_path=str(qdrant_path), collection="code-embeddings"
                        )
                        logger.info("Semantic search initialized with legacy fallback")
                except Exception as e2:
                    logger.warning(f"Legacy fallback also failed: {e2}")

        # Initialize plugins
        if plugins:
            # Use provided plugins (backward compatibility)
            self._plugins = plugins
            self._by_lang = {p.lang: p for p in plugins}
            for plugin in plugins:
                self._loaded_languages.add(getattr(plugin, "lang", "unknown"))
            if self._enable_advanced:
                self._register_plugins_with_router()
        elif use_plugin_factory and not lazy_load:
            # Load all plugins immediately
            self._load_all_plugins()
        # If lazy_load is True, plugins will be loaded on demand

        # Compile document query patterns for performance
        self._compiled_doc_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.DOCUMENT_QUERY_PATTERNS
        ]
        self._compiled_file_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.DOCUMENTATION_FILE_PATTERNS
        ]

        # Graph analysis components (lazy initialized)
        self._graph_builder: Optional[XRefAdapter] = None
        self._graph_analyzer: Optional[GraphAnalyzer] = None
        self._context_selector: Optional[ContextSelector] = None
        self._graph_nodes: List[GraphNode] = []
        self._graph_edges = []

        logger.info(f"Enhanced dispatcher initialized with {len(self._plugins)} plugins")

    def _load_all_plugins(self):
        """Load all available plugins using PluginFactory with timeout protection."""
        logger.info("Loading all available plugins with timeout...")

        import signal
        from contextlib import contextmanager

        @contextmanager
        def timeout(seconds):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Plugin loading timed out after {seconds}s")

            # Only use alarm on Unix-like systems
            if hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # On Windows, just yield without timeout
                yield

        try:
            with timeout(5):  # 5 second timeout
                # Use repository-aware loading if available
                if self._repo_plugin_loader and self._memory_aware:
                    # Get languages to load based on repository content
                    languages_to_load = self._repo_plugin_loader.get_required_plugins()
                    priority_order = self._repo_plugin_loader.get_priority_languages()

                    # Log loading plan
                    self._repo_plugin_loader.log_loading_plan()

                    # Load plugins in priority order
                    for lang in priority_order:
                        if lang in languages_to_load:
                            try:
                                # Use memory manager if available
                                if self._memory_manager:
                                    import asyncio

                                    # Check if we're already in an async context
                                    try:
                                        _ = asyncio.get_running_loop()
                                        # We're in an async context, can't use asyncio.run
                                        logger.warning(
                                            f"Cannot use async memory manager from sync context for {lang}, using direct creation"
                                        )
                                        plugin = PluginFactory.create_plugin(
                                            lang, self._sqlite_store, self._semantic_enabled
                                        )
                                    except RuntimeError:
                                        # No running loop, safe to use asyncio.run
                                        plugin = asyncio.run(self._memory_manager.get_plugin(lang))
                                else:
                                    plugin = PluginFactory.create_plugin(
                                        lang, self._sqlite_store, self._semantic_enabled
                                    )

                                if plugin:
                                    self._plugins.append(plugin)
                                    self._by_lang[lang] = plugin
                                    self._loaded_languages.add(lang)
                                    self._operation_stats["plugins_loaded"] += 1
                                    self._repo_plugin_loader.mark_loaded(lang)
                            except Exception as e:
                                logger.error(f"Failed to load {lang} plugin: {e}")
                else:
                    # Fall back to loading all plugins
                    all_plugins = PluginFactory.create_all_plugins(
                        sqlite_store=self._sqlite_store, enable_semantic=self._semantic_enabled
                    )

                    for lang, plugin in all_plugins.items():
                        self._plugins.append(plugin)
                        self._by_lang[lang] = plugin
                        self._loaded_languages.add(lang)
                        self._operation_stats["plugins_loaded"] += 1

                if self._enable_advanced:
                    self._register_plugins_with_router()

                logger.info(
                    f"Loaded {len(self._plugins)} plugins: {', '.join(sorted(self._loaded_languages))}"
                )

        except TimeoutError as e:
            logger.warning(f"Plugin loading timeout: {e}")
            self._plugins = []  # Ensure empty list on timeout
            self._loaded_languages = set()
        except Exception as e:
            logger.error(f"Plugin loading failed: {e}")
            self._plugins = []  # Ensure empty list on failure
            self._loaded_languages = set()

    def _ensure_plugin_loaded(self, language: str) -> Optional[IPlugin]:
        """Ensure a plugin for the given language is loaded.

        Args:
            language: Language code (e.g., 'python', 'go')

        Returns:
            Plugin instance or None if not available
        """
        # Normalize language
        language = language.lower().replace("-", "_")

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
                enable_semantic=self._semantic_enabled,
            )

            # Add to collections
            self._plugins.append(plugin)
            self._by_lang[language] = plugin
            self._loaded_languages.add(language)
            self._operation_stats["plugins_loaded"] += 1

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
        lang = getattr(plugin, "lang", "unknown")

        # Base capabilities all plugins have
        capabilities.append(
            PluginCapability(
                "syntax_analysis",
                "1.0",
                f"{lang} syntax analysis",
                priority=70,
                metadata={"language": lang},
            )
        )

        capabilities.append(
            PluginCapability(
                "code_search",
                "1.0",
                f"{lang} code search",
                priority=80,
                metadata={"language": lang},
            )
        )

        # Check for semantic search capability
        if hasattr(plugin, "_enable_semantic") and plugin._enable_semantic:
            capabilities.append(
                PluginCapability(
                    "semantic_search",
                    "1.0",
                    f"{lang} semantic search",
                    priority=90,
                    metadata={"language": lang},
                )
            )

        # Language-specific capabilities
        if lang == "python":
            capabilities.extend(
                [
                    PluginCapability("refactoring", "1.0", "Python refactoring support", 75),
                    PluginCapability("type_analysis", "1.0", "Python type analysis", 85),
                ]
            )
        elif lang in ["javascript", "typescript"]:
            capabilities.extend(
                [
                    PluginCapability("linting", "1.0", "JavaScript/TypeScript linting", 85),
                    PluginCapability("bundling_analysis", "1.0", "Module bundling analysis", 70),
                    PluginCapability("framework_support", "1.0", "Framework-specific support", 75),
                ]
            )
        elif lang in ["c", "cpp"]:
            capabilities.extend(
                [
                    PluginCapability("compilation_analysis", "1.0", "Compilation analysis", 80),
                    PluginCapability("memory_analysis", "1.0", "Memory usage analysis", 70),
                    PluginCapability("performance_profiling", "1.0", "Performance profiling", 75),
                ]
            )
        elif lang in ["go", "rust"]:
            capabilities.extend(
                [
                    PluginCapability("package_analysis", "1.0", f"{lang} package analysis", 80),
                    PluginCapability(
                        "concurrency_analysis",
                        "1.0",
                        f"{lang} concurrency analysis",
                        75,
                    ),
                ]
            )
        elif lang in ["java", "kotlin", "scala"]:
            capabilities.extend(
                [
                    PluginCapability("jvm_analysis", "1.0", "JVM bytecode analysis", 75),
                    PluginCapability("build_tool_integration", "1.0", "Build tool integration", 70),
                ]
            )

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

    def lookup(self, symbol: str, limit: int = 20) -> SymbolDef | None:
        """Look up symbol definition across all plugins."""
        start_time = time.time()

        try:
            # For symbol lookup, prefer BM25 direct lookup to avoid plugin loading delays
            # Only load plugins if explicitly needed and BM25 fails
            if self._sqlite_store:
                logger.debug("Using BM25 lookup directly for better performance")
                try:
                    import sqlite3

                    conn = sqlite3.connect(self._sqlite_store.db_path)
                    cursor = conn.cursor()

                    # First try symbols table for exact matches
                    cursor.execute(
                        """
                        SELECT s.name, s.kind, s.line_start, s.signature, s.documentation, f.path
                        FROM symbols s
                        JOIN files f ON s.file_id = f.id
                        WHERE s.name = ? OR s.name LIKE ?
                        ORDER BY CASE WHEN s.name = ? THEN 0 ELSE 1 END
                        LIMIT 1
                    """,
                        (symbol, f"%{symbol}%", symbol),
                    )

                    row = cursor.fetchone()
                    if row:
                        name, kind, line, signature, doc, filepath = row
                        conn.close()

                        # Return proper SymbolDef dict
                        return {
                            "symbol": name,
                            "kind": kind,
                            "language": "unknown",  # Not stored in symbols table
                            "signature": signature or f"{kind} {name}",
                            "doc": doc,
                            "defined_in": filepath,
                            "line": line or 1,
                            "span": (0, len(name)),
                        }

                    # Fallback to BM25 if available
                    try:
                        patterns = [
                            f"class {symbol}",
                            f"def {symbol}",
                            f"function {symbol}",
                            symbol,  # Try exact symbol match as fallback
                        ]

                        for pattern in patterns:
                            cursor.execute(
                                """
                                SELECT filepath, snippet(bm25_content, -1, '', '', '...', 20), language
                                FROM bm25_content
                                WHERE bm25_content MATCH ?
                                ORDER BY rank
                                LIMIT 1
                            """,
                                (pattern,),
                            )

                            row = cursor.fetchone()
                            if row:
                                filepath, snippet, language = row

                                # Determine kind from pattern
                                pattern_lower = pattern.lower()
                                if "class" in pattern_lower:
                                    kind = "class"
                                elif "def" in pattern_lower or "function" in pattern_lower:
                                    kind = "function"
                                else:
                                    kind = "symbol"

                                conn.close()

                                return {
                                    "symbol": symbol,
                                    "kind": kind,
                                    "language": language or "unknown",
                                    "signature": snippet,
                                    "doc": None,
                                    "defined_in": filepath,
                                    "line": 1,
                                    "span": (0, len(symbol)),
                                }
                    except sqlite3.OperationalError:
                        # BM25 table doesn't exist, that's fine
                        pass

                    conn.close()
                except Exception as e:
                    logger.error(f"Error in direct symbol lookup: {e}")

            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                definitions_by_plugin = {}
                for plugin in self._plugins:
                    try:
                        definition = plugin.getDefinition(symbol)
                        definitions_by_plugin[plugin] = definition
                    except Exception as e:
                        logger.warning(
                            f"Plugin {plugin.lang} failed to get definition for {symbol}: {e}"
                        )
                        definitions_by_plugin[plugin] = None

                result = self._aggregator.aggregate_symbol_definitions(definitions_by_plugin)

                self._operation_stats["lookups"] += 1
                self._operation_stats["total_time"] += time.time() - start_time

                return result
            else:
                # Fallback to basic lookup
                for p in self._plugins:
                    res = p.getDefinition(symbol)
                    if res:
                        self._operation_stats["lookups"] += 1
                        self._operation_stats["total_time"] += time.time() - start_time
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
        question_starters = [
            "how",
            "what",
            "where",
            "when",
            "why",
            "can",
            "is",
            "does",
            "should",
        ]
        first_word = query_lower.split()[0] if query_lower.split() else ""
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
            "install": ["installation", "setup", "getting started", "requirements"],
            "config": [
                "configuration",
                "configure",
                "settings",
                "options",
                "parameters",
            ],
            "api": ["api documentation", "api reference", "endpoint", "method"],
            "how to": ["tutorial", "guide", "example", "usage"],
            "example": ["sample", "snippet", "demo", "code example"],
            "error": ["troubleshoot", "debug", "issue", "problem", "fix"],
            "getting started": ["quickstart", "tutorial", "introduction", "setup"],
            "guide": ["tutorial", "documentation", "walkthrough", "how to"],
            "usage": ["how to use", "example", "api", "reference"],
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
                if word not in [
                    "how",
                    "to",
                    "the",
                    "a",
                    "an",
                    "is",
                    "are",
                    "what",
                    "where",
                    "when",
                ]:
                    topic_words.append(word)

            if topic_words:
                topic = " ".join(topic_words[:2])  # Use first two topic words
                expanded_queries.extend(
                    [
                        f"README {topic}",
                        f"{topic} documentation",
                        f"{topic} docs",
                        f"{topic} guide",
                    ]
                )

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

    def _adjust_ranking_for_documents(
        self, query: str, results: List[AggregatedResult]
    ) -> List[AggregatedResult]:
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
            if self._is_documentation_file(result.primary_result.get("file", "")):
                # Boost documentation files for document queries
                result.rank_score *= 1.5
                result.metadata["doc_boost"] = True
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
            # Quick BM25 bypass for non-semantic searches when plugins aren't loaded
            if (
                self._sqlite_store
                and not semantic
                and not self._semantic_enabled
                and (not self._plugins or len(self._plugins) == 0)
            ):
                logger.info(f"Using direct BM25 search bypass for query: {query}")
                try:
                    # Try different table names based on index schema
                    tables_to_try = ["bm25_content", "fts_code"]

                    for table in tables_to_try:
                        try:
                            results = self._sqlite_store.search_bm25(
                                query, table=table, limit=limit
                            )
                            if results:
                                for result in results:
                                    # Handle different result formats
                                    if "filepath" in result:
                                        file_path = result["filepath"]
                                    else:
                                        file_path = result.get("file_path", "")

                                    yield SearchResult(
                                        file_path=file_path,
                                        line=result.get("line", 0),
                                        column=result.get("column", 0),
                                        snippet=result.get("snippet", ""),
                                        score=result.get("score", 0.0),
                                        metadata=result.get("metadata", {}),
                                    )
                                self._operation_stats["searches"] += 1
                                self._operation_stats["total_time"] += time.time() - start_time
                                return  # Success, exit early
                        except Exception as e:
                            logger.debug(f"BM25 search in table '{table}' failed: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"Direct BM25 bypass failed: {e}")

            # For search, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()

            # If still no plugins, try hybrid or BM25 search directly
            if len(self._plugins) == 0 and self._sqlite_store:
                # Use semantic search if available and requested
                if semantic and self._semantic_indexer:
                    logger.info("No plugins loaded, using semantic search")
                    try:
                        # Search using semantic indexer
                        semantic_results = self._semantic_indexer.search(query=query, limit=limit)

                        for result in semantic_results:
                            # Extract file content for snippet
                            snippet = result.get("snippet", "")
                            if not snippet and "code" in result:
                                # Take first few lines of code as snippet
                                lines = result["code"].split("\n")
                                snippet = "\n".join(lines[:5])

                            yield {
                                "file": result.get("file_path", result.get("filepath", "")),
                                "line": result.get("line", 1),
                                "snippet": snippet,
                                "score": result.get("score", 0.0),
                                "language": result.get("metadata", {}).get("language", "unknown"),
                            }

                        self._operation_stats["searches"] += 1
                        self._operation_stats["total_time"] += time.time() - start_time
                        return
                    except Exception as e:
                        logger.error(f"Error in semantic search: {e}")
                        # Fall back to BM25

                # Fall back to BM25-only search
                logger.info("Using BM25 search directly")
                try:
                    import sqlite3

                    conn = sqlite3.connect(self._sqlite_store.db_path)
                    cursor = conn.cursor()

                    # Check if this is a BM25 index
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'"
                    )
                    if cursor.fetchone():
                        # Use BM25 search
                        cursor.execute(
                            """
                            SELECT 
                                filepath,
                                filename,
                                snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                                language,
                                rank
                            FROM bm25_content
                            WHERE bm25_content MATCH ?
                            ORDER BY rank
                            LIMIT ?
                        """,
                            (query, limit),
                        )

                        for row in cursor.fetchall():
                            filepath, filename, snippet, language, rank = row
                            yield {
                                "file": filepath,
                                "line": 1,
                                "snippet": snippet,
                                "score": abs(rank),
                                "language": language or "unknown",
                            }

                        conn.close()
                        self._operation_stats["searches"] += 1
                        self._operation_stats["total_time"] += time.time() - start_time
                        return

                    conn.close()
                except Exception as e:
                    logger.error(f"Error in direct BM25 search: {e}")

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
                opts = {
                    "semantic": semantic,
                    "limit": limit * 2 if is_doc_query else limit,
                }

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
                            logger.warning(
                                f"Plugin {plugin.lang} failed to search for {search_query}: {e}"
                            )

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
                        relevance_weight=0.5,  # Increase relevance weight
                        confidence_weight=0.2,  # Reduce confidence weight
                        frequency_weight=0.2,  # Keep frequency weight
                        recency_weight=0.1,  # Keep recency weight
                        prefer_exact_matches=False,  # Natural language doesn't need exact matches
                        boost_multiple_sources=True,
                        boost_common_extensions=True,
                    )
                    self._aggregator.configure(ranking_criteria=doc_criteria)

                aggregated_results, stats = self._aggregator.aggregate_search_results(
                    all_results_by_plugin, limit=limit * 2 if is_doc_query else limit
                )

                # Adjust ranking for document queries
                if is_doc_query:
                    aggregated_results = self._adjust_ranking_for_documents(
                        query, aggregated_results
                    )

                # Apply final limit
                if limit and len(aggregated_results) > limit:
                    aggregated_results = aggregated_results[:limit]

                logger.debug(
                    f"Search aggregation stats: {stats.total_results} total, "
                    f"{stats.unique_results} unique, {stats.plugins_used} plugins used, "
                    f"document_query={is_doc_query}"
                )

                self._operation_stats["searches"] += 1
                self._operation_stats["total_time"] += time.time() - start_time

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
                            logger.warning(
                                f"Plugin {p.lang} failed to search for {search_query}: {e}"
                            )

                # Deduplicate results
                seen = set()
                unique_results = []
                for result in all_results:
                    key = f"{result['file']}:{result['line']}"
                    if key not in seen:
                        seen.add(key)
                        unique_results.append(result)

                # Sort by score if available
                unique_results.sort(key=lambda r: r.get("score", 0.5) or 0.5, reverse=True)

                # Prioritize documentation files for document queries
                if is_doc_query:
                    doc_results = []
                    code_results = []
                    for result in unique_results:
                        if self._is_documentation_file(result.get("file", "")):
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

                self._operation_stats["searches"] += 1
                self._operation_stats["total_time"] += time.time() - start_time

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
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try with different encodings
                try:
                    content = path.read_text(encoding="latin-1")
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

            self._operation_stats["indexings"] += 1
            self._operation_stats["total_time"] += time.time() - start_time

            logger.info(
                f"Successfully indexed {path}: {len(shard.get('symbols', []))} symbols found"
            )

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
            "operations": self._operation_stats.copy(),
        }

        # Add language breakdown
        stats["by_language"] = {}
        for lang, plugin in self._by_lang.items():
            plugin_info = {"loaded": True, "class": plugin.__class__.__name__}
            if hasattr(plugin, "get_indexed_count"):
                plugin_info["indexed_files"] = plugin.get_indexed_count()
            stats["by_language"][lang] = plugin_info

        return stats

    def index_directory(self, directory: Path, recursive: bool = True) -> Dict[str, int]:
        """
        Index all files in a directory, respecting ignore patterns.

        Args:
            directory: Directory to index
            recursive: Whether to index subdirectories

        Returns:
            Statistics about indexed files
        """
        logger.info(f"Indexing directory: {directory} (recursive={recursive})")

        # Note: We don't use ignore patterns during indexing
        # ALL files are indexed for local search capability
        # Filtering happens only during export/sharing

        # Get all supported extensions
        supported_extensions = get_all_extensions()

        stats = {
            "total_files": 0,
            "indexed_files": 0,
            "ignored_files": 0,
            "failed_files": 0,
            "by_language": {},
        }

        # Walk directory
        if recursive:
            file_iterator = directory.rglob("*")
        else:
            file_iterator = directory.glob("*")

        for path in file_iterator:
            if not path.is_file():
                continue

            stats["total_files"] += 1

            # NOTE: We index ALL files locally, including gitignored ones
            # Filtering happens only during export/sharing
            # This allows local search of .env, secrets, etc.

            # Try to find a plugin that supports this file
            # This allows us to index ALL files, including .env, .key, etc.
            try:
                # First try to match by extension
                if path.suffix in supported_extensions:
                    self.index_file(path)
                    stats["indexed_files"] += 1
                # For files without recognized extensions, try each plugin's supports() method
                # This allows plugins to match by filename patterns (e.g., .env, Dockerfile)
                else:
                    matched = False
                    for plugin in self._plugins:
                        if plugin.supports(path):
                            self.index_file(path)
                            stats["indexed_files"] += 1
                            matched = True
                            break

                    # If no plugin matched but we want to index everything,
                    # we could add a fallback here to index as plaintext
                    # For now, we'll skip unmatched files
                    if not matched:
                        logger.debug(f"No plugin found for {path}")

                # Track by language
                language = get_language_by_extension(path.suffix)
                if language:
                    stats["by_language"][language] = stats["by_language"].get(language, 0) + 1

            except Exception as e:
                logger.error(f"Failed to index {path}: {e}")
                stats["failed_files"] += 1

        logger.info(
            f"Directory indexing complete: {stats['indexed_files']} indexed, "
            f"{stats['ignored_files']} ignored, {stats['failed_files']} failed"
        )

        return stats

    def search_documentation(
        self, topic: str, doc_types: Optional[List[str]] = None, limit: int = 20
    ) -> Iterable[SearchResult]:
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
            doc_types = [
                "readme",
                "documentation",
                "guide",
                "tutorial",
                "api",
                "changelog",
                "contributing",
            ]

        # Build search queries for different document types
        queries = []
        for doc_type in doc_types:
            queries.extend([f"{doc_type} {topic}", f"{topic} {doc_type}", f"{topic} in {doc_type}"])

        # Also search for the topic in common doc filenames
        queries.extend(
            [
                f"README {topic}",
                f"CONTRIBUTING {topic}",
                f"docs {topic}",
                f"documentation {topic}",
            ]
        )

        # Deduplicate queries
        queries = list(dict.fromkeys(queries))

        logger.info(f"Cross-document search for '{topic}' with {len(queries)} query variations")

        # Use the enhanced search with document-specific handling
        all_results = []
        seen = set()

        for query in queries[:10]:  # Limit to 10 queries to avoid too many searches
            for result in self.search(query, semantic=True, limit=limit):
                # Only include documentation files
                if self._is_documentation_file(result.get("file", "")):
                    key = f"{result['file']}:{result['line']}"
                    if key not in seen:
                        seen.add(key)
                        all_results.append(result)

        # Sort by relevance (score) and return top results
        all_results.sort(key=lambda r: r.get("score", 0.5) or 0.5, reverse=True)

        count = 0
        for result in all_results:
            if count >= limit:
                break
            yield result
            count += 1

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on all components."""
        health = {
            "status": "healthy",
            "components": {
                "dispatcher": {
                    "status": "healthy",
                    "plugins_loaded": len(self._plugins),
                    "languages_supported": len(self.supported_languages),
                    "factory_enabled": self._use_factory,
                    "lazy_loading": self._lazy_load,
                }
            },
            "plugins": {},
            "errors": [],
        }

        # Check plugin health
        for lang, plugin in self._by_lang.items():
            try:
                plugin_health = {
                    "status": "healthy",
                    "class": plugin.__class__.__name__,
                    "semantic_enabled": getattr(plugin, "_enable_semantic", False),
                }
                if hasattr(plugin, "get_indexed_count"):
                    plugin_health["indexed_files"] = plugin.get_indexed_count()
            except Exception as e:
                plugin_health = {"status": "error", "error": str(e)}
                health["errors"].append(f"Plugin {lang}: {str(e)}")

            health["plugins"][lang] = plugin_health

        # Determine overall health
        if len(health["errors"]) > 0:
            health["status"] = "degraded" if len(health["errors"]) < 3 else "unhealthy"

        return health

    def remove_file(self, path: Union[Path, str]) -> None:
        """Remove a file from all indexes.

        Args:
            path: File path to remove
        """
        path = Path(path).resolve()
        logger.info(f"Removing file from index: {path}")

        try:
            # Remove from SQLite if available
            if self._sqlite_store:
                from ..core.path_resolver import PathResolver

                path_resolver = PathResolver()
                try:
                    relative_path = path_resolver.normalize_path(path)
                    # Get repository ID - for now assume 1
                    # TODO: Properly detect repository
                    self._sqlite_store.remove_file(relative_path, repository_id=1)
                except Exception as e:
                    logger.error(f"Error removing from SQLite: {e}")

            # Remove from semantic index if available
            try:
                plugin = self._match_plugin(path)
                if plugin and hasattr(plugin, "_indexer") and plugin._indexer:
                    plugin._indexer.remove_file(path)
                    logger.info(f"Removed from semantic index: {path}")
            except Exception as e:
                logger.warning(f"Error removing from semantic index: {e}")

            # Update statistics
            self._operation_stats["deletions"] = self._operation_stats.get("deletions", 0) + 1

        except Exception as e:
            logger.error(f"Error removing file {path}: {e}", exc_info=True)

    def move_file(
        self,
        old_path: Union[Path, str],
        new_path: Union[Path, str],
        content_hash: Optional[str] = None,
    ) -> None:
        """Move a file in all indexes.

        Args:
            old_path: Original file path
            new_path: New file path
            content_hash: Optional content hash to verify unchanged content
        """
        old_path = Path(old_path).resolve()
        new_path = Path(new_path).resolve()
        logger.info(f"Moving file in index: {old_path} -> {new_path}")

        try:
            # Move in SQLite if available
            if self._sqlite_store:
                from ..core.path_resolver import PathResolver

                path_resolver = PathResolver()
                try:
                    old_relative = path_resolver.normalize_path(old_path)
                    new_relative = path_resolver.normalize_path(new_path)
                    # Get repository ID - for now assume 1
                    # TODO: Properly detect repository
                    self._sqlite_store.move_file(
                        old_relative,
                        new_relative,
                        repository_id=1,
                        content_hash=content_hash,
                    )
                except Exception as e:
                    logger.error(f"Error moving in SQLite: {e}")

            # Move in semantic index if available
            try:
                plugin = self._match_plugin(new_path)
                if plugin and hasattr(plugin, "_indexer") and plugin._indexer:
                    plugin._indexer.move_file(old_path, new_path, content_hash)
                    logger.info(f"Moved in semantic index: {old_path} -> {new_path}")
            except Exception as e:
                logger.warning(f"Error moving in semantic index: {e}")

            # Update statistics
            self._operation_stats["moves"] = self._operation_stats.get("moves", 0) + 1

        except Exception as e:
            logger.error(f"Error moving file {old_path} -> {new_path}: {e}", exc_info=True)

    async def cross_repo_symbol_search(
        self,
        symbol: str,
        repositories: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for a symbol across multiple repositories.

        Args:
            symbol: Symbol name to search for
            repositories: Optional list of specific repository IDs
            languages: Optional list of languages to filter by
            max_repositories: Maximum number of repositories to search

        Returns:
            Dictionary containing aggregated search results
        """
        if not self._cross_repo_coordinator:
            raise RuntimeError(
                "Cross-repository search not enabled. Set MCP_ENABLE_MULTI_REPO=true"
            )

        scope = SearchScope(
            repositories=repositories,
            languages=languages,
            max_repositories=max_repositories,
            priority_order=True,
        )

        try:
            result = await self._cross_repo_coordinator.search_symbol(symbol, scope)

            # Convert to dictionary format for MCP tools
            return {
                "query": result.query,
                "total_results": result.total_results,
                "repositories_searched": result.repositories_searched,
                "search_time": result.search_time,
                "results": result.results,
                "repository_stats": result.repository_stats,
                "deduplication_stats": result.deduplication_stats,
            }
        except Exception as e:
            logger.error(f"Cross-repository symbol search failed: {e}")
            return {
                "query": symbol,
                "total_results": 0,
                "repositories_searched": 0,
                "search_time": 0.0,
                "results": [],
                "repository_stats": {},
                "deduplication_stats": {},
                "error": str(e),
            }

    async def cross_repo_code_search(
        self,
        query: str,
        repositories: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None,
        semantic: bool = False,
        limit: int = 50,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for code patterns across multiple repositories.

        Args:
            query: Search query/pattern
            repositories: Optional list of specific repository IDs
            languages: Optional list of languages to filter by
            file_types: Optional list of file extensions to filter by
            semantic: Whether to use semantic search
            limit: Maximum number of results to return
            max_repositories: Maximum number of repositories to search

        Returns:
            Dictionary containing aggregated search results
        """
        if not self._cross_repo_coordinator:
            raise RuntimeError(
                "Cross-repository search not enabled. Set MCP_ENABLE_MULTI_REPO=true"
            )

        scope = SearchScope(
            repositories=repositories,
            languages=languages,
            file_types=file_types,
            max_repositories=max_repositories,
            priority_order=True,
        )

        try:
            result = await self._cross_repo_coordinator.search_code(query, scope, semantic, limit)

            # Convert to dictionary format for MCP tools
            return {
                "query": result.query,
                "total_results": result.total_results,
                "repositories_searched": result.repositories_searched,
                "search_time": result.search_time,
                "results": result.results,
                "repository_stats": result.repository_stats,
                "deduplication_stats": result.deduplication_stats,
            }
        except Exception as e:
            logger.error(f"Cross-repository code search failed: {e}")
            return {
                "query": query,
                "total_results": 0,
                "repositories_searched": 0,
                "search_time": 0.0,
                "results": [],
                "repository_stats": {},
                "deduplication_stats": {},
                "error": str(e),
            }

    async def get_cross_repo_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about cross-repository search capabilities.

        Returns:
            Dictionary containing repository statistics
        """
        if not self._cross_repo_coordinator:
            return {
                "enabled": False,
                "message": "Cross-repository search not enabled. Set MCP_ENABLE_MULTI_REPO=true",
            }

        try:
            stats = await self._cross_repo_coordinator.get_search_statistics()
            stats["enabled"] = True
            return stats
        except Exception as e:
            logger.error(f"Failed to get cross-repository statistics: {e}")
            return {
                "enabled": True,
                "error": str(e),
                "total_repositories": 0,
                "total_files": 0,
                "total_symbols": 0,
                "languages": [],
                "repository_details": [],
            }

    def _ensure_graph_initialized(self, file_paths: Optional[List[str]] = None) -> bool:
        """
        Ensure graph components are initialized.

        Args:
            file_paths: Optional list of files to build graph from

        Returns:
            True if graph is initialized, False otherwise
        """
        if not CHUNKER_AVAILABLE:
            logger.warning("Graph features not available: TreeSitter Chunker not installed")
            return False

        # If already initialized and no new files, return
        if self._graph_analyzer is not None and file_paths is None:
            return True

        try:
            # Initialize graph builder
            if self._graph_builder is None:
                self._graph_builder = XRefAdapter()

            # Build graph from files
            if file_paths:
                nodes, edges = self._graph_builder.build_graph(file_paths)
                self._graph_nodes = nodes
                self._graph_edges = edges

                # Initialize analyzer and selector
                self._graph_analyzer = GraphAnalyzer(nodes, edges)
                self._context_selector = ContextSelector(nodes, edges)

                logger.info(
                    f"Graph initialized: {len(nodes)} nodes, {len(edges)} edges"
                )
                return True
            else:
                # No files provided and not initialized
                return False

        except Exception as e:
            logger.error(f"Failed to initialize graph: {e}", exc_info=True)
            return False

    def graph_search(
        self,
        query: str,
        expansion_radius: int = 1,
        max_context_nodes: int = 50,
        semantic: bool = False,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """
        Search with graph-based context expansion.

        Args:
            query: Search query
            expansion_radius: How far to expand from search results
            max_context_nodes: Maximum context nodes to add
            semantic: Use semantic search
            limit: Maximum search results

        Returns:
            Search results with expanded context
        """
        # First, perform regular search
        search_results = list(self.search(query, semantic=semantic, limit=limit))

        if not search_results:
            return

        # Try to expand with graph context
        if self._context_selector:
            try:
                context_nodes = self._context_selector.expand_search_results(
                    search_results, expansion_radius, max_context_nodes
                )

                # Add context nodes as additional results
                for node in context_nodes:
                    # Check if already in results
                    already_included = any(
                        r.get("file") == node.file_path for r in search_results
                    )
                    if not already_included:
                        yield {
                            "file": node.file_path,
                            "line": node.line_start or 1,
                            "snippet": f"Context: {node.symbol or node.kind}",
                            "score": node.score,
                            "language": node.language,
                            "context": True,
                        }
            except Exception as e:
                logger.error(f"Error expanding search with graph: {e}")

        # Yield original results
        for result in search_results:
            yield result

    def get_context_for_symbols(
        self,
        symbols: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[GraphCutResult]:
        """
        Get optimal context for a list of symbols using graph cut.

        Args:
            symbols: Symbol names to find context for
            radius: Maximum distance from symbols
            budget: Maximum number of nodes in context
            weights: Scoring weights

        Returns:
            GraphCutResult or None if graph not available
        """
        if not self._context_selector:
            logger.warning("Context selector not initialized")
            return None

        try:
            # Find nodes matching symbols
            seed_nodes = []
            for node in self._graph_nodes:
                if node.symbol in symbols:
                    seed_nodes.append(node.id)

            if not seed_nodes:
                logger.warning(f"No graph nodes found for symbols: {symbols}")
                return None

            # Select context
            result = self._context_selector.select_context(
                seeds=seed_nodes, radius=radius, budget=budget, weights=weights
            )

            return result

        except Exception as e:
            logger.error(f"Error getting context for symbols: {e}", exc_info=True)
            return None

    def find_symbol_dependencies(
        self, symbol: str, max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find dependencies of a symbol.

        Args:
            symbol: Symbol name
            max_depth: Maximum depth to traverse

        Returns:
            List of dependent symbols with metadata
        """
        if not self._graph_analyzer:
            logger.warning("Graph analyzer not initialized")
            return []

        try:
            # Find node with this symbol
            node_id = None
            for node in self._graph_nodes:
                if node.symbol == symbol:
                    node_id = node.id
                    break

            if not node_id:
                logger.warning(f"Symbol not found in graph: {symbol}")
                return []

            # Get dependencies
            deps = self._graph_analyzer.find_dependencies(node_id, max_depth)

            # Convert to dict format
            return [
                {
                    "symbol": dep.symbol,
                    "file": dep.file_path,
                    "kind": dep.kind,
                    "language": dep.language,
                    "line": dep.line_start,
                }
                for dep in deps
            ]

        except Exception as e:
            logger.error(f"Error finding dependencies for {symbol}: {e}")
            return []

    def find_symbol_dependents(
        self, symbol: str, max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find dependents of a symbol (what depends on it).

        Args:
            symbol: Symbol name
            max_depth: Maximum depth to traverse

        Returns:
            List of dependent symbols with metadata
        """
        if not self._graph_analyzer:
            logger.warning("Graph analyzer not initialized")
            return []

        try:
            # Find node with this symbol
            node_id = None
            for node in self._graph_nodes:
                if node.symbol == symbol:
                    node_id = node.id
                    break

            if not node_id:
                logger.warning(f"Symbol not found in graph: {symbol}")
                return []

            # Get dependents
            dependents = self._graph_analyzer.find_dependents(node_id, max_depth)

            # Convert to dict format
            return [
                {
                    "symbol": dep.symbol,
                    "file": dep.file_path,
                    "kind": dep.kind,
                    "language": dep.language,
                    "line": dep.line_start,
                }
                for dep in dependents
            ]

        except Exception as e:
            logger.error(f"Error finding dependents for {symbol}: {e}")
            return []

    def get_code_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get code hotspots (highly connected nodes).

        Args:
            top_n: Number of hotspots to return

        Returns:
            List of hotspot information
        """
        if not self._graph_analyzer:
            logger.warning("Graph analyzer not initialized")
            return []

        try:
            hotspots = self._graph_analyzer.get_hotspots(top_n)

            return [
                {
                    "symbol": node.symbol,
                    "file": node.file_path,
                    "kind": node.kind,
                    "language": node.language,
                    "line": node.line_start,
                    "score": node.score,
                }
                for node in hotspots
            ]

        except Exception as e:
            logger.error(f"Error getting hotspots: {e}")
            return []
