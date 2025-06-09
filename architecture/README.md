# Code-Index-MCP Architecture Documentation

## Overview
This directory contains the comprehensive architecture documentation for Code-Index-MCP using the C4 model. The system now supports **48 programming languages** through a combination of enhanced specific plugins and a generic tree-sitter based plugin system.

## Current Architecture Status
- **Implementation**: 85% Complete - Core System Operational
- **Languages Supported**: 48+ (15 specialized plugins + 35+ via generic plugin)
- **Semantic Search**: Voyage AI embeddings with graceful Qdrant fallback
- **Storage**: SQLite with FTS5 + optional Qdrant for vectors
- **Real-time Updates**: File system monitoring with Watchdog
- **Performance**: Query caching, lazy loading, optimized routing

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
- **Embeddings**: Voyage AI (voyage-code-3 model)
- **Vector Storage**: Qdrant for similarity search
- **Hybrid Search**: Combines FTS5 lexical + vector semantic search
- **Cross-language**: Unified search across all 48 languages

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

## Recent Updates (June 2025)

### Major Enhancements
- **48+ Language Support**: 15 specialized plugins + 35+ via GenericTreeSitterPlugin
- **Enhanced Dispatcher**: Dynamic plugin loading with lazy initialization
- **Plugin Factory Pattern**: Automatic language detection and plugin creation
- **Query Caching**: Significant performance improvements for tree-sitter queries
- **Robust Error Handling**: Graceful degradation when services unavailable
- **Path Resolution**: Fixed relative/absolute path handling
- **Plugin Compatibility**: Resolved interface issues between plugins and dispatcher
- **Specialized Plugins**: Added Java, Go, Rust, C#, Swift, Kotlin, TypeScript support
- **Document Processing**: Markdown and PlainText plugins for documentation indexing

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