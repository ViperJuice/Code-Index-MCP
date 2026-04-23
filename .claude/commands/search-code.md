# Search Code Patterns

Search for code patterns, text, or concepts across the entire codebase using the MCP index.
Use indexed results as authoritative only when repository readiness is `ready`.
If `search_code` returns `index_unavailable` with
`safe_fallback: "native_search"`, use native `rg`/file search and follow the
readiness remediation, such as `reindex`.

## Usage
```
/search-code <pattern> [options]
```

## Examples
- `/search-code "def process_.*"` - Find all process functions
- `/search-code "class.*Plugin"` - Find all plugin classes
- `/search-code "error handling" semantic` - Semantic search for error handling patterns
- `/search-code "import torch"` - Find all files importing torch

## Options
- `semantic` - Enable semantic search for concept queries
- `limit=N` - Limit results (default: 10)

## Implementation
This command uses `mcp__code-index-mcp__search_code` with these features:
- Regular expression support
- Semantic search with Voyage AI embeddings
- Context snippets with highlighting
- <500ms response time

Ready indexes return ordinary `results: []` for no matches. Non-ready indexes
return `index_unavailable`, where `native_search` is expected until remediation
is complete.
