# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with this codebase.

## Current State

**⚠️ PROTOTYPE STATUS**: This is an early-stage prototype with significant implementation gaps. Most functionality is stubbed or partially implemented.

### What's Actually Implemented
- ✅ Basic FastAPI gateway with `/symbol` and `/search` endpoints
- ✅ Plugin base class structure
- ✅ Python plugin with partial Jedi integration (basic functionality only)
- ✅ TreeSitter wrapper utility class
- ✅ Architecture documentation (C4 model)

### What's NOT Implemented (Stubs/Placeholders)
- ❌ Dispatcher (stub returning "not found")
- ❌ File watcher (empty implementation)
- ❌ Local storage/indexing (no persistence)
- ❌ All language plugins except Python (empty stubs)
- ❌ Fuzzy and semantic indexers (placeholders)
- ❌ Cloud sync (stub only)
- ❌ Actual code indexing functionality

## Agent Capabilities

### Code Understanding
- Parse and understand the intended architecture
- Navigate plugin structure (though most are stubs)
- Interpret C4 architecture diagrams
- Understand the gap between design and implementation

### Code Modification
- Add new language plugin stubs
- Extend API endpoint definitions
- Update architecture diagrams
- Implement missing functionality

### Testing & Validation
- Run basic test files (`test_python_plugin.py`, `test_tree_sitter.py`)
- Validate TreeSitter functionality
- Check architecture consistency
- Identify implementation gaps

## Agent Constraints

1. **Implementation Gaps**
   - Be aware that most components are not functional
   - The dispatcher doesn't route to plugins properly
   - No actual indexing or storage occurs
   - Search functionality returns empty results

2. **Local-First Priority**
   - Design for local indexing (when implemented)
   - Maintain offline functionality goals
   - Minimize external dependencies

3. **Plugin Architecture**
   - Follow plugin base class requirements
   - Maintain language-specific conventions
   - Preserve plugin isolation design

4. **Security**
   - No hardcoded credentials
   - Respect file system permissions
   - Validate all external inputs

5. **Performance**
   - Consider indexing speed in future implementations
   - Plan for efficient memory usage
   - Design efficient file watching

## Common Commands

```bash
# Start the server (runs but most features don't work)
uvicorn mcp_server.gateway:app --reload

# View architecture diagrams
docker run --rm -p 8080:8080 -v "$(pwd)/architecture":/usr/local/structurizr structurizr/lite

# Run available tests
python test_python_plugin.py  # Tests basic Python plugin functionality
python test_tree_sitter.py    # Tests TreeSitter wrapper

# Note: No pytest tests exist yet
```

## Development Priorities

1. **Implement the Dispatcher** - Currently returns "not found" for everything
2. **Complete Python Plugin** - Add actual indexing beyond basic Jedi calls
3. **Add Local Storage** - Implement SQLite with FTS5 for persistence
4. **Implement File Watcher** - Make it actually monitor file changes
5. **Create Working Tests** - Add pytest suite for all components 