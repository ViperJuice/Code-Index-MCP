# Haskell Plugin Agent Instructions

This plugin provides comprehensive support for Haskell code analysis, including:

## Key Features
- Type signatures and type class detection
- Data type and newtype declarations  
- Pattern matching analysis
- Module imports and exports
- Language pragmas
- Literate Haskell support
- Cabal/Stack project file parsing

## Symbol Types
The plugin recognizes and extracts:
- Functions with type signatures
- Data types (data, newtype, type synonyms)
- Type classes and instances
- Module declarations with exports
- Import statements (qualified, hiding, aliases)
- Infix operators with precedence
- Type and data families
- GADTs and other advanced type features

## Usage Notes
- The plugin automatically detects literate Haskell files (.lhs)
- Supports both Bird-style (>) and LaTeX-style code blocks
- Handles multi-line type signatures correctly
- Parses Cabal, Stack, and package.yaml project files
- Extracts dependencies, exposed modules, and build targets

## Testing
Run comprehensive tests with:
```bash
pytest mcp_server/plugins/haskell_plugin/test_haskell_plugin.py
```