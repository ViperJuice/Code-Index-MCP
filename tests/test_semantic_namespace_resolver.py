"""Tests for semantic namespace resolution contract."""

import re

from mcp_server.artifacts.semantic_namespace import SemanticNamespaceResolver


def test_derive_repo_hash_is_deterministic():
    resolver = SemanticNamespaceResolver()
    repo_identifier = "git@github.com:acme/example-repo.git"

    h1 = resolver.derive_repo_hash(repo_identifier)
    h2 = resolver.derive_repo_hash(repo_identifier)

    assert h1 == h2
    assert re.fullmatch(r"[0-9a-f]{12}", h1)


def test_derive_lineage_id_is_deterministic_for_branch_and_commit():
    resolver = SemanticNamespaceResolver()

    l1 = resolver.derive_lineage_id("feature/semantic-v2", "ABCDEF1234567890")
    l2 = resolver.derive_lineage_id("feature/semantic-v2", "abcdef1234567890")

    assert l1 == l2
    assert re.fullmatch(r"[0-9a-f]{12}", l1)


def test_derive_lineage_id_defaults_to_workspace_when_empty():
    resolver = SemanticNamespaceResolver()

    lineage_id = resolver.derive_lineage_id(None, None)

    assert lineage_id == "workspace"


def test_sanitize_profile_id_replaces_invalid_characters():
    resolver = SemanticNamespaceResolver()

    sanitized = resolver.sanitize_profile_id("  Commercial/High_V2@2026  ")

    assert sanitized == "commercial-high-v2-2026"


def test_resolve_collection_name_uses_contract_format():
    resolver = SemanticNamespaceResolver()

    collection_name = resolver.resolve_collection_name(
        repo_identifier="https://github.com/acme/example.git",
        profile_id="Commercial High",
        lineage_id="main@abc123",
    )

    assert re.fullmatch(
        r"ci__[0-9a-f]{12}__[a-z0-9-]+__[a-z0-9-]+",
        collection_name,
    )
