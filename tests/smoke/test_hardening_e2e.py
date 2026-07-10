"""Contract tests for the HARDVERIFY runtime evidence reducer."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import hardening_e2e


def test_group_manifest_covers_every_hardening_runtime_contract() -> None:
    manifest = "\n".join(
        item for group in hardening_e2e.GROUPS for item in (group.name, *group.targets)
    )

    for required in (
        "test_mcpbase_stdio_smoke.py",
        "test_mcpeval_sdk_surface.py",
        "test_secondary_tool_readiness_smoke.py",
        "test_multi_repo_production_matrix.py",
        "test_unregistered_repository_refuses_secondary_tools",
        "test_classifies_missing_index",
        "test_classifies_corrupt_sqlite",
        "test_staged_rebuild_bootstraps_missing_index",
        "test_staged_rebuild_quarantines_corrupt_bytes_without_reopening_them",
        "test_status_read_does_not_allocate_plugins",
        "test_worker_limit_evicts_deterministic_lru",
        "test_repo_eviction_and_shutdown_close_every_adapter_once",
        "test_handshake.py",
        "test_parent_signal_leaves_no_live_sandbox_worker",
    ):
        assert required in manifest

    sigterm = next(
        group for group in hardening_e2e.GROUPS if group.name == "sigterm-worker-cleanup"
    )
    assert sigterm.marker is None


def test_run_group_records_only_metadata_summary(monkeypatch) -> None:
    completed = SimpleNamespace(
        returncode=0,
        stdout="1 passed in 0.12s\nsecret-looking application log that must not survive",
        stderr="",
    )
    monkeypatch.setattr(hardening_e2e.subprocess, "run", lambda *_args, **_kwargs: completed)
    ticks = iter((100.0, 100.125))
    monkeypatch.setattr(hardening_e2e.time, "monotonic", lambda: next(ticks))

    result = hardening_e2e.run_group(hardening_e2e.GROUPS[0])

    assert result["status"] == "passed"
    assert result["summary"] == "1 passed"
    assert result["duration_seconds"] == 0.125
    assert "application log" not in json.dumps(result)


def test_run_stops_after_failure(monkeypatch) -> None:
    results = iter(
        [
            {"name": "one", "status": "passed", "returncode": 0, "summary": "1 passed"},
            {"name": "two", "status": "failed", "returncode": 1, "summary": "1 failed"},
        ]
    )
    monkeypatch.setattr(hardening_e2e, "run_group", lambda _group: next(results))
    groups = (
        hardening_e2e.VerificationGroup("one", ("one.py",)),
        hardening_e2e.VerificationGroup("two", ("two.py",)),
        hardening_e2e.VerificationGroup("three", ("three.py",)),
    )

    evidence = hardening_e2e.run(groups)

    assert evidence["passed"] is False
    assert evidence["groups_expected"] == 3
    assert evidence["groups_completed"] == 2


def test_main_writes_json_report(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "runtime.json"
    evidence = {
        "schema": "hardverify_runtime.v1",
        "passed": True,
        "groups_expected": 0,
        "groups_completed": 0,
        "groups": [],
    }
    monkeypatch.setattr(hardening_e2e, "run", lambda: evidence)
    monkeypatch.setattr(
        hardening_e2e.sys,
        "argv",
        ["hardening_e2e.py", "--json-output", str(output)],
    )

    assert hardening_e2e.main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == evidence
