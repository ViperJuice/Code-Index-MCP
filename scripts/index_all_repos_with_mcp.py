#!/usr/bin/env python3
"""
Index all test repositories using MCP's built-in capabilities.
This script properly integrates SQL and semantic indexing.
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import time
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.plugin_system import PluginManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_test_repositories() -> List[Path]:
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    # Find all .git directories
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    return repos


def get_repo_hash(repo_path: Path) -> str:
    """Get hash identifier for a repository."""
    import hashlib
    
    # Try git remote URL first
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        return hashlib.sha256(url.encode()).hexdigest()[:12]
    except:
        # Fall back to path hash
        return hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]


def get_repo_info(repo_path: Path) -> Dict[str, str]:
    """Extract repository information."""
    repo_name = repo_path.name
    
    # Try to determine language from path
    language = "unknown"
    path_str = str(repo_path).lower()
    
    if 'python' in path_str or 'django' in path_str or 'flask' in path_str:
        language = "python"
    elif 'javascript' in path_str or 'react' in path_str or 'express' in path_str:
        language = "javascript"
    elif 'typescript' in path_str:
        language = "typescript"
    elif 'go' in path_str or 'gin' in path_str:
        language = "go"
    elif 'rust' in path_str or 'tokio' in path_str:
        language = "rust"
    elif 'java' in path_str or 'kafka' in path_str:
        language = "java"
    elif 'csharp' in path_str or 'aspnetcore' in path_str:
        language = "csharp"
    elif 'cpp' in path_str or 'grpc' in path_str:
        language = "cpp"
    elif 'c' in path_str or 'redis' in path_str:
        language = "c"
    elif 'ruby' in path_str or 'rails' in path_str:
        language = "ruby"
    elif 'php' in path_str:
        language = "php"
    elif 'swift' in path_str:
        language = "swift"
    elif 'kotlin' in path_str:
        language = "kotlin"
    elif 'scala' in path_str:
        language = "scala"
    elif 'dart' in path_str:
        language = "dart"
    
    return {
        "name": repo_name,
        "language": language,
        "path": str(repo_path)
    }


def index_repository(repo_path: Path, repo_info: Dict[str, str]) -> Dict[str, Any]:
    """Index a single repository with both SQL and semantic indexing."""
    logger.info(f"\nIndexing {repo_info['name']} ({repo_info['language']})...")
    start_time = time.time()
    
    result = {
        "repo": str(repo_path),
        "name": repo_info['name'],
        "language": repo_info['language'],
        "success": False,
        "sql_indexed": 0,
        "semantic_indexed": 0,
        "error": None,
        "time": 0
    }
    
    try:
        # Get repository hash for unique identification
        repo_hash = get_repo_hash(repo_path)
        
        # Create index directory
        index_dir = Path(".indexes") / repo_hash
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # Create SQLite database
        db_path = index_dir / "current.db"
        logger.info(f"Creating SQL index at {db_path}")
        
        # Initialize storage
        sqlite_store = SQLiteStore(str(db_path))
        
        # Initialize dispatcher with semantic support
        dispatcher = EnhancedDispatcher(
            sqlite_store=sqlite_store,
            semantic_search_enabled=True,
            lazy_load=False
        )
        
        # Initialize semantic indexer with central Qdrant location
        semantic_indexer = None
        if os.getenv("VOYAGE_AI_API_KEY"):
            try:
                qdrant_path = ".indexes/qdrant/main.qdrant"
                collection_name = f"{repo_info['language']}_{repo_info['name']}"
                
                semantic_indexer = SemanticIndexer(
                    collection=collection_name,
                    qdrant_path=qdrant_path
                )
                logger.info(f"Initialized semantic indexer for collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic indexer: {e}")
        
        # Create plugin manager
        plugin_manager = PluginManager(sqlite_store=sqlite_store)
        
        # Initialize index engine with semantic support
        index_engine = IndexEngine(
            plugin_manager=plugin_manager,
            storage=sqlite_store,
            semantic_indexer=semantic_indexer,
            repository_path=str(repo_path)
        )
        
        # Index the repository directory
        logger.info(f"Indexing files in {repo_path}")
        
        # Use the index engine to index all files
        batch_result = index_engine.index_directory(
            str(repo_path),
            recursive=True
        )
        
        # Wait for async operation to complete
        import asyncio
        loop = asyncio.get_event_loop()
        batch_result = loop.run_until_complete(batch_result)
        
        result["sql_indexed"] = batch_result.successful
        result["success"] = batch_result.successful > 0
        
        # Count semantic embeddings if available
        if semantic_indexer:
            try:
                collection_info = semantic_indexer.qdrant.get_collection(collection_name)
                result["semantic_indexed"] = collection_info.points_count
            except:
                pass
        
        # Create metadata file
        metadata = {
            "repository_name": repo_info['name'],
            "repository_path": str(repo_path),
            "language": repo_info['language'],
            "repo_hash": repo_hash,
            "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files_indexed": batch_result.successful,
            "semantic_enabled": semantic_indexer is not None
        }
        
        metadata_path = index_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Successfully indexed {repo_info['name']}: {result['sql_indexed']} files, {result['semantic_indexed']} embeddings")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ Failed to index {repo_info['name']}: {e}")
    
    result["time"] = time.time() - start_time
    return result


def main():
    """Main function to index all test repositories."""
    print("MCP-Based Repository Indexing")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("VOYAGE_AI_API_KEY"):
        print("⚠️  Warning: VOYAGE_AI_API_KEY not set. Semantic indexing will be disabled.")
        print("Set it in .env file to enable semantic search.")
    
    # Enable semantic search
    os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
    os.environ["QDRANT_PATH"] = ".indexes/qdrant/main.qdrant"
    
    # Find all test repositories
    repos = find_test_repositories()
    print(f"\nFound {len(repos)} repositories to index")
    
    # Index each repository
    results = []
    success_count = 0
    total_sql_indexed = 0
    total_semantic_indexed = 0
    
    for i, repo_path in enumerate(repos, 1):
        print(f"\n[{i}/{len(repos)}] Processing {repo_path.name}...")
        
        # Get repository info
        repo_info = get_repo_info(repo_path)
        
        # Index the repository
        result = index_repository(repo_path, repo_info)
        results.append(result)
        
        if result["success"]:
            success_count += 1
            total_sql_indexed += result["sql_indexed"]
            total_semantic_indexed += result["semantic_indexed"]
    
    # Summary
    print("\n" + "=" * 60)
    print("Indexing Summary")
    print("=" * 60)
    print(f"Total repositories: {len(repos)}")
    print(f"Successfully indexed: {success_count}")
    print(f"Failed: {len(repos) - success_count}")
    print(f"Total SQL documents: {total_sql_indexed}")
    print(f"Total semantic embeddings: {total_semantic_indexed}")
    
    # Save detailed results
    report_path = Path("PathUtils.get_workspace_root()/mcp_indexing_results.json")
    with open(report_path, 'w') as f:
        json.dump({
            "total": len(repos),
            "success": success_count,
            "failed": len(repos) - success_count,
            "total_sql_indexed": total_sql_indexed,
            "total_semantic_indexed": total_semantic_indexed,
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {report_path}")
    
    # Create mapping file
    mapping = {
        "sql_indexes": {},
        "qdrant_collections": {},
        "repository_mapping": {}
    }
    
    # Build mapping from results
    for result in results:
        if result["success"]:
            repo_hash = get_repo_hash(Path(result["repo"]))
            repo_key = f"{result['language']}_{result['name']}"
            
            # SQL index info
            mapping["sql_indexes"][repo_hash] = {
                "path": f".indexes/{repo_hash}/current.db",
                "documents": result["sql_indexed"],
                "repo_name": result["name"],
                "language": result["language"]
            }
            
            # Qdrant collection info
            if result["semantic_indexed"] > 0:
                collection_name = f"{result['language']}_{result['name']}"
                mapping["qdrant_collections"][collection_name] = {
                    "path": ".indexes/qdrant/main.qdrant",
                    "points": result["semantic_indexed"],
                    "repo_name": result["name"],
                    "language": result["language"]
                }
            
            # Repository mapping
            mapping["repository_mapping"][repo_key] = {
                "language": result["language"],
                "sql_index": repo_hash,
                "sql_path": f".indexes/{repo_hash}/current.db",
                "qdrant_collection": collection_name if result["semantic_indexed"] > 0 else None,
                "qdrant_path": ".indexes/qdrant/main.qdrant" if result["semantic_indexed"] > 0 else None
            }
    
    # Save mapping
    mapping_path = Path("PathUtils.get_workspace_root()/mcp_repo_mapping.json")
    with open(mapping_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Repository mapping saved to: {mapping_path}")
    
    print("\n✅ MCP indexing complete!")
    print("\nNote: The MCP server must be restarted to use the updated indexes.")
    print("Semantic indexing will only work if VOYAGE_AI_API_KEY is set.")


if __name__ == "__main__":
    main()