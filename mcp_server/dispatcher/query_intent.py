"""Query intent classification for routing search queries to the right backend."""

from __future__ import annotations

import re
from enum import IntEnum
from typing import Optional, Tuple


class QueryIntent(IntEnum):
    SYMBOL = 1  # Class/function/identifier lookup → route to symbols table
    LEXICAL = 2  # Keyword / multi-word text → BM25


# (regex, kind_hint) — matched in order; first match wins
_KIND_PREFIX_PATTERNS: list[tuple[str, str | None]] = [
    (r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", "class"),
    (r"^def\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
    (r"^function\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
    (r"^func\s+([A-Za-z_][A-Za-z0-9_]*)", "function"),
    (r"^interface\s+([A-Za-z_][A-Za-z0-9_]*)", "interface"),
    (r"^struct\s+([A-Za-z_][A-Za-z0-9_]*)", "struct"),
    (r"^type\s+([A-Za-z_][A-Za-z0-9_]*)", "type"),
    (r"^enum\s+([A-Za-z_][A-Za-z0-9_]*)", "enum"),
    (r"^(?:const|var|let)\s+([A-Za-z_][A-Za-z0-9_]*)", None),
]


def classify(query: str) -> Tuple[QueryIntent, str, Optional[str]]:
    """Classify a query and return (intent, symbol_name, kind_hint).

    Returns:
        intent      — SYMBOL if the query looks like a symbol lookup, else LEXICAL
        symbol_name — cleaned symbol name to look up (stripped of keyword prefix)
        kind_hint   — 'class', 'function', etc. when inferrable, else None
    """
    q = query.strip()
    if not q:
        return QueryIntent.LEXICAL, q, None

    # Multi-word queries with no leading keyword are always LEXICAL
    # ("semantic preflight", "qdrant docker compose autostart", etc.)
    tokens = q.split()

    # --- Explicit keyword-prefixed patterns ---
    for pattern, kind in _KIND_PREFIX_PATTERNS:
        m = re.match(pattern, q, re.IGNORECASE)
        if m:
            return QueryIntent.SYMBOL, m.group(1), kind

    # --- Single-token patterns ---
    if len(tokens) == 1:
        # CamelCase (two or more words joined): MyClass, EnhancedDispatcher
        if re.match(r"^[A-Z][a-zA-Z0-9]+$", q) and re.search(r"[A-Z]", q[1:]):
            return QueryIntent.SYMBOL, q, "class"

        # ALL_CAPS constant: MAX_RETRIES
        if re.match(r"^[A-Z][A-Z0-9_]{2,}$", q):
            return QueryIntent.SYMBOL, q, None

        # snake_case identifier with at least one underscore and len > 3
        if re.match(r"^[a-z_][a-z0-9_]*$", q) and "_" in q and len(q) > 3:
            return QueryIntent.SYMBOL, q, "function"

    # --- Dotted name: Module.method or Class.attr ---
    if len(tokens) == 1 and re.match(r"^[A-Za-z_]\w*\.[A-Za-z_]\w*$", q):
        name = q.split(".")[-1]
        return QueryIntent.SYMBOL, name, None

    return QueryIntent.LEXICAL, q, None
