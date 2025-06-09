# Code-Index-MCP Architecture Agent Configuration

This file defines the capabilities and constraints for AI agents working with the Code-Index-MCP architecture documentation. The system now supports 48 programming languages through enhanced and generic plugins.

## ARCHITECTURE_STATUS
**C4 Model Maturity**: ADVANCED (95% complete)
**Implementation Alignment**: 85% (Strong alignment between design and code)
**Last Updated**: 2025-06-08
**Complexity Score**: 5/5 (Distributed system with ML/AI, 136k lines, 48 plugins)

### C4_LEVELS_STATUS
- **Workspace Definition**: architecture/workspace.dsl | status:CURRENT | c4_levels:4 | implementation_match:85%
- **System Context (L1)**: Claude Code integration | status:CURRENT | systems:3 | external_deps:2
- **Container Level (L2)**: 6 main containers | status:CURRENT | containers:[API,Dispatcher,Plugins,Index,Storage,Watcher]
- **Component Level (L3)**: Plugin system detail | status:CURRENT | components:15 | well_defined:YES
- **Code Level (L4)**: 22 PlantUML diagrams | status:CURRENT | coverage:90% | implementation_match:85%

## Agent Capabilities

### Architecture Understanding
- Interpret C4 model diagrams
- Understand system boundaries
- Analyze component relationships
- Evaluate architecture decisions

### Documentation
- Update architecture diagrams
- Maintain documentation
- Add new views
- Document decisions

### Analysis
- Review architecture changes
- Validate design decisions
- Check consistency
- Identify improvements

### Visualization
- Generate diagrams
- Update views
- Maintain consistency
- Export formats

## C4_MODEL_COMMANDS

### STRUCTURIZR_DSL_COMMANDS
```bash
# View architecture diagrams locally
docker run --rm -p 8080:8080 -v "$(pwd)/architecture":/usr/local/structurizr structurizr/lite

# Validate DSL syntax
docker run --rm -v "$(pwd)/architecture":/workspace structurizr/cli validate /workspace/workspace.dsl

# Export diagrams
docker run --rm -v "$(pwd)/architecture":/workspace -v "$(pwd)/output":/output structurizr/cli export /workspace/workspace.dsl
```

### PLANTUML_COMMANDS
```bash
# Generate PNG diagrams
find architecture/level4 -name "*.puml" -exec plantuml {} \;

# Generate SVG diagrams  
find architecture/level4 -name "*.puml" -exec plantuml -tsvg {} \;

# Validate PlantUML syntax
find architecture/level4 -name "*.puml" -exec plantuml -syntax {} \;
```

## ARCHITECTURE_ALIGNMENT_STATUS

### ALIGNED_COMPONENTS (85% implementation match)
- ✅ Plugin Factory pattern → GenericTreeSitterPlugin + 48 languages implemented
- ✅ Enhanced Dispatcher → Caching, routing, error handling operational  
- ✅ Storage abstraction → SQLite + FTS5 with optional Qdrant integration
- ✅ API Gateway → FastAPI with all documented endpoints functional
- ✅ File Watcher → Real-time monitoring with Watchdog implemented

### RECENTLY_IMPLEMENTED (validation needed)
- ⚠️ Document Processing plugins → Markdown/PlainText created, testing in progress
- ⚠️ Specialized Language plugins → 7 plugins implemented, production validation needed
- ⚠️ Semantic Search integration → Voyage AI integrated with graceful fallback

### ARCHITECTURE_WORK_NEEDED
- Missing PlantUML for newer components (document processing, specialized plugins)
- Some diagrams need updates to match latest implementations
- Performance benchmark results architecture documentation needed

## DEVELOPMENT_ITERATION_GUIDANCE

### IMMEDIATE_ARCHITECTURE_TASKS
1. **Update PlantUML diagrams** - Match recent implementations (Complexity: 2)
2. **Document processing architecture** - Add Level 4 diagrams (Complexity: 3)
3. **Validate alignment** - Ensure architecture matches 85% implementation (Complexity: 2)

### ARCHITECTURE_ALIGNMENT_MAINTENANCE
- Update implementation percentages in workspace.dsl when features are completed
- Maintain PlantUML diagrams when new components are added
- Ensure C4 levels remain synchronized with actual system structure

## Current Architecture State

1. **Unified C4 Model**
   - All levels in `workspace.dsl` (Structurizr DSL)
   - System Context, Container, Component views
   - Dynamic views for indexing and search flows
   - Deployment view for production setup

2. **48-Language Support**
   - 6 enhanced plugins (Python, JS, C, C++, Dart, HTML/CSS)
   - 42 generic plugins via tree-sitter
   - Plugin factory with lazy loading
   - Language registry for configuration

3. **Key Components**
   - FastAPI gateway for MCP protocol
   - Enhanced dispatcher with caching
   - SQLite + FTS5 for symbol storage
   - Qdrant for vector embeddings
   - Voyage AI for semantic search

## Agent Constraints

1. **Architecture Updates**
   - Update `workspace.dsl` for C4 changes
   - Keep PlantUML diagrams in `level4/` current
   - Maintain consistency across all views
   - Document rationale for changes

2. **Language Support**
   - New languages via generic plugin
   - Enhanced plugins for complex languages
   - Update language registry configuration
   - Test with real-world repositories

3. **Performance Considerations**
   - Lazy loading for all plugins
   - Query caching per language
   - Parallel processing support
   - Memory limits for parsers

4. **Quality**
   - Clear diagrams
   - Accurate representation
   - Complete documentation
   - Valid DSL syntax

## ESSENTIAL_COMMANDS

```bash
# Architecture Visualization
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
# Then open: http://localhost:8080

# PlantUML Generation (if needed)
plantuml architecture/level4/*.puml

# DSL Validation
# Edit .dsl files and check browser refresh for syntax errors

# Architecture Documentation
find architecture/ -name "*.dsl" -o -name "*.puml" | sort
```

## CODE_STYLE_PREFERENCES

```dsl
# Structurizr DSL Style (discovered patterns)
# - Use descriptive identifiers
# - Consistent indentation (2 spaces)
# - Group related elements
# - Document relationships clearly

workspace "MCP Server" {
    model {
        person = person "Developer" "Uses Code-Index-MCP"
        softwareSystem = softwareSystem "Code-Index-MCP" {
            // Components follow snake_case
            apiGateway = container "API Gateway"
            dispatcher = container "Dispatcher"
        }
    }
}

# PlantUML Style (discovered patterns)
@startuml
!theme plain
skinparam componentStyle rectangle
skinparam linetype ortho
@enduml
```

## ARCHITECTURAL_PATTERNS

```bash
# C4 Model Levels
# Level 1: System Context - External interactions
# Level 2: Container - High-level technology choices  
# Level 3: Component - Internal structure
# Level 4: Code - Implementation details (PlantUML)

# Architecture File Patterns
level1_context.dsl          # System boundaries
level2_containers.dsl       # Container architecture
level3_mcp_components.dsl   # Component details
level4/*.puml              # Detailed component designs

# Dual Pattern: Planned vs Actual
api_gateway.puml           # Planned architecture
api_gateway_actual.puml    # Current implementation
```

## NAMING_CONVENTIONS

```bash
# DSL Files: level{N}_{purpose}.dsl
level1_context.dsl
level2_containers.dsl  
level3_mcp_components.dsl

# PlantUML Files: {component}.puml, {component}_actual.puml
api_gateway.puml, api_gateway_actual.puml
dispatcher.puml, dispatcher_actual.puml
plugin_system.puml, plugin_system_actual.puml

# Identifiers: camelCase in DSL
apiGateway, pluginSystem, storageLayer

# Documentation: {topic}.md
data_model.md, security_model.md, performance_requirements.md
```

## DEVELOPMENT_ENVIRONMENT

```bash
# Docker: Required for Structurizr visualization
docker --version

# PlantUML: Optional for direct diagram generation
java -jar plantuml.jar

# Browser: View Structurizr diagrams
# Navigate to: http://localhost:8080

# File Organization
architecture/
├── level1_context.dsl
├── level2_containers.dsl  
├── level3_mcp_components.dsl
├── level4/
│   ├── {component}.puml
│   └── {component}_actual.puml
└── *.md
```

## TEAM_SHARED_PRACTICES

```bash
# Architecture Updates: Always update both planned and actual diagrams
# DSL Editing: Validate syntax by checking browser refresh
# Documentation: Keep architecture docs in sync with implementation
# Version Control: Commit architecture changes with code changes

# Diagram Guidelines:
# - Clear component boundaries
# - Consistent styling across diagrams
# - Document technology choices
# - Show data flow and dependencies

# Architecture Reviews:
# - Verify planned vs actual alignment
# - Check for missing components
# - Validate security boundaries
# - Ensure scalability considerations
``` 