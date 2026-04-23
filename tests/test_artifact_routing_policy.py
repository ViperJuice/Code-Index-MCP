"""Tests for deterministic artifact routing policy."""

from mcp_server.artifacts.routing_policy import (
    ArtifactRoutingContext,
    ArtifactRoutingPolicy,
)


def test_public_small_routes_to_github_actions() -> None:
    policy = ArtifactRoutingPolicy(
        large_artifact_threshold_bytes=1024,
        s3_configured=True,
    )
    decision = policy.choose(
        ArtifactRoutingContext(
            repo_visibility="public",
            artifact_size_bytes=512,
            profile_type="standard",
        )
    )

    assert decision.provider == "github_actions"
    assert "public repository" in decision.explain()


def test_private_skips_unimplemented_s3_when_configured() -> None:
    policy = ArtifactRoutingPolicy(
        large_artifact_threshold_bytes=1024,
        s3_configured=True,
    )
    decision = policy.choose(
        ArtifactRoutingContext(
            repo_visibility="private",
            artifact_size_bytes=1,
            profile_type="standard",
        )
    )

    assert decision.provider == "local_fs"
    assert "s3 is configured but not implemented" in decision.explain()


def test_unimplemented_fallback_order_entries_are_skipped() -> None:
    policy = ArtifactRoutingPolicy(
        large_artifact_threshold_bytes=1024,
        s3_configured=False,
        fallback_order=("s3", "gcs", "github_actions"),
    )
    decision = policy.choose(
        ArtifactRoutingContext(
            repo_visibility="private",
            artifact_size_bytes=1,
            profile_type="standard",
        )
    )

    assert decision.provider == "github_actions"


def test_large_without_s3_falls_back_to_local_fs() -> None:
    policy = ArtifactRoutingPolicy(
        large_artifact_threshold_bytes=1024,
        s3_configured=False,
        fallback_order=("local_fs", "github_actions"),
    )
    decision = policy.choose(
        ArtifactRoutingContext(
            repo_visibility="public",
            artifact_size_bytes=2048,
            profile_type="standard",
        )
    )

    assert decision.provider == "local_fs"
    assert "s3 not configured" in decision.explain()


def test_explicit_override_wins() -> None:
    policy = ArtifactRoutingPolicy(
        large_artifact_threshold_bytes=1024,
        s3_configured=False,
    )
    decision = policy.choose(
        ArtifactRoutingContext(
            repo_visibility="private",
            artifact_size_bytes=2048,
            profile_type="sensitive",
            explicit_override="github_actions",
        )
    )

    assert decision.provider == "github_actions"
    assert "explicit override requested" in decision.explain()
