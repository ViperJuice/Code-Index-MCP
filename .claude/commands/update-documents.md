# update-documents

Updates and synchronizes all documentation files including AGENTS.md, CLAUDE.md, cursor rules, and other markdown files to ensure consistency and reflect the current state of the codebase.

## What it does

This command performs a comprehensive documentation update:

1. **Reviews AGENTS.md files** across all directories to ensure they provide accurate, directory-specific guidance
2. **Updates CLAUDE.md** to reflect current project configuration and features
3. **Synchronizes .cursor/rules** to match current architecture and integrations
4. **Consolidates markdown files** by:
   - Identifying outdated or redundant documentation
   - Merging relevant content into README.md
   - Removing duplicate information
   - Organizing remaining docs into logical structure
5. **Updates README.md** to accurately describe the current state of the project

## When to use

Run this command when:
- Major features have been added or removed
- Project architecture has changed significantly
- You notice inconsistencies between documentation and code
- Before major releases to ensure docs are current
- After integrating new services or providers

## Steps performed

1. **Scan all AGENTS.md files**
   - Root directory rules
   - Source code organization (src/)
   - App Router patterns (src/app/)
   - API route standards (src/app/api/)
   - Component guidelines (src/components/)
   - Service-specific rules (enrichment, workers)

2. **Update cursor IDE rules**
   - ai-integration.mdc (BYOK providers, Pinecone, Neo4j)
   - database.mdc (multi-database coordination)
   - Security and TypeScript rules
   - React and Next.js patterns

3. **Analyze markdown documentation**
   - Keep: Essential references (API-REFERENCE.md, ENVIRONMENT-VARIABLES.md)
   - Merge: Architecture and feature descriptions into README
   - Delete: Outdated roadmaps and temporary notes

4. **Synchronize CLAUDE.md**
   - Update technology stack
   - Refresh command list
   - Update deployment checklist
   - Add new features and integrations

5. **Update README.md**
   - Current feature set
   - Accurate architecture diagram
   - Updated deployment instructions
   - Current development status

## Documentation structure after update

```
/
├── README.md (comprehensive project overview)
├── CLAUDE.md (Claude Code configuration)
├── CHANGELOG.md
├── SECURITY.md
├── TROUBLESHOOTING.md
├── docs/
│   ├── API-REFERENCE.md
│   ├── DEPLOYMENT-GUIDE.md
│   ├── ENVIRONMENT-VARIABLES.md
│   ├── TESTING-GUIDE.md
│   ├── NEO4J-SETUP.md
│   └── NEO4J-QUICK-START.md
├── ai_docs/ (tool-specific documentation)
├── .cursor/rules/ (IDE configuration)
└── AGENTS.md files (hierarchical throughout codebase)
```

## Best practices

- Run `npm run check` after documentation updates
- Verify examples in docs still work with current code
- Ensure environment variable lists are complete
- Update deployment guides with new requirements
- Keep command documentation in sync with actual implementations