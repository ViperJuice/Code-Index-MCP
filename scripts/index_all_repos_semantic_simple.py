#!/usr/bin/env python3
"""
Complete semantic indexing for all test repositories.
Processes entire files without limits, using direct Voyage AI and Qdrant APIs.
Updated to process test_repos directly and handle all file content.
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


def find_test_repositories() -> List[Dict[str, Any]]:
    """Find all test repositories and their metadata."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    # Define language patterns for detection
    language_patterns = {
        'python': ['django', 'flask', 'requests', 'python'],
        'javascript': ['react', 'express', 'javascript', 'jquery'],
        'typescript': ['typescript', 'angular'],
        'go': ['gin', 'terraform', 'go'],
        'rust': ['tokio', 'rust'],
        'java': ['kafka', 'spring', 'java'],
        'csharp': ['aspnetcore', 'csharp', 'dotnet'],
        'cpp': ['grpc', 'cpp', 'c++'],
        'c': ['redis', 'phoenix', 'curl'],
        'ruby': ['rails', 'ruby'],
        'php': ['laravel', 'framework', 'php'],
        'swift': ['alamofire', 'swift'],
        'kotlin': ['kotlin'],
        'scala': ['akka', 'scala'],
        'dart': ['dart', 'flutter']
    }
    
    # Find all repositories with .git directories
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
            
            # Find corresponding SQL index if it exists
            repo_hash = None
            sql_db_path = None
            indexes_dir = Path(".indexes")
            
            # Try to find existing index by checking sample paths
            for idx_dir in indexes_dir.iterdir():
                if idx_dir.is_dir() and any(idx_dir.glob("*.db")):
                    # Check if this index contains files from this repo
                    db_files = list(idx_dir.glob("*.db"))
                    if db_files:
                        try:
                            conn = sqlite3.connect(db_files[0])
                            cursor = conn.cursor()
                            cursor.execute("SELECT filepath FROM bm25_content LIMIT 1")
                            sample_path = cursor.fetchone()
                            conn.close()
                            
                            if sample_path and repo_name in sample_path[0]:
                                repo_hash = idx_dir.name
                                sql_db_path = db_files[0]
                                break
                        except:
                            pass
            
            repos.append({
                'path': repo_dir,
                'name': repo_name,
                'language': language,
                'repo_hash': repo_hash,
                'sql_db_path': sql_db_path
            })
    
    return sorted(repos, key=lambda x: (x['language'], x['name']))


def create_embeddings(texts: List[str], voyage_client) -> List[List[float]]:
    """Create embeddings for a list of texts."""
    if not texts:
        return []
    
    try:
        result = voyage_client.embed(
            texts,
            model="voyage-code-3",
            input_type="document",
            output_dimension=1024,
            output_dtype="float"
        )
        return result.embeddings
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        return []


def process_repository(repo_info: Dict[str, Any], qdrant_client: QdrantClient, voyage_client):
    """Process a single repository and create embeddings for ALL files."""
    repo_path = repo_info['path']
    repo_name = repo_info['name']
    language = repo_info['language']
    collection_name = f"{language}_{repo_name}".replace("-", "_").replace(" ", "_").lower()
    
    logger.info(f"Processing {repo_name} ({language}) from {repo_path}")
    
    # Check if we have an SQL database to use
    db_path = repo_info.get('sql_db_path')
    if db_path and Path(db_path).exists():
        logger.info(f"Using existing SQL index: {db_path}")
        return process_from_sql_index(db_path, repo_name, collection_name, qdrant_client, voyage_client)
    else:
        logger.info("No SQL index found, processing files directly")
        return process_from_filesystem(repo_path, repo_name, language, collection_name, qdrant_client, voyage_client)


def process_from_sql_index(db_path: Path, repo_name: str, collection_name: str, qdrant_client: QdrantClient, voyage_client):
    """Process repository using existing SQL index."""
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    total_embeddings = 0
    
    try:
        # Get all indexed files
        cursor.execute("""
            SELECT DISTINCT filepath, content 
            FROM bm25_content 
            WHERE content IS NOT NULL AND content != ''
            AND length(content) > 50
            ORDER BY filepath
        """)
        
        files = cursor.fetchall()
        logger.info(f"Found {len(files)} files to process")
        
        # Process in batches
        batch_size = 10
        points = []
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            texts = []
            metadatas = []
            
            for file_path, content in batch:
                if not content or len(content) < 50:
                    continue
                    
                # Skip non-code files
                if not any(file_path.endswith(ext) for ext in [
                    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
                    '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.jl', '.dart', '.m', '.mm'
                ]):
                    continue
                
                # Process entire file content, chunking if necessary
                chunk_size = 2000  # Characters per chunk for embedding
                if len(content) > chunk_size:
                    # Split large files into chunks
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                else:
                    chunks = [content]
                
                for chunk_idx, chunk_content in enumerate(chunks):
                    if not chunk_content.strip():
                        continue
                
                    texts.append(chunk_content)
                    metadatas.append({
                        'file_path': file_path,
                        'repository': repo_name,
                        'language': Path(file_path).suffix[1:] or 'unknown',
                        'chunk_index': chunk_idx,
                        'total_chunks': len(chunks),
                        'indexed_at': datetime.now().isoformat()
                    })
            
            if texts:
                # Create embeddings
                embeddings = create_embeddings(texts, voyage_client)
                
                if embeddings:
                    # Create points for Qdrant
                    for j, (embedding, metadata) in enumerate(zip(embeddings, metadatas)):
                        # Create unique ID based on repo and file path
                        unique_str = f"{collection_name}:{metadata['file_path']}"
                        point_id = abs(hash(unique_str)) % (10**15)
                        
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload=metadata
                            )
                        )
                    
                    logger.info(f"Created {len(embeddings)} embeddings for batch {i//batch_size + 1}")
                    total_embeddings += len(embeddings)
            
            # Upload points in chunks to avoid memory issues
            if len(points) >= 100:
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                logger.info(f"Uploaded {len(points)} embeddings to Qdrant")
                points = []
        
        # Upload remaining points
        if points:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Uploaded final {len(points)} embeddings to Qdrant")
                
    except Exception as e:
        logger.error(f"Error processing repository: {e}")
    finally:
        conn.close()
    
    return total_embeddings


def process_from_filesystem(repo_path: Path, repo_name: str, language: str, collection_name: str, 
                          qdrant_client: QdrantClient, voyage_client):
    """Process repository by reading files directly from filesystem."""
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
    
    # Collect code files
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
        '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
        '.kt', '.scala', '.r', '.jl', '.dart', '.m', '.mm', '.cc', '.cxx'
    }
    
    files_processed = 0
    total_embeddings = 0
    texts = []
    metadatas = []
    points = []
    
    # Skip directories
    skip_dirs = {'.git', 'node_modules', 'vendor', '__pycache__', '.pytest_cache', 
                 'target', 'build', 'dist', '.next', '.nuxt', 'coverage'}
    
    for file_path in repo_path.rglob('*'):
        # Skip directories we don't want
        if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
            continue
            
        if file_path.is_file() and file_path.suffix in code_extensions:
            try:
                # Skip very large files (> 1MB)
                if file_path.stat().st_size > 1048576:
                    logger.debug(f"Skipping large file: {file_path}")
                    continue
                    
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if len(content) < 50:  # Skip very small files
                    continue
                
                files_processed += 1
                
                # Process entire file content, chunking if necessary
                chunk_size = 2000  # Characters per chunk
                if len(content) > chunk_size:
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                else:
                    chunks = [content]
                
                for chunk_idx, chunk_content in enumerate(chunks):
                    if not chunk_content.strip():
                        continue
                    
                    texts.append(chunk_content)
                    metadatas.append({
                        'file_path': str(file_path),
                        'repository': repo_name,
                        'language': language,
                        'chunk_index': chunk_idx,
                        'total_chunks': len(chunks),
                        'indexed_at': datetime.now().isoformat()
                    })
                
                # Process batch when we have enough
                if len(texts) >= 10:
                    embeddings = create_embeddings(texts, voyage_client)
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
                        logger.info(f"Created {len(embeddings)} embeddings ({files_processed} files processed)")
                    
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
                        
            except Exception as e:
                logger.debug(f"Error processing {file_path}: {e}")
                continue
    
    # Process remaining texts
    if texts:
        embeddings = create_embeddings(texts, voyage_client)
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
    
    # Upload remaining points
    if points:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Uploaded final {len(points)} embeddings to Qdrant")
    
    logger.info(f"Processed {files_processed} files, created {total_embeddings} embeddings")
    return total_embeddings


def main():
    """Main function to create embeddings for all repositories."""
    # Check API key
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY environment variable not set")
        return
    
    # Setup paths
    indexes_dir = Path(".indexes")
    qdrant_path = indexes_dir / "qdrant" / "main.qdrant"
    
    # Ensure Qdrant directory exists
    qdrant_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize Voyage AI client
    logger.info("Initializing Voyage AI client...")
    voyage_client = voyageai.Client(api_key=api_key)
    
    # Initialize Qdrant client
    logger.info("Initializing Qdrant client...")
    qdrant_client = QdrantClient(path=str(qdrant_path))
    
    # Find all test repositories
    repos = find_test_repositories()
    logger.info(f"Found {len(repos)} test repositories")
    
    # Group by language for summary
    by_language = {}
    for repo in repos:
        lang = repo['language']
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(repo)
    
    logger.info("Repository distribution:")
    for lang, lang_repos in sorted(by_language.items()):
        logger.info(f"  {lang}: {len(lang_repos)} repositories")
    
    # Process each repository
    total_embeddings = 0
    results = []
    
    start_time = datetime.now()
    
    for i, repo_info in enumerate(repos, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing repository {i}/{len(repos)}")
        logger.info(f"{'='*60}")
        
        # Collection will be created in process_repository function
        
        # Process repository
        try:
            embeddings_count = process_repository(repo_info, qdrant_client, voyage_client)
            total_embeddings += embeddings_count
            
            results.append({
                "repo_path": str(repo_info['path']),
                "repo_name": repo_info['name'],
                "language": repo_info['language'],
                "embeddings": embeddings_count,
                "success": True
            })
            
            logger.info(f"✅ Successfully created {embeddings_count} embeddings for {repo_info['name']}")
        except Exception as e:
            logger.error(f"❌ Failed to process {repo_info['name']}: {e}")
            results.append({
                "repo_path": str(repo_info['path']),
                "repo_name": repo_info['name'],
                "language": repo_info['language'],
                "embeddings": 0,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("INDEXING COMPLETE")
    logger.info(f"{'='*60}")
    total_time = datetime.now() - start_time
    logger.info(f"Total repositories processed: {len(repos)}")
    logger.info(f"Total embeddings created: {total_embeddings}")
    logger.info(f"Total time: {total_time.total_seconds():.1f}s")
    
    # Save results
    results_path = Path("semantic_indexing_results.json")
    with open(results_path, 'w') as f:
        json.dump({
            "total_repos": len(repo_dirs),
            "total_embeddings": total_embeddings,
            "results": results
        }, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_path}")
    
    # Update repository mapping
    update_repository_mapping(results)


def update_repository_mapping(results):
    """Update the repository mapping file with semantic collection info."""
    # Create comprehensive mapping
    mapping = {
        "qdrant_collections": {},
        "repository_mapping": {},
        "summary": {
            "total_repositories": len(results),
            "successfully_indexed": sum(1 for r in results if r["success"] and r["embeddings"] > 0),
            "total_embeddings": sum(r["embeddings"] for r in results if r["success"])
        }
    }
    
    # Update mappings
    for result in results:
        if result["success"] and result["embeddings"] > 0:
            # Derive collection name
            collection_name = f"{result['language']}_{result['repo_name']}".replace("-", "_").replace(" ", "_").lower()
            
            mapping["qdrant_collections"][collection_name] = {
                "path": ".indexes/qdrant/main.qdrant",
                "points": result["embeddings"],
                "repo_name": result["repo_name"],
                "language": result["language"]
            }
            
            # Update repository mapping
            repo_key = f"{result['language']}_{result['repo_name']}"
            mapping["repository_mapping"][repo_key] = {
                "language": result["language"],
                "qdrant_collection": collection_name,
                "qdrant_path": ".indexes/qdrant/main.qdrant",
                "embeddings": result["embeddings"]
            }
    
    # Save updated mapping
    with open("complete_semantic_mapping.json", 'w') as f:
        json.dump(mapping, f, indent=2)
    
    logger.info(f"Complete semantic mapping saved to: complete_semantic_mapping.json")


if __name__ == "__main__":
    main()