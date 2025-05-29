# Qdrant Documentation

## Overview and Key Features

Qdrant is a vector similarity search engine designed to work with high-dimensional vectors produced by neural networks. It provides a production-ready service for storing, searching, and managing vectors with additional payload, making it ideal for semantic search, recommendation systems, and similarity matching applications.

### Key Features
- **High Performance**: Optimized for vector similarity search at scale
- **Filtering Support**: Combine vector search with attribute filtering
- **Payload Storage**: Store and filter by additional metadata
- **Real-time Updates**: Add, update, and delete vectors in real-time
- **Distributed**: Horizontal scaling with sharding and replication
- **REST & gRPC APIs**: Multiple interfaces for different use cases
- **Rich Query Language**: Complex filtering and search conditions
- **Persistence**: Disk-based storage with memory caching
- **Cloud-Native**: Docker support and Kubernetes-ready

## Installation and Basic Setup

### Installing Qdrant

```bash
# Using Docker (recommended)
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Using Docker Compose
cat > docker-compose.yml << EOF
version: '3.4'
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
EOF

docker-compose up -d
```

### Python Client Installation

```bash
# Basic installation
pip install qdrant-client

# With all optional dependencies
pip install "qdrant-client[fastembed]"
```

### Basic Configuration

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Local connection
client = QdrantClient(host="localhost", port=6333)

# In-memory mode (for testing)
client = QdrantClient(":memory:")

# Cloud connection
client = QdrantClient(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key",
)

# Create a collection
client.create_collection(
    collection_name="code_embeddings",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
```

## MCP Server Use Cases

### 1. Semantic Code Search

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint
)
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import hashlib

@dataclass
class CodeEmbedding:
    file_path: str
    function_name: str
    code_snippet: str
    language: str
    vector: List[float]
    metadata: Dict[str, Any]

class SemanticCodeSearch:
    """Semantic search for code using Qdrant."""
    
    def __init__(self, qdrant_client: QdrantClient, 
                 model_name: str = "microsoft/codebert-base"):
        self.client = qdrant_client
        self.collection_name = "code_search"
        self.model = SentenceTransformer(model_name)
        self.vector_size = self.model.get_sentence_embedding_dimension()
        
        # Initialize collection
        self._init_collection()
    
    def _init_collection(self):
        """Initialize Qdrant collection for code search."""
        collections = self.client.get_collections().collections
        
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "indexing_threshold": 20000,
                    "memmap_threshold": 50000
                }
            )
            
            # Create payload indices for filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="language",
                field_type="keyword"
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="file_path",
                field_type="keyword"
            )
    
    def _generate_id(self, file_path: str, function_name: str) -> str:
        """Generate unique ID for a code snippet."""
        content = f"{file_path}:{function_name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def index_code(self, code_embedding: CodeEmbedding):
        """Index a code snippet."""
        point_id = self._generate_id(
            code_embedding.file_path,
            code_embedding.function_name
        )
        
        # Prepare payload
        payload = {
            "file_path": code_embedding.file_path,
            "function_name": code_embedding.function_name,
            "code_snippet": code_embedding.code_snippet,
            "language": code_embedding.language,
            **code_embedding.metadata
        }
        
        # Create point
        point = PointStruct(
            id=point_id,
            vector=code_embedding.vector,
            payload=payload
        )
        
        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def index_batch(self, embeddings: List[CodeEmbedding]):
        """Index multiple code snippets efficiently."""
        points = []
        
        for embedding in embeddings:
            point_id = self._generate_id(
                embedding.file_path,
                embedding.function_name
            )
            
            payload = {
                "file_path": embedding.file_path,
                "function_name": embedding.function_name,
                "code_snippet": embedding.code_snippet,
                "language": embedding.language,
                **embedding.metadata
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding.vector,
                payload=payload
            ))
        
        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True
        )
    
    def search(self, query: str, limit: int = 10,
              language: Optional[str] = None,
              file_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar code snippets."""
        # Encode query
        query_vector = self.model.encode(query).tolist()
        
        # Build filter
        must_conditions = []
        if language:
            must_conditions.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(value=language)
                )
            )
        
        if file_pattern:
            must_conditions.append(
                FieldCondition(
                    key="file_path",
                    match=MatchValue(value=file_pattern)
                )
            )
        
        search_filter = Filter(must=must_conditions) if must_conditions else None
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter,
            with_payload=True
        )
        
        # Format results
        return [
            {
                "score": result.score,
                "file_path": result.payload["file_path"],
                "function_name": result.payload["function_name"],
                "code_snippet": result.payload["code_snippet"],
                "language": result.payload["language"],
                "metadata": {
                    k: v for k, v in result.payload.items()
                    if k not in ["file_path", "function_name", "code_snippet", "language"]
                }
            }
            for result in results
        ]
    
    def find_similar_functions(self, file_path: str, function_name: str,
                             limit: int = 5) -> List[Dict[str, Any]]:
        """Find functions similar to a given function."""
        point_id = self._generate_id(file_path, function_name)
        
        # Get the original point
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True
            )
            
            if not points:
                return []
            
            original_vector = points[0].vector
            
            # Search for similar
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=original_vector,
                limit=limit + 1,  # +1 to exclude self
                with_payload=True
            )
            
            # Filter out the original
            return [
                {
                    "score": r.score,
                    "file_path": r.payload["file_path"],
                    "function_name": r.payload["function_name"],
                    "code_snippet": r.payload["code_snippet"],
                    "language": r.payload["language"]
                }
                for r in results
                if r.id != point_id
            ][:limit]
            
        except Exception:
            return []
```

### 2. Documentation Search Engine

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import re
from typing import List, Dict, Optional
from datetime import datetime

class DocumentationSearch:
    """Search engine for code documentation."""
    
    def __init__(self, qdrant_client: QdrantClient,
                 embedding_model: SentenceTransformer):
        self.client = qdrant_client
        self.collection_name = "documentation"
        self.model = embedding_model
        self.vector_size = self.model.get_sentence_embedding_dimension()
        
        self._init_collection()
    
    def _init_collection(self):
        """Initialize documentation collection."""
        collections = self.client.get_collections().collections
        
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "content": VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    ),
                    "title": VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                }
            )
            
            # Create indices
            for field in ["doc_type", "module", "class_name", "language"]:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_type="keyword"
                )
    
    def index_documentation(self, doc_id: str, title: str, content: str,
                          doc_type: str, metadata: Dict[str, Any]):
        """Index documentation with multiple vectors."""
        # Generate embeddings
        title_vector = self.model.encode(title).tolist()
        content_vector = self.model.encode(content[:2000]).tolist()  # Limit content length
        
        # Prepare payload
        payload = {
            "title": title,
            "content": content,
            "doc_type": doc_type,
            "indexed_at": datetime.utcnow().isoformat(),
            **metadata
        }
        
        # Create point with named vectors
        point = PointStruct(
            id=doc_id,
            vector={
                "content": content_vector,
                "title": title_vector
            },
            payload=payload
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def search_documentation(self, query: str, 
                           search_mode: str = "content",
                           doc_type: Optional[str] = None,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """Search documentation by content or title."""
        # Encode query
        query_vector = self.model.encode(query).tolist()
        
        # Build filter
        filters = []
        if doc_type:
            filters.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchValue(value=doc_type)
                )
            )
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=Filter(must=filters) if filters else None,
            limit=limit,
            vector_name=search_mode,  # "content" or "title"
            with_payload=True
        )
        
        return [
            {
                "score": r.score,
                "title": r.payload["title"],
                "content": r.payload["content"],
                "doc_type": r.payload["doc_type"],
                "metadata": {
                    k: v for k, v in r.payload.items()
                    if k not in ["title", "content", "doc_type"]
                }
            }
            for r in results
        ]
    
    def hybrid_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform hybrid search on both title and content."""
        query_vector = self.model.encode(query).tolist()
        
        # Search by title
        title_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            vector_name="title",
            with_payload=True
        )
        
        # Search by content
        content_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            vector_name="content",
            with_payload=True
        )
        
        # Merge results with weighted scores
        results_map = {}
        
        for r in title_results:
            results_map[r.id] = {
                "title_score": r.score * 1.5,  # Boost title matches
                "content_score": 0,
                "payload": r.payload
            }
        
        for r in content_results:
            if r.id in results_map:
                results_map[r.id]["content_score"] = r.score
            else:
                results_map[r.id] = {
                    "title_score": 0,
                    "content_score": r.score,
                    "payload": r.payload
                }
        
        # Calculate combined scores
        combined_results = []
        for doc_id, data in results_map.items():
            combined_score = data["title_score"] + data["content_score"]
            combined_results.append({
                "score": combined_score,
                "title_score": data["title_score"],
                "content_score": data["content_score"],
                **data["payload"]
            })
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_results[:limit]
```

### 3. Code Clone Detection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
import ast
import hashlib
from typing import List, Dict, Tuple, Set

class CodeCloneDetector:
    """Detect similar or duplicate code using vector similarity."""
    
    def __init__(self, qdrant_client: QdrantClient,
                 embedding_model: SentenceTransformer):
        self.client = qdrant_client
        self.collection_name = "code_clones"
        self.model = embedding_model
        self.vector_size = self.model.get_sentence_embedding_dimension()
        
        self._init_collection()
    
    def _init_collection(self):
        """Initialize collection for clone detection."""
        collections = self.client.get_collections().collections
        
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                optimizers_config={
                    "indexing_threshold": 10000
                }
            )
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for better similarity comparison."""
        try:
            # Parse and unparse to normalize formatting
            tree = ast.parse(code)
            # Remove docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    if (node.body and 
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Str)):
                        node.body = node.body[1:]
            
            return ast.unparse(tree)
        except:
            # Fallback to simple normalization
            lines = code.strip().split('\n')
            # Remove comments and empty lines
            lines = [l.strip() for l in lines 
                    if l.strip() and not l.strip().startswith('#')]
            return '\n'.join(lines)
    
    def index_code_fragment(self, file_path: str, start_line: int,
                          end_line: int, code: str, fragment_type: str):
        """Index a code fragment for clone detection."""
        # Normalize code
        normalized_code = self._normalize_code(code)
        
        # Generate embedding
        embedding = self.model.encode(normalized_code).tolist()
        
        # Generate ID
        fragment_id = hashlib.sha256(
            f"{file_path}:{start_line}:{end_line}".encode()
        ).hexdigest()[:16]
        
        # Create point
        point = PointStruct(
            id=fragment_id,
            vector=embedding,
            payload={
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "fragment_type": fragment_type,
                "code": code,
                "normalized_code": normalized_code,
                "line_count": end_line - start_line + 1,
                "char_count": len(code)
            }
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def find_clones(self, code: str, similarity_threshold: float = 0.9,
                   min_lines: int = 5) -> List[Dict[str, Any]]:
        """Find code clones similar to given code."""
        # Normalize and encode
        normalized_code = self._normalize_code(code)
        embedding = self.model.encode(normalized_code).tolist()
        
        # Search with threshold
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="line_count",
                        range={"gte": min_lines}
                    )
                ]
            ),
            limit=100,
            score_threshold=similarity_threshold,
            with_payload=True
        )
        
        clones = []
        for r in results:
            clone_info = {
                "similarity": r.score,
                "file_path": r.payload["file_path"],
                "start_line": r.payload["start_line"],
                "end_line": r.payload["end_line"],
                "fragment_type": r.payload["fragment_type"],
                "code": r.payload["code"],
                "line_count": r.payload["line_count"]
            }
            
            # Calculate detailed similarity metrics
            clone_info["metrics"] = self._calculate_similarity_metrics(
                normalized_code,
                r.payload["normalized_code"]
            )
            
            clones.append(clone_info)
        
        return clones
    
    def _calculate_similarity_metrics(self, code1: str, code2: str) -> Dict[str, float]:
        """Calculate detailed similarity metrics."""
        from difflib import SequenceMatcher
        
        # Token-based similarity
        tokens1 = set(code1.split())
        tokens2 = set(code2.split())
        
        jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2) if tokens1 | tokens2 else 0
        
        # Sequence similarity
        sequence_sim = SequenceMatcher(None, code1, code2).ratio()
        
        return {
            "jaccard_similarity": jaccard,
            "sequence_similarity": sequence_sim,
            "token_overlap": len(tokens1 & tokens2),
            "unique_tokens": len(tokens1 | tokens2)
        }
    
    def detect_cross_project_clones(self, project_paths: List[str],
                                  similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
        """Detect clones across multiple projects."""
        # Group by project
        project_filter = Filter(
            should=[
                FieldCondition(
                    key="file_path",
                    match={"text": path}
                )
                for path in project_paths
            ]
        )
        
        # Retrieve all fragments
        fragments = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=project_filter,
            limit=1000,
            with_payload=True,
            with_vectors=True
        )
        
        # Find cross-project clones
        cross_clones = []
        processed = set()
        
        for i, frag1 in enumerate(fragments[0]):
            for j, frag2 in enumerate(fragments[0][i+1:], i+1):
                # Skip if same project
                proj1 = self._get_project(frag1.payload["file_path"], project_paths)
                proj2 = self._get_project(frag2.payload["file_path"], project_paths)
                
                if proj1 == proj2:
                    continue
                
                # Skip if already processed
                pair = tuple(sorted([frag1.id, frag2.id]))
                if pair in processed:
                    continue
                processed.add(pair)
                
                # Calculate similarity
                similarity = self._cosine_similarity(frag1.vector, frag2.vector)
                
                if similarity >= similarity_threshold:
                    cross_clones.append({
                        "similarity": similarity,
                        "fragment1": {
                            "project": proj1,
                            "file": frag1.payload["file_path"],
                            "lines": f"{frag1.payload['start_line']}-{frag1.payload['end_line']}",
                            "type": frag1.payload["fragment_type"]
                        },
                        "fragment2": {
                            "project": proj2,
                            "file": frag2.payload["file_path"],
                            "lines": f"{frag2.payload['start_line']}-{frag2.payload['end_line']}",
                            "type": frag2.payload["fragment_type"]
                        }
                    })
        
        return sorted(cross_clones, key=lambda x: x["similarity"], reverse=True)
    
    def _get_project(self, file_path: str, project_paths: List[str]) -> str:
        """Determine which project a file belongs to."""
        for project in project_paths:
            if file_path.startswith(project):
                return project
        return "unknown"
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 * norm2 else 0
```

### 4. API Recommendation System

```python
from qdrant_client import QdrantClient
from qdrant_client.models import RecommendStrategy, Filter, FieldCondition
from collections import defaultdict
import json

class APIRecommendationSystem:
    """Recommend APIs based on code context."""
    
    def __init__(self, qdrant_client: QdrantClient,
                 embedding_model: SentenceTransformer):
        self.client = qdrant_client
        self.collection_name = "api_usage"
        self.model = embedding_model
        self.vector_size = self.model.get_sentence_embedding_dimension()
        
        self._init_collection()
    
    def _init_collection(self):
        """Initialize API usage collection."""
        collections = self.client.get_collections().collections
        
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def index_api_usage(self, context_code: str, api_calls: List[str],
                       language: str, metadata: Dict[str, Any]):
        """Index API usage patterns."""
        # Generate context embedding
        context_vector = self.model.encode(context_code).tolist()
        
        # Create unique ID
        usage_id = hashlib.sha256(
            f"{context_code}:{':'.join(sorted(api_calls))}".encode()
        ).hexdigest()[:16]
        
        # Create point
        point = PointStruct(
            id=usage_id,
            vector=context_vector,
            payload={
                "context_code": context_code,
                "api_calls": api_calls,
                "language": language,
                "api_count": len(api_calls),
                **metadata
            }
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def recommend_apis(self, code_context: str, limit: int = 10,
                      language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recommend APIs based on code context."""
        # Encode context
        context_vector = self.model.encode(code_context).tolist()
        
        # Build filter
        filters = []
        if language:
            filters.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(value=language)
                )
            )
        
        # Search similar contexts
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=context_vector,
            query_filter=Filter(must=filters) if filters else None,
            limit=limit * 3,  # Get more to aggregate
            with_payload=True
        )
        
        # Aggregate API recommendations
        api_scores = defaultdict(float)
        api_contexts = defaultdict(list)
        
        for result in results:
            for api in result.payload["api_calls"]:
                # Weight by similarity score
                api_scores[api] += result.score
                api_contexts[api].append({
                    "score": result.score,
                    "context": result.payload["context_code"][:200]
                })
        
        # Sort by score
        recommendations = []
        for api, score in sorted(api_scores.items(), 
                               key=lambda x: x[1], reverse=True)[:limit]:
            recommendations.append({
                "api": api,
                "confidence": score / len(api_contexts[api]),
                "total_score": score,
                "usage_count": len(api_contexts[api]),
                "example_contexts": api_contexts[api][:3]
            })
        
        return recommendations
    
    def get_api_usage_patterns(self, api_name: str, 
                             limit: int = 10) -> List[Dict[str, Any]]:
        """Get common usage patterns for a specific API."""
        # Search for all usages of this API
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="api_calls",
                        match={"any": [api_name]}
                    )
                ]
            ),
            limit=100,
            with_payload=True,
            with_vectors=True
        )
        
        if not results[0]:
            return []
        
        # Cluster usage patterns
        patterns = []
        
        # Simple clustering by finding diverse examples
        selected_indices = set()
        
        while len(patterns) < limit and len(selected_indices) < len(results[0]):
            # Find most diverse from already selected
            best_idx = None
            best_diversity = -1
            
            for i, point in enumerate(results[0]):
                if i in selected_indices:
                    continue
                
                if not selected_indices:
                    # First selection
                    best_idx = i
                    break
                
                # Calculate minimum similarity to selected
                min_sim = float('inf')
                for j in selected_indices:
                    sim = self._cosine_similarity(
                        point.vector,
                        results[0][j].vector
                    )
                    min_sim = min(min_sim, sim)
                
                if min_sim > best_diversity:
                    best_diversity = min_sim
                    best_idx = i
            
            if best_idx is not None:
                selected_indices.add(best_idx)
                point = results[0][best_idx]
                
                # Extract pattern info
                patterns.append({
                    "context_code": point.payload["context_code"],
                    "co_occurring_apis": [
                        api for api in point.payload["api_calls"]
                        if api != api_name
                    ],
                    "language": point.payload.get("language", "unknown"),
                    "metadata": {
                        k: v for k, v in point.payload.items()
                        if k not in ["context_code", "api_calls", "language"]
                    }
                })
        
        return patterns
```

## Code Examples

### Basic Vector Operations

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Initialize client
client = QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="embeddings",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

# Insert vectors
points = [
    PointStruct(
        id=1,
        vector=[0.1] * 384,
        payload={"text": "Example 1", "category": "A"}
    ),
    PointStruct(
        id=2,
        vector=[0.2] * 384,
        payload={"text": "Example 2", "category": "B"}
    )
]

client.upsert(collection_name="embeddings", points=points)

# Search
results = client.search(
    collection_name="embeddings",
    query_vector=[0.15] * 384,
    limit=5
)
```

### Advanced Filtering

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

# Text matching
filter_category = Filter(
    must=[
        FieldCondition(
            key="category",
            match=MatchValue(value="A")
        )
    ]
)

# Range filtering
filter_range = Filter(
    must=[
        FieldCondition(
            key="score",
            range=Range(gte=0.5, lte=0.9)
        )
    ]
)

# Combined filters
combined_filter = Filter(
    must=[
        FieldCondition(key="language", match=MatchValue(value="python")),
        FieldCondition(key="lines", range=Range(gte=10))
    ],
    should=[
        FieldCondition(key="complexity", match=MatchValue(value="high")),
        FieldCondition(key="complexity", match=MatchValue(value="medium"))
    ]
)

# Search with filter
results = client.search(
    collection_name="code_embeddings",
    query_vector=query_vector,
    query_filter=combined_filter,
    limit=10
)
```

### Batch Operations

```python
# Batch insert with progress
from tqdm import tqdm

def batch_index_embeddings(embeddings: List[tuple], batch_size: int = 100):
    """Index embeddings in batches."""
    total = len(embeddings)
    
    for i in tqdm(range(0, total, batch_size)):
        batch = embeddings[i:i + batch_size]
        points = [
            PointStruct(
                id=idx,
                vector=vec,
                payload=payload
            )
            for idx, vec, payload in batch
        ]
        
        client.upsert(
            collection_name="embeddings",
            points=points,
            wait=True  # Wait for indexing
        )

# Batch retrieval
def retrieve_batch(ids: List[int], batch_size: int = 100):
    """Retrieve points in batches."""
    all_points = []
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        points = client.retrieve(
            collection_name="embeddings",
            ids=batch_ids,
            with_payload=True,
            with_vectors=True
        )
        all_points.extend(points)
    
    return all_points
```

## Best Practices

### 1. Collection Design

```python
class OptimizedCollection:
    """Best practices for collection design."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def create_optimized_collection(self, name: str, vector_size: int,
                                  expected_points: int):
        """Create collection with optimal settings."""
        # Determine optimal parameters based on scale
        if expected_points < 10000:
            # Small collection
            optimizers_config = {
                "indexing_threshold": 1000,
                "memmap_threshold": 5000
            }
        elif expected_points < 1000000:
            # Medium collection
            optimizers_config = {
                "indexing_threshold": 20000,
                "memmap_threshold": 100000
            }
        else:
            # Large collection
            optimizers_config = {
                "indexing_threshold": 50000,
                "memmap_threshold": 500000
            }
        
        # Create collection
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
                hnsw_config={
                    "m": 16,
                    "ef_construct": 100,
                    "full_scan_threshold": 10000
                }
            ),
            optimizers_config=optimizers_config,
            shard_number=max(1, expected_points // 1000000),  # 1 shard per million
            replication_factor=1  # Increase for HA
        )
        
        # Create indices for common filters
        common_fields = ["language", "file_type", "project", "author"]
        for field in common_fields:
            try:
                self.client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_type="keyword"
                )
            except:
                pass  # Field might not exist yet
```

### 2. Error Handling and Retries

```python
import time
from functools import wraps

def qdrant_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying Qdrant operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
            
            raise last_exception
        return wrapper
    return decorator

class ResilientQdrantClient:
    """Qdrant client with built-in resilience."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    @qdrant_retry()
    def search(self, collection_name: str, query_vector: List[float], **kwargs):
        """Search with automatic retry."""
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            **kwargs
        )
    
    @qdrant_retry()
    def upsert(self, collection_name: str, points: List[PointStruct], **kwargs):
        """Upsert with automatic retry."""
        return self.client.upsert(
            collection_name=collection_name,
            points=points,
            **kwargs
        )
```

### 3. Performance Monitoring

```python
import time
from contextlib import contextmanager
from typing import Dict
import statistics

class QdrantPerformanceMonitor:
    """Monitor Qdrant operation performance."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
    
    @contextmanager
    def measure(self, operation: str):
        """Measure operation duration."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.metrics:
            return {}
        
        durations = self.metrics[operation]
        return {
            "count": len(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "p95": statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations),
            "min": min(durations),
            "max": max(durations)
        }
    
    def print_report(self):
        """Print performance report."""
        print("\n=== Qdrant Performance Report ===")
        for operation, durations in self.metrics.items():
            stats = self.get_stats(operation)
            print(f"\n{operation}:")
            print(f"  Count: {stats['count']}")
            print(f"  Mean: {stats['mean']:.3f}s")
            print(f"  Median: {stats['median']:.3f}s")
            print(f"  P95: {stats['p95']:.3f}s")

# Usage
monitor = QdrantPerformanceMonitor()

with monitor.measure("search"):
    results = client.search(...)

with monitor.measure("upsert"):
    client.upsert(...)

monitor.print_report()
```

### 4. Data Consistency

```python
class ConsistentQdrantOperations:
    """Ensure data consistency in Qdrant operations."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def atomic_update(self, collection_name: str, point_id: int,
                     new_vector: List[float], new_payload: Dict[str, Any]):
        """Atomically update point vector and payload."""
        # Use optimistic concurrency control
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Get current point
                points = self.client.retrieve(
                    collection_name=collection_name,
                    ids=[point_id],
                    with_payload=True,
                    with_vectors=True
                )
                
                if not points:
                    raise ValueError(f"Point {point_id} not found")
                
                current_point = points[0]
                
                # Update point
                updated_point = PointStruct(
                    id=point_id,
                    vector=new_vector,
                    payload={**current_point.payload, **new_payload}
                )
                
                # Upsert with verification
                self.client.upsert(
                    collection_name=collection_name,
                    points=[updated_point],
                    wait=True
                )
                
                # Verify update
                verification = self.client.retrieve(
                    collection_name=collection_name,
                    ids=[point_id],
                    with_payload=True
                )
                
                if verification[0].payload == updated_point.payload:
                    return True
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (2 ** attempt))
        
        return False
    
    def bulk_update_with_rollback(self, collection_name: str,
                                 updates: List[Dict[str, Any]]):
        """Bulk update with rollback capability."""
        # Backup current state
        backup_points = []
        
        try:
            # Backup
            for update in updates:
                points = self.client.retrieve(
                    collection_name=collection_name,
                    ids=[update['id']],
                    with_payload=True,
                    with_vectors=True
                )
                if points:
                    backup_points.append(points[0])
            
            # Perform updates
            update_points = [
                PointStruct(
                    id=update['id'],
                    vector=update.get('vector'),
                    payload=update.get('payload', {})
                )
                for update in updates
            ]
            
            self.client.upsert(
                collection_name=collection_name,
                points=update_points,
                wait=True
            )
            
        except Exception as e:
            # Rollback
            print(f"Error during update, rolling back: {e}")
            if backup_points:
                self.client.upsert(
                    collection_name=collection_name,
                    points=backup_points,
                    wait=True
                )
            raise
```

## Performance Tips

### 1. Vector Optimization

```python
import numpy as np

class VectorOptimizer:
    """Optimize vectors for Qdrant storage and search."""
    
    @staticmethod
    def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / (norms + 1e-10)
    
    @staticmethod
    def quantize_vectors(vectors: np.ndarray, bits: int = 8) -> np.ndarray:
        """Quantize vectors to reduce memory usage."""
        if bits == 8:
            # Scale to int8 range
            min_val = vectors.min()
            max_val = vectors.max()
            scale = 255.0 / (max_val - min_val)
            quantized = ((vectors - min_val) * scale).astype(np.uint8)
            return quantized
        else:
            raise ValueError("Only 8-bit quantization supported")
    
    @staticmethod
    def reduce_dimensions(vectors: np.ndarray, target_dim: int) -> np.ndarray:
        """Reduce vector dimensions using PCA."""
        from sklearn.decomposition import PCA
        
        if vectors.shape[1] <= target_dim:
            return vectors
        
        pca = PCA(n_components=target_dim)
        reduced = pca.fit_transform(vectors)
        
        print(f"Explained variance: {pca.explained_variance_ratio_.sum():.2%}")
        return reduced
```

### 2. Efficient Searching

```python
class EfficientSearcher:
    """Efficient search strategies for Qdrant."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def two_stage_search(self, collection_name: str, query_vector: List[float],
                        initial_limit: int = 100, final_limit: int = 10,
                        filter_func: callable = None):
        """Two-stage search for better precision."""
        # Stage 1: Fast approximate search
        initial_results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=initial_limit,
            params={"hnsw_ef": 64}  # Lower ef for speed
        )
        
        if not filter_func:
            return initial_results[:final_limit]
        
        # Stage 2: Detailed filtering
        filtered_results = []
        for result in initial_results:
            if filter_func(result):
                filtered_results.append(result)
                if len(filtered_results) >= final_limit:
                    break
        
        return filtered_results
    
    def parallel_search(self, collection_name: str, 
                       query_vectors: List[List[float]],
                       limit: int = 10) -> List[List[ScoredPoint]]:
        """Search multiple vectors in parallel."""
        from concurrent.futures import ThreadPoolExecutor
        
        def search_single(query_vector):
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(search_single, query_vectors))
        
        return results
```

### 3. Memory Management

```python
class QdrantMemoryManager:
    """Manage memory usage in Qdrant operations."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def stream_large_dataset(self, collection_name: str, vectors_file: str,
                           batch_size: int = 1000):
        """Stream large datasets without loading all into memory."""
        import h5py
        
        with h5py.File(vectors_file, 'r') as f:
            vectors_dataset = f['vectors']
            payloads_dataset = f['payloads']
            
            total = len(vectors_dataset)
            
            for i in range(0, total, batch_size):
                # Load batch
                batch_vectors = vectors_dataset[i:i+batch_size]
                batch_payloads = payloads_dataset[i:i+batch_size]
                
                # Create points
                points = [
                    PointStruct(
                        id=i+j,
                        vector=batch_vectors[j].tolist(),
                        payload=json.loads(batch_payloads[j])
                    )
                    for j in range(len(batch_vectors))
                ]
                
                # Upsert batch
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True
                )
                
                print(f"Processed {min(i+batch_size, total)}/{total}")
    
    def optimize_collection(self, collection_name: str):
        """Optimize collection for better memory usage."""
        # Update collection parameters
        self.client.update_collection(
            collection_name=collection_name,
            optimizers_config={
                "deleted_threshold": 0.2,
                "vacuum_min_vector_number": 100000,
                "default_segment_number": 2,
                "max_segment_size": 200000,
                "memmap_threshold": 50000,
                "indexing_threshold": 20000,
                "flush_interval_sec": 5,
                "max_optimization_threads": 2
            }
        )
```

### 4. Monitoring and Metrics

```python
class QdrantMonitor:
    """Monitor Qdrant cluster health and performance."""
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def get_collection_metrics(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed collection metrics."""
        info = self.client.get_collection(collection_name)
        
        return {
            "status": info.status,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "config": {
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
                "shard_number": info.config.params.shard_number,
                "replication_factor": info.config.params.replication_factor
            }
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check overall cluster health."""
        try:
            # Get cluster info
            collections = self.client.get_collections()
            
            # Test search on each collection
            health_status = {
                "status": "healthy",
                "collections": {}
            }
            
            for collection in collections.collections:
                try:
                    # Perform test search
                    test_vector = [0.0] * collection.config.params.vectors.size
                    self.client.search(
                        collection_name=collection.name,
                        query_vector=test_vector,
                        limit=1
                    )
                    health_status["collections"][collection.name] = "ok"
                except Exception as e:
                    health_status["collections"][collection.name] = f"error: {str(e)}"
                    health_status["status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
```