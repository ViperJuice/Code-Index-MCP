"""Run the frozen HARDVERIFY runtime evidence groups without exposing test logs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

EVIDENCE_SCHEMA = "hardverify_runtime.v1"
REPO = Path(__file__).resolve().parents[1]
SUMMARY_RE = re.compile(r"(?P<summary>\d+ passed(?:, \d+ skipped)?(?:, \d+ deselected)?)")


@dataclass(frozen=True)
class VerificationGroup:
    """One independently reportable pytest evidence group."""

    name: str
    targets: tuple[str, ...]
    marker: str | None = None


GROUPS = (
    VerificationGroup(
        "stdio-sdk-and-secondary-tools",
        (
            "tests/smoke/test_mcpbase_stdio_smoke.py",
            "tests/smoke/test_mcpeval_sdk_surface.py",
            "tests/smoke/test_secondary_tool_readiness_smoke.py",
        ),
    ),
    VerificationGroup(
        "repository-isolation-and-refusal",
        (
            "tests/test_multi_repo_production_matrix.py",
            "tests/test_multi_repo_failure_matrix.py::test_unregistered_repository_refuses_secondary_tools",
        ),
    ),
    VerificationGroup(
        "readiness-and-recovery",
        (
            "tests/test_repository_readiness.py::test_classifies_missing_index",
            "tests/test_repository_readiness.py::test_classifies_corrupt_sqlite",
            "tests/test_git_index_manager.py::test_staged_rebuild_bootstraps_missing_index",
            "tests/test_git_index_manager.py::test_staged_rebuild_quarantines_corrupt_bytes_without_reopening_them",
        ),
    ),
    VerificationGroup(
        "worker-lifecycle",
        (
            "tests/test_plugin_set_registry.py::TestPluginsFor::test_status_read_does_not_allocate_plugins",
            "tests/test_plugin_set_registry.py::TestPluginsForFile::test_allocates_only_languages_requested_for_repo",
            "tests/test_memory_aware_manager.py::TestWorkerLifecycleGovernance::test_worker_limit_evicts_deterministic_lru",
            "tests/test_memory_aware_manager.py::TestWorkerLifecycleGovernance::test_idle_expiry_closes_adapter",
            "tests/test_memory_aware_manager.py::TestWorkerLifecycleGovernance::test_repo_eviction_and_shutdown_close_every_adapter_once",
        ),
    ),
    VerificationGroup(
        "stdio-handshake",
        (
            "tests/test_handshake.py",
            "tests/security/test_mcpauth_boundary.py",
            "tests/test_mcpauth_stdio_contract.py",
        ),
    ),
    VerificationGroup(
        "sigterm-worker-cleanup",
        (
            "tests/integration/test_sigterm_shutdown.py::test_parent_signal_leaves_no_live_sandbox_worker",
        ),
    ),
)


def _summary(output: str) -> str:
    matches = list(SUMMARY_RE.finditer(output))
    return matches[-1].group("summary") if matches else "summary unavailable"


def run_group(group: VerificationGroup) -> dict[str, object]:
    """Run one group and return metadata-only evidence."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        *group.targets,
        "-q",
        "--no-cov",
        "--benchmark-skip",
    ]
    if group.marker is not None:
        command.extend(["-m", group.marker])

    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = round(time.monotonic() - started, 3)
    combined = f"{completed.stdout}\n{completed.stderr}"
    return {
        "name": group.name,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "duration_seconds": duration,
        "summary": _summary(combined),
        "target_count": len(group.targets),
    }


def run(groups: Sequence[VerificationGroup] = GROUPS) -> dict[str, object]:
    """Run groups in order and stop after the first failure."""
    results: list[dict[str, object]] = []
    for group in groups:
        result = run_group(group)
        results.append(result)
        print(f"group={group.name} status={result['status']} " f"summary={result['summary']}")
        if result["status"] != "passed":
            break

    passed = len(results) == len(groups) and all(result["status"] == "passed" for result in results)
    return {
        "schema": EVIDENCE_SCHEMA,
        "passed": passed,
        "groups_expected": len(groups),
        "groups_completed": len(results),
        "groups": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--list-groups", action="store_true")
    args = parser.parse_args()

    if args.list_groups:
        for group in GROUPS:
            print(group.name)
        return 0

    evidence = run()
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
