#!/usr/bin/env python3
"""End-to-end indexing and retrieval validation runner.

Runs lexical and semantic retrieval over this repository (or a target path),
evaluates against a fixed query suite, and emits JSON + Markdown reports.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Tuple

from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
from mcp_server.utils.semantic_indexer import SemanticIndexer


@dataclass(frozen=True)
class QueryCase:
    mode: str
    query: str
    expected_path_fragment: str


QUERY_SUITE = [
    QueryCase("classic", "semantic preflight", "semantic_preflight.py"),
    QueryCase("bm25", "qdrant docker compose autostart", "qdrant_autostart.py"),
    QueryCase("fuzzy", "semntic preflite raport", "semantic_preflight.py"),
    QueryCase(
        "semantic", "where is qdrant autostart implemented", "qdrant_autostart.py"
    ),
    QueryCase(
        "hybrid",
        "how does semantic setup validate qdrant and embedding readiness",
        "setup_commands.py",
    ),
]


def _collect_files(repo_path: Path, max_files: int) -> List[Path]:
    exts = {".py", ".md", ".yml", ".yaml", ".json"}
    ignored = {".git", ".venv", "node_modules", "qdrant_storage", ".indexes"}
    files: List[Path] = []
    for path in repo_path.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in exts:
            files.append(path)
            if len(files) >= max_files:
                break
    return files


def _top_file(results: List[Dict[str, object]]) -> str:
    if not results:
        return ""
    first = results[0]
    for key in ["file_path", "filepath", "file", "path", "relative_path"]:
        value = first.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _to_rows(
    results: List[Dict[str, object]],
    query: str,
    mode: str,
    elapsed_ms: float,
    expected: str,
):
    top = _top_file(results)
    passed = expected in top
    return {
        "mode": mode,
        "query": query,
        "expected": expected,
        "count": len(results),
        "top_file": top,
        "latency_ms": round(elapsed_ms, 2),
        "pass": passed,
    }


def run(args: argparse.Namespace) -> Dict[str, object]:
    repo_path = Path(args.repo).resolve()
    files = _collect_files(repo_path, args.max_files)

    if not files:
        raise RuntimeError(f"No indexable files found at {repo_path}")

    with tempfile.TemporaryDirectory(prefix="mcp-e2e-") as td:
        store = SQLiteStore(str(Path(td) / "code_index.db"))
        repo_id = store.create_repository(str(repo_path), repo_path.name)
        bm25 = BM25Indexer(store)
        fuzzy = FuzzyIndexer(store)

        profiles = {
            "oss_high": {
                "provider": "openai_compatible",
                "model_name": args.qwen_model,
                "model_version": "e2e",
                "vector_dimension": args.qwen_dim,
                "distance_metric": "dot",
                "normalization_policy": "l2",
                "chunk_schema_version": "1",
                "chunker_version": "treesitter-chunker@2.2.2",
                "build_metadata": {"openai_api_base": args.openai_base},
            }
        }
        if args.enable_voyage:
            profiles["commercial_high"] = {
                "provider": "voyage",
                "model_name": args.voyage_model,
                "model_version": "3",
                "vector_dimension": args.voyage_dim,
                "distance_metric": "dot",
                "normalization_policy": "provider-default",
                "chunk_schema_version": "1",
                "chunker_version": "treesitter-chunker@2.2.2",
            }

        os.environ["OPENAI_API_BASE"] = args.openai_base
        os.environ.setdefault("OPENAI_API_KEY", args.openai_key)
        os.environ["QDRANT_URL"] = args.qdrant_url

        registry = SemanticProfileRegistry.from_raw(
            profiles, "oss_high", tool_version="e2e"
        )
        qwen_sem = SemanticIndexer(
            collection=args.qwen_collection,
            qdrant_path=args.qdrant_url,
            profile_registry=registry,
            semantic_profile="oss_high",
        )
        voyage_sem = None
        if args.enable_voyage:
            voyage_sem = SemanticIndexer(
                collection=args.voyage_collection,
                qdrant_path=args.qdrant_url,
                profile_registry=registry,
                semantic_profile="commercial_high",
            )

        for path in files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            fid = store.store_file(
                repo_id, path, language="python" if path.suffix == ".py" else "text"
            )
            bm25.add_document(str(path), text, metadata={"language": "python"})
            fuzzy.add_file(str(path), text)
            qwen_sem.index_file(path)
            if voyage_sem:
                voyage_sem.index_file(path)
            # lightweight symbols for fuzzy symbol route
            for n, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith("def ") or s.startswith("class "):
                    name = s.split()[1].split("(")[0].split(":")[0]
                    store.store_symbol(
                        file_id=fid,
                        name=name,
                        kind="function" if s.startswith("def ") else "class",
                        line_start=n,
                        line_end=n,
                        signature=s,
                        documentation="",
                        metadata={"source": "e2e"},
                    )

        hybrid = HybridSearch(
            storage=store,
            bm25_indexer=bm25,
            semantic_indexer=qwen_sem,
            fuzzy_indexer=fuzzy,
            config=HybridSearchConfig(
                enable_bm25=True,
                enable_semantic=True,
                enable_fuzzy=True,
                cache_results=False,
                final_limit=args.limit,
                individual_limit=max(args.limit, 8),
            ),
        )

        rows = []
        for case in QUERY_SUITE:
            t0 = perf_counter()
            if case.mode == "classic":
                results = store.search_code_fts(case.query, limit=args.limit)
            elif case.mode == "bm25":
                results = bm25.search(case.query, limit=args.limit)
            elif case.mode == "fuzzy":
                results = store.search_symbols_fuzzy(case.query, limit=args.limit)
            elif case.mode == "semantic":
                results = qwen_sem.search(case.query, limit=args.limit)
            elif case.mode == "hybrid":
                results = asyncio.run(hybrid.search(case.query, limit=args.limit))
            else:
                continue
            elapsed = (perf_counter() - t0) * 1000.0
            rows.append(
                _to_rows(
                    results, case.query, case.mode, elapsed, case.expected_path_fragment
                )
            )

        model_rows = []
        if voyage_sem:
            q = "where is qdrant autostart implemented"
            t0 = perf_counter()
            qwen_res = qwen_sem.search(q, limit=args.limit)
            qwen_ms = (perf_counter() - t0) * 1000.0
            t0 = perf_counter()
            voy_res = voyage_sem.search(q, limit=args.limit)
            voy_ms = (perf_counter() - t0) * 1000.0
            model_rows.extend(
                [
                    _to_rows(
                        qwen_res, q, "semantic_qwen", qwen_ms, "qdrant_autostart.py"
                    ),
                    _to_rows(
                        voy_res, q, "semantic_voyage", voy_ms, "qdrant_autostart.py"
                    ),
                ]
            )

        summary = {
            "repo": str(repo_path),
            "indexed_files": len(files),
            "qdrant_url": args.qdrant_url,
            "openai_base": args.openai_base,
            "results": rows,
            "semantic_models": model_rows,
            "pass_rate": round(
                (sum(1 for r in rows if r["pass"]) / max(len(rows), 1)) * 100.0, 1
            ),
        }
        return summary


def write_markdown(result: Dict[str, object], output: Path) -> None:
    lines = [
        "# E2E Retrieval Validation",
        "",
        f"- Repo: `{result['repo']}`",
        f"- Indexed files: `{result['indexed_files']}`",
        f"- Pass rate: `{result['pass_rate']}%`",
        "",
        "## Retrieval Modes",
        "",
        "| Mode | Query | Top File | Pass | Latency (ms) |",
        "|---|---|---|---:|---:|",
    ]
    for row in result["results"]:
        lines.append(
            f"| {row['mode']} | {row['query']} | {row['top_file']} | {'yes' if row['pass'] else 'no'} | {row['latency_ms']} |"
        )

    semantic_models = result.get("semantic_models") or []
    if semantic_models:
        lines.extend(
            [
                "",
                "## Semantic Model Comparison",
                "",
                "| Mode | Top File | Pass | Latency (ms) |",
                "|---|---|---:|---:|",
            ]
        )
        for row in semantic_models:
            lines.append(
                f"| {row['mode']} | {row['top_file']} | {'yes' if row['pass'] else 'no'} | {row['latency_ms']} |"
            )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP retrieval E2E validation")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--max-files", type=int, default=200)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--openai-base", default="http://localhost:8001/v1")
    parser.add_argument("--openai-key", default="vllm-local")
    parser.add_argument("--enable-voyage", action="store_true")
    parser.add_argument("--voyage-model", default="voyage-code-3")
    parser.add_argument("--voyage-dim", type=int, default=2048)
    parser.add_argument("--qwen-model", default="Qwen/Qwen3-Embedding-8B")
    parser.add_argument("--qwen-dim", type=int, default=4096)
    parser.add_argument("--qwen-collection", default="code-index-e2e-oss-high")
    parser.add_argument("--voyage-collection", default="code-index-e2e-commercial-high")
    parser.add_argument(
        "--json-out", default="docs/benchmarks/e2e_retrieval_validation.json"
    )
    parser.add_argument(
        "--md-out", default="docs/benchmarks/e2e_retrieval_validation.md"
    )
    args = parser.parse_args()

    result = run(args)

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(result, md_path)

    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(md_path),
                "pass_rate": result["pass_rate"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
