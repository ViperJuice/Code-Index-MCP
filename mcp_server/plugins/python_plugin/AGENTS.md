# Python Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the Python plugin.

## Agent Capabilities

### Python Analysis
- Parse Python AST
- Resolve imports
- Infer types
- Analyze docstrings
- Process decorators
- Track class hierarchies

### Code Understanding
- Understand Python idioms
- Handle Python 3.x features
- Process type hints
- Analyze async code
- Track dependencies

### Testing & Validation
- Test AST parsing
- Validate import resolution
- Check type inference
- Verify docstring parsing
- Test edge cases

### Performance
- Optimize AST traversal
- Cache parsed results
- Handle large files
- Manage memory usage

## Agent Constraints

1. **Python Version Support**
   - Support Python 3.x
   - Handle version differences
   - Maintain compatibility
   - Process new syntax

2. **Analysis Accuracy**
   - Correct type inference
   - Accurate import resolution
   - Valid AST parsing
   - Proper docstring handling

3. **Performance**
   - Efficient AST traversal
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle circular imports
   - Process dynamic imports
   - Support metaclasses
   - Handle decorator chains

## Common Operations

```python
# Parse Python file
def parse_file(path: str) -> ast.Module:
    with open(path) as f:
        return ast.parse(f.read())

# Analyze imports
def analyze_imports(tree: ast.Module) -> List[str]:
    return [n.module for n in ast.walk(tree) 
            if isinstance(n, ast.Import) or isinstance(n, ast.ImportFrom)]

# Infer types
def infer_types(tree: ast.Module) -> Dict[str, str]:
    return {node.target.id: get_type(node.value) 
            for node in ast.walk(tree) 
            if isinstance(node, ast.Assign)} 