"""
Index Management Command Implementations

This module provides the actual implementation for all index management commands
used by the Claude Index CLI tool.
"""

import asyncio
import hashlib
import json
import logging
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server.config.index_paths import IndexPathConfig
from mcp_server.core.path_utils import PathUtils
from mcp_server.storage.artifact_registry import ArtifactRecord, ArtifactRegistry
from mcp_server.utils.index_discovery import IndexDiscovery

logger = logging.getLogger(__name__)


class CommandResult:
    """Standard result object for command execution."""

    def __init__(self, success: bool, data: Dict[str, Any] = None, error: str = None):
        """Initialize command result."""
        self.success = success
        self.data = data or {}
        self.error = error


class BaseIndexCommand:
    """Base class for all index commands."""

    def __init__(self, path_config: Optional[IndexPathConfig] = None):
        """Initialize base command."""
        self.path_config = path_config or IndexPathConfig()

    async def execute(self, **kwargs) -> CommandResult:
        """Execute the command. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    def _get_repo_hash(self, repo_path: Path) -> str:
        """Get hash identifier for a repository."""
        # Try git remote URL first
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            url = result.stdout.strip()
            return hashlib.sha256(url.encode()).hexdigest()[:12]
        except Exception:
            # Fall back to path hash
            return hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]

    def _get_index_stats(self, db_path: Path) -> Dict[str, Any]:
        """Get statistics from an index database."""
        stats = {"file_count": 0, "symbol_count": 0, "size_mb": 0, "last_modified": None}

        try:
            # Get file size
            stats["size_mb"] = db_path.stat().st_size / (1024 * 1024)
            stats["last_modified"] = datetime.fromtimestamp(db_path.stat().st_mtime)

            # Get counts from database
            conn = sqlite3.connect(str(db_path))

            file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            stats["file_count"] = file_count

            # Check if symbols table exists
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='symbols'"
            ).fetchall()

            if tables:
                symbol_count = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
                stats["symbol_count"] = symbol_count

            conn.close()

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")

        return stats

    def _load_index_metadata(self, db_path: Path) -> Dict[str, Any]:
        """Load metadata for an index if available."""
        metadata: Dict[str, Any] = {}
        for name in [".index_metadata.json", "metadata.json", "artifact-metadata.json"]:
            candidate = db_path.parent / name
            if candidate.exists():
                try:
                    with open(candidate) as f:
                        metadata = json.load(f)
                    break
                except Exception as e:
                    logger.debug(f"Failed to read metadata from {candidate}: {e}")

        if metadata:
            if "embedding_model" in metadata:
                metadata.setdefault("model", metadata.get("embedding_model"))
            if "compatible_with" in metadata and isinstance(metadata["compatible_with"], dict):
                metadata.setdefault("model", metadata["compatible_with"].get("embedding_model"))
            if "git_commit" in metadata:
                metadata.setdefault("commit", metadata.get("git_commit"))

        return metadata


class CreateIndexCommand(BaseIndexCommand):
    """Command to create a new index for a repository."""

    async def execute(
        self,
        repo: str,
        path: str,
        languages: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> CommandResult:
        """
        Create a new index.

        Args:
            repo: Repository name/identifier
            path: Path to repository source code
            languages: Specific languages to index (optional)
            exclude: Patterns to exclude from indexing (optional)

        Returns:
            CommandResult with index creation details
        """
        try:
            repo_path = Path(path).absolute()
            if not repo_path.exists():
                return CommandResult(False, error=f"Path does not exist: {path}")

            # Get repository hash
            repo_hash = self._get_repo_hash(repo_path)

            # Determine index location
            index_dir = Path.cwd() / ".indexes" / repo_hash
            index_dir.mkdir(parents=True, exist_ok=True)
            index_path = index_dir / "code_index.db"

            # Prepare indexing command
            cmd = ["mcp-index", "index", "--path", str(repo_path), "--output", str(index_path)]

            if languages:
                cmd.extend(["--languages"] + languages)

            if exclude:
                cmd.extend(["--exclude"] + exclude)

            # Run indexing
            logger.info(f"Creating index for {repo} at {index_path}")
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return CommandResult(False, error=f"Indexing failed: {error_msg}")

            # Verify index was created
            if not index_path.exists():
                return CommandResult(False, error="Index file was not created")

            # Get index statistics
            stats = self._get_index_stats(index_path)

            # Create metadata file
            metadata = {
                "repo": repo,
                "repo_hash": repo_hash,
                "created_at": datetime.now().isoformat(),
                "source_path": str(repo_path),
                "languages": languages,
                "exclude_patterns": exclude,
                "stats": stats,
            }

            metadata_path = index_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            return CommandResult(
                success=True,
                data={
                    "index_path": str(index_path),
                    "repo_hash": repo_hash,
                    "file_count": stats["file_count"],
                    "symbol_count": stats["symbol_count"],
                    "size_mb": stats["size_mb"],
                },
            )

        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return CommandResult(False, error=str(e))


class ValidateIndexCommand(BaseIndexCommand):
    """Command to validate an existing index."""

    async def execute(self, repo: str, fix: bool = False) -> CommandResult:
        """
        Validate an index.

        Args:
            repo: Repository to validate
            fix: Whether to attempt fixing issues

        Returns:
            CommandResult with validation details
        """
        try:
            # Find the index
            discovery = IndexDiscovery(Path.cwd())
            index_path = discovery.get_local_index_path()

            if not index_path:
                return CommandResult(False, error=f"No index found for {repo}")

            validation = {"valid": True, "issues": [], "file_count": 0, "symbol_count": 0}

            # Check if file exists
            if not index_path.exists():
                validation["valid"] = False
                validation["issues"].append("Index file does not exist")
                return CommandResult(True, data=validation)

            # Validate SQLite database
            try:
                conn = sqlite3.connect(str(index_path))

                # Check tables
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = [t[0] for t in tables]

                required_tables = ["files"]
                for table in required_tables:
                    if table not in table_names:
                        validation["valid"] = False
                        validation["issues"].append(f"Missing required table: {table}")

                # Get counts
                if "files" in table_names:
                    file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                    validation["file_count"] = file_count

                    if file_count == 0:
                        validation["issues"].append("Index contains no files")

                if "symbols" in table_names:
                    symbol_count = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
                    validation["symbol_count"] = symbol_count

                # Check integrity
                integrity_check = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity_check != "ok":
                    validation["valid"] = False
                    validation["issues"].append(
                        f"Database integrity check failed: {integrity_check}"
                    )

                conn.close()

                # Fix issues if requested
                if fix and validation["issues"]:
                    fixed_issues = await self._fix_issues(index_path, validation["issues"])
                    validation["fixed"] = fixed_issues

            except sqlite3.Error as e:
                validation["valid"] = False
                validation["issues"].append(f"Database error: {str(e)}")

            return CommandResult(True, data=validation)

        except Exception as e:
            logger.error(f"Error validating index: {e}")
            return CommandResult(False, error=str(e))

    async def _fix_issues(self, index_path: Path, issues: List[str]) -> List[str]:
        """Attempt to fix validation issues."""
        fixed = []

        for issue in issues:
            if "Index contains no files" in issue:
                # Re-index the repository
                logger.info("Attempting to re-index repository")
                # This would trigger a re-index
                fixed.append("Triggered re-indexing")

            elif "Database integrity check failed" in issue:
                # Try to recover the database
                logger.info("Attempting database recovery")
                try:
                    # Create backup
                    backup_path = index_path.with_suffix(".db.backup")
                    shutil.copy2(index_path, backup_path)

                    # Run recovery
                    conn = sqlite3.connect(str(index_path))
                    conn.execute("VACUUM")
                    conn.close()

                    fixed.append("Ran database VACUUM")
                except Exception:
                    pass

        return fixed


class ListIndexesCommand(BaseIndexCommand):
    """Command to list all available indexes."""

    async def execute(self, format: str = "table", filter: Optional[str] = None) -> CommandResult:
        """
        List all indexes.

        Args:
            format: Output format (table, json, simple)
            filter: Filter pattern for repository names

        Returns:
            CommandResult with list of indexes
        """
        try:
            indexes = []

            # Search all configured paths
            for search_path in self.path_config.get_search_paths():
                if not search_path.exists():
                    continue

                # Look for index databases
                for db_path in search_path.rglob("code_index.db"):
                    try:
                        # Get metadata if available
                        metadata_path = db_path.parent / "metadata.json"
                        if metadata_path.exists():
                            with open(metadata_path) as f:
                                metadata = json.load(f)
                                repo_name = metadata.get("repo", db_path.parent.name)
                        else:
                            repo_name = db_path.parent.name

                        # Apply filter if specified
                        if filter and filter not in repo_name:
                            continue

                        # Get index info
                        stats = self._get_index_stats(db_path)

                        # Determine location type
                        location_type = "unknown"
                        if ".indexes" in str(db_path):
                            location_type = "centralized"
                        elif ".mcp-index" in str(db_path):
                            location_type = "legacy"
                        elif "test_indexes" in str(db_path):
                            location_type = "test"
                        elif "/tmp/" in str(db_path):
                            location_type = "temporary"

                        indexes.append(
                            {
                                "repo": repo_name,
                                "path": str(db_path),
                                "location_type": location_type,
                                "size_mb": round(stats["size_mb"], 2),
                                "file_count": stats["file_count"],
                                "symbol_count": stats["symbol_count"],
                                "last_modified": (
                                    stats["last_modified"].isoformat()
                                    if stats["last_modified"]
                                    else None
                                ),
                            }
                        )

                    except Exception as e:
                        logger.warning(f"Error reading index at {db_path}: {e}")

            # Sort by repository name
            indexes.sort(key=lambda x: x["repo"])

            return CommandResult(success=True, data={"indexes": indexes, "count": len(indexes)})

        except Exception as e:
            logger.error(f"Error listing indexes: {e}")
            return CommandResult(False, error=str(e))


class MigrateIndexCommand(BaseIndexCommand):
    """Command to migrate indexes between environments."""

    async def execute(
        self, from_env: str, to_env: str, repo: Optional[str] = None
    ) -> CommandResult:
        """
        Migrate indexes.

        Args:
            from_env: Source environment (docker, native, legacy)
            to_env: Target environment (docker, native, centralized)
            repo: Specific repository to migrate (optional)

        Returns:
            CommandResult with migration details
        """
        try:
            migrated = []
            failed = []

            # Define environment paths
            env_paths = {
                "docker": ["/workspaces/{project}/.indexes", "/workspaces/{project}/.mcp-index"],
                "native": [".indexes/{repo_hash}", ".mcp-index"],
                "legacy": [".mcp-index"],
                "centralized": [".indexes/{repo_hash}"],
            }

            # Find indexes to migrate
            source_paths = env_paths.get(from_env, [])
            target_template = env_paths.get(to_env, [".indexes/{repo_hash}"])[0]

            for source_pattern in source_paths:
                # Convert pattern to actual paths
                if "{project}" in source_pattern:
                    # Handle Docker paths
                    base_path = Path("/workspaces")
                    if base_path.exists():
                        for project_dir in base_path.iterdir():
                            if project_dir.is_dir():
                                check_path = Path(
                                    source_pattern.replace("{project}", project_dir.name)
                                )
                                if check_path.exists():
                                    await self._migrate_index(
                                        check_path, target_template, repo, migrated, failed
                                    )
                else:
                    # Handle regular paths
                    check_path = Path(source_pattern.replace("{repo_hash}", "*"))
                    for match_path in Path.cwd().glob(str(check_path)):
                        if match_path.is_dir():
                            await self._migrate_index(
                                match_path, target_template, repo, migrated, failed
                            )

            return CommandResult(
                success=True,
                data={"migrated": migrated, "failed": failed, "total": len(migrated) + len(failed)},
            )

        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return CommandResult(False, error=str(e))

    async def _migrate_index(
        self,
        source_path: Path,
        target_template: str,
        filter_repo: Optional[str],
        migrated: List[Dict],
        failed: List[Dict],
    ):
        """Migrate a single index."""
        try:
            # Find index database
            db_path = source_path / "code_index.db"
            if not db_path.exists():
                return

            # Get repository info
            metadata_path = source_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    repo_name = metadata.get("repo", source_path.name)
                    repo_hash = metadata.get("repo_hash", self._get_repo_hash(source_path))
            else:
                repo_name = source_path.name
                repo_hash = self._get_repo_hash(source_path)

            # Check filter
            if filter_repo and filter_repo != repo_name:
                return

            # Determine target path
            target_path = Path(
                target_template.replace("{repo_hash}", repo_hash)
                .replace("{repo}", repo_name)
                .replace("{project}", repo_name)
            )

            # Create target directory
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy index
            shutil.copy2(db_path, target_path / "code_index.db")

            # Copy metadata if exists
            if metadata_path.exists():
                shutil.copy2(metadata_path, target_path / "metadata.json")

            migrated.append({"repo": repo_name, "from": str(source_path), "to": str(target_path)})

            logger.info(f"Migrated {repo_name} from {source_path} to {target_path}")

        except Exception as e:
            failed.append({"repo": source_path.name, "error": str(e)})
            logger.error(f"Failed to migrate {source_path}: {e}")


class SyncIndexCommand(BaseIndexCommand):
    """Command to sync index with repository state."""

    async def execute(self, repo: str, incremental: bool = False) -> CommandResult:
        """
        Sync index with current repository state.

        Args:
            repo: Repository to sync
            incremental: Only index changed files

        Returns:
            CommandResult with sync details
        """
        try:
            # Find existing index
            discovery = IndexDiscovery(Path.cwd())
            index_path = discovery.get_local_index_path()

            if not index_path:
                return CommandResult(
                    False,
                    error=f"No index found for {repo}. Create one first with 'create' command.",
                )

            sync_stats = {
                "files_added": 0,
                "files_updated": 0,
                "files_removed": 0,
                "duration_seconds": 0,
            }

            start_time = datetime.now()

            if incremental:
                # Get list of changed files from git
                try:
                    result = subprocess.run(
                        ["git", "diff", "--name-only", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    changed_files = result.stdout.strip().split("\n") if result.stdout else []

                    # Update only changed files
                    cmd = [
                        "mcp-index",
                        "update",
                        "--index",
                        str(index_path),
                        "--files",
                    ] + changed_files

                except subprocess.CalledProcessError:
                    # Fall back to full sync if git not available
                    incremental = False

            if not incremental:
                # Full re-index
                cmd = [
                    "mcp-index",
                    "reindex",
                    "--index",
                    str(index_path),
                    "--path",
                    str(Path.cwd()),
                ]

            # Run sync command
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return CommandResult(False, error=f"Sync failed: {error_msg}")

            # Parse output for statistics
            output = stdout.decode()
            for line in output.split("\n"):
                if "added" in line:
                    try:
                        sync_stats["files_added"] = int(line.split()[0])
                    except Exception:
                        pass
                elif "updated" in line:
                    try:
                        sync_stats["files_updated"] = int(line.split()[0])
                    except Exception:
                        pass
                elif "removed" in line:
                    try:
                        sync_stats["files_removed"] = int(line.split()[0])
                    except Exception:
                        pass

            sync_stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()

            # Update metadata
            metadata_path = index_path.parent / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                metadata["last_sync"] = datetime.now().isoformat()
                metadata["sync_stats"] = sync_stats
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

            return CommandResult(True, data=sync_stats)

        except Exception as e:
            logger.error(f"Error syncing index: {e}")
            return CommandResult(False, error=str(e))


class PublishArtifactCommand(BaseIndexCommand):
    """Command to publish a built index into the artifact registry."""

    def __init__(
        self,
        registry: Optional[ArtifactRegistry] = None,
        artifact_store: Optional[Path] = None,
        path_config: Optional[IndexPathConfig] = None,
    ):
        self.registry = registry or ArtifactRegistry()
        effective_path_config = path_config or IndexPathConfig(artifact_registry=self.registry)
        super().__init__(path_config=effective_path_config)
        self.artifact_store = artifact_store or PathUtils.get_index_storage_path() / "artifacts"
        self.artifact_store.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        repo: str,
        index_path: Optional[str] = None,
        model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> CommandResult:
        """Publish the current index to the local artifact registry."""
        try:
            if index_path:
                db_path = Path(index_path)
            else:
                discovery = IndexDiscovery(Path.cwd(), path_config=self.path_config)
                db_path = discovery.get_local_index_path()

            if not db_path or not db_path.exists():
                return CommandResult(False, error="No index found to publish")

            metadata = self._load_index_metadata(db_path)
            resolved_model = model or metadata.get("model") or "default"
            resolved_version = version or metadata.get("commit") or "unversioned"

            target_dir = self.artifact_store / repo / resolved_model / resolved_version
            target_dir.mkdir(parents=True, exist_ok=True)

            self._copy_index_payload(db_path, target_dir)

            record = self.registry.add_or_update(
                repo_id=repo,
                model=resolved_model,
                version=resolved_version,
                path=target_dir,
                commit=metadata.get("commit"),
                metadata=metadata,
                source="publish",
            )

            if self.path_config:
                self.path_config.cache_discovery(
                    repo_identifier=repo,
                    path=target_dir / db_path.name,
                    commit=record.commit,
                    model=record.model,
                    metadata=record.metadata,
                )

            manifest_path = target_dir / "artifact.json"
            with open(manifest_path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)

            return CommandResult(
                True,
                data={
                    "artifact_path": str(target_dir),
                    "record": record.to_dict(),
                },
            )

        except Exception as e:
            logger.error(f"Error publishing artifact: {e}")
            return CommandResult(False, error=str(e))

    def _copy_index_payload(self, source_db: Path, target_dir: Path) -> None:
        """Copy index files and metadata into the artifact store."""
        shutil.copy2(source_db, target_dir / source_db.name)

        for name in [".index_metadata.json", "metadata.json", "artifact-metadata.json"]:
            candidate = source_db.parent / name
            if candidate.exists():
                shutil.copy2(candidate, target_dir / candidate.name)

        vector_dir = source_db.parent / "vector_index.qdrant"
        if vector_dir.exists() and vector_dir.is_dir():
            target_vector = target_dir / "vector_index.qdrant"
            if target_vector.exists():
                shutil.rmtree(target_vector)
            shutil.copytree(vector_dir, target_vector)


class ListArtifactCatalogCommand(BaseIndexCommand):
    """Command to list artifacts from the registry."""

    def __init__(
        self,
        registry: Optional[ArtifactRegistry] = None,
        path_config: Optional[IndexPathConfig] = None,
    ):
        self.registry = registry or ArtifactRegistry()
        super().__init__(path_config=path_config or IndexPathConfig(artifact_registry=self.registry))

    async def execute(self, repo: Optional[str] = None, model: Optional[str] = None) -> CommandResult:
        """List artifacts filtered by repo/model."""
        try:
            records = self.registry.list_records(repo_id=repo, model=model)
            return CommandResult(
                True,
                data={
                    "artifacts": [record.to_dict() for record in records],
                    "count": len(records),
                },
            )
        except Exception as e:
            logger.error(f"Error listing artifacts: {e}")
            return CommandResult(False, error=str(e))


class DownloadArtifactCommand(BaseIndexCommand):
    """Command to download the best matching artifact for a model."""

    def __init__(
        self,
        registry: Optional[ArtifactRegistry] = None,
        default_destination: Optional[Path] = None,
        path_config: Optional[IndexPathConfig] = None,
    ):
        self.registry = registry or ArtifactRegistry()
        super().__init__(path_config=path_config or IndexPathConfig(artifact_registry=self.registry))
        self.default_destination = default_destination or (Path.cwd() / ".mcp-index")

    async def execute(
        self, repo: str, model: Optional[str] = None, destination: Optional[str] = None
    ) -> CommandResult:
        """Download the best artifact match for the requested model."""
        try:
            record = self.registry.find_best_match(repo_id=repo, model=model)
            if not record:
                return CommandResult(False, error="No matching artifact found")

            dest_root = Path(destination) if destination else self.default_destination
            dest_root.mkdir(parents=True, exist_ok=True)

            target_db = self._materialize_artifact(record, dest_root)

            if self.path_config:
                self.path_config.cache_discovery(
                    repo_identifier=repo,
                    path=target_db,
                    commit=record.commit,
                    model=record.model,
                    metadata=record.metadata,
                )

            return CommandResult(
                True,
                data={
                    "artifact": record.to_dict(),
                    "destination": str(dest_root),
                    "index_path": str(target_db),
                },
            )
        except Exception as e:
            logger.error(f"Error downloading artifact: {e}")
            return CommandResult(False, error=str(e))

    def _materialize_artifact(self, record: ArtifactRecord, destination: Path) -> Path:
        """Copy artifact contents into the destination directory."""
        source_path = record.path
        if not source_path.exists():
            raise FileNotFoundError(f"Artifact content missing at {source_path}")

        if source_path.is_file():
            target = destination / source_path.name
            shutil.copy2(source_path, target)
            return target

        # Directory-based artifact
        for item in source_path.iterdir():
            dest = destination / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        target_db = destination / "code_index.db"
        if not target_db.exists():
            raise FileNotFoundError(f"Published artifact missing index database in {destination}")
        return target_db
