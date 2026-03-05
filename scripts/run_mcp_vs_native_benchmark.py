#!/usr/bin/env python3
"""Benchmark MCP retrieval against native grep/ripgrep/glob approaches."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Dict, List


NATIVE_QUERIES = [
    {"query": "semantic preflight", "expected": "semantic_preflight.py"},
    {"query": "qdrant autostart", "expected": "qdrant_autostart.py"},
    {"query": "setup semantic", "expected": "setup_commands.py"},
]


def _load_local_env_file() -> None:
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


def _run_cmd(cmd: List[str], cwd: Path) -> Dict[str, object]:
    t0 = perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, check=False
    )
    elapsed = (perf_counter() - t0) * 1000.0
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "latency_ms": round(elapsed, 2),
    }


def _top_line(output: str) -> str:
    for line in output.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = max(0.0, min(1.0, pct)) * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def benchmark_native(repo: Path, iterations: int) -> Dict[str, object]:
    rows = []

    for item in NATIVE_QUERIES:
        query = item["query"]
        expected = item["expected"]

        rg_lats: List[float] = []
        grep_lats: List[float] = []
        glob_lats: List[float] = []
        rg_top = ""
        grep_top = ""
        top_glob = ""
        rg_passes = 0
        grep_passes = 0
        glob_passes = 0

        for _ in range(max(1, iterations)):
            rg = _run_cmd(["rg", "-n", "--no-heading", query, str(repo)], repo)
            grep = _run_cmd(["grep", "-R", "-n", query, str(repo)], repo)

            t0 = perf_counter()
            pattern = f"**/*{query.split()[0]}*"
            glob_matches = list(repo.glob(pattern))
            glob_elapsed = (perf_counter() - t0) * 1000.0

            rg_lats.append(float(str(rg["latency_ms"])))
            grep_lats.append(float(str(grep["latency_ms"])))
            glob_lats.append(glob_elapsed)

            if not rg_top:
                rg_top = _top_line(str(rg["stdout"]))
            if not grep_top:
                grep_top = _top_line(str(grep["stdout"]))
            if not top_glob:
                top_glob = str(glob_matches[0]) if glob_matches else ""

            rg_passes += 1 if expected in _top_line(str(rg["stdout"])) else 0
            grep_passes += 1 if expected in _top_line(str(grep["stdout"])) else 0
            glob_passes += (
                1 if expected in (str(glob_matches[0]) if glob_matches else "") else 0
            )

        rows.extend(
            [
                {
                    "backend": "ripgrep",
                    "query": query,
                    "top": rg_top,
                    "latency_ms": round(_percentile(rg_lats, 0.5), 2),
                    "latency_p50_ms": round(_percentile(rg_lats, 0.5), 2),
                    "latency_p95_ms": round(_percentile(rg_lats, 0.95), 2),
                    "top1_accuracy_pct": round(
                        (rg_passes / max(iterations, 1)) * 100.0,
                        1,
                    ),
                    "pass": rg_passes > 0,
                },
                {
                    "backend": "grep",
                    "query": query,
                    "top": grep_top,
                    "latency_ms": round(_percentile(grep_lats, 0.5), 2),
                    "latency_p50_ms": round(_percentile(grep_lats, 0.5), 2),
                    "latency_p95_ms": round(_percentile(grep_lats, 0.95), 2),
                    "top1_accuracy_pct": round(
                        (grep_passes / max(iterations, 1)) * 100.0,
                        1,
                    ),
                    "pass": grep_passes > 0,
                },
                {
                    "backend": "glob",
                    "query": query,
                    "top": top_glob,
                    "latency_ms": round(_percentile(glob_lats, 0.5), 2),
                    "latency_p50_ms": round(_percentile(glob_lats, 0.5), 2),
                    "latency_p95_ms": round(_percentile(glob_lats, 0.95), 2),
                    "top1_accuracy_pct": round(
                        (glob_passes / max(iterations, 1)) * 100.0,
                        1,
                    ),
                    "pass": glob_passes > 0,
                },
            ]
        )

    pass_rate = round(
        (sum(1 for r in rows if r["pass"]) / max(len(rows), 1)) * 100.0, 1
    )
    return {"rows": rows, "pass_rate": pass_rate}


def benchmark_mcp(
    repo: Path, e2e_script: Path, args: argparse.Namespace
) -> Dict[str, object]:
    temp_json = Path("/tmp/mcp_e2e_benchmark_validation.json")
    temp_md = Path("/tmp/mcp_e2e_benchmark_validation.md")
    cmd = [
        "uv",
        "run",
        "python",
        str(e2e_script),
        "--repo",
        str(repo),
        "--max-files",
        str(args.max_files),
        "--semantic-max-chars",
        str(args.semantic_max_chars),
        "--iterations",
        str(args.iterations),
        "--limit",
        "5",
        "--qdrant-url",
        args.qdrant_url,
        "--fireworks-base",
        args.fireworks_base,
        "--fireworks-api-key",
        args.fireworks_api_key,
        "--qwen-model",
        args.qwen_model,
        "--qwen-dim",
        str(args.qwen_dim),
        "--local-openai-base",
        args.local_openai_base,
        "--local-openai-key",
        args.local_openai_key,
        "--local-qwen-model",
        args.local_qwen_model,
        "--json-out",
        str(temp_json),
        "--md-out",
        str(temp_md),
    ]
    if args.enable_voyage:
        cmd.append("--enable-voyage")
    out = _run_cmd(cmd, repo)
    if out["returncode"] != 0:
        return {"error": out["stderr"], "latency_ms": out["latency_ms"]}

    if not temp_json.exists():
        return {"error": "E2E output file missing", "latency_ms": out["latency_ms"]}

    e2e_data = json.loads(temp_json.read_text(encoding="utf-8"))
    return {
        "latency_ms": out["latency_ms"],
        "pass_rate": e2e_data.get("pass_rate"),
        "results": e2e_data.get("results", []),
        "semantic_models": e2e_data.get("semantic_models", []),
    }


def main() -> int:
    _load_local_env_file()
    parser = argparse.ArgumentParser(
        description="Benchmark MCP retrieval vs native tools"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--max-files", type=int, default=200)
    parser.add_argument("--semantic-max-chars", type=int, default=24000)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument(
        "--fireworks-base",
        "--openai-base",
        dest="fireworks_base",
        default=os.getenv("FIREWORKS_BASE", "https://api.fireworks.ai/inference/v1"),
    )
    parser.add_argument(
        "--fireworks-api-key",
        "--openai-key",
        dest="fireworks_api_key",
        default="",
    )
    parser.add_argument("--qwen-model", default="Qwen/Qwen3-Embedding-8B")
    parser.add_argument("--qwen-dim", type=int, default=4096)
    parser.add_argument(
        "--local-openai-base", default=os.getenv("LOCAL_OPENAI_BASE", "")
    )
    parser.add_argument("--local-openai-key", default=os.getenv("LOCAL_OPENAI_KEY", ""))
    parser.add_argument("--local-qwen-model", default="")
    parser.add_argument("--enable-voyage", action="store_true")
    parser.add_argument(
        "--out-json", default="docs/benchmarks/mcp_vs_native_benchmark.json"
    )
    parser.add_argument(
        "--out-md", default="docs/benchmarks/mcp_vs_native_benchmark.md"
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    e2e_script = repo / "scripts" / "run_e2e_retrieval_validation.py"

    args.iterations = max(1, int(args.iterations))
    native = benchmark_native(repo, args.iterations)
    mcp = benchmark_mcp(repo, e2e_script, args)

    report = {
        "repo": str(repo),
        "native": native,
        "mcp": mcp,
        "iterations": args.iterations,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# MCP vs Native Benchmark",
        "",
        f"- Repo: `{repo}`",
        f"- Iterations per query: `{args.iterations}`",
        f"- Native pass rate: `{native['pass_rate']}%`",
        f"- MCP pass rate: `{mcp.get('pass_rate', 'n/a')}%`",
        "",
        "## Native Tools",
        "",
        "| Backend | Query | Top Result | Top-1 | P50 (ms) | P95 (ms) |",
        "|---|---|---|---:|---:|---:|",
    ]
    native_rows = native.get("rows", [])
    if isinstance(native_rows, list):
        for row in native_rows:
            lines.append(
                f"| {row['backend']} | {row['query']} | {row['top']} | {row.get('top1_accuracy_pct', 0)}% | {row.get('latency_p50_ms', row['latency_ms'])} | {row.get('latency_p95_ms', row['latency_ms'])} |"
            )

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
