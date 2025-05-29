# Redis Documentation

## Overview and Key Features

Redis (Remote Dictionary Server) is an open-source, in-memory data structure store that can be used as a database, cache, message broker, and queue. It supports various data structures and provides high performance through memory-based operations.

### Key Features
- **In-Memory Storage**: Extremely fast read/write operations
- **Data Structures**: Strings, hashes, lists, sets, sorted sets, bitmaps, hyperloglogs, geospatial indexes
- **Persistence**: Optional disk persistence with RDB snapshots and AOF logs
- **Pub/Sub**: Built-in publish/subscribe messaging
- **Transactions**: Atomic execution of command groups
- **Lua Scripting**: Server-side scripting for complex operations
- **Clustering**: Horizontal scaling with automatic sharding
- **Replication**: Master-slave replication for high availability

## Installation and Basic Setup

### Installing Redis

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install redis-server

# macOS (using Homebrew)
brew install redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### Python Client Installation

```bash
pip install redis
# For async support
pip install redis[hiredis]
```

### Basic Configuration

```python
import redis

# Standard connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Connection pool (recommended for production)
pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)

# With authentication
r = redis.Redis(
    host='localhost',
    port=6379,
    password='your_password',
    ssl=True,
    ssl_cert_reqs='required'
)
```

## MCP Server Use Cases

### 1. Caching Code Analysis Results

```python
import redis
import json
import hashlib
from typing import Optional, Dict, Any

class CodeAnalysisCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour default TTL
    
    def _generate_key(self, file_path: str, analysis_type: str) -> str:
        """Generate a unique cache key."""
        content = f"{file_path}:{analysis_type}"
        return f"mcp:analysis:{hashlib.md5(content.encode()).hexdigest()}"
    
    def get_analysis(self, file_path: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results."""
        key = self._generate_key(file_path, analysis_type)
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set_analysis(self, file_path: str, analysis_type: str, 
                     results: Dict[str, Any], ttl: Optional[int] = None):
        """Cache analysis results."""
        key = self._generate_key(file_path, analysis_type)
        self.redis.setex(
            key, 
            ttl or self.ttl,
            json.dumps(results)
        )
    
    def invalidate(self, file_path: str):
        """Invalidate all cached analyses for a file."""
        pattern = f"mcp:analysis:*{file_path}*"
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)
```

### 2. Task Queue Backend

```python
import redis
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

class TaskQueue:
    def __init__(self, redis_client: redis.Redis, queue_name: str = 'mcp:tasks'):
        self.redis = redis_client
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}:processing"
        self.failed_queue = f"{queue_name}:failed"
    
    def enqueue(self, task_type: str, payload: Dict[str, Any], 
                priority: int = 0) -> str:
        """Add a task to the queue."""
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'type': task_type,
            'payload': payload,
            'created_at': datetime.utcnow().isoformat(),
            'priority': priority
        }
        
        # Use sorted set for priority queue
        self.redis.zadd(
            self.queue_name,
            {json.dumps(task): priority}
        )
        return task_id
    
    def dequeue(self, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Get the highest priority task."""
        # Blocking pop from sorted set
        result = self.redis.bzpopmin(self.queue_name, timeout)
        if result:
            _, task_json, _ = result
            task = json.loads(task_json)
            
            # Move to processing queue
            self.redis.hset(self.processing_queue, task['id'], task_json)
            return task
        return None
    
    def complete(self, task_id: str):
        """Mark a task as completed."""
        self.redis.hdel(self.processing_queue, task_id)
    
    def fail(self, task_id: str, error: str):
        """Move a task to the failed queue."""
        task_json = self.redis.hget(self.processing_queue, task_id)
        if task_json:
            task = json.loads(task_json)
            task['error'] = error
            task['failed_at'] = datetime.utcnow().isoformat()
            
            self.redis.hset(self.failed_queue, task_id, json.dumps(task))
            self.redis.hdel(self.processing_queue, task_id)
```

### 3. Session Management

```python
import redis
import json
from typing import Dict, Any, Optional
from datetime import timedelta

class SessionManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "mcp:session:"
        self.default_ttl = timedelta(hours=24)
    
    def create_session(self, user_id: str, data: Dict[str, Any]) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        key = f"{self.prefix}{session_id}"
        
        session_data = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'data': data
        }
        
        self.redis.setex(
            key,
            self.default_ttl,
            json.dumps(session_data)
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data."""
        key = f"{self.prefix}{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update session data and refresh TTL."""
        session = self.get_session(session_id)
        if session:
            session['data'].update(data)
            session['updated_at'] = datetime.utcnow().isoformat()
            
            key = f"{self.prefix}{session_id}"
            self.redis.setex(
                key,
                self.default_ttl,
                json.dumps(session)
            )
```

## Code Examples

### Using Redis Data Structures

```python
# Strings
r.set('key', 'value')
value = r.get('key')

# Hashes (ideal for storing objects)
r.hset('user:1000', mapping={
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30
})
user = r.hgetall('user:1000')

# Lists (queues, logs)
r.lpush('queue:tasks', 'task1', 'task2')
task = r.rpop('queue:tasks')

# Sets (unique collections)
r.sadd('tags:python', 'web', 'api', 'backend')
tags = r.smembers('tags:python')

# Sorted Sets (leaderboards, priorities)
r.zadd('leaderboard', {'player1': 100, 'player2': 85})
top_players = r.zrevrange('leaderboard', 0, 9, withscores=True)

# Pub/Sub
# Publisher
r.publish('notifications', json.dumps({'event': 'file_changed', 'file': 'main.py'}))

# Subscriber
pubsub = r.pubsub()
pubsub.subscribe('notifications')
for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        print(f"Received: {data}")
```

### Atomic Operations and Transactions

```python
# Atomic increment
r.incr('counter')
r.incrby('counter', 5)

# Transactions
with r.pipeline() as pipe:
    pipe.multi()
    pipe.set('key1', 'value1')
    pipe.set('key2', 'value2')
    pipe.incr('counter')
    results = pipe.execute()

# Optimistic locking with WATCH
def transfer_funds(from_account: str, to_account: str, amount: float):
    with r.pipeline() as pipe:
        while True:
            try:
                # Watch the keys
                pipe.watch(from_account, to_account)
                
                # Get current balances
                from_balance = float(pipe.get(from_account) or 0)
                to_balance = float(pipe.get(to_account) or 0)
                
                if from_balance < amount:
                    pipe.unwatch()
                    raise ValueError("Insufficient funds")
                
                # Start transaction
                pipe.multi()
                pipe.set(from_account, from_balance - amount)
                pipe.set(to_account, to_balance + amount)
                pipe.execute()
                break
            except redis.WatchError:
                # Retry if keys were modified
                continue
```

### Lua Scripting

```python
# Define a Lua script
lua_script = """
local key = KEYS[1]
local increment = ARGV[1]
local current = redis.call('get', key)
if not current then
    current = 0
else
    current = tonumber(current)
end
local new_value = current + tonumber(increment)
redis.call('set', key, new_value)
return new_value
"""

# Register and execute
increment_script = r.register_script(lua_script)
result = increment_script(keys=['counter'], args=[10])
```

## Best Practices

### 1. Connection Management

```python
# Use connection pooling
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=50,
    decode_responses=True
)
r = redis.Redis(connection_pool=pool)

# Context manager for automatic cleanup
class RedisConnection:
    def __init__(self, **kwargs):
        self.pool = redis.ConnectionPool(**kwargs)
        self.redis = None
    
    def __enter__(self):
        self.redis = redis.Redis(connection_pool=self.pool)
        return self.redis
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.disconnect()
```

### 2. Key Naming Conventions

```python
# Use consistent key patterns
KEY_PATTERNS = {
    'user': 'user:{user_id}',
    'session': 'session:{session_id}',
    'cache': 'cache:{type}:{id}',
    'queue': 'queue:{name}',
    'lock': 'lock:{resource}'
}

def get_key(pattern: str, **kwargs) -> str:
    """Generate a key from pattern."""
    return KEY_PATTERNS[pattern].format(**kwargs)
```

### 3. Error Handling

```python
import redis
from functools import wraps
import time

def redis_retry(max_attempts=3, delay=1.0):
    """Decorator for retrying Redis operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except redis.ConnectionError as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
                except redis.TimeoutError:
                    if attempt == max_attempts - 1:
                        raise
                    continue
        return wrapper
    return decorator

@redis_retry()
def get_cached_data(key: str):
    return r.get(key)
```

### 4. Memory Management

```python
# Set memory limits in Redis config
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# Monitor memory usage
def check_memory_usage():
    info = r.info('memory')
    used_memory = info['used_memory_human']
    used_memory_peak = info['used_memory_peak_human']
    return {
        'current': used_memory,
        'peak': used_memory_peak,
        'percentage': info['used_memory_rss'] / info['used_memory_peak']
    }

# Implement key expiration
def set_with_expiry(key: str, value: Any, ttl_seconds: int):
    r.setex(key, ttl_seconds, json.dumps(value))
```

## Performance Tips

### 1. Pipelining

```python
# Bad: Multiple round trips
for i in range(1000):
    r.set(f'key:{i}', f'value:{i}')

# Good: Single round trip
with r.pipeline() as pipe:
    for i in range(1000):
        pipe.set(f'key:{i}', f'value:{i}')
    pipe.execute()
```

### 2. Use Appropriate Data Structures

```python
# Bad: Storing list as JSON string
users = json.dumps(['user1', 'user2', 'user3'])
r.set('users', users)
users = json.loads(r.get('users'))
users.append('user4')
r.set('users', json.dumps(users))

# Good: Use Redis list
r.rpush('users', 'user1', 'user2', 'user3')
r.rpush('users', 'user4')
users = r.lrange('users', 0, -1)
```

### 3. Batch Operations

```python
# Batch get operations
keys = [f'user:{i}' for i in range(100)]
values = r.mget(keys)

# Batch set operations
mapping = {f'user:{i}': f'data:{i}' for i in range(100)}
r.mset(mapping)
```

### 4. Connection Optimization

```python
# Use Unix sockets for local connections
r = redis.Redis(unix_socket_path='/tmp/redis.sock')

# Enable TCP keepalive
r = redis.Redis(
    host='localhost',
    port=6379,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    }
)
```

### 5. Monitor Performance

```python
def monitor_performance():
    """Monitor Redis performance metrics."""
    info = r.info('stats')
    return {
        'total_commands': info['total_commands_processed'],
        'ops_per_sec': info['instantaneous_ops_per_sec'],
        'total_connections': info['total_connections_received'],
        'rejected_connections': info['rejected_connections'],
        'keyspace_hits': info['keyspace_hits'],
        'keyspace_misses': info['keyspace_misses'],
        'hit_rate': info['keyspace_hits'] / (info['keyspace_hits'] + info['keyspace_misses'])
    }
```

## Advanced Patterns

### Distributed Locking

```python
import time
import uuid

class RedisLock:
    def __init__(self, redis_client: redis.Redis, key: str, timeout: int = 10):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.identifier = str(uuid.uuid4())
    
    def acquire(self, blocking: bool = True, blocking_timeout: float = None):
        """Acquire a distributed lock."""
        start_time = time.time()
        
        while True:
            if self.redis.set(self.key, self.identifier, nx=True, ex=self.timeout):
                return True
            
            if not blocking:
                return False
            
            if blocking_timeout is not None:
                if time.time() - start_time > blocking_timeout:
                    return False
            
            time.sleep(0.01)
    
    def release(self):
        """Release the lock if we own it."""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis.eval(lua_script, 1, self.key, self.identifier)
    
    def __enter__(self):
        if not self.acquire():
            raise Exception("Could not acquire lock")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
```

### Rate Limiting

```python
def is_rate_limited(user_id: str, max_requests: int = 100, window: int = 3600) -> bool:
    """Check if user has exceeded rate limit."""
    key = f"rate_limit:{user_id}"
    current_time = int(time.time())
    window_start = current_time - window
    
    # Remove old entries
    r.zremrangebyscore(key, 0, window_start)
    
    # Count requests in current window
    request_count = r.zcard(key)
    
    if request_count < max_requests:
        # Add current request
        r.zadd(key, {str(uuid.uuid4()): current_time})
        r.expire(key, window)
        return False
    
    return True
```