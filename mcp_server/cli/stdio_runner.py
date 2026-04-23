"""MCP stdio server runner — IF-0-P2B-3 / IF-0-P18-3 implementation.

Wires the MCP Server, list_tools(), and call_tool() dispatcher using
tool_handlers. Invoked by server_commands:stdio() and the shim at
scripts/cli/mcp_server_cli.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Optional, Sequence

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.cli import tool_handlers
from mcp_server.cli.bootstrap import initialize_stateless_services, timeout, validate_index
from mcp_server.cli.handshake import HandshakeGate
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher
from mcp_server.health.repository_readiness import ReadinessClassifier
from mcp_server.metrics.prometheus_exporter import PrometheusExporter, record_tool_call
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.watcher import FileWatcher
from mcp_server.watcher.ref_poller import RefPoller
from mcp_server.watcher_multi_repo import MultiRepositoryWatcher

logger = logging.getLogger(__name__)

# Server-level constants
_SERVER_NAME = "code-index-mcp-fast-search"
_SERVER_INSTRUCTIONS = (
    "This server provides a pre-built code index (BM25 + semantic vector search). "
    "Indexed search is authoritative when repository readiness is ready. "
    "Use get_status to inspect readiness, or honor an index_unavailable response from "
    "search_code or symbol_lookup. index_unavailable includes safe_fallback=native_search "
    "and remediation; use native search while following remediation such as reindex. "
    "Ready indexes with no matches return ordinary empty results or not_found."
)

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        _SERVER_VERSION = _pkg_version("index-it-mcp")
    except PackageNotFoundError:
        _SERVER_VERSION = "unknown"
except Exception:
    _SERVER_VERSION = "unknown"

USE_SIMPLE_DISPATCHER = os.getenv("MCP_USE_SIMPLE_DISPATCHER", "false").lower() == "true"
PLUGIN_LOAD_TIMEOUT = int(os.getenv("MCP_PLUGIN_TIMEOUT", "5"))

# ---------------------------------------------------------------------------
# Module-level mutable state (7 globals + 2 aux)
# ---------------------------------------------------------------------------

dispatcher: EnhancedDispatcher | SimpleDispatcher | None = None
plugin_manager: PluginManager | None = None
sqlite_store: SQLiteStore | None = None
initialization_error: str | None = None
_file_watcher: FileWatcher | None = None
_indexing_thread: threading.Thread | None = None
_fts_rebuild_thread: threading.Thread | None = None
_indexing_total_files: int = 0
_indexing_started_at: Optional[float] = None
_repo_resolver: Any = None
_store_registry: Any = None
_local_ctx: Any = None  # RepoContext for the local repo, built by initialize_services()


class _LocalRepoResolver:
    """Minimal resolver that returns _local_ctx for any path, used when no registry is available."""

    def classify(self, path: Any) -> Any:
        if _local_ctx is None:
            return None
        return ReadinessClassifier.classify_registered(
            _local_ctx.registry_entry,
            requested_path=Path(path),
        )

    def resolve(self, path: Any) -> Any:
        return _local_ctx


def _build_tool_list() -> list[types.Tool]:
    return [
        types.Tool(
            name="symbol_lookup",
            description="Look up a class, function, method, or variable definition from the index when repository readiness is ready. If the tool returns index_unavailable with safe_fallback=native_search, use native search and follow the readiness remediation, such as reindex. Ready misses return not_found with readiness metadata. Accepts optional repository param (registered repo name or filesystem path); filesystem paths must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The symbol name to look up"},
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository.",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="search_code",
            description="Search indexed code by pattern, keyword, or natural language (semantic=true) when repository readiness is ready. If the tool returns index_unavailable with safe_fallback=native_search, use native search and follow the readiness remediation, such as reindex. Ready misses return results=[] with readiness metadata. Accepts optional repository param (registered repo name or filesystem path); filesystem paths must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository.",
                    },
                    "semantic": {
                        "type": "boolean",
                        "description": "Whether to use semantic search",
                        "default": False,
                    },
                    "fuzzy": {
                        "type": "boolean",
                        "description": "Trigram-based fuzzy match for misspelled queries",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_status",
            description="Get the status of the code index server. Shows index health, supported languages, and performance statistics.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_plugins",
            description="List all loaded plugins and plugin availability states, including enabled, unsupported, disabled, missing-extra, and load-error capabilities.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="reindex",
            description="Reindex files in the codebase. Updates the index for changed files or specific paths. The path must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path to reindex. If not provided, reindexes all files.",
                    },
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository.",
                    },
                },
            },
        ),
        types.Tool(
            name="write_summaries",
            description=(
                "Run the full LLM summarization pass over all un-summarized chunks in the index. "
                "Persists results. Use summarize_sample first to validate quality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of chunks to summarize in this call.",
                        "default": 500,
                    },
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository.",
                    },
                },
            },
        ),
        types.Tool(
            name="summarize_sample",
            description=(
                "Summarize a sample of indexed files using the LLM and return results "
                "for quality evaluation. Does not persist results by default. "
                "Each entry in paths is checked against the sandbox; mismatches return path_outside_allowed_roots."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific file paths to summarize (optional).",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of random files to sample when paths not given.",
                        "default": 3,
                    },
                    "persist": {
                        "type": "boolean",
                        "description": "Save summaries to index (default false for evaluation).",
                        "default": False,
                    },
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository.",
                    },
                },
            },
        ),
        types.Tool(
            name="handshake",
            description="Authenticate with the server using the configured secret. Required before other tools when MCP_CLIENT_SECRET is set.",
            inputSchema={
                "type": "object",
                "properties": {"secret": {"type": "string"}},
                "required": ["secret"],
            },
        ),
    ]


_shutdown_called = False


async def _graceful_shutdown(
    multi_watcher: Any,
    ref_poller: Any,
    store_registry: Any,
    exporter: Any,
    timeout: float = 5.0,
) -> None:
    """Stop watcher -> poller -> store -> exporter in order, each bounded by timeout."""
    global _shutdown_called
    if _shutdown_called:
        logger.debug("_graceful_shutdown: already called, skipping")
        return
    _shutdown_called = True

    if multi_watcher is not None:
        try:
            logger.info("Stopping MultiRepositoryWatcher...")
            await asyncio.wait_for(asyncio.to_thread(multi_watcher.stop), timeout=timeout)
            logger.info("MultiRepositoryWatcher stopped")
        except asyncio.TimeoutError:
            logger.warning("MultiRepositoryWatcher.stop timed out after %.1fs", timeout)
        except Exception as exc:
            logger.warning("MultiRepositoryWatcher.stop error: %s", exc)

    if ref_poller is not None:
        try:
            logger.info("Stopping RefPoller...")
            await asyncio.wait_for(asyncio.to_thread(ref_poller.stop), timeout=timeout)
            logger.info("RefPoller stopped")
        except asyncio.TimeoutError:
            logger.warning("RefPoller.stop timed out after %.1fs", timeout)
        except Exception as exc:
            logger.warning("RefPoller.stop error: %s", exc)

    if store_registry is not None:
        try:
            logger.info("Shutting down StoreRegistry...")
            await asyncio.wait_for(asyncio.to_thread(store_registry.shutdown), timeout=timeout)
            logger.info("StoreRegistry shut down")
        except asyncio.TimeoutError:
            logger.warning("StoreRegistry.shutdown timed out after %.1fs", timeout)
        except Exception as exc:
            logger.warning("StoreRegistry.shutdown error: %s", exc)

    if exporter is not None:
        try:
            logger.info("Stopping PrometheusExporter...")
            exporter.stop()
            logger.info("PrometheusExporter stopped")
        except Exception as exc:
            logger.warning("PrometheusExporter.stop error: %s", exc)


# ---------------------------------------------------------------------------
# Module-level initialize_services() — hoisted from _serve()'s lazy_initialize()
# ---------------------------------------------------------------------------


async def initialize_services() -> None:
    """Initialize all services needed for the MCP server."""
    global dispatcher, plugin_manager, sqlite_store, initialization_error
    global _file_watcher, _indexing_thread, _fts_rebuild_thread
    global _indexing_total_files, _indexing_started_at, _local_ctx
    _auto_index = False

    try:
        from mcp_server.core.ignore_patterns import build_walker_filter

        current_dir = Path.cwd()
        enable_multi_path = os.getenv("MCP_ENABLE_MULTI_PATH", "true").lower() == "true"

        logger.info("Searching for index using multi-path discovery...")
        discovery = IndexDiscovery(current_dir, enable_multi_path=enable_multi_path)
        index_info = discovery.get_index_info()

        if not index_info["enabled"]:
            if os.getenv("MCP_INDEX_ENABLED", "").lower() == "false":
                raise RuntimeError("MCP indexing disabled via MCP_INDEX_ENABLED=false")
            explicit_config = discovery.get_index_config()
            if explicit_config is not None and explicit_config.get("enabled") is False:
                raise RuntimeError("MCP indexing disabled in .mcp-index.json")
            logger.info("No MCP index config found — will auto-initialize index on first use")

        index_path = discovery.get_local_index_path()

        if index_path:
            logger.info(f"Found index at: {index_path}")
            sqlite_store = SQLiteStore(str(index_path))

            validation_result = validate_index(sqlite_store, current_dir)
            if not validation_result["valid"]:
                for issue in validation_result["issues"]:
                    logger.warning(f"  - {issue}")

            _vstats = validation_result.get("stats", {})
            if _vstats.get("bm25_documents", 1) == 0 and _vstats.get("total_files", 0) > 0:
                _heal_store = sqlite_store

                def _rebuild_fts():
                    try:
                        rows = _heal_store.rebuild_fts_code()
                        logger.info(f"BM25 FTS rebuild complete: {rows} documents")
                    except Exception as _fts_err:
                        logger.warning(f"BM25 FTS rebuild failed (non-fatal): {_fts_err}")

                _fts_rebuild_thread = threading.Thread(
                    target=_rebuild_fts, daemon=True, name="mcp-fts-rebuild"
                )
                _fts_rebuild_thread.start()
        else:
            index_dir = current_dir / ".mcp-index"
            index_dir.mkdir(exist_ok=True)
            index_path = index_dir / "code_index.db"
            logger.info(f"No index found — creating new index at {index_path}")
            sqlite_store = SQLiteStore(str(index_path))
            _auto_index = True

            gitignore_path = current_dir / ".gitignore"
            gitignore_entries = [
                ".mcp-index/code_index.db",
                ".mcp-index/code_index.db-shm",
                ".mcp-index/code_index.db-wal",
                ".mcp-index/.index_metadata.json",
            ]
            try:
                existing = (
                    gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
                )
                missing = [e for e in gitignore_entries if e not in existing]
                if missing:
                    with gitignore_path.open("a", encoding="utf-8") as _gf:
                        _gf.write("\n# MCP Index files\n")
                        _gf.write("\n".join(missing) + "\n")
            except Exception as _gi_err:
                logger.debug(f"Could not update .gitignore: {_gi_err}")

        # Initialize dispatcher (simple or enhanced with plugins)
        if USE_SIMPLE_DISPATCHER:
            logger.info("Using SimpleDispatcher (BM25-only mode)")
            dispatcher = SimpleDispatcher()
        else:
            logger.info("Initializing plugin system...")
            config_path = Path("plugins.yaml")
            plugin_manager = PluginManager(sqlite_store=sqlite_store)

            logger.info(f"Loading plugins (timeout: {PLUGIN_LOAD_TIMEOUT}s)...")
            try:
                with timeout(PLUGIN_LOAD_TIMEOUT):
                    load_result = plugin_manager.load_plugins_safe(
                        config_path if config_path.exists() else None
                    )
                    if not load_result.success:
                        logger.error(f"Plugin loading failed: {load_result.error.message}")
                    else:
                        logger.info(f"Plugin loading completed: {load_result.metadata}")
            except TimeoutError:
                logger.warning(f"Plugin loading timed out after {PLUGIN_LOAD_TIMEOUT} seconds")

            active_plugins = plugin_manager.get_active_plugins() if plugin_manager else {}
            plugin_instances = list(active_plugins.values())
            logger.info(f"Loaded {len(plugin_instances)} active plugins from plugin manager")

            logger.info("Creating enhanced dispatcher with timeout protection...")
            _explicit = os.getenv("RERANKER_TYPE", "").strip().lower()
            reranker_type = _explicit if _explicit else "none"
            dispatcher = EnhancedDispatcher(
                plugins=plugin_instances,
                enable_advanced_features=True,
                use_plugin_factory=True,
                lazy_load=True,
                semantic_search_enabled=True,
                memory_aware=True,
                multi_repo_enabled=None,
                reranker_type=reranker_type,
            )

        _supported = dispatcher.supported_languages
        supported_languages = _supported() if callable(_supported) else _supported
        logger.info(f"Enhanced dispatcher created - supports {len(supported_languages)} languages")

        # Build a minimal RepoContext for local single-repo use when no registry is available
        if sqlite_store is not None and _local_ctx is None:
            try:
                from datetime import datetime as _dt

                from mcp_server.core.repo_context import RepoContext
                from mcp_server.storage.multi_repo_manager import RepositoryInfo
                from mcp_server.storage.repo_identity import compute_repo_id

                _repo_id_result = compute_repo_id(current_dir)
                _repo_id = (
                    _repo_id_result.repo_id
                    if hasattr(_repo_id_result, "repo_id")
                    else str(_repo_id_result)
                )
                _reg_entry = RepositoryInfo(
                    repository_id=_repo_id,
                    name=current_dir.name,
                    path=current_dir,
                    index_path=Path(sqlite_store.db_path),
                    language_stats={},
                    total_files=0,
                    total_symbols=0,
                    indexed_at=_dt.now(),
                    tracked_branch="",
                )
                _local_ctx = RepoContext(
                    repo_id=_repo_id,
                    sqlite_store=sqlite_store,
                    workspace_root=current_dir,
                    tracked_branch="",
                    registry_entry=_reg_entry,
                )
            except Exception as _ctx_err:
                logger.debug(f"Could not build local RepoContext (non-fatal): {_ctx_err}")

        # Pre-create plugins with sqlite_store so BM25 indexing persists via ctx.repo_id lookup
        # This ensures _match_plugin finds a store-aware plugin before lazy-loading a bare one.
        if (
            _local_ctx is not None
            and isinstance(dispatcher, EnhancedDispatcher)
            and sqlite_store is not None
        ):
            try:
                from mcp_server.plugins.plugin_factory import PluginFactory as _PF

                _languages_to_preload = ["python", "javascript", "typescript", "go", "rust", "java"]
                for _lang in _languages_to_preload:
                    try:
                        # Only pre-load if not already in _legacy_plugins
                        _already = any(
                            getattr(_p, "lang", None) == _lang
                            or getattr(_p, "lang_id", None) == _lang
                            for _p in getattr(dispatcher, "_legacy_plugins", [])
                        )
                        if not _already:
                            _store_plugin = _PF.create_plugin(_lang, sqlite_store=sqlite_store)
                            if _store_plugin is not None:
                                dispatcher._legacy_plugins.insert(0, _store_plugin)
                    except Exception:
                        pass
            except Exception as _inj_err:
                logger.debug(f"Plugin preload with store failed (non-fatal): {_inj_err}")

        if (
            isinstance(dispatcher, EnhancedDispatcher)
            and getattr(dispatcher, "_semantic_indexer", None) is None
        ):
            logger.warning(
                "Semantic search not available — running in BM25-only mode. "
                "Set VOYAGE_API_KEY (Voyage AI) or configure a vLLM endpoint in "
                "code-index-mcp.profiles.yaml to enable semantic (vector) search."
            )

        # Start FileWatcher — deferred until after auto-index when _auto_index is True
        if _file_watcher is None and isinstance(dispatcher, EnhancedDispatcher):
            try:
                _file_watcher = FileWatcher(root=current_dir, dispatcher=dispatcher)
                if not _auto_index:
                    _file_watcher.start()
                    logger.info(f"FileWatcher started, watching {current_dir}")
                # else: started inside _run_initial_index() after indexing completes
            except Exception as _fw_err:
                logger.warning(f"FileWatcher failed to start (non-fatal): {_fw_err}")

        # Guard: skip auto-index for very large repos
        if _auto_index:
            _max_files = int(os.getenv("MCP_AUTO_INDEX_MAX_FILES", "100000"))
            _file_count = 0
            _is_excluded = build_walker_filter(current_dir)
            for _root, _dirs, _files in os.walk(current_dir, followlinks=False):
                _dirs[:] = [d for d in _dirs if not _is_excluded(Path(_root) / d)]
                _file_count += len(_files)
                if _file_count > _max_files:
                    break
            if _file_count > _max_files:
                logger.warning(f"Repository has >{_max_files} files — skipping auto-index")
                _auto_index = False

        if (
            _auto_index
            and _indexing_thread is None
            and isinstance(dispatcher, EnhancedDispatcher)
            and os.getenv("MCP_AUTO_INDEX", "true").lower() != "false"
        ):
            _captured_dir = current_dir
            _captured_store = sqlite_store

            _captured_ctx = _local_ctx

            def _run_initial_index():
                logger.info("Background initial index started...")
                try:
                    if _captured_ctx is not None:
                        stats = dispatcher.index_directory(
                            _captured_ctx, _captured_dir, recursive=True
                        )
                    else:
                        # Fallback: walk files and index without ctx (BM25 only via sqlite_store)
                        stats = {"indexed_files": 0}
                        if _captured_store is not None:
                            for _f in _captured_dir.rglob("*.py"):
                                try:
                                    _content = _f.read_text(encoding="utf-8")
                                    _hash = (
                                        __import__("hashlib").sha256(_content.encode()).hexdigest()
                                    )
                                    _fid = _captured_store.store_file(
                                        "local",
                                        str(_f),
                                        str(_f.relative_to(_captured_dir)),
                                        language="python",
                                        size=len(_content),
                                        hash=_hash,
                                    )
                                    if _fid:
                                        _captured_store.store_code_chunk(
                                            _fid, _content, 1, _content.count("\n") + 1
                                        )
                                        stats["indexed_files"] += 1
                                except Exception:
                                    pass
                    if _captured_store:
                        _captured_store.rebuild_fts_code()
                    logger.info(f"Background initial index complete: {stats}")
                except Exception as _idx_err:
                    logger.error(f"Background initial index failed: {_idx_err}")
                finally:
                    if _file_watcher is not None:
                        try:
                            _file_watcher.start()
                            logger.info(
                                f"FileWatcher started after initial index, watching {_captured_dir}"
                            )
                        except Exception as _fw_err:
                            logger.warning(f"FileWatcher failed to start (non-fatal): {_fw_err}")

            _indexing_total_files = _file_count
            _indexing_started_at = time.time()
            _indexing_thread = threading.Thread(
                target=_run_initial_index, daemon=True, name="mcp-initial-index"
            )
            _indexing_thread.start()
            logger.info(f"Indexing {_captured_dir} in background")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        initialization_error = str(e)


# ---------------------------------------------------------------------------
# Module-level call_tool() — hoisted from _serve()'s closure
# ---------------------------------------------------------------------------

# Per-process singleton gate and lazy summarizer (scoped to process lifetime)
_gate: Optional[HandshakeGate] = None
_lazy_summarizer: Optional[Any] = None
_init_lock: Optional[asyncio.Lock] = None


async def call_tool(
    name: str, arguments: dict | None
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    global _lazy_summarizer, _init_lock, _gate

    _current_session = None
    _client_name = None
    try:
        from mcp.server.lowlevel.server import request_ctx

        _ctx = request_ctx.get()
        _current_session = _ctx.session
        _params = getattr(_current_session, "client_params", None)
        _client_name = getattr(getattr(_params, "clientInfo", None), "name", None)
    except Exception as _e:
        logger.debug("request_ctx not available: %s", _e)

    # Lazy initialize on first call
    if sqlite_store is None and initialization_error is None:
        if _init_lock is None:
            _init_lock = asyncio.Lock()
        async with _init_lock:
            if sqlite_store is None and initialization_error is None:
                await initialize_services()

    if initialization_error:
        return [
            types.TextContent(
                type="text",
                text=tool_handlers._ensure_response(
                    {
                        "error": "MCP server initialization failed",
                        "details": initialization_error,
                        "suggestion": (
                            "No index found. Run 'mcp-index index' or "
                            "'python scripts/reindex_current_repo.py' in your repository root."
                        ),
                    }
                ),
            )
        ]

    if _lazy_summarizer is None and sqlite_store is not None:
        from mcp_server.config.settings import Settings
        from mcp_server.indexing.summarization import LazyChunkWriter

        _settings = Settings.from_environment()
        _lazy_summarizer = LazyChunkWriter(
            db_path=sqlite_store.db_path,
            qdrant_client=None,
            session=_current_session,
            client_name=_client_name,
            summarization_config=_settings.get_profile_summarization_config(
                _settings.semantic_default_profile
            ),
        )
        _lazy_summarizer.start()
    elif _lazy_summarizer is not None and _current_session is not None:
        _lazy_summarizer.update_session(_current_session)

    # Gate check before logging to avoid leaking the handshake secret.
    if _gate is None:
        _gate = HandshakeGate()
        if not _gate.enabled:
            logger.warning("running unauthenticated \u2014 MCP_CLIENT_SECRET not set")
    _gate_err = _gate.check(name, arguments or {})
    if _gate_err is not None:
        return [types.TextContent(type="text", text=tool_handlers._ensure_response(_gate_err))]

    logger.info(f"=== MCP Tool Call: {name} args={arguments} ===")
    start_time = time.time()

    _effective_resolver = (
        _repo_resolver
        if _repo_resolver is not None
        else (_LocalRepoResolver() if _local_ctx is not None else None)
    )
    common_kwargs = dict(
        arguments=arguments or {},
        dispatcher=dispatcher,
        repo_resolver=_effective_resolver,
    )

    _tool_status = "success"
    try:
        if name == "handshake":
            _secret = (arguments or {}).get("secret", "")
            if _gate.verify(_secret):
                response = [
                    types.TextContent(
                        type="text", text=tool_handlers._ensure_response({"authenticated": True})
                    )
                ]
            else:
                response = [
                    types.TextContent(
                        type="text",
                        text=tool_handlers._ensure_response(
                            {
                                "error": "Invalid secret.",
                                "code": "handshake_required",
                            }
                        ),
                    )
                ]
        elif name == "symbol_lookup":
            response = await tool_handlers.handle_symbol_lookup(
                **common_kwargs,
                sqlite_store=sqlite_store,
            )
        elif name == "search_code":
            response = await tool_handlers.handle_search_code(
                **common_kwargs,
                sqlite_store=sqlite_store,
                indexing_thread=_indexing_thread,
                lazy_summarizer=_lazy_summarizer,
            )
        elif name == "get_status":
            response = await tool_handlers.handle_get_status(
                **common_kwargs,
                sqlite_store=sqlite_store,
                file_watcher=_file_watcher,
                indexing_thread=_indexing_thread,
                indexing_started_at=_indexing_started_at,
                indexing_total_files=_indexing_total_files,
                lazy_summarizer=_lazy_summarizer,
                server_version=_SERVER_VERSION,
                use_simple_dispatcher=USE_SIMPLE_DISPATCHER,
                current_session=_current_session,
                client_name=_client_name,
            )
        elif name == "list_plugins":
            response = await tool_handlers.handle_list_plugins(
                **common_kwargs,
                plugin_manager=plugin_manager,
            )
        elif name == "reindex":
            response = await tool_handlers.handle_reindex(
                **common_kwargs,
                sqlite_store=sqlite_store,
            )
        elif name == "write_summaries":
            response = await tool_handlers.handle_write_summaries(
                **common_kwargs,
                sqlite_store=sqlite_store,
                lazy_summarizer=_lazy_summarizer,
                current_session=_current_session,
                client_name=_client_name,
            )
        elif name == "summarize_sample":
            response = await tool_handlers.handle_summarize_sample(
                **common_kwargs,
                sqlite_store=sqlite_store,
                lazy_summarizer=_lazy_summarizer,
                current_session=_current_session,
                client_name=_client_name,
            )
        else:
            response = [
                types.TextContent(
                    type="text",
                    text=tool_handlers._ensure_response(
                        {
                            "error": "Unknown tool",
                            "tool": name,
                            "available_tools": [
                                "symbol_lookup",
                                "search_code",
                                "get_status",
                                "list_plugins",
                                "reindex",
                                "write_summaries",
                                "summarize_sample",
                                "handshake",
                            ],
                        }
                    ),
                )
            ]
    except Exception as e:
        _tool_status = "error"
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        response = [
            types.TextContent(
                type="text",
                text=tool_handlers._ensure_response(
                    {
                        "error": f"Tool execution failed: {name}",
                        "details": str(e),
                        "tool": name,
                    }
                ),
            )
        ]

    record_tool_call(name, _tool_status)

    elapsed = time.time() - start_time
    logger.info(f"=== MCP Tool Response: {name} ({elapsed:.2f}s) ===")

    if not response:
        response = [
            types.TextContent(
                type="text",
                text=tool_handlers._ensure_response(
                    {
                        "error": "No response generated",
                        "tool": name,
                        "elapsed": elapsed,
                    }
                ),
            )
        ]

    return response


# ---------------------------------------------------------------------------
# _serve() — thin orchestrator
# ---------------------------------------------------------------------------


async def _serve(registry_path=None) -> None:
    """Set up and run the MCP stdio server."""
    global _shutdown_called, _gate, _repo_resolver, _store_registry

    _shutdown_called = False

    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(__import__("sys").stderr)],
    )

    logger.info("=" * 60)
    logger.info("Code Index MCP Server Starting")
    logger.info(
        f"Dispatcher Mode: {'Simple (BM25-only)' if USE_SIMPLE_DISPATCHER else 'Enhanced (with plugins)'}"
    )
    logger.info(f"Plugin Timeout: {PLUGIN_LOAD_TIMEOUT} seconds")
    logger.info("=" * 60)
    from mcp_server.artifacts.attestation import warn_if_gh_attestation_missing

    warn_if_gh_attestation_missing()

    # Process-wide service pool — stateless, no cwd capture
    store_registry, repo_resolver, _disp, repo_registry, git_index_manager = (
        initialize_stateless_services(registry_path=registry_path)
    )
    _repo_resolver = repo_resolver
    _store_registry = store_registry

    # Start Prometheus metrics exporter
    exporter = PrometheusExporter()
    exporter.start(int(os.getenv("MCP_METRICS_PORT", "9090")))

    # Start multi-repo watcher + ref poller eagerly, after registries are ready
    multi_watcher: Optional[MultiRepositoryWatcher] = None
    ref_poller: Optional[RefPoller] = None
    try:
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher as _ED

        if isinstance(_disp, _ED):
            multi_watcher = MultiRepositoryWatcher(
                registry=repo_registry,
                dispatcher=_disp,
                index_manager=git_index_manager,
                repo_resolver=repo_resolver,
            )
            ref_poller = RefPoller(
                registry=repo_registry,
                git_index_manager=git_index_manager,
                dispatcher=_disp,
                repo_resolver=repo_resolver,
            )
            multi_watcher.start_watching_all()
            ref_poller.start()
            logger.info("MultiRepositoryWatcher and RefPoller started")
    except Exception as _watcher_err:
        logger.warning(f"MultiRepositoryWatcher failed to start: {_watcher_err}")
        multi_watcher = None
        ref_poller = None

    # Install SIGTERM/SIGINT handlers for graceful shutdown
    _loop = asyncio.get_running_loop()
    _shutdown_tasks: list[asyncio.Task] = []

    def _handle_signal() -> None:
        logger.info("Signal received — initiating graceful shutdown")
        task = asyncio.create_task(
            _graceful_shutdown(multi_watcher, ref_poller, store_registry, exporter, timeout=5.0)
        )
        _shutdown_tasks.append(task)

    try:
        _loop.add_signal_handler(signal.SIGTERM, _handle_signal)
        _loop.add_signal_handler(signal.SIGINT, _handle_signal)
    except NotImplementedError:
        pass

    # Fresh gate for this server invocation
    _gate = HandshakeGate()
    if not _gate.enabled:
        logger.warning("running unauthenticated \u2014 MCP_CLIENT_SECRET not set")

    server = Server(_SERVER_NAME)
    server.instructions = _SERVER_INSTRUCTIONS

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _build_tool_list()

    # Register module-level call_tool via imperative decorator application
    server.call_tool()(call_tool)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await _graceful_shutdown(multi_watcher, ref_poller, store_registry, exporter, timeout=5.0)


def run() -> None:
    """Boot the MCP stdio server."""
    asyncio.run(_serve())


async def main() -> None:
    """Async entry point — used by the shim for asyncio.run(main())."""
    await _serve()
