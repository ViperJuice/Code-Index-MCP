# Code-Index-MCP (Local-first Code Indexer)

Modular, extensible local-first code indexer designed to enhance Claude Code and other LLMs with deep code understanding capabilities. Built on the Model Context Protocol (MCP) for seamless integration with AI assistants.

## Implementation Status
**Version**: 1.0.0 (MVP Release)
**Core Features**: Stable - Local indexing, symbol/text search, 48-language support
**Optional Features**: Semantic search (requires Voyage AI), Index sync (beta)
**Performance**: Sub-100ms queries, <10s indexing for cached repositories

> **New to Code-Index-MCP?** Check out our [Getting Started Guide](docs/GETTING_STARTED.md) for a quick walkthrough.

## 🎯 Key Features

- **🚀 Local-First Architecture**: All indexing happens locally for speed and privacy
- **📂 Local Index Storage**: All indexes stored at `.indexes/` (relative to MCP server)
- **🔌 Plugin-Based Design**: Easily extensible with language-specific plugins
- **🔍 48-Language Support**: Complete tree-sitter integration with semantic search
- **⚡ Real-Time Updates**: File system monitoring for instant index updates
- **🧠 Semantic Search**: AI-powered code search with Voyage AI embeddings
- **📊 Rich Code Intelligence**: Symbol resolution, type inference, dependency tracking
- **🚀 Enhanced Performance**: Sub-100ms queries with timeout protection and BM25 bypass
- **🔄 Git Synchronization**: Automatic index updates tracking repository changes
- **📦 Portable Index Management**: Zero-cost index sharing via GitHub Artifacts
- **🔄 Automatic Index Sync**: Pull indexes on clone, push on changes
- **🎯 Smart Result Reranking**: Multi-strategy reranking for improved relevance
- **🔒 Security-Aware Export**: Automatic filtering of sensitive files from shared indexes
- **🔍 Hybrid Search**: BM25 + semantic search with configurable fusion
- **🔐 Index Everything Locally**: Search .env files and secrets on your machine
- **🚫 Smart Filtering on Share**: .gitignore and .mcp-index-ignore patterns applied only during export
- **🌐 Multi-Language Indexing**: Index entire repositories with mixed languages

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

## 📁 Project Structure

The project follows a clean, organized structure. See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for detailed layout.

Key directories:
- `mcp_server/` - Core MCP server implementation
- `scripts/` - Development and utility scripts
- `tests/` - Comprehensive test suite with fixtures
- `docs/` - Documentation and guides
- `architecture/` - System design and diagrams
- `docker/` - Docker configurations and compose files
- `data/` - Database files and indexes
- `logs/` - Application and test logs
- `reports/` - Generated performance reports and analysis
- `analysis_archive/` - Historical analysis and archived research

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

## 🚀 Quick Start

### 🎯 Automatic Setup for Claude Code/Desktop (Recommended)
```bash
# Auto-configures MCP for your environment
./scripts/setup-mcp-json.sh

# Or interactive mode
./scripts/setup-mcp-json.sh --interactive
```

This automatically detects your environment and creates the appropriate `.mcp.json` configuration.

### 🐳 Docker Setup by Environment

#### Option 1: Basic Search (No API Keys) - 2 Minutes
```bash
# Install MCP Index with Docker
curl -sSL https://raw.githubusercontent.com/ViperJuice/Code-Index-MCP/main/scripts/install-mcp-docker.sh | bash

# Index your current directory
docker run -it -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:minimal
```

#### Option 2: AI-Powered Search
```bash
# Set your API key (get one at https://voyageai.com)
export VOYAGE_AI_API_KEY=your-key

# Run with semantic search
docker run -it -v $(pwd):/workspace -e VOYAGE_AI_API_KEY ghcr.io/code-index-mcp/mcp-index:standard
```

### 💻 Environment-Specific Setup

#### 🪟 Windows (Native)
```powershell
# PowerShell
.\scripts\setup-mcp-json.ps1

# Or manually with Docker Desktop
docker run -it -v ${PWD}:/workspace ghcr.io/code-index-mcp/mcp-index:minimal
```

#### 🍎 macOS
```bash
# Install Docker Desktop or use Homebrew
brew install --cask docker

# Run setup
./scripts/setup-mcp-json.sh
```

#### 🐧 Linux
```bash
# Install Docker (no Desktop needed)
curl -fsSL https://get.docker.com | sh

# Run setup
./scripts/setup-mcp-json.sh
```

#### 🔄 WSL2 (Windows Subsystem for Linux)
```bash
# With Docker Desktop integration
./scripts/setup-mcp-json.sh  # Auto-detects WSL+Docker

# Without Docker Desktop
cp .mcp.json.templates/native.json .mcp.json
pip install -e .
```

#### 📦 Nested Containers (Dev Containers)
```bash
# For VS Code/Cursor dev containers
# Option 1: Use native Python (already in container)
cp .mcp.json.templates/native.json .mcp.json

# Option 2: Use Docker sidecar (avoids dependency conflicts)
docker-compose -f docker/compose/development/docker-compose.mcp-sidecar.yml up -d
cp .mcp.json.templates/docker-sidecar.json .mcp.json
```

### 📋 MCP.json Configuration Examples

The setup script creates the appropriate `.mcp.json` for your environment. Manual examples:

#### Native Python (Dev Container/Local)
```json
{
  "mcpServers": {
    "code-index-native": {
      "command": "python",
      "args": ["scripts/cli/mcp_server_cli.py"],
      "cwd": "${workspace}"
    }
  }
}
```

#### Docker (Windows/Mac/Linux)
```json
{
  "mcpServers": {
    "code-index-docker": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${workspace}:/workspace",
        "ghcr.io/code-index-mcp/mcp-index:minimal"
      ]
    }
  }
}
```

### 💰 Costs & Features
| Feature | Minimal | Standard | Full | Cost |
|---------|---------|----------|------|------|
| Code Search | ✅ | ✅ | ✅ | Free |
| 48 Languages | ✅ | ✅ | ✅ | Free |
| Semantic Search | ❌ | ✅ | ✅ | ~$0.05/1M tokens |
| GitHub Sync | ❌ | ✅ | ✅ | Free |
| Monitoring | ❌ | ❌ | ✅ | Free |

## 🚀 Quickstart (Python)

### Prerequisites
- Python 3.12+
- Git

### Installation

#### Option 1: Install via pip (Recommended)
```bash
# Install the package
pip install code-index-mcp

# Or install with dev tools for testing
pip install code-index-mcp[dev]
```

#### Option 2: Install from Source
```bash
# Clone the repository
git clone https://github.com/ViperJuice/Code-Index-MCP.git
cd Code-Index-MCP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Quick Start After Installation

```bash
# Authenticate GitHub artifact access once
gh auth login

# Pull the latest published index baseline for this repo
mcp-index artifact pull --latest

# Reconcile only your local drift after restore
mcp-index artifact sync

# Check index status
mcp-index index status

# Start the API server
uvicorn mcp_server.gateway:app --host 0.0.0.0 --port 8000

# Test the API
curl http://localhost:8000/status
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

# GitHub Artifact Sync (privacy settings)
MCP_ARTIFACT_SYNC=false  # Set to true to enable
AUTO_UPLOAD=false        # Auto-upload on changes
AUTO_DOWNLOAD=true       # Auto-download on clone
```

### 🔐 Privacy & GitHub Artifact Sync

Control how your code index is shared:

```json
// .mcp-index.json
{
  "github_artifacts": {
    "enabled": false,        // Disable sync entirely
    "auto_upload": false,    // Manual upload only
    "auto_download": true,   // Still get team indexes
    "exclude_patterns": [    // Additional exclusions
      "internal/*",
      "proprietary/*"
    ]
  }
}
```

**Privacy Features:**
- Indexes filtered by .gitignore automatically
- Additional patterns via .mcp-index-ignore
- Audit logs show what was excluded
- Sync disabled by default in Docker minimal version

## 🆕 Advanced Features

### Search Result Reranking

The system includes multiple reranking strategies to improve search relevance:

```python
# Configure reranking in your searches
from mcp_server.indexer.reranker import RerankConfig, TFIDFReranker

config = RerankConfig(
    enabled=True,
    reranker=TFIDFReranker(),  # Or CohereReranker(), CrossEncoderReranker()
    top_k=20
)

# Search with reranking
results = await search_engine.search(query, rerank_config=config)
```

**Available Rerankers:**
- **TF-IDF**: Fast, local reranking using term frequency
- **Cohere**: Cloud-based neural reranking (requires API key)
- **Cross-Encoder**: Local transformer-based reranking
- **Hybrid**: Combines multiple rerankers with fallback

### Security-Aware Index Sharing

Prevent accidental sharing of sensitive files:

```bash
# Analyze current index for security issues
python scripts/utilities/analyze_gitignore_security.py

# Create secure index export (filters gitignored files)
python scripts/utilities/secure_index_export.py

# The secure export will:
# - Exclude all gitignored files
# - Remove sensitive patterns (*.env, *.key, etc.)
# - Create audit logs of excluded files
```

### BM25 Hybrid Search

Combines traditional full-text search with semantic search:

```python
# The system automatically uses hybrid search when available
# Configure weights in settings:
HYBRID_SEARCH_BM25_WEIGHT=0.3
HYBRID_SEARCH_SEMANTIC_WEIGHT=0.5
HYBRID_SEARCH_FUZZY_WEIGHT=0.2
```

## 🔧 Dispatcher Configuration

### Enhanced Dispatcher (Default)
The enhanced dispatcher includes timeout protection and automatic fallback:

```python
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

store = SQLiteStore(".indexes/YOUR_REPO_ID/current.db")
dispatcher = EnhancedDispatcher(
    sqlite_store=store,
    semantic_search_enabled=True,  # Enable if Qdrant available
    lazy_load=True,               # Load plugins on-demand
    use_plugin_factory=True       # Use dynamic plugin loading
)

# Search with automatic optimization
results = list(dispatcher.search("your query", limit=10))
```

### Simple Dispatcher (Lightweight Alternative)
For maximum performance with BM25-only search:

```python
from mcp_server.dispatcher.simple_dispatcher import create_simple_dispatcher

# Ultra-fast BM25 search without plugin overhead
dispatcher = create_simple_dispatcher(".indexes/YOUR_REPO_ID/current.db")
results = list(dispatcher.search("your query", limit=10))
```

### Configuration Options
Configure dispatcher behavior via environment variables:

```env
# Dispatcher settings
MCP_DISPATCHER_TIMEOUT=5          # Plugin loading timeout (seconds)
MCP_USE_SIMPLE_DISPATCHER=false   # Use simple dispatcher
MCP_PLUGIN_LAZY_LOAD=true        # Load plugins on-demand

# Performance tuning
MCP_BM25_BYPASS_ENABLED=true     # Enable direct BM25 bypass
MCP_MAX_PLUGIN_MEMORY=1024       # Max memory for plugins (MB)
```

## 🗂️ Index Management

### Centralized Index Storage

All indexes are now stored centrally at `.indexes/` (relative to the MCP project) for better organization and to prevent accidental commits:

```
.indexes/
├── {repo_hash}/              # Unique hash for each repository
│   ├── main_abc123.db        # Index for main branch at commit abc123
│   ├── main_abc123.metadata.json
│   └── current.db -> main_abc123.db  # Symlink to active index
├── qdrant/                   # Semantic search embeddings
│   └── main.qdrant/          # Centralized Qdrant database
```

**Benefits:**
- Indexes never accidentally committed to git
- Reusable across multiple clones of same repository
- Clear separation between code and indexes
- Automatic discovery based on git remote

**Migration:**
For existing repositories with local indexes:
```bash
python scripts/move_indexes_to_central.py
```

### For This Repository

This project uses GitHub Actions Artifacts for efficient index sharing, so most users start from a published index baseline instead of rebuilding locally.

```bash
# First time setup - pull latest indexes
mcp-index artifact pull --latest

# After pull, reconcile only your branch/worktree drift
mcp-index artifact sync

# Share your indexes with the team
mcp-index artifact push

# Check sync status
mcp-index artifact sync

# Optional: Install git hooks for automatic sync
mcp-index hooks install
# Now indexes upload automatically on git push
# and download automatically on git pull
```

### For ANY Repository (MCP Index Kit)

Enable portable index management in any repository with zero GitHub compute costs:

#### Quick Install

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/ViperJuice/Code-Index-MCP/main/scripts/install-mcp.sh | bash

# Or via npm
npm install -g mcp-index-kit
mcp-index init
```

#### How It Works

1. **Zero-Cost Architecture**:
   - All indexing happens on developer machines
   - Indexes stored as GitHub Artifacts (free for public repos)
   - Automatic download on clone, upload on push
   - No GitHub Actions compute required

2. **Portable Design**:
   - Single command setup for any repository
   - Auto-detected by MCP servers and tools
   - Works with all 48 supported languages
   - Enable/disable per repository

3. **Usage**:
   ```bash
   # Initialize in your repo
   cd your-repo
   mcp-index init

   # Build index locally
   mcp-index build

   # Push to GitHub Artifacts
   mcp-index push

   # Pull latest index
   mcp-index pull

   # Auto sync
   mcp-index sync
   ```

#### Configuration

##### Semantic Search Configuration

To enable semantic search capabilities, you need a Voyage AI API key. Get one from [https://www.voyageai.com/](https://www.voyageai.com/).

**Method 1: Claude Code Configuration (Recommended)**

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "code-index-mcp": {
      "command": "uvicorn",
      "args": ["mcp_server.gateway:app", "--host", "0.0.0.0", "--port", "8000"],
      "env": {
        "VOYAGE_AI_API_KEY": "your-voyage-ai-api-key-here",
        "SEMANTIC_SEARCH_ENABLED": "true"
      }
    }
  }
}
```

**Method 2: Claude Code CLI**

```bash
claude mcp add code-index-mcp -e VOYAGE_AI_API_KEY=your_key -e SEMANTIC_SEARCH_ENABLED=true -- uvicorn mcp_server.gateway:app
```

**Method 3: Environment Variables**

```bash
export VOYAGE_AI_API_KEY=your_key
export SEMANTIC_SEARCH_ENABLED=true
```

**Method 4: .env File**

Create a `.env` file in your project root:

```
VOYAGE_AI_API_KEY=your_key
SEMANTIC_SEARCH_ENABLED=true
```

**Check Configuration**

Verify your semantic search setup:

```bash
python scripts/cli/mcp_cli.py index check-semantic
```

##### Index Configuration

Edit `.mcp-index.json` in your repository:

```json
{
  "enabled": true,
  "auto_download": true,
  "artifact_retention_days": 30,
  "github_artifacts": {
    "enabled": true,
    "max_size_mb": 100
  }
}
```

See [mcp-index-kit](./mcp-index-kit/) for full documentation


# View artifact details
mcp-index artifact info 12345
```

#### Index Management
```bash
# Check index status
mcp-index index status

# Check compatibility
mcp-index index check-compatibility

# Rebuild indexes locally only if artifact sync cannot catch up
mcp-index index rebuild

# Create backup
python scripts/cli/mcp_cli.py index backup my_backup

# Restore from backup
python scripts/cli/mcp_cli.py index restore my_backup
```

### GitHub Actions Integration

- **Pull Requests**: Validates developer-provided indexes (no rebuilding)
- **Merges to Main**: Promotes validated indexes to artifacts
- **Cost-Efficient**: Uses free GitHub Actions Artifacts storage
- **Auto-Cleanup**: Old artifacts cleaned up after 30 days

### Storage & Cost

- **GitHub Actions Artifacts**: FREE for public repos, included in private repo quotas
- **Retention**: 7 days for PR artifacts, 30 days for main branch
- **Size Limits**: 500MB per artifact (compressed)
- **Automatic Compression**: ~70% size reduction with tar.gz

### Developer Workflow

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/Code-Index-MCP.git
   cd Code-Index-MCP
   ```

2. **Get Latest Indexes**
   ```bash
    gh auth login
    mcp-index artifact pull --latest
   ```
    - This downloads the current full GitHub artifact snapshot.
    - `mcp-index artifact sync` then reconciles only your local branch/worktree drift when incremental catch-up is appropriate.

3. **Make Your Changes**
   - Edit code as normal
    - Indexes update automatically via file watcher

4. **Share Updates**
   ```bash
   # Your indexes are already updated locally
    mcp-index artifact push
   ```

### Embedding Model Compatibility

The system tracks embedding model versions to ensure compatibility:
- **Current model**: `voyage-code-3` (1024 dimensions)
- **Distance metric**: Cosine similarity
- **Auto-detection**: System checks compatibility before download

Multi-profile semantic config can be provided in either:
- `SEMANTIC_PROFILES_JSON` (environment variable), or
- `code-index-mcp.profiles.yaml` (repository root).

### Artifact Strategy

- GitHub artifact pulls are full snapshot downloads, not partial remote patch fetches.
- The current compressed artifact is modest enough that full downloads stay simpler
  than a remote delta protocol.
- Efficiency comes from local incremental indexing after restore:
  - pull the latest full artifact
  - compare the restored artifact commit to local `HEAD`
  - let the watcher or local incremental reindexing reconcile added, modified,
    deleted, and renamed files
- Branch-specific remote artifacts are optional. The default strategy is to use
  the latest `main` artifact as the base and reconcile branch drift locally.

### Easy Semantic Setup (Docker-First)

Run onboarding with automatic local Qdrant startup:

```bash
python scripts/cli/mcp_cli.py setup semantic
```

Settings precedence (highest to lowest):
1. CLI flags (for one command run)
2. Environment variables / `.env`
3. `code-index-mcp.profiles.yaml`
4. `SEMANTIC_PROFILES_JSON`
5. Built-in defaults

Common controls:

```bash
# Preflight checks only
python scripts/cli/mcp_cli.py setup semantic --dry-run

# Strict mode: fail command if semantic stack isn't ready
python scripts/cli/mcp_cli.py setup semantic --strict

# Override local embedding endpoint
python scripts/cli/mcp_cli.py setup semantic --openai-api-base http://127.0.0.1:8001/v1
```

Plugin loading is auto-optimized by default using fast repository language detection:
- `MCP_AUTO_DETECT_LANGUAGES=true`
- `MCP_LANGUAGE_DETECT_MAX_FILES=5000`
- `MCP_LANGUAGE_DETECT_MIN_FILES=2`

For startup-sensitive environments, enable:
- `MCP_FAST_STARTUP=true` (uses lazy plugin loading and skips file watcher startup)

When `MCP_AUTO_DETECT_LANGUAGES=true`, auto-detection takes precedence over `plugins.yaml`.
Set `MCP_AUTO_DETECT_LANGUAGES=false` to force `plugins.yaml` language selection.

For a dual-profile setup (Voyage + local vLLM/Qwen), set:
- `VOYAGE_API_KEY` (or `VOYAGE_AI_API_KEY`)
- `OPENAI_API_BASE` (for example `http://127.0.0.1:8000/v1`)
- `OPENAI_API_KEY` (placeholder accepted for local vLLM setups)

If you use a different embedding model, the system will detect incompatibility and rebuild locally with your configuration.

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

## 📦 Releases & Pre-built Indexes

### Using Pre-built Indexes

For quick setup, download pre-built indexes from our GitHub releases:

```bash
# List available releases
python scripts/download-release.py --list

# Download latest release
python scripts/download-release.py --latest

# Download specific version
python scripts/download-release.py --tag v2024.01.15 --output ./my-index
```

### Creating Releases

Maintainers can create new releases with pre-built indexes:

```bash
# Create a new release (as draft)
python scripts/create-release.py --version 1.0.0

# Create and publish immediately
python scripts/create-release.py --version 1.0.0 --publish
```

### Automatic Index Synchronization

The project includes Git hooks for automatic index synchronization:
- **Pre-push**: Uploads index changes to GitHub artifacts
- **Post-merge**: Downloads compatible indexes after pulling

Install hooks with: `mcp-index hooks install`

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
| Symbol Lookup | <100ms (p95) | ✅ Achieved - All queries < 100ms |
| Code Search | <500ms (p95) | ✅ Achieved - BM25 search < 50ms |
| File Indexing | 10K files/min | ✅ Achieved - 152K files indexed |

### Full-Repo E2E Rerun (2026-03-05)

Latest rerun indexed the full `Code-Index-MCP` repository using:
- Qwen embeddings via Fireworks (`fireworks/qwen3-embedding-8b`)
- Voyage embeddings (`voyage-code-3`)
- Local Qwen embeddings (`Qwen/Qwen3-Embedding-8B` via tailnet endpoint)
- BM25, fuzzy, classic FTS, and hybrid retrieval

| Metric | Result |
|---|---:|
| Files indexed | 1282 |
| Semantic-skipped files (oversized) | 1 |
| MCP query suite Top-1 pass rate | 33.3% |
| MCP query suite Top-3 pass rate | 64.4% |
| Native tools pass rate (`rg`/`grep`/`glob`) | 44.4% |
| Semantic Qwen latency p50 (single query, top-5) | 238.5 ms |
| Semantic Voyage latency p50 (single query, top-5) | 116.68 ms |
| Semantic Local Qwen latency p50 (single query, top-5) | 49.22 ms |
| BM25 latency p50 (single query, top-5) | 46.45 ms |
| Fuzzy latency p50 (single query, top-5) | 10.11 ms |
| Hybrid semantic-intent latency p50 (single query, top-5) | 5093.14 ms |

Known gaps from this rerun:
- `classic` mode still surfaces benchmark/doc artifacts for the semantic-preflight probe.
- `hybrid` mode still has high tail latency and low Top-1 on intent/persistence probes.
- Top-3 improved materially, but Top-1 remains a ranking problem.

Benchmark artifacts:
- `docs/benchmarks/e2e_retrieval_validation_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.json`
- `docs/benchmarks/fullrepo-benchmark-analysis.md`

## 🏗️ Architecture Overview

The system follows C4 model architecture patterns:

- **Workspace Definition**: 100% implemented (architecture/workspace.dsl) - Validated with CLI tools
- **System Context (L1)**: Claude Code integration with MCP sub-agent support fully operational
- **Container Level (L2)**: 8 main containers including enhanced MCP server and user documentation
- **Component Level (L3)**: Plugin system with 48 languages, memory management, and cross-repo coordination
- **Code Level (L4)**: 43 PlantUML diagrams documenting all system components and flows

For detailed architectural documentation, see the [architecture/](architecture/) directory.

## 🗺️ Development Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development plans and current progress.

**Current Status**: v1.0.0 MVP Release
- ✅ **Core Indexing**: SQLite + FTS5 for fast local search
- ✅ **Multi-Language**: 48 languages via tree-sitter integration
- ✅ **MCP Protocol**: Full compatibility with Claude Code and other MCP clients
- ✅ **Performance**: Sub-100ms queries with BM25 optimization
- 🔄 **Index Sync**: Beta support via GitHub Artifacts
- 🔄 **Semantic Search**: Optional feature requiring Voyage AI API

**Recent Improvements**:
- **⚡ Dispatcher Optimization**: Timeout protection and BM25 bypass for reliability
- **🔄 Hybrid Search**: BM25 + semantic search with graceful degradation
- **📊 Result Ranking**: Improved relevance with score normalization
- **🔧 CLI Tools**: Full-featured `mcp-index` command for index management

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

- **Issues**: [GitHub Issues](https://github.com/ViperJuice/Code-Index-MCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ViperJuice/Code-Index-MCP/discussions)

---

<p align="center">Built with ❤️ for the developer community</p>
