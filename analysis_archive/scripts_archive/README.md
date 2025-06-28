# Scripts Archive

This directory contains old test scripts, debug utilities, and setup scripts that were moved from the root directory and scripts/ folder on June 26, 2025 to reduce clutter while preserving development history.

## Directory Structure

### `root_test_scripts/`
Contains test scripts that were previously in the root directory:

**MCP Test Scripts:**
- `test_mcp_*.py` (13 files) - Various iterations of MCP functionality testing
- `test_semantic_*.py` (3 files) - Semantic search testing scripts
- `test_simple_*.py` (2 files) - Simple test variations and quick tests

**Integration Tests:**
- `test_git_*.py` (4 files) - Git integration and version control testing
- `test_docker_setup.py` - Docker environment testing
- `test_qdrant_server.py` - Vector database testing
- `test_minimal_imports.py` - Import dependency testing

**Other Tests:**
- `test_language_detection.py` - Language detection testing
- `test_bm25_*.py` - BM25 search testing
- `test_patched_dispatcher.py` - Dispatcher patch testing

### `root_debug_scripts/`
Contains debugging and utility scripts from the root directory:

**Debug Utilities:**
- `debug_mcp_components.py` - MCP system debugging tools
- `fix_dispatcher_timeout.py` - Dispatcher timeout fixes
- `fix_qdrant_server_mode.py` - Qdrant server mode fixes

**Index Management:**
- `index_all_test_repos.py` - Index all test repositories
- `index_test_repos.py` - Repository indexing script
- `index_test_repos_simple.py` - Simplified repository indexing
- `create_local_index.py` - Local index creation

**Verification:**
- `verify_all_indexes.py` - Index verification utility
- `verify_mcp_fix.py` - MCP fix verification
- `run_git_integration_tests.py` - Git integration test runner
- `sync_indexes_with_git.py` - Git synchronization utility

### `root_setup_scripts/`
Contains old setup and configuration scripts:

**Setup Scripts:**
- `setup-documentation.sh` (49KB) - Large documentation setup script
- `test_mcp_integration.sh` - MCP integration testing script

### `scripts_test_files/`
Contains test and utility scripts from the scripts/ directory:

**Test Scripts:**
- 18+ `test_*.py` files - Various testing utilities and scripts
- Debug and verification scripts moved from scripts/
- Obsolete analysis and testing tools

## Current Active Scripts (Preserved in Root)

The following essential scripts remain in the root directory:

**Development Scripts:**
- `codex-setup.sh` - Updated MCP dependencies setup for Codex development
- `dev.sh` - Development helper script
- `docker-setup.sh` - Docker infrastructure setup
- `docker-build-commands.sh` - Docker build commands

**Current Test Files:**
- Only actively maintained test files remain in root
- Current testing infrastructure in `tests/` directory remains untouched

## Usage Notes

- **Historical Reference**: All archived scripts are preserved for historical reference
- **Development Patterns**: Scripts show evolution of testing and debugging approaches
- **Reusability**: Many utilities can be referenced for similar future development needs
- **Documentation**: Script names and contents provide insight into development challenges solved

## Restoration

If any archived script is needed:
1. Copy from the appropriate archive subdirectory
2. Update dependencies and paths as needed
3. Test in current development environment
4. Consider modernizing based on current project structure

This archive maintains complete development history while keeping the active workspace clean and focused.