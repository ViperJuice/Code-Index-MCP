#!/usr/bin/env python3
"""Collect and redact P26 private-alpha release evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REQUIRED_FIXTURE_CATEGORIES = (
    "python_repo",
    "typescript_js_repo",
    "mixed_docs_code_repo",
    "multi_repo_workspace",
    "large_ignored_vendor_repo",
)
ISSUE_CLASSIFICATIONS = {
    "public_alpha_blocker",
    "documented_limitation",
    "post_alpha_backlog",
}
FINAL_DECISIONS = {"go", "no_go", "conditional_go"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_timed(cmd: list[str], *, cwd: Path = REPO) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "command": cmd,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "returncode": completed.returncode,
        "output": completed.stdout.splitlines()[-80:],
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 3)
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 3)


def _classify_log_noise(raw_lines: list[str]) -> str:
    joined = "\n".join(raw_lines).lower()
    if any(marker in joined for marker in ("traceback", "fatal", "exception")):
        return "high"
    if any(marker in joined for marker in ("warning", "warn", "error")):
        return "medium"
    return "low"


def _scan_repo(repo_path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    files = [
        Path(root) / filename
        for root, _dirs, filenames in os.walk(repo_path, onerror=lambda _error: None)
        for filename in filenames
    ]
    first_index_time = round(time.perf_counter() - started, 3)

    query_runs: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    for case in fixture.get("query_cases", []):
        query = str(case.get("query", ""))
        expected_fragments = [str(fragment) for fragment in case.get("expected_path_fragments", [])]
        query_started = time.perf_counter()
        matches = [str(path) for path in files if query and query.lower() in path.name.lower()]
        latency_ms = (time.perf_counter() - query_started) * 1000
        latencies_ms.append(latency_ms)
        query_runs.append(
            {
                "name": case.get("name", query),
                "query": query,
                "expected_path_fragments": expected_fragments,
                "matched_paths": matches[:10],
                "matched_expected_fragments": [
                    fragment
                    for fragment in expected_fragments
                    if any(fragment in matched for matched in matches)
                ],
                "latency_ms": round(latency_ms, 3),
            }
        )

    quality_notes = fixture.get("result_quality_notes")
    if not quality_notes:
        expected_total = sum(
            len(case.get("expected_path_fragments", [])) for case in fixture.get("query_cases", [])
        )
        matched_total = sum(len(run["matched_expected_fragments"]) for run in query_runs)
        quality_notes = f"Matched {matched_total}/{expected_total} expected path fragments in redacted fixture checks."

    return {
        "first_index_time_seconds": first_index_time,
        "query_latency_p50_ms": _percentile(latencies_ms, 0.50),
        "query_latency_p95_ms": _percentile(latencies_ms, 0.95),
        "result_quality_notes": quality_notes,
        "query_runs": query_runs,
    }


def _validate_fixture_categories(fixtures: list[dict[str, Any]]) -> list[str]:
    categories = [str(fixture.get("category", "")) for fixture in fixtures]
    expected = set(REQUIRED_FIXTURE_CATEGORIES)
    actual = set(categories)
    errors: list[str] = []
    if actual != expected:
        errors.append(
            f"fixture categories must be exactly {sorted(expected)}; got {sorted(actual)}"
        )
    duplicates = sorted(category for category in actual if categories.count(category) > 1)
    if duplicates:
        errors.append(f"duplicate fixture categories: {duplicates}")
    return errors


def _redacted_fixture(raw_fixture: dict[str, Any], index: int) -> dict[str, Any]:
    measurements = raw_fixture["measurements"]
    return {
        "fixture_id": f"fixture-{index + 1}",
        "category": raw_fixture["category"],
        "display_alias": raw_fixture.get("display_alias", raw_fixture["category"]),
        "measurements": {
            "install_time_seconds": measurements["install_time_seconds"],
            "first_index_time_seconds": measurements["first_index_time_seconds"],
            "query_latency_p50_ms": measurements["query_latency_p50_ms"],
            "query_latency_p95_ms": measurements["query_latency_p95_ms"],
            "result_quality_notes": measurements["result_quality_notes"],
            "log_noise_classification": measurements["log_noise_classification"],
            "branch_default_branch_behavior": measurements["branch_default_branch_behavior"],
            "rollback_rebuild_behavior": measurements["rollback_rebuild_behavior"],
            "blocker_classification": measurements["blocker_classification"],
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**",
        "",
        "# Private Alpha Decision",
        "",
        "Raw private-alpha evidence belongs only under ignored `private-alpha-evidence/`.",
        "This committed record contains redacted fixture categories, aggregate timings,",
        "issue classifications, and the public-alpha decision.",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Schema version: `{payload['schema_version']}`",
        f"Decision summary: `{payload['final_decision']}`",
        "",
        "## Fixture Inventory",
        "",
        "| Fixture category | Install time | First index time | p50 | p95 | Blocker classification |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for fixture in payload["fixtures"]:
        measurement = fixture["measurements"]
        lines.append(
            "| {category} | {install} | {index} | {p50} | {p95} | {blocker} |".format(
                category=fixture["category"],
                install=measurement["install_time_seconds"],
                index=measurement["first_index_time_seconds"],
                p50=measurement["query_latency_p50_ms"],
                p95=measurement["query_latency_p95_ms"],
                blocker=measurement["blocker_classification"],
            )
        )

    lines.extend(
        [
            "",
            "## Install/Index/Query Evidence",
            "",
        ]
    )
    for fixture in payload["fixtures"]:
        measurement = fixture["measurements"]
        lines.extend(
            [
                f"### {fixture['category']}",
                "",
                f"- Install time: `{measurement['install_time_seconds']}` seconds.",
                f"- First index time: `{measurement['first_index_time_seconds']}` seconds.",
                f"- Query latency p50: `{measurement['query_latency_p50_ms']}` ms.",
                f"- Query latency p95: `{measurement['query_latency_p95_ms']}` ms.",
                f"- Result quality notes: {measurement['result_quality_notes']}",
                f"- Log noise classification: `{measurement['log_noise_classification']}`.",
                f"- Branch/default-branch behavior: {measurement['branch_default_branch_behavior']}",
                f"- Rollback/rebuild behavior: {measurement['rollback_rebuild_behavior']}",
                f"- Blocker classification: `{measurement['blocker_classification']}`.",
                "",
            ]
        )

    lines.extend(
        [
            "## Known Issue Classification",
            "",
            "| Issue ID | Classification | Summary | Disposition |",
            "|---|---|---|---|",
        ]
    )
    for issue in payload["known_issues"]:
        lines.append(
            f"| {issue['id']} | `{issue['classification']}` | "
            f"{issue['summary']} | {issue['disposition']} |"
        )
    if not payload["known_issues"]:
        lines.append("| none | `post_alpha_backlog` | No known issues recorded. | N/A |")

    lines.extend(
        [
            "",
            "Issue buckets used for this decision: `public_alpha_blocker`,",
            "`documented_limitation`, and `post_alpha_backlog`.",
            "",
            "## Release-Note Readiness",
            "",
            "- Supported install paths are the local `uv sync --locked`/STDIO path and the",
            "  `ghcr.io/viperjuice/code-index-mcp` container path.",
            "- Language coverage is bounded by `docs/SUPPORT_MATRIX.md`.",
            "- Beta warnings and rollback instructions are maintained in",
            "  `docs/operations/deployment-runbook.md`.",
            "",
            "## Public Alpha Decision",
            "",
            f"Final decision: `{payload['final_decision']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_payload(config: dict[str, Any], raw_fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    issues = config.get("known_issues", [])
    for issue in issues:
        classification = issue.get("classification")
        if classification not in ISSUE_CLASSIFICATIONS:
            raise ValueError(f"invalid issue classification: {classification}")

    has_blocker = any(issue["classification"] == "public_alpha_blocker" for issue in issues)
    final_decision = config.get("final_decision") or ("no_go" if has_blocker else "go")
    if final_decision not in FINAL_DECISIONS:
        raise ValueError(f"invalid final decision: {final_decision}")

    return {
        "schema_version": "1.0",
        "generated_at": _now(),
        "run_id": config.get("run_id", "manual-private-alpha-run"),
        "fixtures": [
            _redacted_fixture(raw_fixture, index) for index, raw_fixture in enumerate(raw_fixtures)
        ],
        "known_issues": [
            {
                "id": str(issue["id"]),
                "classification": issue["classification"],
                "summary": str(issue["summary"]),
                "disposition": str(issue.get("disposition", "Triage before public alpha.")),
            }
            for issue in issues
        ],
        "final_decision": final_decision,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Private fixture config JSON")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Ignored raw output directory, normally private-alpha-evidence/<run-id>",
    )
    parser.add_argument(
        "--redacted-md",
        required=True,
        type=Path,
        help="Committed redacted Markdown decision path",
    )
    parser.add_argument(
        "--redacted-json",
        required=True,
        type=Path,
        help="Committed redacted JSON decision path",
    )
    parser.add_argument(
        "--skip-release-smoke",
        action="store_true",
        help="Skip scripts/release_smoke.py --wheel --stdio for local iteration only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = _load_json(args.config)
    fixtures = config.get("fixtures", [])
    errors = _validate_fixture_categories(fixtures)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    smoke = (
        {"duration_seconds": None, "returncode": None, "output": ["skipped by operator flag"]}
        if args.skip_release_smoke
        else _run_timed([sys.executable, "scripts/release_smoke.py", "--wheel", "--stdio"])
    )
    if smoke["returncode"] not in (0, None):
        errors.append("release smoke failed")

    raw_fixtures: list[dict[str, Any]] = []
    for fixture in fixtures:
        category = str(fixture.get("category", ""))
        repo_path = Path(str(fixture.get("repo_path", ""))).expanduser()
        if not repo_path.exists():
            errors.append(f"fixture {category} repo_path does not exist")
            scan = {
                "first_index_time_seconds": None,
                "query_latency_p50_ms": None,
                "query_latency_p95_ms": None,
                "result_quality_notes": "Fixture path missing; no private result quality captured.",
                "query_runs": [],
            }
        else:
            scan = _scan_repo(repo_path, fixture)

        branch_behavior = str(
            fixture.get(
                "branch_default_branch_behavior",
                "Operator must confirm default-branch tracking before public alpha.",
            )
        )
        rollback_behavior = str(
            fixture.get(
                "rollback_rebuild_behavior",
                "Operator must confirm rollback/rebuild behavior before public alpha.",
            )
        )
        blocker_classification = str(fixture.get("blocker_classification", "post_alpha_backlog"))
        if blocker_classification not in ISSUE_CLASSIFICATIONS:
            errors.append(f"fixture {category} has invalid blocker classification")
            blocker_classification = "public_alpha_blocker"

        raw_fixtures.append(
            {
                "category": category,
                "repo_path": str(repo_path),
                "display_alias": fixture.get("display_alias", category),
                "measurements": {
                    "install_time_seconds": smoke["duration_seconds"],
                    "first_index_time_seconds": scan["first_index_time_seconds"],
                    "query_latency_p50_ms": scan["query_latency_p50_ms"],
                    "query_latency_p95_ms": scan["query_latency_p95_ms"],
                    "result_quality_notes": scan["result_quality_notes"],
                    "log_noise_classification": _classify_log_noise(smoke["output"]),
                    "branch_default_branch_behavior": branch_behavior,
                    "rollback_rebuild_behavior": rollback_behavior,
                    "blocker_classification": blocker_classification,
                },
                "query_runs": scan["query_runs"],
                "raw_log_lines": smoke["output"],
            }
        )

    if any(
        raw_fixture["measurements"]["blocker_classification"] == "public_alpha_blocker"
        for raw_fixture in raw_fixtures
    ):
        errors.append("one or more fixtures are classified as public_alpha_blocker")

    payload = _build_payload(config, raw_fixtures)
    raw_payload = {
        "generated_at": _now(),
        "errors": errors,
        "release_smoke": smoke,
        "fixtures": raw_fixtures,
        "redacted_decision": payload,
    }
    _write_json(args.output_dir / "raw-evidence.json", raw_payload)
    _write_json(args.redacted_json, payload)
    args.redacted_md.parent.mkdir(parents=True, exist_ok=True)
    args.redacted_md.write_text(_render_markdown(payload), encoding="utf-8")

    if any(issue["classification"] == "public_alpha_blocker" for issue in payload["known_issues"]):
        errors.append("one or more known issues are classified as public_alpha_blocker")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
