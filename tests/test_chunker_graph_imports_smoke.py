"""Grep-derived smoke tests for the ``chunker`` (treesitter-chunker) surface.

Two disjoint CHUNKERSAFE Lane A checks live here:

1. ``test_all_chunker_imports_resolve`` — at *runtime* greps ``mcp_server/`` for
   every ``chunker`` import site (``from chunker... import ...`` / ``import
   chunker...``), derives the (module, symbol) pairs from what it finds (nothing
   is hand-enumerated), and asserts each one imports/resolves under the installed
   ``treesitter-chunker``. This catches a v4 interface-consolidation move that
   relocates a symbol/module out from under an import, which would otherwise
   degrade silently. Failure is hard (ImportError / resolves-to-None -> assert),
   never a soft skip.

2. ``test_part_like_query_escapes_metacharacters`` — proves the ``:part:`` LIKE
   query in ``IncrementalIndexer._get_chunk_ids_for_path`` matches only a
   chunk_id's own ``:part:`` rows even when the id contains SQL LIKE
   metacharacters (``%`` / ``_``), which v4's collision-free ids may contain.
"""

from __future__ import annotations

import importlib
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER_DIR = REPO_ROOT / "mcp_server"

# ``from <module> import <names>`` where module is chunker or a chunker submodule.
_FROM_RE = re.compile(
    r"^\s*from\s+(chunker(?:\.[A-Za-z0-9_.]+)?)\s+import\s+(.+?)\s*$"
)
# ``import <module>`` (optionally ``as alias``) where module is chunker/submodule.
_IMPORT_RE = re.compile(
    r"^\s*import\s+(chunker(?:\.[A-Za-z0-9_.]+)?)(?:\s+as\s+[A-Za-z0-9_]+)?\s*$"
)


def _grep_chunker_import_lines() -> List[str]:
    """Grep mcp_server/ for every chunker import line.

    Uses ``grep`` at runtime (per spec) rather than a static/hand-maintained
    list. Returns the raw matching source lines.
    """
    result = subprocess.run(
        [
            "grep",
            "-rhE",
            r"(from[[:space:]]+chunker([.][A-Za-z0-9_.]+)?[[:space:]]+import|^[[:space:]]*import[[:space:]]+chunker)",
            str(MCP_SERVER_DIR),
        ],
        capture_output=True,
        text=True,
    )
    # grep exit code 1 == "no matches"; that is itself a failure for this repo.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"grep failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _parse_import_targets(lines: List[str]) -> List[Tuple[str, str]]:
    """Derive (module, symbol) pairs from grepped import lines.

    ``symbol`` is ``""`` for a bare ``import chunker.x`` (module-only resolution).
    ``import X as Y`` binds are reduced to their real (pre-``as``) name.
    """
    pairs: set[Tuple[str, str]] = set()
    for line in lines:
        m = _FROM_RE.match(line)
        if m:
            module = m.group(1)
            names = m.group(2)
            # Strip a trailing inline comment, if any.
            names = names.split("#", 1)[0]
            # Defensive: drop wrapping parens for single-line grouped imports.
            names = names.strip().strip("()")
            for raw in names.split(","):
                raw = raw.strip()
                if not raw or raw == "*":
                    continue
                # ``name as alias`` -> real name is the pre-``as`` token.
                symbol = re.split(r"\s+as\s+", raw)[0].strip()
                if symbol:
                    pairs.add((module, symbol))
            continue
        m = _IMPORT_RE.match(line)
        if m:
            pairs.add((m.group(1), ""))
    return sorted(pairs)


def test_grep_finds_chunker_imports():
    """Sanity: the runtime grep must actually find import sites.

    Guards against a silently-empty grep (wrong path / broken pattern) that would
    make the resolution test vacuously pass.
    """
    lines = _grep_chunker_import_lines()
    pairs = _parse_import_targets(lines)
    # Not hand-enumerated, but a broken grep would yield 0; the repo has many.
    assert len(pairs) >= 6, f"grep derived too few chunker imports: {pairs}"


def test_all_chunker_imports_resolve():
    """Every grepped chunker import must resolve under installed treesitter-chunker.

    Hard failure (assert) on ImportError or a resolves-to-None symbol; no soft
    "unavailable" path.
    """
    pairs = _parse_import_targets(_grep_chunker_import_lines())
    assert pairs, "no chunker imports discovered by grep"

    failures: List[str] = []
    for module_name, symbol in pairs:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # ImportError and anything raised at import
            failures.append(f"import {module_name!r} failed: {exc!r}")
            continue
        if not symbol:
            continue
        if not hasattr(module, symbol):
            failures.append(f"{module_name}.{symbol} is missing")
            continue
        if getattr(module, symbol) is None:
            failures.append(f"{module_name}.{symbol} resolved to None")

    assert not failures, (
        "chunker import surface degraded (v4 interface move?):\n  "
        + "\n  ".join(failures)
    )


# --------------------------------------------------------------------------- #
# CHUNKERSAFE Lane A item 2: :part: LIKE metacharacter escaping.
# --------------------------------------------------------------------------- #


@pytest.fixture
def like_indexer(tmp_path: Path):
    from mcp_server.core.path_resolver import PathResolver
    from mcp_server.core.repo_context import RepoContext
    from mcp_server.indexing.incremental_indexer import IncrementalIndexer
    from mcp_server.storage.sqlite_store import SQLiteStore

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    store = SQLiteStore(
        str(tmp_path / "code_index.db"), path_resolver=PathResolver(repo_path)
    )
    repo_id = store.create_repository(str(repo_path), "test-repo")
    ctx = RepoContext(
        repo_id=repo_id,
        sqlite_store=store,
        workspace_root=repo_path,
        tracked_branch="main",
        registry_entry=SimpleNamespace(repository_id=repo_id, path=repo_path),
    )
    indexer = IncrementalIndexer(
        store=store,
        dispatcher=None,
        repo_path=repo_path,
        semantic_indexer=None,
        ctx=ctx,
    )
    indexer._get_repository_id = lambda: repo_id  # type: ignore[method-assign]
    return repo_path, store, indexer, repo_id


def test_part_like_query_escapes_metacharacters(like_indexer):
    """A chunk_id containing % / _ matches only its own :part: rows.

    Under an unescaped ``chunk_id LIKE '<id>:part:%'`` query, a ``%`` in the id
    matches any run of characters and ``_`` matches any single character, so a
    chunk id like ``a%b`` would wrongly harvest an unrelated file's
    ``aXYZb:part:1`` semantic point. With ESCAPE-clause metacharacter escaping,
    only literal matches survive.
    """
    repo_path, store, indexer, repo_id = like_indexer

    # Target file whose chunk ids contain LIKE metacharacters.
    target_file = repo_path / "target.py"
    target_file.write_text("x = 1\n")
    target_id = store.store_file(repo_id, target_file, language="python")
    store.store_chunk(
        file_id=target_id,
        content="x = 1",
        content_start=0,
        content_end=5,
        line_start=1,
        line_end=1,
        chunk_id="a%b",  # contains the '%' multi-char wildcard
        node_id="node-a",
        treesitter_file_id="ts-a",
    )
    store.store_chunk(
        file_id=target_id,
        content="x = 1",
        content_start=0,
        content_end=5,
        line_start=1,
        line_end=1,
        chunk_id="c_d",  # contains the '_' single-char wildcard
        node_id="node-c",
        treesitter_file_id="ts-c",
    )

    # A DIFFERENT file whose semantic points would be caught by the unescaped
    # wildcards ('a' + any + 'b', 'c' + one char + 'd') but must NOT be returned.
    other_file = repo_path / "other.py"
    other_file.write_text("y = 2\n")
    other_id = store.store_file(repo_id, other_file, language="python")
    store.store_chunk(
        file_id=other_id,
        content="y = 2",
        content_start=0,
        content_end=5,
        line_start=1,
        line_end=1,
        chunk_id="aZZb",
        node_id="node-z",
        treesitter_file_id="ts-z",
    )

    # Own :part: rows for the target chunks (should be returned).
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="a%b:part:1:2",
        point_id=7001,
        collection="code-index",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="c_d:part:1:2",
        point_id=7002,
        collection="code-index",
    )
    # Foreign :part: rows that ONLY an unescaped LIKE would mis-match.
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="aZZb:part:1:2",  # matched by unescaped 'a%b:part:%'
        point_id=7003,
        collection="code-index",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="cXd:part:1:2",  # matched by unescaped 'c_d:part:%'
        point_id=7004,
        collection="code-index",
    )

    resolved = indexer._get_chunk_ids_for_path("target.py")

    # Base chunk ids for the target file are always present.
    assert "a%b" in resolved
    assert "c_d" in resolved
    # Its own :part: rows are harvested.
    assert "a%b:part:1:2" in resolved
    assert "c_d:part:1:2" in resolved
    # The foreign rows must NOT leak in (this is the escape bug this test guards).
    assert "aZZb:part:1:2" not in resolved
    assert "cXd:part:1:2" not in resolved
