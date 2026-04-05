#!/usr/bin/env python3
"""
MCP Server CLI for Code Index MCP - Claude Code compatible version
This server provides tools only (no resources) to ensure compatibility with Claude Code.
"""

import asyncio
import json
import os
import sys
import hashlib
import subprocess
import time
from typing import Any, Sequence
from dotenv import load_dotenv
from mcp_server.core.path_utils import PathUtils

# Load environment variables from .env file
load_dotenv()

# Enable debug mode
DEBUG_MODE = os.getenv("MCP_DEBUG", "0") == "1"

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher
from mcp_server.watcher import FileWatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.config.index_paths import IndexPathConfig
from mcp_server.config.settings import Settings
from pathlib import Path
import logging
import signal
import threading
from contextlib import contextmanager

# Set up logging - send all logs to stderr to avoid interfering with MCP protocol on stdout
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Send all logs to stderr
    ],
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("code-index-mcp-fast-search")
server.instructions = (
    "This server provides a pre-built code index (BM25 + semantic vector search). "
    "ALWAYS use search_code and symbol_lookup BEFORE grep, glob, or find. "
    "search_code: pattern/keyword/natural-language search, <500ms, ranked results with line numbers. "
    "symbol_lookup: exact class/function/method lookup by name, <100ms. "
    "Fall back to native tools ONLY if a search returns 0 results."
)

# Global instances
dispatcher: EnhancedDispatcher | SimpleDispatcher | None = None
plugin_manager: PluginManager | None = None
sqlite_store: SQLiteStore | None = None
initialization_error: str | None = None
_file_watcher: FileWatcher | None = None
_indexing_thread: threading.Thread | None = None
_fts_rebuild_thread: threading.Thread | None = None
_indexing_total_files: int = 0
_indexing_started_at: float | None = None

# Configuration from environment
USE_SIMPLE_DISPATCHER = (
    os.getenv("MCP_USE_SIMPLE_DISPATCHER", "false").lower() == "true"
)
PLUGIN_LOAD_TIMEOUT = int(os.getenv("MCP_PLUGIN_TIMEOUT", "5"))


@contextmanager
def timeout(seconds):
    """Context manager for timeout operations (Unix only; no-op on Windows)."""
    if not hasattr(signal, "SIGALRM"):
        # Windows does not support SIGALRM; run without timeout protection
        yield
        return

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the timeout handler
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Cancel the alarm
        signal.alarm(0)
        # Restore the original handler
        signal.signal(signal.SIGALRM, original_handler)


async def initialize_services():
    """Initialize all services needed for the MCP server."""
    global dispatcher, plugin_manager, sqlite_store, initialization_error
    _auto_index = False

    try:
        # Use multi-path discovery to find index
        current_dir = Path.cwd()
        enable_multi_path = os.getenv("MCP_ENABLE_MULTI_PATH", "true").lower() == "true"

        logger.info("Searching for index using multi-path discovery...")
        discovery = IndexDiscovery(current_dir, enable_multi_path=enable_multi_path)

        # Get information about index discovery
        index_info = discovery.get_index_info()

        if not index_info["enabled"]:
            # Respect explicit opt-outs; allow auto-init for repos with no config yet
            if os.getenv("MCP_INDEX_ENABLED", "").lower() == "false":
                raise RuntimeError("MCP indexing disabled via MCP_INDEX_ENABLED=false")
            explicit_config = discovery.get_index_config()
            if explicit_config is not None and explicit_config.get("enabled") is False:
                raise RuntimeError("MCP indexing disabled in .mcp-index.json")
            logger.info("No MCP index config found — will auto-initialize index on first use")

        # Find the index
        index_path = discovery.get_local_index_path()

        if index_path:
            logger.info(f"Found index at: {index_path}")
            logger.info(
                f"Location type: {discovery._classify_location(index_path.parent)}"
            )
            sqlite_store = SQLiteStore(str(index_path))

            # Validate index
            validation_result = validate_index(sqlite_store, current_dir)
            if not validation_result["valid"]:
                logger.warning(f"Index validation issues found:")
                for issue in validation_result["issues"]:
                    logger.warning(f"  - {issue}")
            else:
                logger.info(f"Index validation passed: {validation_result['stats']}")

            # Auto-heal: if files are tracked but BM25 FTS is empty, rebuild in background
            _vstats = validation_result.get("stats", {})
            if _vstats.get("bm25_documents", 1) == 0 and _vstats.get("total_files", 0) > 0:
                global _fts_rebuild_thread
                _heal_store = sqlite_store

                def _rebuild_fts():
                    logger.info("Rebuilding BM25 FTS content (was empty despite indexed files)...")
                    try:
                        rows = _heal_store.rebuild_fts_code()
                        logger.info(f"BM25 FTS rebuild complete: {rows} documents")
                    except Exception as _fts_err:
                        logger.warning(f"BM25 FTS rebuild failed (non-fatal): {_fts_err}")

                _fts_rebuild_thread = threading.Thread(
                    target=_rebuild_fts, daemon=True, name="mcp-fts-rebuild"
                )
                _fts_rebuild_thread.start()

            # Log search paths that were checked
            if enable_multi_path and index_info.get("search_paths"):
                logger.debug(f"Searched {len(index_info['search_paths'])} paths:")
                for i, path in enumerate(index_info["search_paths"][:5]):
                    logger.debug(f"  {i + 1}. {path}")
                if len(index_info["search_paths"]) > 5:
                    logger.debug(
                        f"  ... and {len(index_info['search_paths']) - 5} more"
                    )
        else:
            # No index found — create one automatically and index in background
            index_dir = current_dir / ".mcp-index"
            index_dir.mkdir(exist_ok=True)
            index_path = index_dir / "code_index.db"
            logger.info(f"No index found — creating new index at {index_path}")
            sqlite_store = SQLiteStore(str(index_path))
            _auto_index = True

            # Ensure SQLite WAL sidecar files and the DB itself are gitignored
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
                    logger.info(f"Added {len(missing)} MCP index entries to .gitignore")
            except Exception as _gi_err:
                logger.debug(f"Could not update .gitignore (non-fatal): {_gi_err}")

        # Check if we should use simple dispatcher
        if USE_SIMPLE_DISPATCHER:
            logger.info("Using SimpleDispatcher (BM25-only mode)")
            dispatcher = SimpleDispatcher(sqlite_store=sqlite_store)
        else:
            # Initialize plugin manager
            logger.info("Initializing plugin system...")
            config_path = Path("plugins.yaml")
            plugin_manager = PluginManager(sqlite_store=sqlite_store)

            # Load plugins with timeout protection
            logger.info(f"Loading plugins (timeout: {PLUGIN_LOAD_TIMEOUT}s)...")
            try:
                with timeout(PLUGIN_LOAD_TIMEOUT):
                    load_result = plugin_manager.load_plugins_safe(
                        config_path if config_path.exists() else None
                    )

                    if not load_result.success:
                        logger.error(
                            f"Plugin loading failed: {load_result.error.message}"
                        )
                    else:
                        logger.info(f"Plugin loading completed: {load_result.metadata}")
            except TimeoutError:
                logger.warning(
                    f"Plugin loading timed out after {PLUGIN_LOAD_TIMEOUT} seconds"
                )
                # Continue with empty plugin list

            # Get active plugin instances from plugin manager (for existing 6 plugins)
            active_plugins = (
                plugin_manager.get_active_plugins() if plugin_manager else {}
            )
            plugin_instances = list(active_plugins.values())

            logger.info(
                f"Loaded {len(plugin_instances)} active plugins from plugin manager"
            )

            # Create enhanced dispatcher with dynamic plugin loading
            logger.info("Creating enhanced dispatcher with timeout protection...")
            # Note: EnhancedDispatcher has built-in 5-second timeout in _load_all_plugins()
            _explicit = os.getenv("RERANKER_TYPE", "").strip().lower()
            reranker_type = _explicit if _explicit else "none"
            dispatcher = EnhancedDispatcher(
                plugins=plugin_instances,  # Use existing plugins as base
                sqlite_store=sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,  # Enable dynamic loading
                lazy_load=True,  # Load plugins on demand
                semantic_search_enabled=True,
                memory_aware=True,  # Enable memory-aware plugin management
                multi_repo_enabled=None,  # Auto-detect from environment
                reranker_type=reranker_type,
            )

        supported_languages = dispatcher.supported_languages
        logger.info(
            f"Enhanced dispatcher created - supports {len(supported_languages)} languages"
        )
        logger.info(
            f"Languages: {', '.join(supported_languages[:10])}{'...' if len(supported_languages) > 10 else ''}"
        )

        # Qdrant / semantic-search availability — log clearly so users know what mode they're in
        if isinstance(dispatcher, EnhancedDispatcher) and getattr(dispatcher, "_semantic_indexer", None) is None:
            logger.warning(
                "Semantic search not available — running in BM25-only mode. "
                "Set VOYAGE_API_KEY (Voyage AI) or configure a vLLM endpoint in "
                "code-index-mcp.profiles.yaml to enable semantic (vector) search."
            )

        # Start filesystem watcher so the index stays current automatically.
        # Only for EnhancedDispatcher — SimpleDispatcher is read-only BM25 mode.
        # When _auto_index is True we defer .start() until after the initial index
        # completes to avoid concurrent SQLite writes during the bulk index pass.
        global _file_watcher
        if _file_watcher is None and isinstance(dispatcher, EnhancedDispatcher):
            try:
                _file_watcher = FileWatcher(root=current_dir, dispatcher=dispatcher)
                if not _auto_index:
                    _file_watcher.start()
                    logger.info(f"FileWatcher started, watching {current_dir}")
                # else: started inside _run_initial_index() after indexing completes
            except Exception as _fw_err:
                logger.warning(f"FileWatcher failed to start (non-fatal): {_fw_err}")

        # Guard: skip auto-index for very large repos to avoid hours of startup I/O.
        # MCP_AUTO_INDEX_MAX_FILES controls the threshold (default 100 000 files).
        if _auto_index:
            _max_files = int(os.getenv("MCP_AUTO_INDEX_MAX_FILES", "100000"))
            _file_count = 0
            for _root, _dirs, _files in os.walk(current_dir):
                _dirs[:] = [
                    d for d in _dirs
                    if d not in {".git", "node_modules", "__pycache__", ".venv", "venv"}
                ]
                _file_count += len(_files)
                if _file_count > _max_files:
                    break
            if _file_count > _max_files:
                logger.warning(
                    f"Repository has >{_max_files} files — skipping auto-index to avoid "
                    f"a long blocking startup. Set MCP_AUTO_INDEX_MAX_FILES to raise the "
                    f"limit, or run the 'reindex' MCP tool manually when ready."
                )
                _auto_index = False

        # If no index existed, kick off a full background reindex now.
        # Set MCP_AUTO_INDEX=false to disable for large repos and run reindex manually.
        # Tools return partial/empty results until it completes — server stays responsive.
        global _indexing_thread
        if (
            _auto_index
            and _indexing_thread is None
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
                finally:
                    # Start the watcher now that the initial index is complete
                    if _file_watcher is not None:
                        try:
                            _file_watcher.start()
                            logger.info(f"FileWatcher started after initial index, watching {_captured_dir}")
                        except Exception as _fw_err:
                            logger.warning(f"FileWatcher failed to start (non-fatal): {_fw_err}")

            global _indexing_total_files, _indexing_started_at
            _indexing_total_files = _file_count
            _indexing_started_at = time.time()

            _indexing_thread = threading.Thread(
                target=_run_initial_index, daemon=True, name="mcp-initial-index"
            )
            _indexing_thread.start()
            logger.info(f"Indexing {_captured_dir} in background — search results will populate shortly")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        initialization_error = str(e)
        # Don't raise - let the server run but return errors in tools


# Tool: Symbol Lookup
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="symbol_lookup",
            description="[USE BEFORE GREP] Look up any class, function, or method definition. 100x faster than grep. Returns file + line number. Fall back to Grep ONLY if this returns not_found.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The symbol name to look up",
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="search_code",
            description="[USE BEFORE GREP] Search code by pattern, keyword, or natural language (semantic=true). Indexed, <500ms, returns ranked results with line numbers and last_indexed timestamp. Fall back to Grep ONLY if this returns 0 results.",
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
            description="List all loaded plugins. Shows 48 supported languages with specialized and generic plugin information.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="reindex",
            description="Reindex files in the codebase. Updates the index for changed files or specific paths.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path to reindex. If not provided, reindexes all files.",
                    }
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
                },
            },
        ),
        types.Tool(
            name="summarize_sample",
            description=(
                "Summarize a sample of indexed files using the LLM and return results "
                "for quality evaluation. Does not persist results by default."
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
                },
            },
        ),
    ]


def validate_index(store: SQLiteStore, repo_path: Path) -> dict:
    """Validate that the index is up-to-date and accessible."""
    import sqlite3

    issues = []
    stats = {}

    try:
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()

        # Check total file count
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]
        stats["total_files"] = total_files

        # Check BM25 content count
        cursor.execute("SELECT COUNT(*) FROM bm25_content")
        bm25_count = cursor.fetchone()[0]
        stats["bm25_documents"] = bm25_count

        # Check for current repository files
        cursor.execute(
            "SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE ?",
            (f"{repo_path}%",),
        )
        current_repo_files = cursor.fetchone()[0]
        stats["current_repo_files"] = current_repo_files

        # Check for stale Docker paths
        cursor.execute(
            "SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE 'PathUtils.get_workspace_root() / %'"
        )
        docker_files = cursor.fetchone()[0]
        stats["docker_files"] = docker_files

        # Validation checks
        if total_files == 0:
            issues.append("Index is empty - no files indexed")

        if bm25_count == 0:
            issues.append("No BM25 documents in index")

        if current_repo_files == 0 and docker_files > 0:
            issues.append(
                f"Index contains {docker_files} Docker paths but no files from current repo"
            )

        # Sample path accessibility check
        cursor.execute("SELECT filepath FROM bm25_content LIMIT 10")
        sample_paths = cursor.fetchall()
        inaccessible_count = 0
        for (path,) in sample_paths:
            if not Path(path).exists():
                inaccessible_count += 1

        if inaccessible_count > len(sample_paths) * 0.5:
            issues.append(
                f"{inaccessible_count}/{len(sample_paths)} sampled paths are inaccessible"
            )

        conn.close()

    except Exception as e:
        issues.append(f"Database error: {str(e)}")

    return {"valid": len(issues) == 0, "issues": issues, "stats": stats}


def translate_path(path: str) -> str:
    """Translate Docker paths to current environment paths."""
    if not path:
        return ""

    # Handle Docker PathUtils.get_workspace_root() /  paths
    if path.startswith("PathUtils.get_workspace_root() / "):
        # Replace PathUtils.get_workspace_root() /  with current working directory
        translated = path.replace(
            "PathUtils.get_workspace_root() / ", str(Path.cwd()) + "/", 1
        )
        # Verify the translated path exists
        if Path(translated).exists():
            return translated
        # Return relative path as fallback
        return path.replace("PathUtils.get_workspace_root() / ", "", 1)

    # Handle absolute paths that already exist
    if path.startswith("/") and Path(path).exists():
        return path

    # Handle relative paths
    if not path.startswith("/"):
        full_path = Path.cwd() / path
        if full_path.exists():
            return str(full_path)

    # Return original path if no translation worked
    return path


def ensure_response(data: Any) -> str:
    """Ensure response is never empty and always valid JSON."""
    if data is None:
        data = {"status": "empty", "message": "No data returned"}

    try:
        # Ensure it's valid JSON
        response = json.dumps(data, indent=2)

        # Log response in debug mode
        if DEBUG_MODE:
            logger.info(f"MCP Response: {response[:200]}...")

        # Ensure minimum size
        if len(response) < 10:
            response = json.dumps(
                {"status": "minimal", "original": str(data), "timestamp": time.time()},
                indent=2,
            )

        return response
    except Exception as e:
        # Fallback to ensure we always return something
        return json.dumps(
            {
                "error": "Response serialization failed",
                "details": str(e),
                "timestamp": time.time(),
            },
            indent=2,
        )


from mcp_server.indexing.summarization import ComprehensiveChunkWriter, FileBatchSummarizer, LazyChunkWriter

# Global chunk writer instance
lazy_summarizer = None


@server.call_tool()
async def call_tool(
    name: str, arguments: dict | None
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    global dispatcher, lazy_summarizer

    # Resolve the current MCP session so the lazy summarizer can issue
    # sampling/createMessage requests back to the client.
    _current_session = None
    _client_name = None
    try:
        from mcp.server.lowlevel.server import request_ctx

        _ctx = request_ctx.get()
        _current_session = _ctx.session
        # clientInfo lives on client_params, not directly on session
        _params = getattr(_current_session, "client_params", None)
        _client_name = getattr(getattr(_params, "clientInfo", None), "name", None)
        # Log full capabilities for diagnostics
        _caps = getattr(_params, "capabilities", None)
        logger.debug("MCP client caps: %s", _caps)
    except Exception as _e:
        logger.debug("request_ctx not available: %s", _e)

    if lazy_summarizer is None:
        _settings = Settings.from_environment()
        lazy_summarizer = LazyChunkWriter(
            db_path=sqlite_store.db_path if sqlite_store else "code_index.db",
            qdrant_client=None,  # Passed inside SemanticIndexer
            session=_current_session,
            client_name=_client_name,
            summarization_config=_settings.get_profile_summarization_config(
                _settings.semantic_default_profile
            ),
        )
        lazy_summarizer.start()
    else:
        # Refresh the session reference on every call so we always hold a
        # live handle even if the client reconnected.
        if _current_session is not None:
            lazy_summarizer.update_session(_current_session)

    # Always log tool calls for debugging
    logger.info(f"=== MCP Tool Call ===")
    logger.info(f"Tool: {name}")
    logger.info(f"Arguments: {arguments}")
    logger.info(f"Thread: {threading.current_thread().name}")
    logger.info(f"Event loop: {asyncio.get_running_loop()}")

    # Track request time
    start_time = time.time()
    response = None

    try:
        if dispatcher is None:
            await initialize_services()

        # Check if initialization failed
        if initialization_error:
            error_response = {
                "error": "MCP server initialization failed",
                "details": initialization_error,
                "suggestion": (
                    "No index found. Run 'mcp-index index' or "
                    "'python scripts/reindex_current_repo.py' in your repository root. "
                    "Check server logs for the exact paths searched."
                ),
            }
            response = [
                types.TextContent(type="text", text=ensure_response(error_response))
            ]
            return response

        # Check if dispatcher is still None
        if dispatcher is None:
            error_response = {
                "error": "MCP dispatcher not initialized",
                "details": "Unable to load dispatcher after initialization",
                "suggestion": "Check server logs for errors",
            }
            response = [
                types.TextContent(type="text", text=ensure_response(error_response))
            ]
            return response
        if name == "symbol_lookup":
            symbol = arguments.get("symbol") if arguments else None
            if not symbol:
                error_response = {
                    "error": "Missing parameter",
                    "details": "'symbol' parameter is required",
                }
                response = [
                    types.TextContent(type="text", text=ensure_response(error_response))
                ]

            result = dispatcher.lookup(symbol)
            if result:
                # Translate Docker paths to current environment
                defined_in = result.get("defined_in", "")
                translated_path = translate_path(defined_in)

                response_data = {
                    "symbol": result.get("symbol"),
                    "kind": result.get("kind"),
                    "language": result.get("language"),
                    "signature": result.get("signature"),
                    "doc": result.get("doc"),
                    "defined_in": translated_path,
                    "line": result.get("line"),
                    "span": result.get("span"),
                }

                # Add navigation hint if line number is available
                if result.get("line") and translated_path:
                    offset = result.get("line", 1) - 1
                    response_data["_usage_hint"] = (
                        f"To view definition: Read(file_path='{translated_path}', offset={offset}, limit=20)"
                    )

                response = [
                    types.TextContent(type="text", text=ensure_response(response_data))
                ]
            else:
                # Check index validation
                response_data = {
                    "result": "not_found",
                    "symbol": symbol,
                    "message": f"Symbol '{symbol}' not found in index",
                }

                if hasattr(dispatcher, "_sqlite_store") and dispatcher._sqlite_store:
                    validation_result = validate_index(
                        dispatcher._sqlite_store, Path.cwd()
                    )
                    if not validation_result["valid"]:
                        response_data["index_issues"] = validation_result["issues"]
                        response_data["suggestion"] = (
                            "Index may be stale. Run 'python scripts/reindex_current_repo.py'"
                        )

                response = [
                    types.TextContent(type="text", text=ensure_response(response_data))
                ]

        elif name == "search_code":
            query = arguments.get("query") if arguments else None
            if not query:
                error_response = {
                    "error": "Missing parameter",
                    "details": "'query' parameter is required",
                }
                response = [
                    types.TextContent(type="text", text=ensure_response(error_response))
                ]

            semantic = arguments.get("semantic", False) if arguments else False
            fuzzy = arguments.get("fuzzy", False) if arguments else False
            limit = arguments.get("limit", 20) if arguments else 20
            repository = arguments.get("repository") if arguments else None

            # Handle multi-repository search if enabled
            if (
                repository
                and hasattr(dispatcher, "_multi_repo_manager")
                and dispatcher._multi_repo_manager
            ):
                try:
                    from ..storage.multi_repo_manager import MultiRepoIndexManager

                    repo_id = MultiRepoIndexManager.resolve_repo_id(repository)

                    # Check authorization
                    if not dispatcher._multi_repo_manager.is_repo_authorized(repo_id):
                        error_response = {
                            "error": "Repository not authorized",
                            "repository": repository,
                            "repo_id": repo_id,
                            "message": "Add to MCP_REFERENCE_REPOS environment variable",
                        }
                        response = [
                            types.TextContent(
                                type="text", text=ensure_response(error_response)
                            )
                        ]
                        return response

                    # Properly handle multi-repo search with timeout protection
                    try:
                        # Set a 10-second timeout for multi-repo search
                        search_results = await asyncio.wait_for(
                            dispatcher._multi_repo_manager.search_code(
                                query, repository_ids=[repo_id], limit=limit
                            ),
                            timeout=10.0,
                        )

                        # Convert CrossRepoSearchResult to standard format
                        results = []
                        for repo_result in search_results:
                            for r in repo_result.results:
                                results.append(
                                    {
                                        "file": r.get("file", r.get("file_path", "")),
                                        "line": r.get("line", 0),
                                        "snippet": r.get(
                                            "snippet", r.get("context", "")
                                        ),
                                        "score": r.get("score", 0.0),
                                        "repository": repo_result.repository_name,
                                    }
                                )

                        logger.info(
                            f"Multi-repo search completed for '{query}' in repository {repository}"
                        )

                    except asyncio.TimeoutError:
                        logger.warning(
                            f"Multi-repo search timed out after 10s, falling back to single-repo search"
                        )
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: list(
                                        dispatcher.search(
                                            query, semantic=semantic, fuzzy=fuzzy, limit=limit
                                        )
                                    ),
                                ),
                                timeout=5.0,  # Shorter timeout for fallback
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search also timed out")
                            results = []
                    except AttributeError as e:
                        # Handle case where search_code method doesn't exist
                        logger.warning(
                            f"Multi-repo search method not available: {e}, falling back to single-repo search"
                        )
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: list(
                                        dispatcher.search(
                                            query, semantic=semantic, fuzzy=fuzzy, limit=limit
                                        )
                                    ),
                                ),
                                timeout=10.0,
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search timed out")
                            results = []
                    except Exception as e:
                        logger.error(
                            f"Multi-repo search failed: {e}, falling back to single-repo search"
                        )
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: list(
                                        dispatcher.search(
                                            query, semantic=semantic, fuzzy=fuzzy, limit=limit
                                        )
                                    ),
                                ),
                                timeout=10.0,
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search timed out")
                            results = []

                except Exception as e:
                    logger.error(f"Multi-repo search failed: {e}")
                    # Fall back to normal search with timeout
                    try:
                        results = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: list(
                                    dispatcher.search(
                                        query, semantic=semantic, limit=limit
                                    )
                                ),
                            ),
                            timeout=10.0,
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Fallback search also timed out")
                        results = []
            else:
                # Normal single-repo search with timeout protection
                logger.info(f"Executing single-repo search for query: {query}")
                try:
                    # Use asyncio timeout for consistency
                    # Create async wrapper for sync search method
                    async def async_search():
                        return list(
                            dispatcher.search(query, semantic=semantic, fuzzy=fuzzy, limit=limit)
                        )

                    # Run with timeout
                    results = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: list(
                                dispatcher.search(query, semantic=semantic, fuzzy=fuzzy, limit=limit)
                            ),
                        ),
                        timeout=10.0,
                    )
                    logger.info(
                        f"Single-repo search completed with {len(results)} results"
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Single-repo search timed out after 10s for query: {query}"
                    )
                    error_response = {
                        "error": "Search timeout",
                        "details": "Search operation exceeded 10 second timeout",
                        "query": query,
                        "suggestion": "Try a simpler query or check index status with get_status",
                    }
                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(error_response)
                        )
                    ]
                    return response
                except Exception as e:
                    logger.error(f"Single-repo search failed: {e}")
                    error_response = {
                        "error": "Search failed",
                        "details": str(e),
                        "query": query,
                    }
                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(error_response)
                        )
                    ]
                    return response

            # Check if we have index validation info
            if hasattr(dispatcher, "_sqlite_store") and dispatcher._sqlite_store:
                validation_result = validate_index(dispatcher._sqlite_store, Path.cwd())
                if not validation_result["valid"] and len(results) == 0:
                    error_response = {
                        "error": "No results found - index may be stale",
                        "query": query,
                        "index_stats": validation_result["stats"],
                        "issues": validation_result["issues"],
                        "suggestion": "Run 'python scripts/reindex_current_repo.py' to update index",
                    }
                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(error_response)
                        )
                    ]
                    return response

            # Add note if repository was specified
            multi_repo_info = None
            if (
                repository
                and hasattr(dispatcher, "_multi_repo_manager")
                and dispatcher._multi_repo_manager
            ):
                # Check if results include repository info
                has_repo_info = any(
                    "repository" in r for r in results if isinstance(r, dict)
                )
                if has_repo_info:
                    multi_repo_info = f"Searched in repository: {repository}"

            if results:
                results_data = []
                for r in results:
                    # Translate Docker paths to current environment
                    file_path = translate_path(r.get("file", ""))

                    result_item = {
                        "file": file_path,
                        "line": r.get("line"),
                        "line_end": r.get("line_end"),
                        "symbol": r.get("symbol"),
                        "snippet": r.get("snippet"),
                        "last_indexed": r.get("last_modified"),
                    }

                    # Add navigation hint if line number is available
                    if r.get("line") and file_path:
                        offset = r.get("line", 1) - 1
                        result_item["_usage_hint"] = (
                            f"For more context: Read(file_path='{file_path}', offset={offset}, limit=30)"
                        )

                    results_data.append(result_item)

                # Lazily enqueue top results for background summarization.
                if (
                    lazy_summarizer
                    and lazy_summarizer.can_summarize()
                    and sqlite_store
                ):
                    for r in results[:5]:
                        raw_file = r.get("file", "")
                        raw_line = r.get("line", 1)
                        if raw_file and raw_line:
                            chunk_info = sqlite_store.find_chunk_at_line(
                                raw_file, int(raw_line)
                            )
                            if chunk_info:
                                lazy_summarizer.enqueue(chunk_info)

                # Include repository info in response if applicable
                if multi_repo_info:
                    response_with_info = {
                        "results": results_data,
                        "search_scope": multi_repo_info,
                        "multi_repo": True,
                    }
                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(response_with_info)
                        )
                    ]
                else:
                    _indexing_active = _indexing_thread is not None and _indexing_thread.is_alive()
                    if _indexing_active:
                        search_response = {
                            "results": results_data,
                            "indexing_in_progress": True,
                            "note": "Initial index is still building — results may be incomplete",
                        }
                    else:
                        search_response = results_data
                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(search_response)
                        )
                    ]
            else:
                _indexing_active = _indexing_thread is not None and _indexing_thread.is_alive()
                response_data = {
                    "results": [],
                    "query": query,
                    "message": (
                        "No results yet — initial index is still building"
                        if _indexing_active
                        else "No results found in index"
                    ),
                }
                if _indexing_active:
                    response_data["indexing_in_progress"] = True
                response = [
                    types.TextContent(type="text", text=ensure_response(response_data))
                ]

        elif name == "get_status":
            # Get comprehensive statistics from enhanced dispatcher
            if hasattr(dispatcher, "get_statistics"):
                stats = dispatcher.get_statistics()
                health = (
                    dispatcher.health_check()
                    if hasattr(dispatcher, "health_check")
                    else {}
                )
            else:
                # Fallback for basic dispatcher
                plugin_count = (
                    len(dispatcher._plugins) if hasattr(dispatcher, "_plugins") else 0
                )
                stats = {
                    "total_plugins": plugin_count,
                    "loaded_languages": [],
                    "supported_languages": plugin_count,
                    "operations": {},
                    "by_language": {},
                }
                health = {"status": "unknown"}

            status_data = {
                "status": health.get("status", "operational"),
                "version": "0.2.0",
                "dispatcher_type": dispatcher.__class__.__name__,
                "dispatcher_mode": "simple" if USE_SIMPLE_DISPATCHER else "enhanced",
                "features": {
                    "dynamic_loading": getattr(dispatcher, "_use_factory", False),
                    "lazy_loading": getattr(dispatcher, "_lazy_load", False),
                    "semantic_search": getattr(dispatcher, "_semantic_enabled", False),
                    "semantic_available": (
                        isinstance(dispatcher, EnhancedDispatcher)
                        and getattr(dispatcher, "_semantic_indexer", None) is not None
                    ),
                    "semantic_indexer_active": getattr(dispatcher, "_semantic_indexer", None) is not None,
                    "advanced_features": getattr(dispatcher, "_enable_advanced", False),
                    "timeout_protection": True,
                    "file_watcher": _file_watcher is not None,
                    "initial_index_running": _indexing_thread is not None and _indexing_thread.is_alive(),
                    "indexing_elapsed_seconds": (
                        int(time.time() - _indexing_started_at)
                        if (_indexing_thread is not None and _indexing_thread.is_alive() and _indexing_started_at)
                        else None
                    ),
                    "indexing_estimated_files": (
                        _indexing_total_files
                        if (_indexing_thread is not None and _indexing_thread.is_alive() and _indexing_total_files)
                        else None
                    ),
                },
                "languages": {
                    "supported": stats.get("supported_languages", 0),
                    "loaded": len(stats.get("loaded_languages", [])),
                    "loaded_list": stats.get("loaded_languages", []),
                },
                "plugins": {
                    "total": stats.get("total_plugins", 0),
                    "by_language": stats.get("by_language", {}),
                },
                "operations": stats.get("operations", {}),
                "health": health,
                "summarization": {
                    "available": lazy_summarizer.can_summarize() if lazy_summarizer else False,
                    "mcp_sampling": lazy_summarizer._has_sampling_capability() if lazy_summarizer else False,
                    "direct_api": lazy_summarizer._has_direct_api() if lazy_summarizer else False,
                    "api_provider": (
                        "anthropic" if os.environ.get("ANTHROPIC_API_KEY")
                        else "openai" if os.environ.get("OPENAI_API_KEY")
                        else None
                    ),
                    "client": _client_name,
                    "session_available": _current_session is not None,
                    "raw_capabilities": str(getattr(getattr(_current_session, "client_params", None), "capabilities", None)) if _current_session else None,
                },
            }

            response = [
                types.TextContent(type="text", text=ensure_response(status_data))
            ]

        elif name == "list_plugins":
            response_data = {
                "plugin_manager_plugins": [],
                "supported_languages": [],
                "loaded_plugins": [],
            }

            # Get plugin manager plugins (existing 6)
            if plugin_manager is not None:
                plugin_infos = plugin_manager._registry.list_plugins()
                plugin_status = plugin_manager.get_plugin_status()

                for info in plugin_infos:
                    status = plugin_status.get(info.name, {})
                    plugin_data = {
                        "name": info.name,
                        "version": info.version,
                        "description": info.description,
                        "language": info.language,
                        "file_extensions": info.file_extensions,
                        "state": status.get("state", "unknown"),
                        "enabled": status.get("enabled", False),
                    }
                    response_data["plugin_manager_plugins"].append(plugin_data)

            # Get all supported languages from enhanced dispatcher
            if hasattr(dispatcher, "supported_languages"):
                response_data["supported_languages"] = dispatcher.supported_languages

            # Get loaded plugin details
            if hasattr(dispatcher, "_by_lang"):
                for lang, plugin in dispatcher._by_lang.items():
                    loaded_plugin_data = {
                        "language": lang,
                        "class": plugin.__class__.__name__,
                        "is_generic": "GenericTreeSitterPlugin"
                        in plugin.__class__.__name__,
                        "semantic_enabled": getattr(plugin, "_enable_semantic", False),
                    }
                    if hasattr(plugin, "get_indexed_count"):
                        loaded_plugin_data["indexed_files"] = plugin.get_indexed_count()
                    response_data["loaded_plugins"].append(loaded_plugin_data)

            response = [
                types.TextContent(type="text", text=ensure_response(response_data))
            ]

        elif name == "reindex":
            path = arguments.get("path") if arguments else None

            if path:
                # Reindex specific path
                target_path = Path(path)
                if not target_path.exists():
                    return [
                        types.TextContent(
                            type="text", text=f"Error: Path not found: {path}"
                        )
                    ]

                if target_path.is_file():
                    # Single file - use index_file
                    try:
                        dispatcher.index_file(target_path)
                        return [
                            types.TextContent(
                                type="text", text=f"Reindexed file: {path}"
                            )
                        ]
                    except Exception as e:
                        return [
                            types.TextContent(
                                type="text", text=f"Error reindexing {path}: {str(e)}"
                            )
                        ]
                else:
                    # Directory - use index_directory which handles ignore patterns
                    stats = dispatcher.index_directory(target_path, recursive=True)
                    lexical_rows = sqlite_store.rebuild_fts_code() if sqlite_store else 0

                    response_data = {
                        "path": str(target_path),
                        "mode": "merge",
                        "indexed_files": stats["indexed_files"],
                        "ignored_files": stats["ignored_files"],
                        "failed_files": stats["failed_files"],
                        "total_files": stats["total_files"],
                        "by_language": stats["by_language"],
                        "lexical_rows": lexical_rows,
                        "semantic_indexed": stats.get("semantic_indexed"),
                        "semantic_failed": stats.get("semantic_failed"),
                        "semantic_skipped": stats.get("semantic_skipped"),
                        "total_embedding_units": stats.get("total_embedding_units"),
                        "merge_note": (
                            "Changed/new files updated; deleted files are not purged — "
                            "FileWatcher handles those on next change, or reindex again after deletions."
                        ),
                    }

                    response = [
                        types.TextContent(
                            type="text", text=ensure_response(response_data)
                        )
                    ]
            else:
                # Reindex all files in current directory
                stats = dispatcher.index_directory(Path("."), recursive=True)
                lexical_rows = sqlite_store.rebuild_fts_code() if sqlite_store else 0

                response_data = {
                    "path": ".",
                    "mode": "merge",
                    "indexed_files": stats["indexed_files"],
                    "ignored_files": stats["ignored_files"],
                    "failed_files": stats["failed_files"],
                    "total_files": stats["total_files"],
                    "by_language": stats["by_language"],
                    "lexical_rows": lexical_rows,
                    "semantic_indexed": stats.get("semantic_indexed"),
                    "semantic_failed": stats.get("semantic_failed"),
                    "semantic_skipped": stats.get("semantic_skipped"),
                    "total_embedding_units": stats.get("total_embedding_units"),
                    "semantic_error": stats.get("semantic_error"),
                    "semantic_paths_queued": stats.get("semantic_paths_queued"),
                    "semantic_indexer_present": stats.get("semantic_indexer_present"),
                    "merge_note": (
                        "Changed/new files updated; deleted files are not purged — "
                        "FileWatcher handles those on next change, or reindex again after deletions."
                    ),
                }

                response = [
                    types.TextContent(type="text", text=ensure_response(response_data))
                ]

        elif name == "write_summaries":
            if lazy_summarizer is None or not lazy_summarizer.can_summarize():
                response = [
                    types.TextContent(
                        type="text",
                        text=ensure_response(
                            {
                                "error": "Summarization not available",
                                "details": (
                                    "No API key configured. Set CEREBRAS_API_KEY, "
                                    "ANTHROPIC_API_KEY, or OPENAI_API_KEY."
                                ),
                            }
                        ),
                    )
                ]
            else:
                db_path = sqlite_store.db_path if sqlite_store else "code_index.db"
                limit_arg = int((arguments or {}).get("limit", 500))
                model_used = lazy_summarizer._get_model_name()

                _settings = Settings.from_environment()
                writer = ComprehensiveChunkWriter(
                    db_path=db_path,
                    qdrant_client=None,
                    session=_current_session,
                    client_name=_client_name,
                    summarization_config=_settings.get_profile_summarization_config(
                        _settings.semantic_default_profile
                    ),
                )
                chunks_written = await writer.process_all(limit=limit_arg)

                response = [
                    types.TextContent(
                        type="text",
                        text=ensure_response(
                            {
                                "chunks_summarized": chunks_written,
                                "limit": limit_arg,
                                "model_used": model_used,
                                "persisted": True,
                            }
                        ),
                    )
                ]

        elif name == "summarize_sample":
            if lazy_summarizer is None or not lazy_summarizer.can_summarize():
                response = [
                    types.TextContent(
                        type="text",
                        text=ensure_response(
                            {
                                "error": "Summarization not available",
                                "details": (
                                    "No API key configured. Set CEREBRAS_API_KEY, "
                                    "ANTHROPIC_API_KEY, or OPENAI_API_KEY."
                                ),
                            }
                        ),
                    )
                ]
            else:
                import sqlite3 as _sqlite3
                paths_arg = (arguments or {}).get("paths")
                n_arg = int((arguments or {}).get("n", 3))
                persist_flag = bool((arguments or {}).get("persist", False))

                db_path = sqlite_store.db_path if sqlite_store else "code_index.db"
                model_used = lazy_summarizer._get_model_name()

                # Resolve file rows.
                with _sqlite3.connect(db_path) as _conn:
                    if paths_arg:
                        placeholders = ",".join("?" * len(paths_arg))
                        file_rows = _conn.execute(
                            f"SELECT id, path, language FROM files WHERE path IN ({placeholders})",
                            paths_arg,
                        ).fetchall()
                    else:
                        file_rows = _conn.execute(
                            "SELECT id, path, language FROM files ORDER BY RANDOM() LIMIT ?",
                            (n_arg,),
                        ).fetchall()

                file_results = []
                total_chunks = 0

                for file_id, file_path, language in file_rows:
                    # Read file from disk.
                    try:
                        with open(file_path, encoding="utf-8", errors="replace") as _fh:
                            file_content = _fh.read()
                    except Exception as _e:
                        file_results.append(
                            {"file_path": file_path, "error": str(_e)}
                        )
                        continue

                    # Load chunks with symbol names via JOIN.
                    with _sqlite3.connect(db_path) as _conn:
                        chunk_rows = _conn.execute(
                            """SELECT c.chunk_id, c.line_start, c.line_end,
                                      c.content, c.node_type, c.parent_chunk_id,
                                      c.language, c.symbol_id, s.name AS symbol
                               FROM code_chunks c
                               LEFT JOIN symbols s ON c.symbol_id = s.id
                               WHERE c.file_id = ?
                               ORDER BY c.chunk_index, c.line_start""",
                            (file_id,),
                        ).fetchall()

                    chunks = [
                        {
                            "chunk_id": r[0],
                            "line_start": r[1],
                            "line_end": r[2],
                            "content": r[3],
                            "node_type": r[4],
                            "parent_chunk_id": r[5],
                            "language": r[6] or language,
                            "symbol_id": r[7],
                        }
                        for r in chunk_rows
                    ]
                    symbol_map = {
                        r[7]: r[8] for r in chunk_rows if r[7] and r[8]
                    }

                    used_batch = (
                        len(file_content) <= 400_000
                        and bool(os.environ.get("CEREBRAS_API_KEY"))
                    )

                    summarizer = FileBatchSummarizer(
                        db_path=db_path,
                        qdrant_client=None,
                        session=_current_session,
                        client_name=_client_name,
                    )

                    try:
                        summaries = await summarizer.summarize_file_chunks(
                            file_id=file_id,
                            file_path=file_path,
                            file_content=file_content,
                            chunks=chunks,
                            symbol_map=symbol_map,
                            persist=persist_flag,
                        )
                    except Exception as _e:
                        file_results.append(
                            {"file_path": file_path, "error": str(_e)}
                        )
                        continue

                    # Build symbol/line lookup for output enrichment.
                    chunk_meta = {
                        c["chunk_id"]: c for c in chunks
                    }
                    summary_list = []
                    for s in summaries:
                        meta = chunk_meta.get(s.chunk_id, {})
                        sym_name = (
                            symbol_map.get(meta.get("symbol_id"))
                            or meta.get("node_type")
                            or s.chunk_id
                        )
                        summary_list.append(
                            {
                                "symbol": sym_name,
                                "lines": f"{meta.get('line_start', '?')}-{meta.get('line_end', '?')}",
                                "summary": s.summary,
                            }
                        )

                    total_chunks += len(summaries)
                    file_results.append(
                        {
                            "file_path": file_path,
                            "chunk_count": len(summaries),
                            "used_batch_path": used_batch,
                            "summaries": summary_list,
                        }
                    )

                response_data = {
                    "files_processed": len(file_results),
                    "total_chunks": total_chunks,
                    "model_used": model_used,
                    "persisted": persist_flag,
                    "files": file_results,
                }
                response = [
                    types.TextContent(type="text", text=ensure_response(response_data))
                ]

        else:
            response = [
                types.TextContent(
                    type="text",
                    text=ensure_response(
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
                            ],
                        }
                    ),
                )
            ]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        error_response = {
            "error": f"Tool execution failed: {name}",
            "details": str(e),
            "tool": name,
        }
        response = [
            types.TextContent(type="text", text=ensure_response(error_response))
        ]
    finally:
        # Log response time and ensure we always return something
        elapsed = time.time() - start_time
        if DEBUG_MODE:
            logger.info(f"MCP Response time: {elapsed:.3f}s for tool {name}")

        # Ensure we have a response
        if response is None:
            response = [
                types.TextContent(
                    type="text",
                    text=ensure_response(
                        {
                            "error": "No response generated",
                            "tool": name,
                            "elapsed": elapsed,
                        }
                    ),
                )
            ]

    # Log response
    elapsed = time.time() - start_time
    logger.info(f"=== MCP Tool Response ===")
    logger.info(f"Tool: {name}")
    logger.info(f"Elapsed: {elapsed:.2f}s")
    logger.info(f"Response type: {type(response)}")
    if response and len(response) > 0:
        logger.info(
            f"Response length: {len(response[0].text) if hasattr(response[0], 'text') else 'N/A'}"
        )

    # Return the response
    return response


async def main():
    """Main entry point."""
    # Log configuration
    logger.info("=" * 60)
    logger.info("Code Index MCP Server Starting")
    logger.info(
        f"Dispatcher Mode: {'Simple (BM25-only)' if USE_SIMPLE_DISPATCHER else 'Enhanced (with plugins)'}"
    )
    logger.info(f"Plugin Timeout: {PLUGIN_LOAD_TIMEOUT} seconds")
    logger.info(f"Debug Mode: {'Enabled' if DEBUG_MODE else 'Disabled'}")
    logger.info("=" * 60)

    # Skip eager initialization — the dispatcher and sqlite_store are
    # initialized lazily on the first tool call (see call_tool above).
    # Eager init was causing the stdio server to never start because the
    # embedded Qdrant client blocks the event loop indefinitely on startup.

    # Run the stdio server
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    finally:
        if _file_watcher is not None:
            _file_watcher.stop()
            logger.info("FileWatcher stopped")


if __name__ == "__main__":
    asyncio.run(main())
