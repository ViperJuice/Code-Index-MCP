"""Delta artifact chain resolution helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def resolve_delta_chain(
    artifacts: List[Dict[str, Any]],
    target_commit: str,
) -> List[Dict[str, Any]]:
    """Resolve a full+delta chain for target_commit.

    Returns ordered list [full_artifact, delta_1, ..., delta_n].
    Raises ValueError if a valid chain cannot be resolved.
    """
    by_target = {
        a.get("target_commit"): a
        for a in artifacts
        if a.get("artifact_type") == "delta" and a.get("target_commit")
    }
    full_by_commit = {
        a.get("target_commit") or a.get("commit"): a
        for a in artifacts
        if a.get("artifact_type") == "full"
    }

    chain: List[Dict[str, Any]] = []
    seen = set()
    cursor = target_commit

    while cursor not in full_by_commit:
        if cursor in seen:
            raise ValueError("Delta artifact chain contains a cycle")
        seen.add(cursor)

        delta = by_target.get(cursor)
        if not delta:
            raise ValueError(f"No delta artifact found targeting commit {cursor}")
        chain.append(delta)
        base = delta.get("base_commit")
        if not base:
            raise ValueError(f"Delta artifact missing base_commit for target {cursor}")
        cursor = base

    full = full_by_commit[cursor]
    chain.reverse()
    return [full] + chain


def select_best_target_commit(artifacts: List[Dict[str, Any]]) -> Optional[str]:
    """Select newest target commit among full/delta artifacts."""
    sorted_artifacts = sorted(
        artifacts,
        key=lambda a: a.get("created_at", ""),
        reverse=True,
    )
    for artifact in sorted_artifacts:
        if artifact.get("target_commit"):
            return artifact["target_commit"]
        if artifact.get("commit"):
            return artifact["commit"]
    return None
