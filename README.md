# Code-Index-MCP (Local-first Code Indexer)

Modular, extensible local-first code indexer designed to enhance Claude Code and other LLMs with deep code understanding capabilities. Built on the Model Context Protocol (MCP) for seamless integration with AI assistants.

## Implementation Status
**Current completion**: 85% (Core system operational with 48-language support)  
**System complexity**: 5/5 (High - 136k lines, semantic search, distributed architecture)  
**Production ready**: Core features operational, deployment automation in progress

## 🎯 Key Features

- **🚀 Local-First Architecture**: All indexing happens locally for speed and privacy
- **🔌 Plugin-Based Design**: Easily extensible with language-specific plugins
- **🔍 48-Language Support**: Complete tree-sitter integration with semantic search
- **⚡ Real-Time Updates**: File system monitoring for instant index updates
- **🧠 Semantic Search**: AI-powered code search with Voyage AI embeddings
- **📊 Rich Code Intelligence**: Symbol resolution, type inference, dependency tracking

## 🏗️ Architecture

The Code-Index-MCP follows a modular, plugin-based architecture designed for extensibility and performance:

### System Layers

1. **🌐 System Context (Level 1)**
   - Developer interacts with Claude Code or other LLMs
   - MCP protocol provides standardized tool interface
   - Local-first processing with optional cloud features
   - Performance SLAs: <100ms symbol lookup, <500ms search

2. **📦 Container Architecture (Level 2)**
   ```
   ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
   │   API Gateway   │────▶│  Dispatcher  │────▶│   Plugins   │
   │   (FastAPI)     │     │              │     │ (Language)  │
   └─────────────────┘     └──────────────┘     └─────────────┘
          │                        │                     │
          ▼                        ▼                     ▼
   ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
   │  Local Index    │     │ File Watcher │     │  Embedding  │
   │  (SQLite+FTS5)  │     │  (Watchdog)  │     │   Service   │
   └─────────────────┘     └──────────────┘     └─────────────┘
   ```

3. **🔧 Component Details (Level 3)**
   - **Gateway Controller**: RESTful API endpoints
   - **Dispatcher Core**: Plugin routing and lifecycle
   - **Plugin Base**: Standard interface for all plugins
   - **Language Plugins**: Specialized parsers and analyzers
   - **Index Manager**: SQLite with FTS5 for fast searches
   - **Watcher Service**: Real-time file monitoring

## 🛠️ Language Support

### ✅ Fully Supported Languages (46+ Total)

**Production-Ready Features:**
- **Dynamic Plugin Loading**: Languages are loaded on-demand for optimal performance
- **Tree-sitter Parsing**: Accurate AST-based symbol extraction with language-specific queries
- **Query Caching**: Improved performance with cached tree-sitter queries
- **Semantic Search**: Optional AI-powered code search (when Qdrant is available)
- **Cross-Language Search**: Find symbols and patterns across all supported languages

**Language Categories:**

| Category | Languages | Features |
|----------|-----------|----------|
| **Dedicated Plugins** | Python, JavaScript, TypeScript, C, C++, Dart, HTML/CSS | Enhanced analysis, framework support |
| **Systems Languages** | Go, Rust, C, C++, Zig, Nim, D, V | Memory safety, performance analysis |
| **JVM Languages** | Java, Kotlin, Scala, Clojure | Package analysis, build tool integration |
| **Web Technologies** | JavaScript, TypeScript, HTML, CSS, SCSS, PHP | Framework detection, bundler support |
| **Scripting Languages** | Python, Ruby, Perl, Lua, R, Julia | Dynamic typing, REPL integration |
| **Functional Languages** | Haskell, Elixir, Erlang, F#, OCaml | Pattern matching, type inference |
| **Mobile Development** | Swift, Kotlin, Dart, Objective-C | Platform-specific APIs |
| **Infrastructure** | Dockerfile, Bash, PowerShell, Makefile, CMake | Build automation, CI/CD |
| **Data Formats** | JSON, YAML, TOML, XML, GraphQL, SQL | Schema validation, query optimization |
| **Documentation** | Markdown, LaTeX, reStructuredText | Cross-references, formatting |

**Implementation Status: Production-Ready** - All languages supported via the enhanced dispatcher with:
- ✅ Dynamic plugin loading (lazy initialization)
- ✅ Robust error handling and fallback mechanisms
- ✅ Path resolution for complex project structures
- ✅ Graceful degradation when external services unavailable

## 🚀 Quickstart

### Prerequisites
- Python 3.8+
- Git
- Docker (optional, for architecture diagrams)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Code-Index-MCP.git
   cd Code-Index-MCP
   ```

2. **Install dependencies**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install requirements
   pip install -r requirements.txt
   ```

3. **Start the server**
   ```bash
   # Start the MCP server
   uvicorn mcp_server.gateway:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Test the API**
   ```bash
   # Check server status
   curl http://localhost:8000/status
   
   # Search for code
   curl -X POST http://localhost:8000/search \
     -H "Content-Type: application/json" \
     -d '{"query": "def parse"}'
   ```

### 🔧 Configuration

Create a `.env` file for configuration:

```env
# Optional: Voyage AI for semantic search
VOYAGE_AI_API_KEY=your_api_key_here

# Server settings
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Workspace settings
MCP_WORKSPACE_ROOT=.
MCP_MAX_FILE_SIZE=10485760  # 10MB
```

## 🗂️ Index Artifact Management

**Zero Reindex Time for Developers** - This project includes pre-built index artifacts that are committed to the repository, eliminating the need for new developers to spend time reindexing.

### How It Works

1. **Pre-built Indexes**: The repository includes:
   - `code_index.db` - SQLite database with all symbols (70MB)
   - `vector_index.qdrant/` - Vector embeddings for semantic search
   - `.index_metadata.json` - Compatibility and version info

2. **Automatic Compatibility**: The system checks embedding model compatibility:
   ```bash
   # Check if your local config is compatible with committed indexes
   python mcp_cli.py index check-compatibility
   ```

3. **Smart Rebuilding**: Indexes are automatically rebuilt when:
   - Embedding model changes
   - Significant code changes occur
   - Manual rebuild requested

### CLI Management

```bash
# Check index status
python mcp_cli.py index status

# Check compatibility
python mcp_cli.py index check-compatibility

# Rebuild if needed
python mcp_cli.py index rebuild

# Create backup before major changes
python mcp_cli.py index backup my_backup

# Restore from backup
python mcp_cli.py index restore my_backup
```

### GitHub Actions Integration

- **Pull Requests**: Automatically validate index compatibility
- **Merges to Main**: Rebuild and commit updated indexes if needed
- **Manual Trigger**: Force rebuild via GitHub Actions

### Embedding Model Compatibility

The system tracks embedding model versions to ensure compatibility:
- **Current model**: `voyage-code-3` (1024 dimensions)
- **Distance metric**: Cosine similarity
- **Auto-rebuild**: Triggered when model changes

If you use a different embedding model, the system will detect incompatibility and offer to rebuild indexes with your configuration.

## 💻 Development

### Creating a New Language Plugin

1. **Create plugin structure**
   ```bash
   mkdir -p mcp_server/plugins/my_language_plugin
   cd mcp_server/plugins/my_language_plugin
   touch __init__.py plugin.py
   ```

2. **Implement the plugin interface**
   ```python
   from mcp_server.plugin_base import PluginBase
   
   class MyLanguagePlugin(PluginBase):
       def __init__(self):
           self.tree_sitter_language = "my_language"
       
       def index(self, file_path: str) -> Dict:
           # Parse and index the file
           pass
       
       def getDefinition(self, symbol: str, context: Dict) -> Dict:
           # Find symbol definition
           pass
       
       def getReferences(self, symbol: str, context: Dict) -> List[Dict]:
           # Find symbol references
           pass
   ```

3. **Register the plugin**
   ```python
   # In dispatcher.py
   from .plugins.my_language_plugin import MyLanguagePlugin
   
   self.plugins['my_language'] = MyLanguagePlugin()
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest test_python_plugin.py

# Run with coverage
pytest --cov=mcp_server --cov-report=html
```

### Architecture Visualization

```bash
# View C4 architecture diagrams
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite

# Open http://localhost:8080 in your browser
```

## 📚 API Reference

### Core Endpoints

#### `GET /symbol`
Get symbol definition
```
GET /symbol?symbol_name=parseFile&file_path=/path/to/file.py
```
Query parameters:
- `symbol_name` (required): Name of the symbol to find
- `file_path` (optional): Specific file to search in

#### `GET /search`
Search for code patterns
```
GET /search?query=async+def.*parse&file_extensions=.py,.js
```
Query parameters:
- `query` (required): Search pattern (regex supported)
- `file_extensions` (optional): Comma-separated list of extensions

### Response Format

All API responses follow a consistent JSON structure:

**Success Response:**
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🚢 Deployment

### Docker Deployment Options

The project includes multiple Docker configurations for different environments:

**Development (Default):**
```bash
# Uses docker-compose.yml + Dockerfile
docker-compose up -d
# - SQLite database
# - Uvicorn development server  
# - Volume mounts for code changes
# - Debug logging enabled
```

**Production:**
```bash
# Uses docker-compose.production.yml + Dockerfile.production
docker-compose -f docker-compose.production.yml up -d
# - PostgreSQL database
# - Gunicorn + Uvicorn workers
# - Multi-stage optimized builds
# - Security hardening (non-root user)
# - Production logging
```

**Enhanced Development:**
```bash
# Uses both compose files with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
# - Development base + enhanced debugging
# - Source code volume mounting
# - Read-write code access
```

### Container Restart Behavior

**Important**: By default, `docker-compose restart` uses the **DEVELOPMENT** configuration:
- `docker-compose restart` → Uses `docker-compose.yml` (Development)
- `docker-compose -f docker-compose.production.yml restart` → Uses Production

### Production Deployment

For production environments, we provide:

1. **Multi-stage Docker builds** with security hardening
2. **PostgreSQL database** with async support
3. **Redis caching** for performance optimization
4. **Qdrant vector database** for semantic search
5. **Prometheus + Grafana** monitoring stack
6. **Kubernetes manifests** in `k8s/` directory
7. **nginx reverse proxy** configuration

See our [Deployment Guide](docs/DEPLOYMENT-GUIDE.md) for detailed instructions including:
- Kubernetes deployment configurations
- Auto-scaling setup
- Database optimization
- Security best practices
- Monitoring and observability

### System Requirements

- **Minimum**: 2GB RAM, 2 CPU cores, 10GB storage
- **Recommended**: 8GB RAM, 4 CPU cores, 50GB SSD storage
- **Large codebases**: 16GB+ RAM, 8+ CPU cores, 100GB+ SSD storage

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Process

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Add tests** (aim for 90%+ coverage)
5. **Update documentation**
6. **Submit a pull request**

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Write descriptive docstrings
- Keep functions small and focused

## 📈 Performance

### Benchmarks

| Operation | Performance Target | Current Status |
|-----------|-------------------|----------------|
| Symbol Lookup | <100ms (p95) | ✅ Implemented, pending benchmark results |
| Code Search | <500ms (p95) | ✅ Implemented, pending benchmark results |
| File Indexing | 10K files/min | ✅ Implemented, pending benchmark results |

## 🏗️ Architecture Overview

The system follows C4 model architecture patterns:

- **Workspace Definition**: 85% implemented (architecture/workspace.dsl)
- **System Context (L1)**: Claude Code integration operational
- **Container Level (L2)**: 6 main containers (API, Dispatcher, Plugins, Index, Storage, Watcher)
- **Component Level (L3)**: Plugin system with 48 languages, 15 well-defined components
- **Code Level (L4)**: 22 PlantUML diagrams with 90% coverage

For detailed architectural documentation, see the [architecture/](architecture/) directory.

## 🗺️ Development Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development plans and current progress.

**Current Status**: 85% Complete - Core System Operational
- ✅ **Completed**: 48-language support, semantic search, real-time indexing, production infrastructure
- 🔄 **In Progress**: Document processing validation, performance benchmark publication
- 📋 **Planned**: Production deployment automation, monitoring framework

**Next Steps**: Interface-first development hierarchy focusing on container interfaces and external module boundaries.

### Optimization Tips

Performance optimization features are implemented and available:

1. **Enable caching**: Redis caching is implemented and configurable via environment variables
2. **Adjust batch size**: Configurable via `INDEXING_BATCH_SIZE` environment variable
3. **Use SSD storage**: Improves indexing speed significantly
4. **Limit file size**: Configurable via `INDEXING_MAX_FILE_SIZE` environment variable
5. **Parallel processing**: Multi-worker indexing configurable via `INDEXING_MAX_WORKERS`

## 🔒 Security

- **Local-first**: All processing happens locally by default
- **Path validation**: Prevents directory traversal attacks
- **Input sanitization**: All queries are sanitized
- **Secret detection**: Automatic redaction of detected secrets
- **Plugin isolation**: Plugins run in restricted environments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Tree-sitter](https://tree-sitter.github.io/) for language parsing
- [Jedi](https://jedi.readthedocs.io/) for Python analysis
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [Voyage AI](https://www.voyageai.com/) for embeddings
- [Anthropic](https://www.anthropic.com/) for the MCP protocol

## 📬 Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/Code-Index-MCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Code-Index-MCP/discussions)
- **Email**: your.email@example.com

---

<p align="center">Built with ❤️ for the developer community</p>
