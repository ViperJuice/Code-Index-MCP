# AI Documentation Index

This directory contains comprehensive documentation for all APIs, frameworks, and technologies used in the MCP Server project. Each document includes installation instructions, code examples, best practices, and MCP-specific implementation patterns.

## Core Frameworks

### [FastAPI](./fastapi_overview.md)
Modern, fast web framework for building the MCP Server REST API. Includes async support, automatic validation, and OpenAPI documentation.

### [Pydantic](./pydantic_overview.md)
Data validation using Python type annotations. Used for request/response models, configuration management, and schema generation.

### [Tree-sitter](./tree_sitter_overview.md)
Incremental parsing library for code analysis. Provides language-agnostic parsing with error recovery for 100+ programming languages.

## Code Analysis Tools

### [Jedi](./jedi.md)
Static analysis library for Python. Provides code completion, goto definitions, reference finding, and type inference.

### [Voyage AI](./voyage_ai_overview.md)
State-of-the-art embedding models for semantic code understanding. Powers semantic search and code similarity features.

## Storage & Search

### [SQLite FTS5](./sqlite_fts5_overview.md)
Full-text search extension for SQLite. Provides efficient code search with support for boolean queries and ranking.

### [Qdrant](./qdrant.md)
Vector database for semantic search. Stores and queries code embeddings for intelligent code discovery.

### [Redis](./redis.md)
In-memory data structure store. Used for caching, task queue backend (Celery), and session management.

## Async & Background Processing

### [Celery](./celery_overview.md)
Distributed task queue for Python. Handles long-running indexing operations, batch processing, and scheduled tasks.

### [Watchdog](./watchdog.md)
Cross-platform file system event monitoring. Triggers automatic re-indexing when code files change.

## Cloud & Communication

### [gRPC](./grpc_overview.md)
High-performance RPC framework. Enables efficient cloud sync and distributed indexing across services.

## Security & Monitoring

### [JWT Authentication](./jwt_authentication_overview.md)
JSON Web Token implementation for secure API access. Provides stateless authentication with role-based permissions.

### [Prometheus](./prometheus_overview.md)
Metrics collection and monitoring. Tracks indexing performance, API latency, and system health.

## Quick Reference

| Technology | Purpose | Key Features |
|------------|---------|--------------|
| FastAPI | REST API Framework | Async, auto-validation, OpenAPI |
| Tree-sitter | Code Parsing | Incremental, error-tolerant, multi-language |
| SQLite FTS5 | Full-text Search | Fast queries, boolean operators, ranking |
| Celery | Task Queue | Distributed, scheduled tasks, retries |
| Redis | Cache & Queue | In-memory, pub/sub, data structures |
| Qdrant | Vector Search | Semantic search, filtering, clustering |
| Jedi | Python Analysis | Completions, definitions, references |
| Watchdog | File Monitoring | Cross-platform, event-based, filters |
| gRPC | RPC Framework | Streaming, protobuf, high performance |
| JWT | Authentication | Stateless, role-based, secure |
| Prometheus | Monitoring | Time-series, alerting, visualization |

## Implementation Priority

1. **Phase 1 - Core**: FastAPI, Pydantic, Tree-sitter, SQLite FTS5
2. **Phase 2 - Enhancement**: Jedi, Watchdog, Redis, JWT
3. **Phase 3 - Advanced**: Celery, Qdrant, Voyage AI
4. **Phase 4 - Scale**: gRPC, Prometheus

## Best Practices

1. **Start Simple**: Begin with core technologies and add advanced features incrementally
2. **Test Integration**: Each technology should be tested in isolation before integration
3. **Monitor Performance**: Use Prometheus from the start to track system behavior
4. **Security First**: Implement JWT authentication early in development
5. **Document APIs**: Leverage FastAPI's automatic OpenAPI documentation

## Resources

- [MCP Server Architecture](../architecture/)
- [Development Roadmap](../ROADMAP.md)
- [Security Model](../architecture/security_model.md)
- [Performance Requirements](../architecture/performance_requirements.md)