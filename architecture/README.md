# Code-Index-MCP Architecture Guide

## Overview

This architecture follows the C4 model with four levels of abstraction, from high-level system context down to detailed code design. Each level provides increasing detail while maintaining clear boundaries and relationships.

## Navigation Guide

### Starting Point: System Context (Level 1)
**File**: `level1_context.dsl`
- Shows how MCP Server fits in the broader ecosystem
- Identifies external systems and users
- Defines system boundaries and responsibilities

### Container Architecture (Level 2)
**File**: `level2_containers.dsl`
- 14 containers including API Gateway, Dispatcher, Plugin System, Graph Store
- Shows technical architecture and data flow
- Identifies integration points and storage systems

### Component Details (Level 3)
**File**: `level3_mcp_components.dsl`
- Internal structure of each container
- Component interfaces listed in properties
- References to Level 4 PlantUML files for each component

### Code Design (Level 4)
**Directory**: `level4/`
- Detailed PlantUML class diagrams
- Interface definitions with method signatures
- Implementation classes and internal structures
- Cross-component contracts

## Implementation Status

**IMPORTANT**: The current implementation is a prototype that implements ~20% of the designed architecture. See `IMPLEMENTATION_GAP_ANALYSIS.md` for details.

### Actual Implementation Diagrams
For the current implementation state, refer to:
- `level3_mcp_components_actual.dsl` - Shows implementation status with color coding
- `level4/*_actual.puml` - Actual implementation details for each component
- `IMPLEMENTATION_GAP_ANALYSIS.md` - Detailed gap analysis

### Implementation Coverage
- ✅ Basic API, Dispatcher, Python Plugin, Indexers
- ⚠️ File Watcher (partial)
- 🔶 Other language plugins (stubs)
- ❌ Graph Store, Cache, Security, Config, Queue, etc.

## How to Read the Architecture

### Top-Down Approach
1. Start with `level1_context.dsl` to understand the system's purpose
2. Move to `level2_containers.dsl` to see technical building blocks
3. Dive into `level3_mcp_components.dsl` for component details
4. Reference specific `level4/*.puml` files for implementation details

### Component-Focused Approach
1. Find the component of interest in `level3_mcp_components.dsl`
2. Note its `interfaces` and `level4` properties
3. Open the referenced PlantUML file for detailed design
4. Check `shared_interfaces.puml` for cross-cutting concerns

### Interface-Driven Navigation
1. Start with `level4/shared_interfaces.puml` for common contracts
2. Find components that implement specific interfaces
3. Trace relationships through component boundaries
4. Verify interface usage in implementation files

## Key Architectural Decisions

### Dual Storage Strategy
- **SQLite + FTS5**: Fast text search and basic indexing
- **Memgraph**: Graph relationships and context analysis

### Plugin Architecture
- All plugins implement `IPlugin` interface
- Language-specific analysis in separate components
- Dynamic loading and lifecycle management

### Component Interfaces
- Public interfaces marked with `<<Component Interface>>`
- Internal interfaces marked with `<<Internal>>`
- Cross-cutting concerns in shared interfaces

### Async Design
- Methods marked with `<<async>>` for concurrent operations
- Event-driven file watching
- Batch processing for performance

## PlantUML File Guide

### Core Infrastructure
- `shared_interfaces.puml`: Common types, logging, metrics, security
- `api_gateway.puml`: HTTP endpoints, auth, validation
- `dispatcher.puml`: Request routing, plugin coordination

### Plugin System
- `plugin_system.puml`: Plugin framework and lifecycle
- `python_plugin.puml`: Example language plugin implementation
- Additional plugin files for each supported language

### Data Processing
- `indexer.puml`: Code indexing and search
- `graph_store.puml`: Graph database operations
- `file_watcher.puml`: File system monitoring

### Utilities
- `shared_utilities.puml`: Tree-sitter wrapper, common parsing

## Viewing the Diagrams

### Structurizr DSL (Levels 1-3)
```bash
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
```

### PlantUML (Level 4)
- Use PlantUML extension in VS Code
- Or online at http://www.plantuml.com/plantuml
- Or with Docker: `docker run -p 8080:8080 plantuml/plantuml-server`

## Making Changes

### Adding a Component
1. Add to `level3_mcp_components.dsl` with interface properties
2. Create corresponding `level4/component_name.puml`
3. Define public interfaces as `<<Component Interface>>`
4. Update relationships in both DSL and PlantUML

### Adding an Interface
1. Determine if shared or component-specific
2. Add to appropriate PlantUML file
3. Mark with correct stereotype
4. Update implementing classes

### Modifying Relationships
1. Update Structurizr DSL for component relationships
2. Verify interface dependencies in PlantUML
3. Ensure consistency across levels

## Best Practices

### Interface Design
- Keep interfaces focused and cohesive
- Use async methods for I/O operations
- Document exceptions with `throws` or `{exceptions=}`
- Include type parameters for generic interfaces

### Component Boundaries
- Public interfaces form component contracts
- Internal classes should not be referenced externally
- Use dependency injection for cross-component usage
- Maintain clear separation of concerns

### Documentation
- Each interface should have a clear purpose
- Methods should be self-documenting
- Complex logic should have implementation notes
- Keep PlantUML files focused on one component

## Architecture Principles

1. **Local-First**: Core functionality works offline
2. **Plugin Isolation**: Plugins can't affect system stability
3. **Interface Segregation**: Many specific interfaces over few general ones
4. **Async by Default**: Non-blocking operations for scalability
5. **Fail-Safe**: Graceful degradation on component failure