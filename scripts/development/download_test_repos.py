#!/usr/bin/env python3
"""Download small public repositories for testing the indexing and retrieval system."""

import os
import subprocess
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Small, diverse repositories for testing different languages
TEST_REPOS = [
    # Python - Flask hello world app
    {
        "url": "https://github.com/pallets/flask-hello",
        "name": "flask-hello",
        "language": "Python",
        "description": "Simple Flask hello world app"
    },
    # JavaScript/TypeScript - Express REST API
    {
        "url": "https://github.com/developit/express-es6-rest-api",
        "name": "express-es6-rest-api",
        "language": "JavaScript",
        "description": "Express.js REST API boilerplate"
    },
    # Java - Simple Spring Boot app
    {
        "url": "https://github.com/spring-guides/gs-spring-boot",
        "name": "gs-spring-boot",
        "language": "Java",
        "description": "Spring Boot getting started guide"
    },
    # Go - Simple web server
    {
        "url": "https://github.com/golang/example",
        "name": "golang-example",
        "language": "Go",
        "description": "Go example programs"
    },
    # Rust - Command line tool
    {
        "url": "https://github.com/sharkdp/bat",
        "name": "bat",
        "language": "Rust",
        "description": "A cat clone with syntax highlighting",
        "sparse_checkout": ["src", "Cargo.toml"]  # Only download src for this larger repo
    },
    # PHP - Simple Laravel app
    {
        "url": "https://github.com/laravel/quickstart-basic",
        "name": "laravel-quickstart",
        "language": "PHP", 
        "description": "Laravel quickstart tutorial"
    },
    # Ruby - Sinatra app
    {
        "url": "https://github.com/sinatra/sinatra-recipes",
        "name": "sinatra-recipes",
        "language": "Ruby",
        "description": "Community contributed recipes and techniques for Sinatra"
    },
    # Mixed language - TodoMVC
    {
        "url": "https://github.com/tastejs/todomvc",
        "name": "todomvc",
        "language": "Mixed",
        "description": "TodoMVC implementations in various frameworks",
        "sparse_checkout": ["examples/vanilla-js", "examples/react", "examples/vue"]
    }
]

def download_repo(repo_info, base_dir):
    """Download a single repository."""
    repo_dir = base_dir / repo_info["name"]
    
    if repo_dir.exists():
        logger.info(f"Repository {repo_info['name']} already exists, skipping...")
        return True
    
    logger.info(f"Downloading {repo_info['name']} ({repo_info['language']})...")
    
    try:
        if "sparse_checkout" in repo_info:
            # Use sparse checkout for larger repos
            subprocess.run(["git", "clone", "--filter=blob:none", "--sparse", 
                          repo_info["url"], str(repo_dir)], check=True)
            
            # Set up sparse checkout
            current_dir = os.getcwd()
            os.chdir(repo_dir)
            subprocess.run(["git", "sparse-checkout", "init", "--cone"], check=True)
            subprocess.run(["git", "sparse-checkout", "set"] + repo_info["sparse_checkout"], check=True)
            os.chdir(current_dir)
        else:
            # Regular clone with depth limit
            subprocess.run(["git", "clone", "--depth", "1", 
                          repo_info["url"], str(repo_dir)], check=True)
        
        # Remove .git directory to save space
        git_dir = repo_dir / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
        
        logger.info(f"Successfully downloaded {repo_info['name']}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download {repo_info['name']}: {e}")
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        return False

def main():
    """Download all test repositories."""
    # Create test repos directory
    test_repos_dir = Path("test_repos")
    test_repos_dir.mkdir(exist_ok=True)
    
    logger.info(f"Downloading test repositories to {test_repos_dir.absolute()}")
    
    successful = 0
    failed = 0
    
    for repo in TEST_REPOS:
        if download_repo(repo, test_repos_dir):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"\nDownload complete: {successful} successful, {failed} failed")
    
    # Create a summary file
    summary_file = test_repos_dir / "repos_summary.txt"
    with open(summary_file, "w") as f:
        f.write("Test Repositories Summary\n")
        f.write("========================\n\n")
        
        for repo in TEST_REPOS:
            repo_dir = test_repos_dir / repo["name"]
            if repo_dir.exists():
                file_count = sum(1 for _ in repo_dir.rglob("*") if _.is_file())
                f.write(f"{repo['name']}:\n")
                f.write(f"  Language: {repo['language']}\n")
                f.write(f"  Description: {repo['description']}\n")
                f.write(f"  Files: {file_count}\n")
                f.write(f"  Path: {repo_dir.absolute()}\n\n")
    
    logger.info(f"Summary written to {summary_file}")

if __name__ == "__main__":
    main()