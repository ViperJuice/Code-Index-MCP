#!/usr/bin/env python3
"""
Script to download and prepare real-world GitHub repositories for testing.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test repository configurations
TEST_REPOSITORIES = {
    "tier1": {
        "requests": {
            "url": "https://github.com/psf/requests.git",
            "description": "Python HTTP library",
            "expected_files": 50,
            "languages": ["python"]
        },
        "django": {
            "url": "https://github.com/django/django.git", 
            "description": "Python web framework",
            "expected_files": 2000,
            "languages": ["python"]
        },
        "react": {
            "url": "https://github.com/facebook/react.git",
            "description": "JavaScript UI library", 
            "expected_files": 800,
            "languages": ["javascript", "typescript"]
        },
        "vscode": {
            "url": "https://github.com/microsoft/vscode.git",
            "description": "TypeScript editor",
            "expected_files": 3000,
            "languages": ["typescript", "javascript"]
        },
        "terminal": {
            "url": "https://github.com/microsoft/terminal.git",
            "description": "C++ terminal application",
            "expected_files": 800,
            "languages": ["cpp", "c"]
        },
        "kubernetes": {
            "url": "https://github.com/kubernetes/kubernetes.git",
            "description": "Go orchestration platform",
            "expected_files": 8000,
            "languages": ["go", "yaml", "shell"]
        }
    },
    "tier2": {
        "linux": {
            "url": "https://github.com/torvalds/linux.git",
            "description": "Linux kernel",
            "expected_files": 70000,
            "languages": ["c"],
            "subset_size": 5000  # Create subset for testing
        },
        "git": {
            "url": "https://github.com/git/git.git",
            "description": "Git version control",
            "expected_files": 900,
            "languages": ["c"]
        }
    }
}


class RepositoryDownloader:
    """Download and prepare test repositories."""
    
    def __init__(self, workspace_dir: str = "test_workspace/real_repos"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
    def download_repository(self, name: str, config: Dict, shallow: bool = True) -> bool:
        """Download a single repository."""
        repo_path = self.workspace_dir / name
        
        if repo_path.exists():
            logger.info(f"Repository {name} already exists, skipping download")
            return True
            
        logger.info(f"Downloading {name}: {config['description']}")
        
        try:
            # Clone repository (shallow for speed)
            cmd = ["git", "clone"]
            if shallow:
                cmd.extend(["--depth=1"])
            cmd.extend([config["url"], str(repo_path)])
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                file_count = self._count_source_files(repo_path, config["languages"])
                logger.info(f"✅ Downloaded {name} in {duration:.1f}s ({file_count} source files)")
                
                # Create subset if specified
                if "subset_size" in config:
                    self._create_subset(repo_path, config["subset_size"], config["languages"])
                
                return True
            else:
                logger.error(f"❌ Failed to download {name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout downloading {name}")
            return False
        except Exception as e:
            logger.error(f"❌ Error downloading {name}: {e}")
            return False
    
    def _count_source_files(self, repo_path: Path, languages: List[str]) -> int:
        """Count source files for given languages."""
        extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
            "go": [".go"],
            "yaml": [".yml", ".yaml"],
            "shell": [".sh", ".bash"]
        }
        
        target_extensions = []
        for lang in languages:
            target_extensions.extend(extensions.get(lang, []))
        
        count = 0
        for ext in target_extensions:
            count += len(list(repo_path.rglob(f"*{ext}")))
        
        return count
    
    def _create_subset(self, repo_path: Path, subset_size: int, languages: List[str]) -> None:
        """Create a subset of a large repository for testing."""
        subset_path = repo_path.parent / f"{repo_path.name}_subset"
        subset_path.mkdir(exist_ok=True)
        
        logger.info(f"Creating subset of {repo_path.name} with {subset_size} files")
        
        # Find all source files
        source_files = []
        extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx"], 
            "typescript": [".ts", ".tsx"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp"],
            "go": [".go"]
        }
        
        for lang in languages:
            for ext in extensions.get(lang, []):
                source_files.extend(repo_path.rglob(f"*{ext}"))
        
        # Select subset (prioritize smaller files for faster testing)
        source_files.sort(key=lambda f: f.stat().st_size)
        selected_files = source_files[:subset_size]
        
        # Copy files to subset directory
        for file_path in selected_files:
            try:
                relative_path = file_path.relative_to(repo_path)
                dest_path = subset_path / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file content
                dest_path.write_bytes(file_path.read_bytes())
                
            except Exception as e:
                logger.warning(f"Failed to copy {file_path}: {e}")
        
        logger.info(f"Created subset with {len(selected_files)} files")
    
    def download_all(self, tier: Optional[str] = None) -> Dict[str, bool]:
        """Download all repositories or a specific tier."""
        results = {}
        
        if tier:
            repos = {tier: TEST_REPOSITORIES[tier]}
        else:
            repos = TEST_REPOSITORIES
        
        for tier_name, tier_repos in repos.items():
            logger.info(f"Downloading {tier_name} repositories...")
            
            for name, config in tier_repos.items():
                success = self.download_repository(name, config)
                results[name] = success
        
        return results
    
    def validate_downloads(self) -> Dict[str, Dict]:
        """Validate that downloaded repositories are complete."""
        validation_results = {}
        
        for tier_name, tier_repos in TEST_REPOSITORIES.items():
            for name, config in tier_repos.items():
                repo_path = self.workspace_dir / name
                
                result = {
                    "exists": repo_path.exists(),
                    "file_count": 0,
                    "size_mb": 0,
                    "valid": False
                }
                
                if repo_path.exists():
                    # Count source files
                    result["file_count"] = self._count_source_files(repo_path, config["languages"])
                    
                    # Calculate directory size
                    total_size = sum(f.stat().st_size for f in repo_path.rglob("*") if f.is_file())
                    result["size_mb"] = total_size / (1024 * 1024)
                    
                    # Validate file count (allow 20% variance)
                    expected_files = config["expected_files"]
                    result["valid"] = result["file_count"] >= expected_files * 0.2
                
                validation_results[name] = result
        
        return validation_results
    
    def cleanup_repositories(self, repos: Optional[List[str]] = None) -> None:
        """Clean up downloaded repositories."""
        if repos is None:
            # Remove entire workspace
            if self.workspace_dir.exists():
                logger.info(f"Removing workspace directory: {self.workspace_dir}")
                subprocess.run(["rm", "-rf", str(self.workspace_dir)])
        else:
            # Remove specific repositories
            for repo in repos:
                repo_path = self.workspace_dir / repo
                if repo_path.exists():
                    logger.info(f"Removing repository: {repo}")
                    subprocess.run(["rm", "-rf", str(repo_path)])


def main():
    """Main entry point for repository download."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download test repositories for MCP Server testing")
    parser.add_argument("--tier", choices=["tier1", "tier2"], help="Download specific tier only")
    parser.add_argument("--validate", action="store_true", help="Validate downloaded repositories")
    parser.add_argument("--cleanup", action="store_true", help="Clean up downloaded repositories")
    parser.add_argument("--workspace", default="test_workspace/real_repos", help="Workspace directory")
    
    args = parser.parse_args()
    
    downloader = RepositoryDownloader(args.workspace)
    
    if args.cleanup:
        downloader.cleanup_repositories()
        logger.info("Cleanup completed")
        return
    
    if args.validate:
        logger.info("Validating downloaded repositories...")
        results = downloader.validate_downloads()
        
        print("\n📊 Repository Validation Results:")
        print("-" * 60)
        
        for name, result in results.items():
            status = "✅" if result["valid"] else "❌"
            if result["exists"]:
                print(f"{status} {name:15s} | {result['file_count']:5d} files | {result['size_mb']:6.1f} MB")
            else:
                print(f"❌ {name:15s} | Not downloaded")
        
        return
    
    # Download repositories
    logger.info("Starting repository download process...")
    start_time = time.time()
    
    results = downloader.download_all(args.tier)
    
    duration = time.time() - start_time
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"\n📋 Download Summary:")
    print(f"✅ Successfully downloaded: {success_count}/{total_count} repositories")
    print(f"⏱️  Total time: {duration:.1f} seconds")
    
    # Show validation results
    validation_results = downloader.validate_downloads()
    print(f"\n📊 Repository Status:")
    print("-" * 60)
    
    for name, result in validation_results.items():
        status = "✅" if result["valid"] else "❌"
        if result["exists"]:
            print(f"{status} {name:15s} | {result['file_count']:5d} files | {result['size_mb']:6.1f} MB")
    
    if success_count == total_count:
        print(f"\n🎉 All repositories downloaded successfully!")
        print(f"Ready to run real-world tests with: python run_parallel_tests.py --phases real_world_validation")
    else:
        failed_repos = [name for name, success in results.items() if not success]
        print(f"\n⚠️  Some repositories failed to download: {failed_repos}")


if __name__ == "__main__":
    main()