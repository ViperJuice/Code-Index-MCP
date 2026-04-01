# Ignore Patterns Behavior

## Overview

The MCP Indexer uses an **"index everything, filter on share"** approach to provide the best of both worlds: comprehensive local search capabilities while maintaining security when sharing indexes.

## How It Works

### 🔍 Local BM25/FTS5 Index (SQLite)
**ALL files are indexed** for lexical search, including:
- `.env` files with environment variables and secrets
- API keys and credentials (`.key`, `.pem` files)
- Private configuration files
- Files listed in `.gitignore`
- Build outputs, node_modules, etc.

This gives you full search capabilities across your entire codebase locally.

**Example**: You can search for `DATABASE_PASSWORD` and find it in your `.env` file.

### 🧠 Semantic Index (Qdrant vectors)
The semantic (vector) index **respects `.gitignore` and `.mcp-index-ignore`** at build
time. Files matching those patterns are not embedded into Qdrant. This prevents large
external fixture directories (e.g. `test_workspace/`) from polluting vector search results
and causing unnecessary embedding API spend during rebuilds.

### 🔒 Sharing/Exporting (GitHub Artifacts)
**Sensitive files are automatically filtered out** before sharing:
- Files matching `.gitignore` patterns are excluded
- Files matching `.mcp-index-ignore` patterns are excluded  
- The shared index NEVER contains sensitive data
- Other developers get a clean, safe index without secrets

**Example**: When you push an index to GitHub Artifacts, `.env` files are automatically excluded.

## Why This Approach?

1. **🚀 Local Power**: Search everything in your codebase, including configuration and secrets
2. **🔐 Share Safely**: Sensitive data is automatically removed from shared indexes
3. **👥 Team Friendly**: Other developers can pull clean indexes without your local secrets
4. **🎯 Best Developer Experience**: No need to manually exclude files from local search

## Pattern Files

### `.gitignore`
Standard git ignore patterns that are automatically respected during export:
```
.env
*.key
*.pem
node_modules/
__pycache__/
build/
dist/
```

### `.mcp-index-ignore`  
Additional patterns specifically for MCP index sharing:
```
# External fixture repos (excluded from semantic index at build time)
test_workspace/
test_repos/
vendor/
third_party/

# Generated code
baml_client/
*_pb2.py

# Large files
*.zip
*.tar.gz

# Temporary files
*.tmp
temp/
```

**Note**: These patterns do NOT affect BM25/FTS5 local indexing — you can still search
these files lexically. They only exclude files from the Qdrant semantic (vector) index.

## Security Guarantees

Even though sensitive files are indexed locally, they are:
- ✅ Never included in shared index artifacts
- ✅ Never uploaded to GitHub
- ✅ Only searchable on your local machine
- ✅ Automatically filtered by `SecureIndexExporter`

## Common Use Cases

### Local Development
```bash
# Index everything, including .env files
mcp reindex

# Search for database configuration (finds results in .env)
mcp search "DATABASE_URL"
```

### Sharing with Team
```bash
# Create index artifact (automatically excludes .env, secrets, etc.)
mcp index push

# Team member pulls clean index (no secrets included)
mcp index pull
```

### Debugging Production Issues
```bash
# Search across ALL files including logs and configs
mcp search "error 500" --include-all

# Find API keys (only works locally)
mcp search "API_KEY"
```

## Best Practices

1. **Review Before Sharing**: Always check what files are being excluded:
   ```bash
   mcp index status --show-excluded
   ```

2. **Use .mcp-index-ignore**: Add patterns for files that shouldn't be in shared indexes but aren't in .gitignore:
   ```
   # Large test fixtures
   tests/fixtures/large_*.json
   
   # Personal notes
   personal_notes.md
   TODO_private.md
   ```

3. **Security Audit**: Periodically run the security analyzer:
   ```bash
   python analyze_gitignore_security.py
   ```

## Comparison with Other Approaches

| Approach | Local Search | Shared Indexes | Security |
|----------|--------------|----------------|-----------|
| **MCP (Current)** | ✅ All files | ✅ Filtered | ✅ Automatic |
| Exclude at Index | ❌ Limited | ✅ Safe | ✅ Manual |
| Include Everything | ✅ All files | ❌ Unsafe | ❌ Risk |

## Implementation Details

The filtering happens in `SecureIndexExporter`:
1. Loads patterns from `.gitignore` and `.mcp-index-ignore`
2. Creates a filtered copy of the SQLite database
3. Excludes all files matching the patterns
4. Creates an audit log of excluded files
5. Packages the clean index for sharing

This ensures that sensitive data never leaves your machine while maintaining full local search capabilities.