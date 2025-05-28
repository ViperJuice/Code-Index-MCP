# Python Plugin

This plugin provides Python code indexing and analysis capabilities for the MCP server.

## Features

- AST-based code parsing
- Import resolution
- Type inference
- Docstring analysis
- Decorator handling
- Class hierarchy tracking

## Implementation Details

### Parser
- Uses Python's built-in `ast` module
- Handles Python 3.x syntax
- Supports async/await
- Processes type hints

### Indexer
- Tracks module dependencies
- Maps symbols to definitions
- Records import relationships
- Maintains class hierarchies

### Analysis
- Type inference
- Docstring parsing
- Decorator analysis
- Import resolution

## Common Patterns

1. **Module Analysis**
   ```python
   def analyze_module(path: str) -> Dict:
       with open(path) as f:
           tree = ast.parse(f.read())
       return process_ast(tree)
   ```

2. **Import Resolution**
   ```python
   def resolve_import(module: str) -> str:
       return find_module_path(module)
   ```

3. **Type Inference**
   ```python
   def infer_type(node: ast.AST) -> str:
       return analyze_type_hints(node)
   ```

## Edge Cases

- Circular imports
- Dynamic imports
- Runtime type changes
- Metaclass usage
- Decorator chains 