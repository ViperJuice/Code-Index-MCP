# Docker Development Environment for Repository Management

This document describes the enhanced Docker development setup that supports the new repository management features for cross-language translation and refactoring.

## 🐳 Enhanced Docker Configuration

### **Dockerfile.dev Updates**

The development container now includes:

```dockerfile
# Additional system dependencies
RUN apt-get install -y \
    sqlite3 \                    # SQLite CLI for database inspection
    libsqlite3-dev              # SQLite development headers

# Additional directories
RUN mkdir -p /app/repositories  # Repository storage
VOLUME ["/external_repos"]      # Mount point for external repositories

# Repository management environment variables
ENV ENABLE_REPOSITORY_MANAGEMENT=true
ENV REPOSITORY_AUTO_CLEANUP=true
ENV DEFAULT_REPOSITORY_TTL_DAYS=30
```

### **docker-compose.dev.yml Updates**

Enhanced development configuration:

```yaml
services:
  mcp-server:
    build:
      dockerfile: Dockerfile.dev  # Use development Dockerfile
    volumes:
      - ./external_repos:/external_repos:ro  # External repositories mount
    environment:
      # Repository management settings
      - ENABLE_REPOSITORY_MANAGEMENT=true
      - REPOSITORY_AUTO_CLEANUP=true
      - DEFAULT_REPOSITORY_TTL_DAYS=7       # Shorter TTL for development
      - EXTERNAL_REPOS_PATH=/external_repos
```

## 🛠 Development Setup Scripts

### **Quick Setup**

```bash
# Run the automated setup
./scripts/setup-repository-dev.sh
```

This script:
1. Creates necessary directories (`external_repos`, `data`, `logs`)
2. Sets up sample repositories for testing
3. Builds the development container
4. Provides usage instructions

### **Manual Setup**

```bash
# 1. Create test repositories
python3 scripts/development/setup_repository_test.py

# 2. Build development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# 3. Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 📁 Directory Structure

After setup, your project will have:

```
Code-Index-MCP/
├── external_repos/           # External repositories for testing
│   ├── rust_auth_examples/   # Sample Rust authentication code
│   ├── go_web_examples/      # Sample Go web service code
│   └── python_fastapi_examples/ # Sample Python FastAPI code
├── data/                     # SQLite database storage
│   └── code_index.db        # Main database (includes all repositories)
├── logs/                     # Application logs
└── repositories/            # Repository metadata cache
```

## 🧪 Sample Test Repositories

The setup creates three sample repositories for testing cross-language translation:

### **1. Rust Authentication Examples** (`/external_repos/rust_auth_examples`)
- **Language**: Rust (Axum framework)
- **Features**: JWT authentication, bcrypt password hashing, middleware
- **Files**: `auth.rs`, `middleware.rs`, `models.rs`
- **Use Case**: Learn Rust authentication patterns

### **2. Go Web Service Examples** (`/external_repos/go_web_examples`)
- **Language**: Go (Gorilla Mux)
- **Features**: HTTP handlers, JWT tokens, authentication middleware
- **Files**: `auth/handlers.go`, `middleware/auth.go`
- **Use Case**: Compare Go vs Rust/Python approaches

### **3. Python FastAPI Examples** (`/external_repos/python_fastapi_examples`)
- **Language**: Python (FastAPI)
- **Features**: Pydantic models, OAuth2, dependency injection
- **Files**: `main.py` with complete FastAPI authentication
- **Use Case**: Source codebase for translation to Rust/Go

## 🔄 Development Workflow

### **1. Start Development Environment**

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### **2. Access Container**

```bash
# Get a shell in the running container
docker exec -it code-index-mcp_mcp-server_1 /bin/bash

# Or start container with shell access
docker-compose -f docker-compose.yml -f docker-compose.dev.yml run mcp-server /bin/bash
```

### **3. Test Repository Management**

```bash
# Run the repository features test
python3 scripts/development/test_repository_features.py
```

### **4. Interactive MCP Testing**

```python
# In Python shell within container
import asyncio
from mcp_server.tools.handlers.repository_manager import *
from mcp_server.storage.sqlite_store import SQLiteStore

# Initialize storage
storage = SQLiteStore("/app/data/code_index.db")
context = {"storage": storage}

# Add reference repository
result = await add_reference_repository_handler({
    "path": "/external_repos/rust_auth_examples",
    "name": "Rust Auth Reference",
    "language": "rust",
    "purpose": "python_to_rust_translation",
    "days_to_keep": 7
}, context)
print(result)

# List repositories
repos = await list_repositories_handler({"include_stats": True}, context)
print(repos)
```

## 🔍 Database Inspection

### **SQLite CLI Access**

```bash
# Access database directly
sqlite3 /app/data/code_index.db

# Useful queries
.tables                                    # Show all tables
SELECT * FROM repositories;               # List repositories
SELECT * FROM repositories WHERE json_extract(metadata, '$.temporary') = 1;  # Temporary repos
```

### **Repository Metadata Structure**

```sql
-- Example repository metadata
{
  "type": "reference",
  "language": "rust", 
  "purpose": "python_to_rust_translation",
  "temporary": true,
  "cleanup_after": "2025-02-10T10:30:00",
  "days_to_keep": 7,
  "created_at": "2025-01-03T10:30:00",
  "project": "auth_service_migration"
}
```

## 🧪 Testing Cross-Language Patterns

### **Example Translation Workflow**

```python
# 1. Add reference repositories
await add_reference_repository_handler({
    "path": "/external_repos/rust_auth_examples",
    "language": "rust",
    "purpose": "translation_target"
}, context)

# 2. Index both local and reference code
# (This would typically be done via MCP tools in actual usage)

# 3. Search for patterns across languages
# search_code("authentication middleware", repository_filter={"group_by_repository": true})
# This would return results grouped by repository/language for comparison

# 4. Clean up when done
await cleanup_repositories_handler({"cleanup_expired": true}, context)
```

## 🔧 Troubleshooting

### **Container Won't Start**

```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs mcp-server

# Rebuild container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
```

### **External Repositories Not Accessible**

```bash
# Check mount points
docker exec -it code-index-mcp_mcp-server_1 ls -la /external_repos

# Verify permissions
ls -la external_repos/
```

### **Database Issues**

```bash
# Check database file
docker exec -it code-index-mcp_mcp-server_1 ls -la /app/data/

# Reset database (warning: deletes all data)
rm data/code_index.db
docker-compose restart mcp-server
```

### **Repository Management Not Working**

```bash
# Run health check
docker exec -it code-index-mcp_mcp-server_1 python3 scripts/development/test_repository_features.py

# Check environment variables
docker exec -it code-index-mcp_mcp-server_1 env | grep REPOSITORY
```

## 📊 Performance Considerations

### **Development Settings**

For development, the following optimizations are applied:

- **Shorter TTLs**: Repository cleanup every 7 days vs 30 days in production
- **Smaller batch sizes**: Reduced indexing batch sizes for faster iteration
- **Debug logging**: Detailed logs for troubleshooting
- **Auto-reload**: Container automatically reloads on code changes

### **Resource Usage**

- **SQLite Database**: Stores all repositories in single file (`code_index.db`)
- **Memory**: Vector embeddings for all repositories stored in database
- **Disk Space**: Sample repositories add ~5MB, real repositories much larger

## 🚀 Production Considerations

When moving to production:

1. **Remove sample repositories**: Delete `external_repos/` directory
2. **Increase TTLs**: Set `DEFAULT_REPOSITORY_TTL_DAYS=30` or higher
3. **Use external storage**: Consider separate vector database for large deployments
4. **Monitor cleanup**: Set up monitoring for automatic repository cleanup
5. **Backup strategy**: Include repository metadata in backup procedures

## 📖 Related Documentation

- **[Translation Workflow Guide](../TRANSLATION_WORKFLOW_GUIDE.md)**: Complete workflow examples
- **[MCP Protocol Documentation](../planning/MCP_IMPLEMENTATION_EXAMPLES.md)**: MCP implementation details
- **[Repository Management API](../api/API-REFERENCE.md)**: Tool reference documentation

---

This enhanced Docker development environment provides everything needed to test and develop with the new repository management features for cross-language translation and refactoring workflows.