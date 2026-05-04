"""MCP tool handler functions — one async def per tool.

Each handler resolves a RepoContext via RepoResolver from the tool's path/repository
argument or the MCP_WORKSPACE_ROOT default, then delegates to the dispatcher.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional, Sequence

import mcp.types as types

from mcp_server.cli.bootstrap import _allowed_roots, _path_within_allowed, validate_index
from mcp_server.cli.task_reindex import run_reindex_task
from mcp_server.cli.task_write_summaries import run_write_summaries_task
from mcp_server.core.repo_context import RepoContext
from mcp_server.core.repo_resolver import RepoResolver
from mcp_server.dispatcher.dispatcher_enhanced import SemanticSearchFailure
from mcp_server.dispatcher.protocol import DispatcherProtocol
from mcp_server.health.repository_readiness import (
    ReadinessClassifier,
    RepositoryReadiness,
    RepositoryReadinessState,
)

logger = logging.getLogger(__name__)

DEBUG_MODE = os.getenv("MCP_DEBUG", "0") == "1"


def _looks_like_path(x: str) -> bool:
    """True when x is path-shaped (contains separator or resolves to existing entity).

    Returns False for plain repo names/aliases with no path separators.
    Contract consumed verbatim by SL-3.
    """
    if not x:
        return False
    if "/" in x or "\\" in x:
        return True
    try:
        return Path(x).exists()
    except Exception:
        return False


def _ensure_response(data: Any) -> str:
    """Ensure response is never empty and always valid JSON."""
    if data is None:
        data = {"status": "empty", "message": "No data returned"}
    try:
        response = json.dumps(data, indent=2)
        if DEBUG_MODE:
            logger.info(f"MCP Response: {response[:200]}...")
        if len(response) < 10:
            response = json.dumps(
                {"status": "minimal", "original": str(data), "timestamp": time.time()},
                indent=2,
            )
        return response
    except Exception as e:
        return json.dumps(
            {"error": "Response serialization failed", "details": str(e), "timestamp": time.time()},
            indent=2,
        )


def _json_text_response(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=_ensure_response(data))]


def _translate_path(path: str) -> str:
    """Translate legacy Docker paths to current environment paths."""
    if not path:
        return ""
    if path.startswith("PathUtils.get_workspace_root() / "):
        translated = path.replace("PathUtils.get_workspace_root() / ", str(Path.cwd()) + "/", 1)
        if Path(translated).exists():
            return translated
        return path.replace("PathUtils.get_workspace_root() / ", "", 1)
    if path.startswith("/") and Path(path).exists():
        return path
    if not path.startswith("/"):
        full_path = Path.cwd() / path
        if full_path.exists():
            return str(full_path)
    return path


def _resolve_ctx(
    repo_resolver: RepoResolver,
    path_arg: Optional[str],
) -> Optional[RepoContext]:
    """Resolve a RepoContext from path_arg or MCP_WORKSPACE_ROOT fallback."""
    readiness = _classify_ctx(repo_resolver, path_arg)
    if readiness is not None and readiness.state in {
        RepositoryReadinessState.UNREGISTERED_REPOSITORY,
        RepositoryReadinessState.UNSUPPORTED_WORKTREE,
    }:
        return None

    target = path_arg or os.environ.get("MCP_WORKSPACE_ROOT", "")
    if not target:
        target = str(Path.cwd())
    try:
        return repo_resolver.resolve(Path(target))
    except Exception as exc:
        logger.debug("RepoResolver.resolve(%s) failed: %s", target, exc)
        return None


def _classify_ctx(
    repo_resolver: RepoResolver,
    path_arg: Optional[str],
) -> Optional[RepositoryReadiness]:
    """Classify a tool repository/path target when the resolver supports it."""
    target = path_arg or os.environ.get("MCP_WORKSPACE_ROOT", "")
    if not target:
        target = str(Path.cwd())
    classifier = getattr(repo_resolver, "classify", None)
    if not callable(classifier):
        return None
    try:
        readiness = classifier(Path(target))
    except Exception as exc:
        logger.debug("RepoResolver.classify(%s) failed: %s", target, exc)
        return None
    return readiness if isinstance(readiness, RepositoryReadiness) else None


def _unsupported_worktree_response(readiness: RepositoryReadiness) -> list[types.TextContent]:
    return _json_text_response(
        {
            "results": [],
            "code": readiness.code,
            "readiness": readiness.to_dict(),
            "message": "Repository path is an unsupported sibling worktree.",
        }
    )


def _index_unavailable_response(
    readiness: RepositoryReadiness,
    tool: str,
    *,
    query: Optional[str] = None,
    symbol: Optional[str] = None,
) -> list[types.TextContent]:
    response: dict[str, Any] = {
        "error": "Index unavailable",
        "code": "index_unavailable",
        "tool": tool,
        "safe_fallback": "native_search",
        "readiness": readiness.to_dict(),
        "message": "Indexed search is available only when repository readiness is ready.",
        "remediation": readiness.remediation,
    }
    if query is not None:
        response["query"] = query
    if symbol is not None:
        response["symbol"] = symbol
    return _json_text_response(response)


def _secondary_readiness_refusal_response(
    readiness: RepositoryReadiness,
    tool: str,
) -> list[types.TextContent]:
    response: dict[str, Any] = {
        "results": [],
        "code": readiness.code,
        "tool": tool,
        "readiness": readiness.to_dict(),
        "message": f"{tool} is available only when repository readiness is ready.",
        "remediation": readiness.remediation,
    }
    if tool == "reindex":
        response["mutation_performed"] = False
    else:
        response["persisted"] = False
    return _json_text_response(response)


def _semantic_not_ready_response(
    semantic_readiness: Any,
    *,
    query: str,
) -> list[types.TextContent]:
    response = {
        "results": [],
        "code": "semantic_not_ready",
        "query": query,
        "semantic_requested": True,
        "semantic_source": "semantic",
        "semantic_profile_id": semantic_readiness.profile_id,
        "semantic_collection_name": semantic_readiness.collection_name,
        "semantic_fallback_status": "refused_not_ready",
        "semantic_readiness": semantic_readiness.to_dict(),
        "message": "Semantic search requested, but enriched semantic vectors are not ready.",
        "remediation": semantic_readiness.remediation,
    }
    return _json_text_response(response)


def _semantic_failure_response(
    *,
    query: str,
    semantic_readiness: Any | None,
    error: Exception,
) -> list[types.TextContent]:
    profile_id = getattr(semantic_readiness, "profile_id", None)
    collection_name = getattr(semantic_readiness, "collection_name", None)
    if isinstance(error, SemanticSearchFailure):
        profile_id = error.profile_id or profile_id
        collection_name = error.collection_name or collection_name

    response = {
        "results": [],
        "code": "semantic_search_failed",
        "query": query,
        "semantic_requested": True,
        "semantic_source": "semantic",
        "semantic_profile_id": profile_id,
        "semantic_collection_name": collection_name,
        "semantic_fallback_status": "failed_runtime",
        "semantic_readiness": semantic_readiness.to_dict() if semantic_readiness else None,
        "message": "Semantic search failed at runtime; lexical fallback was not used.",
        "details": str(error),
    }
    return _json_text_response(response)


def _record_reindexed_files(active_store: Any, workspace_root: Path, target_path: Path) -> int:
    """Record durable file rows for handler-driven reindex responses."""
    if active_store is None:
        return 0

    repo_row = active_store.ensure_repository_row(workspace_root)
    if target_path.is_file():
        paths = [target_path]
    else:
        paths = [
            p
            for p in target_path.rglob("*")
            if p.is_file() and ".git" not in p.parts and ".mcp-index" not in p.parts
        ]

    recorded = 0
    for file_path in paths:
        try:
            relative_path = file_path.relative_to(workspace_root).as_posix()
        except ValueError:
            relative_path = file_path.name
        try:
            active_store.store_file(
                repo_row,
                path=file_path,
                relative_path=relative_path,
                language=file_path.suffix.lstrip(".") or None,
                size=file_path.stat().st_size,
            )
            recorded += 1
        except Exception as exc:
            logger.debug("Could not record reindexed file %s: %s", file_path, exc)
    return recorded


async def handle_symbol_lookup(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
) -> Sequence[types.TextContent]:
    symbol = (arguments or {}).get("symbol")
    if not symbol:
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {"error": "Missing parameter", "details": "'symbol' parameter is required"}
                ),
            )
        ]

    repository = (arguments or {}).get("repository")
    if repository and _looks_like_path(repository):
        allowed = _allowed_roots()
        if not _path_within_allowed(Path(repository), allowed):
            return _json_text_response(
                {
                    "error": "Path outside allowed roots",
                    "code": "path_outside_allowed_roots",
                    "path": str(Path(repository).resolve()),
                    "allowed_roots": [str(r) for r in allowed],
                    "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                }
            )

    readiness = _classify_ctx(repo_resolver, repository)
    if readiness is not None and not readiness.ready:
        return _index_unavailable_response(readiness, "symbol_lookup", symbol=symbol)

    ctx = _resolve_ctx(repo_resolver, repository)

    try:
        if ctx is not None:
            result = dispatcher.lookup(ctx, symbol)
        else:
            # Fallback: call without ctx for pre-SL-1 compatibility
            result = dispatcher.lookup(symbol)  # type: ignore[call-arg]
    except TypeError:
        result = dispatcher.lookup(symbol)  # type: ignore[call-arg]

    if result:
        defined_in = (
            result.get("defined_in", "")
            if isinstance(result, dict)
            else getattr(result, "defined_in", "")
        )
        translated_path = _translate_path(defined_in)
        line = result.get("line") if isinstance(result, dict) else getattr(result, "line", None)
        response_data: dict = {
            "symbol": (
                result.get("symbol")
                if isinstance(result, dict)
                else getattr(result, "symbol", symbol)
            ),
            "kind": (
                result.get("kind") if isinstance(result, dict) else getattr(result, "kind", None)
            ),
            "language": (
                result.get("language")
                if isinstance(result, dict)
                else getattr(result, "language", None)
            ),
            "signature": (
                result.get("signature")
                if isinstance(result, dict)
                else getattr(result, "signature", None)
            ),
            "doc": result.get("doc") if isinstance(result, dict) else getattr(result, "doc", None),
            "defined_in": translated_path,
            "line": line,
            "span": (
                result.get("span") if isinstance(result, dict) else getattr(result, "span", None)
            ),
        }
        if line and translated_path:
            offset = line - 1
            response_data["_usage_hint"] = (
                f"To view definition: Read(file_path='{translated_path}', offset={offset}, limit=20)"
            )
        return [types.TextContent(type="text", text=_ensure_response(response_data))]
    else:
        response_data = {
            "result": "not_found",
            "symbol": symbol,
            "message": f"Symbol '{symbol}' not found in index",
        }
        if readiness is not None:
            response_data["readiness"] = readiness.to_dict()
        if sqlite_store is not None:
            validation_result = validate_index(sqlite_store, Path.cwd())
            if not validation_result["valid"]:
                response_data["index_issues"] = validation_result["issues"]
                response_data["suggestion"] = "Index may be stale. Run 'reindex' tool."
        return [types.TextContent(type="text", text=_ensure_response(response_data))]


async def handle_search_code(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
    indexing_thread: Any = None,
    lazy_summarizer: Any = None,
) -> Sequence[types.TextContent]:
    query = (arguments or {}).get("query")
    if not query:
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {"error": "Missing parameter", "details": "'query' parameter is required"}
                ),
            )
        ]

    semantic = (arguments or {}).get("semantic", False)
    fuzzy = (arguments or {}).get("fuzzy", False)
    limit = (arguments or {}).get("limit", 20)
    repository = (arguments or {}).get("repository")

    if repository and _looks_like_path(repository):
        allowed = _allowed_roots()
        if not _path_within_allowed(Path(repository), allowed):
            return [
                types.TextContent(
                    type="text",
                    text=_ensure_response(
                        {
                            "error": "Path outside allowed roots",
                            "code": "path_outside_allowed_roots",
                            "path": str(Path(repository).resolve()),
                            "allowed_roots": [str(r) for r in allowed],
                            "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                        }
                    ),
                )
            ]

    readiness = _classify_ctx(repo_resolver, repository)
    if readiness is not None and not readiness.ready:
        return _index_unavailable_response(readiness, "search_code", query=query)

    # Resolve ctx via RepoResolver (replaces old multi-repo bypass)
    ctx = _resolve_ctx(repo_resolver, repository)
    semantic_readiness = None
    if semantic and ctx is not None:
        semantic_readiness = ReadinessClassifier.classify_semantic_registered(
            ctx.registry_entry,
            ctx.sqlite_store,
        )
        if not semantic_readiness.ready:
            return _semantic_not_ready_response(semantic_readiness, query=query)

    try:
        if ctx is not None:
            results_iter = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: list(dispatcher.search(ctx, query, semantic=semantic, fuzzy=fuzzy, limit=limit)),  # type: ignore[call-arg]
                ),
                timeout=10.0,
            )
        else:
            # Pre-SL-1 fallback — search without ctx
            results_iter = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: list(dispatcher.search(query, semantic=semantic, fuzzy=fuzzy, limit=limit)),  # type: ignore[call-arg]
                ),
                timeout=10.0,
            )
        results = list(results_iter)
    except asyncio.TimeoutError:
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {
                        "error": "Search timeout",
                        "details": "Search operation exceeded 10 second timeout",
                        "query": query,
                        "suggestion": "Try a simpler query or check index status with get_status",
                    }
                ),
            )
        ]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        if semantic:
            return _semantic_failure_response(
                query=query,
                semantic_readiness=semantic_readiness,
                error=e,
            )
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {
                        "error": "Search failed",
                        "details": str(e),
                        "query": query,
                    }
                ),
            )
        ]

    logger.info(f"Search completed with {len(results)} results")

    _indexing_active = indexing_thread is not None and indexing_thread.is_alive()

    if results:
        results_data = []
        for r in results:
            file_path = _translate_path(
                r.get("file", "") if isinstance(r, dict) else getattr(r, "file", "")
            )
            line = r.get("line") if isinstance(r, dict) else getattr(r, "line", None)
            result_item = {
                "file": file_path,
                "line": line,
                "line_end": (
                    r.get("line_end") if isinstance(r, dict) else getattr(r, "line_end", None)
                ),
                "symbol": r.get("symbol") if isinstance(r, dict) else getattr(r, "symbol", None),
                "snippet": r.get("snippet") if isinstance(r, dict) else getattr(r, "snippet", None),
                "last_indexed": (
                    r.get("last_modified")
                    if isinstance(r, dict)
                    else getattr(r, "last_modified", None)
                ),
            }
            if semantic:
                result_item["semantic_source"] = (
                    r.get("semantic_source")
                    if isinstance(r, dict)
                    else getattr(r, "semantic_source", None)
                )
                result_item["semantic_profile_id"] = (
                    r.get("semantic_profile_id")
                    if isinstance(r, dict)
                    else getattr(r, "semantic_profile_id", None)
                )
                result_item["semantic_collection_name"] = (
                    r.get("semantic_collection_name")
                    if isinstance(r, dict)
                    else getattr(r, "semantic_collection_name", None)
                )
            if line and file_path:
                offset = line - 1
                result_item["_usage_hint"] = (
                    f"For more context: Read(file_path='{file_path}', offset={offset}, limit=30)"
                )
            results_data.append(result_item)

        # Lazy summarization enqueue
        if lazy_summarizer and lazy_summarizer.can_summarize() and sqlite_store:
            for r in results[:5]:
                raw_file = r.get("file", "") if isinstance(r, dict) else getattr(r, "file", "")
                raw_line = r.get("line", 1) if isinstance(r, dict) else getattr(r, "line", 1)
                if raw_file and raw_line:
                    chunk_info = sqlite_store.find_chunk_at_line(raw_file, int(raw_line))
                    if chunk_info:
                        lazy_summarizer.enqueue(chunk_info)

        if semantic:
            search_response = {
                "results": results_data,
                "query": query,
                "semantic_requested": True,
                "semantic_source": "semantic",
                "semantic_profile_id": (
                    semantic_readiness.profile_id if semantic_readiness is not None else None
                ),
                "semantic_collection_name": (
                    semantic_readiness.collection_name if semantic_readiness is not None else None
                ),
                "semantic_fallback_status": "not_attempted",
            }
            if _indexing_active:
                search_response["indexing_in_progress"] = True
                search_response["note"] = (
                    "Initial index is still building — results may be incomplete"
                )
        elif _indexing_active:
            search_response = {
                "results": results_data,
                "indexing_in_progress": True,
                "note": "Initial index is still building — results may be incomplete",
            }
        else:
            search_response = results_data
        return [types.TextContent(type="text", text=_ensure_response(search_response))]
    else:
        response_data: dict = {
            "results": [],
            "query": query,
            "message": (
                "No results yet — initial index is still building"
                if _indexing_active
                else "No results found in index"
            ),
        }
        if semantic:
            response_data["semantic_requested"] = True
            response_data["semantic_source"] = "semantic"
            response_data["semantic_profile_id"] = (
                semantic_readiness.profile_id if semantic_readiness is not None else None
            )
            response_data["semantic_collection_name"] = (
                semantic_readiness.collection_name if semantic_readiness is not None else None
            )
            response_data["semantic_fallback_status"] = "not_attempted"
        if readiness is not None:
            response_data["readiness"] = readiness.to_dict()
        if _indexing_active:
            response_data["indexing_in_progress"] = True
        return [types.TextContent(type="text", text=_ensure_response(response_data))]


def _build_repositories(repo_resolver: Any, dispatcher: Any = None) -> list:
    """Return a list of health rows for all registered repositories."""
    from mcp_server.health.repo_status import build_health_row

    if repo_resolver is None:
        return []
    registry = getattr(repo_resolver, "_registry", None)
    if registry is None:
        return []
    try:
        all_repos = registry.get_all_repositories()
    except Exception:
        return []
    rows = []
    for info in all_repos.values():
        features = None
        semantic_readiness = None
        if dispatcher is not None and hasattr(dispatcher, "get_runtime_feature_status"):
            try:
                ctx = repo_resolver.resolve(info.path)
                if ctx is not None:
                    features = dispatcher.get_runtime_feature_status(ctx)
                    semantic_readiness = ReadinessClassifier.classify_semantic_registered(
                        ctx.registry_entry,
                        ctx.sqlite_store,
                    )
            except Exception:
                features = None
        rows.append(
            build_health_row(
                info,
                features=features,
                semantic_readiness=semantic_readiness,
            )
        )
    return rows


async def handle_get_status(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
    file_watcher: Any = None,
    indexing_thread: Any = None,
    indexing_started_at: Optional[float] = None,
    indexing_total_files: int = 0,
    lazy_summarizer: Any = None,
    server_version: str = "unknown",
    use_simple_dispatcher: bool = False,
    current_session: Any = None,
    client_name: Optional[str] = None,
) -> Sequence[types.TextContent]:
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from mcp_server.plugins.plugin_factory import PluginFactory

    ctx = _resolve_ctx(repo_resolver, None)

    try:
        if ctx is not None and hasattr(dispatcher, "get_statistics"):
            stats = dispatcher.get_statistics(ctx)  # type: ignore[call-arg]
            health = dispatcher.health_check(ctx) if hasattr(dispatcher, "health_check") else {}  # type: ignore[call-arg]
        elif hasattr(dispatcher, "get_statistics"):
            stats = dispatcher.get_statistics()  # type: ignore[call-arg]
            health = dispatcher.health_check() if hasattr(dispatcher, "health_check") else {}  # type: ignore[call-arg]
        else:
            plugin_count = len(dispatcher.plugins()) if hasattr(dispatcher, "plugins") else 0
            stats = {
                "total_plugins": plugin_count,
                "loaded_languages": [],
                "supported_languages": plugin_count,
                "operations": {},
                "by_language": {},
            }
            health = {"status": "unknown"}
    except TypeError:
        stats = {
            "total_plugins": 0,
            "loaded_languages": [],
            "supported_languages": 0,
            "operations": {},
            "by_language": {},
        }
        health = {"status": "unknown"}

    _is_enhanced = isinstance(dispatcher, EnhancedDispatcher)
    _indexing_alive = indexing_thread is not None and indexing_thread.is_alive()
    features: dict = {
        "timeout_protection": True,
        "file_watcher": file_watcher is not None,
        "initial_index_running": _indexing_alive,
        "indexing_elapsed_seconds": (
            int(time.time() - indexing_started_at)
            if (_indexing_alive and indexing_started_at)
            else None
        ),
        "indexing_estimated_files": (
            indexing_total_files if (_indexing_alive and indexing_total_files) else None
        ),
    }
    if _is_enhanced:
        semantic_active = bool(
            getattr(dispatcher, "_semantic_registry", None)
            or getattr(dispatcher, "_semantic_indexer_fallback", None)
        )
        features.update(
            {
                "dynamic_loading": getattr(dispatcher, "_use_factory", False),
                "lazy_loading": getattr(dispatcher, "_lazy_load", False),
                "advanced_features": getattr(dispatcher, "_enable_advanced", False),
                "semantic_search_enabled": getattr(dispatcher, "_semantic_enabled", False),
                "semantic_indexer_active": semantic_active,
            }
        )

    status_data = {
        "status": health.get("status", "operational"),
        "version": server_version,
        "dispatcher_type": dispatcher.__class__.__name__,
        "dispatcher_mode": "simple" if use_simple_dispatcher else "enhanced",
        "features": features,
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
            "mcp_sampling": (
                lazy_summarizer._has_sampling_capability() if lazy_summarizer else False
            ),
            "direct_api": lazy_summarizer._has_direct_api() if lazy_summarizer else False,
            "api_provider": (
                "anthropic"
                if os.environ.get("ANTHROPIC_API_KEY")
                else "openai" if os.environ.get("OPENAI_API_KEY") else None
            ),
            "client": client_name,
            "session_available": current_session is not None,
        },
        "repositories": _build_repositories(repo_resolver, dispatcher),
    }
    availability_rows = PluginFactory.get_plugin_availability()
    counts: dict[str, int] = {}
    for row in availability_rows:
        state = row.get("state", "load_error")
        counts[state] = counts.get(state, 0) + 1
    status_data["plugins"]["availability_counts"] = counts
    return [types.TextContent(type="text", text=_ensure_response(status_data))]


async def handle_list_plugins(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    plugin_manager: Any = None,
) -> Sequence[types.TextContent]:
    from mcp_server.plugins.plugin_factory import PluginFactory

    availability_rows = PluginFactory.get_plugin_availability()
    counts: dict[str, int] = {}
    for row in availability_rows:
        state = row.get("state", "load_error")
        counts[state] = counts.get(state, 0) + 1

    response_data: dict = {
        "plugin_manager_plugins": [],
        "supported_languages": [],
        "loaded_plugins": [],
        "plugin_availability": availability_rows,
        "availability_counts": counts,
    }

    if plugin_manager is not None:
        plugin_infos = plugin_manager._registry.list_plugins()
        plugin_status = plugin_manager.get_plugin_status()
        for info in plugin_infos:
            status = plugin_status.get(info.name, {})
            response_data["plugin_manager_plugins"].append(
                {
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                    "language": info.language,
                    "file_extensions": info.file_extensions,
                    "state": status.get("state", "unknown"),
                    "enabled": status.get("enabled", False),
                }
            )

    if hasattr(dispatcher, "supported_languages"):
        try:
            response_data["supported_languages"] = dispatcher.supported_languages()  # type: ignore[call-arg]
        except TypeError:
            response_data["supported_languages"] = dispatcher.supported_languages  # type: ignore[assignment]

    if hasattr(dispatcher, "_by_lang"):
        for lang, plugin in dispatcher._by_lang.items():  # type: ignore[attr-defined]
            loaded = {
                "language": lang,
                "class": plugin.__class__.__name__,
                "is_generic": "GenericTreeSitterPlugin" in plugin.__class__.__name__,
                "semantic_enabled": getattr(plugin, "_enable_semantic", False),
            }
            if hasattr(plugin, "get_indexed_count"):
                loaded["indexed_files"] = plugin.get_indexed_count()
            response_data["loaded_plugins"].append(loaded)

    return [types.TextContent(type="text", text=_ensure_response(response_data))]


async def handle_reindex(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
    request_experimental: Any = None,
    task_registry: Any = None,
) -> Sequence[types.TextContent] | types.CreateTaskResult:
    path = (arguments or {}).get("path")
    repository = (arguments or {}).get("repository")

    # Sandbox check for repository when it looks like a path
    if repository and _looks_like_path(repository):
        allowed = _allowed_roots()
        if not _path_within_allowed(Path(repository), allowed):
            return [
                types.TextContent(
                    type="text",
                    text=_ensure_response(
                        {
                            "error": "Path outside allowed roots",
                            "code": "path_outside_allowed_roots",
                            "path": str(Path(repository).resolve()),
                            "allowed_roots": [str(r) for r in allowed],
                            "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                        }
                    ),
                )
            ]

    # Conflict detection: both path and repository provided but resolve to different repos
    if path and repository:
        ctx_from_path = _resolve_ctx(repo_resolver, str(path))
        ctx_from_repo = _resolve_ctx(repo_resolver, repository)
        if (
            ctx_from_path is not None
            and ctx_from_repo is not None
            and ctx_from_path.repo_id != ctx_from_repo.repo_id
        ):
            return _json_text_response(
                {
                    "error": "Conflicting scope",
                    "code": "conflicting_path_and_repository",
                    "path": str(path),
                    "repository": repository,
                    "hint": "Provide only one, or ensure both resolve to the same repo.",
                }
            )

    scope_arg = repository or (str(path) if path else None)
    readiness = _classify_ctx(repo_resolver, scope_arg)
    if readiness is not None and not readiness.ready:
        return _secondary_readiness_refusal_response(readiness, "reindex")

    # Resolve ctx — repository takes precedence when both are set and consistent
    ctx = _resolve_ctx(repo_resolver, scope_arg)
    active_store = ctx.sqlite_store if ctx is not None else sqlite_store

    allowed = _allowed_roots()
    # Determine target_path: prefer ctx.workspace_root when ctx resolved, else path
    if path:
        target_path = Path(path).expanduser()
    elif ctx is not None:
        target_path = ctx.workspace_root
    else:
        target_path = allowed[0]

    if not target_path.exists():
        return _json_text_response({"error": "Path not found", "path": str(target_path)})

    if not _path_within_allowed(target_path, allowed):
        return _json_text_response(
            {
                "error": "Path outside allowed roots",
                "code": "path_outside_allowed_roots",
                "path": str(target_path.resolve()),
                "allowed_roots": [str(r) for r in allowed],
                "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
            }
        )

    if path and target_path.is_file():
        if request_experimental is not None and request_experimental.is_task:
            return await request_experimental.run_task(
                lambda task: run_reindex_task(
                    task=task,
                    registry=task_registry,
                    dispatcher=dispatcher,
                    ctx=ctx,
                    active_store=active_store,
                    target_path=target_path,
                    requested_path=path,
                ),
                model_immediate_response="Reindex task created; poll tasks/get or tasks/result for progress.",
            )
        try:
            if ctx is not None:
                dispatcher.index_file(ctx, target_path)  # type: ignore[call-arg]
            else:
                dispatcher.index_file(target_path)  # type: ignore[call-arg]
            durable_files = (
                _record_reindexed_files(active_store, ctx.workspace_root, target_path)
                if ctx is not None and active_store is not None
                else 0
            )
            return _json_text_response(
                {
                    "path": str(target_path),
                    "mode": "file",
                    "indexed_files": 1,
                    "durable_files": durable_files,
                    "mutation_performed": True,
                    "message": f"Reindexed file: {path}",
                }
            )
        except TypeError:
            dispatcher.index_file(target_path)  # type: ignore[call-arg]
            durable_files = (
                _record_reindexed_files(active_store, ctx.workspace_root, target_path)
                if ctx is not None and active_store is not None
                else 0
            )
            return _json_text_response(
                {
                    "path": str(target_path),
                    "mode": "file",
                    "indexed_files": 1,
                    "durable_files": durable_files,
                    "mutation_performed": True,
                    "message": f"Reindexed file: {path}",
                }
            )
        except Exception as e:
            return _json_text_response(
                {
                    "error": "Reindex failed",
                    "code": "reindex_failed",
                    "path": str(target_path),
                    "message": f"Error reindexing {path}",
                    "details": str(e),
                    "mutation_performed": False,
                }
            )
    else:
        if request_experimental is not None and request_experimental.is_task:
            return await request_experimental.run_task(
                lambda task: run_reindex_task(
                    task=task,
                    registry=task_registry,
                    dispatcher=dispatcher,
                    ctx=ctx,
                    active_store=active_store,
                    target_path=target_path,
                    requested_path=path,
                ),
                model_immediate_response="Reindex task created; poll tasks/get or tasks/result for progress.",
            )
        try:
            if ctx is not None:
                stats = dispatcher.index_directory(ctx, target_path, recursive=True)  # type: ignore[call-arg]
            else:
                stats = dispatcher.index_directory(target_path, recursive=True)  # type: ignore[call-arg]
        except TypeError:
            stats = dispatcher.index_directory(target_path, recursive=True)  # type: ignore[call-arg]

        durable_files = (
            _record_reindexed_files(active_store, ctx.workspace_root, target_path)
            if ctx is not None and active_store is not None
            else 0
        )
        lexical_rows = active_store.rebuild_fts_code() if active_store else 0

        response_data = {
            "path": str(target_path),
            "mode": "merge",
            "mutation_performed": True,
            "indexed_files": stats.get("indexed_files"),
            "ignored_files": stats.get("ignored_files"),
            "failed_files": stats.get("failed_files"),
            "total_files": stats.get("total_files"),
            "by_language": stats.get("by_language"),
            "lexical_rows": lexical_rows,
            "durable_files": durable_files,
            "semantic_indexed": stats.get("semantic_indexed"),
            "semantic_failed": stats.get("semantic_failed"),
            "semantic_skipped": stats.get("semantic_skipped"),
            "semantic_blocked": stats.get("semantic_blocked"),
            "semantic_stage": stats.get("semantic_stage"),
            "summaries_written": stats.get("summaries_written"),
            "summary_chunks_attempted": stats.get("summary_chunks_attempted"),
            "summary_missing_chunks": stats.get("summary_missing_chunks"),
            "total_embedding_units": stats.get("total_embedding_units"),
            "semantic_error": stats.get("semantic_error"),
            "semantic_blocker": stats.get("semantic_blocker"),
            "semantic_paths_queued": stats.get("semantic_paths_queued"),
            "semantic_indexer_present": stats.get("semantic_indexer_present"),
            "merge_note": (
                "Changed/new files updated; deleted files are not purged — "
                "FileWatcher handles those on next change, or reindex again after deletions."
            ),
        }
        return _json_text_response(response_data)


async def handle_write_summaries(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
    lazy_summarizer: Any = None,
    current_session: Any = None,
    client_name: Optional[str] = None,
    request_experimental: Any = None,
    task_registry: Any = None,
) -> Sequence[types.TextContent] | types.CreateTaskResult:
    from mcp_server.config.settings import Settings
    from mcp_server.indexing.summarization import ComprehensiveChunkWriter

    repository = (arguments or {}).get("repository")

    if repository and _looks_like_path(repository):
        allowed = _allowed_roots()
        if not _path_within_allowed(Path(repository), allowed):
            return [
                types.TextContent(
                    type="text",
                    text=_ensure_response(
                        {
                            "error": "Path outside allowed roots",
                            "code": "path_outside_allowed_roots",
                            "path": str(Path(repository).resolve()),
                            "allowed_roots": [str(r) for r in allowed],
                            "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                        }
                    ),
                )
            ]

    readiness = _classify_ctx(repo_resolver, repository)
    if readiness is not None and not readiness.ready:
        return _secondary_readiness_refusal_response(readiness, "write_summaries")

    ctx = _resolve_ctx(repo_resolver, repository)
    active_store = ctx.sqlite_store if ctx is not None else sqlite_store

    if lazy_summarizer is None or not lazy_summarizer.can_summarize():
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {
                        "error": "Summarization not available",
                        "details": "No API key configured. Set CEREBRAS_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY.",
                    }
                ),
            )
        ]

    if active_store is None:
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {
                        "error": "sqlite_store not initialized",
                    }
                ),
            )
        ]

    db_path = active_store.db_path
    limit_arg = int((arguments or {}).get("limit", 500))
    model_used = lazy_summarizer._get_model_name()

    if request_experimental is not None and request_experimental.is_task:
        return await request_experimental.run_task(
            lambda task: run_write_summaries_task(
                task=task,
                registry=task_registry,
                active_store=active_store,
                current_session=current_session,
                client_name=client_name,
                limit_arg=limit_arg,
                model_used=model_used,
            ),
            model_immediate_response=(
                "Summary task created; use tasks/get and tasks/result to observe bounded progress."
            ),
        )

    _settings = Settings.from_environment()
    writer = ComprehensiveChunkWriter(
        db_path=db_path,
        qdrant_client=None,
        session=current_session,
        client_name=client_name,
        summarization_config={
            **_settings.get_profile_summarization_config(_settings.semantic_default_profile),
            "profile_id": _settings.semantic_default_profile,
        },
    )
    summary_result = await writer.process_scope(limit=limit_arg)

    return [
        types.TextContent(
            type="text",
            text=_ensure_response(
                {
                    "chunks_summarized": summary_result.summaries_written,
                    "limit": limit_arg,
                    "model_used": model_used,
                    "persisted": True,
                    "semantic_vectors_written": False,
                    "summary_chunks_attempted": summary_result.chunks_attempted,
                    "summary_missing_chunks": len(summary_result.missing_chunk_ids),
                }
            ),
        )
    ]


async def handle_summarize_sample(
    *,
    arguments: dict,
    dispatcher: DispatcherProtocol,
    repo_resolver: RepoResolver,
    sqlite_store: Any = None,
    lazy_summarizer: Any = None,
    current_session: Any = None,
    client_name: Optional[str] = None,
) -> Sequence[types.TextContent]:
    import sqlite3 as _sqlite3

    from mcp_server.indexing.summarization import FileBatchSummarizer

    repository = (arguments or {}).get("repository")

    if repository and _looks_like_path(repository):
        allowed = _allowed_roots()
        if not _path_within_allowed(Path(repository), allowed):
            return [
                types.TextContent(
                    type="text",
                    text=_ensure_response(
                        {
                            "error": "Path outside allowed roots",
                            "code": "path_outside_allowed_roots",
                            "path": str(Path(repository).resolve()),
                            "allowed_roots": [str(r) for r in allowed],
                            "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                        }
                    ),
                )
            ]

    paths_arg = (arguments or {}).get("paths")
    n_arg = int((arguments or {}).get("n", 3))
    persist_flag = bool((arguments or {}).get("persist", False))

    repository_readiness = (
        _classify_ctx(repo_resolver, repository) if repository or not paths_arg else None
    )

    if paths_arg:
        allowed = _allowed_roots()
        path_readiness_by_repo: dict[str, RepositoryReadiness] = {}
        for p in paths_arg:
            if _looks_like_path(p) and not _path_within_allowed(Path(p), allowed):
                return [
                    types.TextContent(
                        type="text",
                        text=_ensure_response(
                            {
                                "error": "Path outside allowed roots",
                                "code": "path_outside_allowed_roots",
                                "path": str(Path(p).resolve()),
                                "allowed_roots": [str(r) for r in allowed],
                                "hint": "Set MCP_ALLOWED_ROOTS using the OS path separator to expand the allowlist.",
                            }
                        ),
                    )
                ]
            path_readiness = _classify_ctx(repo_resolver, str(p))
            if path_readiness is not None:
                if (
                    repository_readiness is not None
                    and repository_readiness.repository_id != path_readiness.repository_id
                ):
                    return [
                        types.TextContent(
                            type="text",
                            text=_ensure_response(
                                {
                                    "error": "Conflicting scope",
                                    "code": "conflicting_path_and_repository",
                                    "path": str(p),
                                    "repository": repository,
                                    "hint": "Provide only one, or ensure both resolve to the same repo.",
                                }
                            ),
                        )
                    ]
                if not path_readiness.ready:
                    return _secondary_readiness_refusal_response(path_readiness, "summarize_sample")
                repo_key = path_readiness.repository_id or ""
                path_readiness_by_repo[repo_key] = path_readiness

        if len(path_readiness_by_repo) > 1:
            return [
                types.TextContent(
                    type="text",
                    text=_ensure_response(
                        {
                            "error": "Conflicting scope",
                            "code": "conflicting_path_and_repository",
                            "paths": list(paths_arg),
                            "hint": "All explicit paths must resolve to one ready repository.",
                        }
                    ),
                )
            ]

    if repository_readiness is not None and not repository_readiness.ready:
        return _secondary_readiness_refusal_response(repository_readiness, "summarize_sample")

    scope_arg = repository
    if not scope_arg and paths_arg:
        scope_arg = str(paths_arg[0])

    ctx = _resolve_ctx(repo_resolver, scope_arg)
    active_store = ctx.sqlite_store if ctx is not None else sqlite_store

    if lazy_summarizer is None or not lazy_summarizer.can_summarize():
        return [
            types.TextContent(
                type="text",
                text=_ensure_response(
                    {
                        "error": "Summarization not available",
                        "details": "No API key configured. Set CEREBRAS_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY.",
                    }
                ),
            )
        ]

    if active_store is None:
        return [
            types.TextContent(
                type="text", text=_ensure_response({"error": "sqlite_store not initialized"})
            )
        ]

    db_path = active_store.db_path
    model_used = lazy_summarizer._get_model_name()

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
        try:
            with open(file_path, encoding="utf-8", errors="replace") as _fh:
                file_content = _fh.read()
        except Exception as _e:
            file_results.append({"file_path": file_path, "error": str(_e)})
            continue

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
        symbol_map = {r[7]: r[8] for r in chunk_rows if r[7] and r[8]}

        summarizer = FileBatchSummarizer(
            db_path=db_path,
            qdrant_client=None,
            session=current_session,
            client_name=client_name,
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
            file_results.append({"file_path": file_path, "error": str(_e)})
            continue

        chunk_meta = {c["chunk_id"]: c for c in chunks}
        summary_list = []
        for s in summaries:
            meta = chunk_meta.get(s.chunk_id, {})
            sym_name = symbol_map.get(meta.get("symbol_id")) or meta.get("node_type") or s.chunk_id
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
                "summaries": summary_list,
            }
        )

    return [
        types.TextContent(
            type="text",
            text=_ensure_response(
                {
                    "files_processed": len(file_results),
                    "total_chunks": total_chunks,
                    "model_used": model_used,
                    "persisted": persist_flag,
                    "files": file_results,
                }
            ),
        )
    ]
