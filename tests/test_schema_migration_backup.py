"""Tests for SchemaMigrator backup/rollback behaviour (SL-3)."""

import shutil
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.core.errors import SchemaMigrationError
from mcp_server.storage.schema_migrator import SchemaMigrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_migrator():
    store_stub = object.__new__(object)  # minimal stand-in, migrator only uses it for type hint
    m = SchemaMigrator.__new__(SchemaMigrator)
    m._store = store_stub
    return m


def _make_artifact_dir(tmp_path: Path) -> Path:
    d = tmp_path / "artifact_v1"
    d.mkdir()
    (d / "manifest.json").write_text('{"version": "1"}')
    (d / "data.bin").write_bytes(b"\x00\x01\x02")
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrationBackup:
    def test_backup_created_before_migration(self, tmp_path):
        """A timestamped backup dir exists while migration runs and is removed on success."""
        migrator = _make_migrator()
        extracted_dir = _make_artifact_dir(tmp_path)

        observed_backups: list[Path] = []

        original_migrate = SchemaMigrator._migrate_1_to_2

        def spy_migrate(self_inner, d: Path) -> Path:
            # Collect sibling dirs that look like backups right now.
            for sibling in d.parent.iterdir():
                if sibling.name.startswith(d.name + ".backup."):
                    observed_backups.append(sibling)
            return original_migrate(self_inner, d)

        migrator._migrate_1_to_2 = spy_migrate.__get__(migrator, SchemaMigrator)

        result = migrator.migrate_artifact(extracted_dir, "1", "2")

        # Backup was present during migration.
        assert len(observed_backups) == 1
        backup_dir = observed_backups[0]
        # Backup removed after success.
        assert not backup_dir.exists()
        # Result dir still exists.
        assert result.exists()

    def test_rollback_restores_on_schema_error(self, tmp_path):
        """SchemaMigrationError triggers rollback; extracted_dir matches pre-call state."""
        migrator = _make_migrator()
        extracted_dir = _make_artifact_dir(tmp_path)

        original_contents = {p.name: p.read_bytes() for p in extracted_dir.iterdir()}

        def bad_migrate(self_inner, d: Path) -> Path:
            # Mutate the directory then fail.
            (d / "bad_file.txt").write_text("corrupt")
            raise SchemaMigrationError("step failed")

        migrator._migrate_1_to_2 = bad_migrate.__get__(migrator, SchemaMigrator)

        with pytest.raises(SchemaMigrationError):
            migrator.migrate_artifact(extracted_dir, "1", "2")

        # extracted_dir should be back to original state.
        assert extracted_dir.exists()
        restored_contents = {p.name: p.read_bytes() for p in extracted_dir.iterdir()}
        assert restored_contents == original_contents

    def test_canonical_error_class(self):
        """SchemaMigrationError imported from schema_migrator IS the canonical class."""
        from mcp_server.core.errors import SchemaMigrationError as B
        from mcp_server.storage.schema_migrator import SchemaMigrationError as A

        assert A is B
