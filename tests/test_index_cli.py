"""
Tests for Index Management CLI

These tests verify that the Claude Index CLI tool correctly manages
indexes across different environments.
"""

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.cli.index_commands import (
    CreateIndexCommand,
    ListIndexesCommand,
    MigrateIndexCommand,
    SyncIndexCommand,
    ValidateIndexCommand,
)


class TestCreateIndexCommand:
    """Test index creation functionality."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return CreateIndexCommand()

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create some test files
        (repo_path / "test.py").write_text("def test(): pass")
        (repo_path / "main.js").write_text("console.log('test');")

        # Initialize git
        os.system(f"cd {repo_path} && git init && git add . && git commit -m 'Initial'")

        return repo_path

    @pytest.mark.asyncio
    async def test_create_index_success(self, command, temp_repo):
        """Test successful index creation."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful indexing
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate.return_value = (b"Success", b"")
            mock_subprocess.return_value = mock_proc

            # Create mock index file
            index_dir = Path.cwd() / ".indexes" / "abc123"
            index_dir.mkdir(parents=True, exist_ok=True)
            index_path = index_dir / "code_index.db"

            # Create minimal SQLite database
            conn = sqlite3.connect(str(index_path))
            conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
            conn.execute("INSERT INTO files (path) VALUES ('test.py')")
            conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT)")
            conn.commit()
            conn.close()

            result = await command.execute(
                repo="test_repo", path=str(temp_repo), languages=["python", "javascript"]
            )

            assert result.success is True
            assert result.data["file_count"] == 1
            assert "index_path" in result.data
            assert "repo_hash" in result.data

            # Verify metadata was created
            metadata_path = index_dir / "metadata.json"
            assert metadata_path.exists()

            with open(metadata_path) as f:
                metadata = json.load(f)
                assert metadata["repo"] == "test_repo"
                assert metadata["languages"] == ["python", "javascript"]

    @pytest.mark.asyncio
    async def test_create_index_invalid_path(self, command):
        """Test index creation with invalid path."""
        result = await command.execute(repo="test_repo", path="/nonexistent/path")

        assert result.success is False
        assert "does not exist" in result.error

    @pytest.mark.asyncio
    async def test_create_index_with_excludes(self, command, temp_repo):
        """Test index creation with exclude patterns."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            await command.execute(
                repo="test_repo", path=str(temp_repo), exclude=["*.log", "node_modules/"]
            )

            # Verify exclude patterns were passed to mcp-index
            call_args = mock_subprocess.call_args[0]
            assert "--exclude" in call_args
            assert "*.log" in call_args
            assert "node_modules/" in call_args


class TestValidateIndexCommand:
    """Test index validation functionality."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return ValidateIndexCommand()

    @pytest.fixture
    def valid_index(self, tmp_path):
        """Create a valid test index."""
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"

        conn = sqlite3.connect(str(index_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("INSERT INTO files (path) VALUES ('test.py')")
        conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO symbols (name) VALUES ('test_function')")
        conn.commit()
        conn.close()

        # Enable indexing
        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        return index_path

    @pytest.mark.asyncio
    async def test_validate_valid_index(self, command, valid_index, tmp_path):
        """Test validation of a valid index."""
        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await command.execute(repo="test_repo")

            assert result.success is True
            assert result.data["valid"] is True
            assert result.data["file_count"] == 1
            assert result.data["symbol_count"] == 1
            assert len(result.data["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_index(self, command, tmp_path):
        """Test validation when index is missing."""
        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await command.execute(repo="test_repo")

            assert result.success is False
            assert "No index found" in result.error

    @pytest.mark.asyncio
    async def test_validate_corrupted_index(self, command, tmp_path):
        """Test validation of corrupted index."""
        # Create corrupted index
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"
        index_path.write_text("corrupted data")

        # Enable indexing
        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await command.execute(repo="test_repo")

            assert result.success is True
            assert result.data["valid"] is False
            assert "Database error" in str(result.data["issues"])

    @pytest.mark.asyncio
    async def test_validate_empty_index(self, command, tmp_path):
        """Test validation of empty index."""
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"

        conn = sqlite3.connect(str(index_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
        conn.commit()
        conn.close()

        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await command.execute(repo="test_repo")

            assert result.success is True
            assert result.data["valid"] is True  # Empty but valid
            assert result.data["file_count"] == 0
            assert "Index contains no files" in result.data["issues"]


class TestListIndexesCommand:
    """Test index listing functionality."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return ListIndexesCommand()

    @pytest.fixture
    def multiple_indexes(self, tmp_path):
        """Create multiple test indexes."""
        indexes = []

        # Create centralized index
        central_dir = tmp_path / ".indexes" / "hash1"
        central_dir.mkdir(parents=True)
        db_path = central_dir / "code_index.db"
        self._create_test_db(db_path, 10, 50)

        metadata = {"repo": "project1", "repo_hash": "hash1"}
        (central_dir / "metadata.json").write_text(json.dumps(metadata))
        indexes.append(db_path)

        # Create legacy index
        legacy_dir = tmp_path / ".mcp-index"
        legacy_dir.mkdir()
        db_path = legacy_dir / "code_index.db"
        self._create_test_db(db_path, 5, 20)
        indexes.append(db_path)

        # Create test index
        test_dir = tmp_path / "test_indexes" / "test_repo"
        test_dir.mkdir(parents=True)
        db_path = test_dir / "code_index.db"
        self._create_test_db(db_path, 15, 75)
        indexes.append(db_path)

        return indexes

    def _create_test_db(self, db_path, file_count, symbol_count):
        """Create a test database with specified counts."""
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT)")

        for i in range(file_count):
            conn.execute("INSERT INTO files (path) VALUES (?)", (f"file{i}.py",))

        for i in range(symbol_count):
            conn.execute("INSERT INTO symbols (name) VALUES (?)", (f"symbol{i}",))

        conn.commit()
        conn.close()

    @pytest.mark.asyncio
    async def test_list_all_indexes(self, command, multiple_indexes, tmp_path):
        """Test listing all indexes."""
        with patch.object(command.path_config, "get_search_paths", return_value=[tmp_path]):
            result = await command.execute()

            assert result.success is True
            assert result.data["count"] == 3

            indexes = result.data["indexes"]

            # Check we found all types
            location_types = {idx["location_type"] for idx in indexes}
            assert "centralized" in location_types
            assert "legacy" in location_types
            assert "test" in location_types

            # Verify sorting
            repos = [idx["repo"] for idx in indexes]
            assert repos == sorted(repos)

    @pytest.mark.asyncio
    async def test_list_with_filter(self, command, multiple_indexes, tmp_path):
        """Test listing with repository filter."""
        with patch.object(command.path_config, "get_search_paths", return_value=[tmp_path]):
            result = await command.execute(filter="project1")

            assert result.success is True
            assert result.data["count"] == 1
            assert result.data["indexes"][0]["repo"] == "project1"

    @pytest.mark.asyncio
    async def test_list_empty(self, command, tmp_path):
        """Test listing when no indexes exist."""
        with patch.object(command.path_config, "get_search_paths", return_value=[tmp_path]):
            result = await command.execute()

            assert result.success is True
            assert result.data["count"] == 0
            assert result.data["indexes"] == []


class TestMigrateIndexCommand:
    """Test index migration functionality."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return MigrateIndexCommand()

    @pytest.fixture
    def legacy_index(self, tmp_path):
        """Create a legacy index."""
        legacy_dir = tmp_path / ".mcp-index"
        legacy_dir.mkdir()

        db_path = legacy_dir / "code_index.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY)")
        conn.close()

        metadata = {"repo": "legacy_project", "repo_hash": "legacy123"}
        (legacy_dir / "metadata.json").write_text(json.dumps(metadata))

        return legacy_dir

    @pytest.mark.asyncio
    async def test_migrate_legacy_to_centralized(self, command, legacy_index, tmp_path):
        """Test migrating from legacy to centralized location."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = await command.execute(from_env="legacy", to_env="centralized")

            assert result.success is True
            assert len(result.data["migrated"]) == 1
            assert len(result.data["failed"]) == 0

            # Verify migration
            migrated = result.data["migrated"][0]
            assert migrated["repo"] == "legacy_project"

            # Check target exists
            target_path = tmp_path / ".indexes" / "legacy123" / "code_index.db"
            assert target_path.exists()

    @pytest.mark.asyncio
    async def test_migrate_specific_repo(self, command, legacy_index, tmp_path):
        """Test migrating specific repository only."""
        # Create additional index
        other_dir = tmp_path / "other_index"
        other_dir.mkdir()
        (other_dir / "code_index.db").touch()

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = await command.execute(
                from_env="legacy", to_env="centralized", repo="legacy_project"
            )

            assert result.success is True
            assert len(result.data["migrated"]) == 1
            assert result.data["migrated"][0]["repo"] == "legacy_project"

    @pytest.mark.asyncio
    async def test_migrate_with_failures(self, command, tmp_path):
        """Test migration with some failures."""
        # Create index with no write permissions on target
        legacy_dir = tmp_path / ".mcp-index"
        legacy_dir.mkdir()
        (legacy_dir / "code_index.db").touch()

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            with patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission")):
                result = await command.execute(from_env="legacy", to_env="centralized")

                assert result.success is True
                assert len(result.data["failed"]) > 0


class TestSyncIndexCommand:
    """Test index synchronization functionality."""

    @pytest.fixture
    def command(self):
        """Create command instance."""
        return SyncIndexCommand()

    @pytest.fixture
    def existing_index(self, tmp_path):
        """Create an existing index."""
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"

        conn = sqlite3.connect(str(index_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY)")
        conn.close()

        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        return index_path

    @pytest.mark.asyncio
    async def test_sync_full(self, command, existing_index, tmp_path):
        """Test full index sync."""
        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate.return_value = (
                    b"5 files added\n3 files updated\n1 files removed",
                    b"",
                )
                mock_subprocess.return_value = mock_proc

                result = await command.execute(repo="test_repo")

                assert result.success is True
                assert result.data["files_added"] == 5
                assert result.data["files_updated"] == 3
                assert result.data["files_removed"] == 1
                assert result.data["duration_seconds"] > 0

    @pytest.mark.asyncio
    async def test_sync_incremental(self, command, existing_index, tmp_path):
        """Test incremental index sync."""
        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            with patch("subprocess.run") as mock_run:
                # Mock git diff output
                mock_run.return_value = Mock(returncode=0, stdout="file1.py\nfile2.js\n")

                with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                    mock_proc = AsyncMock()
                    mock_proc.returncode = 0
                    mock_proc.communicate.return_value = (b"2 files updated", b"")
                    mock_subprocess.return_value = mock_proc

                    result = await command.execute(repo="test_repo", incremental=True)

                    assert result.success is True
                    assert result.data["files_updated"] == 2

                    # Verify incremental update was called
                    call_args = mock_subprocess.call_args[0]
                    assert "update" in call_args
                    assert "--files" in call_args

    @pytest.mark.asyncio
    async def test_sync_no_index(self, command, tmp_path):
        """Test sync when no index exists."""
        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await command.execute(repo="test_repo")

            assert result.success is False
            assert "No index found" in result.error
            assert "Create one first" in result.error


class TestIntegration:
    """Integration tests for CLI commands."""

    @pytest.mark.asyncio
    async def test_create_validate_list_flow(self, tmp_path):
        """Test complete workflow: create, validate, list."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "test.py").write_text("print('test')")

        # Mock the mcp-index command
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            # Create index
            create_cmd = CreateIndexCommand()

            # Create the index directory and file that would be created
            index_dir = Path.cwd() / ".indexes" / "test123"
            index_dir.mkdir(parents=True, exist_ok=True)
            index_path = index_dir / "code_index.db"

            conn = sqlite3.connect(str(index_path))
            conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
            conn.execute("INSERT INTO files (path) VALUES ('test.py')")
            conn.commit()
            conn.close()

            result = await create_cmd.execute(repo="integration_test", path=str(repo_path))
            assert result.success is True

            # Validate index
            validate_cmd = ValidateIndexCommand()
            with patch(
                "mcp_server.utils.index_discovery.IndexDiscovery.get_local_index_path",
                return_value=index_path,
            ):
                result = await validate_cmd.execute(repo="integration_test")
                assert result.success is True
                assert result.data["valid"] is True

            # List indexes
            list_cmd = ListIndexesCommand()
            with patch.object(list_cmd.path_config, "get_search_paths", return_value=[Path.cwd()]):
                result = await list_cmd.execute()
                assert result.success is True
                assert result.data["count"] >= 1
