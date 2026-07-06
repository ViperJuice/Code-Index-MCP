from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from mcp_server.indexing.source_metadata import HistoryIssueRecord
from mcp_server.utils.subprocess_env import get_command_availability, get_full_env

_JSON_FIELDS = [
    "number",
    "title",
    "labels",
    "state",
    "createdAt",
    "updatedAt",
    "closedAt",
    "url",
]


@dataclass(frozen=True)
class GitHubIssueFetchOptions:
    repo: str
    labels: tuple[str, ...] = ()
    since: str | None = None
    until: str | None = None
    state: str = "all"
    include_body_learnings: bool = False
    limit: int = 200


def extract_issue_learnings(body: str | None) -> list[str]:
    if not body:
        return []

    learnings: list[str] = []
    collecting_bullets = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        lowered = line.lower().rstrip(":")
        if not line:
            collecting_bullets = False
            continue
        direct_match = re.match(r"^learnings?:\s*(.+)$", line, flags=re.IGNORECASE)
        if direct_match:
            learnings.append(direct_match.group(1).strip())
            collecting_bullets = False
            continue
        if lowered in {"learnings", "key learnings", "lessons learned"}:
            collecting_bullets = True
            continue
        if collecting_bullets and line[:1] in {"-", "*"}:
            bullet = line[1:].strip()
            if bullet:
                learnings.append(bullet)
            continue
        collecting_bullets = False

    normalized = {entry.strip() for entry in learnings if entry.strip()}
    return sorted(normalized, key=str.lower)


def normalize_github_issue(
    issue: dict[str, Any],
    *,
    repo: str,
    include_body_learnings: bool = False,
) -> HistoryIssueRecord:
    label_names = sorted(
        {
            str(label.get("name", "")).strip().lower()
            for label in issue.get("labels") or []
            if isinstance(label, dict) and str(label.get("name", "")).strip()
        }
    )
    title = str(issue["title"]).strip()
    inferred_type = _infer_issue_type(label_names, title)
    learnings = (
        extract_issue_learnings(str(issue.get("body") or ""))
        if include_body_learnings
        else []
    )
    normalized: HistoryIssueRecord = {
        "source_type": "history",
        "type": inferred_type,
        "repo": repo.strip().lower(),
        "number": int(issue["number"]),
        "title": title,
        "labels": label_names,
        "state": str(issue["state"]).strip().lower(),
        "created_at": str(issue["createdAt"]).strip(),
        "updated_at": str(issue["updatedAt"]).strip(),
        "url": str(issue["url"]).strip(),
        "summary": title,
        "learnings": learnings,
    }
    closed_at = issue.get("closedAt")
    if closed_at not in (None, ""):
        normalized["closed_at"] = str(closed_at).strip()
    return normalized


def issue_history_dedupe_key(record: HistoryIssueRecord) -> str:
    learning_hash = hashlib.sha256("\n".join(record["learnings"]).encode("utf-8")).hexdigest()[:16]
    return (
        f"{record['repo']}#{record['number']}:"
        f"{record['type']}:{record['updated_at']}:{learning_hash}"
    )


def fetch_github_issues(options: GitHubIssueFetchOptions) -> list[dict[str, Any]]:
    availability = get_command_availability("gh")
    if not availability.available:
        raise RuntimeError(availability.remediation)

    fields = list(_JSON_FIELDS)
    if options.include_body_learnings:
        fields.append("body")

    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        options.repo,
        "--state",
        options.state,
        "--limit",
        str(options.limit),
        "--json",
        ",".join(fields),
    ]
    for label in options.labels:
        command.extend(["--label", label])

    search_terms = []
    if options.since:
        search_terms.append(f"updated:>={options.since}")
    if options.until:
        search_terms.append(f"updated:<={options.until}")
    if search_terms:
        command.extend(["--search", " ".join(search_terms)])

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=get_full_env(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "gh issue list failed"
        raise RuntimeError(stderr)

    payload = json.loads(completed.stdout or "[]")
    if not isinstance(payload, list):
        raise RuntimeError("gh issue list returned a non-list payload")
    return [item for item in payload if isinstance(item, dict)]


def _infer_issue_type(labels: list[str], title: str) -> str:
    normalized_title = title.strip().lower()
    if any(label in {"phase-complete", "phase complete", "phase_complete"} for label in labels):
        return "phase_complete"
    if "phase complete" in normalized_title:
        return "phase_complete"
    if any("reflection" == label for label in labels) or "reflection" in normalized_title:
        return "reflection"
    if any("retrospective" == label for label in labels) or "retrospective" in normalized_title:
        return "retrospective"
    return "issue"
