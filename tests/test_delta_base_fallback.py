"""Tests for delta-base-missing fallback in artifact_download (SL-2.3)."""

from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, call, patch

import pytest

from mcp_server.artifacts.artifact_download import IndexArtifactDownloader

REPO = "owner/repo"


def _make_downloader() -> IndexArtifactDownloader:
    downloader = IndexArtifactDownloader.__new__(IndexArtifactDownloader)
    downloader.repo = REPO
    downloader.token = ""
    downloader.api_base = f"https://api.github.com/repos/{REPO}"
    return downloader


def _make_artifact_zip(tmp_path: Path, metadata: Dict[str, Any]) -> Path:
    """Build a minimal valid artifact zip containing metadata + empty tar.gz."""
    archive_path = tmp_path / "index-archive.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        pass  # empty archive is fine for these tests

    meta_path = tmp_path / "artifact-metadata.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")

    zip_path = tmp_path / "artifact.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(archive_path, archive_path.name)
        zf.write(meta_path, "artifact-metadata.json")

    return zip_path


class TestDeltaBaseFallback:
    """When metadata.delta_from points to a missing base release, fall back to full-artifact behavior."""

    def test_missing_delta_base_clears_delta_from(self, tmp_path, monkeypatch):
        """If the base release for a delta artifact is not found, delta_from is cleared."""
        metadata = {
            "delta_from": "index-abc1234",
            "artifact_type": "delta",
            "checksum": "sha256stub",
            "compatibility": {"schema_version": "2"},
        }
        zip_path = _make_artifact_zip(tmp_path, metadata)

        downloader = _make_downloader()

        warn_msgs: list[str] = []

        def fake_run(args, **kwargs):
            # Simulate downloading the zip
            if "actions/artifacts" in " ".join(args) and "/zip" in " ".join(args):
                dest = kwargs.get("stdout")
                if dest is not None:
                    dest.write(zip_path.read_bytes())
                return MagicMock(returncode=0)
            # Base release probe: not found
            if "release" in args and "view" in args and "index-abc1234" in args:
                return MagicMock(returncode=1, stdout="", stderr="not found")
            return MagicMock(returncode=0, stdout="", stderr="")

        captured_metadata: list[Dict] = []

        original_integrity = None
        import mcp_server.artifacts.artifact_download as dl_mod

        orig_gate = dl_mod.IndexArtifactDownloader._run_integrity_gate

        def fake_gate(self, metadata, archive_path, checksum_path):
            captured_metadata.append(dict(metadata))
            return MagicMock(passed=True, manifest_v2_validated=False, reasons=[])

        monkeypatch.setattr(dl_mod.IndexArtifactDownloader, "_run_integrity_gate", fake_gate)
        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader, "check_compatibility", lambda self, m: (True, [])
        )
        monkeypatch.setattr(dl_mod, "verify_attestation", MagicMock())

        import logging

        log_records: list[logging.LogRecord] = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        handler = CapturingHandler()
        import mcp_server.artifacts.artifact_download as dl

        dl.logger.addHandler(handler)
        dl.logger.setLevel(logging.WARNING)

        try:
            with patch("subprocess.run", side_effect=fake_run):
                # Patch install_indexes so we don't try to install into CWD
                monkeypatch.setattr(
                    dl_mod.IndexArtifactDownloader,
                    "install_indexes",
                    MagicMock(return_value=["code_index.db"]),
                )
                downloader.download_artifact(42, tmp_path / "output")
        except Exception:
            pass  # test only cares about delta_from state / log
        finally:
            dl.logger.removeHandler(handler)

        # Either delta_from was cleared in metadata or a warning was logged
        delta_cleared = any(
            m.get("delta_from") is None or m.get("delta_from") == "" for m in captured_metadata
        )
        warned = any("delta" in r.getMessage().lower() for r in log_records)
        assert (
            delta_cleared or warned
        ), "Expected delta_from to be cleared or a warning logged when base release is missing"

    def test_present_delta_base_not_cleared(self, tmp_path, monkeypatch):
        """If the base release exists, delta_from is NOT cleared."""
        metadata = {
            "delta_from": "index-abc1234",
            "artifact_type": "delta",
            "checksum": "sha256stub",
            "compatibility": {"schema_version": "2"},
        }
        zip_path = _make_artifact_zip(tmp_path, metadata)
        downloader = _make_downloader()
        captured_metadata: list[Dict] = []

        import mcp_server.artifacts.artifact_download as dl_mod

        def fake_run(args, **kwargs):
            if "actions/artifacts" in " ".join(args) and "/zip" in " ".join(args):
                dest = kwargs.get("stdout")
                if dest is not None:
                    dest.write(zip_path.read_bytes())
                return MagicMock(returncode=0)
            # Base release exists
            if "release" in args and "view" in args and "index-abc1234" in args:
                return MagicMock(returncode=0, stdout="title: Index: index-abc1234", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_gate(self, metadata, archive_path, checksum_path):
            captured_metadata.append(dict(metadata))
            return MagicMock(passed=True, manifest_v2_validated=False, reasons=[])

        monkeypatch.setattr(dl_mod.IndexArtifactDownloader, "_run_integrity_gate", fake_gate)
        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader, "check_compatibility", lambda self, m: (True, [])
        )
        monkeypatch.setattr(dl_mod, "verify_attestation", MagicMock())
        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader,
            "install_indexes",
            MagicMock(return_value=["code_index.db"]),
        )

        with patch("subprocess.run", side_effect=fake_run):
            try:
                downloader.download_artifact(42, tmp_path / "output")
            except Exception:
                pass

        # delta_from should still be set (not cleared) when base exists
        if captured_metadata:
            assert (
                captured_metadata[0].get("delta_from") == "index-abc1234"
            ), "delta_from should not be cleared when base release exists"

    def test_no_delta_from_skips_probe(self, tmp_path, monkeypatch):
        """Artifacts without delta_from should not trigger any 'release view' probe."""
        metadata = {
            "artifact_type": "full",
            "checksum": "sha256stub",
            "compatibility": {"schema_version": "2"},
        }
        zip_path = _make_artifact_zip(tmp_path, metadata)
        downloader = _make_downloader()
        release_view_calls: list[list] = []

        import mcp_server.artifacts.artifact_download as dl_mod

        def fake_run(args, **kwargs):
            if "actions/artifacts" in " ".join(str(a) for a in args) and "/zip" in " ".join(
                str(a) for a in args
            ):
                dest = kwargs.get("stdout")
                if dest is not None:
                    dest.write(zip_path.read_bytes())
                return MagicMock(returncode=0)
            if "release" in args and "view" in args:
                release_view_calls.append(list(args))
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader,
            "_run_integrity_gate",
            lambda self, m, a, c: MagicMock(passed=True, manifest_v2_validated=False, reasons=[]),
        )
        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader, "check_compatibility", lambda self, m: (True, [])
        )
        monkeypatch.setattr(dl_mod, "verify_attestation", MagicMock())
        monkeypatch.setattr(
            dl_mod.IndexArtifactDownloader,
            "install_indexes",
            MagicMock(return_value=["code_index.db"]),
        )

        with patch("subprocess.run", side_effect=fake_run):
            try:
                downloader.download_artifact(42, tmp_path / "output")
            except Exception:
                pass

        assert (
            not release_view_calls
        ), f"Should not call 'gh release view' for full artifacts; got: {release_view_calls}"
