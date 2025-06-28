#!/usr/bin/env python3
"""
Index remaining repositories, skipping very large ones.
Focuses on completing small to medium repositories first.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Large repositories to skip
SKIP_LARGE_REPOS = {
    'grpc', 'TypeScript', 'react', 'django', 'aspnetcore', 
    'rails', 'laravel', 'spring-boot'
}


def get_progress():
    """Load current progress."""
    progress_file = "semantic_indexing_progress.json"
    if Path(progress_file).exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
            return progress.get("completed", {}), progress.get("in_progress")
    return {}, None


def get_all_repos():
    """Get list of all repositories."""
    repos = []
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    
    for repo_path in test_repos_dir.rglob('.git'):
        if repo_path.is_dir():
            repo_dir = repo_path.parent
            repo_name = repo_dir.name
            repos.append(repo_name)
    
    return repos


def main():
    """Main function to show remaining work."""
    completed, in_progress = get_progress()
    all_repos = get_all_repos()
    
    logger.info("Semantic Indexing Progress Report")
    logger.info("="*60)
    
    # Completed repositories
    logger.info(f"\n✅ Completed ({len(completed)} repositories):")
    total_files = 0
    total_embeddings = 0
    
    for key, info in completed.items():
        total_files += info['files_processed']
        total_embeddings += info['embeddings']
        logger.info(f"  {info['repo']}: {info['files_processed']} files → {info['embeddings']:,} embeddings")
    
    logger.info(f"\nTotal: {total_files:,} files → {total_embeddings:,} embeddings")
    
    # In progress
    if in_progress:
        logger.info(f"\n🔄 In Progress:")
        logger.info(f"  {in_progress['repo_key']}: {len(in_progress['processed_files'])} files processed so far")
    
    # Remaining repositories
    completed_names = {info['repo'] for info in completed.values()}
    if in_progress:
        completed_names.add(in_progress['repo_key'].split('_', 1)[1])
    
    remaining = [r for r in all_repos if r not in completed_names]
    
    logger.info(f"\n📋 Remaining ({len(remaining)} repositories):")
    
    # Categorize by size
    small_repos = []
    large_repos = []
    
    for repo in remaining:
        if repo in SKIP_LARGE_REPOS:
            large_repos.append(repo)
        else:
            small_repos.append(repo)
    
    if small_repos:
        logger.info(f"\n  Small/Medium (ready to process): {len(small_repos)}")
        for repo in sorted(small_repos):
            logger.info(f"    - {repo}")
    
    if large_repos:
        logger.info(f"\n  Large (requires dedicated processing): {len(large_repos)}")
        for repo in sorted(large_repos):
            logger.info(f"    - {repo} ⚠️")
    
    # Next steps
    logger.info("\n" + "="*60)
    logger.info("Next Steps:")
    logger.info("1. Continue running: python scripts/index_all_repos_complete.py")
    logger.info("2. It will resume from where it left off")
    logger.info(f"3. Consider skipping large repos: {', '.join(sorted(large_repos))}")
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "completed": len(completed),
        "total_files": total_files,
        "total_embeddings": total_embeddings,
        "remaining": len(remaining),
        "remaining_small": len(small_repos),
        "remaining_large": len(large_repos),
        "repositories": {
            "completed": list(completed_names),
            "remaining_small": sorted(small_repos),
            "remaining_large": sorted(large_repos)
        }
    }
    
    with open("indexing_progress_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nSummary saved to: indexing_progress_summary.json")


if __name__ == "__main__":
    main()