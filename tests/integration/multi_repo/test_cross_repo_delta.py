"""
SL-1.2: Cross-repo delta chain resolution.

repo-A publishes a delta whose base_commit matches repo-B's full artifact.
resolve_delta_chain must return the full chain [full_B, delta_A].
"""

import pytest

from mcp_server.artifacts.delta_resolver import resolve_delta_chain

COMMIT_B_FULL = "aaaa0000bbbb0001"  # repo-B's baseline commit
COMMIT_A_TARGET = "cccc0000dddd0002"  # repo-A's new commit built on top


def test_cross_repo_delta_chain_resolution():
    """
    Delta from repo-A refers to a base_commit that is repo-B's full artifact commit.
    resolve_delta_chain must successfully walk the chain and return [full, delta].
    """
    # repo-B's full artifact anchors the chain
    full_artifact_b = {
        "artifact_type": "full",
        "repo_id": "repo-b-id",
        "target_commit": COMMIT_B_FULL,
        "created_at": "2026-04-20T00:00:00Z",
    }

    # repo-A's delta: depends on repo-B's commit as its base
    delta_artifact_a = {
        "artifact_type": "delta",
        "repo_id": "repo-a-id",
        "target_commit": COMMIT_A_TARGET,
        "base_commit": COMMIT_B_FULL,  # cross-repo dependency
        "created_at": "2026-04-20T01:00:00Z",
    }

    artifacts = [full_artifact_b, delta_artifact_a]
    chain = resolve_delta_chain(artifacts, target_commit=COMMIT_A_TARGET)

    assert len(chain) == 2, f"Expected chain length 2, got {len(chain)}: {chain}"
    assert chain[0]["artifact_type"] == "full", "First element must be the full artifact"
    assert chain[0]["repo_id"] == "repo-b-id", "Full artifact must be from repo-B"
    assert chain[1]["artifact_type"] == "delta", "Second element must be the delta"
    assert chain[1]["repo_id"] == "repo-a-id", "Delta must be from repo-A"
    assert (
        chain[1]["base_commit"] == COMMIT_B_FULL
    ), "Delta base_commit must reference repo-B's commit"


def test_cross_repo_delta_chain_contains_repo_b_base():
    """
    Full artifact from repo-B is reachable at the base of the chain.
    """
    full_artifact_b = {
        "artifact_type": "full",
        "repo_id": "repo-b-id",
        "target_commit": COMMIT_B_FULL,
        "created_at": "2026-04-20T00:00:00Z",
    }
    delta_artifact_a = {
        "artifact_type": "delta",
        "repo_id": "repo-a-id",
        "target_commit": COMMIT_A_TARGET,
        "base_commit": COMMIT_B_FULL,
        "created_at": "2026-04-20T01:00:00Z",
    }

    chain = resolve_delta_chain([full_artifact_b, delta_artifact_a], COMMIT_A_TARGET)
    base_commits = {a.get("target_commit") for a in chain}
    assert (
        COMMIT_B_FULL in base_commits
    ), f"repo-B's base commit {COMMIT_B_FULL!r} must appear in the resolved chain"
