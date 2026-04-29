from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

import jedi

try:
    from chunker import chunk_text as chunk_text

    _CHUNKER_AVAILABLE = True
except Exception:
    chunk_text = None  # type: ignore[assignment]
    _CHUNKER_AVAILABLE = False

from ...plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ...storage.sqlite_store import SQLiteStore
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...utils.treesitter_wrapper import TreeSitterWrapper


class Plugin(IPlugin):
    lang = "python"
    _BOUNDED_CHUNK_PATHS = {
        "scripts/create_multi_repo_visual_report.py",
        "scripts/quick_mcp_vs_native_validation.py",
        "scripts/verify_embeddings.py",
        "scripts/claude_code_behavior_simulator.py",
        "scripts/create_semantic_embeddings.py",
        "scripts/consolidate_real_performance_data.py",
        "tests/test_artifact_publish_race.py",
        "tests/docs/test_gaclose_evidence_closeout.py",
        "tests/docs/test_p8_deployment_security.py",
        "tests/docs/test_semincr_contract.py",
        "tests/docs/test_gabase_ga_readiness_contract.py",
        "tests/docs/test_garc_rc_soak_contract.py",
        "tests/docs/test_garel_ga_release_contract.py",
        "tests/security/fixtures/mock_plugin/plugin.py",
        "tests/security/fixtures/mock_plugin/__init__.py",
        "mcp_server/visualization/quick_charts.py",
    }

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None, preindex: bool = True) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "python"}
            )

        if preindex and os.getenv("MCP_SKIP_PLUGIN_PREINDEX", "false").lower() != "true":
            self._preindex()

    # ------------------------------------------------------------------
    _EXCLUDED_DIRS = {
        "htmlcov",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
    }

    def _preindex(self) -> None:
        for path in Path(".").rglob("*.py"):
            if any(part in self._EXCLUDED_DIRS for part in path.parts):
                continue
            try:
                text = path.read_text()
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    # ------------------------------------------------------------------
    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        return Path(path).suffix == ".py"

    def _normalized_relative_path(self, path: Path) -> str:
        if self._sqlite_store is not None:
            try:
                return self._sqlite_store.path_resolver.normalize_path(path)
            except Exception:
                pass
        if path.is_absolute():
            try:
                return path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                return path.as_posix()
        return path.as_posix()

    def _uses_bounded_chunk_path(self, path: Path) -> bool:
        return self._normalized_relative_path(path) in self._BOUNDED_CHUNK_PATHS

    # ------------------------------------------------------------------
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        if isinstance(path, str):
            path = Path(path)
        self._indexer.add_file(str(path), content)
        tree = self._ts._parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            rel_path = self._normalized_relative_path(path)
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                rel_path,
                language="python",
                size=len(content),
                hash=file_hash,
            )

        symbols: list[dict] = []
        for child in root.named_children:
            if child.type not in {"function_definition", "class_definition"}:
                continue

            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            name = name_node.text.decode("utf-8")

            start_line = child.start_point[0] + 1
            end_line = child.end_point[0] + 1

            if child.type == "function_definition":
                kind = "function"
                signature = f"def {name}(...):"
            else:
                kind = "class"
                signature = f"class {name}:"

            # Store symbol in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, name, kind, start_line, end_line, signature=signature
                )
                # Add to fuzzy indexer with metadata
                self._indexer.add_symbol(
                    name,
                    str(path),
                    start_line,
                    {"symbol_id": symbol_id, "file_id": file_id},
                )

            symbols.append(
                {
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": start_line,
                    "span": (start_line, end_line),
                }
            )

            # Index class methods
            if child.type == "class_definition":
                body = child.child_by_field_name("body")
                if body:
                    for method_node in body.named_children:
                        if method_node.type != "function_definition":
                            continue
                        method_name_node = method_node.child_by_field_name("name")
                        if method_name_node is None:
                            continue
                        method_name = method_name_node.text.decode("utf-8")
                        method_start = method_node.start_point[0] + 1
                        method_end = method_node.end_point[0] + 1
                        method_sig = f"def {method_name}(...):"
                        if self._sqlite_store and file_id:
                            method_id = self._sqlite_store.store_symbol(
                                file_id,
                                method_name,
                                "method",
                                method_start,
                                method_end,
                                signature=method_sig,
                                metadata={"parent_class": name},
                            )
                            self._indexer.add_symbol(
                                method_name,
                                str(path),
                                method_start,
                                {"symbol_id": method_id, "file_id": file_id, "parent_class": name},
                            )
                        symbols.append(
                            {
                                "symbol": method_name,
                                "kind": "method",
                                "signature": method_sig,
                                "line": method_start,
                                "span": (method_start, method_end),
                            }
                        )

        # Store chunks in SQLite (delete old ones first since chunk_id uses temp path)
        if self._sqlite_store and file_id:
            _chunks = []
            self._sqlite_store.delete_chunks_for_file(file_id)
            if not self._uses_bounded_chunk_path(path):
                try:
                    _chunks = chunk_text(content, "python")
                except Exception:
                    pass
            for i, chunk in enumerate(_chunks):
                try:
                    self._sqlite_store.store_chunk(
                        file_id=file_id,
                        content=chunk.content,
                        content_start=chunk.byte_start,
                        content_end=chunk.byte_end,
                        line_start=chunk.start_line,
                        line_end=chunk.end_line,
                        chunk_id=chunk.chunk_id,
                        node_id=chunk.node_id,
                        treesitter_file_id=str(chunk.file_id),
                        definition_id=chunk.definition_id,
                        parent_chunk_id=chunk.parent_chunk_id,
                        node_type=chunk.node_type,
                        language="python",
                        chunk_index=i,
                        metadata=chunk.metadata,
                    )
                except Exception:
                    pass

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    # ------------------------------------------------------------------
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        # First try SQLite if available
        if self._sqlite_store:
            results = self._sqlite_store.search_symbols_fuzzy(symbol, limit=1)
            if results and results[0]["name"] == symbol:
                result = results[0]
                line = result.get("line_start") or result.get("line", 0)
                end_line = result.get("line_end") or result.get("end_line", line)
                return {
                    "symbol": result["name"],
                    "kind": result["kind"],
                    "language": self.lang,
                    "signature": result.get("signature", ""),
                    "doc": None,
                    "defined_in": result["file_path"],
                    "line": line,
                    "span": (line, end_line),
                }
            # SQLite is authoritative when available — no filesystem fallback
            return None

        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                names = script.get_names(all_scopes=True, definitions=True, references=False)
                for name in names:
                    if name.name == symbol and name.type in ("function", "class"):
                        defs = name.goto()
                        if defs:
                            d = defs[0]
                            return {
                                "symbol": d.name,
                                "kind": d.type,
                                "language": self.lang,
                                "signature": d.get_line_code().strip(),
                                "doc": d.docstring(raw=True),
                                "defined_in": str(path),
                                "line": d.line,
                                "span": (d.line, d.line + 3),
                            }
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    def findReferences(self, symbol: str) -> list[Reference]:
        refs: list[Reference] = []
        seen: set[tuple[str, int]] = set()
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                for r in script.get_references():
                    if r.name == symbol:
                        key = (str(path), r.line)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=r.line))
                            seen.add(key)
            except Exception:
                continue
        return refs

    # ------------------------------------------------------------------
    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)

    # ------------------------------------------------------------------
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        # The fuzzy indexer tracks files internally
        if hasattr(self._indexer, "index"):
            return len(self._indexer.index)
        return 0
