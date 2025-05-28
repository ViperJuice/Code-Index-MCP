# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server core implementation.

## Agent Capabilities

### Server Management
- Start/stop the FastAPI server
- Monitor server health
- Manage plugin lifecycle
- Handle file watching

### Plugin Development
- Create new language plugins
- Extend existing plugins
- Debug plugin issues
- Optimize plugin performance

### API Development
- Add new endpoints
- Modify existing endpoints
- Update request/response models
- Implement authentication

### File System
- Monitor file changes
- Handle file events
- Manage indexing state
- Coordinate cloud sync

## Agent Constraints

1. **Plugin Safety**
   - Validate plugin inputs
   - Handle plugin errors gracefully
   - Prevent plugin crashes
   - Maintain plugin isolation

2. **Performance**
   - Minimize indexing overhead
   - Efficient file watching
   - Optimize search queries
   - Manage memory usage

3. **Security**
   - Validate all API inputs
   - Sanitize file paths
   - Handle permissions properly
   - Secure plugin loading

4. **Reliability**
   - Maintain index consistency
   - Handle file system errors
   - Recover from crashes
   - Preserve data integrity

## Common Operations

```python
# Start server
uvicorn mcp_server.gateway:app --reload

# Add new plugin
class MyPlugin(PluginBase):
    def index(self, path: str) -> Dict:
        # Implementation
        pass

# Monitor files
watcher = FileWatcher()
watcher.watch("/path/to/code")
``` 