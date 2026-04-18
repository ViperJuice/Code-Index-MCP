"""MCP stdio server runner — IF-0-P2B-3 implementation.

Wires the MCP Server, list_tools(), and call_tool() dispatcher using
tool_handlers. Invoked by server_commands:stdio() and the shim at
scripts/cli/mcp_server_cli.py.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional, Sequence

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.cli.bootstrap import initialize_stateless_services, timeout
from mcp_server.cli import tool_handlers
from mcp_server.cli.handshake import HandshakeGate
from mcp_server.watcher_multi_repo import MultiRepositoryWatcher
from mcp_server.watcher.ref_poller import RefPoller

logger = logging.getLogger(__name__)

# Server-level constants
_SERVER_NAME = "code-index-mcp-fast-search"
_SERVER_INSTRUCTIONS = (
    "This server provides a pre-built code index (BM25 + semantic vector search). "
    "ALWAYS use search_code and symbol_lookup BEFORE grep, glob, or find. "
    "search_code: pattern/keyword/natural-language search, <500ms, ranked results with line numbers. "
    "symbol_lookup: exact class/function/method lookup by name, <100ms. "
    "Fall back to native tools ONLY if a search returns 0 results."
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


def _build_tool_list() -> list[types.Tool]:
    return [
        types.Tool(
            name="symbol_lookup",
            description="[USE BEFORE GREP] Look up any class, function, or method definition. 100x faster than grep. Returns file + line number. Fall back to Grep ONLY if this returns not_found. Accepts optional repository param (registered repo name or filesystem path); filesystem paths must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "The symbol name to look up"},
                    "repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."},
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="search_code",
            description="[USE BEFORE GREP] Search code by pattern, keyword, or natural language (semantic=true). Indexed, <500ms, returns ranked results with line numbers and last_indexed timestamp. Fall back to Grep ONLY if this returns 0 results. Accepts optional repository param (registered repo name or filesystem path); filesystem paths must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."},
                    "semantic": {"type": "boolean", "description": "Whether to use semantic search", "default": False},
                    "fuzzy": {"type": "boolean", "description": "Trigram-based fuzzy match for misspelled queries", "default": False},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 20},
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
            description="List all loaded plugins. Shows 48 supported languages with specialized and generic plugin information.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="reindex",
            description="Reindex files in the codebase. Updates the index for changed files or specific paths. The path must be inside MCP_ALLOWED_ROOTS or the tool returns path_outside_allowed_roots.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional path to reindex. If not provided, reindexes all files."},
                    "repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."},
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
                    "limit": {"type": "integer", "description": "Maximum number of chunks to summarize in this call.", "default": 500},
                    "repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."},
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
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "Specific file paths to summarize (optional)."},
                    "n": {"type": "integer", "description": "Number of random files to sample when paths not given.", "default": 3},
                    "persist": {"type": "boolean", "description": "Save summaries to index (default false for evaluation).", "default": False},
                    "repository": {"type": "string", "description": "Repository ID, path, or git URL. Defaults to current repository."},
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


async def _serve(registry_path=None) -> None:
    """Set up and run the MCP stdio server."""
    from dotenv import load_dotenv

    from mcp_server.config.settings import Settings
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from mcp_server.indexing.summarization import LazyChunkWriter
    from mcp_server.plugin_system import PluginManager
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.utils.index_discovery import IndexDiscovery

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(__import__("sys").stderr)],
    )

    logger.info("=" * 60)
    logger.info("Code Index MCP Server Starting")
    logger.info(f"Dispatcher Mode: {'Simple (BM25-only)' if USE_SIMPLE_DISPATCHER else 'Enhanced (with plugins)'}")
    logger.info(f"Plugin Timeout: {PLUGIN_LOAD_TIMEOUT} seconds")
    logger.info("=" * 60)

    # Process-wide service pool — stateless, no cwd capture
    store_registry, repo_resolver, dispatcher, repo_registry, git_index_manager = initialize_stateless_services(
        registry_path=registry_path
    )

    # Start multi-repo watcher + ref poller eagerly, after registries are ready
    multi_watcher: Optional[MultiRepositoryWatcher] = None
    ref_poller: Optional[RefPoller] = None
    try:
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher as _ED
        if isinstance(dispatcher, _ED):
            multi_watcher = MultiRepositoryWatcher(
                registry=repo_registry,
                dispatcher=dispatcher,
                index_manager=git_index_manager,
                repo_resolver=repo_resolver,
            )
            ref_poller = RefPoller(
                registry=repo_registry,
                git_index_manager=git_index_manager,
                dispatcher=dispatcher,
                repo_resolver=repo_resolver,
            )
            multi_watcher.start_watching_all()
            ref_poller.start()
            logger.info("MultiRepositoryWatcher and RefPoller started")
    except Exception as _watcher_err:
        logger.warning(f"MultiRepositoryWatcher failed to start: {_watcher_err}")
        multi_watcher = None
        ref_poller = None

    # Optional client handshake gate — closure-scoped so each _serve() invocation
    # gets a fresh instance (required for test isolation).
    gate = HandshakeGate()
    if not gate.enabled:
        logger.warning("running unauthenticated \u2014 MCP_CLIENT_SECRET not set")

    # Per-process mutable state for lazy indexing
    plugin_manager: Optional[PluginManager] = None
    sqlite_store: Optional[SQLiteStore] = None
    initialization_error: Optional[str] = None
    indexing_thread: Optional[threading.Thread] = None
    fts_rebuild_thread: Optional[threading.Thread] = None
    indexing_total_files: int = 0
    indexing_started_at: Optional[float] = None
    init_lock: Optional[asyncio.Lock] = None
    lazy_summarizer: Optional[Any] = None

    async def lazy_initialize():
        nonlocal dispatcher, plugin_manager, sqlite_store, initialization_error
        nonlocal indexing_thread, fts_rebuild_thread
        nonlocal indexing_total_files, indexing_started_at
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

                from mcp_server.cli.bootstrap import validate_index as _validate_index
                validation_result = _validate_index(sqlite_store, current_dir)
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

                    nonlocal fts_rebuild_thread
                    fts_rebuild_thread = threading.Thread(target=_rebuild_fts, daemon=True, name="mcp-fts-rebuild")
                    fts_rebuild_thread.start()
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
                    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
                    missing = [e for e in gitignore_entries if e not in existing]
                    if missing:
                        with gitignore_path.open("a", encoding="utf-8") as _gf:
                            _gf.write("\n# MCP Index files\n")
                            _gf.write("\n".join(missing) + "\n")
                except Exception as _gi_err:
                    logger.debug(f"Could not update .gitignore: {_gi_err}")

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
                and indexing_thread is None
                and isinstance(dispatcher, EnhancedDispatcher)
                and os.getenv("MCP_AUTO_INDEX", "true").lower() != "false"
            ):
                _captured_dir = current_dir
                _captured_store = sqlite_store

                def _run_initial_index():
                    logger.info("Background initial index started...")
                    try:
                        stats = dispatcher.index_directory(_captured_dir, recursive=True)
                        if _captured_store:
                            _captured_store.rebuild_fts_code()
                        logger.info(f"Background initial index complete: {stats}")
                    except Exception as _idx_err:
                        logger.error(f"Background initial index failed: {_idx_err}")

                indexing_total_files = _file_count
                indexing_started_at = time.time()
                indexing_thread = threading.Thread(
                    target=_run_initial_index, daemon=True, name="mcp-initial-index"
                )
                indexing_thread.start()
                logger.info(f"Indexing {_captured_dir} in background")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            initialization_error = str(e)

    server = Server(_SERVER_NAME)
    server.instructions = _SERVER_INSTRUCTIONS

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _build_tool_list()

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict | None
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        nonlocal lazy_summarizer, initialization_error, init_lock, sqlite_store

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
            if init_lock is None:
                init_lock = asyncio.Lock()
            async with init_lock:
                if sqlite_store is None and initialization_error is None:
                    await lazy_initialize()

        if initialization_error:
            return [types.TextContent(type="text", text=tool_handlers._ensure_response({
                "error": "MCP server initialization failed",
                "details": initialization_error,
                "suggestion": (
                    "No index found. Run 'mcp-index index' or "
                    "'python scripts/reindex_current_repo.py' in your repository root."
                ),
            }))]

        if lazy_summarizer is None and sqlite_store is not None:
            _settings = Settings.from_environment()
            lazy_summarizer = LazyChunkWriter(
                db_path=sqlite_store.db_path,
                qdrant_client=None,
                session=_current_session,
                client_name=_client_name,
                summarization_config=_settings.get_profile_summarization_config(
                    _settings.semantic_default_profile
                ),
            )
            lazy_summarizer.start()
        elif lazy_summarizer is not None and _current_session is not None:
            lazy_summarizer.update_session(_current_session)

        # Gate check before logging to avoid leaking the handshake secret.
        _gate_err = gate.check(name, arguments or {})
        if _gate_err is not None:
            return [types.TextContent(type="text", text=tool_handlers._ensure_response(_gate_err))]

        logger.info(f"=== MCP Tool Call: {name} args={arguments} ===")
        start_time = time.time()

        common_kwargs = dict(
            arguments=arguments or {},
            dispatcher=dispatcher,
            repo_resolver=repo_resolver,
        )

        try:
            if name == "handshake":
                _secret = (arguments or {}).get("secret", "")
                if gate.verify(_secret):
                    response = [types.TextContent(type="text", text=tool_handlers._ensure_response({"authenticated": True}))]
                else:
                    response = [types.TextContent(type="text", text=tool_handlers._ensure_response({
                        "error": "Invalid secret.",
                        "code": "handshake_required",
                    }))]
            elif name == "symbol_lookup":
                response = await tool_handlers.handle_symbol_lookup(
                    **common_kwargs,
                    sqlite_store=sqlite_store,
                )
            elif name == "search_code":
                response = await tool_handlers.handle_search_code(
                    **common_kwargs,
                    sqlite_store=sqlite_store,
                    indexing_thread=indexing_thread,
                    lazy_summarizer=lazy_summarizer,
                )
            elif name == "get_status":
                response = await tool_handlers.handle_get_status(
                    **common_kwargs,
                    sqlite_store=sqlite_store,
                    file_watcher=multi_watcher,
                    indexing_thread=indexing_thread,
                    indexing_started_at=indexing_started_at,
                    indexing_total_files=indexing_total_files,
                    lazy_summarizer=lazy_summarizer,
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
                    lazy_summarizer=lazy_summarizer,
                    current_session=_current_session,
                    client_name=_client_name,
                )
            elif name == "summarize_sample":
                response = await tool_handlers.handle_summarize_sample(
                    **common_kwargs,
                    sqlite_store=sqlite_store,
                    lazy_summarizer=lazy_summarizer,
                    current_session=_current_session,
                    client_name=_client_name,
                )
            else:
                response = [types.TextContent(type="text", text=tool_handlers._ensure_response({
                    "error": "Unknown tool",
                    "tool": name,
                    "available_tools": [
                        "symbol_lookup", "search_code", "get_status",
                        "list_plugins", "reindex", "write_summaries", "summarize_sample",
                        "handshake",
                    ],
                }))]
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}", exc_info=True)
            response = [types.TextContent(type="text", text=tool_handlers._ensure_response({
                "error": f"Tool execution failed: {name}",
                "details": str(e),
                "tool": name,
            }))]

        elapsed = time.time() - start_time
        logger.info(f"=== MCP Tool Response: {name} ({elapsed:.2f}s) ===")

        if not response:
            response = [types.TextContent(type="text", text=tool_handlers._ensure_response({
                "error": "No response generated", "tool": name, "elapsed": elapsed,
            }))]

        return response

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    finally:
        if multi_watcher is not None:
            try:
                multi_watcher.stop_watching_all()
                logger.info("MultiRepositoryWatcher stopped")
            except Exception as _e:
                logger.warning(f"MultiRepositoryWatcher stop error: {_e}")
        if ref_poller is not None:
            try:
                ref_poller.stop()
                logger.info("RefPoller stopped")
            except Exception as _e:
                logger.warning(f"RefPoller stop error: {_e}")


def run() -> None:
    """Boot the MCP stdio server."""
    asyncio.run(_serve())


async def main() -> None:
    """Async entry point — used by the shim for asyncio.run(main())."""
    await _serve()
