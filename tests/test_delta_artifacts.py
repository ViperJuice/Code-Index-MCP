"""Tests for delta artifact creation and application."""

from pathlib import Path

from mcp_server.artifacts.delta_artifacts import (
    apply_delta_archive,
    build_delta_archive,
    create_delta_manifest,
    validate_delta_manifest,
)


def test_delta_manifest_and_apply_roundtrip(tmp_path: Path):
    """Delta archive should transform base directory into target directory."""
    base_dir = tmp_path / "base"
    target_dir = tmp_path / "target"
    apply_dir = tmp_path / "apply"

    base_dir.mkdir()
    target_dir.mkdir()
    apply_dir.mkdir()

    (base_dir / "a.txt").write_text("alpha\n")
    (base_dir / "b.txt").write_text("bravo\n")

    (target_dir / "a.txt").write_text("alpha-updated\n")
    (target_dir / "c.txt").write_text("charlie\n")

    # Start apply dir as a copy of base state
    (apply_dir / "a.txt").write_text("alpha\n")
    (apply_dir / "b.txt").write_text("bravo\n")

    manifest = create_delta_manifest(base_dir, target_dir, "base1234", "target5678")
    archive_path = tmp_path / "delta.tar.gz"
    build_delta_archive(manifest, target_dir, archive_path)

    apply_delta_archive(apply_dir, archive_path)

    assert (apply_dir / "a.txt").read_text() == "alpha-updated\n"
    assert (apply_dir / "c.txt").read_text() == "charlie\n"
    assert not (apply_dir / "b.txt").exists()


def test_validate_delta_manifest_rejects_unsafe_path():
    payload = {
        "delta_schema_version": "1",
        "base_commit": "aaaa",
        "target_commit": "bbbb",
        "checksums": {},
        "operations": [{"op": "modify", "path": "../../etc/passwd"}],
    }
    err = validate_delta_manifest(payload)
    assert err is not None
    assert "unsafe operation path" in err
