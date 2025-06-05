# TOML Plugin Agent Instructions

## Overview
The TOML plugin provides comprehensive support for TOML (Tom's Obvious, Minimal Language) files with special handling for Cargo.toml and pyproject.toml files.

## Key Features

### Symbol Extraction
- **Tables/Sections**: `[section]` headers
- **Table Arrays**: `[[array]]` repeated blocks
- **Key-Value Pairs**: Configuration variables
- **Inline Tables**: `{ key = "value" }` compact definitions
- **Nested Structures**: Dotted keys and hierarchical tables

### Special File Support

#### Cargo.toml (Rust)
- Package metadata (name, version, edition)
- Dependencies with features
- Dev dependencies
- Build dependencies
- Feature flags
- Workspace configuration

#### pyproject.toml (Python)
- Project metadata (PEP 621)
- Build system configuration
- Tool configurations (black, mypy, ruff, etc.)
- Poetry sections
- Optional dependencies

### Advanced Features
- Full key path extraction for nested values
- Multi-line string detection
- Date/time value recognition
- Array and inline table parsing
- Comment extraction as documentation

## Usage Guidelines

### When to Use
- Indexing Rust projects (Cargo.toml)
- Indexing Python projects (pyproject.toml)
- Parsing application configuration files
- Analyzing dependency trees
- Extracting build configurations

### Symbol Types
- `MODULE`: Table sections `[section]`
- `CLASS`: Table arrays `[[array]]`
- `VARIABLE`: Key-value pairs
- `FIELD`: Inline tables
- `PROPERTY`: Nested keys with paths
- `IMPORT`: Dependencies in Cargo.toml

### Metadata Fields
- `full_path`: Complete dotted path to nested values
- `cargo_field`: Specific Cargo.toml fields
- `is_dependency`: Marks dependency entries
- `feature`: Feature flag information
- `tool`: Tool configuration sections

## Best Practices

1. **Path Navigation**: Use full_path metadata to navigate nested structures
2. **Dependency Analysis**: Check is_dependency metadata for package dependencies
3. **Configuration Extraction**: Use section metadata to group related settings
4. **Feature Detection**: Look for feature metadata in Cargo.toml files

## Integration Points

- Works with Tree-sitter for accurate parsing
- Falls back to regex patterns when needed
- Caches results for performance
- Supports incremental updates

## Testing
The plugin includes comprehensive tests for:
- Basic TOML parsing
- Cargo.toml specifics
- pyproject.toml specifics
- Nested structures
- Inline tables
- Array handling