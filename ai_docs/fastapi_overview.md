# FastAPI Overview

## Introduction
FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It's one of the fastest Python frameworks available, on par with NodeJS and Go.

## Key Features

### Performance
- **High Performance**: Built on Starlette and Pydantic
- **Async Support**: Native async/await support
- **Production-Ready**: Suitable for high-load applications

### Developer Experience
- **Type Hints**: Leverages Python type hints for validation
- **Auto Documentation**: Generates interactive API docs (Swagger/OpenAPI)
- **IDE Support**: Excellent autocompletion and error checking
- **Fast Development**: 200-300% faster feature development

## Installation

```bash
# Full installation with all features
pip install "fastapi[standard]"

# Minimal installation
pip install fastapi
pip install uvicorn[standard]
```

## Basic Example

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = False

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items/")
async def create_item(item: Item):
    return {"item": item}
```

## MCP Server Usage

### API Gateway Implementation
```python
from fastapi import FastAPI, HTTPException
from typing import Optional

app = FastAPI(title="MCP Server", version="1.0.0")

@app.post("/symbol")
async def lookup_symbol(
    file_path: str,
    symbol_name: str,
    symbol_type: Optional[str] = None
):
    """Lookup symbol definition in codebase"""
    try:
        result = await dispatcher.lookup(file_path, symbol_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_code(
    query: str,
    semantic: bool = False,
    file_pattern: Optional[str] = None
):
    """Search code with optional semantic search"""
    results = await dispatcher.search(query, semantic, file_pattern)
    return {"results": results}
```

## Project Structure Best Practices

```
mcp_server/
├── gateway.py          # FastAPI app definition
├── routers/           # API route definitions
│   ├── __init__.py
│   ├── symbol.py      # Symbol lookup endpoints
│   └── search.py      # Search endpoints
├── dependencies/      # Dependency injection
│   ├── __init__.py
│   ├── auth.py        # Authentication deps
│   └── validation.py  # Validation deps
├── schemas/           # Pydantic models
│   ├── __init__.py
│   ├── requests.py    # Request models
│   └── responses.py   # Response models
└── middleware/        # Custom middleware
    ├── __init__.py
    ├── auth.py        # Auth middleware
    └── logging.py     # Request logging
```

## Async Best Practices

### Do Use Async For:
```python
# I/O bound operations
@app.get("/search")
async def search(query: str):
    results = await async_database_query(query)
    embeddings = await async_embedding_service(query)
    return {"results": results, "embeddings": embeddings}
```

### Don't Use Async For:
```python
# CPU bound operations - use sync or background tasks
@app.post("/index")
def index_file(file_path: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(cpu_intensive_indexing, file_path)
    return {"status": "indexing started"}
```

## Dependency Injection

```python
from fastapi import Depends

async def get_dispatcher():
    """Dependency to get dispatcher instance"""
    return dispatcher_instance

async def verify_api_key(api_key: str = Header()):
    """Verify API key from header"""
    if not is_valid_key(api_key):
        raise HTTPException(status_code=403)
    return api_key

@app.get("/protected")
async def protected_route(
    dispatcher = Depends(get_dispatcher),
    api_key = Depends(verify_api_key)
):
    return {"status": "authenticated"}
```

## Error Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.post("/symbol")
async def lookup_symbol(request: SymbolRequest):
    if not dispatcher:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    return await dispatcher.lookup(request)
```

## Request Validation with Pydantic

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class SymbolRequest(BaseModel):
    file_path: str = Field(..., description="Path to source file")
    symbol_name: str = Field(..., min_length=1)
    symbol_type: Optional[str] = Field(None, regex="^(function|class|variable)$")
    
    @validator('file_path')
    def validate_path(cls, v):
        if not v.startswith('/'):
            raise ValueError('Path must be absolute')
        return v

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=100)
    semantic: bool = False
    languages: Optional[List[str]] = None
    max_results: int = Field(20, ge=1, le=100)
```

## Middleware Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1"]
)

# Custom middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## Testing FastAPI Applications

```python
from fastapi.testclient import TestClient
from mcp_server.gateway import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "MCP Server"}

def test_symbol_lookup():
    response = client.post(
        "/symbol",
        json={
            "file_path": "/test/file.py",
            "symbol_name": "test_function"
        }
    )
    assert response.status_code == 200
```

## Performance Optimization

### Response Caching
```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@app.get("/search")
@cache(expire=300)  # Cache for 5 minutes
async def search(query: str):
    return await expensive_search_operation(query)
```

### Background Tasks
```python
from fastapi import BackgroundTasks

@app.post("/index")
async def trigger_indexing(
    file_path: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(index_file_async, file_path)
    return {"message": "Indexing started"}
```

## Security Best Practices

### Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/search")
@limiter.limit("10/minute")
async def search(request: Request, query: str):
    return await search_handler(query)
```

### Input Sanitization
```python
from fastapi import Query
import re

@app.get("/search")
async def search(
    query: str = Query(
        ..., 
        min_length=2,
        max_length=100,
        regex="^[a-zA-Z0-9_\\s]+$"
    )
):
    # Query is automatically validated
    return await search_handler(query)
```

## Deployment Considerations

### Production Server
```bash
# Development
uvicorn mcp_server.gateway:app --reload

# Production with Gunicorn
gunicorn mcp_server.gateway:app -w 4 -k uvicorn.workers.UvicornWorker

# Production with multiple workers
uvicorn mcp_server.gateway:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Configuration
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    api_key: str
    database_url: str
    redis_url: str = "redis://localhost"
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Integration with MCP Server

FastAPI will serve as the primary API gateway for the MCP Server, handling:
- Request routing to appropriate plugins
- Authentication and authorization
- Request validation and sanitization
- Response formatting and caching
- Error handling and logging
- Performance monitoring

The framework's async capabilities make it ideal for handling multiple concurrent code analysis requests while maintaining high performance.