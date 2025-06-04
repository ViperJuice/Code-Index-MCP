"""Smart indexing handler that automatically sets up and uses pre-built indexes."""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import json

from mcp_server.tools.base import BaseTool
from mcp_server.tools.schemas import ToolResult
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.config.settings import Settings


class SmartIndexTool(BaseTool):
    """Intelligently handles indexing with automatic setup and remote index usage."""
    
    name = "index_project"
    description = "Index a project with automatic setup and pre-built index support"
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.index_cache = {}
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Smart indexing with automatic setup."""
        project_path = Path(arguments.get("path", ".")).resolve()
        force_rebuild = arguments.get("force_rebuild", False)
        
        # Determine index location
        project_name = project_path.name
        index_dir = Path.home() / ".mcp" / "indexes" / project_name
        
        # Check if already indexed and not forcing rebuild
        if not force_rebuild and self._is_indexed(index_dir):
            return ToolResult(
                success=True,
                data={
                    "status": "already_indexed",
                    "index_path": str(index_dir),
                    "message": f"Project already indexed at {index_dir}"
                }
            )
        
        # Try to get pre-built index
        if not force_rebuild:
            remote_result = await self._try_remote_index(project_path, index_dir)
            if remote_result:
                return remote_result
        
        # Fall back to local indexing
        return await self._build_local_index(project_path, index_dir)
    
    def _is_indexed(self, index_dir: Path) -> bool:
        """Check if valid index exists."""
        return (index_dir / "code_index.db").exists()
    
    async def _try_remote_index(self, project_path: Path, index_dir: Path) -> Optional[ToolResult]:
        """Try to download pre-built index from remote."""
        try:
            # Check if it's a git repository
            git_dir = project_path / ".git"
            if not git_dir.exists():
                return None
            
            # Get remote info
            os.chdir(project_path)
            
            # Check for remote
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # Try to fetch mcp-index branch
            fetch_result = subprocess.run(
                ["git", "fetch", "origin", "mcp-index", "--depth=1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if fetch_result.returncode != 0:
                return None
            
            # Download index
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract index file
                extract_result = subprocess.run(
                    ["git", "checkout", "origin/mcp-index", "--", "mcp-index-latest.tar.gz"],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )
                
                if extract_result.returncode != 0:
                    # Try alternate locations
                    extract_result = subprocess.run(
                        ["git", "archive", "--remote=origin", "mcp-index", "mcp-index-latest.tar.gz"],
                        capture_output=True,
                        cwd=temp_dir
                    )
                    
                    if extract_result.returncode != 0:
                        return None
                
                # Extract to index directory
                index_file = Path(temp_dir) / "mcp-index-latest.tar.gz"
                if index_file.exists():
                    index_dir.mkdir(parents=True, exist_ok=True)
                    
                    subprocess.run(
                        ["tar", "-xzf", str(index_file), "-C", str(index_dir)],
                        check=True
                    )
                    
                    # Verify extraction
                    if self._is_indexed(index_dir):
                        # Set up git hooks for future updates
                        self._setup_git_hooks(project_path)
                        
                        return ToolResult(
                            success=True,
                            data={
                                "status": "remote_index_downloaded",
                                "index_path": str(index_dir),
                                "message": "Successfully downloaded pre-built index from remote"
                            }
                        )
        
        except Exception as e:
            # Silently fail and fall back to local indexing
            pass
        
        return None
    
    async def _build_local_index(self, project_path: Path, index_dir: Path) -> ToolResult:
        """Build index locally."""
        try:
            index_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure settings for this index
            settings = Settings()
            settings.DATABASE_URL = f"sqlite:///{index_dir}/code_index.db"
            settings.CACHE_DIR = str(index_dir / "cache")
            
            # Create index engine
            engine = IndexEngine(settings)
            
            # Index the project
            engine.index_directory(project_path)
            
            # Save metadata
            metadata = {
                "version": "1.0",
                "path": str(project_path),
                "created": str(Path.cwd()),
                "type": "local_build"
            }
            
            with open(index_dir / "index_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Set up git hooks for future updates
            if (project_path / ".git").exists():
                self._setup_git_hooks(project_path)
            
            return ToolResult(
                success=True,
                data={
                    "status": "locally_indexed",
                    "index_path": str(index_dir),
                    "message": f"Successfully built local index at {index_dir}"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to build index: {str(e)}"
            )
    
    def _setup_git_hooks(self, project_path: Path):
        """Set up git hooks for automatic index updates."""
        try:
            # Check if setup script exists
            setup_script = project_path / "scripts" / "setup-git-hooks.sh"
            if setup_script.exists():
                subprocess.run(
                    ["bash", str(setup_script)],
                    cwd=project_path,
                    capture_output=True
                )
            else:
                # Basic git config for hooks
                subprocess.run(
                    ["git", "config", "core.hooksPath", ".githooks"],
                    cwd=project_path,
                    capture_output=True
                )
        except:
            # Silently fail - hooks are optional
            pass
    
    @property
    def json_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the project to index"
                },
                "force_rebuild": {
                    "type": "boolean",
                    "description": "Force rebuild even if index exists",
                    "default": False
                }
            },
            "required": ["path"]
        }