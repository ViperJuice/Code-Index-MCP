"""Integration tests for migration maintenance CLI."""

import sqlite3
from pathlib import Path

from click.testing import CliRunner

from mcp_server.cli.index_management import index
from mcp_server.storage.sqlite_store import SQLiteStore


def _create_legacy_database(tmp_path: Path) -> Path:
    """Create a legacy SQLite database without recent migrations."""
    legacy_root = tmp_path / "legacy_repo" / ".mcp-index"
    legacy_root.mkdir(parents=True, exist_ok=True)
    db_path = legacy_root / "code_index.db"

    migration_001 = Path(__file__).parents[2] / "mcp_server" / "storage" / "migrations" / "001_initial_schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(migration_001.read_text())
    conn.execute("INSERT INTO repositories (path, name) VALUES (?, ?)", ("/repo", "legacy"))
    conn.commit()
    conn.close()

    return db_path


def test_migrate_command_upgrades_legacy_database_and_backfills_manifests(tmp_path):
    """Ensure migrate command updates schema and creates manifest files."""
    db_path = _create_legacy_database(tmp_path)
    runner = CliRunner()

    result = runner.invoke(index, ["migrate", "--db-path", str(db_path)])

    assert result.exit_code == 0

    store = SQLiteStore(str(db_path))
    health = store.health_check()
    assert health["status"] == "healthy"
    assert health["required_migrations"] == []

    with store._get_connection() as conn:  # noqa: SLF001
        file_columns = {row[1] for row in conn.execute("PRAGMA table_info(files)")}
        assert {"content_hash", "is_deleted", "deleted_at"}.issubset(file_columns)

        embedding_indexes = {row[1] for row in conn.execute("PRAGMA index_list(embeddings)")}
        assert "idx_embeddings_unique_scope" in embedding_indexes

    manifest_parent = db_path.parent.parent
    assert (manifest_parent / ".mcp-index.json").exists()
    assert (manifest_parent / ".index_metadata.json").exists()


def test_migrate_check_only_reports_pending_state(tmp_path):
    """Check-only mode should not mutate the database but should signal pending migrations."""
    db_path = _create_legacy_database(tmp_path)
    runner = CliRunner()

    result = runner.invoke(index, ["migrate", "--db-path", str(db_path), "--check-only"])

    assert result.exit_code == 1

    manifest_parent = db_path.parent.parent
    assert not (manifest_parent / ".mcp-index.json").exists()
    assert not (manifest_parent / ".index_metadata.json").exists()

    store = SQLiteStore(str(db_path))
    health = store.health_check()
    assert health["required_migrations"]
    assert health["status"] != "healthy"
