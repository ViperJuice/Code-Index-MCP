# AI Agent Markdown Documentation Index Generator

You are an AI assistant creating a comprehensive markdown file index optimized for AI coding agents. The output will be referenced in CLAUDE.md stubs (which point to AGENTS.md) to help agents quickly locate, read, consolidate, or remove markdown documentation.

## Agent-Optimized Analysis

1. **File Discovery and Classification**
   - Locate all markdown files (*.md) recursively
   - Classify by type: README, API docs, tutorials, specs, changelogs, etc.
   -- Make sure to annotate whether a file is for AI AGENT CONTEXT or HUMAN CONTEXT
   -- CLAUDE.md stubs, AGENTS.md, items in .cursor/rules, and .claude/commands directories are all AI AGENT CONTEXT
   -- README.md is always HUMAN CONTEXT and it should normally be the only HUMAN CONTEXT markdown file in the codebase
   - Extract primary purpose and target audience from content

2. **Content Fingerprinting**
   - Generate content hash for duplicate detection
   - Extract key topics, code examples, and referenced technologies
   - Identify semantic similarity between files (>70% overlap flagged)

3. **Actionability Assessment**
   For each file, determine:
   - **CURRENT**: Active, referenced, up-to-date content
   - **STALE**: Last modified >6 months with version-specific references
   - **DUPLICATE**: Content similarity >70% with another file
   - **ORPHANED**: No references from code or other docs
   - **OBSOLETE**: References deprecated APIs, tools, or processes
   - **MERGEABLE**: Small file (<500 words) that could be consolidated

4. **Agent Action Mapping**
   For each flagged file, provide specific agent instructions:
   - Files to read for context
   - Files to merge or consolidate
   - Files to delete with confirmation
   - Files requiring content updates

## Output Format (markdown-table-of-contents.md)

```markdown
# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: [TIMESTAMP]

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content

## FILE_INVENTORY

### ACTIVE_DOCS
```
/README.md | purpose:project_overview | refs:high | status:CURRENT | size:1.2kb
/docs/api-reference.md | purpose:api_documentation | refs:medium | status:CURRENT | size:8.4kb  
/docs/installation.md | purpose:setup_guide | refs:high | status:CURRENT | size:2.1kb
```

### MAINTENANCE_REQUIRED
```
/docs/legacy-api.md | purpose:deprecated_api | refs:none | status:OBSOLETE | last_modified:2023-08-15 | action:DELETE
/docs/quick-start.md | purpose:tutorial | refs:low | status:DUPLICATE | similarity:installation.md:85% | action:MERGE_INTO:installation.md
/docs/troubleshooting.md | purpose:support | refs:none | status:ORPHANED | size:0.3kb | action:MERGE_INTO:README.md
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# Delete obsolete files (no references, deprecated content)
rm docs/legacy-api.md
rm docs/old-deployment-notes.md
```

### CONSOLIDATION_TASKS
```
MERGE: docs/quick-start.md → docs/installation.md 
  REASON: 85% content overlap, both cover setup process
  PRESERVE: code examples from quick-start.md
  
MERGE: docs/troubleshooting.md → README.md
  REASON: <500 words, general support info
  LOCATION: Add as "Common Issues" section
```

### CONTENT_UPDATES_NEEDED
```
docs/deployment.md | STALE | References Docker v19, current is v24
docs/api-examples.md | STALE | Uses deprecated v1 endpoints, update to v2
```

## SEMANTIC_CLUSTERS
```
setup_documentation: [README.md, docs/installation.md, docs/quick-start.md]
api_documentation: [docs/api-reference.md, docs/api-examples.md]
deployment_guides: [docs/deployment.md, docs/docker-setup.md]
```

## REFERENCE_MAP
```
# Incoming references (files that link to this doc)
docs/api-reference.md ← [src/api/routes.js:12, README.md:45]
docs/installation.md ← [README.md:23, docs/deployment.md:8]

# Outgoing references (files this doc links to)
README.md → [docs/installation.md, docs/api-reference.md, LICENSE.md]
```

## CONTENT_GAPS
```
# Missing documentation that should exist based on codebase analysis
MISSING: API authentication guide (referenced in code but no docs)
MISSING: Development environment setup (mentioned in README but no detailed guide)
MISSING: Contribution guidelines (CONTRIBUTING.md referenced but doesn't exist)
```

## AGENT_PROMPTS
```
# When creating new documentation:
"Before creating new docs, check SEMANTIC_CLUSTERS and FILE_INVENTORY to avoid duplication"

# When modifying existing docs:
"Check REFERENCE_MAP to understand dependencies before major changes"

# For maintenance tasks:
"Execute IMMEDIATE_CLEANUP actions first, then handle CONSOLIDATION_TASKS"
```
```

## Implementation Instructions

1. **Check for existing markdown-table-of-contents.md**
   - If exists, compare timestamps and update incrementally
   - If missing, create complete new index

2. **Content Analysis Depth**
   - Parse first 500 words of each file for classification  
   - Use file path and name patterns for type detection
   - Extract referenced file names, URLs, and version numbers

3. **Similarity Detection**
   - Compare file content using semantic similarity
   - Flag files with >70% content overlap
   - Prioritize smaller files for merger into larger ones

4. **Reference Tracking**
   - Scan all markdown files for internal links
   - Check code files for documentation references
   - Build bidirectional reference map

5. **Action Generation**
   - Generate specific bash commands for file operations
   - Provide merge instructions with content preservation notes
   - Include confirmation prompts for destructive actions

## Agent Usage Examples

```markdown
# In CLAUDE.md stub, reference this index:
"Before modifying documentation, consult markdown-table-of-contents.md for current file inventory and planned changes"

# For cleanup tasks:
"Use AGENT_ACTIONS section from markdown-table-of-contents.md to identify files for removal or consolidation"

# For new documentation:
"Check SEMANTIC_CLUSTERS in markdown-table-of-contents.md to determine optimal file placement"
```

This command generates a structured, actionable index that AI agents can parse and execute automatically, with clear instructions for maintenance, consolidation, and cleanup tasks.