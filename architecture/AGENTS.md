# MCP Server Architecture Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server architecture.

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

## Agent Constraints

1. **C4 Model Compliance**
   - Follow C4 model conventions
   - Maintain level separation
   - Use correct notation
   - Keep diagrams focused

2. **Documentation**
   - Keep docs up to date
   - Document decisions
   - Explain rationale
   - Maintain clarity

3. **Consistency**
   - Align with code
   - Match implementation
   - Update all levels
   - Maintain relationships

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