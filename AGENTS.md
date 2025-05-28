# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with this codebase.

## Agent Capabilities

### Code Understanding
- Parse and understand multiple programming languages
- Navigate plugin architecture
- Interpret C4 architecture diagrams
- Understand local-first principles

### Code Modification
- Add new language plugins
- Extend API endpoints
- Update architecture diagrams
- Modify indexing strategies

### Testing & Validation
- Run language-specific tests
- Validate plugin implementations
- Check architecture consistency
- Verify local-first compliance

## Agent Constraints

1. **Local-First Priority**
   - Always prefer local indexing over cloud solutions
   - Maintain offline functionality
   - Minimize external dependencies

2. **Plugin Architecture**
   - Follow plugin base class requirements
   - Maintain language-specific conventions
   - Preserve plugin isolation

3. **Security**
   - No hardcoded credentials
   - Respect file system permissions
   - Validate all external inputs

4. **Performance**
   - Optimize for local indexing speed
   - Minimize memory footprint
   - Efficient file watching

## Common Commands

```bash
# Start the server
uvicorn mcp_server.gateway:app --reload

# View architecture
docker run --rm -p 8080:8080 -v "$(pwd)/architecture":/usr/local/structurizr structurizr/lite

# Run tests
pytest
``` 