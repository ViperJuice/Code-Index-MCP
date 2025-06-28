#!/usr/bin/env python3
"""
Create semantic embeddings for ALL files in ALL test repositories.
This script processes entire repositories without limits.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime
import voyageai
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_all_code_files(repo_path: Path) -> List[tuple]:
    """Get all code files from a repository without limits."""
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
        '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
        '.kt', '.scala', '.r', '.jl', '.dart', '.m', '.mm', '.cc', '.cxx'
    }
    
    files = []
    skip_dirs = {'.git', 'node_modules', 'vendor', '__pycache__', '.pytest_cache', 
                 'target', 'build', 'dist', '.next', '.nuxt', 'coverage'}
    
    for file_path in repo_path.rglob('*'):
        # Skip directories we don't want
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            continue
            
        if file_path.is_file() and file_path.suffix in code_extensions:
            try:
                # Check file size (skip very large files > 1MB)
                if file_path.stat().st_size > 1048576:
                    logger.debug(f"Skipping large file: {file_path}")
                    continue
                    
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if len(content) > 50:  # Skip very small files
                    files.append((str(file_path), content))
            except Exception as e:
                logger.debug(f"Error reading {file_path}: {e}")
                continue
    
    return files


def create_embeddings_batch(texts: List[str], voyage_client, batch_size: int = 20) -> List[List[float]]:
    """Create embeddings in batches with retry logic."""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        retries = 3
        
        while retries > 0:
            try:
                result = voyage_client.embed(
                    batch,
                    model="voyage-code-3",
                    input_type="document",
                    output_dimension=1024,
                    output_dtype="float"
                )
                all_embeddings.extend(result.embeddings)
                break
            except Exception as e:
                retries -= 1
                if retries == 0:
                    logger.error(f"Failed to create embeddings after 3 attempts: {e}")
                    # Return empty embeddings for this batch
                    all_embeddings.extend([[0.0] * 1024 for _ in batch])
                else:
                    logger.warning(f"Embedding error, retrying ({retries} left): {e}")
                    time.sleep(2)
    
    return all_embeddings


def process_repository(repo_info: Dict[str, Any], qdrant_client: QdrantClient, voyage_client) -> Dict[str, Any]:
    """Process a single repository and create embeddings for ALL files."""
    start_time = time.time()
    repo_path = Path(repo_info['path'])
    collection_name = f"{repo_info['language']}_{repo_info['name']}".replace("-", "_").lower()
    
    logger.info(f"\nProcessing {repo_info['name']} ({repo_info['language']}) - FULL repository")
    
    # Create or recreate collection
    try:
        qdrant_client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection '{collection_name}'")
    except:
        pass
    
    logger.info(f"Creating collection '{collection_name}'")
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=1024,
            distance=models.Distance.COSINE
        )
    )
    
    # Collect ALL code files
    files = get_all_code_files(repo_path)
    logger.info(f"Found {len(files)} code files in entire repository")
    
    if not files:
        return {
            'repo': repo_info['name'],
            'language': repo_info['language'],
            'collection': collection_name,
            'files_processed': 0,
            'embeddings': 0,
            'success': True,
            'time': time.time() - start_time
        }
    
    # Process files in chunks
    chunk_size = 2000  # Characters per chunk
    total_embeddings = 0
    texts = []
    metadatas = []
    
    for file_path, content in files:
        # Split large files into chunks
        if len(content) > chunk_size:
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        else:
            chunks = [content]
        
        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                'file_path': file_path,
                'repository': repo_info['name'],
                'language': repo_info['language'],
                'chunk_index': i,
                'total_chunks': len(chunks),
                'indexed_at': datetime.now().isoformat()
            })
    
    logger.info(f"Created {len(texts)} chunks from {len(files)} files")
    
    # Create embeddings in batches
    embeddings = create_embeddings_batch(texts, voyage_client)
    
    if embeddings:
        # Create points for Qdrant
        points = []
        for j, (embedding, metadata) in enumerate(zip(embeddings, metadatas)):
            # Create unique ID
            unique_str = f"{collection_name}:{metadata['file_path']}:{metadata['chunk_index']}"
            point_id = abs(hash(unique_str)) % (10**15)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=metadata
                )
            )
        
        # Upload points in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            qdrant_client.upsert(
                collection_name=collection_name,
                points=batch
            )
            logger.info(f"Uploaded batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")
        
        total_embeddings = len(points)
        logger.info(f"✅ Created {total_embeddings} embeddings from {len(files)} files")
    
    return {
        'repo': repo_info['name'],
        'language': repo_info['language'],
        'collection': collection_name,
        'files_processed': len(files),
        'embeddings': total_embeddings,
        'success': True,
        'time': time.time() - start_time
    }


def find_test_repositories() -> List[Dict[str, str]]:
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    # Define language patterns
    language_patterns = {
        'python': ['django', 'flask', 'requests', 'python'],
        'javascript': ['react', 'express', 'javascript', 'jquery'],
        'typescript': ['typescript', 'angular'],
        'go': ['gin', 'terraform', 'go'],
        'rust': ['tokio', 'rust'],
        'java': ['kafka', 'spring', 'java'],
        'csharp': ['aspnetcore', 'csharp', 'dotnet'],
        'cpp': ['grpc', 'cpp', 'c++'],
        'c': ['redis', 'phoenix', '/c/'],
        'ruby': ['rails', 'ruby'],
        'php': ['laravel', 'framework', 'php'],
        'swift': ['alamofire', 'swift'],
        'kotlin': ['kotlin'],
        'scala': ['akka', 'scala'],
        'dart': ['dart', 'flutter']
    }
    
    # Find all repositories
    for category_dir in test_repos_dir.iterdir():
        if category_dir.is_dir() and category_dir.name not in ['.git', '__pycache__']:
            for lang_dir in category_dir.iterdir():
                if lang_dir.is_dir():
                    for repo_dir in lang_dir.iterdir():
                        if repo_dir.is_dir() and (repo_dir / '.git').exists():
                            # Determine language
                            path_str = str(repo_dir).lower()
                            language = 'unknown'
                            
                            for lang, patterns in language_patterns.items():
                                if any(pattern in path_str for pattern in patterns):
                                    language = lang
                                    break
                            
                            repos.append({
                                'path': str(repo_dir),
                                'name': repo_dir.name,
                                'language': language,
                                'category': category_dir.name
                            })
    
    return sorted(repos, key=lambda x: (x['language'], x['name']))


def main():
    """Main function to create FULL embeddings for all repositories."""
    # Check API key
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY not set!")
        return
    
    logger.info("Starting FULL semantic indexing of all test repositories")
    
    # Initialize clients
    voyage_client = voyageai.Client(api_key=api_key)
    qdrant_path = ".indexes/qdrant/main.qdrant"
    Path(qdrant_path).parent.mkdir(parents=True, exist_ok=True)
    qdrant_client = QdrantClient(path=qdrant_path)
    
    # Find all test repositories
    repos = find_test_repositories()
    logger.info(f"Found {len(repos)} test repositories")
    
    # Group by language
    by_language = {}
    for repo in repos:
        lang = repo['language']
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(repo)
    
    logger.info(f"Languages: {', '.join(f'{lang}({len(repos)})' for lang, repos in by_language.items())}")
    
    # Process repositories
    results = []
    total_files = 0
    total_embeddings = 0
    start_time = time.time()
    
    # Process ALL repositories
    for i, repo_info in enumerate(repos, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Repository {i}/{len(repos)}")
        logger.info(f"{'='*60}")
        
        try:
            result = process_repository(repo_info, qdrant_client, voyage_client)
            results.append(result)
            total_files += result['files_processed']
            total_embeddings += result['embeddings']
            logger.info(f"✅ Success: {result['files_processed']} files, {result['embeddings']} embeddings in {result['time']:.1f}s")
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            results.append({
                'repo': repo_info['name'],
                'language': repo_info['language'],
                'collection': f"{repo_info['language']}_{repo_info['name']}",
                'files_processed': 0,
                'embeddings': 0,
                'success': False,
                'error': str(e),
                'time': 0
            })
    
    # Summary
    total_time = time.time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info("FULL INDEXING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total repositories processed: {len(results)}")
    logger.info(f"Total files processed: {total_files:,}")
    logger.info(f"Total embeddings created: {total_embeddings:,}")
    logger.info(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    logger.info(f"Average time per repo: {total_time/len(results):.1f}s")
    
    # Save results
    results_path = Path("full_semantic_indexing_results.json")
    with open(results_path, 'w') as f:
        json.dump({
            "total_repos": len(results),
            "total_files": total_files,
            "total_embeddings": total_embeddings,
            "total_time": total_time,
            "results": results
        }, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_path}")
    
    # Create comprehensive mapping
    mapping = {
        "qdrant_collections": {},
        "repository_mapping": {}
    }
    
    for result in results:
        if result['success'] and result['embeddings'] > 0:
            collection = result['collection']
            mapping["qdrant_collections"][collection] = {
                "path": qdrant_path,
                "points": result['embeddings'],
                "files": result['files_processed'],
                "repo_name": result['repo'],
                "language": result['language']
            }
            
            repo_key = f"{result['language']}_{result['repo']}"
            mapping["repository_mapping"][repo_key] = {
                "language": result['language'],
                "qdrant_collection": collection,
                "qdrant_path": qdrant_path,
                "embeddings": result['embeddings'],
                "files": result['files_processed']
            }
    
    mapping_path = Path("full_repo_mapping.json")
    with open(mapping_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    logger.info(f"Repository mapping saved to: {mapping_path}")


if __name__ == "__main__":
    main()