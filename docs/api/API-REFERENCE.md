# Code-Index-MCP API Reference

## Overview

Code-Index-MCP provides a comprehensive FastAPI-based REST API for code indexing, searching, and management across multiple programming languages. The API features authentication, monitoring, caching, and a plugin-based architecture for language-specific functionality.

## Base URL

```
# Development
http://localhost:8000

# Production
https://api.yourdomain.com
```

## Authentication

The API uses JWT (JSON Web Token) based authentication with role-based access control.

### Authentication Flow

1. **Login** with username/password to get access and refresh tokens
2. **Include access token** in Authorization header for protected endpoints
3. **Refresh tokens** when access token expires

### Authentication Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

## API Endpoints

### Authentication Endpoints

#### POST /auth/login

Authenticate user and receive JWT tokens.

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "user-id",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials",
  "error_code": "INVALID_CREDENTIALS"
}
```

#### POST /auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /auth/logout

Invalidate current session tokens.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

#### GET /auth/me

Get current user information.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "id": "user-id",
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-01-01T12:00:00Z"
}
```

### User Management Endpoints

#### POST /users

Create a new user (admin only).

**Headers:** `Authorization: Bearer <admin_access_token>`

**Request Body:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "secure-password",
  "role": "user"
}
```

**Response (201 Created):**
```json
{
  "id": "user-id",
  "username": "newuser",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### GET /users

List all users (admin only).

**Headers:** `Authorization: Bearer <admin_access_token>`

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `size` (integer, optional): Page size (default: 50)
- `role` (string, optional): Filter by role

**Response (200 OK):**
```json
{
  "users": [
    {
      "id": "user-id",
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z",
      "last_login": "2025-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

### Code Search and Symbol Lookup

#### GET /symbol

Look up a symbol definition across all indexed files.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `symbol` (string, required): The symbol name to look up
- `language` (string, optional): Filter by programming language
- `file_path` (string, optional): Filter by file path pattern

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.yourdomain.com/symbol?symbol=MyClass&language=python"
```

**Response (200 OK):**
```json
{
  "symbol": "MyClass",
  "definitions": [
    {
      "kind": "class",
      "language": "python",
      "signature": "class MyClass(BaseClass):",
      "documentation": "A sample class for demonstration",
      "file_path": "/path/to/file.py",
      "line_start": 42,
      "line_end": 58,
      "column_start": 0,
      "column_end": 15,
      "context": {
        "module": "mymodule",
        "namespace": "mypackage.mymodule"
      }
    }
  ],
  "total_matches": 1
}
```

**No Results (200 OK):**
```json
{
  "symbol": "UnknownSymbol",
  "definitions": [],
  "total_matches": 0
}
```

#### GET /search

Search for code patterns, symbols, or text across indexed files.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `q` (string, required): Search query
- `language` (string, optional): Filter by programming language
- `file_path` (string, optional): Filter by file path pattern
- `symbol_type` (string, optional): Filter by symbol type (function, class, variable, etc.)
- `limit` (integer, optional): Maximum results (default: 20, max: 100)
- `offset` (integer, optional): Result offset for pagination (default: 0)

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.yourdomain.com/search?q=user+authentication&language=python&limit=10"
```

**Response (200 OK):**
```json
{
  "query": "user authentication",
  "results": [
    {
      "file_path": "/src/auth.py",
      "line_number": 25,
      "content": "def authenticate_user(username: str, password: str) -> bool:",
      "symbol": {
        "name": "authenticate_user",
        "kind": "function",
        "signature": "def authenticate_user(username: str, password: str) -> bool"
      },
      "context": {
        "before": "# User authentication module",
        "after": "    \"\"\"Authenticate user with username and password.\"\"\""
      },
      "score": 0.95
    }
  ],
  "total_results": 1,
  "search_time_ms": 45,
  "limit": 10,
  "offset": 0
}
```

#### GET /search/semantic

Semantic code search using AI embeddings (if enabled).

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `q` (string, required): Natural language search query
- `language` (string, optional): Filter by programming language
- `limit` (integer, optional): Maximum results (default: 10, max: 50)

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "https://api.yourdomain.com/search/semantic?q=find functions that validate email addresses"
```

**Response (200 OK):**
```json
{
  "query": "find functions that validate email addresses",
  "results": [
    {
      "file_path": "/src/validators.py",
      "symbol": {
        "name": "validate_email",
        "kind": "function",
        "signature": "def validate_email(email: str) -> bool",
        "documentation": "Validates email address format using regex"
      },
      "similarity_score": 0.92,
      "context": {
        "snippet": "def validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return re.match(pattern, email) is not None"
      }
    }
  ],
  "total_results": 1,
  "search_time_ms": 150
}
```

### Plugin Management

#### GET /plugins

List all available language plugins.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "plugins": [
    {
      "name": "python",
      "language": "Python",
      "version": "1.0.0",
      "status": "active",
      "supported_extensions": [".py", ".pyw"],
      "features": ["syntax_analysis", "symbol_extraction", "documentation_parsing"],
      "files_indexed": 1542,
      "last_updated": "2025-01-01T12:00:00Z"
    },
    {
      "name": "javascript",
      "language": "JavaScript/TypeScript",
      "version": "1.0.0",
      "status": "active",
      "supported_extensions": [".js", ".jsx", ".ts", ".tsx"],
      "features": ["syntax_analysis", "symbol_extraction"],
      "files_indexed": 856,
      "last_updated": "2025-01-01T11:30:00Z"
    }
  ],
  "total_plugins": 6,
  "active_plugins": 6
}
```

#### GET /plugins/{plugin_name}

Get detailed information about a specific plugin.

**Headers:** `Authorization: Bearer <access_token>`

**Path Parameters:**
- `plugin_name` (string): Name of the plugin (e.g., "python", "javascript")

**Response (200 OK):**
```json
{
  "name": "python",
  "language": "Python",
  "version": "1.0.0",
  "status": "active",
  "supported_extensions": [".py", ".pyw"],
  "features": ["syntax_analysis", "symbol_extraction", "documentation_parsing"],
  "configuration": {
    "include_private_symbols": true,
    "parse_docstrings": true,
    "follow_imports": false
  },
  "statistics": {
    "files_indexed": 1542,
    "symbols_extracted": 15420,
    "last_indexing_time": "2025-01-01T12:00:00Z",
    "average_processing_time_ms": 45
  },
  "health": {
    "status": "healthy",
    "last_check": "2025-01-01T12:30:00Z",
    "error_count": 0
  }
}
```

### Indexing and File Management

#### POST /reindex

Trigger re-indexing of the entire codebase or specific paths.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "paths": ["/src", "/lib"],  // Optional: specific paths to reindex
  "force": false,             // Optional: force reindex even if files unchanged
  "background": true          // Optional: run in background
}
```

**Response (202 Accepted):**
```json
{
  "message": "Indexing started",
  "job_id": "reindex-job-12345",
  "status": "running",
  "estimated_duration_seconds": 300
}
```

#### GET /reindex/status/{job_id}

Get status of a reindexing job.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "job_id": "reindex-job-12345",
  "status": "completed",
  "progress": {
    "files_processed": 2500,
    "files_total": 2500,
    "percentage": 100.0
  },
  "started_at": "2025-01-01T12:00:00Z",
  "completed_at": "2025-01-01T12:05:00Z",
  "duration_seconds": 300,
  "results": {
    "files_added": 50,
    "files_updated": 200,
    "files_removed": 10,
    "symbols_extracted": 5420,
    "errors": []
  }
}
```

#### GET /files

List indexed files with optional filtering.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
- `language` (string, optional): Filter by programming language
- `path` (string, optional): Filter by file path pattern
- `modified_since` (string, optional): ISO datetime filter
- `limit` (integer, optional): Maximum results (default: 50, max: 500)
- `offset` (integer, optional): Result offset for pagination

**Response (200 OK):**
```json
{
  "files": [
    {
      "path": "/src/auth.py",
      "language": "python",
      "size_bytes": 5420,
      "lines_of_code": 180,
      "symbol_count": 12,
      "last_modified": "2025-01-01T10:30:00Z",
      "last_indexed": "2025-01-01T12:00:00Z",
      "checksum": "sha256:abc123..."
    }
  ],
  "total_files": 2500,
  "limit": 50,
  "offset": 0
}
```

### System Status and Health

#### GET /health

Get system health status (no authentication required).

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:30:00Z",
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "connections_active": 8,
      "connections_max": 20
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2,
      "memory_usage_mb": 128,
      "hit_rate": 0.85
    },
    "plugins": {
      "status": "healthy",
      "active_count": 6,
      "total_count": 6
    },
    "file_watcher": {
      "status": "healthy",
      "files_watched": 2500,
      "events_processed": 150
    }
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_total": 15420,
    "requests_per_second": 12.5,
    "response_time_avg_ms": 85
  }
}
```

#### GET /health/detailed

Get detailed health information (requires authentication).

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T12:30:00Z",
  "detailed_checks": {
    "database_connectivity": {
      "status": "healthy",
      "details": "PostgreSQL connection pool healthy",
      "response_time_ms": 5
    },
    "redis_connectivity": {
      "status": "healthy", 
      "details": "Redis cluster responding normally",
      "response_time_ms": 2
    },
    "disk_space": {
      "status": "healthy",
      "details": "Disk usage: 45% (2.1GB / 4.7GB)",
      "usage_percentage": 45
    },
    "memory_usage": {
      "status": "healthy",
      "details": "Memory usage: 1.2GB / 2.0GB",
      "usage_percentage": 60
    },
    "plugin_health": {
      "status": "healthy",
      "details": "All 6 plugins responding normally",
      "plugin_statuses": {
        "python": "healthy",
        "javascript": "healthy",
        "c": "healthy",
        "cpp": "healthy",
        "dart": "healthy", 
        "html_css": "healthy"
      }
    }
  }
}
```

#### GET /status

Get comprehensive system status and statistics.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "system": {
    "version": "1.0.0",
    "environment": "production",
    "uptime_seconds": 86400,
    "started_at": "2025-01-01T00:00:00Z"
  },
  "indexing": {
    "total_files": 2500,
    "total_symbols": 25420,
    "languages": {
      "python": {"files": 1542, "symbols": 15420},
      "javascript": {"files": 856, "symbols": 8420},
      "c": {"files": 102, "symbols": 1580}
    },
    "last_full_index": "2025-01-01T06:00:00Z",
    "last_incremental_index": "2025-01-01T12:00:00Z"
  },
  "performance": {
    "avg_symbol_lookup_ms": 12,
    "avg_search_time_ms": 85,
    "cache_hit_rate": 0.85,
    "requests_per_second": 12.5
  },
  "storage": {
    "database_size_mb": 145,
    "cache_size_mb": 128,
    "index_size_mb": 89
  }
}
```

### Metrics and Monitoring

#### GET /metrics

Prometheus-compatible metrics endpoint (no authentication required).

**Response (200 OK):**
```text
# HELP mcp_requests_total Total number of requests
# TYPE mcp_requests_total counter
mcp_requests_total{method="GET",endpoint="/symbol"} 1542.0

# HELP mcp_request_duration_seconds Request duration in seconds
# TYPE mcp_request_duration_seconds histogram
mcp_request_duration_seconds_bucket{le="0.1"} 1200.0
mcp_request_duration_seconds_bucket{le="0.5"} 1500.0
mcp_request_duration_seconds_bucket{le="1.0"} 1540.0
mcp_request_duration_seconds_bucket{le="+Inf"} 1542.0

# HELP mcp_active_users Current number of active users
# TYPE mcp_active_users gauge
mcp_active_users 25.0

# HELP mcp_indexed_files_total Total number of indexed files
# TYPE mcp_indexed_files_total gauge
mcp_indexed_files_total{language="python"} 1542.0
mcp_indexed_files_total{language="javascript"} 856.0
```

#### GET /metrics/business

Business metrics and KPIs (requires authentication).

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "timestamp": "2025-01-01T12:30:00Z",
  "period": "24h",
  "metrics": {
    "searches_performed": 1542,
    "symbols_looked_up": 856,
    "unique_users": 25,
    "popular_languages": [
      {"language": "python", "usage_percentage": 65.2},
      {"language": "javascript", "usage_percentage": 28.1},
      {"language": "c", "usage_percentage": 6.7}
    ],
    "top_search_terms": [
      {"term": "authenticate", "count": 45},
      {"term": "validate", "count": 32},
      {"term": "parse", "count": 28}
    ],
    "performance_slo": {
      "symbol_lookup_p95_ms": 45,
      "search_p95_ms": 180,
      "availability_percentage": 99.9
    }
  }
}
```

### Cache Management

#### DELETE /cache

Clear application cache (admin only).

**Headers:** `Authorization: Bearer <admin_access_token>`

**Query Parameters:**
- `type` (string, optional): Cache type to clear ("search", "symbols", "all")

**Response (200 OK):**
```json
{
  "message": "Cache cleared successfully",
  "cache_type": "all",
  "items_cleared": 1542
}
```

#### GET /cache/stats

Get cache statistics.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200 OK):**
```json
{
  "cache_stats": {
    "total_size_mb": 128,
    "total_items": 5420,
    "hit_rate": 0.85,
    "miss_rate": 0.15,
    "evictions": 42
  },
  "cache_types": {
    "search_results": {
      "size_mb": 64,
      "items": 2500,
      "hit_rate": 0.82,
      "ttl_seconds": 600
    },
    "symbol_lookups": {
      "size_mb": 48,
      "items": 2420,
      "hit_rate": 0.89,
      "ttl_seconds": 1800
    },
    "file_metadata": {
      "size_mb": 16,
      "items": 500,
      "hit_rate": 0.95,
      "ttl_seconds": 3600
    }
  }
}
```

## Error Responses

### Standard Error Format

All API errors follow this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-01-01T12:30:00Z",
  "request_id": "req-12345",
  "errors": [  // Optional: for validation errors
    {
      "field": "username",
      "message": "Username is required",
      "code": "REQUIRED"
    }
  ]
}
```

### Common Error Codes

- **400 Bad Request**: Invalid request parameters
  ```json
  {
    "detail": "Invalid search query parameters",
    "error_code": "INVALID_PARAMETERS"
  }
  ```

- **401 Unauthorized**: Missing or invalid authentication
  ```json
  {
    "detail": "Access token is required",
    "error_code": "MISSING_TOKEN"
  }
  ```

- **403 Forbidden**: Insufficient permissions
  ```json
  {
    "detail": "Admin privileges required for this operation",
    "error_code": "INSUFFICIENT_PERMISSIONS"
  }
  ```

- **404 Not Found**: Resource not found
  ```json
  {
    "detail": "Plugin 'unknown' not found",
    "error_code": "PLUGIN_NOT_FOUND"
  }
  ```

- **429 Too Many Requests**: Rate limit exceeded
  ```json
  {
    "detail": "Rate limit exceeded. Try again in 60 seconds",
    "error_code": "RATE_LIMIT_EXCEEDED",
    "retry_after": 60
  }
  ```

- **500 Internal Server Error**: Server error
  ```json
  {
    "detail": "An internal error occurred while processing the request",
    "error_code": "INTERNAL_ERROR"
  }
  ```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **General endpoints**: 100 requests per hour per user
- **Search endpoints**: 60 requests per hour per user
- **Authentication endpoints**: 10 requests per minute per IP

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints support pagination using `limit` and `offset` parameters:

```bash
# Get second page of 50 results
GET /files?limit=50&offset=50
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "total": 2500,
    "limit": 50,
    "offset": 50,
    "has_next": true,
    "has_prev": true
  }
}
```

## WebSocket Support

Real-time updates are available via WebSocket connections:

```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://api.yourdomain.com/ws');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your-access-token'
}));

// Subscribe to indexing updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'indexing'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

## SDK and Client Libraries

Official SDKs are available for:

- **Python**: `pip install mcp-server-client`
- **JavaScript/TypeScript**: `npm install @mcp/client`
- **Go**: `go get github.com/mcp-server/go-client`

Example Python usage:

```python
from mcp_client import MCPClient

# Initialize client
client = MCPClient(base_url="https://api.yourdomain.com")

# Authenticate
token = client.auth.login("username", "password")

# Search for symbols
results = client.search.symbols("authenticate")

# Get symbol definition
definition = client.symbols.get("MyClass")
```

## OpenAPI Specification

Interactive API documentation is available at:

- **Swagger UI**: `https://api.yourdomain.com/docs`
- **ReDoc**: `https://api.yourdomain.com/redoc`
- **OpenAPI JSON**: `https://api.yourdomain.com/openapi.json`