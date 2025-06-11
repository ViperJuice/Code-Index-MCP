# CLAUDE.md Memory File Template
# Location: /docs/templates/claude-memory-template.md

This template shows the standardized format for CLAUDE.md files after consolidation.

## Standardized CLAUDE.md Format

```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.

# important-instruction-reminders
- Follow complexity ordering in Next Steps
- Check architecture alignment before implementing
- Update implementation status after completing tasks
```

## Key Features

1. **Pure Pointer**: No custom guidance mixed with navigation
2. **@imports**: Uses Claude Code's import syntax
3. **Clear Direction**: Points to consolidated guidance
4. **Minimal Content**: Reduces confusion and duplication

## Migration Process

### Before (Mixed Content):
```markdown
# Claude Agent Instructions
- Always use JWT tokens with 15min expiry
- Validate all inputs
See AGENTS.md for more details
- Use dependency injection
```

### After (Pure Pointer):
```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
[Rest of template...]
```

Custom content moves to AGENTS.md with proper organization.

## Directory-Specific Context

For subdirectories, the template remains the same but references are relative:

```markdown
# Claude Agent Instructions
> **AI Agents:** All guidance has been consolidated into `AGENTS.md` in this directory.

See @AGENTS.md for complete instructions.
See @/ROADMAP.md for implementation priorities.
See @/architecture/workspace.dsl for system design.

# important-instruction-reminders
- Context-specific reminders for this directory
- Follow parent directory guidelines
- Check module-specific architecture
```

## Benefits

1. **Consistency**: All CLAUDE.md files follow same format
2. **No Duplication**: Guidance lives in one place
3. **Clear Navigation**: AI agents know where to look
4. **Easy Updates**: Change guidance in AGENTS.md only
5. **Platform Agnostic**: Works with any AI coding assistant
