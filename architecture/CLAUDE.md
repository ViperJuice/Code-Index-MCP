# MCP Server Architecture

This directory contains C4 model architecture diagrams that document the system's structure and components.

## Diagram Levels

1. **Level 1 (Context)**
   - System context and boundaries
   - External dependencies
   - User interactions
   - System scope

2. **Level 2 (Containers)**
   - Application containers
   - Data stores
   - External systems
   - Communication patterns

3. **Level 3 (Components)**
   - Internal components
   - Dependencies
   - Responsibilities
   - Interfaces

## File Structure

- `level1_context.dsl`: System context diagram
- `level2_containers.dsl`: Container diagram
- `level3_mcp_components.dsl`: Component diagram

## Viewing Diagrams

Use Structurizr Lite to view the diagrams:
```bash
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
```

## Architecture Principles

1. Local-first design
2. Plugin-based extensibility
3. Language-agnostic core
4. Optional cloud sync
5. Security by isolation 