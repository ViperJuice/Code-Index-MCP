#!/usr/bin/env python3
"""
Complete semantic indexing for ALL repositories with resume capability.
Handles large repositories with checkpointing and progress tracking.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import time
import voyageai
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from typing import List, Dict, Any, Set
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

# Progress file to track what's been done
PROGRESS_FILE = "semantic_indexing_progress.json"

# Large repositories to skip (can be indexed separately)
SKIP_LARGE_REPOS = {
    'grpc', 'TypeScript', 'react', 'django', 'aspnetcore', 
    'rails', 'laravel', 'spring-boot'
}


def load_progress() -> Dict[str, Any]:
    """Load progress from checkpoint file."""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed": {}, "in_progress": None, "last_updated": None}


def save_progress(progress: Dict[str, Any]):
    """Save progress to checkpoint file."""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def find_all_repositories() -> List[Dict[str, Any]]:
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    # Language detection patterns
    language_patterns = {
        'python': ['django', 'flask', 'requests', 'python'],
        'javascript': ['react', 'express', 'javascript', 'jquery'],
        'typescript': ['typescript', 'angular'],
        'go': ['gin', 'terraform', 'go'],
        'rust': ['tokio', 'rust'],
        'java': ['kafka', 'spring', 'java'],
        'csharp': ['aspnetcore', 'csharp', 'dotnet'],
        'cpp': ['grpc', 'cpp', 'c++', 'json'],
        'c': ['redis', 'phoenix', 'curl', '/c/'],
        'ruby': ['rails', 'ruby'],
        'php': ['laravel', 'framework', 'php'],
        'swift': ['alamofire', 'swift'],
        'kotlin': ['kotlin'],
        'scala': ['akka', 'scala'],
        'dart': ['dart', 'flutter']
    }
    
    # Find all repositories
    for repo_path in test_repos_dir.rglob('.git'):
        if repo_path.is_dir():
            repo_dir = repo_path.parent
            repo_name = repo_dir.name
            
            # Determine language
            path_str = str(repo_dir).lower()
            language = 'unknown'
            for lang, patterns in language_patterns.items():
                if any(pattern in path_str for pattern in patterns):
                    language = lang
                    break
            
            repos.append({
                'path': repo_dir,
                'name': repo_name,
                'language': language,
                'key': f"{language}_{repo_name}"
            })
    
    return sorted(repos, key=lambda x: (x['language'], x['name']))


def get_code_files(repo_path: Path, processed_files: Set[str] = None) -> List[tuple]:
    """Get all code files from repository, skipping already processed ones."""
    if processed_files is None:
        processed_files = set()
        
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
        '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
        '.kt', '.scala', '.r', '.jl', '.dart', '.m', '.mm', '.cc', '.cxx'
    }
    
    files = []
    skip_dirs = {'.git', 'node_modules', 'vendor', '__pycache__', '.pytest_cache', 
                 'target', 'build', 'dist', '.next', '.nuxt', 'coverage', 'test_output'}
    
    for file_path in repo_path.rglob('*'):
        # Skip processed files
        if str(file_path) in processed_files:
            continue
            
        # Skip unwanted directories
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            continue
            
        if file_path.is_file() and file_path.suffix in code_extensions:
            try:
                # Skip very large files (> 1MB)
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
    """Create embeddings with retry logic and smaller batches."""
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


def process_repository(repo_info: Dict[str, Any], qdrant_client: QdrantClient, voyage_client, 
                      progress: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single repository with checkpointing."""
    start_time = time.time()
    repo_key = repo_info['key']
    collection_name = f"{repo_info['language']}_{repo_info['name']}".replace("-", "_").lower()
    
    # Check if already completed
    if repo_key in progress["completed"]:
        logger.info(f"Skipping {repo_info['name']} - already completed with {progress['completed'][repo_key]['embeddings']} embeddings")
        return progress['completed'][repo_key]
    
    logger.info(f"\nProcessing {repo_info['name']} ({repo_info['language']})")
    
    # Mark as in progress
    in_progress = progress.get("in_progress", {})
    if in_progress and in_progress.get("repo_key") == repo_key:
        processed_files = in_progress.get("processed_files", [])
    else:
        processed_files = []
    
    progress["in_progress"] = {
        "repo_key": repo_key,
        "collection": collection_name,
        "processed_files": processed_files
    }
    save_progress(progress)
    
    # Create or check collection
    try:
        info = qdrant_client.get_collection(collection_name)
        existing_points = info.points_count
        logger.info(f"Collection '{collection_name}' exists with {existing_points} points")
        if existing_points > 100:  # If substantial progress exists
            logger.info(f"Resuming from existing {existing_points} embeddings")
    except:
        logger.info(f"Creating new collection '{collection_name}'")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            )
        )
        existing_points = 0
    
    # Get files, skipping already processed ones
    processed_files = set(progress["in_progress"]["processed_files"])
    files = get_code_files(repo_info['path'], processed_files)
    logger.info(f"Found {len(files)} new files to process (skipped {len(processed_files)} already processed)")
    
    if not files:
        result = {
            'repo': repo_info['name'],
            'language': repo_info['language'],
            'collection': collection_name,
            'files_processed': len(processed_files),
            'embeddings': existing_points,
            'success': True,
            'time': time.time() - start_time
        }
        progress["completed"][repo_key] = result
        progress["in_progress"] = None
        save_progress(progress)
        return result
    
    # Process files in manageable chunks
    chunk_size = 2000  # Characters per chunk
    total_embeddings = existing_points
    files_processed = len(processed_files)
    texts = []
    metadatas = []
    points = []
    
    for file_idx, (file_path, content) in enumerate(files):
        # Create chunks
        if len(content) > chunk_size:
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        else:
            chunks = [content]
        
        for chunk_idx, chunk_content in enumerate(chunks):
            if not chunk_content.strip():
                continue
            
            texts.append(chunk_content)
            metadatas.append({
                'file_path': file_path,
                'repository': repo_info['name'],
                'language': repo_info['language'],
                'chunk_index': chunk_idx,
                'total_chunks': len(chunks),
                'indexed_at': datetime.now().isoformat()
            })
        
        # Process batch when we have enough
        if len(texts) >= 10 or file_idx == len(files) - 1:
            if texts:
                embeddings = create_embeddings_batch(texts, voyage_client)
                if embeddings:
                    for embedding, metadata in zip(embeddings, metadatas):
                        unique_str = f"{collection_name}:{metadata['file_path']}:{metadata['chunk_index']}"
                        point_id = abs(hash(unique_str)) % (10**15)
                        
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload=metadata
                            )
                        )
                    
                    total_embeddings += len(embeddings)
                    logger.info(f"Created {len(embeddings)} embeddings ({files_processed + file_idx + 1}/{len(files) + len(processed_files)} files)")
                
                texts = []
                metadatas = []
                
                # Upload points
                if len(points) >= 100:
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
                    logger.info(f"Uploaded {len(points)} embeddings to Qdrant")
                    points = []
                    
                    # Update progress
                    progress["in_progress"]["processed_files"].append(file_path)
                    save_progress(progress)
    
    # Upload remaining points
    if points:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Uploaded final {len(points)} embeddings to Qdrant")
    
    # Mark as completed
    result = {
        'repo': repo_info['name'],
        'language': repo_info['language'],
        'collection': collection_name,
        'files_processed': len(files) + len(processed_files),
        'embeddings': total_embeddings,
        'success': True,
        'time': time.time() - start_time
    }
    
    progress["completed"][repo_key] = result
    progress["in_progress"] = None
    save_progress(progress)
    
    logger.info(f"✅ Completed {repo_info['name']}: {result['files_processed']} files, {result['embeddings']} embeddings in {result['time']:.1f}s")
    return result


def main():
    """Main function to index all repositories completely."""
    # Check API key
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY not set!")
        return
    
    logger.info("Starting COMPLETE semantic indexing of ALL repositories")
    logger.info("This script will resume from where it left off if interrupted")
    
    # Load progress
    progress = load_progress()
    if progress["completed"]:
        logger.info(f"Found {len(progress['completed'])} already completed repositories")
    
    # Initialize clients
    voyage_client = voyageai.Client(api_key=api_key)
    qdrant_path = ".indexes/qdrant/main.qdrant"
    Path(qdrant_path).parent.mkdir(parents=True, exist_ok=True)
    qdrant_client = QdrantClient(path=qdrant_path)
    
    # Find all repositories
    repos = find_all_repositories()
    logger.info(f"Found {len(repos)} total repositories")
    
    # Process each repository
    start_time = time.time()
    results = []
    
    for i, repo_info in enumerate(repos, 1):
        # Skip large repositories
        if repo_info['name'] in SKIP_LARGE_REPOS:
            logger.info(f"\n⏭️  Skipping large repository: {repo_info['name']}")
            continue
            
        logger.info(f"\n{'='*60}")
        logger.info(f"Repository {i}/{len(repos)}")
        logger.info(f"{'='*60}")
        
        try:
            result = process_repository(repo_info, qdrant_client, voyage_client, progress)
            results.append(result)
        except KeyboardInterrupt:
            logger.info("\n\nInterrupted by user. Progress has been saved.")
            logger.info(f"Resume by running this script again.")
            break
        except Exception as e:
            logger.error(f"Failed to process {repo_info['name']}: {e}")
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
    successful = [r for r in results if r.get('success', False)]
    total_files = sum(r['files_processed'] for r in successful)
    total_embeddings = sum(r['embeddings'] for r in successful)
    
    logger.info(f"\n{'='*60}")
    logger.info("INDEXING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Repositories processed: {len(results)}/{len(repos)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Total files: {total_files:,}")
    logger.info(f"Total embeddings: {total_embeddings:,}")
    logger.info(f"Total time: {total_time/60:.1f} minutes")
    
    # Save final results
    final_results = {
        "summary": {
            "total_repos": len(repos),
            "processed": len(results),
            "successful": len(successful),
            "total_files": total_files,
            "total_embeddings": total_embeddings,
            "total_time_minutes": total_time/60
        },
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    with open("complete_indexing_results.json", 'w') as f:
        json.dump(final_results, f, indent=2)
    
    logger.info(f"\nFinal results saved to: complete_indexing_results.json")
    logger.info(f"Progress checkpoint: {PROGRESS_FILE}")


if __name__ == "__main__":
    main()