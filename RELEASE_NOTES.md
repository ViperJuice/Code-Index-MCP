# Changelog for vindex-latest.index-latest.1

## What's Changed

- fix: replace tree_sitter_languages ctypes loading with cross-platform tree_sitter_language_pack (ViperJuice)
- fix: lower flashrank version constraint from >=0.3.0 to >=0.2.0 (ViperJuice)
- feat: cross-repo readiness — profiles fallback, env-var substitution, auto-heal, UX polish (ViperJuice)
- docs: sync documentation with recent feature additions (ViperJuice)
- fix: wire IgnorePatternManager into semantic rebuild to exclude fixtures (ViperJuice)
- fix: correct Qwen vLLM endpoint URL and profile URL priority in settings (ViperJuice)
- feat: wire profile summarization config into ChunkWriter (ViperJuice)
- fix: achieve 17/17 benchmark score with Qwen/Qwen3-Embedding-8B (ViperJuice)
- benchmark: full matrix with working rerankers (flashrank + cross-encoder) (ViperJuice)
- fix: reranker packaging, index pollution, and retrieval quality (ViperJuice)
- fix(hook): resolve mcp-index CLI via .venv/bin when not on PATH (ViperJuice)

## Pull Requests


## Statistics
- Commits: 11
- Contributors: 1
- Files changed: 46


## Feature Highlights
- 🚀 Dynamic plugin loading system
- 📊 Comprehensive monitoring with Prometheus & Grafana
- 🔍 48+ language support via tree-sitter
- 📝 Document processing (Markdown & PlainText)
- 🔐 Security with JWT authentication
- ⚡ High-performance caching system
