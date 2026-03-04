#!/usr/bin/env python3
"""Benchmark MCP retrieval against native grep/ripgrep/glob approaches."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Dict, List


NATIVE_QUERIES = [
    {"query": "semantic preflight", "expected": "semantic_preflight.py"},
    {"query": "qdrant autostart", "expected": "qdrant_autostart.py"},
    {"query": "setup semantic", "expected": "setup_commands.py"},
]


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


def benchmark_native(repo: Path) -> Dict[str, object]:
    rows = []

    for item in NATIVE_QUERIES:
        query = item["query"]
        expected = item["expected"]

        rg = _run_cmd(["rg", "-n", "--no-heading", query, str(repo)], repo)
        grep = _run_cmd(["grep", "-R", "-n", query, str(repo)], repo)

        # Glob baseline approximates name-oriented retrieval
        pattern = f"**/*{query.split()[0]}*"
        glob_matches = list(repo.glob(pattern))
        top_glob = str(glob_matches[0]) if glob_matches else ""

        rg_top = _top_line(str(rg["stdout"]))
        grep_top = _top_line(str(grep["stdout"]))
        rows.extend(
            [
                {
                    "backend": "ripgrep",
                    "query": query,
                    "top": rg_top,
                    "latency_ms": rg["latency_ms"],
                    "pass": expected in rg_top,
                },
                {
                    "backend": "grep",
                    "query": query,
                    "top": grep_top,
                    "latency_ms": grep["latency_ms"],
                    "pass": expected in grep_top,
                },
                {
                    "backend": "glob",
                    "query": query,
                    "top": top_glob,
                    "latency_ms": 0.0,
                    "pass": expected in top_glob,
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
        "200",
        "--limit",
        "5",
        "--qdrant-url",
        args.qdrant_url,
        "--openai-base",
        args.openai_base,
        "--openai-key",
        args.openai_key,
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
    parser = argparse.ArgumentParser(
        description="Benchmark MCP retrieval vs native tools"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--openai-base", default="http://localhost:8001/v1")
    parser.add_argument("--openai-key", default="vllm-local")
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

    native = benchmark_native(repo)
    mcp = benchmark_mcp(repo, e2e_script, args)

    report = {
        "repo": str(repo),
        "native": native,
        "mcp": mcp,
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# MCP vs Native Benchmark",
        "",
        f"- Repo: `{repo}`",
        f"- Native pass rate: `{native['pass_rate']}%`",
        f"- MCP pass rate: `{mcp.get('pass_rate', 'n/a')}%`",
        "",
        "## Native Tools",
        "",
        "| Backend | Query | Top Result | Pass | Latency (ms) |",
        "|---|---|---|---:|---:|",
    ]
    native_rows = native.get("rows", [])
    if isinstance(native_rows, list):
        for row in native_rows:
            lines.append(
                f"| {row['backend']} | {row['query']} | {row['top']} | {'yes' if row['pass'] else 'no'} | {row['latency_ms']} |"
            )

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"json": str(out_json), "markdown": str(out_md)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
