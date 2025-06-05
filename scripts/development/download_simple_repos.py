#!/usr/bin/env python3
"""Download small public repositories for testing."""

import subprocess
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Small repos that should clone successfully
TEST_REPOS = [
    # JavaScript - Express API  
    ("https://github.com/developit/express-es6-rest-api", "express-api", "JavaScript"),
    # Java - Spring Boot
    ("https://github.com/spring-guides/gs-spring-boot", "spring-boot", "Java"),
    # Go examples
    ("https://github.com/golang/example", "go-examples", "Go"),
    # Python - Flask example
    ("https://github.com/miguelgrinberg/flasky", "flask-app", "Python"),
    # Ruby - Sinatra
    ("https://github.com/sinatra/sinatra-book", "sinatra-book", "Ruby"),
    # PHP - Slim framework example
    ("https://github.com/slimphp/Slim-Skeleton", "slim-skeleton", "PHP"),
]

def main():
    """Download test repositories."""
    test_repos_dir = Path("test_repos")
    test_repos_dir.mkdir(exist_ok=True)
    
    logger.info(f"Downloading to {test_repos_dir.absolute()}")
    
    for url, name, lang in TEST_REPOS:
        repo_dir = test_repos_dir / name
        
        if repo_dir.exists():
            logger.info(f"{name} already exists, skipping...")
            continue
            
        logger.info(f"Downloading {name} ({lang})...")
        
        try:
            # Simple shallow clone
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Remove .git to save space
            git_dir = repo_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)
                
            logger.info(f"✓ Downloaded {name}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed {name}: {e.stderr}")
            if repo_dir.exists():
                shutil.rmtree(repo_dir)
    
    # Count files
    logger.info("\nRepository Summary:")
    for _, name, lang in TEST_REPOS:
        repo_dir = test_repos_dir / name
        if repo_dir.exists():
            file_count = sum(1 for f in repo_dir.rglob("*") if f.is_file())
            logger.info(f"  {name}: {file_count} files ({lang})")

if __name__ == "__main__":
    main()