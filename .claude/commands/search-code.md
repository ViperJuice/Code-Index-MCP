# Search Code Patterns

Search for code patterns, text, or concepts across the entire codebase using the MCP index.

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

Never use grep - MCP search is 100x faster and understands code semantics!