#!/usr/bin/env python3
"""Sync existing indexes with their Git repositories."""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.git_index_manager import GitAwareIndexManager
from mcp_server.indexing.change_detector import ChangeDetector


class IndexGitSynchronizer:
    """Synchronize indexes with their Git repositories."""
    
    def __init__(self):
        self.indexes_path = Path(".indexes")
        self.registry = RepositoryRegistry()
        self.results = {
            "synced": [],
            "missing_repo": [],
            "errors": [],
            "stats": {}
        }
    
    def find_repository_path(self, index_id: str, db_path: Path) -> Optional[Path]:
        """Try to find the repository path for an index."""
        
        # Strategy 1: Check registry
        repo_info = self.registry.get_repository(index_id)
        if repo_info and Path(repo_info.path).exists():
            return Path(repo_info.path)
        
        # Strategy 2: Check database for file paths
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get a sample file path
            cursor.execute("SELECT filepath FROM bm25_content LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                file_path = Path(result[0])
                # Try to find git root from file path
                if file_path.is_absolute():
                    current = file_path.parent
                    while current != current.parent:
                        if (current / ".git").exists():
                            return current
                        current = current.parent
        except:
            pass
        
        # Strategy 3: Check test_repos directory
        test_repos = Path("test_repos")
        if test_repos.exists():
            for category in test_repos.iterdir():
                if category.is_dir():
                    for repo in category.iterdir():
                        if repo.is_dir() and (repo / ".git").exists():
                            # Check if this repo matches the index
                            repo_id = self.get_repo_id(repo)
                            if repo_id == index_id[:12]:
                                return repo
        
        return None
    
    def get_repo_id(self, repo_path: Path) -> str:
        """Get repository ID from path."""
        import hashlib
        try:
            # Try to get remote URL
            result = subprocess.run(
                ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
        except:
            # Fall back to path hash
            return hashlib.sha256(str(repo_path).encode()).hexdigest()[:12]
    
    def get_git_info(self, repo_path: Path) -> Dict[str, str]:
        """Get current Git information."""
        try:
            # Get current commit
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            commit = result.stdout.strip()
            
            # Get current branch
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "-C", str(repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            has_changes = bool(result.stdout.strip())
            
            return {
                "commit": commit,
                "branch": branch,
                "has_changes": has_changes,
                "synced_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def sync_index(self, index_id: str, db_path: Path) -> Dict[str, any]:
        """Sync a single index with its repository."""
        
        # Find repository path
        repo_path = self.find_repository_path(index_id, db_path)
        
        if not repo_path:
            return {
                "status": "missing_repo",
                "index_id": index_id,
                "error": "Could not find repository path"
            }
        
        # Get Git info
        git_info = self.get_git_info(repo_path)
        
        if "error" in git_info:
            return {
                "status": "error",
                "index_id": index_id,
                "repo_path": str(repo_path),
                "error": git_info["error"]
            }
        
        # Update index metadata
        try:
            metadata_path = db_path.parent / "metadata.json"
            metadata = {}
            
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            
            metadata.update({
                "git": git_info,
                "repository_path": str(repo_path),
                "last_sync": datetime.now().isoformat()
            })
            
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Register with repository registry if not already
            if not self.registry.get_repository(index_id):
                self.registry.register_repository(str(repo_path))
            
            return {
                "status": "synced",
                "index_id": index_id,
                "repo_path": str(repo_path),
                "git_info": git_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "index_id": index_id,
                "repo_path": str(repo_path),
                "error": str(e)
            }
    
    def sync_all_indexes(self):
        """Sync all populated indexes with their repositories."""
        
        print("SYNCING INDEXES WITH GIT REPOSITORIES")
        print("=" * 80)
        
        # Find all indexes
        populated_indexes = []
        
        for repo_dir in self.indexes_path.iterdir():
            if not repo_dir.is_dir():
                continue
            
            db_path = repo_dir / "current.db"
            if not db_path.exists():
                continue
            
            # Check if populated
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
                conn.close()
                
                if file_count > 0:
                    populated_indexes.append({
                        "id": repo_dir.name,
                        "db_path": db_path,
                        "file_count": file_count
                    })
            except:
                continue
        
        print(f"\nFound {len(populated_indexes)} populated indexes")
        
        # Sync each index
        for idx, index_info in enumerate(populated_indexes):
            print(f"\n[{idx+1}/{len(populated_indexes)}] Syncing {index_info['id']}...")
            
            result = self.sync_index(index_info['id'], index_info['db_path'])
            
            if result['status'] == 'synced':
                print(f"  ✓ Synced with {result['repo_path']}")
                print(f"    Commit: {result['git_info']['commit'][:8]}")
                print(f"    Branch: {result['git_info']['branch']}")
                self.results['synced'].append(result)
            elif result['status'] == 'missing_repo':
                print(f"  ⚠️ Could not find repository")
                self.results['missing_repo'].append(result)
            else:
                print(f"  ❌ Error: {result['error']}")
                self.results['errors'].append(result)
        
        # Summary
        print("\n" + "="*80)
        print("SYNC SUMMARY")
        print("="*80)
        print(f"Total indexes: {len(populated_indexes)}")
        print(f"Successfully synced: {len(self.results['synced'])}")
        print(f"Missing repositories: {len(self.results['missing_repo'])}")
        print(f"Errors: {len(self.results['errors'])}")
        
        # Save results
        with open("index_sync_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed results saved to: index_sync_results.json")


def main():
    """Run the synchronization."""
    synchronizer = IndexGitSynchronizer()
    synchronizer.sync_all_indexes()


if __name__ == "__main__":
    main()