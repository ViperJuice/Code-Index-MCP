# MCP Tools Quick Reference

Complete guide to using MCP (Model Context Protocol) tools for efficient code exploration.
Indexed search is authoritative only when repository readiness is `ready`. If
`search_code` or `symbol_lookup` returns `index_unavailable` with
`safe_fallback: "native_search"`, use native search and follow the remediation,
such as `reindex`.

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
- **Returns**: Indexed files, languages, plugin status, repository readiness

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

### Use MCP Indexed Search When Readiness Is `ready` For:
- Finding symbol definitions
- Searching code patterns
- Understanding code relationships
- Locating usage examples
- Semantic concept searches

### Use Native Search For:
- Non-ready repositories
- Query responses with `code: "index_unavailable"`
- Any response carrying `safe_fallback: "native_search"`
- Work while `reindex` or other remediation is pending

## Performance Comparison

| Operation | Native search | Ready MCP index | Speedup |
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

Remember: check readiness first; ready MCP indexes are fast, and
`index_unavailable` means `native_search` is the safe fallback.
