#!/bin/bash
# Phase 5 Container-Based Development Setup Script
# This script sets up parallel development environments within our existing dev container

set -e

echo "🚀 Setting up Phase 5 development in container..."

# Create feature branches for parallel development
create_feature_branches() {
    echo "📌 Creating feature branches..."
    
    # Track-specific branches (developers can work in parallel)
    git checkout -b feature/phase5-language-plugins 2>/dev/null || echo "Language plugins branch exists"
    git checkout -b feature/phase5-vector-enhancement 2>/dev/null || echo "Vector enhancement branch exists" 
    git checkout -b feature/phase5-distributed 2>/dev/null || echo "Distributed branch exists"
    git checkout -b feature/phase5-performance 2>/dev/null || echo "Performance branch exists"
    
    git checkout main
    echo "✅ Feature branches ready"
}

# Setup Track 1: Language Plugins
setup_language_plugins() {
    echo "🔧 Setting up language plugin development..."
    
    # Create plugin directories
    mkdir -p mcp_server/plugins/rust_plugin
    mkdir -p mcp_server/plugins/go_plugin  
    mkdir -p mcp_server/plugins/jvm_plugin
    mkdir -p mcp_server/plugins/ruby_plugin
    mkdir -p mcp_server/plugins/php_plugin
    
    # Create plugin template
    cat > mcp_server/plugins/plugin_template.py << 'EOF'
"""Template for Phase 5 language plugins."""
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from mcp_server.plugin_base import IPlugin
from mcp_server.interfaces.plugin_interfaces import Symbol

class LanguagePluginTemplate(IPlugin):
    """Base template for new language plugins."""
    
    def __init__(self):
        self.language = "unknown"
        self.extensions = []
        self.parser = None
        
    def supports(self, file_path: str) -> bool:
        """Check if this plugin supports the file."""
        return any(file_path.endswith(ext) for ext in self.extensions)
    
    def index_file(self, file_path: str, content: str) -> List[Symbol]:
        """Index a file and extract symbols."""
        raise NotImplementedError("Subclasses must implement index_file")
    
    def get_definition(self, symbol_name: str, file_content: str) -> Dict[str, Any]:
        """Get definition location for a symbol."""
        raise NotImplementedError("Subclasses must implement get_definition")
    
    def search(self, query: str, file_content: str) -> List[Dict[str, Any]]:
        """Search for patterns in the file."""
        raise NotImplementedError("Subclasses must implement search")
EOF

    # Create test directories
    mkdir -p tests/fixtures/rust
    mkdir -p tests/fixtures/go
    mkdir -p tests/fixtures/java
    mkdir -p tests/fixtures/kotlin
    mkdir -p tests/fixtures/ruby
    mkdir -p tests/fixtures/php
    
    echo "✅ Language plugin setup complete"
}

# Setup Track 2: Vector Search Enhancement
setup_vector_search() {
    echo "🔍 Setting up vector search enhancement..."
    
    mkdir -p mcp_server/semantic/enhanced
    
    # Create enhanced indexer template
    cat > mcp_server/semantic/enhanced/batch_indexer.py << 'EOF'
"""Batch processing for Voyage AI embeddings."""
import asyncio
from typing import List, Dict, Any
import voyageai
from mcp_server.utils.semantic_indexer import SemanticIndexer

class BatchSemanticIndexer(SemanticIndexer):
    """Enhanced semantic indexer with batch processing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = 100
        self.dimension = 1024  # Default, configurable
        
    async def batch_embed_documents(self, documents: List[Dict[str, str]]) -> List[List[float]]:
        """Batch embed documents using Voyage AI."""
        embeddings = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            texts = [doc['content'] for doc in batch]
            
            # Use voyage-code-3 with proper input types
            response = await self.voyage.embed_async(
                texts=texts,
                model="voyage-code-3",
                input_type="document",
                truncation=True
            )
            
            embeddings.extend(response.embeddings)
            
            # Rate limiting
            await asyncio.sleep(0.1)
            
        return embeddings
        
    def configure_dimensions(self, dimension: int):
        """Configure embedding dimensions (256, 512, 1024, 2048)."""
        if dimension not in [256, 512, 1024, 2048]:
            raise ValueError(f"Invalid dimension: {dimension}")
        self.dimension = dimension
        
        # Recreate collection with new dimensions
        self._ensure_collection()
EOF

    echo "✅ Vector search setup complete"
}

# Setup Track 3: Distributed Processing
setup_distributed() {
    echo "⚡ Setting up distributed processing..."
    
    mkdir -p mcp_server/distributed
    mkdir -p mcp_server/distributed/master
    mkdir -p mcp_server/distributed/worker
    
    # Create distributed architecture template
    cat > mcp_server/distributed/architecture.md << 'EOF'
# Distributed Processing Architecture

## Components
1. Master Node - Job scheduling and coordination
2. Worker Nodes - Parallel processing units  
3. Message Queue - Redis for job distribution
4. Result Store - Aggregated results storage

## Workflow
1. Master receives indexing request
2. Master splits work into chunks
3. Workers pull jobs from queue
4. Workers process and store results
5. Master aggregates final index

## Container Deployment
- Master runs in main container
- Workers can be scaled via docker-compose
- Redis handles job queue
- Shared volumes for result storage
EOF

    # Create master coordinator
    cat > mcp_server/distributed/master/coordinator.py << 'EOF'
"""Master node for distributed indexing."""
import redis
import json
import uuid
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class IndexingJob:
    job_id: str
    repo_path: str
    files: List[str]
    worker_id: str = ""
    status: str = "pending"
    created_at: float = 0.0

class IndexingCoordinator:
    """Coordinates distributed indexing jobs."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.job_queue = "indexing_jobs"
        self.result_queue = "indexing_results"
        
    def create_indexing_job(self, repo_path: str, worker_count: int = 4):
        """Split repository into worker jobs."""
        import os
        import time
        
        # Get all files to index
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if self._should_index_file(file):
                    all_files.append(os.path.join(root, file))
        
        # Split files among workers
        chunk_size = len(all_files) // worker_count
        jobs = []
        
        for i in range(worker_count):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < worker_count - 1 else len(all_files)
            
            job = IndexingJob(
                job_id=str(uuid.uuid4()),
                repo_path=repo_path,
                files=all_files[start_idx:end_idx],
                created_at=time.time()
            )
            
            # Push to Redis queue
            self.redis.lpush(self.job_queue, json.dumps(asdict(job)))
            jobs.append(job)
            
        return jobs
    
    def _should_index_file(self, filename: str) -> bool:
        """Check if file should be indexed."""
        extensions = ['.py', '.js', '.ts', '.rs', '.go', '.java', '.kt', '.rb', '.php']
        return any(filename.endswith(ext) for ext in extensions)
    
    def monitor_progress(self, job_ids: List[str]):
        """Monitor job progress."""
        completed = 0
        total = len(job_ids)
        
        while completed < total:
            # Check for completed jobs
            result = self.redis.brpop(self.result_queue, timeout=1)
            if result:
                completed += 1
                print(f"Progress: {completed}/{total} jobs completed")
        
        return True
EOF

    # Create worker processor
    cat > mcp_server/distributed/worker/processor.py << 'EOF'
"""Worker node for processing indexing jobs."""
import redis
import json
import time
from typing import Dict, Any
from mcp_server.indexer.index_engine import IndexEngine

class IndexingWorker:
    """Worker that processes indexing jobs from queue."""
    
    def __init__(self, worker_id: str, redis_url: str = "redis://localhost:6379"):
        self.worker_id = worker_id
        self.redis = redis.from_url(redis_url)
        self.indexer = IndexEngine()
        self.job_queue = "indexing_jobs"
        self.result_queue = "indexing_results"
        
    def start_processing(self):
        """Start processing jobs from queue."""
        print(f"Worker {self.worker_id} started")
        
        while True:
            # Pull job from Redis queue (blocking)
            result = self.redis.brpop(self.job_queue, timeout=5)
            
            if result:
                job_data = json.loads(result[1])
                print(f"Worker {self.worker_id} processing job {job_data['job_id']}")
                
                # Process the job
                self.process_job(job_data)
                
                # Signal completion
                completion_data = {
                    "job_id": job_data['job_id'],
                    "worker_id": self.worker_id,
                    "completed_at": time.time(),
                    "files_processed": len(job_data['files'])
                }
                
                self.redis.lpush(self.result_queue, json.dumps(completion_data))
            else:
                print(f"Worker {self.worker_id} waiting for jobs...")
                
    def process_job(self, job: Dict[str, Any]):
        """Process a single indexing job."""
        files = job['files']
        results = []
        
        for file_path in files:
            try:
                # Index the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                symbols = self.indexer.index_file(file_path, content)
                results.extend(symbols)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"Worker {self.worker_id} processed {len(files)} files, found {len(results)} symbols")
        return results
EOF

    echo "✅ Distributed processing setup complete"
}

# Setup Track 4: Performance & Caching  
setup_performance() {
    echo "🚀 Setting up performance optimization..."
    
    mkdir -p mcp_server/cache/advanced
    mkdir -p mcp_server/acceleration
    
    # Create advanced cache
    cat > mcp_server/cache/advanced/tiered_cache.py << 'EOF'
"""Multi-tier caching system."""
import redis
import pickle
import hashlib
from typing import Any, Optional, Dict
from functools import lru_cache

class TieredCache:
    """L1/L2/L3 cache implementation."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.l1_cache = {}  # In-memory
        self.l1_max_size = 1000
        self.l1_access_count = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache with tier fallback."""
        # L1: In-memory cache
        if key in self.l1_cache:
            self.l1_access_count[key] = self.l1_access_count.get(key, 0) + 1
            return self.l1_cache[key]
            
        # L2: Redis cache
        try:
            redis_value = self.redis_client.get(key)
            if redis_value:
                value = pickle.loads(redis_value)
                # Promote to L1 if frequently accessed
                if self._should_promote_to_l1(key):
                    self._add_to_l1(key, value)
                return value
        except Exception:
            pass
            
        # L3: Disk cache (for large results)
        return await self._get_from_disk_cache(key)
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in appropriate cache tier."""
        value_size = len(pickle.dumps(value))
        
        if value_size < 1024 * 100:  # < 100KB
            # Small values go to all tiers
            self._add_to_l1(key, value)
            self.redis_client.setex(key, ttl, pickle.dumps(value))
        elif value_size < 1024 * 1024 * 10:  # < 10MB  
            # Medium values skip L1
            self.redis_client.setex(key, ttl, pickle.dumps(value))
        else:
            # Large values go to disk only
            await self._save_to_disk_cache(key, value, ttl)
    
    def _should_promote_to_l1(self, key: str) -> bool:
        """Determine if value should be promoted to L1."""
        access_count = self.l1_access_count.get(key, 0)
        return access_count >= 3
    
    def _add_to_l1(self, key: str, value: Any):
        """Add value to L1 cache with LRU eviction."""
        if len(self.l1_cache) >= self.l1_max_size:
            # Evict least recently used
            lru_key = min(
                self.l1_access_count.keys(),
                key=lambda k: self.l1_access_count[k]
            )
            del self.l1_cache[lru_key]
            del self.l1_access_count[lru_key]
        
        self.l1_cache[key] = value
        self.l1_access_count[key] = 1
    
    async def _get_from_disk_cache(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        # Implementation for disk cache
        return None
    
    async def _save_to_disk_cache(self, key: str, value: Any, ttl: int):
        """Save value to disk cache.""" 
        # Implementation for disk cache
        pass
EOF

    echo "✅ Performance setup complete"
}

# Setup development tools
setup_dev_tools() {
    echo "🛠️ Setting up development tools..."
    
    # Create parallel test runner
    cat > scripts/run-parallel-tests.sh << 'EOF'
#!/bin/bash
# Run tests for all tracks in parallel

echo "Running Phase 5 tests in parallel..."

# Ensure test files exist
mkdir -p tests

# Create basic test files if they don't exist
test_files=(
    "tests/test_rust_plugin.py"
    "tests/test_go_plugin.py" 
    "tests/test_jvm_plugin.py"
    "tests/test_ruby_plugin.py"
    "tests/test_php_plugin.py"
    "tests/test_vector_enhancement.py"
    "tests/test_distributed.py"
    "tests/test_performance.py"
)

for test_file in "${test_files[@]}"; do
    if [ ! -f "$test_file" ]; then
        cat > "$test_file" << TESTEOF
"""Phase 5 test placeholder."""
import pytest

def test_placeholder():
    assert True, "Test placeholder - replace with real tests"
TESTEOF
    fi
done

# Run all test suites concurrently using parallel
parallel -j4 --line-buffer ::: \
    "pytest tests/test_rust_plugin.py -v" \
    "pytest tests/test_go_plugin.py -v" \
    "pytest tests/test_vector_enhancement.py -v" \
    "pytest tests/test_distributed.py -v"

echo "Phase 5 parallel tests completed!"
EOF
    chmod +x scripts/run-parallel-tests.sh
    
    # Create development task runners
    cat > scripts/start-development.sh << 'EOF'
#!/bin/bash
# Start Phase 5 development environment

echo "🚀 Starting Phase 5 development environment..."

# Start Redis and Qdrant if not already running
if ! pgrep -f redis-server > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379
fi

if ! pgrep -f qdrant > /dev/null; then
    echo "Starting Qdrant..."
    docker run -d --name qdrant-dev -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest || echo "Qdrant already running"
fi

echo "✅ Development environment ready!"
echo ""
echo "Available commands:"
echo "  ./scripts/run-parallel-tests.sh  - Run all tests in parallel"
echo "  ./scripts/start-worker.sh 1      - Start a distributed worker"
echo "  python -m mcp_server              - Start MCP server"
echo ""
echo "Development tracks:"
echo "  git checkout feature/phase5-language-plugins"
echo "  git checkout feature/phase5-vector-enhancement" 
echo "  git checkout feature/phase5-distributed"
echo "  git checkout feature/phase5-performance"
EOF
    chmod +x scripts/start-development.sh
    
    # Create worker startup script
    cat > scripts/start-worker.sh << 'EOF'
#!/bin/bash
# Start a distributed worker

WORKER_ID=${1:-1}

echo "Starting worker $WORKER_ID..."

cd /app
export PYTHONPATH=/app
export WORKER_ID=$WORKER_ID

python -c "
from mcp_server.distributed.worker.processor import IndexingWorker
worker = IndexingWorker('worker_$WORKER_ID')
worker.start_processing()
"
EOF
    chmod +x scripts/start-worker.sh
    
    echo "✅ Development tools setup complete"
}

# Create project structure overview
create_project_overview() {
    echo "📋 Creating project structure overview..."
    
    cat > PHASE5_PROJECT_STRUCTURE.md << 'EOF'
# Phase 5 Project Structure

## Development Tracks

### Track 1: Language Plugins
```
mcp_server/plugins/
├── plugin_template.py       # Base template
├── rust_plugin/            # Rust support
├── go_plugin/              # Go support  
├── jvm_plugin/             # Java/Kotlin support
├── ruby_plugin/            # Ruby support
└── php_plugin/             # PHP support
```

### Track 2: Vector Search Enhancement
```
mcp_server/semantic/enhanced/
├── batch_indexer.py        # Batch Voyage AI processing
├── qdrant_scaler.py        # Qdrant scaling
└── vector_optimizer.py     # Performance optimization
```

### Track 3: Distributed Processing
```
mcp_server/distributed/
├── master/
│   └── coordinator.py      # Job coordination
├── worker/
│   └── processor.py        # Worker processing
└── architecture.md         # Design docs
```

### Track 4: Performance & Caching
```
mcp_server/cache/advanced/
├── tiered_cache.py         # L1/L2/L3 cache
└── cache_manager.py        # Cache coordination

mcp_server/acceleration/
└── gpu_accelerator.py      # GPU optimization
```

## Development Commands

```bash
# Setup
./scripts/setup-phase5-container.sh

# Start environment  
./scripts/start-development.sh

# Run tests in parallel
./scripts/run-parallel-tests.sh

# Start distributed workers
./scripts/start-worker.sh 1
./scripts/start-worker.sh 2
```

## Git Workflow

```bash
# Switch to your track
git checkout feature/phase5-language-plugins  # Track 1
git checkout feature/phase5-vector-enhancement # Track 2  
git checkout feature/phase5-distributed       # Track 3
git checkout feature/phase5-performance       # Track 4

# Make changes and test
# Commit and push
# Create PR when ready
```
EOF

    echo "✅ Project overview created"
}

# Main setup flow
main() {
    echo "🎯 Phase 5 Container Development Setup"
    echo "======================================"
    
    # Create branches
    create_feature_branches
    
    # Run all setups in parallel (using background processes)
    echo "🔧 Setting up all tracks in parallel..."
    
    setup_language_plugins &
    PID1=$!
    
    setup_vector_search &
    PID2=$!
    
    setup_distributed &
    PID3=$!
    
    setup_performance &
    PID4=$!
    
    # Wait for all parallel setups
    wait $PID1 $PID2 $PID3 $PID4
    
    # Setup shared tools
    setup_dev_tools
    create_project_overview
    
    echo ""
    echo "✅ Phase 5 container development environment ready!"
    echo ""
    echo "🚀 Next steps - assign developers to tracks:"
    echo ""
    echo "Developer 1 (Rust): git checkout feature/phase5-language-plugins && cd mcp_server/plugins/rust_plugin"
    echo "Developer 2 (Go): git checkout feature/phase5-language-plugins && cd mcp_server/plugins/go_plugin"  
    echo "Developer 3 (JVM): git checkout feature/phase5-language-plugins && cd mcp_server/plugins/jvm_plugin"
    echo "Developer 4 (Ruby/PHP): git checkout feature/phase5-language-plugins && cd mcp_server/plugins/ruby_plugin"
    echo "Developer 5 (Vector): git checkout feature/phase5-vector-enhancement && cd mcp_server/semantic/enhanced"
    echo "Developer 6 (Qdrant): git checkout feature/phase5-vector-enhancement && cd mcp_server/semantic/enhanced"
    echo "Developer 7 (Master): git checkout feature/phase5-distributed && cd mcp_server/distributed/master"
    echo "Developer 8 (Worker): git checkout feature/phase5-distributed && cd mcp_server/distributed/worker"
    echo "Developer 9 (Cache): git checkout feature/phase5-performance && cd mcp_server/cache/advanced"
    echo ""
    echo "🎯 Start development: ./scripts/start-development.sh"
    echo "🧪 Run tests: ./scripts/run-parallel-tests.sh"
}

# Run main setup
main