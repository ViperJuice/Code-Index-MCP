#!/usr/bin/env python3
"""
Index only test repositories with semantic embeddings.
This script directly processes files from test_repos directory.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_test_repositories() -> List[Dict[str, str]]:
    """Find all test repositories and determine their languages."""
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


def collect_code_files(repo_path: Path, limit: int = 100) -> List[tuple]:
    """Collect code files from a repository."""
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
        '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
        '.kt', '.scala', '.r', '.jl', '.dart', '.m', '.mm'
    }
    
    files = []
    count = 0
    
    for file_path in repo_path.rglob('*'):
        if count >= limit:
            break
            
        if file_path.is_file() and file_path.suffix in code_extensions:
            # Skip test files and vendor directories
            path_str = str(file_path)
            if any(skip in path_str for skip in ['test/', 'vendor/', 'node_modules/', '.git/']):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if len(content) > 50:  # Skip very small files
                    files.append((str(file_path), content))
                    count += 1
            except Exception:
                continue
    
    return files


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


def process_repository(repo_info: Dict[str, str], qdrant_client: QdrantClient, voyage_client) -> Dict[str, Any]:
    """Process a single repository and create embeddings."""
    repo_path = Path(repo_info['path'])
    collection_name = f"{repo_info['language']}_{repo_info['name']}".replace("-", "_").lower()
    
    logger.info(f"Processing {repo_info['name']} ({repo_info['language']})")
    
    # Create or get collection
    try:
        qdrant_client.get_collection(collection_name)
        logger.info(f"Collection '{collection_name}' already exists")
    except:
        logger.info(f"Creating collection '{collection_name}'")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            )
        )
    
    # Collect code files
    files = collect_code_files(repo_path, limit=50)  # Limit files per repo
    logger.info(f"Found {len(files)} code files")
    
    if not files:
        return {
            'repo': repo_info['name'],
            'language': repo_info['language'],
            'collection': collection_name,
            'embeddings': 0,
            'success': True
        }
    
    # Process in batches
    batch_size = 5
    total_embeddings = 0
    points = []
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        texts = []
        metadatas = []
        
        for file_path, content in batch:
            # Take first 1000 lines
            lines = content.split('\n')[:1000]
            chunk_content = '\n'.join(lines)
            
            texts.append(chunk_content)
            metadatas.append({
                'file_path': file_path,
                'repository': repo_info['name'],
                'language': repo_info['language'],
                'indexed_at': datetime.now().isoformat()
            })
        
        if texts:
            # Create embeddings
            embeddings = create_embeddings(texts, voyage_client)
            
            if embeddings:
                # Create points for Qdrant
                for embedding, metadata in zip(embeddings, metadatas):
                    unique_str = f"{collection_name}:{metadata['file_path']}"
                    point_id = abs(hash(unique_str)) % (10**15)
                    
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=metadata
                        )
                    )
                
                total_embeddings += len(embeddings)
                logger.info(f"Created {len(embeddings)} embeddings (batch {i//batch_size + 1})")
    
    # Upload all points
    if points:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Uploaded {len(points)} embeddings to Qdrant")
    
    return {
        'repo': repo_info['name'],
        'language': repo_info['language'],
        'collection': collection_name,
        'embeddings': total_embeddings,
        'success': True
    }


def main():
    """Main function to create embeddings for test repositories."""
    # Check API key
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY not set!")
        return
    
    logger.info("Starting semantic indexing of test repositories")
    
    # Initialize clients
    voyage_client = voyageai.Client(api_key=api_key)
    qdrant_path = ".indexes/qdrant/main.qdrant"
    Path(qdrant_path).parent.mkdir(parents=True, exist_ok=True)
    qdrant_client = QdrantClient(path=qdrant_path)
    
    # Find test repositories
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
    total_embeddings = 0
    
    # Process top repositories from each language
    for language, lang_repos in by_language.items():
        # Take up to 3 repositories per language
        for repo_info in lang_repos[:3]:
            logger.info(f"\n{'='*60}")
            try:
                result = process_repository(repo_info, qdrant_client, voyage_client)
                results.append(result)
                total_embeddings += result['embeddings']
                logger.info(f"✅ Success: {result['embeddings']} embeddings")
            except Exception as e:
                logger.error(f"❌ Failed: {e}")
                results.append({
                    'repo': repo_info['name'],
                    'language': repo_info['language'],
                    'collection': f"{repo_info['language']}_{repo_info['name']}",
                    'embeddings': 0,
                    'success': False,
                    'error': str(e)
                })
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("INDEXING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total repositories processed: {len(results)}")
    logger.info(f"Total embeddings created: {total_embeddings}")
    
    # Save results
    results_path = Path("test_repos_semantic_results.json")
    with open(results_path, 'w') as f:
        json.dump({
            "total_repos": len(results),
            "total_embeddings": total_embeddings,
            "results": results
        }, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_path}")
    
    # Create repository mapping
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
                "repo_name": result['repo'],
                "language": result['language']
            }
            
            repo_key = f"{result['language']}_{result['repo']}"
            mapping["repository_mapping"][repo_key] = {
                "language": result['language'],
                "qdrant_collection": collection,
                "qdrant_path": qdrant_path
            }
    
    mapping_path = Path("test_repos_mapping.json")
    with open(mapping_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    logger.info(f"Repository mapping saved to: {mapping_path}")


if __name__ == "__main__":
    main()