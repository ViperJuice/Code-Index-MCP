# Code-Index-MCP Architecture Documentation

## Overview
This directory contains the comprehensive architecture documentation for Code-Index-MCP using the C4 model. The system now supports **48 programming languages** through a combination of enhanced specific plugins and a generic tree-sitter based plugin system.

## Current Architecture Status
- **Implementation**: 95% Complete - PRODUCTION READY
- **Languages Supported**: 48 (13 specialized plugins + 35 via generic plugin)
- **Semantic Search**: Voyage AI embeddings with Qdrant server/file mode
- **Storage**: SQLite with FTS5 + optional Qdrant for vectors
- **Real-time Updates**: File system monitoring with Watchdog
- **Performance**: Sub-100ms queries with timeout protection & BM25 bypass
- **Index Management**: Centralized storage at `~/.mcp/indexes/`
- **Git Integration**: Repository tracking and synchronization

## Recent Architectural Updates (January 2025)

### Local Index Storage
The system now uses local index storage architecture:

- **Default Location**: Indexes stored at `.indexes/{repo_hash}/{branch}_{commit}.db` relative to MCP server
- **Repository Isolation**: Each repository gets a unique hash-based directory
- **Version Management**: Multiple versions per branch supported
- **Automatic Discovery**: MCP server automatically finds indexes based on git remote
- **Migration Tool**: Simple script to move existing indexes to local storage
- **Configurable**: Can override location with MCP_INDEX_STORAGE_PATH environment variable

Benefits:
- Indexes never accidentally committed to git (added to .gitignore)
- Self-contained MCP server with all data in one place
- Easy to backup or move entire MCP installation
- No dependency on home directory or user-specific paths
- Simplified deployment and distribution

## Recent Architectural Updates (June 10, 2025)

### Enhanced Search Pipeline
The system now includes a sophisticated multi-stage search pipeline:

1. **Initial Retrieval**: BM25, semantic, and fuzzy search run in parallel
2. **Result Fusion**: Reciprocal rank fusion combines results
3. **Reranking**: Optional reranking stage for relevance improvement
4. **Metadata Preservation**: All original metadata maintained through pipeline

### Security Architecture
New security layers for index sharing:

- **Gitignore Filtering**: Automatic exclusion of sensitive files
- **Pattern-Based Security**: Support for .mcp-index-ignore patterns
- **Audit Logging**: Track all excluded files for compliance
- **Secure Export Pipeline**: Filtered database creation before sharing

### Contextual Embeddings
Advanced document understanding capabilities:

- **Adaptive Chunking**: Token-based sizing instead of character limits
- **Context Windows**: Include surrounding text for better understanding
- **Hierarchical Structure**: Preserve document relationships
- **Performance**: 35-67% reduction in retrieval failures

## Architecture Documentation Structure

### 📄 Unified C4 Model
- **workspace.dsl** - Complete Structurizr DSL workspace containing all C4 levels:
  - Level 1: System Context
  - Level 2: Container Diagram
  - Level 3: Component Diagrams
  - Level 4: Code (see PlantUML diagrams)
  - Dynamic Views: Indexing and Search flows
  - Deployment View: Production setup

### 📋 Supporting Documentation
- **data_model.md** - Data structures, schemas, and storage design
- **performance_requirements.md** - Performance specifications and benchmarks
- **security_model.md** - Security architecture and considerations
- **document_processing_architecture.md** - Document processing plugin architecture
- **specialized_plugins_architecture.md** - Specialized language plugin details
- **path_management_architecture.md** - 🆕 Path management and file tracking system
- **portable_index_architecture.md** - Index artifact portability and sharing
- **index_artifact_architecture.md** - GitHub artifact-based index distribution
- **AGENTS.md** - AI agent-specific architecture guidance
- **CLAUDE.md** - Navigation stub for AI agents

### 📊 Level 4 - Code Diagrams (PlantUML)
The `level4/` directory contains detailed class and interface diagrams:

#### Core System Components
- **api_gateway_actual.puml** - FastAPI/MCP gateway implementation
- **dispatcher_actual.puml** - Request routing and caching
- **enhanced_dispatcher.puml** - Enhanced dispatcher with dynamic loading
- **indexer_actual.puml** - Indexing engine details
- **storage_actual.puml** - SQLite and Qdrant integration
- **file_watcher.puml** - File system monitoring

#### Plugin System
- **plugin_system_actual.puml** - Plugin architecture overview
- **plugin_factory.puml** - Dynamic plugin creation system
- **generic_plugin.puml** - GenericTreeSitterPlugin architecture
- **python_plugin_actual.puml** - Enhanced Python plugin
- **js_plugin_actual.puml** - JavaScript/TypeScript plugin
- **c_plugin_actual.puml** - C language plugin
- **shared_interfaces.puml** - Common plugin interfaces
- **shared_utilities.puml** - Utility classes

## Key Architectural Components

### 1. Language Support Architecture
```
┌─────────────────────────────────────────────────────┐
│                 Plugin Framework                      │
├─────────────────────────────────────────────────────┤
│  Plugin Factory → Language Registry → Plugin Cache   │
├─────────────────┬─────────────────┬─────────────────┤
│ Enhanced Plugins │ Specialized     │ Generic Plugin  │
├─────────────────┼─────────────────┼─────────────────┤
│ • Python        │ • Java          │ • Ruby          │
│ • JavaScript    │ • Go            │ • PHP           │
│ • C/C++         │ • Rust          │ • Scala         │
│ • Dart          │ • C#            │ • Haskell       │
│ • HTML/CSS      │ • Swift         │ • Elixir        │
│                 │ • Kotlin        │ • Erlang        │
│                 │ • TypeScript    │ • F#            │
│                 │                 │ • ... 28 more   │
├─────────────────┼─────────────────┼─────────────────┤
│ Document Plugins│                 │                 │
├─────────────────┤                 │                 │
│ • Markdown      │                 │                 │
│ • PlainText     │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

### 2. Plugin Factory Pattern
- **Dynamic Loading**: Plugins loaded on-demand based on file type
- **Caching**: Plugin instances cached for performance
- **Configuration**: Language-specific settings in registry
- **Fallback**: Generic tree-sitter plugin for unsupported extensions

### 3. Semantic Search Integration
- **Embeddings**: Voyage AI (voyage-code-3 model) with contextual enhancements
- **Vector Storage**: Qdrant for similarity search
- **Hybrid Search**: Combines FTS5 lexical + vector semantic search
- **Cross-language**: Unified search across all 48 languages
- **Contextual Understanding**: Language-specific context improves search relevance
  - Type-aware embeddings for better code understanding
  - Import/dependency context for related code discovery
  - Framework-specific patterns for domain-aware search
  - Cross-file relationships for comprehensive results

### 4. Performance Optimizations
- **Lazy Loading**: Parsers loaded only when needed
- **Query Caching**: AST queries cached per language
- **Parallel Processing**: Multi-threaded indexing
- **Incremental Updates**: Only changed files re-indexed

## Viewing the Architecture

### Structurizr DSL
To view the C4 diagrams from workspace.dsl:

1. **Using Structurizr Lite** (recommended):
   ```bash
   docker run -it --rm -p 8080:8080 \
     -v /app/architecture:/usr/local/structurizr \
     structurizr/lite
   ```
   Then open http://localhost:8080

2. **Using Structurizr CLI**:
   ```bash
   structurizr-cli export -workspace workspace.dsl -format plantuml
   ```

3. **Online**: Upload workspace.dsl to https://structurizr.com/dsl

### PlantUML Diagrams
View the Level 4 diagrams in the `level4/` directory using:
- PlantUML extension in VS Code
- Online at http://www.plantuml.com/plantuml
- Command line: `plantuml level4/*.puml`

## Architecture Principles

1. **Plugin-Based Extensibility**: Easy to add new language support
2. **Local-First Processing**: All indexing happens locally
3. **Performance at Scale**: Handles large codebases efficiently
4. **Language Agnostic Core**: Same interfaces for all languages
5. **Semantic Understanding**: AI-powered code comprehension

## Project Organization Updates (January 2025)

### Directory Structure Refactoring
The project underwent a major directory reorganization for improved maintainability:

- **Root Directory Consolidation**: Reduced from 44+ files to ~30 essential files
- **Organized Scripts**: Scripts moved to logical subdirectories:
  - `scripts/cli/` - Command-line interfaces (mcp_cli.py, mcp_server_cli.py)
  - `scripts/utilities/` - Utility scripts for indexing, analysis, and management
  - `scripts/development/` - Development tools (scaffolding, setup)
  - `scripts/testing/` - Test runners and validation scripts
- **Docker Organization**: All Docker files moved to `docker/` with subdirectories:
  - `docker/compose/` - Docker Compose configurations by environment
  - `docker/dockerfiles/` - All Dockerfile variants
- **Test Organization**: Test fixtures and data moved to `tests/fixtures/`
- **Documentation**: Comprehensive docs in `docs/` with categorized subdirectories

See [docs/PROJECT_STRUCTURE.md](../docs/PROJECT_STRUCTURE.md) for the complete structure.

### Test Suite Maintenance
Following the directory refactoring, the test suite was updated to maintain full compatibility:
- Fixed import paths for moved modules
- Added missing `language` property to IPlugin interface
- Created DocumentProcessingError exception class  
- Corrected method signatures for store_file calls
- Updated test expectations to match plugin behavior

## Recent Updates (June 2025)

### Dispatcher Performance Fixes (June 24)
- **Timeout Protection**: Added 5-second timeout to prevent plugin loading hangs
- **BM25 Bypass**: Direct SQLite search when plugins unavailable (< 100ms)
- **Simple Dispatcher**: New lightweight alternative for BM25-only deployments
- **Qdrant Server Mode**: Automatic server/file mode switching
- **Git Synchronization**: Index metadata tracks commits and branches
- **Environment Configuration**: 
  - `MCP_USE_SIMPLE_DISPATCHER=true` for lightweight mode
  - `MCP_PLUGIN_TIMEOUT=5` to configure timeout
  - `QDRANT_USE_SERVER=true` for server mode

### Major Enhancements (June 10)
- **48 Language Support**: 13 specialized plugins + 35 via GenericTreeSitterPlugin
- **Enhanced Dispatcher**: Dynamic plugin loading with lazy initialization
- **Plugin Factory Pattern**: Automatic language detection and plugin creation
- **Query Caching**: Significant performance improvements for tree-sitter queries
- **Robust Error Handling**: Graceful degradation when services unavailable
- **Path Resolution**: Fixed relative/absolute path handling
- **Plugin Compatibility**: Resolved interface issues between plugins and dispatcher
- **Specialized Plugins**: Added Java, Go, Rust, C#, Swift, Kotlin, TypeScript support
- **Document Processing**: Markdown and PlainText plugins for documentation indexing
- **Contextual Embeddings**: Language-aware embeddings that understand code relationships
  - Type context from specialized plugins enhances search accuracy
  - Import graphs and dependencies improve result relevance
  - Framework-specific patterns enable domain-aware searches
  - Cross-file relationships provide comprehensive results
- **Ignore Pattern Support**: Comprehensive filtering across all operations
  - MCP reindex now uses enhanced dispatcher's index_directory method
  - File watcher applies ignore patterns in real-time
  - Secure index export filters gitignored files automatically

### Production-Ready Features
- **Dynamic Loading**: Plugins loaded on-demand for optimal performance
- **Fallback Mechanisms**: System continues working even without external services
- **Cross-Language Search**: Unified search across all supported languages
- **Real-World Testing**: Validated with large codebases (httpie, lodash, etc.)

## Next Steps

For extending the architecture:
1. Review workspace.dsl for system overview
2. Check data_model.md for storage schemas
3. See performance_requirements.md for benchmarks
4. Refer to AGENTS.md for AI integration patterns