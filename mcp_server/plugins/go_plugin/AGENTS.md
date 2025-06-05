# Go Plugin Agent Instructions

This plugin handles Go language parsing and indexing with the following capabilities:

## Features
- Function declarations (func keyword)
- Interface definitions  
- Struct types and methods
- Package declarations and imports
- Go modules (go.mod parsing)
- Type declarations
- Constants and variables

## Performance Target
- Parse Go files within 100ms

## Implementation Notes
- Uses tree-sitter-go for AST parsing
- Supports go.mod dependency tracking
- Handles Go-specific syntax patterns