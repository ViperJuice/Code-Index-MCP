"""Artifact persistence lifecycle tests.

These tests validate create/extract behavior for commit artifacts,
delta generation/apply, and chain resolution semantics used for
default-branch and commit-targeted recovery.
"""

from pathlib import Path

from mcp_server.artifacts.commit_artifacts import CommitArtifactManager
from mcp_server.artifacts.delta_artifacts import (
    apply_delta_archive,
    build_delta_archive,
    create_delta_manifest,
)
from mcp_server.artifacts.delta_resolver import resolve_delta_chain


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_commit_artifact_create_extract_roundtrip(tmp_path: Path):
    manager = CommitArtifactManager(artifacts_dir=str(tmp_path / "artifacts"))

    index_dir = tmp_path / "index"
    _write(index_dir / "code_index.db", "db-bytes")
    _write(index_dir / "artifact-metadata.json", '{"ok": true}')

    artifact = manager.create_commit_artifact("repo", "abcdef123456", index_dir)
    assert artifact is not None
    assert artifact.exists()

    target_dir = tmp_path / "restore"
    restored = manager.extract_commit_artifact("repo", "abcdef123456", target_dir)
    assert restored is True
    assert (target_dir / "code_index.db").read_text(encoding="utf-8") == "db-bytes"


def test_delta_manifest_apply_roundtrip(tmp_path: Path):
    base = tmp_path / "base"
    target = tmp_path / "target"
    _write(base / "a.txt", "one")
    _write(base / "b.txt", "two")

    _write(target / "a.txt", "one-updated")
    _write(target / "c.txt", "three")

    manifest = create_delta_manifest(base, target, "commit-a", "commit-b")
    archive = build_delta_archive(manifest, target, tmp_path / "delta.tar.gz")

    apply_delta_archive(base, archive)

    assert (base / "a.txt").read_text(encoding="utf-8") == "one-updated"
    assert not (base / "b.txt").exists()
    assert (base / "c.txt").read_text(encoding="utf-8") == "three"


def test_delta_chain_resolution_for_default_branch_updates():
    artifacts = [
        {
            "artifact_type": "full",
            "target_commit": "main-a",
            "created_at": "2026-03-01T00:00:00Z",
            "id": 100,
        },
        {
            "artifact_type": "delta",
            "base_commit": "main-a",
            "target_commit": "main-b",
            "created_at": "2026-03-02T00:00:00Z",
            "id": 101,
        },
        {
            "artifact_type": "delta",
            "base_commit": "main-b",
            "target_commit": "main-c",
            "created_at": "2026-03-03T00:00:00Z",
            "id": 102,
        },
    ]

    chain = resolve_delta_chain(artifacts, target_commit="main-c")
    ids = [item["id"] for item in chain]
    assert ids == [100, 101, 102]
