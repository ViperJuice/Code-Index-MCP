# Documentation Commands Implementation Guide
# Location: /docs/tools/documentation-commands.md

## Overview

This guide provides implementation details for the AI-optimized documentation maintenance system, consisting of two complementary commands that work together to keep documentation aligned with code.

## Command Summary

### `/project:analyze-docs`
Performs comprehensive documentation analysis and generates actionable insights.

**Key Functions:**
- Discovers and classifies all documentation
- Analyzes architecture alignment (C4 levels)
- Detects platform-specific AI guidance
- Identifies stale framework documentation
- Scores roadmap items by complexity
- Generates `markdown-table-of-contents.md`

### `/project:update-docs`
Executes documentation updates based on analysis while respecting governance rules.

**Key Functions:**
- Plans updates before execution
- Migrates custom guidance between files
- Enhances roadmap with interface-first approach
- Documents but doesn't modify architecture
- Updates stale documentation via web search
- Consolidates multi-platform AI guidance

## Architecture & Governance

### Governance Modes

**DOCUMENT_ONLY Mode:**
- Triggered when existing architecture detected
- Preserves all architectural decisions
- Only documents divergences
- Never modifies .dsl or .puml files
- Creates `implementation-status.md`

**CREATE_NEW Mode:**
- Only for brand new projects
- Safe to create initial structure
- Generates starter templates
- Sets up documentation hierarchy

### Architecture Alignment

The commands understand C4 architecture model:
- **Levels 1-3**: Structurizr DSL (`workspace.dsl`)
- **Level 4**: PlantUML diagrams (`*.puml`)

Alignment tracking:
- Maps implementation to architecture
- Calculates coverage percentages
- Documents divergences without judgment
- Provides recommendations for architects

## AI Platform Integration

### Supported Platforms

**Claude Code:**
- Memory file: `CLAUDE.md`
- Uses @import syntax
- Directory-scoped

**Codex:**
- Guidance file: `AGENTS.md`
- Markdown format
- Directory-scoped

**Cursor:**
- Rules: `.cursor/rules/*.mdc`
- YAML/MDC format
- Repository-scoped

### Smart Consolidation

Instead of duplicating content:
1. Reads all platform files
2. Identifies common guidance
3. Deduplicates intelligently
4. Generates unified content
5. Formats for each platform

Result: Single source of truth with platform-specific formatting.

## Implementation Details

### File Discovery

Dynamic discovery approach:
```bash
# Find all markdown files
find . -name "*.md" -type f

# Classify by context
# - AI_AGENT_CONTEXT: CLAUDE.md, AGENTS.md
# - HUMAN_CONTEXT: README.md
# - MIXED_CONTEXT: Other .md files

# Find architecture files
find . -name "*.dsl" -o -name "*.puml"
```

### Complexity Scoring

Roadmap items scored 1-5 based on:
- Integration requirements
- Migration complexity
- Refactoring scope
- Architectural impact

### Next Steps Generation

Creates interface-first development plan:
1. Container interfaces (external-facing)
2. Module interfaces (boundaries)
3. Internal interfaces (integration)
4. Class design (structure)
5. Implementation (logic)

Each level includes:
- File mappings
- Complexity ratings
- Parallel execution options
- AI documentation needs

## Workflow Integration

### Development Iteration Cycle

```mermaid
graph TD
    A[Start Iteration] --> B[/project:analyze-docs]
    B --> C[Review Analysis]
    C --> D[/project:update-docs]
    D --> E[AI Development]
    E --> F[Code Changes]
    F --> G[End Iteration]
    G --> A
```

### Continuous Improvement

Each cycle:
- Discovers new patterns
- Updates documentation
- Improves alignment
- Reduces technical debt

## Configuration & Customization

### Project-Specific Settings

No configuration files needed - commands adapt to:
- Project structure
- Programming languages
- Architecture patterns
- Team conventions

### Extension Points

To support new platforms:
1. Add discovery logic in analyze phase
2. Define consolidation rules
3. Specify output format
4. Test with sample files

## Best Practices

### Do's
- Run analysis before major changes
- Review alignment plans before executing
- Preserve backup directories
- Document architectural decisions
- Keep roadmap Next Steps current

### Don'ts
- Don't modify architecture without architect approval
- Don't delete backup files immediately
- Don't skip analysis phase
- Don't ignore divergence warnings

## Troubleshooting

### Common Scenarios

**"No architecture found"**
- Normal for new projects
- CREATE_NEW mode activates
- Templates will be generated

**"Divergences detected"**
- Expected as code evolves
- Document for architect review
- Don't auto-fix

**"Stale documentation"**
- Common for fast-moving frameworks
- Web search updates available
- Manual update option provided

### Debug Mode

For detailed output:
```bash
# Run with verbose logging
set -x
/project:analyze-docs
set +x
```

## Performance Considerations

- First run may be slower (full discovery)
- Subsequent runs use cached structure
- Large codebases: expect 30-60s analysis
- Updates are incremental when possible

## Security & Privacy

- All operations are local
- No data sent externally
- Web search only for public docs
- Respects .gitignore patterns

## Future Enhancements

Potential improvements:
- Git integration for change detection
- Automated PR generation
- Architecture drift metrics
- Team analytics dashboard

## Support & Contribution

These commands are part of your project's documentation system. To contribute improvements:
1. Test changes thoroughly
2. Update this guide
3. Maintain backward compatibility
4. Document new features

Remember: The goal is to make documentation maintenance effortless while preserving human decision-making for architectural choices.
