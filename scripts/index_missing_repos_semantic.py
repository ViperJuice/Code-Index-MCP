#!/usr/bin/env python3
"""
Index only the missing repositories that don't have semantic embeddings yet.
Skips very large repositories to avoid timeouts.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from qdrant_client import QdrantClient

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_existing_collections():
    """Get list of existing Qdrant collections."""
    try:
        qdrant_path = ".indexes/qdrant/main.qdrant"
        client = QdrantClient(path=qdrant_path)
        collections = client.get_collections()
        existing = {}
        for coll in collections.collections:
            try:
                info = client.get_collection(coll.name)
                if info.points_count > 0:
                    existing[coll.name] = info.points_count
            except:
                pass
        return existing
    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        return {}


def find_missing_repositories():
    """Find repositories that need semantic indexing."""
    existing = get_existing_collections()
    logger.info(f"Found {len(existing)} existing collections with embeddings")
    
    # All expected repositories
    all_repos = [
        ('c', 'curl'), ('c', 'phoenix'), ('c', 'redis'),
        ('cpp', 'grpc'), ('cpp', 'json'),
        ('csharp', 'aspnetcore'),
        ('dart', 'flutter_examples'),
        ('go', 'gin'), ('go', 'terraform'),
        ('java', 'kafka'), ('java', 'spring-boot'),
        ('javascript', 'express'), ('javascript', 'react'),
        ('kotlin', 'kotlin'),
        ('php', 'laravel'),
        ('python', 'django'), ('python', 'flask'), ('python', 'requests'),
        ('ruby', 'rails'),
        ('rust', 'rust'), ('rust', 'tokio'),
        ('scala', 'akka'),
        ('swift', 'alamofire'),
        ('typescript', 'TypeScript')
    ]
    
    missing = []
    for lang, repo in all_repos:
        collection_name = f"{lang}_{repo}".replace("-", "_").lower()
        if collection_name not in existing:
            missing.append((lang, repo, collection_name))
        else:
            logger.info(f"✓ {collection_name}: {existing[collection_name]} embeddings")
    
    return missing


def estimate_repo_size(repo_name):
    """Estimate repository size to skip very large ones."""
    # Known large repositories that cause timeouts
    large_repos = {
        'typescript': 50000,  # TypeScript compiler
        'grpc': 6000,         # gRPC framework
        'aspnetcore': 5000,   # ASP.NET Core
        'spring-boot': 3000,  # Spring Boot
        'django': 5000,       # Django
        'react': 6000,        # React
        'laravel': 4000,      # Laravel
        'rails': 5000         # Ruby on Rails
    }
    
    return large_repos.get(repo_name.lower(), 1000)


def main():
    """Main function to index missing repositories."""
    # Check API key
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY not set!")
        return
    
    # Find missing repositories
    missing = find_missing_repositories()
    logger.info(f"\nMissing semantic indexing for {len(missing)} repositories:")
    
    # Filter out very large repositories
    to_process = []
    skipped = []
    
    for lang, repo, collection in missing:
        size_estimate = estimate_repo_size(repo)
        if size_estimate > 2000:
            skipped.append((lang, repo, size_estimate))
            logger.info(f"  ⏭️  {lang}/{repo} - SKIPPING (est. {size_estimate} files)")
        else:
            to_process.append((lang, repo, collection))
            logger.info(f"  📋 {lang}/{repo} - will process")
    
    if skipped:
        logger.info(f"\nSkipping {len(skipped)} large repositories to avoid timeouts")
        logger.info("These can be indexed separately with dedicated scripts")
    
    if not to_process:
        logger.info("\nNo repositories to process!")
        return
    
    logger.info(f"\nWill process {len(to_process)} repositories")
    logger.info("\nTo index the remaining repositories, run:")
    logger.info("python scripts/index_all_repos_semantic_simple.py")
    
    # Save list of repositories to process
    with open("missing_repos_to_index.json", "w") as f:
        json.dump({
            "to_process": [{"language": t[0], "repo": t[1], "collection": t[2]} for t in to_process],
            "skipped": [{"language": s[0], "repo": s[1], "estimated_files": s[2]} for s in skipped],
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info("\nSaved repository list to: missing_repos_to_index.json")


if __name__ == "__main__":
    main()