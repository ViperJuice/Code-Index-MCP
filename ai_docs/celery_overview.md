# Celery Overview

## Introduction
Celery is a distributed task queue system for Python that enables asynchronous task execution. It's designed to handle millions of tasks and is the de-facto standard for Python applications requiring background job processing.

## Key Features

### Core Capabilities
- **Distributed Processing**: Scale across multiple workers and machines
- **Asynchronous Execution**: Non-blocking task execution
- **Task Scheduling**: Cron-like periodic task execution
- **Result Storage**: Track task results and status
- **Task Routing**: Route tasks to specific workers
- **Rate Limiting**: Control task execution rate
- **Retries**: Automatic retry with exponential backoff

### Why Celery for MCP Server
- Handle long-running indexing operations
- Process file changes asynchronously
- Batch embedding generation
- Schedule periodic index maintenance
- Distribute work across multiple cores

## Installation

```bash
# Install with Redis support
pip install "celery[redis]"

# Additional dependencies for monitoring
pip install flower  # Web-based monitoring
pip install celery-progress  # Progress bars
```

## Basic Configuration

### Celery Application Setup
```python
# celery_app.py
from celery import Celery

# Create Celery instance
app = Celery(
    'mcp_server',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['mcp_server.tasks']
)

# Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)
```

### Redis Configuration
```python
app.conf.broker_transport_options = {
    'visibility_timeout': 3600,  # 1 hour
    'fanout_prefix': True,
    'fanout_patterns': True,
    'priority_steps': list(range(10)),  # Priority queue support
}
```

## MCP Server Task Implementation

### Task Definitions
```python
# tasks.py
from celery import Task
from celery.utils.log import get_task_logger
from typing import Dict, List
import time

logger = get_task_logger(__name__)

class CallbackTask(Task):
    """Task that sends progress updates"""
    def on_success(self, retval, task_id, args, kwargs):
        """Called on successful completion"""
        logger.info(f'Task {task_id} succeeded with result: {retval}')
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f'Task {task_id} failed: {exc}')

@app.task(base=CallbackTask, bind=True, name='index_file')
def index_file(self, file_path: str) -> Dict:
    """Index a single file asynchronously"""
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Parsing file...'}
        )
        
        # Simulate indexing work
        result = parse_and_index_file(file_path)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Complete'}
        )
        
        return {
            'file_path': file_path,
            'symbols': result['symbols'],
            'status': 'success'
        }
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

@app.task(bind=True, name='batch_index_files')
def batch_index_files(self, file_paths: List[str]) -> Dict:
    """Index multiple files with progress tracking"""
    total = len(file_paths)
    results = []
    
    for i, file_path in enumerate(file_paths):
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i,
                'total': total,
                'status': f'Processing {file_path}'
            }
        )
        
        # Process file
        result = index_file.apply_async(args=[file_path])
        results.append(result.id)
    
    return {'task_ids': results, 'total': total}

@app.task(name='generate_embeddings')
def generate_embeddings(content: str, model: str = 'voyage-code-3') -> List[float]:
    """Generate embeddings for code content"""
    logger.info(f"Generating embeddings for content of length {len(content)}")
    
    # Call embedding service
    embeddings = embedding_service.generate(content, model)
    
    return embeddings

@app.task(name='cleanup_old_indices')
def cleanup_old_indices(days: int = 7) -> Dict:
    """Periodic task to clean up old indices"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    deleted_count = delete_indices_before(cutoff_date)
    
    return {
        'deleted': deleted_count,
        'cutoff_date': cutoff_date.isoformat()
    }
```

### Task Chaining and Workflows
```python
from celery import chain, group, chord

# Chain tasks sequentially
@app.task
def process_repository(repo_path: str):
    """Process entire repository"""
    workflow = chain(
        scan_directory.s(repo_path),
        group(index_file.s(f) for f in files),
        generate_repository_summary.s()
    )
    return workflow.apply_async()

# Parallel processing with chord
@app.task
def parallel_index_with_summary(file_paths: List[str]):
    """Index files in parallel and generate summary"""
    callback = generate_summary.s()
    header = group(index_file.s(f) for f in file_paths)
    result = chord(header)(callback)
    return result
```

## Worker Management

### Starting Workers
```bash
# Start worker with concurrency
celery -A mcp_server.celery_app worker --loglevel=info --concurrency=4

# Start worker with specific queues
celery -A mcp_server.celery_app worker -Q indexing,embeddings --loglevel=info

# Start beat scheduler for periodic tasks
celery -A mcp_server.celery_app beat --loglevel=info
```

### Worker Configuration
```python
# Worker optimizations
app.conf.worker_pool = 'prefork'  # or 'eventlet' for I/O bound tasks
app.conf.worker_concurrency = 4
app.conf.worker_prefetch_multiplier = 1  # Disable prefetch for long tasks
app.conf.task_acks_late = True  # Acknowledge after completion
```

## Queue Management

### Priority Queues
```python
# Define task priorities
app.conf.task_routes = {
    'index_file': {'queue': 'indexing', 'priority': 5},
    'generate_embeddings': {'queue': 'embeddings', 'priority': 3},
    'cleanup_old_indices': {'queue': 'maintenance', 'priority': 1},
}

# Send high-priority task
index_file.apply_async(
    args=['/critical/file.py'],
    priority=9,  # 0-9, higher is more important
    queue='indexing'
)
```

### Rate Limiting
```python
# Limit task execution rate
app.conf.task_annotations = {
    'generate_embeddings': {
        'rate_limit': '100/m',  # 100 per minute
    },
    'external_api_call': {
        'rate_limit': '10/s',  # 10 per second
    },
}
```

## Monitoring and Management

### Flower Web UI
```bash
# Start Flower monitoring
celery -A mcp_server.celery_app flower --port=5555

# Access at http://localhost:5555
```

### Programmatic Monitoring
```python
from celery import current_app
from celery.result import AsyncResult

# Check task status
def get_task_status(task_id: str) -> Dict:
    result = AsyncResult(task_id, app=current_app)
    
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None,
        'info': result.info,
        'traceback': result.traceback if result.failed() else None
    }

# Get active tasks
def get_active_tasks() -> List[Dict]:
    inspect = current_app.control.inspect()
    active = inspect.active()
    
    return [
        {
            'worker': worker,
            'tasks': tasks
        }
        for worker, tasks in active.items()
    ]
```

## Error Handling and Retries

### Retry Configuration
```python
@app.task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def resilient_task(self, data):
    """Task with automatic retry"""
    try:
        return process_data(data)
    except RecoverableError as exc:
        # Exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)
```

### Dead Letter Queue
```python
# Configure dead letter queue
app.conf.task_reject_on_worker_lost = True
app.conf.task_ignore_result = False

@app.task(bind=True, max_retries=3)
def task_with_dlq(self, data):
    try:
        return process(data)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # Send to dead letter queue
            send_to_dlq.delay(
                task_name=self.name,
                args=self.request.args,
                kwargs=self.request.kwargs,
                exception=str(exc)
            )
        raise
```

## Best Practices

### 1. Task Design
```python
# Keep tasks idempotent
@app.task
def idempotent_index(file_path: str, file_hash: str):
    """Only index if file changed"""
    if is_already_indexed(file_path, file_hash):
        return {'status': 'skipped', 'reason': 'already indexed'}
    
    return perform_indexing(file_path)

# Keep tasks atomic
@app.task
def atomic_operation(data):
    """Single responsibility task"""
    # Do one thing well
    return transform_data(data)
```

### 2. Memory Management
```python
# Limit task memory usage
app.conf.worker_max_memory_per_child = 1000000  # 1GB

# Process large files in chunks
@app.task
def process_large_file(file_path: str, chunk_size: int = 1000):
    """Process file in chunks to avoid memory issues"""
    with open(file_path, 'r') as f:
        while True:
            chunk = list(itertools.islice(f, chunk_size))
            if not chunk:
                break
            process_chunk.delay(chunk)
```

### 3. Result Backend Optimization
```python
# Don't store results for fire-and-forget tasks
@app.task(ignore_result=True)
def fire_and_forget_task(data):
    """Task that doesn't return results"""
    send_notification(data)

# Use result backend only when needed
app.conf.task_ignore_result = True  # Global default
app.conf.task_store_eager_result = False
```

## Integration with FastAPI

```python
# api/endpoints.py
from fastapi import BackgroundTasks, HTTPException
from celery.result import AsyncResult

@app.post("/index/async")
async def trigger_async_indexing(
    file_path: str,
    background_tasks: BackgroundTasks
):
    """Trigger async indexing via Celery"""
    task = index_file.delay(file_path)
    
    return {
        "task_id": task.id,
        "status": "queued",
        "status_url": f"/tasks/{task.id}"
    }

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Check task status"""
    result = AsyncResult(task_id)
    
    if result.state == 'PENDING':
        return {"status": "pending"}
    elif result.state == 'PROGRESS':
        return {
            "status": "progress",
            "current": result.info.get('current', 0),
            "total": result.info.get('total', 1)
        }
    elif result.state == 'SUCCESS':
        return {
            "status": "success",
            "result": result.result
        }
    else:
        return {
            "status": "failed",
            "error": str(result.info)
        }
```

## Performance Tuning

### 1. Connection Pooling
```python
# Redis connection pool
app.conf.broker_pool_limit = 10
app.conf.redis_max_connections = 20
app.conf.broker_connection_retry_on_startup = True
```

### 2. Batch Processing
```python
@app.task
def batch_process_symbols(symbols: List[Dict], batch_size: int = 100):
    """Process symbols in batches"""
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        process_symbol_batch.delay(batch)
```

### 3. Task Optimization
```python
# Use immutable signatures for performance
sig = index_file.si('/path/to/file')  # Immutable signature

# Disable rate limits for internal tasks
@app.task(rate_limit=None)
def internal_task(data):
    return process_internally(data)
```

## Production Deployment

### Supervisor Configuration
```ini
[program:celery_worker]
command=celery -A mcp_server.celery_app worker -l info
directory=/opt/mcp_server
user=mcp
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:celery_beat]
command=celery -A mcp_server.celery_app beat -l info
directory=/opt/mcp_server
user=mcp
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
autostart=true
autorestart=true
```

### Docker Deployment
```dockerfile
# Worker container
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["celery", "-A", "mcp_server.celery_app", "worker", "--loglevel=info"]
```

## Security Considerations

1. **Message Signing**: Enable message signing to prevent tampering
2. **Result Encryption**: Encrypt sensitive task results
3. **Access Control**: Limit worker access to specific queues
4. **Network Security**: Use Redis AUTH and SSL/TLS
5. **Resource Limits**: Set memory and CPU limits for workers

Celery provides the robust task queue infrastructure needed for MCP Server's asynchronous operations, enabling efficient background processing of indexing, embedding generation, and maintenance tasks.