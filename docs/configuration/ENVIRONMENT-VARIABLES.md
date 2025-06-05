# Environment Variables Reference

This document provides a comprehensive reference of all environment variables supported by Code-Index-MCP, including their purposes, default values, and usage examples.

## Core Server Configuration

### `MCP_SERVER_HOST`
- **Description**: The host address for the MCP FastAPI server
- **Type**: String
- **Default**: `"127.0.0.1"`
- **Example**: 
  ```bash
  export MCP_SERVER_HOST="0.0.0.0"  # Listen on all interfaces
  ```

### `MCP_SERVER_PORT`
- **Description**: The port number for the MCP FastAPI server
- **Type**: Integer
- **Default**: `8000`
- **Example**: 
  ```bash
  export MCP_SERVER_PORT=8080
  ```

### `MCP_LOG_LEVEL`
- **Description**: Logging level for the application
- **Type**: String
- **Default**: `"INFO"`
- **Valid Values**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **Example**: 
  ```bash
  export MCP_LOG_LEVEL="DEBUG"
  ```

## File System Configuration

### `MCP_WORKSPACE_ROOT`
- **Description**: Root directory for code indexing operations
- **Type**: Path
- **Default**: Current working directory
- **Example**: 
  ```bash
  export MCP_WORKSPACE_ROOT="/home/user/projects"
  ```

### `MCP_ALLOWED_PATHS`
- **Description**: Comma-separated list of allowed paths for indexing (security feature)
- **Type**: String (comma-separated paths)
- **Default**: Current workspace only
- **Example**: 
  ```bash
  export MCP_ALLOWED_PATHS="/home/user/projects,/workspace"
  ```

### `MCP_DENIED_PATTERNS`
- **Description**: Comma-separated list of file patterns to exclude from indexing
- **Type**: String (comma-separated glob patterns)
- **Default**: `"*.key,*.pem,.env*,*secrets*"`
- **Example**: 
  ```bash
  export MCP_DENIED_PATTERNS="*.key,*.pem,.env*,*secrets*,*.log"
  ```

### `MCP_MAX_FILE_SIZE`
- **Description**: Maximum file size to index (in MB)
- **Type**: Integer
- **Default**: `10`
- **Example**: 
  ```bash
  export MCP_MAX_FILE_SIZE=20  # Allow files up to 20MB
  ```

## Indexing Configuration

### `MCP_INDEX_THREADS`
- **Description**: Number of threads for parallel file indexing
- **Type**: Integer
- **Default**: Number of CPU cores
- **Example**: 
  ```bash
  export MCP_INDEX_THREADS=8
  ```

### `MCP_INDEX_BATCH_SIZE`
- **Description**: Number of files to process in a single batch
- **Type**: Integer
- **Default**: `100`
- **Example**: 
  ```bash
  export MCP_INDEX_BATCH_SIZE=50
  ```

### `MCP_PARSE_TIMEOUT`
- **Description**: Maximum time (in seconds) to parse a single file
- **Type**: Integer
- **Default**: `30`
- **Example**: 
  ```bash
  export MCP_PARSE_TIMEOUT=60
  ```

## Database Configuration

### `MCP_QDRANT_PATH`
- **Description**: Path to Qdrant vector database storage
- **Type**: Path or `:memory:`
- **Default**: `:memory:` (in-memory database)
- **Example**: 
  ```bash
  export MCP_QDRANT_PATH="/var/lib/mcp/qdrant"
  ```

### `MCP_QDRANT_COLLECTION`
- **Description**: Name of the Qdrant collection for code embeddings
- **Type**: String
- **Default**: `"code-index"`
- **Example**: 
  ```bash
  export MCP_QDRANT_COLLECTION="my-project-index"
  ```

## API Keys and External Services

### `VOYAGEAI_API_KEY`
- **Description**: API key for Voyage AI code embeddings service
- **Type**: String
- **Default**: None (required for semantic search)
- **Example**: 
  ```bash
  export VOYAGEAI_API_KEY="pa-xxxxxxxxxxxxx"
  ```
- **Security**: Store in secure keyring or secrets manager

### `OPENAI_API_KEY`
- **Description**: OpenAI API key (for future LLM features)
- **Type**: String
- **Default**: None
- **Example**: 
  ```bash
  export OPENAI_API_KEY="sk-xxxxxxxxxxxxx"
  ```
- **Security**: Never commit to version control

### `GOOGLE_API_KEY`
- **Description**: Google API key (for future features)
- **Type**: String
- **Default**: None
- **Example**: 
  ```bash
  export GOOGLE_API_KEY="AIzaxxxxxxxxxxxxx"
  ```
- **Security**: Use environment-specific keys

## Cache Configuration

### `MCP_CACHE_SIZE`
- **Description**: Maximum number of entries in query cache
- **Type**: Integer
- **Default**: `10000`
- **Example**: 
  ```bash
  export MCP_CACHE_SIZE=5000
  ```

### `MCP_CACHE_TTL`
- **Description**: Cache time-to-live in seconds
- **Type**: Integer
- **Default**: `300` (5 minutes)
- **Example**: 
  ```bash
  export MCP_CACHE_TTL=600  # 10 minutes
  ```

## Performance Tuning

### `MCP_MEMORY_LIMIT`
- **Description**: Maximum memory usage for indexing operations (in MB)
- **Type**: Integer
- **Default**: `2048` (2GB)
- **Example**: 
  ```bash
  export MCP_MEMORY_LIMIT=4096  # 4GB
  ```

### `MCP_CPU_LIMIT`
- **Description**: Maximum CPU usage percentage
- **Type**: Integer (0-100)
- **Default**: `50`
- **Example**: 
  ```bash
  export MCP_CPU_LIMIT=75  # Use up to 75% CPU
  ```

### `MCP_RATE_LIMIT`
- **Description**: API rate limit (requests per minute)
- **Type**: Integer
- **Default**: `1000`
- **Example**: 
  ```bash
  export MCP_RATE_LIMIT=500
  ```

## Security Configuration

### `MCP_AUTH_ENABLED`
- **Description**: Enable API authentication
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_AUTH_ENABLED=true
  ```

### `MCP_JWT_SECRET`
- **Description**: Secret key for JWT token signing
- **Type**: String
- **Default**: None (required if auth enabled)
- **Example**: 
  ```bash
  export MCP_JWT_SECRET="your-secret-key-here"
  ```
- **Security**: Generate with `openssl rand -hex 32`

### `MCP_TOKEN_EXPIRY`
- **Description**: JWT token expiration time (in hours)
- **Type**: Integer
- **Default**: `24`
- **Example**: 
  ```bash
  export MCP_TOKEN_EXPIRY=48  # 2 days
  ```

## Plugin Configuration

### `MCP_ENABLED_PLUGINS`
- **Description**: Comma-separated list of enabled language plugins
- **Type**: String
- **Default**: `"python,javascript,typescript,c,cpp,dart,html,css"`
- **Example**: 
  ```bash
  export MCP_ENABLED_PLUGINS="python,javascript"  # Only enable specific plugins
  ```

### `MCP_PLUGIN_TIMEOUT`
- **Description**: Maximum execution time for plugin operations (seconds)
- **Type**: Integer
- **Default**: `30`
- **Example**: 
  ```bash
  export MCP_PLUGIN_TIMEOUT=60
  ```

## Development and Debug

### `MCP_DEBUG`
- **Description**: Enable debug mode with additional logging
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_DEBUG=true
  ```

### `MCP_PROFILE`
- **Description**: Enable performance profiling
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_PROFILE=true
  ```

### `MCP_TEST_MODE`
- **Description**: Run in test mode with mock services
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_TEST_MODE=true
  ```

## Cloud Sync Configuration (Optional)

### `MCP_CLOUD_SYNC_ENABLED`
- **Description**: Enable cloud synchronization features
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_CLOUD_SYNC_ENABLED=true
  ```

### `MCP_CLOUD_ENDPOINT`
- **Description**: Cloud sync service endpoint
- **Type**: URL
- **Default**: None
- **Example**: 
  ```bash
  export MCP_CLOUD_ENDPOINT="https://sync.example.com"
  ```

### `MCP_CLOUD_API_KEY`
- **Description**: API key for cloud sync service
- **Type**: String
- **Default**: None
- **Example**: 
  ```bash
  export MCP_CLOUD_API_KEY="cloud-key-xxxxx"
  ```

## Usage Examples

### Basic Development Setup
```bash
# .env.development
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=DEBUG
MCP_DEBUG=true
VOYAGEAI_API_KEY=pa-xxxxxxxxxxxxx
```

### Production Setup
```bash
# .env.production
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_LOG_LEVEL=INFO
MCP_AUTH_ENABLED=true
MCP_JWT_SECRET=$(openssl rand -hex 32)
MCP_QDRANT_PATH=/var/lib/mcp/qdrant
MCP_MEMORY_LIMIT=4096
MCP_CPU_LIMIT=75
VOYAGEAI_API_KEY=${VOYAGEAI_API_KEY}  # From secrets manager
```

### Testing Setup
```bash
# .env.test
MCP_TEST_MODE=true
MCP_QDRANT_PATH=:memory:
MCP_LOG_LEVEL=WARNING
MCP_PARSE_TIMEOUT=5
MCP_INDEX_THREADS=2
```

## Environment File Loading

The application supports loading environment variables from files in the following order:

1. System environment variables
2. `.env` file in the project root
3. `.env.local` file (for local overrides, gitignored)
4. Environment-specific files (e.g., `.env.development`, `.env.production`)

Example `.env` file:
```bash
# Core configuration
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Security
MCP_AUTH_ENABLED=false
MCP_ALLOWED_PATHS=/workspace

# Performance
MCP_INDEX_THREADS=4
MCP_CACHE_SIZE=10000

# External services (use secure storage in production)
VOYAGEAI_API_KEY=your-api-key-here
```

## Model Context Protocol (MCP) Configuration

### `MCP_DISABLE_RESOURCES`
- **Description**: Disable resource capabilities for Claude Code compatibility
- **Type**: Boolean (`true`/`false`, `1`/`0`, `yes`/`no`)
- **Default**: `false`
- **Use Case**: Claude Code only supports Tools and Prompts, not Resources
- **Example**: 
  ```bash
  export MCP_DISABLE_RESOURCES=true  # Required for Claude Code
  ```

### `MCP_DEBUG`
- **Description**: Enable MCP protocol debugging output
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Example**: 
  ```bash
  export MCP_DEBUG=true
  ```

### `MCP_CLIENT_TYPE`
- **Description**: Identifies the MCP client type for compatibility adjustments
- **Type**: String
- **Default**: None
- **Valid Values**: `"claude-code"`, `"cursor"`, `"mcp-inspector"`
- **Example**: 
  ```bash
  export MCP_CLIENT_TYPE="claude-code"
  ```

### `MCP_AUTO_INDEX`
- **Description**: Automatically index codebase on startup if database is empty
- **Type**: Boolean (`true`/`false`, `1`/`0`, `yes`/`no`)
- **Default**: `false`
- **Use Case**: Useful for first-time setup or container deployments
- **Note**: Currently indexes up to 100 Python files to avoid slow startup
- **Example**: 
  ```bash
  export MCP_AUTO_INDEX=true  # Auto-index on first run
  ```

## Best Practices

1. **Security**: Never commit sensitive API keys to version control
2. **Defaults**: Always provide sensible defaults for optional variables
3. **Validation**: Validate environment variables at startup
4. **Documentation**: Keep this document updated with new variables
5. **Typing**: Use appropriate types (string, integer, boolean, path)
6. **Naming**: Use `MCP_` prefix for all application-specific variables