# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-01-30 (Enhanced with plugin implementation guides)

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content
- CLAUDE.md files are stubs that point to AGENTS.md - always read AGENTS.md for actual content

## FILE_INVENTORY

### ACTIVE_DOCS - AI AGENT CONTEXT
```
/CLAUDE.md | purpose:ai_agent_navigation | refs:high | status:CURRENT | size:302b | context:AI_AGENT
/AGENTS.md | purpose:ai_agent_instructions | refs:high | status:CURRENT | size:3.5kb | context:AI_AGENT
/MARKDOWN_INDEX.md | purpose:comprehensive_doc_catalog | refs:high | status:CURRENT | size:9.8kb | context:AI_AGENT
/markdown-table-of-contents.md | purpose:ai_agent_doc_index | refs:high | status:CURRENT | size:6.4kb | context:AI_AGENT
/architecture/CLAUDE.md | purpose:ai_agent_navigation | refs:high | status:CURRENT | size:302b | context:AI_AGENT
/architecture/AGENTS.md | purpose:architecture_agent_notes | refs:high | status:CURRENT | size:3.9kb | context:AI_AGENT
/mcp_server/CLAUDE.md | purpose:ai_agent_navigation | refs:high | status:CURRENT | size:302b | context:AI_AGENT
/mcp_server/AGENTS.md | purpose:server_agent_notes | refs:high | status:CURRENT | size:2.8kb | context:AI_AGENT
/.claude/commands/*.md | purpose:ai_command_definitions | refs:medium | status:CURRENT | size:varies | context:AI_AGENT
/mcp_server/plugins/*/CLAUDE.md | purpose:ai_agent_navigation | refs:medium | status:CURRENT | size:302b each | context:AI_AGENT
/mcp_server/plugins/*/AGENTS.md | purpose:plugin_implementation_guides | refs:high | status:ENHANCED | size:7-12kb | context:AI_AGENT
```

### ACTIVE_DOCS - HUMAN CONTEXT
```
/README.md | purpose:project_overview | refs:high | status:CURRENT | size:18.7kb | context:HUMAN
/ROADMAP.md | purpose:development_roadmap | refs:high | status:CURRENT | size:19.2kb | context:HUMAN
/CHANGELOG.md | purpose:release_history | refs:medium | status:CURRENT | size:3.7kb | context:HUMAN
/CONTRIBUTING.md | purpose:contribution_guide | refs:medium | status:CURRENT | size:6.4kb | context:HUMAN
/SECURITY.md | purpose:security_policy | refs:low | status:CURRENT | size:2.5kb | context:HUMAN
/TROUBLESHOOTING.md | purpose:common_issues | refs:medium | status:CURRENT | size:9.5kb | context:HUMAN
/PHASE1_COMPLETION_SUMMARY.md | purpose:milestone_report | refs:low | status:CURRENT | size:3.2kb | context:HUMAN
/DOCUMENTATION_UPDATE_SUMMARY.md | purpose:cleanup_report | refs:low | status:CURRENT | size:11.5kb | context:HUMAN

/architecture/README.md | purpose:architecture_overview | refs:high | status:CURRENT | size:21.8kb | context:HUMAN
/architecture/data_model.md | purpose:database_schema | refs:high | status:CURRENT | size:18.9kb | context:HUMAN
/architecture/performance_requirements.md | purpose:performance_specs | refs:medium | status:CURRENT | size:12.1kb | context:HUMAN
/architecture/security_model.md | purpose:security_design | refs:medium | status:CURRENT | size:15.3kb | context:HUMAN
/architecture/IMPLEMENTATION_GAP_ANALYSIS.md | purpose:gap_analysis | refs:medium | status:CURRENT | size:30.2kb | context:HUMAN
/architecture/ARCHITECTURE_ALIGNMENT_REPORT.md | purpose:alignment_report | refs:low | status:CURRENT | size:1.2kb | context:HUMAN
/architecture/ARCHITECTURE_FIXES.md | purpose:fix_documentation | refs:low | status:CURRENT | size:10.1kb | context:HUMAN

/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_instructions | refs:medium | status:CURRENT | size:14.5kb | context:HUMAN
/docs/api/API-REFERENCE.md | purpose:api_documentation | refs:high | status:CURRENT | size:19.8kb | context:HUMAN
/docs/configuration/ENVIRONMENT-VARIABLES.md | purpose:config_reference | refs:medium | status:CURRENT | size:5.2kb | context:HUMAN
/docs/development/TESTING-GUIDE.md | purpose:testing_instructions | refs:medium | status:CURRENT | size:8.7kb | context:HUMAN

/ai_docs/*.md | purpose:technology_references | refs:medium | status:CURRENT | size:210kb total | context:HUMAN
```

### MAINTENANCE_REQUIRED
```
None - Recent cleanup removed obsolete files as documented in DOCUMENTATION_UPDATE_SUMMARY.md
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# No immediate cleanup required - recent documentation cleanup already completed
```

### CONSOLIDATION_TASKS
```
# All CLAUDE.md files are intentional stubs - DO NOT CONSOLIDATE
# Each points to its corresponding AGENTS.md file for actual content
```

### CONTENT_UPDATES_NEEDED
```
/ROADMAP.md | ACTIVE | Update completion percentages after Phase 1 completion (~25% now)
/mcp_server/plugins/*/AGENTS.md | ENHANCED | Comprehensive implementation guides added for all 5 stub plugins
```

## SEMANTIC_CLUSTERS
```
ai_agent_context: [All CLAUDE.md files, All AGENTS.md files, .claude/commands/*.md]
project_management: [README.md, ROADMAP.md, CHANGELOG.md, CONTRIBUTING.md]
architecture_docs: [architecture/*.md, All dual architecture pattern files]
implementation_guides: [docs/*.md, DEPLOYMENT-GUIDE.md, TESTING-GUIDE.md]
technology_references: [ai_docs/*.md - 17 files covering various tools/libraries]
plugin_documentation: [mcp_server/plugins/*/AGENTS.md, mcp_server/plugins/*/CLAUDE.md]
```

## REFERENCE_MAP
```
# Key Reference Patterns
All CLAUDE.md → AGENTS.md (consistent navigation pattern)
README.md → [architecture/README.md, docs/*, CONTRIBUTING.md]
ROADMAP.md → [architecture/*.md, IMPLEMENTATION_GAP_ANALYSIS.md]
architecture/*_actual.* ← → architecture/*.* (dual architecture pattern)

# Technology Dependencies
ai_docs/tree_sitter_overview.md ← Python plugin implementation
ai_docs/sqlite_fts5_overview.md ← storage/sqlite_store.py
ai_docs/fastapi_overview.md ← gateway.py implementation
```

## CONTENT_GAPS
```
# Missing documentation that should exist based on codebase analysis
MISSING: Plugin development guide (referenced in ROADMAP but doesn't exist)
MISSING: Performance benchmarks documentation (specs exist but no actuals)
MISSING: Migration guide for stub plugins to full implementations
MISSING: Dispatcher initialization detailed guide
```

## DOCUMENTATION_PATTERNS
```
# CLAUDE.md Stub Pattern (All 302 bytes, identical content)
- Every major directory has CLAUDE.md → AGENTS.md navigation
- Consistent message: "Do not modify this file directly"
- Total: 18 CLAUDE.md files, all pointing to corresponding AGENTS.md

# Dual Architecture Pattern
- *_actual.dsl/puml files track implementation (~20% complete)
- Original files show target architecture (100% designed)
- Clear separation between aspiration and reality

# Plugin Documentation Pattern
- Each plugin has CLAUDE.md (stub) + AGENTS.md (content)
- Python plugin: fully documented and implemented
- Other 5 plugins: documentation stubs awaiting implementation
```

## AGENT_PROMPTS
```
# When working with CLAUDE.md files:
"CLAUDE.md files are navigation stubs - always read the corresponding AGENTS.md for actual content"

# When creating new documentation:
"Before creating new docs, check SEMANTIC_CLUSTERS and existing AGENTS.md files"

# When implementing stub plugins:
"Update the corresponding plugin's AGENTS.md file with implementation notes"

# For architecture work:
"Check both ideal and *_actual files to understand design vs implementation gap"
```

## FILE_SIZE_SUMMARY
```
Total Documentation: ~650KB
- AI Agent Context: ~45KB (18 files)
- Human Documentation: ~605KB (50 files)
- Largest file: architecture/IMPLEMENTATION_GAP_ANALYSIS.md (30.2KB)
- Smallest files: All CLAUDE.md stubs (302 bytes each)
```

## IMPLEMENTATION_STATUS
```
Based on documentation analysis:
- Core System: ~20% implemented
- Core System: ~25% implemented (Phase 1 complete)
- Python Plugin: 100% implemented ✓
- Other Language Plugins: 0% implemented (comprehensive guides added)
- Architecture: 100% designed, ~25% implemented
- Documentation: Recently cleaned, enhanced with plugin guides
```