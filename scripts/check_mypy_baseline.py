#!/usr/bin/env python3
"""Enforce a non-growing, module-and-code keyed mypy error baseline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "mypy_baseline.v1"
ERROR_RE = re.compile(
    r"^(?P<module>.+?\.py):(?P<line>\d+)(?::\d+)?: error: .+  " r"\[(?P<code>[a-z0-9-]+)\]$"
)
SUMMARY_RE = re.compile(r"^Found (?P<count>\d+) errors? in ")
SUCCESS_RE = re.compile(r"^Success: no issues found in ")


class BaselineError(ValueError):
    """Raised when mypy output or baseline data is malformed."""


def parse_mypy_output(output: str) -> dict[str, dict[str, int]]:
    """Parse canonical mypy output into module/code counts."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    summary_count: int | None = None
    success_seen = False

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = ERROR_RE.match(line)
        if match:
            module = Path(match.group("module")).as_posix().removeprefix("./")
            counts[module][match.group("code")] += 1
            continue
        summary = SUMMARY_RE.match(line)
        if summary:
            summary_count = int(summary.group("count"))
            continue
        if SUCCESS_RE.match(line):
            success_seen = True
            continue
        if ": error:" in line:
            raise BaselineError(f"Malformed mypy error line: {line}")

    parsed_count = sum(sum(module_counts.values()) for module_counts in counts.values())
    if summary_count is not None and summary_count != parsed_count:
        raise BaselineError(
            f"Mypy summary reports {summary_count} errors but parsed {parsed_count}"
        )
    if summary_count is None and not success_seen:
        raise BaselineError("Mypy output has neither an error summary nor a success summary")
    if success_seen and parsed_count:
        raise BaselineError("Mypy output reports success and errors in the same result")

    return {
        module: dict(sorted(module_counts.items()))
        for module, module_counts in sorted(counts.items())
    }


def build_baseline(counts: dict[str, dict[str, int]], command: Iterable[str]) -> dict[str, Any]:
    """Build the persisted baseline document."""
    return {
        "schema_version": SCHEMA_VERSION,
        "command": list(command),
        "total_errors": sum(sum(codes.values()) for codes in counts.values()),
        "counts": counts,
    }


def load_baseline(path: Path) -> dict[str, Any]:
    """Load and validate a persisted baseline document."""
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"Cannot load baseline {path}: {exc}") from exc
    if not isinstance(baseline, dict) or baseline.get("schema_version") != SCHEMA_VERSION:
        raise BaselineError(f"Baseline must use schema_version {SCHEMA_VERSION}")

    counts = baseline.get("counts")
    if not isinstance(counts, dict):
        raise BaselineError("Baseline counts must be an object")
    for module, codes in counts.items():
        if not isinstance(module, str) or not isinstance(codes, dict) or not codes:
            raise BaselineError(f"Invalid baseline module entry: {module!r}")
        for code, count in codes.items():
            if not isinstance(code, str) or not isinstance(count, int) or count < 1:
                raise BaselineError(f"Invalid baseline count for {module} [{code}]")

    expected_total = sum(sum(codes.values()) for codes in counts.values())
    if baseline.get("total_errors") != expected_total:
        raise BaselineError(
            f"Baseline total_errors must equal the enumerated count {expected_total}"
        )
    return baseline


def compare_counts(
    baseline_counts: dict[str, dict[str, int]],
    current_counts: dict[str, dict[str, int]],
) -> list[str]:
    """Return ratchet violations; shrinkage is intentionally accepted."""
    violations: list[str] = []
    for module, current_codes in sorted(current_counts.items()):
        baseline_codes = baseline_counts.get(module)
        if baseline_codes is None:
            violations.append(f"new failing module: {module}")
            continue
        for code, current_count in sorted(current_codes.items()):
            baseline_count = baseline_codes.get(code)
            if baseline_count is None:
                violations.append(f"new error code: {module} [{code}] ({current_count})")
            elif current_count > baseline_count:
                violations.append(
                    f"error count grew: {module} [{code}] " f"{baseline_count} -> {current_count}"
                )
    return violations


def find_ignore_errors(config_path: Path) -> list[str]:
    """Reject project-wide or override-based mypy ignore_errors switches."""
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise BaselineError(f"Cannot load mypy config {config_path}: {exc}") from exc

    mypy = config.get("tool", {}).get("mypy", {})
    if not isinstance(mypy, dict):
        raise BaselineError("[tool.mypy] must be a table")

    violations = []
    if mypy.get("ignore_errors") is True:
        violations.append("project-level [tool.mypy].ignore_errors=true is forbidden")
    overrides = mypy.get("overrides", [])
    if overrides and not isinstance(overrides, list):
        raise BaselineError("[[tool.mypy.overrides]] must be an array of tables")
    for index, override in enumerate(overrides):
        if isinstance(override, dict) and override.get("ignore_errors") is True:
            violations.append(
                f"mypy override {index} sets ignore_errors=true; fix or baseline errors instead"
            )
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("config/mypy_baseline.json"))
    parser.add_argument("--config", type=Path, default=Path("pyproject.toml"))
    parser.add_argument(
        "--output", type=Path, help="Read existing mypy output instead of running it"
    )
    parser.add_argument("--write-baseline", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    command = ["python", "-m", "mypy", "mcp_server"]
    if args.output:
        output = args.output.read_text(encoding="utf-8")
    else:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "mcp_server"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode not in {0, 1}:
            print(f"mypy failed with exit code {result.returncode}", file=sys.stderr)
            return 2

    try:
        counts = parse_mypy_output(output)
        config_violations = find_ignore_errors(args.config)
        if config_violations:
            for violation in config_violations:
                print(f"mypy baseline violation: {violation}", file=sys.stderr)
            return 1

        if args.write_baseline:
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            args.baseline.write_text(
                json.dumps(build_baseline(counts, command), indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"Wrote mypy baseline with {build_baseline(counts, command)['total_errors']} errors"
            )
            return 0

        baseline = load_baseline(args.baseline)
        violations = compare_counts(baseline["counts"], counts)
    except (BaselineError, OSError) as exc:
        print(f"mypy baseline error: {exc}", file=sys.stderr)
        return 2

    if violations:
        for violation in violations:
            print(f"mypy baseline violation: {violation}", file=sys.stderr)
        return 1

    current_total = sum(sum(codes.values()) for codes in counts.values())
    print(
        f"Mypy ratchet passed: {current_total} current errors "
        f"<= {baseline['total_errors']} enumerated baseline errors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
