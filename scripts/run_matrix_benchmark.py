#!/usr/bin/env python3
"""Matrix benchmark: all rerankers × all retrieval modes × native tools.

Tests the live production index across every meaningful configuration:
  - Embeddings: BM25-only | voyage-code-3 (the one indexed profile)
  - Rerankers:  none | flashrank | voyage | cross-encoder
  - Retrieval:  classic | bm25 | fuzzy | semantic | hybrid (per query)
  - Native:     ripgrep | grep | glob | sed

Reranker only affects the semantic path (BM25 path skips reranking by design),
so BM25-only runs with different rerankers will be identical — they're still
included for completeness.

Usage:
    PYTHONPATH=. VOYAGE_AI_API_KEY=... .venv/bin/python3 \\
        scripts/run_matrix_benchmark.py --repo . --limit 5 \\
        --json-out docs/benchmarks/matrix_benchmark.json \\
        --md-out  docs/benchmarks/matrix_benchmark.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Query suite
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QueryCase:
    mode: str      # classic | bm25 | fuzzy | semantic | hybrid
    query: str
    expected: str  # filename fragment that must appear in top-k
    category: str = "general"


QUERY_SUITE: List[QueryCase] = [
    # --- Original 9 queries ---
    QueryCase("classic",  "semantic preflight checks implementation",
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
    # --- Symbol-routing queries (tests query_intent → symbols table path) ---
    QueryCase("bm25",     "class EnhancedDispatcher",
              "dispatcher_enhanced.py", "symbol_precise"),
    QueryCase("bm25",     "class SQLiteStore",
              "sqlite_store.py",        "symbol_precise"),
    QueryCase("bm25",     "class FlashRankReranker",
              "reranker.py",            "symbol_precise"),
    QueryCase("bm25",     "class VoyageReranker",
              "reranker.py",            "symbol_precise"),
    QueryCase("bm25",     "EnhancedDispatcher",
              "dispatcher_enhanced.py", "symbol_precise"),
    QueryCase("bm25",     "def _symbol_route",
              "dispatcher_enhanced.py", "symbol_precise"),
    QueryCase("semantic", "where is the symbol routing logic implemented",
              "dispatcher_enhanced.py", "semantic_intent"),
    QueryCase("bm25",     "class CrossEncoderReranker",
              "reranker.py",            "symbol_precise"),
]

_SEMANTIC_MODES = {"semantic", "hybrid"}

# Labels for query cases (short form for table headers)
_CASE_LABELS = [
    "classic/sem_preflight",
    "bm25/qdrant_auto",
    "fuzzy/sem_preflite",
    "semantic/qdrant_auto",
    "hybrid/setup_cmd",
    "bm25/SemanticIndexer",
    "semantic/treesitter",
    "fuzzy/SemnticIndexer",
    "hybrid/delta",
    "bm25/EnhancedDispatcher(c)",
    "bm25/SQLiteStore(c)",
    "bm25/FlashRank(c)",
    "bm25/VoyageReranker(c)",
    "bm25/EnhancedDisp(bare)",
    "bm25/def_symbol_route",
    "semantic/sym_routing",
    "bm25/CrossEncoder(c)",
]


# ---------------------------------------------------------------------------
# Benchmark configurations to test
# ---------------------------------------------------------------------------

@dataclass
class BenchConfig:
    label: str
    semantic_enabled: bool
    reranker_type: str
    embedding_label: str = ""
    semantic_profile: str = ""

    def __post_init__(self):
        if not self.embedding_label:
            if self.semantic_profile:
                self.embedding_label = self.semantic_profile
            elif self.semantic_enabled:
                self.embedding_label = "voyage-code-3"
            else:
                self.embedding_label = "BM25-only"


def _load_configs_from_metadata() -> List[BenchConfig]:
    """Auto-discover benchmark configs from .index_metadata.json semantic profiles."""
    try:
        meta = json.loads(Path(".index_metadata.json").read_text(encoding="utf-8"))
        profiles = meta.get("semantic_profiles", {})
    except Exception:
        profiles = {}

    configs: List[BenchConfig] = [
        BenchConfig("BM25-only / no-reranker", semantic_enabled=False, reranker_type="none"),
        BenchConfig("BM25-only / flashrank",   semantic_enabled=False, reranker_type="flashrank"),
    ]

    for pid, pdata in sorted(profiles.items()):
        model = pdata.get("embedding_model", pid)
        provider = pdata.get("embedding_provider", "")
        for reranker in ["none", "flashrank", "cross-encoder"]:
            configs.append(BenchConfig(
                f"{model} / {reranker}",
                semantic_enabled=True,
                reranker_type=reranker,
                semantic_profile=pid,
                embedding_label=model,
            ))
        if provider == "voyage":
            configs.append(BenchConfig(
                f"{model} / voyage-reranker",
                semantic_enabled=True,
                reranker_type="voyage",
                semantic_profile=pid,
                embedding_label=model,
            ))

    return configs


CONFIGS: List[BenchConfig] = _load_configs_from_metadata()


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
    """Exact basename match (avoids false positives from substring matching)."""
    frag_base = fragment.rstrip("/").rsplit("/", 1)[-1]
    for r in results[:k]:
        for key in ("file", "relative_path", "filepath", "file_path", "path"):
            v = r.get(key, "")
            if not isinstance(v, str):
                continue
            # Compare basename — avoids test_foo_semantic_indexer.py matching semantic_indexer.py
            vbase = v.rstrip("/").rsplit("/", 1)[-1]
            if vbase == frag_base:
                return True
            # Fallback: if expected has no dir component, accept suffix match too
            if "/" not in fragment and v.endswith("/" + fragment):
                return True
    return False


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


# ---------------------------------------------------------------------------
# Native tool comparison
# ---------------------------------------------------------------------------

def _run_native_query(query: str, repo: Path) -> List[Tuple[str, str, float]]:
    """Returns list of (backend, top_file, latency_ms)."""
    results: List[Tuple[str, str, float]] = []
    words = query.lower().split()
    first_word = words[0] if words else query

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

    # glob (filename-only)
    t0 = perf_counter()
    try:
        matches = [
            str(p) for p in repo.rglob("*")
            if p.is_file() and any(w in p.name.lower() for w in words)
        ]
        elapsed = (perf_counter() - t0) * 1000.0
        results.append(("glob", matches[0] if matches else "", elapsed))
    except Exception as exc:
        results.append(("glob", f"ERROR:{exc}", (perf_counter() - t0) * 1000.0))

    # sed — use GNU sed `F` command (print filename) to find which files match
    t0 = perf_counter()
    try:
        # Escape the first word for use in a sed address regex
        sed_pattern = re.escape(first_word).replace("/", r"\/")
        # Find source files, then pipe through sed to find ones containing pattern
        bash_cmd = (
            f"find {repo} -type f "
            r"\( -name '*.py' -o -name '*.ts' -o -name '*.js' "
            r"-o -name '*.go' -o -name '*.rs' -o -name '*.java' \) "
            f"| head -2000 "
            f"| xargs sed -n '/{sed_pattern}/F' 2>/dev/null "
            f"| head -1"
        )
        proc = subprocess.run(
            ["bash", "-c", bash_cmd],
            capture_output=True, text=True, timeout=60,
        )
        elapsed = (perf_counter() - t0) * 1000.0
        top = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        results.append(("sed", top, elapsed))
    except Exception as exc:
        results.append(("sed", f"ERROR:{exc}", (perf_counter() - t0) * 1000.0))

    return results


def _run_native_suite(repo: Path) -> List[Dict]:
    """Run native tools against queries where literal search makes sense."""
    rows = []
    # Use all cases — native tools will simply fail on semantic/intent queries
    for case in QUERY_SUITE:
        for backend, top_file, elapsed_ms in _run_native_query(case.query, repo):
            passed = bool(top_file and not top_file.startswith("ERROR"))
            if passed:
                top_base = top_file.rstrip("/").rsplit("/", 1)[-1]
                exp_base = case.expected.rstrip("/").rsplit("/", 1)[-1]
                passed = (top_base == exp_base) or top_file.endswith("/" + case.expected)
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
# MCP dispatcher runner
# ---------------------------------------------------------------------------

def _run_config(
    cfg: BenchConfig,
    store,
    qdrant_str: str,
    iterations: int,
    limit: int,
) -> List[Dict]:
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

    use_qdrant = cfg.semantic_enabled and bool(qdrant_str)
    if cfg.semantic_profile:
        os.environ["SEMANTIC_DEFAULT_PROFILE"] = cfg.semantic_profile
    try:
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            semantic_search_enabled=use_qdrant,
            reranker_type=cfg.reranker_type,
        )

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
                results = list(dispatcher.search(
                    query=case.query, limit=limit, semantic=semantic, fuzzy=fuzzy
                ))
                elapsed = (perf_counter() - t0) * 1000.0
                latencies.append(elapsed)
                if i == 0:
                    top_file = _top_file(results)
                    result_count = len(results)
                if _in_top_k(results, case.expected, 1):
                    top1_hits += 1
                if _in_top_k(results, case.expected, 3):
                    top3_hits += 1

            rows.append({
                "config": cfg.label,
                "embedding": cfg.embedding_label,
                "reranker": cfg.reranker_type,
                "mode": case.mode,
                "category": case.category,
                "query": case.query,
                "expected": case.expected,
                "top_file": top_file,
                "result_count": result_count,
                "latency_p50_ms": round(_percentile(latencies, 0.5), 2),
                "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
                "pass": top1_hits > 0,
                "pass_top3": top3_hits > 0,
            })

        # Cleanup dispatcher resources
        try:
            if hasattr(dispatcher, '_semantic_indexer') and dispatcher._semantic_indexer:
                try:
                    dispatcher._semantic_indexer.qdrant.close()
                except Exception:
                    pass
        except Exception:
            pass

    finally:
        if cfg.semantic_profile:
            os.environ.pop("SEMANTIC_DEFAULT_PROFILE", None)

    return rows


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------

def _write_markdown(result: Dict, output: Path) -> None:
    all_config_rows: List[Dict] = result["mcp_matrix"]
    native_rows: List[Dict] = result["native"]["results"]

    # Group rows by config label
    configs_seen: List[str] = []
    by_config: Dict[str, List[Dict]] = {}
    for r in all_config_rows:
        c = r["config"]
        if c not in by_config:
            by_config[c] = []
            configs_seen.append(c)
        by_config[c].append(r)

    n_queries = len(QUERY_SUITE)

    lines = [
        "# Matrix Benchmark: Rerankers × Embeddings × Retrieval Modes",
        "",
        f"- Run: `{result['timestamp']}`",
        f"- Repo: `{result['repo']}`",
        f"- Index: `{result['index_db']}`",
        f"- Qdrant: `{result['qdrant_path']}`",
        f"- Qdrant points: `{result.get('qdrant_points', 'N/A')}`",
        f"- Queries: {n_queries}  |  Limit: {result['limit']}",
        "",
        "## Summary: Top-1 Pass Rate by Configuration",
        "",
        "| Configuration | Embedding | Reranker | Top-1 | Top-3 |"
        + "".join(f" {lbl} |" for lbl in _CASE_LABELS),
        "|---|---|---|:---:|:---:|"
        + "".join(" :---: |" for _ in _CASE_LABELS),
    ]

    for cfg_label in configs_seen:
        rows = by_config[cfg_label]
        top1 = sum(1 for r in rows if r["pass"])
        top3 = sum(1 for r in rows if r.get("pass_top3"))
        emb = rows[0]["embedding"] if rows else ""
        reranker = rows[0]["reranker"] if rows else ""
        cells = ""
        for r in rows:
            icon = "✅" if r["pass"] else ("🔶" if r.get("pass_top3") else "❌")
            cells += f" {icon} |"
        lines.append(
            f"| {cfg_label} | {emb} | {reranker} "
            f"| **{top1}/{n_queries}** | {top3}/{n_queries} |{cells}"
        )

    # Detailed tables per config
    lines += ["", "---", "", "## Detailed Results per Configuration", ""]
    for cfg_label in configs_seen:
        rows = by_config[cfg_label]
        top1 = sum(1 for r in rows if r["pass"])
        top3 = sum(1 for r in rows if r.get("pass_top3"))
        lines += [
            f"### {cfg_label}",
            "",
            f"Top-1: **{top1}/{n_queries}** ({100*top1/max(n_queries,1):.1f}%)  "
            f"Top-3: {top3}/{n_queries} ({100*top3/max(n_queries,1):.1f}%)",
            "",
            "| Pass | Mode | Category | Query | Expected | Top File | P50ms |",
            "|:---:|---|---|---|---|---|---:|",
        ]
        for r in rows:
            icon = "✅" if r["pass"] else ("🔶" if r.get("pass_top3") else "❌")
            top = Path(r["top_file"]).name if r["top_file"] else "(none)"
            lines.append(
                f"| {icon} | {r['mode']} | {r['category']} | {r['query']} "
                f"| `{r['expected']}` | `{top}` | {r['latency_p50_ms']} |"
            )
        lines.append("")

    # Native comparison
    native_passed = sum(1 for r in native_rows if r["pass"])
    lines += [
        "---",
        "",
        "## Native Tool Comparison (ripgrep / grep / glob / sed)",
        "",
        f"**Pass rate: {native_passed}/{len(native_rows)}**",
        "",
    ]

    # Group by backend
    backends: List[str] = []
    by_backend: Dict[str, List[Dict]] = {}
    for r in native_rows:
        b = r["backend"]
        if b not in by_backend:
            by_backend[b] = []
            backends.append(b)
        by_backend[b].append(r)

    # Summary row per backend
    lines += [
        "| Backend | Top-1 Pass | Avg Latency (ms) |",
        "|---|:---:|---:|",
    ]
    for b in backends:
        br = by_backend[b]
        passed = sum(1 for r in br if r["pass"])
        avg_lat = sum(r["latency_ms"] for r in br) / max(len(br), 1)
        lines.append(f"| {b} | {passed}/{len(br)} | {avg_lat:.1f} |")

    lines += [
        "",
        "| Pass | Backend | Query | Expected | Top File | Latency (ms) |",
        "|:---:|---|---|---|---|---:|",
    ]
    for r in native_rows:
        icon = "✅" if r["pass"] else "❌"
        top = Path(r["top_file"]).name if r["top_file"] and not r["top_file"].startswith("ERROR") else (r["top_file"] or "(none)")
        lines.append(
            f"| {icon} | {r['backend']} | {r['query'][:50]} "
            f"| `{r['expected']}` | `{top}` | {r['latency_ms']} |"
        )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    _load_env_local()

    # Prevent .env.native's stale devcontainer paths from breaking dispatcher init.
    # The benchmark never needs cross-repo support.
    os.environ["MCP_ENABLE_MULTI_REPO"] = "false"

    parser = argparse.ArgumentParser(description="Matrix benchmark: all rerankers × embeddings × native tools")
    parser.add_argument("--repo", default=".", help="Repository root (default: .)")
    parser.add_argument("--db", default="", help="Path to code_index.db (auto-detected if omitted)")
    parser.add_argument("--qdrant", default="", help="Path to vector_index.qdrant (auto-detected if omitted)")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-native", action="store_true", help="Skip native tool comparison")
    parser.add_argument("--configs", default="", help="Comma-separated config labels to run (default: all)")
    parser.add_argument("--json-out", default="docs/benchmarks/matrix_benchmark.json")
    parser.add_argument("--md-out",   default="docs/benchmarks/matrix_benchmark.md")
    parser.add_argument("--bm25-only", action="store_true",
                        help="Run only BM25 configs (no embedding server required)")
    parser.add_argument("--fail-below", type=float, default=0.0,
                        help="Exit non-zero if overall Top-1 accuracy is below this threshold (0.0-1.0)")
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

    # Check Voyage key availability
    has_voyage = bool(os.getenv("VOYAGE_AI_API_KEY") or os.getenv("VOYAGE_API_KEY"))
    if not has_voyage:
        print("WARNING: No VOYAGE_AI_API_KEY found — voyage reranker config will be skipped.")

    # Filter configs
    configs_to_run = CONFIGS
    if args.bm25_only:
        configs_to_run = [c for c in configs_to_run if not c.semantic_enabled]
        print(f"--bm25-only: running {len(configs_to_run)} BM25 config(s).")
    if args.configs:
        requested = {c.strip() for c in args.configs.split(",")}
        configs_to_run = [c for c in CONFIGS if c.label in requested]
        if not configs_to_run:
            print(f"ERROR: No matching configs for: {args.configs}")
            return 1

    # Skip voyage reranker if no key
    if not has_voyage:
        configs_to_run = [c for c in configs_to_run if c.reranker_type != "voyage"]
        print("Skipping voyage-reranker configs (no API key).")

    from mcp_server.storage.sqlite_store import SQLiteStore

    print(f"Loading index: {db_path}")
    store = SQLiteStore(str(db_path))

    # Get Qdrant point count
    qdrant_points: Optional[int] = None
    if qdrant_str:
        try:
            from qdrant_client import QdrantClient
            qc = QdrantClient(path=qdrant_str)
            for col in qc.get_collections().collections:
                info = qc.get_collection(col.name)
                qdrant_points = (qdrant_points or 0) + (info.points_count or 0)
            qc.close()
        except Exception:
            pass

    all_mcp_rows: List[Dict] = []

    for i, cfg in enumerate(configs_to_run):
        print(f"\n[{i+1}/{len(configs_to_run)}] {cfg.label}")
        print(f"  embedding={cfg.embedding_label}  reranker={cfg.reranker_type}")
        rows = _run_config(cfg, store, qdrant_str, args.iterations, args.limit)
        top1 = sum(1 for r in rows if r["pass"])
        top3 = sum(1 for r in rows if r.get("pass_top3"))
        print(f"  → Top-1: {top1}/{len(rows)}  Top-3: {top3}/{len(rows)}")
        all_mcp_rows.extend(rows)

    # Native
    native_rows: List[Dict] = []
    if not args.no_native:
        print("\nRunning native tool comparison (ripgrep / grep / glob / sed)...")
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
        "configs_run": [c.label for c in configs_to_run],
        "mcp_matrix": all_mcp_rows,
        "native": {"results": native_rows},
    }

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_markdown(result, md_path)

    print(f"\nJSON → {json_path}")
    print(f"MD   → {md_path}")

    # Final summary
    print("\n=== SUMMARY ===")
    from collections import defaultdict
    by_config: Dict[str, List[Dict]] = defaultdict(list)
    for r in all_mcp_rows:
        by_config[r["config"]].append(r)
    for cfg_label, rows in by_config.items():
        top1 = sum(1 for r in rows if r["pass"])
        print(f"  {cfg_label:45s}  {top1}/{len(rows)}")

    if args.fail_below > 0.0 and all_mcp_rows:
        overall_top1 = sum(1 for r in all_mcp_rows if r["pass"]) / len(all_mcp_rows)
        print(f"\nOverall Top-1 accuracy: {overall_top1:.1%} (threshold: {args.fail_below:.1%})")
        if overall_top1 < args.fail_below:
            print(f"FAIL: accuracy {overall_top1:.1%} is below --fail-below {args.fail_below:.1%}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
