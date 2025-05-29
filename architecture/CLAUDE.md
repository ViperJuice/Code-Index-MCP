# MCP Server Architecture

This directory contains C4 model architecture diagrams and PlantUML code-level documentation that comprehensively document the system's structure from high-level context down to detailed code design.

**IMPORTANT**: The project is currently ~20% implemented. Architecture files show both the target design and actual implementation state.

## Architecture Levels

### Level 1 (Context)
- System context and boundaries
- External dependencies
- User interactions  
- System scope
- Performance SLAs

### Level 2 (Containers)
- Application containers
- Data stores (SQLite, Memgraph)
- External systems
- Communication patterns
- Operational components

### Level 3 (Components)
- Internal components with interface definitions
- Component relationships  
- Responsibilities
- Public interfaces listed in properties
- Note: Both `level3_mcp_components.dsl` (target) and `level3_mcp_components_actual.dsl` (current) exist

### Level 4 (Code/PlantUML)
- Detailed UML class diagrams
- Interface definitions
- Implementation classes
- Internal structures
- Cross-component contracts

## File Structure

### Structurizr DSL Files
- `level1_context.dsl`: System context diagram
- `level2_containers.dsl`: Container diagram with 14 containers
- `level3_mcp_components.dsl`: Component diagram with interface annotations

### PlantUML Code Design (Level 4)
- `level4/shared_interfaces.puml`: Cross-cutting concerns and shared contracts
- `level4/api_gateway.puml`: Gateway, authentication, validation components (target design)
- `level4/api_gateway_actual.puml`: Current minimal implementation
- `level4/dispatcher.puml`: Request routing and result aggregation (target)
- `level4/dispatcher_actual.puml`: Current basic implementation
- `level4/plugin_system.puml`: Plugin framework and lifecycle management (target)
- `level4/plugin_system_actual.puml`: Current implementation (Python only)
- `level4/indexer.puml`: Indexing engine and search optimization (target)
- `level4/indexer_actual.puml`: Current implementation (merged into plugins)
- `level4/python_plugin.puml`: Python language analysis implementation (target)
- `level4/python_plugin_actual.puml`: Current Tree-sitter + Jedi implementation
- `level4/graph_store.puml`: Memgraph integration and graph analysis (NOT IMPLEMENTED)
- `level4/file_watcher.puml`: File system monitoring (skeleton exists, doesn't trigger indexing)
- `level4/shared_utilities.puml`: Tree-sitter wrapper and common utilities

### Supporting Documentation
- `data_model.md`: SQLite schema and Memgraph graph model (PLANNED, not implemented)
- `performance_requirements.md`: Performance targets and SLAs
- `security_model.md`: Security architecture and policies (PLANNED, not implemented)
- `IMPLEMENTATION_GAP_ANALYSIS.md`: Gap analysis between target and current state
- `ARCHITECTURE_FIXES.md`: Known architecture issues and fixes
- `ARCHITECTURE_ALIGNMENT_REPORT.md`: Auto-generated alignment report

## Viewing Diagrams

Use Structurizr Lite to view the diagrams:
```bash
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
```

## Architecture Principles

1. Local-first design
2. Plugin-based extensibility (currently only Python plugin works)
3. Language-agnostic core
4. Optional cloud sync (NOT IMPLEMENTED)
5. Security by isolation (NOT IMPLEMENTED)

## Current Implementation Status

- ✅ Basic FastAPI gateway with `/symbol` and `/search` endpoints
- ✅ Basic dispatcher (no caching or optimization)
- ✅ Python plugin with Tree-sitter parsing and Jedi integration
- ✅ File watcher skeleton (doesn't trigger indexing)
- ❌ Graph store (Memgraph)
- ❌ Local storage (SQLite/FTS5)
- ❌ Caching layer (Redis)
- ❌ Authentication and security
- ❌ Cloud sync
- ❌ Other language plugins (C, C++, JS, Dart, HTML/CSS are stubs) 