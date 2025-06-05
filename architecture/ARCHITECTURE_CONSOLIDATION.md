# Architecture Consolidation

## Overview

The architecture diagrams have been consolidated from three separate DSL files into a single, comprehensive Structurizr DSL workspace file that includes all levels of the Code-Index MCP server architecture.

## Combined Architecture File

**File**: `code-index-mcp-architecture.dsl`

This single file contains:
- **Level 1**: System Context - Shows external systems and users
- **Level 2**: Container Architecture - Shows major containers/services
- **Level 3**: Component Details - Shows internal components within containers

## Architecture Views

The consolidated DSL provides the following views:

1. **System Context** (`MCPSystemContext`)
   - Shows how the MCP server integrates with AI assistants
   - External systems: Claude/LLMs, code repositories, optional services

2. **Container Architecture** (`MCPContainers`)
   - All containers in the system
   - Color-coded by reusability:
     - 🔴 Red: New MCP-specific components
     - 🟢 Green: Reusable existing components
     - 🟡 Yellow: Components requiring modification

3. **Component Views**:
   - `ProtocolComponents` - MCP protocol handler internals
   - `ResourceComponents` - Resource manager internals
   - `ToolComponents` - Tool manager internals
   - `DispatcherComponents` - Existing dispatcher components
   - `StorageComponents` - Storage layer components

4. **Complete Architecture** (`CompleteArchitecture`)
   - System landscape view showing all elements

## Key Benefits of Consolidation

1. **Single Source of Truth** - One file contains the entire architecture
2. **Consistent Styling** - Unified color scheme and styling across all levels
3. **Relationship Clarity** - All relationships between elements are defined in one place
4. **Easier Maintenance** - Update architecture in a single location
5. **Better Navigation** - Clear hierarchy from system to component level

## Validation

The consolidated DSL has been validated using Structurizr CLI:
```bash
./tools/structurizr.sh validate -workspace architecture/code-index-mcp-architecture.dsl
```

## Exporting Diagrams

To export the architecture diagrams:
```bash
# Export to PlantUML
./tools/structurizr.sh export -workspace architecture/code-index-mcp-architecture.dsl -format plantuml -output architecture/exports

# Export to Mermaid
./tools/structurizr.sh export -workspace architecture/code-index-mcp-architecture.dsl -format mermaid -output architecture/exports
```

## Legacy Files

The original separate DSL files are preserved for reference:
- `level1_mcp_context.dsl` - Original system context
- `level2_mcp_containers.dsl` - Original container view
- `level3_mcp_components.dsl` - Original component view

These can be removed once the team is comfortable with the consolidated version.

## Color Coding Reference

- **Red** (#E74C3C): New components that must be built
- **Green** (#27AE60): Existing components that can be reused as-is
- **Yellow/Orange** (#F39C12): Components requiring modification
- **Purple** (#9B59B6): Adapter components wrapping existing functionality
- **Blue** (#3498DB): Interface/abstract components
- **Gray** (#999999): External systems
- **Light Gray** (#ECF0F1): Future/planned components