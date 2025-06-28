#!/usr/bin/env python3
"""
Continue MCP-based indexing with better timeout handling.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
import subprocess
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP server path
MCP_SERVER_PATH = Path("PathUtils.get_workspace_root()/scripts/cli/mcp_server_cli.py")


def load_indexing_status():
    """Load previous indexing status."""
    status_file = Path("mcp_indexing_status.json")
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {"completed": [], "failed": [], "in_progress": None}


def save_indexing_status(status):
    """Save indexing status."""
    with open("mcp_indexing_status.json", 'w') as f:
        json.dump(status, f, indent=2)


def find_test_repositories() -> List[Dict[str, Any]]:
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            repo_name = repo_path.name
            
            # Determine language from path
            path_str = str(repo_path).lower()
            language = "unknown"
            
            if '/python/' in path_str or 'django' in path_str or 'flask' in path_str:
                language = "python"
            elif '/javascript/' in path_str or 'react' in path_str or 'express' in path_str:
                language = "javascript"
            elif '/typescript/' in path_str:
                language = "typescript"
            elif '/go/' in path_str or 'gin' in path_str:
                language = "go"
            elif '/rust/' in path_str or 'tokio' in path_str:
                language = "rust"
            elif '/java/' in path_str or 'kafka' in path_str:
                language = "java"
            elif '/cpp/' in path_str or 'grpc' in path_str:
                language = "cpp"
            elif '/c/' in path_str or 'redis' in path_str:
                language = "c"
            
            repos.append({
                'name': repo_name,
                'path': str(repo_path),
                'language': language
            })
    
    return repos


def index_repository_with_mcp(repo: Dict[str, Any], timeout: int = 300) -> Dict[str, Any]:
    """Index a single repository using MCP server with timeout."""
    start_time = time.time()
    
    try:
        # Set environment for semantic indexing
        env = os.environ.copy()
        env['SEMANTIC_SEARCH_ENABLED'] = 'true'
        env['MCP_INDEX_STORAGE_PATH'] = 'PathUtils.get_workspace_root()/.indexes'
        
        # Run MCP server to index the repository
        cmd = [
            sys.executable, str(MCP_SERVER_PATH),
            'index', repo['path'],
            '--force-reindex'
        ]
        
        logger.info(f"Indexing {repo['name']} with command: {' '.join(cmd)}")
        
        # Run with timeout
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully indexed {repo['name']} in {elapsed:.1f}s")
            return {
                'name': repo['name'],
                'success': True,
                'time': elapsed,
                'output': result.stdout[-500:]  # Last 500 chars
            }
        else:
            logger.error(f"❌ Failed to index {repo['name']}: {result.stderr}")
            return {
                'name': repo['name'],
                'success': False,
                'time': elapsed,
                'error': result.stderr[-500:]
            }
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.warning(f"⏱️  Timeout indexing {repo['name']} after {elapsed:.1f}s")
        return {
            'name': repo['name'],
            'success': False,
            'time': elapsed,
            'error': 'Timeout'
        }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Error indexing {repo['name']}: {e}")
        return {
            'name': repo['name'],
            'success': False,
            'time': elapsed,
            'error': str(e)
        }


def main():
    """Main function to continue MCP indexing."""
    logger.info("Continuing MCP-based repository indexing")
    logger.info("=" * 60)
    
    # Load status
    status = load_indexing_status()
    completed = set(status['completed'])
    failed = status.get('failed', [])
    
    # Find all repositories
    all_repos = find_test_repositories()
    logger.info(f"Found {len(all_repos)} total repositories")
    
    # Filter out completed ones
    remaining = [r for r in all_repos if r['name'] not in completed]
    logger.info(f"Already completed: {len(completed)}")
    logger.info(f"Remaining: {len(remaining)}")
    
    if not remaining:
        logger.info("All repositories have been processed!")
        return
    
    # Process remaining repositories
    results = []
    
    for i, repo in enumerate(remaining, 1):
        logger.info(f"\n[{i}/{len(remaining)}] Processing {repo['name']} ({repo['language']})")
        
        # Update status
        status['in_progress'] = repo['name']
        save_indexing_status(status)
        
        # Index with appropriate timeout based on expected size
        timeout = 300  # 5 minutes default
        if repo['name'] in ['TypeScript', 'grpc', 'django', 'react', 'rails']:
            timeout = 600  # 10 minutes for large repos
        
        result = index_repository_with_mcp(repo, timeout)
        results.append(result)
        
        # Update status
        if result['success']:
            status['completed'].append(repo['name'])
        else:
            status['failed'].append({
                'name': repo['name'],
                'error': result.get('error', 'Unknown error')
            })
        
        status['in_progress'] = None
        save_indexing_status(status)
        
        # Short break between repositories
        time.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("INDEXING SUMMARY")
    logger.info("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    logger.info(f"Processed: {len(results)} repositories")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if failed:
        logger.info("\nFailed repositories:")
        for r in failed:
            logger.info(f"  - {r['name']}: {r.get('error', 'Unknown')}")
    
    logger.info(f"\nTotal completed: {len(status['completed'])}/{len(all_repos)}")
    
    # Save final summary
    with open("mcp_indexing_summary.json", 'w') as f:
        json.dump({
            'total_repos': len(all_repos),
            'completed': len(status['completed']),
            'failed': len(status.get('failed', [])),
            'results': results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2)
    
    logger.info("\nSummary saved to: mcp_indexing_summary.json")


if __name__ == "__main__":
    main()