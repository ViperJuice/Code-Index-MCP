# MCP Server (Local-first Code Indexer)

Modular, extensible local-first indexer for enhancing Claude Code and other LLMs.

## Features
- Local-first code index (Tree-sitter, LSP, etc.)
- Plugin architecture (Python, Dart, JS, C/C++, HTML/CSS)
- Cloud sync and embeddings fallback (optional)
- Structurizr C4 diagrams

## Quickstart
```bash
uvicorn mcp_server.gateway:app --reload
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
```
