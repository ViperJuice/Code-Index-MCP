import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server.indexing.github_issues import (
    GitHubIssueFetchOptions,
    extract_issue_learnings,
    fetch_github_issues,
    issue_history_dedupe_key,
    normalize_github_issue,
)


def _fixture(name: str) -> dict:
    path = Path("tests/fixtures/github_issues") / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_fetch_github_issues_uses_repo_labels_date_window_state_and_safe_env(monkeypatch):
    recorded = {}

    def _fake_run(command, **kwargs):
        recorded["command"] = command
        recorded["env"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(
        "mcp_server.indexing.github_issues.get_command_availability",
        lambda _command: SimpleNamespace(
            available=True,
            remediation="ok",
            resolved_path="/usr/bin/gh",
        ),
    )
    monkeypatch.setattr("mcp_server.indexing.github_issues.subprocess.run", _fake_run)

    fetch_github_issues(
        GitHubIssueFetchOptions(
            repo="owner/repo",
            labels=("phase-complete", "reflection"),
            since="2026-07-01",
            until="2026-07-06",
            state="closed",
            include_body_learnings=True,
        )
    )

    command = recorded["command"]
    assert command[:5] == ["gh", "issue", "list", "--repo", "owner/repo"]
    assert "--label" in command
    assert command.count("--label") == 2
    assert "--state" in command and "closed" in command
    assert "--search" in command
    assert "updated:>=2026-07-01 updated:<=2026-07-06" in command
    assert "body" in command[command.index("--json") + 1]
    assert "PATH" in recorded["env"]


def test_fetch_github_issues_nonzero_exit_raises_metadata_only_error(monkeypatch):
    monkeypatch.setattr(
        "mcp_server.indexing.github_issues.get_command_availability",
        lambda _command: SimpleNamespace(
            available=True,
            remediation="ok",
            resolved_path="/usr/bin/gh",
        ),
    )
    monkeypatch.setattr(
        "mcp_server.indexing.github_issues.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="authentication required",
        ),
    )

    with pytest.raises(RuntimeError, match="authentication required"):
        fetch_github_issues(GitHubIssueFetchOptions(repo="owner/repo"))


def test_normalize_github_issue_uses_title_summary_without_persisting_raw_body():
    record = normalize_github_issue(_fixture("retrospective"), repo="owner/repo")

    assert record["type"] == "retrospective"
    assert record["summary"] == "Retrospective on history indexing"
    assert record["labels"] == ["retrospective"]
    assert "body" not in record
    assert record["learnings"] == []


def test_normalize_github_issue_extracts_body_learnings_only_when_explicit():
    raw_issue = _fixture("phase_complete")

    without_body = normalize_github_issue(raw_issue, repo="owner/repo", include_body_learnings=False)
    with_body = normalize_github_issue(raw_issue, repo="owner/repo", include_body_learnings=True)

    assert without_body["learnings"] == []
    assert with_body["learnings"] == ["Keep metadata generic", "Preserve legacy shape"]


def test_extract_issue_learnings_handles_direct_and_bullet_forms():
    body = "Learning: First\n\nLearnings:\n- Second\n- Third\n"

    assert extract_issue_learnings(body) == ["First", "Second", "Third"]


def test_issue_history_dedupe_key_is_stable_for_same_normalized_record():
    record = normalize_github_issue(_fixture("reflection"), repo="owner/repo", include_body_learnings=True)

    assert issue_history_dedupe_key(record) == issue_history_dedupe_key(dict(record))  # type: ignore[arg-type]
