"""Enhanced dispatcher with dynamic plugin loading via PluginFactory."""

import hashlib
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ..artifacts.semantic_profiles import SemanticProfileRegistry
from ..config.settings import reload_settings
from ..core.ignore_patterns import (
    IgnorePatternManager,
    build_walker_filter,
    EXCLUDED_DIR_PARTS as _INDEX_EXCLUDED_DIRS,
)
from ..core.repo_context import RepoContext
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
from ..plugins.plugin_set_registry import PluginSetRegistry
from ..plugins.repository_plugin_loader import RepositoryPluginLoader
from ..storage.multi_repo_manager import MultiRepositoryManager
from ..storage.sqlite_store import SQLiteStore
from ..utils.semantic_indexer import SemanticIndexer
from ..utils.semantic_indexer_registry import SemanticIndexerRegistry
from .cross_repo_coordinator import (
    CrossRepositorySearchCoordinator,
    SearchScope,
)
from .plugin_router import FileTypeMatcher, PluginCapability, PluginRouter
from .query_intent import QueryIntent
from .query_intent import classify as classify_query_intent
from .result_aggregator import (
    AggregatedResult,
    RankingCriteria,
    ResultAggregator,
)

logger = logging.getLogger(__name__)


_INDEX_EXCLUDED_FILENAMES = {
    "full_indexing_log.txt",
    "mcp_validation_results.json",
    "mcp_indexing_status.json",
    "semantic_indexing_progress.json",
    "mcp_indexing_summary.json",
    "complete_indexing_results.json",
    "mcp_direct_test_results.json",
    "test_queries.json",
}


def _get_profile_collection_name(profile: Any, fallback: str) -> str:
    """Return the configured collection name for a semantic profile."""
    build_metadata = getattr(profile, "build_metadata", None) or {}
    collection_name = build_metadata.get("collection_name")
    if isinstance(collection_name, str) and collection_name.strip():
        return collection_name.strip()
    return fallback


_INDEX_EXCLUDED_SUFFIXES = {
    ".xml",
}

# Path segment penalties for lexical (BM25/fuzzy) results.
# FTS5 scores are negative; adding a positive penalty degrades rank.
_PATH_PENALTY_RULES: List[Tuple[str, float]] = [
    ("htmlcov/", 10.0),  # coverage HTML — matches every string literally
    ("docs/benchmarks/", 10.0),  # benchmark JSON files contain literal query strings
    ("/tests/", 0.3),  # test files reference queries as test data
    ("makefile", 0.5),  # build files are lower signal than source code
]
_JSON_PENALTY = 0.5  # generic .json data files are lower signal than source code


def _path_score_penalty(file_path: str) -> float:
    """Return an additive BM25 score penalty for non-source paths.

    FTS5 bm25() scores are negative (more negative = better), so adding a
    positive value here degrades a result's rank without altering others.
    """
    p = file_path.replace("\\", "/").lower()
    for segment, penalty in _PATH_PENALTY_RULES:
        if segment in p:
            return penalty
    if p.endswith(".json"):
        return _JSON_PENALTY
    return 0.0


def _filename_token_boost(query: str, file_path: str) -> float:
    """Return a negative BM25 adjustment (rank improvement) when query terms
    appear in the filename stem.

    FTS5 bm25() scores are negative; a negative return value promotes the result.
    Mirrors the _fts_rank_adjustment logic in sqlite_store.py.
    """
    stem = Path(file_path).stem.lower()
    terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    stem_tokens = set(re.findall(r"[a-z0-9]+", stem))
    overlap = len(terms & stem_tokens)
    return -min(overlap, 3) * 0.6


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
        enable_advanced_features: bool = True,
        use_plugin_factory: bool = True,
        lazy_load: bool = True,
        semantic_search_enabled: bool = True,
        memory_aware: bool = True,
        multi_repo_enabled: bool = None,
        reranker_type: str = "none",
        plugin_set_registry: Optional[PluginSetRegistry] = None,
        semantic_indexer_registry: Optional[SemanticIndexerRegistry] = None,
    ):
        """Initialize the enhanced dispatcher.

        Args:
            plugins: Optional list of pre-instantiated plugins (for backward compatibility)
            enable_advanced_features: Whether to enable advanced routing and aggregation
            use_plugin_factory: Whether to use PluginFactory for dynamic loading
            lazy_load: Whether to lazy-load plugins on demand
            semantic_search_enabled: Whether to enable semantic search in plugins
            memory_aware: Whether to use memory-aware plugin management
            multi_repo_enabled: Whether to enable multi-repository support (None = auto from env)
            reranker_type: Reranker to use — "voyage", "flashrank", "cross-encoder", or "none"
        """
        self._memory_aware = memory_aware
        self._multi_repo_enabled = multi_repo_enabled

        # Repository-aware plugin components require a per-call ctx; initialized without store.
        self._repo_plugin_loader = None
        self._memory_manager = None

        # Initialize multi-repo manager if enabled
        if multi_repo_enabled is None:
            multi_repo_enabled = os.getenv("MCP_ENABLE_MULTI_REPO", "false").lower() == "true"

        if multi_repo_enabled:
            default_storage_path = Path.home() / ".mcp" / "indexes"
            storage_path = os.getenv("MCP_INDEX_STORAGE_PATH", str(default_storage_path))
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

        # Per-repo plugin registry (P3)
        self._plugin_set_registry: PluginSetRegistry = (
            plugin_set_registry if plugin_set_registry is not None else PluginSetRegistry()
        )
        # Legacy process-global plugin storage for callers that inject a pre-built plugin list.
        self._legacy_plugins: List[IPlugin] = []
        self._lang_cache: Dict[str, IPlugin] = {}
        self._loaded_languages: set[str] = set()

        # Cache for file hashes to avoid re-indexing unchanged files
        self._file_cache = {}  # path -> (mtime, size, content_hash)
        self._file_cache_lock = threading.RLock()

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

        # Per-repo semantic indexer registry (P3)
        self._semantic_registry: Optional[SemanticIndexerRegistry] = semantic_indexer_registry
        # Fallback process-global semantic indexer for repos not tracked by the registry.
        self._semantic_indexer_fallback: Optional[SemanticIndexer] = None
        if self._semantic_enabled and semantic_indexer_registry is None:
            try:
                settings = reload_settings()
                profile_registry = SemanticProfileRegistry.from_raw(
                    settings.get_semantic_profiles_config(),
                    settings.get_semantic_default_profile(),
                    tool_version=settings.app_version,
                )
                semantic_profile_id = settings.get_semantic_default_profile()
                semantic_profile = profile_registry.get(semantic_profile_id)
                if semantic_profile is None:
                    raise RuntimeError(
                        f"Semantic default profile '{semantic_profile_id}' is not available"
                    )

                qdrant_path = os.getenv("QDRANT_PATH", "vector_index.qdrant")
                collection_name = _get_profile_collection_name(
                    semantic_profile, settings.semantic_collection_name
                )

                if Path(qdrant_path).exists():
                    self._semantic_indexer_fallback = SemanticIndexer(
                        qdrant_path=qdrant_path,
                        collection=collection_name,
                        profile_registry=profile_registry,
                        semantic_profile=semantic_profile_id,
                    )
                    logger.info(
                        "Semantic search initialized: %s at %s (profile=%s)",
                        collection_name,
                        qdrant_path,
                        semantic_profile_id,
                    )
                else:
                    logger.warning(f"Qdrant path not found: {qdrant_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {e}")

        # Initialize reranker
        self._reranker = None  # type: Optional[Any]
        if reranker_type and reranker_type != "none":
            try:
                from ..indexer.reranker import (
                    CrossEncoderReranker,
                    FlashRankReranker,
                    VoyageReranker,
                )

                if reranker_type == "voyage":
                    voyage_model = os.getenv("VOYAGE_RERANK_MODEL", "rerank-2")
                    self._reranker = VoyageReranker(model=voyage_model)
                    logger.info(f"Reranker initialized: VoyageReranker model={voyage_model}")
                elif reranker_type == "flashrank":
                    flashrank_model = os.getenv("FLASHRANK_MODEL", "ms-marco-MiniLM-L-12-v2")
                    self._reranker = FlashRankReranker(model=flashrank_model)
                    logger.info(f"Reranker initialized: FlashRankReranker model={flashrank_model}")
                elif reranker_type == "cross-encoder":
                    ce_model = os.getenv(
                        "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    )
                    self._reranker = CrossEncoderReranker(model=ce_model)
                    logger.info(f"Reranker initialized: CrossEncoderReranker model={ce_model}")
                else:
                    logger.warning(f"Unknown reranker_type '{reranker_type}', disabling reranker")
            except Exception as e:
                logger.warning(f"Failed to initialize reranker: {e}")
        # Text-based rerankers degrade pure vector results; skip them on the semantic path.
        # VoyageReranker ("voyage") is consistent with Voyage embeddings so it is allowed.
        self._reranker_skips_semantic = reranker_type in ("flashrank", "cross-encoder")

        # Initialize legacy plugin list (backward compatibility for callers injecting plugins)
        if plugins:
            self._legacy_plugins = plugins
            self._lang_cache = {p.lang: p for p in plugins}
            for plugin in plugins:
                self._loaded_languages.add(getattr(plugin, "lang", "unknown"))
            if self._enable_advanced:
                self._register_plugins_with_router()
        elif use_plugin_factory and not lazy_load:
            self._load_all_plugins()

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

        logger.info("Enhanced dispatcher initialized")

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
            with timeout(30):  # 30 second timeout for startup plugin loading
                # Use repository-aware loading if available
                if self._repo_plugin_loader and self._memory_aware:
                    languages_to_load = self._repo_plugin_loader.get_required_plugins()
                    priority_order = self._repo_plugin_loader.get_priority_languages()
                    self._repo_plugin_loader.log_loading_plan()

                    for lang in priority_order:
                        if lang in languages_to_load:
                            try:
                                if self._memory_manager:
                                    plugin = self._memory_manager.get_plugin(lang)
                                else:
                                    plugin = PluginFactory.create_plugin(
                                        lang, None, self._semantic_enabled
                                    )

                                if plugin:
                                    self._legacy_plugins.append(plugin)
                                    self._lang_cache[lang] = plugin
                                    self._loaded_languages.add(lang)
                                    self._operation_stats["plugins_loaded"] += 1
                                    self._repo_plugin_loader.mark_loaded(lang)
                            except Exception as e:
                                logger.error(f"Failed to load {lang} plugin: {e}")
                else:
                    all_plugins = PluginFactory.create_all_plugins(
                        sqlite_store=None,
                        enable_semantic=self._semantic_enabled,
                    )

                    for lang, plugin in all_plugins.items():
                        self._legacy_plugins.append(plugin)
                        self._lang_cache[lang] = plugin
                        self._loaded_languages.add(lang)
                        self._operation_stats["plugins_loaded"] += 1

                if self._enable_advanced:
                    self._register_plugins_with_router()

                logger.info(
                    f"Loaded {len(self._legacy_plugins)} plugins: {', '.join(sorted(self._loaded_languages))}"
                )

        except TimeoutError as e:
            logger.warning(f"Plugin loading timeout: {e}")
            self._legacy_plugins = []
            self._loaded_languages = set()
        except Exception as e:
            logger.error(f"Plugin loading failed: {e}")
            self._legacy_plugins = []
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
        if language in self._lang_cache:
            return self._lang_cache[language]

        # If not using factory or already tried to load, return None
        if not self._use_factory or language in self._loaded_languages:
            return None

        # Try to load the plugin
        try:
            logger.info(f"Lazy loading plugin for {language}")
            plugin = PluginFactory.create_plugin(
                language,
                sqlite_store=None,
                enable_semantic=self._semantic_enabled,
            )

            # Add to legacy collections
            self._legacy_plugins.append(plugin)
            self._lang_cache[language] = plugin
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

        # Fallback: try all loaded legacy plugins
        for plugin in self._legacy_plugins:
            if plugin.supports(path):
                return plugin

        return None

    def _register_plugins_with_router(self):
        """Register legacy plugins with the router and assign capabilities."""
        for plugin in self._legacy_plugins:
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

    def plugins(self) -> List[IPlugin]:
        """Return all loaded legacy plugins."""
        return list(self._legacy_plugins)

    def supported_languages(self) -> List[str]:
        """Get list of all supported languages (loaded and available)."""
        if self._use_factory:
            return PluginFactory.get_supported_languages()
        else:
            return list(self._lang_cache.keys())

    def _get_file_hash(self, content: str) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _should_reindex(self, path: Path, content: str) -> bool:
        """Return True if the file needs to be (re-)indexed."""
        key = str(path)
        with self._file_cache_lock:
            if key not in self._file_cache:
                return True
            cached_mtime, cached_size, cached_hash = self._file_cache[key]
        try:
            stat = path.stat()
            if stat.st_mtime == cached_mtime and stat.st_size == cached_size:
                return False
            return self._get_file_hash(content) != cached_hash
        except OSError:
            return True

    def _match_plugin(self, path: Path) -> IPlugin:
        """Match a plugin for the given file path."""
        # Check explicitly-registered legacy plugins first
        for p in self._legacy_plugins:
            if p.supports(path):
                return p

        # Fall back to lazy loading via factory
        if self._lazy_load and self._use_factory:
            plugin = self._ensure_plugin_for_file(path)
            if plugin:
                return plugin

        # Use advanced routing if available
        if self._enable_advanced and self._router:
            route_result = self._router.get_best_plugin(path)
            if route_result:
                return route_result.plugin

        raise RuntimeError(f"No plugin for {path}")

    def get_plugins_for_file(self, ctx: RepoContext, path: Path) -> List[Tuple[IPlugin, float]]:
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
            for plugin in self._legacy_plugins:
                if plugin.supports(path):
                    matching_plugins.append((plugin, 1.0))
            return matching_plugins

    def lookup(self, ctx: RepoContext, symbol: str, limit: int = 20) -> Optional[SymbolDef]:
        """Look up symbol definition within ctx.repo_id."""
        start_time = time.time()

        try:
            # For symbol lookup, prefer BM25 direct lookup to avoid plugin loading delays
            # Only load plugins if explicitly needed and BM25 fails
            if ctx.sqlite_store:
                logger.debug("Using BM25 lookup directly for better performance")
                try:
                    import sqlite3

                    conn = sqlite3.connect(ctx.sqlite_store.db_path)
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

            repo_plugins = self._plugin_set_registry.plugins_for(ctx.repo_id)
            if self._enable_advanced and self._aggregator:
                # Use advanced aggregation
                definitions_by_plugin = {}
                for plugin in repo_plugins:
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
                for p in repo_plugins:
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

    def _get_chunk_content_for_reranking(self, sqlite_store: Optional[SQLiteStore], file_path: str) -> str:
        """Return the best chunk content for a file to use as reranker document text."""
        if not sqlite_store or not file_path:
            return ""
        try:
            file_id = sqlite_store.get_file_id_by_path(file_path)
            if file_id is None:
                return ""
            chunk = sqlite_store.find_best_chunk_for_file(file_id, [])
            return chunk.get("content", "") if chunk else ""
        except Exception:
            return ""

    def _symbol_route(self, sqlite_store: Optional[SQLiteStore], name: str, kind: Optional[str], limit: int) -> List[Dict]:
        """Query the symbols table directly and return search-result-shaped dicts."""
        if not sqlite_store:
            return []
        try:
            rows = sqlite_store.get_symbol(name, kind=kind)
            if not rows and kind:
                # Relax kind constraint and retry
                rows = sqlite_store.get_symbol(name, kind=None)
            if not rows:
                return []

            # Sort: non-__init__ files first, then by line number ascending
            def _rank(row: Dict) -> tuple:
                fp = (row.get("file_path") or "").replace("\\", "/")
                is_init = 1 if (fp.endswith("/__init__.py") or fp == "__init__.py") else 0
                return (is_init, row.get("line_start", 0))

            rows.sort(key=_rank)
            results = []
            for row in rows[:limit]:
                file_path = row.get("file_path", "")
                snippet = row.get("signature") or row.get("documentation") or ""
                results.append(
                    {
                        "file": file_path,
                        "line": row.get("line_start", 1),
                        "line_end": row.get("line_end"),
                        "symbol": row.get("name"),
                        "snippet": snippet,
                        "score": 1.0,
                        "language": "unknown",
                    }
                )
            return results
        except Exception as e:
            logger.warning(f"Symbol route failed for '{name}': {e}")
            return []

    def _apply_reranker(
        self,
        sqlite_store: Optional[SQLiteStore],
        query: str,
        candidates: List[Dict],
        limit: int,
        semantic_source: bool = False,
    ) -> List[Dict]:
        """Enrich candidates with chunk text and apply the reranker if configured."""
        if self._reranker is None:
            return candidates[:limit]
        if semantic_source and self._reranker_skips_semantic:
            return candidates[:limit]
        # Exclude paths with penalty >= 1.0 (benchmark/coverage noise files).
        filtered = [c for c in candidates if _path_score_penalty(c.get("file", "")) < 1.0]
        if not filtered:
            filtered = candidates
        for c in filtered:
            if not c.get("_rerank_doc"):
                c["_rerank_doc"] = self._get_chunk_content_for_reranking(sqlite_store, c.get("file", ""))
        try:
            return self._reranker.rerank(query, filtered, limit)
        except Exception as e:
            logger.warning(f"_apply_reranker failed, returning original order: {e}")
            return candidates[:limit]

    def _get_semantic_indexer(self, ctx: RepoContext) -> Optional[SemanticIndexer]:
        """Return the SemanticIndexer for ctx.repo_id, or the fallback if no registry."""
        if self._semantic_registry is not None:
            try:
                return self._semantic_registry.get(ctx.repo_id)
            except (KeyError, Exception):
                return None
        return self._semantic_indexer_fallback

    def search(
        self,
        ctx: RepoContext,
        query: str,
        semantic: bool = False,
        fuzzy: bool = False,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Search for code and documentation scoped to ctx.repo_id."""
        start_time = time.time()
        sqlite_store = ctx.sqlite_store
        _semantic_indexer = self._get_semantic_indexer(ctx)
        repo_plugins = self._plugin_set_registry.plugins_for(ctx.repo_id)

        try:
            # Fuzzy (trigram) path for misspelled queries
            if fuzzy and sqlite_store:
                logger.info(f"Using fuzzy trigram search for query: {query}")
                try:
                    sym_results = sqlite_store.search_symbols_fuzzy(query, limit)
                    file_results = sqlite_store.search_files_fuzzy(query, limit)

                    # Merge by file_path, keeping best score
                    merged: Dict[str, Dict] = {}
                    for r in sym_results:
                        fp = r.get("file_path", "")
                        if fp and (fp not in merged or r.get("score", 0) > merged[fp]["score"]):
                            merged[fp] = {
                                "file": fp,
                                "score": r.get("score", 0),
                                "line": r.get("line_start", 1),
                                "snippet": r.get("name", ""),
                                "language": r.get("language", "unknown"),
                            }
                    for r in file_results:
                        fp = r.get("file_path", "")
                        if fp and (fp not in merged or r.get("score", 0) > merged[fp]["score"]):
                            merged[fp] = {
                                "file": fp,
                                "score": r.get("score", 0),
                                "line": 1,
                                "snippet": "",
                                "language": "unknown",
                            }

                    sorted_results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
                    for item in sorted_results[:limit]:
                        yield item
                    self._operation_stats["searches"] += 1
                    self._operation_stats["total_time"] += time.time() - start_time
                    return
                except Exception as e:
                    logger.warning(f"Fuzzy search failed: {e}")

            # Prefer direct SQLite lexical search for non-semantic queries so the
            # server remains useful even when plugin in-memory indexes are cold.
            if sqlite_store and (not semantic or _semantic_indexer is None):
                # Symbol routing: bypass BM25 for explicit symbol-pattern queries.
                intent, sym_name, kind_hint = classify_query_intent(query)
                if intent == QueryIntent.SYMBOL:
                    sym_results = self._symbol_route(sqlite_store, sym_name, kind_hint, limit)
                    if sym_results:
                        logger.info(
                            f"Symbol route hit for '{query}' → '{sym_name}' "
                            f"({len(sym_results)} result(s))"
                        )
                        yield from sym_results
                        self._operation_stats["searches"] += 1
                        self._operation_stats["total_time"] += time.time() - start_time
                        return

                logger.info(f"Using direct lexical search for query: {query}")
                try:
                    tables_to_try = ["bm25_content", "fts_code"]

                    for table in tables_to_try:
                        try:
                            # Fetch an oversampled set so path-based penalties can
                            # surface results that BM25 ranked below the cutoff.
                            fetch_limit = max(limit * 8, 50)
                            results = sqlite_store.search_bm25(
                                query, table=table, limit=fetch_limit
                            )
                            if len(results) < fetch_limit:
                                or_query = " OR ".join(
                                    t for t in query.split() if re.match(r"[a-zA-Z0-9_]", t)
                                )
                                if or_query != query:
                                    or_results = sqlite_store.search_bm25(
                                        or_query, table=table, limit=fetch_limit
                                    )
                                    and_paths = {
                                        r.get("filepath") or r.get("file_path", "") for r in results
                                    }
                                    for r in or_results:
                                        fp = r.get("filepath") or r.get("file_path", "")
                                        if fp not in and_paths:
                                            results.append(r)
                            if results:
                                # Apply path-based score penalty and filename token
                                # boost, re-sort, truncate.
                                # FTS5 bm25() scores are negative; adding a positive
                                # penalty degrades rank for non-source paths; a
                                # negative boost from _filename_token_boost improves it.
                                scored = []
                                for result in results:
                                    file_path = result.get("filepath") or result.get(
                                        "file_path", ""
                                    )
                                    raw = result.get("score", 0.0)
                                    adjusted = (
                                        raw
                                        + _path_score_penalty(file_path)
                                        + _filename_token_boost(query, file_path)
                                    )
                                    scored.append((adjusted, file_path, result))
                                scored.sort(key=lambda t: t[0])
                                bm25_candidates = []
                                for adjusted, file_path, result in scored[:limit]:
                                    chunk = None
                                    file_id = result.get("file_id")
                                    if file_id is not None:
                                        try:
                                            chunk = sqlite_store.find_best_chunk_for_file(
                                                int(file_id), query.split()
                                            )
                                        except Exception:
                                            chunk = None
                                    bm25_candidates.append(
                                        {
                                            "file": file_path,
                                            "line": (
                                                chunk["line_start"]
                                                if chunk
                                                else result.get("line", 1)
                                            ),
                                            "line_end": chunk["line_end"] if chunk else None,
                                            "symbol": chunk["symbol"] if chunk else None,
                                            "snippet": result.get("snippet", ""),
                                            "score": adjusted,
                                            "language": result.get("language", "unknown"),
                                        }
                                    )
                                bm25_candidates = self._apply_reranker(
                                    sqlite_store, query, bm25_candidates, limit
                                )
                                for item in bm25_candidates:
                                    yield {k: v for k, v in item.items() if k != "_rerank_doc"}
                                self._operation_stats["searches"] += 1
                                self._operation_stats["total_time"] += time.time() - start_time
                                return
                        except Exception as e:
                            logger.debug(f"Lexical search in table '{table}' failed: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Direct lexical search failed: {e}")

            # Semantic queries go directly to the vector index — plugins explicitly
            # return [] for semantic=True, so bypassing them is correct.
            if semantic and _semantic_indexer:
                logger.info(f"Using semantic indexer for query: {query}")
                try:
                    semantic_results = _semantic_indexer.search(query=query, limit=limit)
                    candidates = []
                    for result in semantic_results:
                        snippet = result.get("snippet", "")
                        if not snippet and "code" in result:
                            lines = result["code"].split("\n")
                            snippet = "\n".join(lines[:5])
                        file_value = (
                            result.get("relative_path")
                            or result.get("file")
                            or result.get("path")
                            or result.get("file_path")
                            or result.get("filepath")
                            or ""
                        )
                        raw_score = result.get("score", 0.0)
                        # Apply a mild penalty for artifact support paths in semantic results.
                        # The artifacts/ directory holds secondary routing/policy helpers, not
                        # primary implementations, so demote them relative to core code.
                        fp_lower = file_value.replace("\\", "/").lower()
                        if "/artifacts/" in fp_lower:
                            raw_score *= 0.85
                        candidates.append(
                            {
                                "file": file_value,
                                "line": result.get("line", 1),
                                "snippet": snippet,
                                "score": raw_score,
                                "language": result.get("metadata", {}).get("language", "unknown"),
                            }
                        )
                    # Re-sort by adjusted score so penalties take effect before reranking.
                    candidates.sort(key=lambda c: c["score"], reverse=True)
                    candidates = self._apply_reranker(
                        sqlite_store, query, candidates, limit, semantic_source=True
                    )
                    for item in candidates:
                        yield {k: v for k, v in item.items() if k != "_rerank_doc"}
                    self._operation_stats["searches"] += 1
                    self._operation_stats["total_time"] += time.time() - start_time
                    return
                except Exception as e:
                    logger.warning(f"Semantic indexer search failed, falling back to plugins: {e}")

            # For search, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(repo_plugins) == 0:
                self._load_all_plugins()
                repo_plugins = self._plugin_set_registry.plugins_for(ctx.repo_id)

            # If still no plugins, try hybrid or BM25 search directly
            if len(repo_plugins) == 0 and sqlite_store:
                # Use semantic search if available and requested
                if semantic and _semantic_indexer:
                    logger.info("No plugins loaded, using semantic search")
                    try:
                        semantic_results = _semantic_indexer.search(query=query, limit=limit)
                        for result in semantic_results:
                            snippet = result.get("snippet", "")
                            if not snippet and "code" in result:
                                lines = result["code"].split("\n")
                                snippet = "\n".join(lines[:5])
                            file_value = (
                                result.get("relative_path")
                                or result.get("file")
                                or result.get("path")
                                or result.get("file_path")
                                or result.get("filepath")
                                or ""
                            )
                            yield {
                                "file": file_value,
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

                    conn = sqlite3.connect(sqlite_store.db_path)
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
                    for plugin in repo_plugins:
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

                # Deduplicate results per plugin (handle both dict results and SearchResult objects)
                for plugin, results in all_results_by_plugin.items():
                    seen = set()
                    unique_results = []
                    for result in results:
                        if hasattr(result, "path"):
                            key = f"{result.path}:{getattr(result, 'line', 0)}"
                        else:
                            key = f"{result.get('file', result.get('path', ''))}:{result.get('line', 0)}"
                        if key not in seen:
                            seen.add(key)
                            unique_results.append(result)
                    all_results_by_plugin[plugin] = unique_results

                # Determine if we have plugin SearchResult dicts (have "path"/"name", not "file")
                # vs BM25 dict results (have "file" key). Plugin results bypass the dict-only aggregator.
                first_result = next(
                    (r for results in all_results_by_plugin.values() for r in results), None
                )
                is_search_result_objects = first_result is not None and (
                    hasattr(first_result, "path")  # dataclass
                    or (
                        isinstance(first_result, dict)
                        and "path" in first_result
                        and "file" not in first_result
                    )
                )

                if is_search_result_objects:
                    # Plugin SearchResult objects: flatten and sort by score, bypassing dict-only aggregator
                    all_search_results = []
                    for results in all_results_by_plugin.values():
                        all_search_results.extend(results)
                    all_search_results.sort(key=lambda r: getattr(r, "score", 0), reverse=True)
                    self._operation_stats["searches"] += 1
                    self._operation_stats["total_time"] += time.time() - start_time
                    for r in all_search_results[:limit]:
                        yield r
                else:
                    # BM25/dict results: use full aggregation pipeline
                    # Configure aggregator for document queries
                    if is_doc_query and self._enable_advanced:
                        doc_criteria = RankingCriteria(
                            relevance_weight=0.5,
                            confidence_weight=0.2,
                            frequency_weight=0.2,
                            recency_weight=0.1,
                            prefer_exact_matches=False,
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
                    for p in repo_plugins:
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

    def index_file(self, ctx: RepoContext, path: Path, do_semantic: bool = True) -> None:
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

            # Skip if file hasn't changed since last index
            if not self._should_reindex(path, content):
                logger.debug(f"Skipping {path} (unchanged)")
                return

            # Index the file
            start_time = time.time()
            logger.info(f"Indexing {path} with {plugin.lang} plugin")
            shard = plugin.indexFile(path, content)

            # Update file cache after successful indexing
            try:
                stat = path.stat()
                with self._file_cache_lock:
                    self._file_cache[str(path)] = (
                        stat.st_mtime,
                        stat.st_size,
                        self._get_file_hash(content),
                    )
            except OSError:
                pass

            # Record performance if advanced features enabled
            if self._enable_advanced and self._router:
                execution_time = time.time() - start_time
                self._router.record_performance(plugin, execution_time)

            self._operation_stats["indexings"] += 1
            self._operation_stats["total_time"] += time.time() - start_time

            logger.info(
                f"Successfully indexed {path}: {len(shard.get('symbols', []))} symbols found"
            )

            # Semantic indexing for incremental single-file updates
            _sem = self._get_semantic_indexer(ctx)
            if do_semantic and _sem:
                try:
                    _sem.index_file(path)
                except Exception as e:
                    logger.warning(f"Semantic indexing failed for {path}: {e}")

        except RuntimeError as e:
            # No plugin found for this file type
            logger.debug(f"No plugin for {path}: {e}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}", exc_info=True)

    def get_statistics(self, ctx: RepoContext) -> Dict[str, Any]:
        """Get statistics about indexed files and languages."""
        try:
            by_language: Dict[str, int] = {}
            with self._file_cache_lock:
                cached_paths = list(self._file_cache.keys())
            for file_path in cached_paths:
                for lang, plugin in self._lang_cache.items():
                    if plugin.supports(Path(file_path)):
                        by_language[lang] = by_language.get(lang, 0) + 1
                        break
            return {
                "total": len(cached_paths),
                "by_language": by_language,
            }
        except Exception:
            return {"total": 0, "by_language": {}}

    def index_directory(self, ctx: RepoContext, directory: Path, recursive: bool = True) -> Dict[str, int]:
        """Index all files in a directory, respecting ignore patterns."""
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

        is_excluded = build_walker_filter(directory)

        # Walk directory while pruning excluded directories early.
        if recursive:

            def iter_files() -> Iterable[Path]:
                # followlinks=False (default, made explicit) keeps us cycle-safe.
                for current_root, dirnames, filenames in os.walk(directory, followlinks=False):
                    dirnames[:] = [d for d in dirnames if d not in _INDEX_EXCLUDED_DIRS]
                    root_path = Path(current_root)
                    for filename in filenames:
                        yield root_path / filename

        else:

            def iter_files() -> Iterable[Path]:
                for path in directory.glob("*"):
                    if path.is_file():
                        yield path

        # Collect paths that were successfully indexed for batch semantic embedding
        semantically_indexed_paths: List[Path] = []

        for path in iter_files():
            if not path.is_file():
                continue

            stats["total_files"] += 1

            relative_parts = (
                path.relative_to(directory).parts if path.is_relative_to(directory) else path.parts
            )
            if any(part.endswith(".egg-info") for part in relative_parts):
                stats["ignored_files"] += 1
                continue

            if path.name in _INDEX_EXCLUDED_FILENAMES:
                stats["ignored_files"] += 1
                continue

            if path.suffix.lower() in _INDEX_EXCLUDED_SUFFIXES:
                stats["ignored_files"] += 1
                continue

            if is_excluded(path):
                stats["ignored_files"] += 1
                continue

            # Try to find a plugin that supports this file
            # This allows us to index ALL files, including .env, .key, etc.
            try:
                # First try to match by extension
                if path.suffix in supported_extensions:
                    # skip_semantic=True — we'll batch semantic embed after the loop
                    self.index_file(ctx, path, do_semantic=False)
                    stats["indexed_files"] += 1
                    semantically_indexed_paths.append(path.resolve())
                # For files without recognized extensions, try each plugin's supports() method
                # This allows plugins to match by filename patterns (e.g., .env, Dockerfile)
                else:
                    matched = False
                    for plugin in self._plugin_set_registry.plugins_for(ctx.repo_id):
                        if plugin.supports(path):
                            self.index_file(ctx, path, do_semantic=False)
                            stats["indexed_files"] += 1
                            semantically_indexed_paths.append(path.resolve())
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

        # Batch semantic embedding — O(n/1000) API calls instead of O(n)
        _sem = self._get_semantic_indexer(ctx)
        stats["semantic_paths_queued"] = len(semantically_indexed_paths)
        stats["semantic_indexer_present"] = _sem is not None
        if _sem and semantically_indexed_paths:
            logger.info(
                f"Batch semantic indexing {len(semantically_indexed_paths)} files "
                f"(embed_batch_size=1000)"
            )
            try:
                sem_stats = _sem.index_files_batch(
                    semantically_indexed_paths, embed_batch_size=1000
                )
                stats["semantic_indexed"] = sem_stats.get("files_indexed", 0)
                stats["semantic_failed"] = sem_stats.get("files_failed", 0)
                stats["semantic_skipped"] = sem_stats.get("files_skipped", 0)
                stats["total_embedding_units"] = sem_stats.get("total_embedding_units", 0)
                logger.info(
                    f"Semantic batch complete: {sem_stats.get('files_indexed', 0)} indexed, "
                    f"{sem_stats.get('files_skipped', 0)} skipped, "
                    f"{sem_stats.get('total_embedding_units', 0)} embedding units"
                )
            except Exception as e:
                logger.error(f"Batch semantic indexing failed: {e}", exc_info=True)
                stats["semantic_error"] = str(e)

        logger.info(
            f"Directory indexing complete: {stats['indexed_files']} indexed, "
            f"{stats['ignored_files']} ignored, {stats['failed_files']} failed"
        )

        return stats

    def search_documentation(
        self,
        ctx: RepoContext,
        topic: str,
        doc_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Search specifically across documentation files scoped to ctx.repo_id.

        Args:
            ctx: Repository context for storage routing
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

        for query in queries[:10]:
            for result in self.search(ctx, query, semantic=True, limit=limit):
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

    def health_check(self, ctx: RepoContext) -> Dict[str, Any]:
        """Perform a health check on all components."""
        health = {
            "status": "healthy",
            "components": {
                "dispatcher": {
                    "status": "healthy",
                    "plugins_loaded": len(self._plugin_set_registry.plugins_for(ctx.repo_id)),
                    "languages_supported": len(self.supported_languages()),
                    "factory_enabled": self._use_factory,
                    "lazy_loading": self._lazy_load,
                }
            },
            "plugins": {},
            "errors": [],
        }

        # Check plugin health
        for lang, plugin in self._lang_cache.items():
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

    def remove_file(self, ctx: RepoContext, path: Union[Path, str]) -> None:
        """Remove a file from all per-repo indexes."""
        path = Path(path).resolve()
        logger.info(f"Removing file from index: {path}")

        # Evict from skip cache so a subsequent index_file() call is not skipped
        with self._file_cache_lock:
            self._file_cache.pop(str(path), None)

        try:
            # Remove from SQLite if available
            if ctx.sqlite_store:
                from ..core.path_resolver import PathResolver

                path_resolver = PathResolver()
                try:
                    relative_path = path_resolver.normalize_path(path)
                    ctx.sqlite_store.remove_file(relative_path, repository_id=1)
                except Exception as e:
                    logger.error(f"Error removing from SQLite: {e}")

            # Remove from plugin fuzzy index if available
            try:
                plugin = self._match_plugin(path)
                if plugin and hasattr(plugin, "_indexer") and plugin._indexer:
                    plugin._indexer.remove_file(path)
            except Exception as e:
                logger.warning(f"Error removing from plugin index: {e}")

            # Remove from Qdrant semantic index if available
            _sem = self._get_semantic_indexer(ctx)
            if _sem is not None:
                try:
                    _sem.remove_file(path)
                    logger.info("Removed %s from semantic index", path)
                except Exception as e:
                    logger.warning("Failed to remove %s from semantic index: %s", path, e)

            # Update statistics
            self._operation_stats["deletions"] = self._operation_stats.get("deletions", 0) + 1

        except Exception as e:
            logger.error(f"Error removing file {path}: {e}", exc_info=True)

    def move_file(
        self,
        ctx: RepoContext,
        old_path: Union[Path, str],
        new_path: Union[Path, str],
        content_hash: Optional[str] = None,
    ) -> None:
        """Relocate a file in the per-repo index."""
        old_path = Path(old_path).resolve()
        new_path = Path(new_path).resolve()
        logger.info(f"Moving file in index: {old_path} -> {new_path}")

        try:
            # Move in SQLite if available
            if ctx.sqlite_store:
                from ..core.path_resolver import PathResolver

                path_resolver = PathResolver()
                try:
                    old_relative = path_resolver.normalize_path(old_path)
                    new_relative = path_resolver.normalize_path(new_path)
                    ctx.sqlite_store.move_file(
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
        contexts: List[RepoContext],
        symbol: str,
        languages: Optional[List[str]] = None,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """Fan symbol-lookup across the provided repo contexts."""
        if not self._cross_repo_coordinator:
            raise RuntimeError(
                "Cross-repository search not enabled. Set MCP_ENABLE_MULTI_REPO=true"
            )

        repositories = [ctx.repo_id for ctx in contexts]
        scope = SearchScope(
            repositories=repositories,
            languages=languages,
            max_repositories=max_repositories,
            priority_order=True,
        )

        try:
            result = await self._cross_repo_coordinator.search_symbol(symbol, scope)
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
        contexts: List[RepoContext],
        query: str,
        languages: Optional[List[str]] = None,
        semantic: bool = False,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """Fan code-search across the provided repo contexts."""
        if not self._cross_repo_coordinator:
            raise RuntimeError(
                "Cross-repository search not enabled. Set MCP_ENABLE_MULTI_REPO=true"
            )

        repositories = [ctx.repo_id for ctx in contexts]
        scope = SearchScope(
            repositories=repositories,
            languages=languages,
            max_repositories=max_repositories,
            priority_order=True,
        )

        try:
            result = await self._cross_repo_coordinator.search_code(query, scope, semantic)

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

    async def get_cross_repo_statistics(self, contexts: List[RepoContext]) -> Dict[str, Any]:
        """Aggregate statistics across the provided repo contexts."""
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

                logger.info(f"Graph initialized: {len(nodes)} nodes, {len(edges)} edges")
                return True
            else:
                # No files provided and not initialized
                return False

        except Exception as e:
            logger.error(f"Failed to initialize graph: {e}", exc_info=True)
            return False

    def graph_search(
        self,
        ctx: RepoContext,
        query: str,
        expansion_radius: int = 1,
        max_context_nodes: int = 50,
        semantic: bool = False,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Search with graph-based context expansion within ctx.repo_id."""
        # First, perform regular search
        search_results = list(self.search(ctx, query, semantic=semantic, limit=limit))

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
                    already_included = any(r.get("file") == node.file_path for r in search_results)
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
        ctx: RepoContext,
        symbols: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[GraphCutResult]:
        """Budgeted graph-cut over the symbols' neighborhood within ctx.repo_id.

        Args:
            ctx: Repository context
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

    def find_symbol_dependencies(self, ctx: RepoContext, symbol: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Outgoing dependency walk from symbol within ctx.repo_id.

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

    def find_symbol_dependents(self, ctx: RepoContext, symbol: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Incoming dependent walk into symbol within ctx.repo_id.
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

    def get_code_hotspots(self, ctx: RepoContext, top_n: int = 10) -> List[Dict[str, Any]]:
        """Highest-centrality symbols in the per-repo call graph.

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
