"""
Enhanced index_file handler that automatically sets up indexes.

This wraps the original index_file handler to provide automatic setup
including downloading pre-built indexes from git remotes.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SmartIndexWrapper:
    """Wrapper that adds automatic index setup to index_file tool."""
    
    def __init__(self, original_handler):
        self.original_handler = original_handler
        self._indexed_paths = set()
        
    async def __call__(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrap index_file to add automatic setup.
        
        First checks if the path has an index, and if not:
        1. Tries to download pre-built index from git remote
        2. Falls back to the original indexing
        """
        path = Path(params.get("path", ".")).resolve()
        
        # Check if we need to run smart setup
        if self._should_run_smart_setup(path):
            logger.info(f"First time indexing {path} - running smart setup")
            
            # Try to run our smart setup script
            setup_result = self._run_smart_setup(path)
            
            if setup_result:
                # Smart setup succeeded - index is ready
                self._indexed_paths.add(str(path))
                
                return {
                    "operation_id": "smart_setup",
                    "path": str(path),
                    "statistics": {
                        "status": "index_ready",
                        "message": "Index successfully set up from remote or built locally",
                        "index_path": self._get_index_path(path)
                    },
                    "progress": {
                        "percentage": 100.0,
                        "processed_files": 1,
                        "failed_files": 0,
                        "success_rate": 100.0
                    }
                }
        
        # Run original handler (for incremental updates or if smart setup wasn't needed)
        return await self.original_handler(params, context)
    
    def _should_run_smart_setup(self, path: Path) -> bool:
        """Check if we should run smart setup for this path."""
        # Skip if we've already indexed this path in this session
        if str(path) in self._indexed_paths:
            return False
            
        # Check if index already exists
        index_path = self._get_index_path(path)
        if (index_path / "code_index.db").exists():
            self._indexed_paths.add(str(path))
            return False
            
        return True
    
    def _get_index_path(self, project_path: Path) -> Path:
        """Get the index path for a project."""
        # Match the logic from our smart setup script
        repo_name = project_path.name
        
        # Try to get from git remote
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                url = result.stdout.strip()
                if url.endswith('.git'):
                    url = url[:-4]
                repo_name = os.path.basename(url)
        except:
            pass
            
        return Path.home() / ".mcp" / "indexes" / repo_name
    
    def _run_smart_setup(self, project_path: Path) -> bool:
        """
        Run the smart setup process.
        
        Returns True if setup succeeded, False otherwise.
        """
        try:
            # First, check if it's a git repo and try to download remote index
            if (project_path / ".git").exists():
                # Try to fetch mcp-index branch
                result = subprocess.run(
                    ["git", "fetch", "origin", "mcp-index", "--depth=1"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Try to download the index
                    logger.info("Found remote index, downloading...")
                    
                    # Check out index file
                    result = subprocess.run(
                        ["git", "checkout", "origin/mcp-index", "--", "mcp-index-latest.tar.gz"],
                        cwd=project_path,
                        capture_output=True
                    )
                    
                    if result.returncode == 0 and (project_path / "mcp-index-latest.tar.gz").exists():
                        # Extract index
                        index_path = self._get_index_path(project_path)
                        index_path.mkdir(parents=True, exist_ok=True)
                        
                        result = subprocess.run(
                            ["tar", "-xzf", "mcp-index-latest.tar.gz", "-C", str(index_path)],
                            cwd=project_path,
                            capture_output=True
                        )
                        
                        # Clean up
                        (project_path / "mcp-index-latest.tar.gz").unlink(missing_ok=True)
                        
                        if result.returncode == 0:
                            logger.info(f"Successfully downloaded pre-built index to {index_path}")
                            self._setup_git_hooks(project_path)
                            return True
            
            # If we get here, no remote index was available
            # The original handler will build it locally
            logger.info("No remote index found, will build locally")
            return False
            
        except Exception as e:
            logger.warning(f"Smart setup encountered error: {e}")
            # Fall back to original handler
            return False
    
    def _setup_git_hooks(self, project_path: Path):
        """Set up git hooks for automatic updates."""
        try:
            # Check if setup script exists
            setup_script = project_path / "scripts" / "setup-git-hooks.sh"
            if setup_script.exists():
                subprocess.run(
                    ["bash", str(setup_script)],
                    cwd=project_path,
                    capture_output=True,
                    timeout=10
                )
                logger.info("Git hooks configured for automatic index updates")
        except:
            # Git hooks are optional, don't fail
            pass


def wrap_index_handler(original_handler):
    """
    Wrap the original index_file handler with smart setup.
    
    This function is called by the tool registry to enhance the handler.
    """
    return SmartIndexWrapper(original_handler)