"""
Portable Index Discovery for MCP
Automatically detects and uses indexes created by mcp-index-kit
Enhanced with multi-path discovery to fix test environment issues
"""

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from mcp_server.storage.index_manager import IndexManifest

logger = logging.getLogger(__name__)


class IndexDiscovery:
    """Discovers and manages portable MCP indexes in repositories"""

    def __init__(
        self,
        workspace_root: Path,
        storage_strategy: Optional[str] = None,
        enable_multi_path: bool = True,
    ):
        self.workspace_root = Path(workspace_root)
        self.index_dir = self.workspace_root / ".mcp-index"
        self.config_file = self.workspace_root / ".mcp-index.json"
        self.metadata_file = self.index_dir / ".index_metadata.json"
        self.enable_multi_path = enable_multi_path

        # Import modules for multi-path support
        from mcp_server.config.index_paths import IndexPathConfig
        from mcp_server.storage.index_manager import IndexManager

        # Initialize multi-path configuration
        self.path_config = IndexPathConfig() if enable_multi_path else None

        # Determine storage strategy
        if storage_strategy is None:
            config = self.get_index_config()
            storage_strategy = config.get("storage_strategy", "inline") if config else "inline"

        self.storage_strategy = storage_strategy
        self.index_manager = IndexManager(storage_strategy=storage_strategy)

    def is_index_enabled(self) -> bool:
        """Check if MCP indexing is enabled for this repository"""
        # Check environment variable first
        if os.getenv("MCP_INDEX_ENABLED", "").lower() == "false":
            return False

        # Check config file
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return config.get("enabled", True)
            except Exception as e:
                logger.warning(f"Failed to read MCP config: {e}")

        # Check if .mcp-index directory exists
        return self.index_dir.exists()

    def get_index_config(self) -> Optional[Dict[str, Any]]:
        """Get the MCP index configuration"""
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index config: {e}")
            return None

    def get_index_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata about the current index"""
        if not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index metadata: {e}")
            return None

    def read_index_manifest(self, index_path: Path) -> Optional["IndexManifest"]:
        """Load manifest for a discovered index if it exists."""
        return self.index_manager.read_index_manifest(index_path)

    def write_index_manifest(
        self,
        index_path: Path,
        schema_version: str,
        embedding_model: str,
        creation_commit: Optional[str] = None,
    ) -> Path:
        """Persist manifest metadata next to a SQLite index."""
        commit = creation_commit or self._get_current_commit()
        return self.index_manager.write_index_manifest(
            index_path=index_path,
            schema_version=schema_version,
            embedding_model=embedding_model,
            creation_commit=commit,
        )

    def get_local_index_path(
        self,
        requested_schema_version: Optional[str] = None,
        requested_embedding_model: Optional[str] = None,
    ) -> Optional[Path]:
        """Get path to local SQLite index if it exists."""
        if not self.is_index_enabled():
            return None

        require_selection = bool(
            requested_schema_version is not None or requested_embedding_model is not None
        )
        candidates: List[Dict[str, Any]] = []
        search_paths: List[Path] = []

        def _record_candidate(db_path: Optional[Path]) -> Optional[Path]:
            if not db_path or not db_path.exists():
                return None

            if not self._validate_sqlite_index(db_path):
                return None

            if require_selection:
                candidates.append({"path": db_path, "manifest": self.read_index_manifest(db_path)})
                return None

            return db_path

        # Try centralized storage first if enabled
        if self.storage_strategy == "centralized":
            centralized_path = self.index_manager.get_current_index_path(self.workspace_root)
            candidate = _record_candidate(centralized_path)
            if candidate:
                return candidate

        # Use multi-path discovery if enabled
        if self.enable_multi_path and self.path_config:
            # Try to determine repository identifier
            repo_id = self._get_repository_identifier()
            search_paths = self.path_config.get_search_paths(repo_id)

            logger.info(f"Searching for index in {len(search_paths)} locations")

            for search_path in search_paths:
                # Look for code_index.db in each path
                db_candidates = [
                    search_path / "code_index.db",
                    search_path / "current.db",
                    search_path / f"{repo_id}.db" if repo_id else None,
                ]

                for db_path in db_candidates:
                    candidate = _record_candidate(db_path)
                    if candidate:
                        logger.info(f"Found valid index at: {db_path}")
                        return candidate

        # Fall back to legacy local storage
        db_path = self.index_dir / "code_index.db"
        candidate = _record_candidate(db_path)
        if candidate:
            return candidate

        # Log detailed information about search failure
        if self.enable_multi_path:
            logger.warning(f"No valid index found after searching {len(search_paths)} paths")
            validation = self.path_config.validate_paths(self._get_repository_identifier())
            existing_paths = [str(p) for p, exists in validation.items() if exists]
            if existing_paths:
                logger.info(f"Existing search paths: {existing_paths}")

        if require_selection and candidates:
            return self.index_manager.select_best_index(
                candidates,
                requested_schema_version=requested_schema_version,
                requested_embedding_model=requested_embedding_model,
            )

        return None

    def _validate_sqlite_index(self, db_path: Path) -> bool:
        """Validate that a file is a valid SQLite database with expected schema."""
        try:
            conn = sqlite3.connect(str(db_path))
            # Check for expected tables
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('files', 'symbols', 'repositories')
            """
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            # Must have at least files table
            if "files" in tables:
                return True
            else:
                logger.debug(f"Index at {db_path} missing required tables")
                return False
        except Exception as e:
            logger.debug(f"Invalid SQLite index at {db_path}: {e}")
            return False

    def _get_repository_identifier(self) -> Optional[str]:
        """Get repository identifier for the current workspace."""
        # Try to get from git remote
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # Fall back to directory name
        return self.workspace_root.name

    def _get_current_commit(self) -> Optional[str]:
        """Get the current git commit hash for the workspace."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            logger.debug("Unable to resolve current git commit for manifest creation")
        return None

    def get_vector_index_path(self) -> Optional[Path]:
        """Get path to local vector index if it exists"""
        if not self.is_index_enabled():
            return None

        vector_path = self.index_dir / "vector_index"
        if vector_path.exists() and vector_path.is_dir():
            return vector_path

        return None

    def should_download_index(self) -> bool:
        """Check if we should attempt to download an index from GitHub"""
        config = self.get_index_config()
        if not config:
            return False

        # Check if auto-download is enabled
        if not config.get("auto_download", True):
            return False

        # Check if GitHub artifacts are enabled
        if not config.get("github_artifacts", {}).get("enabled", True):
            return False

        # Check if we already have a recent index
        metadata = self.get_index_metadata()
        if metadata:
            # Could check age here and decide if it's too old
            # For now, if we have an index, don't download
            return False

        return True

    def download_latest_index(self) -> bool:
        """Attempt to download the latest index from GitHub artifacts"""
        if not self.should_download_index():
            return False

        # Check if gh CLI is available
        if not self._is_gh_cli_available():
            logger.info("GitHub CLI not available, skipping index download")
            return False

        try:
            # Get repository info
            repo = self._get_repository_info()
            if not repo:
                return False

            # Find latest artifact
            artifact = self._find_latest_artifact(repo)
            if not artifact:
                logger.info("No index artifacts found")
                return False

            # Download and extract
            logger.info(f"Downloading index artifact: {artifact['name']}")
            if self._download_and_extract_artifact(repo, artifact["id"]):
                logger.info("Successfully downloaded and extracted index")
                return True

        except Exception as e:
            logger.error(f"Failed to download index: {e}")

        return False

    def _is_gh_cli_available(self) -> bool:
        """Check if GitHub CLI is available"""
        try:
            result = subprocess.run(["gh", "--version"], capture_output=True, check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _get_repository_info(self) -> Optional[str]:
        """Get the repository name in owner/repo format"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "-q",
                    ".nameWithOwner",
                ],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _find_latest_artifact(self, repo: str) -> Optional[Dict[str, Any]]:
        """Find the most recent index artifact"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    "-H",
                    "Accept: application/vnd.github+json",
                    f"/repos/{repo}/actions/artifacts",
                    "--jq",
                    '.artifacts[] | select(.name | startswith("mcp-index-")) | {id, name, created_at}',
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout:
                return None

            # Parse artifacts and find the most recent
            artifacts = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    artifacts.append(json.loads(line))

            if not artifacts:
                return None

            # Sort by creation date and return most recent
            artifacts.sort(key=lambda x: x["created_at"], reverse=True)
            return artifacts[0]

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

    def _download_and_extract_artifact(self, repo: str, artifact_id: int) -> bool:
        """Download and extract an artifact"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download artifact
                zip_path = Path(tmpdir) / "artifact.zip"
                result = subprocess.run(
                    [
                        "gh",
                        "api",
                        "-H",
                        "Accept: application/vnd.github+json",
                        f"/repos/{repo}/actions/artifacts/{artifact_id}/zip",
                    ],
                    capture_output=True,
                    check=True,
                )

                with open(zip_path, "wb") as f:
                    f.write(result.stdout)

                # Extract zip
                subprocess.run(["unzip", "-q", str(zip_path)], cwd=tmpdir, check=True)

                # Find and extract tar.gz
                tar_path = Path(tmpdir) / "mcp-index-archive.tar.gz"
                if not tar_path.exists():
                    logger.error("Archive not found in artifact")
                    return False

                # Verify checksum if available
                checksum_path = Path(tmpdir) / "mcp-index-archive.tar.gz.sha256"
                if checksum_path.exists():
                    if not self._verify_checksum(tar_path, checksum_path):
                        logger.error("Checksum verification failed")
                        return False

                # Extract to index directory
                self.index_dir.mkdir(parents=True, exist_ok=True)
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(self.index_dir)

                return True

            except Exception as e:
                logger.error(f"Failed to download/extract artifact: {e}")
                return False

    def _verify_checksum(self, file_path: Path, checksum_path: Path) -> bool:
        """Verify SHA256 checksum"""
        try:
            with open(checksum_path) as f:
                expected_checksum = f.read().split()[0]

            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)

            actual_checksum = sha256.hexdigest()
            return actual_checksum == expected_checksum

        except Exception as e:
            logger.warning(f"Checksum verification failed: {e}")
            return False

    def get_index_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the index"""
        info = {
            "enabled": self.is_index_enabled(),
            "has_local_index": False,
            "has_vector_index": False,
            "auto_download": False,
            "github_artifacts": False,
            "metadata": None,
            "config": None,
            "search_paths": [],
            "found_at": None,
        }

        if info["enabled"]:
            index_path = self.get_local_index_path()
            info["has_local_index"] = index_path is not None
            info["found_at"] = str(index_path) if index_path else None
            info["has_vector_index"] = self.get_vector_index_path() is not None
            info["metadata"] = self.get_index_metadata()
            info["config"] = self.get_index_config()

            if info["config"]:
                info["auto_download"] = info["config"].get("auto_download", True)
                info["github_artifacts"] = (
                    info["config"].get("github_artifacts", {}).get("enabled", True)
                )

            # Include search paths if multi-path is enabled
            if self.enable_multi_path and self.path_config:
                repo_id = self._get_repository_identifier()
                info["search_paths"] = [str(p) for p in self.path_config.get_search_paths(repo_id)]

        return info

    def find_all_indexes(self) -> List[Dict[str, Any]]:
        """Find all available indexes across all search paths."""
        if not self.enable_multi_path or not self.path_config:
            # Just check the default location
            index_path = self.get_local_index_path()
            if index_path:
                return [
                    {
                        "path": str(index_path),
                        "type": "sqlite",
                        "valid": True,
                        "location_type": "default",
                    }
                ]
            return []

        found_indexes = []
        repo_id = self._get_repository_identifier()
        search_paths = self.path_config.get_search_paths(repo_id)

        for search_path in search_paths:
            # Look for SQLite indexes
            for pattern in ["code_index.db", "current.db", "*.db"]:
                for db_path in search_path.glob(pattern):
                    if self._validate_sqlite_index(db_path):
                        manifest = self.read_index_manifest(db_path)
                        found_indexes.append(
                            {
                                "path": str(db_path),
                                "type": "sqlite",
                                "valid": True,
                                "location_type": self._classify_location(search_path),
                                "size_mb": db_path.stat().st_size / (1024 * 1024),
                                "manifest": manifest.to_dict() if manifest else None,
                            }
                        )

            # Look for vector indexes
            vector_path = search_path / "vector_index"
            if vector_path.exists() and vector_path.is_dir():
                found_indexes.append(
                    {
                        "path": str(vector_path),
                        "type": "vector",
                        "valid": True,
                        "location_type": self._classify_location(search_path),
                    }
                )

        return found_indexes

    def _classify_location(self, path: Path) -> str:
        """Classify the type of location for an index."""
        path_str = str(path)
        if "test_indexes" in path_str:
            return "test"
        elif "/.indexes/" in path_str or path_str.endswith(".indexes"):
            return "centralized"
        elif "/.mcp-index" in path_str:
            return "legacy"
        elif "/tmp/" in path_str:
            return "temporary"
        elif path_str.startswith(str(Path.home())):
            return "user"
        elif "/workspaces/" in path_str:
            return "docker"
        else:
            return "other"

    @staticmethod
    def discover_indexes(search_paths: List[Path]) -> List[Tuple[Path, Dict[str, Any]]]:
        """Discover all MCP indexes in the given search paths"""
        discovered = []

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Look for .mcp-index.json files
            for config_file in search_path.rglob(".mcp-index.json"):
                workspace = config_file.parent
                discovery = IndexDiscovery(workspace)
                info = discovery.get_index_info()

                if info["enabled"] and info["has_local_index"]:
                    discovered.append((workspace, info))

        return discovered
