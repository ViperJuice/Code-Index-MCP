# gRPC Overview

## Introduction

gRPC (gRPC Remote Procedure Calls) is a high-performance, open-source framework developed by Google for building distributed systems. It uses Protocol Buffers (protobuf) as its interface definition language and data serialization format, enabling efficient communication between services across different languages and platforms.

## Architecture Overview

### Core Components

1. **Protocol Buffers (protobuf)**
   - Language-neutral, platform-neutral data serialization
   - Strongly typed schema definition
   - Automatic code generation for multiple languages

2. **HTTP/2 Transport**
   - Multiplexed streams over single connection
   - Bidirectional streaming
   - Header compression
   - Flow control

3. **Service Definition**
   - RPC methods defined in `.proto` files
   - Request/response message types
   - Streaming patterns (unary, server, client, bidirectional)

4. **Code Generation**
   - `protoc` compiler generates client/server code
   - Language-specific plugins
   - Type-safe APIs

### Communication Patterns

1. **Unary RPC**: Single request, single response
2. **Server Streaming**: Single request, stream of responses
3. **Client Streaming**: Stream of requests, single response
4. **Bidirectional Streaming**: Stream of requests and responses

## Python Setup and Integration

### Installation

```bash
pip install grpcio grpcio-tools protobuf
```

### Protocol Buffer Definition

```protobuf
// code_index.proto
syntax = "proto3";

package codeindex;

import "google/protobuf/timestamp.proto";
import "google/protobuf/empty.proto";

// Service definition
service CodeIndexService {
  // Unary RPC
  rpc IndexFile(IndexFileRequest) returns (IndexFileResponse);
  
  // Server streaming RPC
  rpc SearchSymbols(SearchRequest) returns (stream SearchResult);
  
  // Client streaming RPC
  rpc BulkIndex(stream IndexFileRequest) returns (BulkIndexResponse);
  
  // Bidirectional streaming RPC
  rpc SyncIndex(stream SyncRequest) returns (stream SyncResponse);
}

// Message definitions
message IndexFileRequest {
  string file_path = 1;
  string content = 2;
  string language = 3;
  map<string, string> metadata = 4;
}

message IndexFileResponse {
  string file_id = 1;
  int32 symbols_count = 2;
  google.protobuf.Timestamp indexed_at = 3;
  bool success = 4;
  string error = 5;
}

message SearchRequest {
  string query = 1;
  repeated string languages = 2;
  int32 limit = 3;
  bool semantic = 4;
  map<string, string> filters = 5;
}

message SearchResult {
  string file_path = 1;
  string symbol = 2;
  string kind = 3;
  int32 line = 4;
  string snippet = 5;
  float score = 6;
}

message SyncRequest {
  oneof request {
    FileChange file_change = 1;
    HeartBeat heartbeat = 2;
    SyncStatus status = 3;
  }
}

message SyncResponse {
  oneof response {
    SyncAck ack = 1;
    SyncError error = 2;
    SyncProgress progress = 3;
  }
}

message FileChange {
  enum ChangeType {
    CREATED = 0;
    MODIFIED = 1;
    DELETED = 2;
  }
  
  string file_path = 1;
  ChangeType type = 2;
  bytes content = 3;
  google.protobuf.Timestamp timestamp = 4;
}

message HeartBeat {
  string client_id = 1;
  google.protobuf.Timestamp timestamp = 2;
}

message SyncStatus {
  string client_id = 1;
  repeated string indexed_files = 2;
  int64 total_size = 3;
}

message SyncAck {
  string file_path = 1;
  bool success = 2;
}

message SyncError {
  string file_path = 1;
  string error = 2;
}

message SyncProgress {
  int32 files_processed = 1;
  int32 total_files = 2;
  float percentage = 3;
}

// Bulk operations
message BulkIndexResponse {
  int32 total_files = 1;
  int32 successful = 2;
  int32 failed = 3;
  repeated string errors = 4;
}
```

### Generate Python Code

```bash
python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./generated \
  --grpc_python_out=./generated \
  code_index.proto
```

## MCP Server Implementation

### Server Implementation

```python
# mcp_server/grpc_server.py
import grpc
from concurrent import futures
import asyncio
from typing import Iterator, AsyncIterator
import logging

from generated import code_index_pb2
from generated import code_index_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime

from .dispatcher import Dispatcher
from .gateway import Gateway
from .watcher import FileWatcher

class CodeIndexServicer(code_index_pb2_grpc.CodeIndexServicer):
    def __init__(self, dispatcher: Dispatcher):
        self.dispatcher = dispatcher
        self.active_syncs = {}
        self.logger = logging.getLogger(__name__)
    
    def IndexFile(self, request, context):
        """Unary RPC: Index a single file"""
        try:
            # Index the file
            result = self.dispatcher.index_file(
                file_path=request.file_path,
                content=request.content,
                language=request.language,
                metadata=dict(request.metadata)
            )
            
            # Create response
            response = code_index_pb2.IndexFileResponse(
                file_id=result['file_id'],
                symbols_count=len(result.get('symbols', [])),
                success=True
            )
            
            # Set timestamp
            timestamp = Timestamp()
            timestamp.FromDatetime(datetime.utcnow())
            response.indexed_at.CopyFrom(timestamp)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error indexing file: {e}")
            return code_index_pb2.IndexFileResponse(
                success=False,
                error=str(e)
            )
    
    def SearchSymbols(self, request, context) -> Iterator[code_index_pb2.SearchResult]:
        """Server streaming RPC: Search and stream results"""
        try:
            # Perform search
            results = self.dispatcher.search(
                query=request.query,
                languages=list(request.languages),
                limit=request.limit,
                semantic=request.semantic,
                filters=dict(request.filters)
            )
            
            # Stream results
            for result in results:
                yield code_index_pb2.SearchResult(
                    file_path=result['file'],
                    symbol=result['symbol'],
                    kind=result.get('kind', 'unknown'),
                    line=result['line'],
                    snippet=result.get('snippet', ''),
                    score=result.get('score', 1.0)
                )
                
        except Exception as e:
            self.logger.error(f"Error searching symbols: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
    
    def BulkIndex(self, request_iterator, context):
        """Client streaming RPC: Bulk index files"""
        successful = 0
        failed = 0
        errors = []
        
        try:
            for request in request_iterator:
                try:
                    self.dispatcher.index_file(
                        file_path=request.file_path,
                        content=request.content,
                        language=request.language
                    )
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{request.file_path}: {str(e)}")
            
            return code_index_pb2.BulkIndexResponse(
                total_files=successful + failed,
                successful=successful,
                failed=failed,
                errors=errors[:10]  # Limit error messages
            )
            
        except Exception as e:
            self.logger.error(f"Error in bulk indexing: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
    
    def SyncIndex(self, request_iterator, context):
        """Bidirectional streaming RPC: Real-time sync"""
        client_id = context.peer()
        self.active_syncs[client_id] = True
        
        try:
            for request in request_iterator:
                if not self.active_syncs.get(client_id):
                    break
                
                # Handle different request types
                if request.HasField('file_change'):
                    response = self._handle_file_change(request.file_change)
                    yield response
                
                elif request.HasField('heartbeat'):
                    # Just acknowledge heartbeat
                    continue
                
                elif request.HasField('status'):
                    response = self._handle_sync_status(request.status)
                    yield response
                    
        except Exception as e:
            self.logger.error(f"Error in sync: {e}")
            error_response = code_index_pb2.SyncResponse()
            error_response.error.error = str(e)
            yield error_response
        finally:
            del self.active_syncs[client_id]
    
    def _handle_file_change(self, file_change):
        """Handle file change event"""
        response = code_index_pb2.SyncResponse()
        
        try:
            if file_change.type == code_index_pb2.FileChange.DELETED:
                self.dispatcher.remove_file(file_change.file_path)
            else:
                self.dispatcher.index_file(
                    file_path=file_change.file_path,
                    content=file_change.content.decode('utf-8')
                )
            
            response.ack.file_path = file_change.file_path
            response.ack.success = True
            
        except Exception as e:
            response.error.file_path = file_change.file_path
            response.error.error = str(e)
        
        return response
    
    def _handle_sync_status(self, status):
        """Handle sync status request"""
        response = code_index_pb2.SyncResponse()
        # Could trigger a full sync check here
        response.progress.files_processed = len(status.indexed_files)
        response.progress.total_files = len(status.indexed_files)
        response.progress.percentage = 100.0
        return response

async def serve(port: int = 50051):
    """Start the gRPC server"""
    # Initialize components
    dispatcher = Dispatcher()
    
    # Create server
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
        ]
    )
    
    # Add servicer
    code_index_pb2_grpc.add_CodeIndexServicer_to_server(
        CodeIndexServicer(dispatcher), server
    )
    
    # Enable reflection for debugging
    from grpc_reflection.v1alpha import reflection
    SERVICE_NAMES = (
        code_index_pb2.DESCRIPTOR.services_by_name['CodeIndexService'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    
    # Start server
    await server.add_insecure_port(f'[::]:{port}')
    await server.start()
    
    logging.info(f"gRPC server started on port {port}")
    
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
```

### Client Implementation

```python
# mcp_server/grpc_client.py
import grpc
import asyncio
from typing import List, AsyncIterator
import logging

from generated import code_index_pb2
from generated import code_index_pb2_grpc

class CodeIndexClient:
    def __init__(self, server_address: str = 'localhost:50051'):
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Establish gRPC connection"""
        self.channel = grpc.aio.insecure_channel(
            self.server_address,
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ]
        )
        self.stub = code_index_pb2_grpc.CodeIndexServiceStub(self.channel)
    
    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            await self.channel.close()
    
    async def index_file(self, file_path: str, content: str, 
                        language: str = None) -> dict:
        """Index a single file"""
        request = code_index_pb2.IndexFileRequest(
            file_path=file_path,
            content=content,
            language=language or self._detect_language(file_path)
        )
        
        response = await self.stub.IndexFile(request)
        
        if not response.success:
            raise Exception(f"Failed to index file: {response.error}")
        
        return {
            'file_id': response.file_id,
            'symbols_count': response.symbols_count,
            'indexed_at': response.indexed_at.ToDatetime()
        }
    
    async def search_symbols(self, query: str, languages: List[str] = None,
                           limit: int = 20, semantic: bool = False) -> List[dict]:
        """Search symbols with streaming results"""
        request = code_index_pb2.SearchRequest(
            query=query,
            languages=languages or [],
            limit=limit,
            semantic=semantic
        )
        
        results = []
        async for result in self.stub.SearchSymbols(request):
            results.append({
                'file_path': result.file_path,
                'symbol': result.symbol,
                'kind': result.kind,
                'line': result.line,
                'snippet': result.snippet,
                'score': result.score
            })
        
        return results
    
    async def bulk_index(self, files: List[tuple[str, str, str]]) -> dict:
        """Bulk index multiple files"""
        async def request_generator():
            for file_path, content, language in files:
                yield code_index_pb2.IndexFileRequest(
                    file_path=file_path,
                    content=content,
                    language=language
                )
        
        response = await self.stub.BulkIndex(request_generator())
        
        return {
            'total': response.total_files,
            'successful': response.successful,
            'failed': response.failed,
            'errors': list(response.errors)
        }
    
    async def sync_with_server(self, file_watcher):
        """Sync local changes with server"""
        async def request_generator():
            # Send initial status
            status_request = code_index_pb2.SyncRequest()
            status_request.status.client_id = "client-1"
            yield status_request
            
            # Watch for file changes
            async for event in file_watcher.watch():
                request = code_index_pb2.SyncRequest()
                
                if event['type'] == 'created':
                    request.file_change.type = code_index_pb2.FileChange.CREATED
                elif event['type'] == 'modified':
                    request.file_change.type = code_index_pb2.FileChange.MODIFIED
                elif event['type'] == 'deleted':
                    request.file_change.type = code_index_pb2.FileChange.DELETED
                
                request.file_change.file_path = event['path']
                if event['type'] != 'deleted':
                    with open(event['path'], 'rb') as f:
                        request.file_change.content = f.read()
                
                yield request
        
        try:
            async for response in self.stub.SyncIndex(request_generator()):
                if response.HasField('ack'):
                    self.logger.info(f"Synced: {response.ack.file_path}")
                elif response.HasField('error'):
                    self.logger.error(f"Sync error: {response.error.error}")
                elif response.HasField('progress'):
                    self.logger.info(f"Sync progress: {response.progress.percentage}%")
        except grpc.RpcError as e:
            self.logger.error(f"gRPC error: {e}")
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.dart': 'dart',
            '.html': 'html',
            '.css': 'css'
        }
        
        import os
        ext = os.path.splitext(file_path)[1]
        return ext_to_lang.get(ext, 'unknown')
```

## Cloud Sync Patterns

### 1. Distributed Index Synchronization

```python
# mcp_server/cloud_sync.py
import asyncio
from typing import Dict, Set
import hashlib
import json

class CloudSyncManager:
    def __init__(self, grpc_client):
        self.client = grpc_client
        self.local_state: Dict[str, str] = {}  # file_path -> hash
        self.remote_state: Dict[str, str] = {}
        self.sync_queue = asyncio.Queue()
    
    async def compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file content"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    async def sync_state(self):
        """Synchronize local and remote state"""
        # Get local state
        local_files = await self.scan_local_files()
        
        # Get remote state
        remote_files = await self.client.get_remote_state()
        
        # Compute differences
        to_upload = set(local_files.keys()) - set(remote_files.keys())
        to_download = set(remote_files.keys()) - set(local_files.keys())
        to_check = set(local_files.keys()) & set(remote_files.keys())
        
        # Check for modifications
        for file_path in to_check:
            if local_files[file_path] != remote_files[file_path]:
                to_upload.add(file_path)
        
        # Queue sync operations
        for file_path in to_upload:
            await self.sync_queue.put(('upload', file_path))
        
        for file_path in to_download:
            await self.sync_queue.put(('download', file_path))
    
    async def sync_worker(self):
        """Process sync queue"""
        while True:
            operation, file_path = await self.sync_queue.get()
            
            try:
                if operation == 'upload':
                    await self.upload_file(file_path)
                elif operation == 'download':
                    await self.download_file(file_path)
            except Exception as e:
                logging.error(f"Sync error for {file_path}: {e}")
                # Retry logic
                await asyncio.sleep(5)
                await self.sync_queue.put((operation, file_path))
```

### 2. Streaming Large Codebases

```python
# mcp_server/streaming.py
import os
import asyncio
from pathlib import Path
from typing import AsyncIterator

class LargeCodebaseStreamer:
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
    
    async def stream_codebase(self, root_path: str) -> AsyncIterator[dict]:
        """Stream entire codebase in chunks"""
        for file_path in Path(root_path).rglob('*'):
            if file_path.is_file() and self._should_index(file_path):
                async for chunk in self._stream_file(file_path):
                    yield chunk
    
    async def _stream_file(self, file_path: Path) -> AsyncIterator[dict]:
        """Stream single file in chunks"""
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            chunk_num = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                yield {
                    'file_path': str(file_path),
                    'chunk_num': chunk_num,
                    'total_chunks': (file_size // self.chunk_size) + 1,
                    'content': chunk,
                    'is_last': len(chunk) < self.chunk_size
                }
                
                chunk_num += 1
                # Yield control to prevent blocking
                await asyncio.sleep(0)
    
    def _should_index(self, file_path: Path) -> bool:
        """Check if file should be indexed"""
        ignored_dirs = {'.git', 'node_modules', '__pycache__', '.venv'}
        ignored_extensions = {'.pyc', '.pyo', '.so', '.dylib'}
        
        # Check if in ignored directory
        for parent in file_path.parents:
            if parent.name in ignored_dirs:
                return False
        
        # Check extension
        return file_path.suffix not in ignored_extensions

# Integration with gRPC streaming
class StreamingIndexer:
    def __init__(self, grpc_client):
        self.client = grpc_client
        self.streamer = LargeCodebaseStreamer()
    
    async def index_large_codebase(self, root_path: str):
        """Index large codebase using streaming"""
        files_buffer = []
        
        async for chunk in self.streamer.stream_codebase(root_path):
            # Reconstruct files from chunks
            file_path = chunk['file_path']
            
            if file_path not in files_buffer:
                files_buffer[file_path] = {
                    'chunks': {},
                    'total_chunks': chunk['total_chunks']
                }
            
            files_buffer[file_path]['chunks'][chunk['chunk_num']] = chunk['content']
            
            # When file is complete, index it
            if len(files_buffer[file_path]['chunks']) == chunk['total_chunks']:
                content = b''.join(
                    files_buffer[file_path]['chunks'][i]
                    for i in sorted(files_buffer[file_path]['chunks'].keys())
                )
                
                await self.client.index_file(
                    file_path=file_path,
                    content=content.decode('utf-8', errors='ignore')
                )
                
                del files_buffer[file_path]
```

## Performance Monitoring and Optimization

### 1. gRPC Interceptors for Metrics

```python
# mcp_server/grpc_metrics.py
import time
import grpc
from prometheus_client import Counter, Histogram

# Metrics
grpc_requests_total = Counter(
    'grpc_requests_total',
    'Total gRPC requests',
    ['method', 'status']
)

grpc_request_duration = Histogram(
    'grpc_request_duration_seconds',
    'gRPC request duration',
    ['method']
)

class MetricsInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        start_time = time.time()
        
        def wrapper(request, context):
            try:
                response = continuation(handler_call_details)(request, context)
                grpc_requests_total.labels(
                    method=method,
                    status='success'
                ).inc()
                return response
            except Exception as e:
                grpc_requests_total.labels(
                    method=method,
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                grpc_request_duration.labels(method=method).observe(duration)
        
        return wrapper

# Client-side interceptor
class ClientMetricsInterceptor(grpc.UnaryUnaryClientInterceptor,
                              grpc.StreamUnaryClientInterceptor):
    def intercept_unary_unary(self, continuation, client_call_details, request):
        start_time = time.time()
        
        response = continuation(client_call_details, request)
        
        duration = time.time() - start_time
        grpc_request_duration.labels(
            method=client_call_details.method
        ).observe(duration)
        
        return response
```

### 2. Connection Pooling

```python
# mcp_server/connection_pool.py
import asyncio
import grpc
from typing import Dict, List
import random

class GrpcConnectionPool:
    def __init__(self, servers: List[str], pool_size: int = 5):
        self.servers = servers
        self.pool_size = pool_size
        self.connections: Dict[str, List[grpc.aio.Channel]] = {}
        self.lock = asyncio.Lock()
    
    async def get_channel(self, server: str = None) -> grpc.aio.Channel:
        """Get a channel from the pool"""
        if server is None:
            server = random.choice(self.servers)
        
        async with self.lock:
            if server not in self.connections:
                self.connections[server] = []
            
            # Create new connection if needed
            if len(self.connections[server]) < self.pool_size:
                channel = grpc.aio.insecure_channel(
                    server,
                    options=[
                        ('grpc.keepalive_time_ms', 10000),
                        ('grpc.keepalive_timeout_ms', 5000),
                        ('grpc.http2.max_pings_without_data', 0),
                    ]
                )
                self.connections[server].append(channel)
            
            # Round-robin selection
            return self.connections[server][
                len(self.connections[server]) % self.pool_size
            ]
    
    async def close_all(self):
        """Close all connections"""
        async with self.lock:
            for channels in self.connections.values():
                for channel in channels:
                    await channel.close()
            self.connections.clear()
```

### 3. Load Balancing

```python
# mcp_server/load_balancer.py
import grpc
from typing import List, Dict
import asyncio
import random

class LoadBalancedClient:
    def __init__(self, servers: List[str]):
        self.servers = servers
        self.health_status: Dict[str, bool] = {s: True for s in servers}
        self.connection_pool = GrpcConnectionPool(servers)
    
    async def health_check(self):
        """Periodic health checks"""
        while True:
            for server in self.servers:
                try:
                    channel = await self.connection_pool.get_channel(server)
                    stub = code_index_pb2_grpc.CodeIndexServiceStub(channel)
                    
                    # Simple health check - could be a dedicated RPC
                    await asyncio.wait_for(
                        stub.IndexFile(code_index_pb2.IndexFileRequest()),
                        timeout=5.0
                    )
                    self.health_status[server] = True
                except:
                    self.health_status[server] = False
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    def select_server(self, strategy: str = 'round_robin') -> str:
        """Select server based on strategy"""
        healthy_servers = [s for s, healthy in self.health_status.items() if healthy]
        
        if not healthy_servers:
            raise Exception("No healthy servers available")
        
        if strategy == 'round_robin':
            return healthy_servers[hash(asyncio.current_task()) % len(healthy_servers)]
        elif strategy == 'random':
            return random.choice(healthy_servers)
        elif strategy == 'least_connections':
            # Implement based on connection count
            pass
        
        return healthy_servers[0]
```

## Best Practices

### 1. Error Handling

```python
# Comprehensive error handling
class RobustGrpcClient:
    def __init__(self, server_address: str):
        self.server_address = server_address
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def call_with_retry(self, method, request):
        """Call gRPC method with exponential backoff retry"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await method(request)
            except grpc.RpcError as e:
                last_error = e
                
                if e.code() in [grpc.StatusCode.UNAVAILABLE,
                              grpc.StatusCode.DEADLINE_EXCEEDED]:
                    # Retryable errors
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    # Non-retryable errors
                    raise
        
        raise last_error
```

### 2. Security

```python
# TLS/SSL configuration
def create_secure_channel(server_address: str, 
                         root_cert_path: str,
                         private_key_path: str = None,
                         cert_chain_path: str = None):
    """Create secure gRPC channel with TLS"""
    
    # Read certificates
    with open(root_cert_path, 'rb') as f:
        root_cert = f.read()
    
    credentials = grpc.ssl_channel_credentials(root_cert)
    
    # Mutual TLS if client certs provided
    if private_key_path and cert_chain_path:
        with open(private_key_path, 'rb') as f:
            private_key = f.read()
        with open(cert_chain_path, 'rb') as f:
            cert_chain = f.read()
        
        credentials = grpc.ssl_channel_credentials(
            root_certificates=root_cert,
            private_key=private_key,
            certificate_chain=cert_chain
        )
    
    return grpc.aio.secure_channel(server_address, credentials)
```

### 3. Message Size Limits

```python
# Handle large messages
server_options = [
    ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
    ('grpc.max_receive_message_length', 100 * 1024 * 1024),
    ('grpc.max_metadata_size', 16 * 1024),  # 16KB
]

# Chunking large messages
async def send_large_file(stub, file_path: str, chunk_size: int = 1024 * 1024):
    """Send large file in chunks"""
    async def chunk_generator():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                yield code_index_pb2.FileChunk(
                    file_path=file_path,
                    content=chunk,
                    is_last=len(chunk) < chunk_size
                )
    
    return await stub.UploadFile(chunk_generator())
```

### 4. Monitoring Integration

```python
# Complete monitoring setup
from prometheus_client import Counter, Histogram, Gauge
import grpc

# Metrics
grpc_active_connections = Gauge(
    'grpc_active_connections',
    'Number of active gRPC connections',
    ['server']
)

grpc_message_size = Histogram(
    'grpc_message_size_bytes',
    'Size of gRPC messages',
    ['method', 'direction'],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000)
)

class MonitoringInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        grpc_active_connections.labels(server='main').inc()
        
        def wrapper(request_or_iterator, context):
            try:
                # Monitor request size
                if hasattr(request_or_iterator, 'SerializeToString'):
                    size = len(request_or_iterator.SerializeToString())
                    grpc_message_size.labels(
                        method=handler_call_details.method,
                        direction='request'
                    ).observe(size)
                
                response = continuation(handler_call_details)(
                    request_or_iterator, context
                )
                
                # Monitor response size
                if hasattr(response, 'SerializeToString'):
                    size = len(response.SerializeToString())
                    grpc_message_size.labels(
                        method=handler_call_details.method,
                        direction='response'
                    ).observe(size)
                
                return response
                
            finally:
                grpc_active_connections.labels(server='main').dec()
        
        return wrapper
```

## Complete Integration Example

```python
# mcp_server/grpc_integration.py
import asyncio
import logging
from pathlib import Path

from .grpc_server import CodeIndexServicer, serve
from .grpc_client import CodeIndexClient
from .cloud_sync import CloudSyncManager
from .streaming import StreamingIndexer

async def main():
    """Complete gRPC integration for Code Index MCP"""
    
    # Start server
    server_task = asyncio.create_task(serve(port=50051))
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    # Create client
    client = CodeIndexClient('localhost:50051')
    await client.connect()
    
    # Index local codebase
    streamer = StreamingIndexer(client)
    await streamer.index_large_codebase('.')
    
    # Set up cloud sync
    sync_manager = CloudSyncManager(client)
    sync_task = asyncio.create_task(sync_manager.sync_worker())
    
    # Start file watching and syncing
    from .watcher import FileWatcher
    watcher = FileWatcher()
    await client.sync_with_server(watcher)
    
    # Keep running
    await asyncio.gather(server_task, sync_task)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

This comprehensive gRPC implementation provides a complete solution for distributed code indexing with cloud synchronization, streaming support for large codebases, and robust error handling.