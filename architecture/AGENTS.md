# MCP Server Architecture Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server architecture.

## Agent Capabilities

### Architecture Understanding
- Interpret C4 model diagrams
- Understand system boundaries
- Analyze component relationships
- Evaluate architecture decisions

### Documentation
- Update architecture diagrams
- Maintain documentation
- Add new views
- Document decisions

### Analysis
- Review architecture changes
- Validate design decisions
- Check consistency
- Identify improvements

### Visualization
- Generate diagrams
- Update views
- Maintain consistency
- Export formats

## Agent Constraints

1. **C4 Model Compliance**
   - Follow C4 model conventions
   - Maintain level separation
   - Use correct notation
   - Keep diagrams focused

2. **Documentation**
   - Keep docs up to date
   - Document decisions
   - Explain rationale
   - Maintain clarity

3. **Consistency**
   - Align with code
   - Match implementation
   - Update all levels
   - Maintain relationships

4. **Quality**
   - Clear diagrams
   - Accurate representation
   - Complete documentation
   - Valid DSL syntax

## Common Operations

```bash
# View diagrams
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite

# Update diagram
# Edit .dsl files
# Refresh browser
``` 