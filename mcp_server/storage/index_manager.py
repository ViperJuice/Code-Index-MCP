"""
Index Manager for MCP Storage

Provides centralized index management functionality for the MCP server.
This is a minimal implementation to support IndexDiscovery operations.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import hashlib
from mcp_server.core.path_utils import PathUtils

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages index storage and retrieval for MCP operations."""
    
    def __init__(self, storage_strategy: str = "inline"):
        """
        Initialize index manager.
        
        Args:
            storage_strategy: Strategy for index storage ('inline', 'centralized', etc.)
        """
        self.storage_strategy = storage_strategy
        self.base_storage_path = self._get_base_storage_path()
        
    def _get_base_storage_path(self) -> Path:
        """Get the base path for index storage based on strategy."""
        if self.storage_strategy == "centralized":
            # Check environment variable first
            env_path = os.environ.get("MCP_INDEX_STORAGE_PATH")
            if env_path:
                return Path(env_path)
                
            # Default centralized locations
            centralized_paths = [
                Path.home() / ".mcp" / "indexes",
                Path("/tmp/mcp-indexes"),
                Path.cwd() / ".indexes"
            ]
            
            for path in centralized_paths:
                if path.exists() or path.parent.exists():
                    return path
                    
            # Default to first option
            return centralized_paths[0]
        else:
            # For inline storage, use current directory
            return Path.cwd() / ".mcp-index"
            
    def get_current_index_path(self, workspace_root: Path) -> Optional[Path]:
        """
        Get the path to the current index for a workspace.
        
        Args:
            workspace_root: Root directory of the workspace
            
        Returns:
            Path to the current index, or None if not found
        """
        # Priority search paths in order
        search_paths = [
            # First check data directory (where our actual index is)
            workspace_root / "data" / "code_index.db",
            workspace_root / "data" / "current.db",
            
            # Then check centralized storage if enabled
            self.base_storage_path / "code_index.db" if self.storage_strategy == "centralized" else None,
            self.base_storage_path / "current.db" if self.storage_strategy == "centralized" else None,
            
            # For centralized with repo ID
            None,  # Will be filled below
            None,  # Will be filled below
            
            # Finally check legacy inline storage
            workspace_root / ".mcp-index" / "code_index.db",
            workspace_root / ".mcp-index" / "current.db",
        ]
        
        # Add centralized with repo ID paths
        if self.storage_strategy == "centralized":
            repo_id = self._get_repo_identifier(workspace_root)
            if repo_id:
                search_paths[4] = self.base_storage_path / repo_id / "current.db"
                search_paths[5] = self.base_storage_path / repo_id / "code_index.db"
        
        # Search all paths
        for path in search_paths:
            if path and path.exists() and self._validate_index(path):
                logger.info(f"Found valid index at: {path}")
                return path
                
        logger.warning(f"No valid index found in {len([p for p in search_paths if p])} searched locations")
        return None
        
    def _get_repo_identifier(self, workspace_root: Path) -> Optional[str]:
        """Get repository identifier for workspace."""
        try:
            # Try to get git remote URL
            import subprocess
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=str(workspace_root),
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                # Create hash from URL
                return hashlib.sha256(url.encode()).hexdigest()[:12]
        except:
            pass
            
        # Fall back to directory name hash
        return hashlib.sha256(str(workspace_root).encode()).hexdigest()[:12]
        
    def _validate_index(self, index_path: Path) -> bool:
        """Validate that an index file is a valid SQLite database."""
        try:
            conn = sqlite3.connect(str(index_path))
            # Check for expected tables
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('files', 'symbols', 'bm25_content')
            """)
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()
            
            # Must have at least files table
            return 'files' in tables
        except Exception as e:
            logger.debug(f"Index validation failed for {index_path}: {e}")
            return False
            
    def list_available_indexes(self) -> List[Dict[str, Any]]:
        """List all available indexes in the storage system."""
        indexes = []
        
        if self.storage_strategy == "centralized" and self.base_storage_path.exists():
            # Look for indexes in centralized storage
            for repo_dir in self.base_storage_path.iterdir():
                if repo_dir.is_dir():
                    for db_file in repo_dir.glob("*.db"):
                        if self._validate_index(db_file):
                            indexes.append({
                                "path": str(db_file),
                                "repo_id": repo_dir.name,
                                "size": db_file.stat().st_size,
                                "modified": db_file.stat().st_mtime,
                                "storage_type": "centralized"
                            })
                            
        return indexes
        
    def create_index_symlink(self, source_path: Path, target_path: Path) -> bool:
        """Create a symlink from target to source index."""
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                target_path.unlink()
            target_path.symlink_to(source_path)
            logger.info(f"Created index symlink: {target_path} -> {source_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False