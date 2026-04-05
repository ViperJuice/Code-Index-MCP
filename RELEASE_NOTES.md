# Changelog for v2.15.0-alpha.1

## What's Changed

- fix: remove unused tree_sitter.Language imports (flake8 F401) (ViperJuice)
- fix: isort import ordering in test_mcp_server_cli and test_dispatcher_advanced (ViperJuice)
- chore: remove Kubernetes/Slack deployment scaffolding from CI (ViperJuice)
- fix: black formatting and trivy action version pin (ViperJuice)
- fix: alpha readiness — install workflow, post-commit hook, startup warning, test coverage (ViperJuice)
- fix: 5 production readiness items — semantic vector cleanup, CI, install script (ViperJuice)
- fix: untrack qdrant vector store from git and prevent test suite hangs (ViperJuice)
- fix: filter non-semver tags in release version calculation (ViperJuice)
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
- Commits: 19
- Contributors: 1
- Files changed: 376


## Feature Highlights
- 🚀 Dynamic plugin loading system
- 📊 Comprehensive monitoring with Prometheus & Grafana
- 🔍 48+ language support via tree-sitter
- 📝 Document processing (Markdown & PlainText)
- 🔐 Security with JWT authentication
- ⚡ High-performance caching system
