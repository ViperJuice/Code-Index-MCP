"""Integration tests for schema migration wired into check_compatibility."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server.artifacts.artifact_download import IndexArtifactDownloader as ArtifactDownloader
from mcp_server.storage.schema_migrator import UnknownSchemaVersionError


def _base_metadata(schema_version: str = "2") -> dict:
    return {
        "compatibility": {
            "schema_version": schema_version,
            "embedding_model": "voyage-code-3",
        }
    }


def test_compatible_schema_no_issues():
    downloader = ArtifactDownloader.__new__(ArtifactDownloader)
    metadata = _base_metadata("2")
    with patch.dict("os.environ", {"INDEX_SCHEMA_VERSION": "2"}):
        compatible, issues = downloader.check_compatibility(metadata)
    assert compatible is True
    assert not any("Schema mismatch" in i for i in issues)


def test_older_known_schema_triggers_migration():
    """Artifact schema=1, local=2: migrator is invoked, no schema-mismatch issue returned."""
    downloader = ArtifactDownloader.__new__(ArtifactDownloader)
    metadata = _base_metadata("1")
    with patch.dict("os.environ", {"INDEX_SCHEMA_VERSION": "2"}):
        compatible, issues = downloader.check_compatibility(metadata)
    assert not any("Schema mismatch" in i for i in issues), issues


def test_unknown_schema_raises():
    """Artifact schema=99 is unknown: check_compatibility raises UnknownSchemaVersionError."""
    downloader = ArtifactDownloader.__new__(ArtifactDownloader)
    metadata = _base_metadata("99")
    with patch.dict("os.environ", {"INDEX_SCHEMA_VERSION": "2"}):
        with pytest.raises(UnknownSchemaVersionError):
            downloader.check_compatibility(metadata)


def test_equal_schema_versions_pass():
    downloader = ArtifactDownloader.__new__(ArtifactDownloader)
    metadata = _base_metadata("1")
    with patch.dict("os.environ", {"INDEX_SCHEMA_VERSION": "1"}):
        compatible, issues = downloader.check_compatibility(metadata)
    assert not any("Schema mismatch" in i for i in issues)
