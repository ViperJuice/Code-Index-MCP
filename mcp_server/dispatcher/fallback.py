"""Gated, bounded, observed fallback helper for plugin symbol lookup."""

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any, Iterable, Optional

from mcp_server.core.errors import record_handled_error
from mcp_server.plugin_base import IPlugin, SymbolDef
from mcp_server.plugin_system.plugin_registry import PluginRegistry


def _observe(histogram: Optional[Any], outcome: str, duration: float) -> None:
    if histogram is not None:
        histogram.labels(outcome=outcome).observe(duration)


def run_gated_fallback(
    plugins: Iterable[IPlugin],
    symbol: str,
    *,
    source_ext: Optional[str],
    timeout_ms: int,
    histogram: Optional[Any] = None,
    registry: Optional[PluginRegistry] = None,
) -> Optional[SymbolDef]:
    """Run extension-gated, timeout-bounded fallback over the given plugins.

    Returns None immediately if source_ext is None (no extension hint).
    Filters plugins to those whose class name appears in registry.get_plugins_by_extension(source_ext).
    Each surviving plugin's getDefinition is submitted to a per-call ThreadPoolExecutor.
    Observes histogram outcomes: hit, miss, timeout, error.
    """
    if source_ext is None:
        return None

    timeout_s = timeout_ms / 1000.0

    if registry is not None:
        allowed_names = set(registry.get_plugins_by_extension(source_ext))
    else:
        allowed_names = None

    for plugin in plugins:
        if allowed_names is not None and type(plugin).__name__ not in allowed_names:
            continue

        t_start = time.monotonic()
        ex = ThreadPoolExecutor(max_workers=1)
        try:
            future = ex.submit(plugin.getDefinition, symbol)
            try:
                result = future.result(timeout=timeout_s)
            except FuturesTimeout:
                duration = time.monotonic() - t_start
                _observe(histogram, "timeout", duration)
                continue
            except Exception as exc:
                record_handled_error(__name__, exc)
                duration = time.monotonic() - t_start
                _observe(histogram, "error", duration)
                continue
            finally:
                ex.shutdown(wait=False)
        except Exception as exc:
            record_handled_error(__name__, exc)
            ex.shutdown(wait=False)
            duration = time.monotonic() - t_start
            _observe(histogram, "error", duration)
            continue

        duration = time.monotonic() - t_start
        if result:
            _observe(histogram, "hit", duration)
            return result
        else:
            _observe(histogram, "miss", duration)

    return None
