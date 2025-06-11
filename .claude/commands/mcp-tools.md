# MCP Tools Quick Reference

Complete guide to using MCP (Model Context Protocol) tools for efficient code exploration.

## Available MCP Tools

### 1. Symbol Lookup
```python
mcp__code-index-mcp__symbol_lookup(symbol="ClassName")
```
- **Purpose**: Find exact definitions of classes, functions, methods, variables
- **Speed**: <100ms
- **Returns**: File path, line number, signature, documentation

### 2. Code Search
```python
mcp__code-index-mcp__search_code(query="pattern", limit=10, semantic=false)
```
- **Purpose**: Search code patterns, text, or concepts
- **Speed**: <500ms
- **Features**: Regex support, semantic search, context snippets

### 3. Index Status
```python
mcp__code-index-mcp__get_status()
```
- **Purpose**: Check index health and statistics
- **Returns**: Indexed files, languages, plugin status

### 4. List Plugins
```python
mcp__code-index-mcp__list_plugins()
```
- **Purpose**: See all 48 supported programming languages
- **Returns**: Language list with plugin details

### 5. Reindex
```python
mcp__code-index-mcp__reindex(path="specific/path")
```
- **Purpose**: Update index after file changes
- **Use**: After major edits or new files

## Search Strategy

### DO Use MCP For:
- Finding symbol definitions
- Searching code patterns
- Understanding code relationships
- Locating usage examples
- Semantic concept searches

### DON'T Use Native Tools For:
- ❌ Grep/find for searching
- ❌ Reading multiple files to find patterns
- ❌ Glob to discover files with content

## Performance Comparison

| Operation | Traditional | MCP | Speedup |
|-----------|------------|-----|---------|
| Find class definition | 45s | 0.1s | 450x |
| Search pattern | 30s | 0.5s | 60x |
| Semantic search | N/A | 1s | ∞ |

## Examples

### Find where a function is used:
```python
mcp__code-index-mcp__search_code(query="process_file\\(", limit=20)
```

### Find all test files:
```python
mcp__code-index-mcp__search_code(query="test_.*\\.py$")
```

### Understand authentication flow:
```python
mcp__code-index-mcp__search_code(query="authentication flow", semantic=true)
```

### Check what's indexed:
```python
mcp__code-index-mcp__get_status()
```

Remember: The MCP index covers 312 files across 48 languages with instant search!