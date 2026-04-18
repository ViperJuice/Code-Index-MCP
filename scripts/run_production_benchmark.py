#!/usr/bin/env python3
"""Production-index retrieval benchmark.

Runs the standard query suite against the *live* production index
(existing code_index.db + vector_index.qdrant) via EnhancedDispatcher —
the same code path the MCP tool uses — and compares against native
ripgrep / grep / glob.

No re-indexing. No temp databases. What you test is what users get.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Query suite (identical to run_e2e_retrieval_validation.py)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QueryCase:
    mode: str          # classic | bm25 | fuzzy | semantic | hybrid
    query: str
    expected: str      # filename fragment that must appear in top-k results
    category: str = "general"


QUERY_SUITE = [
    QueryCase("classic",  "semantic preflight",
              "semantic_preflight.py",  "semantic"),
    QueryCase("bm25",     "qdrant docker compose autostart",
              "qdrant_autostart.py",    "symbol_precise"),
    QueryCase("fuzzy",    "semntic preflite raport",
              "semantic_preflight.py",  "noisy"),
    QueryCase("semantic", "where is qdrant autostart implemented",
              "qdrant_autostart.py",    "general"),
    QueryCase("hybrid",   "how does semantic setup validate qdrant and embedding readiness",
              "setup_commands.py",      "semantic_intent"),
    QueryCase("bm25",     "class SemanticIndexer",
              "semantic_indexer.py",    "symbol_precise"),
    QueryCase("semantic", "extract symbols from python using treesitter",
              "semantic_indexer.py",    "semantic_intent"),
    QueryCase("fuzzy",    "SemnticIndexer index_file",
              "semantic_indexer.py",    "noisy"),
    QueryCase("hybrid",   "how do artifact push pull and delta resolution work",
              "delta_resolver.py",      "persistence"),
]

# Modes that route through the semantic (Qdrant/Voyage) path
_SEMANTIC_MODES = {"semantic", "hybrid"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env_local() -> None:
    env_path = Path(".env.local")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(0.0, min(1.0, pct)) * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] * (1.0 - rank + lo) + ordered[hi] * (rank - lo)


def _top_file(results: list) -> str:
    if not results:
        return ""
    r = results[0]
    for key in ("file", "relative_path", "filepath", "file_path", "path"):
        v = r.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def _in_top_k(results: list, fragment: str, k: int) -> bool:
    for r in results[:k]:
        for key in ("file", "relative_path", "filepath", "file_path", "path"):
            v = r.get(key, "")
            if isinstance(v, str) and fragment in v:
                return True
    return False


def _make_row(
    mode: str,
    category: str,
    query: str,
    expected: str,
    top_file: str,
    latencies: List[float],
    top1_hits: int,
    top3_hits: int,
    iterations: int,
    result_count: int,
) -> Dict:
    return {
        "mode": mode,
        "category": category,
        "query": query,
        "expected": expected,
        "top_file": top_file,
        "result_count": result_count,
        "latency_ms": round(_percentile(latencies, 0.5), 2),
        "latency_p50_ms": round(_percentile(latencies, 0.5), 2),
        "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
        "top1_accuracy_pct": round(top1_hits / max(iterations, 1) * 100.0, 1),
        "top3_accuracy_pct": round(top3_hits / max(iterations, 1) * 100.0, 1),
        "pass": top1_hits > 0,
        "pass_top3": top3_hits > 0,
    }


# ---------------------------------------------------------------------------
# Native comparison (ripgrep / grep / glob)
# ---------------------------------------------------------------------------

def _run_native(query: str, repo: Path) -> List[Tuple[str, str, float, bool]]:
    """Run ripgrep, grep, glob against the repo. Returns list of (backend, top_file, ms, pass)."""
    results = []
    # ripgrep
    t0 = perf_counter()
    try:
        proc = subprocess.run(
            ["rg", "-l", "--max-count=1", query, str(repo)],
            capture_output=True, text=True, timeout=30,
        )
        elapsed = (perf_counter() - t0) * 1000.0
        top = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        results.append(("ripgrep", top, elapsed))
    except Exception as exc:
        results.append(("ripgrep", f"ERROR:{exc}", (perf_counter() - t0) * 1000.0))

    # grep
    t0 = perf_counter()
    try:
        proc = subprocess.run(
            ["grep", "-rl", query, str(repo)],
            capture_output=True, text=True, timeout=30,
        )
        elapsed = (perf_counter() - t0) * 1000.0
        top = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        results.append(("grep", top, elapsed))
    except Exception as exc:
        results.append(("grep", f"ERROR:{exc}", (perf_counter() - t0) * 1000.0))

    # glob (filename match only)
    t0 = perf_counter()
    try:
        words = query.lower().split()
        matches = [
            str(p) for p in repo.rglob("*")
            if p.is_file() and any(w in p.name.lower() for w in words)
        ]
        elapsed = (perf_counter() - t0) * 1000.0
        results.append(("glob", matches[0] if matches else "", elapsed))
    except Exception as exc:
        results.append(("glob", f"ERROR:{exc}", (perf_counter() - t0) * 1000.0))

    return results


# ---------------------------------------------------------------------------
# MCP retrieval via dispatcher
# ---------------------------------------------------------------------------

def _run_mcp_suite(
    dispatcher,
    iterations: int,
    limit: int,
) -> List[Dict]:
    rows = []
    for case in QUERY_SUITE:
        semantic = case.mode in _SEMANTIC_MODES
        fuzzy = case.mode == "fuzzy"
        latencies: List[float] = []
        top_file = ""
        top1_hits = 0
        top3_hits = 0
        result_count = 0

        for i in range(iterations):
            t0 = perf_counter()
            results = list(dispatcher.search(query=case.query, limit=limit, semantic=semantic, fuzzy=fuzzy))
            elapsed = (perf_counter() - t0) * 1000.0
            latencies.append(elapsed)
            if i == 0:
                top_file = _top_file(results)
                result_count = len(results)
            if _in_top_k(results, case.expected, 1):
                top1_hits += 1
            if _in_top_k(results, case.expected, 3):
                top3_hits += 1

        rows.append(_make_row(
            mode=case.mode,
            category=case.category,
            query=case.query,
            expected=case.expected,
            top_file=top_file,
            latencies=latencies,
            top1_hits=top1_hits,
            top3_hits=top3_hits,
            iterations=iterations,
            result_count=result_count,
        ))
    return rows


# ---------------------------------------------------------------------------
# Native suite
# ---------------------------------------------------------------------------

def _run_native_suite(repo: Path) -> List[Dict]:
    """Run native tools against the subset of queries that have literal-match expectations."""
    # Use only the queries where literal search makes sense (classic/bm25/fuzzy)
    rows = []
    native_cases = [c for c in QUERY_SUITE if c.mode not in _SEMANTIC_MODES]
    for case in native_cases:
        for backend, top_file, elapsed_ms in _run_native(case.query, repo):
            passed = bool(top_file and case.expected in top_file)
            rows.append({
                "backend": backend,
                "mode": case.mode,
                "category": case.category,
                "query": case.query,
                "expected": case.expected,
                "top_file": top_file,
                "latency_ms": round(elapsed_ms, 2),
                "pass": passed,
            })
    return rows


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------

def _write_markdown(result: Dict, output: Path) -> None:
    mcp_rows = result["mcp"]["results"]
    native_rows = result["native"]["results"]

    mcp_passed = sum(1 for r in mcp_rows if r["pass"])
    mcp_passed_top3 = sum(1 for r in mcp_rows if r.get("pass_top3"))
    native_passed = sum(1 for r in native_rows if r["pass"])

    lines = [
        "# Production Retrieval Benchmark",
        "",
        f"- Run: `{result['timestamp']}`",
        f"- Repo: `{result['repo']}`",
        f"- Index: `{result['index_db']}`",
        f"- Qdrant: `{result['qdrant_path']}`",
        f"- Qdrant points: `{result.get('qdrant_points', 'N/A')}`",
        f"- Iterations per query: `{result['iterations']}`",
        "",
        "## MCP Dispatcher Results",
        "",
        f"**Top-1 pass rate: {mcp_passed}/{len(mcp_rows)} "
        f"({100*mcp_passed/max(len(mcp_rows),1):.1f}%)**  "
        f"Top-3: {mcp_passed_top3}/{len(mcp_rows)} "
        f"({100*mcp_passed_top3/max(len(mcp_rows),1):.1f}%)",
        "",
        "| Pass | Mode | Category | Query | Expected | Top File | P50 (ms) | P95 (ms) |",
        "|:---:|---|---|---|---|---|---:|---:|",
    ]
    for r in mcp_rows:
        icon = "✅" if r["pass"] else ("🔶" if r.get("pass_top3") else "❌")
        top = Path(r["top_file"]).name if r["top_file"] else "(none)"
        lines.append(
            f"| {icon} | {r['mode']} | {r['category']} | {r['query']} "
            f"| `{r['expected']}` | `{top}` "
            f"| {r['latency_p50_ms']} | {r['latency_p95_ms']} |"
        )

    lines += [
        "",
        "## Native Tool Comparison",
        "",
        f"**Pass rate: {native_passed}/{len(native_rows)}**",
        "",
        "| Pass | Backend | Query | Expected | Top File | Latency (ms) |",
        "|:---:|---|---|---|---|---:|",
    ]
    for r in native_rows:
        icon = "✅" if r["pass"] else "❌"
        top = Path(r["top_file"]).name if r["top_file"] and not r["top_file"].startswith("ERROR") else r["top_file"]
        lines.append(
            f"| {icon} | {r['backend']} | {r['query']} "
            f"| `{r['expected']}` | `{top}` | {r['latency_ms']} |"
        )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    _load_env_local()

    parser = argparse.ArgumentParser(description="Benchmark MCP retrieval against the live production index")
    parser.add_argument("--repo", default=".", help="Repository root (default: .)")
    parser.add_argument("--db", default="", help="Path to code_index.db (auto-detected if omitted)")
    parser.add_argument("--qdrant", default="", help="Path to vector_index.qdrant (auto-detected if omitted)")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-native", action="store_true", help="Skip native tool comparison")
    parser.add_argument(
        "--json-out",
        default="docs/benchmarks/production_benchmark.json",
    )
    parser.add_argument(
        "--md-out",
        default="docs/benchmarks/production_benchmark.md",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    # Auto-detect index paths
    db_path = Path(args.db) if args.db else None
    if db_path is None:
        for candidate in ["code_index.db", ".indexes/code_index.db"]:
            if (repo / candidate).exists():
                db_path = repo / candidate
                break
    if db_path is None or not db_path.exists():
        print(f"ERROR: code_index.db not found under {repo}. Pass --db to specify.")
        return 1

    qdrant_path = Path(args.qdrant) if args.qdrant else None
    if qdrant_path is None:
        candidate = repo / "vector_index.qdrant"
        if candidate.exists():
            qdrant_path = candidate
    qdrant_str = str(qdrant_path) if qdrant_path else ""

    # Import here so PYTHONPATH / env vars are already set
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

    print(f"Loading index: {db_path}")
    store = SQLiteStore(str(db_path))

    print(f"Initializing dispatcher (Qdrant: {qdrant_str or 'disabled'}) ...")
    _explicit = os.getenv("RERANKER_TYPE", "").strip().lower()
    if _explicit:
        reranker_type = _explicit
    elif os.getenv("VOYAGE_API_KEY"):
        reranker_type = "voyage"
    else:
        reranker_type = "none"
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        semantic_search_enabled=bool(qdrant_str),
        reranker_type=reranker_type,
    )

    # Get Qdrant point count for the report
    qdrant_points: Optional[int] = None
    if dispatcher._semantic_indexer:
        try:
            info = dispatcher._semantic_indexer.qdrant.get_collection(
                dispatcher._semantic_indexer.collection
            )
            qdrant_points = info.points_count
        except Exception:
            pass

    print(f"Semantic indexer active: {dispatcher._semantic_indexer is not None}")
    if qdrant_points is not None:
        print(f"Qdrant points: {qdrant_points}")

    # Run MCP suite
    print(f"\nRunning {len(QUERY_SUITE)} queries × {args.iterations} iteration(s) via dispatcher...")
    mcp_rows = _run_mcp_suite(dispatcher, args.iterations, args.limit)
    mcp_passed = sum(1 for r in mcp_rows if r["pass"])
    mcp_passed_top3 = sum(1 for r in mcp_rows if r.get("pass_top3"))
    print(f"MCP: {mcp_passed}/{len(mcp_rows)} top-1  |  {mcp_passed_top3}/{len(mcp_rows)} top-3")

    # Run native suite
    native_rows: List[Dict] = []
    if not args.no_native:
        print("\nRunning native tool comparison...")
        native_rows = _run_native_suite(repo)
        native_passed = sum(1 for r in native_rows if r["pass"])
        print(f"Native: {native_passed}/{len(native_rows)}")

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "index_db": str(db_path),
        "qdrant_path": qdrant_str,
        "qdrant_points": qdrant_points,
        "iterations": args.iterations,
        "limit": args.limit,
        "mcp": {
            "pass_rate": round(mcp_passed / max(len(mcp_rows), 1) * 100, 1),
            "top3_pass_rate": round(mcp_passed_top3 / max(len(mcp_rows), 1) * 100, 1),
            "passed": mcp_passed,
            "total": len(mcp_rows),
            "results": mcp_rows,
        },
        "native": {
            "results": native_rows,
        },
    }

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown(result, md_path)

    print(f"\nJSON → {json_path}")
    print(f"MD   → {md_path}")
    print(f"\nFinal: MCP {mcp_passed}/{len(mcp_rows)} top-1 ({result['mcp']['pass_rate']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
