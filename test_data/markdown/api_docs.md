# Code Index API Documentation

## Overview

The Code Index API provides powerful search and indexing capabilities for source code repositories. This RESTful API enables developers to index, search, and analyze codebases efficiently.

**Base URL:** `https://api.codeindex.dev/v1`  
**Authentication:** Bearer token required for all endpoints

## Authentication

All API requests must include an authentication token in the header:

```http
Authorization: Bearer YOUR_API_TOKEN
```

### Obtaining an API Token

```bash
curl -X POST https://api.codeindex.dev/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Core Endpoints

### 1. Index Management

#### Create Index

`POST /indices`

Creates a new code index for a repository.

**Request Body:**
```json
{
  "name": "my-project-index",
  "repository_url": "https://github.com/user/repo",
  "branch": "main",
  "languages": ["python", "javascript", "java"],
  "options": {
    "include_tests": true,
    "semantic_analysis": true,
    "max_file_size": 1048576
  }
}
```

**Response:**
```json
{
  "index_id": "idx_1234567890",
  "status": "processing",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z"
}
```

#### Get Index Status

`GET /indices/{index_id}`

Retrieves the current status of an index.

**Parameters:**
- `index_id` (path) - The unique identifier of the index

**Response:**
```json
{
  "index_id": "idx_1234567890",
  "name": "my-project-index",
  "status": "ready",
  "statistics": {
    "total_files": 1523,
    "indexed_files": 1523,
    "total_symbols": 45678,
    "last_updated": "2024-01-15T10:35:00Z"
  }
}
```

### 2. Search Operations

#### Code Search

`POST /search/code`

Search for code patterns across indexed repositories.

**Request Body:**
```json
{
  "query": "def process_data",
  "indices": ["idx_1234567890"],
  "filters": {
    "languages": ["python"],
    "file_patterns": ["*.py", "!*test*.py"],
    "max_results": 50
  },
  "options": {
    "context_lines": 3,
    "highlight": true,
    "semantic_search": false
  }
}
```

**Response:**
```json
{
  "total_results": 12,
  "results": [
    {
      "file_path": "src/data/processor.py",
      "repository": "user/repo",
      "matches": [
        {
          "line_number": 45,
          "content": "def process_data(input_file, output_format='json'):",
          "context": {
            "before": [
              "    return cleaned_data",
              "",
              "@timing_decorator"
            ],
            "after": [
              "    \"\"\"Process raw data and convert to specified format.\"\"\"",
              "    validator = DataValidator()",
              "    if not validator.validate(input_file):"
            ]
          }
        }
      ],
      "score": 0.98
    }
  ]
}
```

#### Symbol Search

`GET /search/symbols`

Search for function, class, and variable definitions.

**Query Parameters:**
- `q` - Search query (required)
- `type` - Symbol type: `function`, `class`, `variable`, `all` (default: `all`)
- `index_id` - Comma-separated list of index IDs
- `limit` - Maximum results (default: 20, max: 100)

**Example:**
```
GET /search/symbols?q=UserAuth&type=class&index_id=idx_1234567890&limit=10
```

**Response:**
```json
{
  "symbols": [
    {
      "name": "UserAuthManager",
      "type": "class",
      "file_path": "src/auth/manager.py",
      "line_number": 23,
      "documentation": "Manages user authentication and session handling.",
      "signature": "class UserAuthManager(BaseAuthManager):",
      "references": 45
    }
  ]
}
```

### 3. Analysis Endpoints

#### File Dependencies

`GET /analysis/dependencies/{file_path}`

Analyzes import dependencies for a specific file.

**Parameters:**
- `file_path` (path) - URL-encoded file path
- `index_id` (query) - Index identifier

**Response:**
```json
{
  "file": "src/main.py",
  "imports": [
    {
      "module": "datetime",
      "type": "standard_library",
      "symbols": ["datetime", "timedelta"]
    },
    {
      "module": "src.utils.helpers",
      "type": "local",
      "symbols": ["format_output", "validate_input"]
    }
  ],
  "imported_by": [
    "tests/test_main.py",
    "src/cli.py"
  ]
}
```

#### Code Metrics

`GET /analysis/metrics`

Get code quality metrics for indexed repositories.

**Query Parameters:**
- `index_id` - Index identifier
- `path` - Optional path to analyze specific directory

**Response:**
```json
{
  "metrics": {
    "complexity": {
      "average": 3.2,
      "max": 15,
      "distribution": {
        "low": 75,
        "medium": 20,
        "high": 5
      }
    },
    "maintainability": {
      "index": 82.5,
      "technical_debt": "3d 4h"
    },
    "test_coverage": {
      "line_coverage": 87.3,
      "branch_coverage": 73.2
    }
  }
}
```

## Semantic Search

### Semantic Code Search

`POST /search/semantic`

Search using natural language queries powered by AI embeddings.

**Request Body:**
```json
{
  "query": "function that validates email addresses",
  "indices": ["idx_1234567890"],
  "options": {
    "similarity_threshold": 0.7,
    "max_results": 20,
    "include_context": true
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "file_path": "src/validators/email.py",
      "function_name": "validate_email_address",
      "similarity_score": 0.92,
      "snippet": "def validate_email_address(email: str) -> bool:\n    \"\"\"Validate email format using regex pattern.\"\"\"\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return re.match(pattern, email) is not None",
      "explanation": "This function validates email addresses using a regular expression pattern that checks for standard email format."
    }
  ]
}
```

## Webhooks

### Configure Webhook

`POST /webhooks`

Set up webhooks for repository events.

**Request Body:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["index.completed", "index.failed", "repository.updated"],
  "index_id": "idx_1234567890",
  "secret": "your-webhook-secret"
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default:** 1000 requests per hour
- **Search endpoints:** 100 requests per minute
- **Index creation:** 10 per hour

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1673784000
```

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:

```json
{
  "error": {
    "code": "INDEX_NOT_FOUND",
    "message": "The specified index does not exist",
    "details": {
      "index_id": "idx_invalid",
      "suggestion": "Check your index ID or create a new index"
    }
  },
  "request_id": "req_abc123"
}
```

### Common Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## SDKs and Libraries

Official SDKs are available for popular languages:

- **Python**: `pip install codeindex-python`
- **JavaScript/Node**: `npm install @codeindex/sdk`
- **Go**: `go get github.com/codeindex/go-sdk`
- **Java**: Maven/Gradle coordinates available

### Python SDK Example

```python
from codeindex import CodeIndexClient

client = CodeIndexClient(api_key="your-api-key")

# Create an index
index = client.create_index(
    name="my-project",
    repository_url="https://github.com/user/repo"
)

# Search for code
results = client.search_code(
    query="async def fetch",
    index_ids=[index.id],
    languages=["python"]
)

for result in results:
    print(f"{result.file_path}:{result.line_number}")
    print(result.content)
```

## Best Practices

1. **Batch Operations**: Use bulk endpoints when indexing multiple repositories
2. **Caching**: Implement client-side caching for frequently accessed data
3. **Pagination**: Always paginate large result sets
4. **Error Handling**: Implement exponential backoff for rate limit errors
5. **Security**: Never expose API tokens in client-side code

## Changelog

### Version 1.2.0 (2024-01-15)
- Added semantic search capabilities
- Improved Python parsing accuracy
- New metrics endpoint for code quality analysis

### Version 1.1.0 (2023-12-01)
- Support for 5 additional programming languages
- Webhook functionality
- Performance improvements for large repositories

### Version 1.0.0 (2023-10-15)
- Initial release
- Core search and indexing functionality
- Support for Python, JavaScript, and Java