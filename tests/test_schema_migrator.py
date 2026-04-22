"""Unit tests for SchemaMigrator."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.storage.schema_migrator import (
    SchemaMigrationError,
    SchemaMigrator,
    UnknownSchemaVersionError,
)


def _make_migrator():
    store = MagicMock()
    return SchemaMigrator(store=store)


def test_is_known_supported_versions():
    m = _make_migrator()
    assert m.is_known("1") is True
    assert m.is_known("2") is True


def test_is_known_unknown_version():
    m = _make_migrator()
    assert m.is_known("99") is False
    assert m.is_known("") is False


def test_equal_version_passthrough(tmp_path):
    m = _make_migrator()
    result = m.migrate_artifact(tmp_path, from_version="2", to_version="2")
    assert result == tmp_path


def test_older_known_runs_migrator(tmp_path):
    m = _make_migrator()
    result = m.migrate_artifact(tmp_path, from_version="1", to_version="2")
    assert isinstance(result, Path)


def test_unknown_version_refuses(tmp_path):
    m = _make_migrator()
    with pytest.raises(UnknownSchemaVersionError):
        m.migrate_artifact(tmp_path, from_version="99", to_version="2")


def test_migration_failure_raises_SchemaMigrationError(tmp_path, monkeypatch):
    m = _make_migrator()

    def _bad_migrate(extracted_dir):
        raise RuntimeError("disk full")

    monkeypatch.setattr(m, "_migrate_1_to_2", _bad_migrate)
    with pytest.raises(SchemaMigrationError):
        m.migrate_artifact(tmp_path, from_version="1", to_version="2")


def test_migrate_artifact_unknown_to_version(tmp_path):
    m = _make_migrator()
    with pytest.raises(UnknownSchemaVersionError):
        m.migrate_artifact(tmp_path, from_version="1", to_version="99")
