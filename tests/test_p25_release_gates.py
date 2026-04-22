"""P25 release gate workflow contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).parent.parent

REQUIRED_GATES = {
    "Alpha Gate - Dependency Sync",
    "Alpha Gate - Format And Lint",
    "Alpha Gate - Unit And Release Smoke",
    "Alpha Gate - Integration Smoke",
    "Alpha Gate - Docker Build And Smoke",
    "Alpha Gate - Docs Truth",
    "Alpha Gate - Required Gates Passed",
}

MAIN_CI_REQUIRED_JOB_IDS = {
    "alpha-format-lint",
    "alpha-unit-release-smoke",
    "alpha-integration-smoke",
    "alpha-docs-truth",
}


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def _load_workflow(relative_path: str) -> dict[str, Any]:
    with (REPO / relative_path).open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=yaml.BaseLoader)


def _jobs(relative_path: str) -> dict[str, Any]:
    return _load_workflow(relative_path)["jobs"]


def _job_names(*workflow_paths: str) -> set[str]:
    names: set[str] = set()
    for workflow_path in workflow_paths:
        for job in _jobs(workflow_path).values():
            names.add(job["name"])
    return names


def _needs(job: dict[str, Any]) -> set[str]:
    raw = job.get("needs", [])
    if isinstance(raw, str):
        return {raw}
    return set(raw)


def _is_true(value: Any) -> bool:
    return str(value).lower() == "true"


def test_required_alpha_gate_names_are_exposed():
    names = _job_names(
        ".github/workflows/ci-cd-pipeline.yml",
        ".github/workflows/lockfile-check.yml",
        ".github/workflows/container-registry.yml",
    )

    assert REQUIRED_GATES <= names


def test_main_ci_required_aggregator_depends_on_blocking_gates():
    jobs = _jobs(".github/workflows/ci-cd-pipeline.yml")
    aggregator = jobs["alpha-required-gates-passed"]

    assert aggregator["name"] == "Alpha Gate - Required Gates Passed"
    assert _needs(aggregator) == MAIN_CI_REQUIRED_JOB_IDS
    assert "continue-on-error" not in aggregator

    for job_id in MAIN_CI_REQUIRED_JOB_IDS:
        job = jobs[job_id]
        assert job["name"].startswith("Alpha Gate - ")
        assert "continue-on-error" not in job


def test_informational_jobs_are_named_and_excluded_from_required_aggregator():
    for workflow_path in (
        ".github/workflows/ci-cd-pipeline.yml",
        ".github/workflows/container-registry.yml",
    ):
        jobs = _jobs(workflow_path)
        aggregator_needs = _needs(jobs.get("alpha-required-gates-passed", {}))
        for job_id, job in jobs.items():
            if job["name"].startswith("Informational - "):
                assert job_id not in aggregator_needs
                assert _is_true(job.get("continue-on-error")) or (
                    "schedule" in str(job.get("if", ""))
                    or "workflow_dispatch" in str(job.get("if", ""))
                    or "pull_request" in str(job.get("if", ""))
                    or "refs/tags/v" in str(job.get("if", ""))
                )
            elif "continue-on-error" in job:
                assert job["name"].startswith("Informational - ")


def test_lockfile_workflow_is_always_visible_dependency_gate():
    workflow = _load_workflow(".github/workflows/lockfile-check.yml")
    job = workflow["jobs"]["alpha-dependency-sync"]

    assert job["name"] == "Alpha Gate - Dependency Sync"
    assert "continue-on-error" not in job
    assert "paths" not in workflow["on"]["push"]
    assert "paths" not in workflow["on"]["pull_request"]
    assert "make alpha-dependency-sync" in _read(".github/workflows/lockfile-check.yml")


def test_container_alpha_gate_builds_and_smokes_without_push():
    jobs = _jobs(".github/workflows/container-registry.yml")
    gate = jobs["alpha-docker-build-smoke"]
    workflow_text = _read(".github/workflows/container-registry.yml")

    assert gate["name"] == "Alpha Gate - Docker Build And Smoke"
    assert "continue-on-error" not in gate
    assert "make release-smoke-container" in workflow_text
    assert "push: false" in workflow_text


def test_release_automation_refuses_before_mutating_or_publishing():
    jobs = _jobs(".github/workflows/release-automation.yml")
    workflow_text = _read(".github/workflows/release-automation.yml")

    assert jobs["preflight-release-gates"]["name"] == "Preflight Release Gates"
    assert "make alpha-release-gates" in workflow_text
    assert _needs(jobs["prepare-release"]) == {"preflight-release-gates"}
    assert "default: 'custom'" in workflow_text
    assert "Prerelease tags must use release_type=custom" in workflow_text

    downstream = {
        "run-tests",
        "build-artifacts",
        "create-release",
        "merge-release",
        "post-release",
    }
    for job_id in downstream:
        assert "preflight-release-gates" in _needs(jobs[job_id]) or (
            "prepare-release" in _needs(jobs[job_id])
            or "run-tests" in _needs(jobs[job_id])
            or "build-artifacts" in _needs(jobs[job_id])
            or "create-release" in _needs(jobs[job_id])
        )


def test_release_automation_marks_prerelease_and_keeps_latest_stable_only():
    workflow_text = _read(".github/workflows/release-automation.yml")

    assert "is_prerelease: ${{ steps.release_flags.outputs.is_prerelease }}" in workflow_text
    assert "prerelease: ${{ needs.prepare-release.outputs.is_prerelease }}" in workflow_text
    assert "tags: ${{ needs.prepare-release.outputs.docker_tags }}" in workflow_text
    assert 'if [ "$IS_PRERELEASE" = "false" ]; then' in workflow_text
    assert "ghcr.io/viperjuice/code-index-mcp:latest" in workflow_text
    assert 'find docs -name "*.md" -exec sed -i' not in workflow_text


def test_attestation_private_alpha_fallback_is_explicit():
    surfaces = "\n".join(
        [
            _read(".github/workflows/ci-cd-pipeline.yml"),
            _read("docs/operations/user-action-runbook.md"),
        ]
    )

    assert "ATTESTATION_GH_TOKEN" in surfaces
    assert "private-alpha" in surfaces
    assert "informational skipped/warn" in surfaces
