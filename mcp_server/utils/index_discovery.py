"""
Portable Index Discovery for MCP
Automatically detects and uses indexes created by mcp-index-kit
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import logging
import sqlite3
import tarfile
import hashlib

logger = logging.getLogger(__name__)


class IndexDiscovery:
    """Discovers and manages portable MCP indexes in repositories"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.index_dir = self.workspace_root / '.mcp-index'
        self.config_file = self.workspace_root / '.mcp-index.json'
        self.metadata_file = self.index_dir / '.index_metadata.json'
        
    def is_index_enabled(self) -> bool:
        """Check if MCP indexing is enabled for this repository"""
        # Check environment variable first
        if os.getenv('MCP_INDEX_ENABLED', '').lower() == 'false':
            return False
            
        # Check config file
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return config.get('enabled', True)
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
    
    def get_local_index_path(self) -> Optional[Path]:
        """Get path to local SQLite index if it exists"""
        if not self.is_index_enabled():
            return None
            
        db_path = self.index_dir / 'code_index.db'
        if db_path.exists():
            # Validate it's a valid SQLite database
            try:
                conn = sqlite3.connect(str(db_path))
                conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                conn.close()
                return db_path
            except Exception as e:
                logger.warning(f"Invalid SQLite index at {db_path}: {e}")
                
        return None
    
    def get_vector_index_path(self) -> Optional[Path]:
        """Get path to local vector index if it exists"""
        if not self.is_index_enabled():
            return None
            
        vector_path = self.index_dir / 'vector_index'
        if vector_path.exists() and vector_path.is_dir():
            return vector_path
            
        return None
    
    def should_download_index(self) -> bool:
        """Check if we should attempt to download an index from GitHub"""
        config = self.get_index_config()
        if not config:
            return False
            
        # Check if auto-download is enabled
        if not config.get('auto_download', True):
            return False
            
        # Check if GitHub artifacts are enabled
        if not config.get('github_artifacts', {}).get('enabled', True):
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
            if self._download_and_extract_artifact(repo, artifact['id']):
                logger.info("Successfully downloaded and extracted index")
                return True
                
        except Exception as e:
            logger.error(f"Failed to download index: {e}")
            
        return False
    
    def _is_gh_cli_available(self) -> bool:
        """Check if GitHub CLI is available"""
        try:
            result = subprocess.run(['gh', '--version'], 
                                  capture_output=True, 
                                  check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _get_repository_info(self) -> Optional[str]:
        """Get the repository name in owner/repo format"""
        try:
            result = subprocess.run(
                ['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'],
                capture_output=True,
                text=True,
                cwd=str(self.workspace_root),
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _find_latest_artifact(self, repo: str) -> Optional[Dict[str, Any]]:
        """Find the most recent index artifact"""
        try:
            result = subprocess.run([
                'gh', 'api',
                '-H', 'Accept: application/vnd.github+json',
                f'/repos/{repo}/actions/artifacts',
                '--jq', '.artifacts[] | select(.name | startswith("mcp-index-")) | {id, name, created_at}'
            ], capture_output=True, text=True, check=True)
            
            if not result.stdout:
                return None
                
            # Parse artifacts and find the most recent
            artifacts = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    artifacts.append(json.loads(line))
                    
            if not artifacts:
                return None
                
            # Sort by creation date and return most recent
            artifacts.sort(key=lambda x: x['created_at'], reverse=True)
            return artifacts[0]
            
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None
    
    def _download_and_extract_artifact(self, repo: str, artifact_id: int) -> bool:
        """Download and extract an artifact"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Download artifact
                zip_path = Path(tmpdir) / 'artifact.zip'
                result = subprocess.run([
                    'gh', 'api',
                    '-H', 'Accept: application/vnd.github+json',
                    f'/repos/{repo}/actions/artifacts/{artifact_id}/zip'
                ], capture_output=True, check=True)
                
                with open(zip_path, 'wb') as f:
                    f.write(result.stdout)
                
                # Extract zip
                subprocess.run(['unzip', '-q', str(zip_path)], 
                             cwd=tmpdir, 
                             check=True)
                
                # Find and extract tar.gz
                tar_path = Path(tmpdir) / 'mcp-index-archive.tar.gz'
                if not tar_path.exists():
                    logger.error("Archive not found in artifact")
                    return False
                
                # Verify checksum if available
                checksum_path = Path(tmpdir) / 'mcp-index-archive.tar.gz.sha256'
                if checksum_path.exists():
                    if not self._verify_checksum(tar_path, checksum_path):
                        logger.error("Checksum verification failed")
                        return False
                
                # Extract to index directory
                self.index_dir.mkdir(parents=True, exist_ok=True)
                with tarfile.open(tar_path, 'r:gz') as tar:
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
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    sha256.update(chunk)
                    
            actual_checksum = sha256.hexdigest()
            return actual_checksum == expected_checksum
            
        except Exception as e:
            logger.warning(f"Checksum verification failed: {e}")
            return False
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the index"""
        info = {
            'enabled': self.is_index_enabled(),
            'has_local_index': False,
            'has_vector_index': False,
            'auto_download': False,
            'github_artifacts': False,
            'metadata': None,
            'config': None
        }
        
        if info['enabled']:
            info['has_local_index'] = self.get_local_index_path() is not None
            info['has_vector_index'] = self.get_vector_index_path() is not None
            info['metadata'] = self.get_index_metadata()
            info['config'] = self.get_index_config()
            
            if info['config']:
                info['auto_download'] = info['config'].get('auto_download', True)
                info['github_artifacts'] = info['config'].get('github_artifacts', {}).get('enabled', True)
                
        return info
    
    @staticmethod
    def discover_indexes(search_paths: List[Path]) -> List[Tuple[Path, Dict[str, Any]]]:
        """Discover all MCP indexes in the given search paths"""
        discovered = []
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            # Look for .mcp-index.json files
            for config_file in search_path.rglob('.mcp-index.json'):
                workspace = config_file.parent
                discovery = IndexDiscovery(workspace)
                info = discovery.get_index_info()
                
                if info['enabled'] and info['has_local_index']:
                    discovered.append((workspace, info))
                    
        return discovered