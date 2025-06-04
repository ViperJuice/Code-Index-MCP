# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-06-03 13:35 UTC

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content

## FILE_INVENTORY

### ACTIVE_DOCS
```
/README.md | purpose:project_overview | refs:high | status:CURRENT | size:25.0kb | context:HUMAN
/CONTRIBUTING.md | purpose:contribution_guide | refs:medium | status:CURRENT | size:6.9kb | context:HUMAN
/ROADMAP.md | purpose:implementation_roadmap | refs:medium | status:CURRENT | size:18.6kb | context:HUMAN
/CLAUDE.md | purpose:ai_agent_pointer | refs:high | status:CURRENT | size:0.7kb | context:AI_AGENT
/AGENTS.md | purpose:ai_agent_config | refs:high | status:CURRENT | size:7.2kb | context:AI_AGENT
/DOCUMENTATION_INDEX.md | purpose:doc_catalog | refs:low | status:CURRENT | size:11.8kb | context:HUMAN
/DIFF_BASED_EDITING_GUIDE.md | purpose:technical_guide | refs:low | status:CURRENT | size:7.5kb | context:AI_AGENT
/DYNAMIC_PROMPT_GUIDE.md | purpose:prompt_system_guide | refs:low | status:CURRENT | size:6.6kb | context:AI_AGENT
/SEMANTIC_SEARCH_GUIDE.md | purpose:search_implementation | refs:low | status:CURRENT | size:6.2kb | context:HUMAN
/STRUCTURED_OUTPUTS_ANALYSIS.md | purpose:structured_output_analysis | refs:low | status:CURRENT | size:15.7kb | context:HUMAN
/STRUCTURED_OUTPUTS_SUMMARY.md | purpose:implementation_summary | refs:low | status:CURRENT | size:6.4kb | context:HUMAN
/SECURITY.md | purpose:security_policy | refs:medium | status:NEW | size:2.7kb | context:HUMAN
/TROUBLESHOOTING.md | purpose:troubleshooting_guide | refs:medium | status:NEW | size:5.2kb | context:HUMAN
/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_instructions | refs:high | status:CURRENT | size:22.1kb | context:HUMAN
/docs/MCP_INDEX_SHARING.md | purpose:index_sharing_guide | refs:medium | status:CURRENT | size:8.6kb | context:HUMAN
/docs/QUICK_START_PHASE4.md | purpose:quick_start_guide | refs:medium | status:CURRENT | size:10.9kb | context:HUMAN
/docs/PHASE4_ADVANCED_FEATURES.md | purpose:phase4_features | refs:low | status:CURRENT | size:15.5kb | context:HUMAN
/docs/PHASE5_IMPLEMENTATION_GUIDE.md | purpose:phase5_consolidated | refs:medium | status:NEW | size:9.2kb | context:HUMAN
/docs/PHASE5_IMMEDIATE_ACTIONS.md | purpose:phase5_actions | refs:low | status:CURRENT | size:13.8kb | context:HUMAN
/docs/PHASE5_PARALLEL_EXECUTION_PLAN.md | purpose:phase5_execution | refs:low | status:CURRENT | size:9.6kb | context:HUMAN
/docs/TRANSLATION_WORKFLOW_GUIDE.md | purpose:translation_guide | refs:low | status:CURRENT | size:10.9kb | context:HUMAN
/architecture/README.md | purpose:architecture_overview | refs:medium | status:CURRENT | size:12.9kb | context:HUMAN
/architecture/AGENTS.md | purpose:arch_agent_config | refs:medium | status:CURRENT | size:18.2kb | context:AI_AGENT
/architecture/IMPLEMENTATION_STATUS.md | purpose:implementation_status | refs:low | status:NEW | size:4.9kb | context:HUMAN
/architecture/ARCHITECTURE_CONSOLIDATION.md | purpose:arch_consolidation | refs:low | status:CURRENT | size:3.2kb | context:HUMAN
/mcp_server/AGENTS.md | purpose:mcp_agent_config | refs:medium | status:CURRENT | size:7.9kb | context:AI_AGENT
```

### MAINTENANCE_REQUIRED
```
/architecture/CLAUDE.md | purpose:duplicate_pointer | refs:low | status:DUPLICATE | similarity:100% | action:REPLACE_WITH_SYMLINK
/mcp_server/CLAUDE.md | purpose:duplicate_pointer | refs:low | status:DUPLICATE | similarity:100% | action:REPLACE_WITH_SYMLINK
/mcp_server/plugins/*/CLAUDE.md | purpose:duplicate_pointers | refs:low | status:DUPLICATE | count:9 | action:REPLACE_WITH_SYMLINK
/docs/planning/markdown-table-of-contents.md | purpose:duplicate_index | refs:none | status:DUPLICATE | size:10.8kb | action:DELETE
/.archive/legacy_docs/* | purpose:archived_content | refs:none | status:ARCHIVED | count:6 | action:NONE
```

### NEW_PLUGIN_AGENTS
```
/mcp_server/plugins/jvm_plugin/AGENTS.md | purpose:jvm_plugin_config | refs:medium | status:NEW | size:3.7kb | context:AI_AGENT
/mcp_server/plugins/php_plugin/AGENTS.md | purpose:php_plugin_config | refs:medium | status:NEW | size:4.5kb | context:AI_AGENT
/mcp_server/plugins/ruby_plugin/AGENTS.md | purpose:ruby_plugin_config | refs:medium | status:NEW | size:4.7kb | context:AI_AGENT
/mcp_server/plugins/rust_plugin/AGENTS.md | purpose:rust_plugin_config | refs:medium | status:NEW | size:4.4kb | context:AI_AGENT
/mcp_server/plugins/go_plugin/AGENTS.md | purpose:go_plugin_config | refs:medium | status:UPDATED | size:0.5kb | context:AI_AGENT
```

### PHASE5_REORGANIZED
```
/docs/phase5/DISTRIBUTED_SYSTEM_SUMMARY.md | purpose:distributed_summary | refs:low | status:MOVED | size:9.5kb | context:HUMAN
/docs/phase5/INDEXING_TEST_SUMMARY.md | purpose:indexing_tests | refs:low | status:MOVED | size:3.4kb | context:HUMAN
/docs/phase5/PHASE5_PROJECT_STRUCTURE.md | purpose:project_structure | refs:low | status:MOVED | size:1.8kb | context:HUMAN
/docs/phase5/PHASE5_RUBY_PHP_PLUGINS_SUMMARY.md | purpose:plugin_summary | refs:low | status:MOVED | size:7.4kb | context:HUMAN
/docs/phase5/PHASE5_VECTOR_SEARCH_ENHANCEMENT_SUMMARY.md | purpose:vector_search | refs:low | status:MOVED | size:8.5kb | context:HUMAN
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# Remove duplicate markdown-table-of-contents.md in planning directory
rm docs/planning/markdown-table-of-contents.md

# Archive completed - no further action needed for legacy docs
# Legacy docs already moved to .archive/legacy_docs/
```

### CONSOLIDATION_TASKS
```
REPLACE_WITH_SYMLINKS: All CLAUDE.md files (11 instances)
  REASON: 100% identical content, all redirect to AGENTS.md
  ACTION: 
    # Create symlinks to root CLAUDE.md
    cd mcp_server && ln -sf ../CLAUDE.md CLAUDE.md
    cd architecture && ln -sf ../CLAUDE.md CLAUDE.md
    for plugin in mcp_server/plugins/*/; do
      cd "$plugin" && ln -sf ../../../CLAUDE.md CLAUDE.md
    done

CONSOLIDATION_COMPLETE: Phase 5 documentation
  STATUS: Already consolidated into docs/PHASE5_IMPLEMENTATION_GUIDE.md
  MOVED: 5 detailed files to docs/phase5/ subdirectory
  PRESERVED: All implementation details and summaries
```

### CONTENT_UPDATES_NEEDED
```
/ai_docs/*.md | ISOLATED | No cross-references, has index page (README.md)
/docs/planning/MCP_MIGRATION_STATUS.md | STALE | References March 2024 timeline
/docs/planning/MCP_IMPLEMENTATION_STATUS.md | STALE | Shows incomplete status (project is complete)
/test_repos/*/README.md | OUTDATED | Generic GitHub READMEs, not project-specific
```

## SEMANTIC_CLUSTERS
```
ai_agent_configuration: [/CLAUDE.md, /AGENTS.md, */AGENTS.md, /DIFF_BASED_EDITING_GUIDE.md, /DYNAMIC_PROMPT_GUIDE.md]
deployment_documentation: [/docs/DEPLOYMENT-GUIDE.md, /docs/QUICK_START_PHASE4.md, /docker/README.md]
mcp_implementation: [/docs/MCP_INDEX_SHARING.md, /docs/planning/MCP_*.md]
phase_documentation: [/docs/phase5/*.md, /docs/PHASE*.md]
api_reference: [/docs/api/API-REFERENCE.md, /ai_docs/*.md]
testing_documentation: [/docs/development/TESTING*.md, /tests/README.md]
architecture: [/architecture/*.md, /docs/planning/*ARCHITECTURE*.md]
security_and_troubleshooting: [/SECURITY.md, /TROUBLESHOOTING.md]
plugin_documentation: [/mcp_server/plugins/*/AGENTS.md, /docs/phase5/*PLUGINS*.md]
```

## REFERENCE_MAP
```
# Incoming references (files that link to this doc)
/README.md ← [Most files reference back to README]
/docs/MCP_INDEX_SHARING.md ← [/README.md:144]
/CONTRIBUTING.md ← [/README.md:551]
/architecture/ ← [/README.md:537]
/SECURITY.md ← [/README.md:security-section]
/TROUBLESHOOTING.md ← [/README.md:troubleshooting-section]

# Outgoing references (files this doc links to)
/README.md → [7 other docs: guides, architecture, contributing]
/CLAUDE.md → [/README.md#ai-agent-integration]
/DOCUMENTATION_INDEX.md → [Multiple inventory references]
/docs/PHASE5_IMPLEMENTATION_GUIDE.md → [phase5/*.md files]
```

## CONTENT_GAPS
```
# Previously missing documentation now created
CREATED: Security policy (/SECURITY.md)
CREATED: Troubleshooting guide (/TROUBLESHOOTING.md)
CREATED: Plugin AGENTS.md for jvm, php, ruby plugins
CREATED: Architecture implementation status (/architecture/IMPLEMENTATION_STATUS.md)
CREATED: Consolidated Phase 5 guide (/docs/PHASE5_IMPLEMENTATION_GUIDE.md)

# Still missing or needs attention
MISSING: Performance tuning guide (benchmarks exist but no guide)
MISSING: Plugin development guide (multiple plugins but no unified guide)
STALE: MCP planning documents need status updates
```

## AGENT_PROMPTS
```
# When creating new documentation:
"Before creating new docs, check SEMANTIC_CLUSTERS and FILE_INVENTORY to avoid duplication"
"If creating AI agent docs, add to appropriate AGENTS.md rather than new files"

# When modifying existing docs:
"Check REFERENCE_MAP to understand dependencies before major changes"
"Update DOCUMENTATION_INDEX.md after significant changes"

# For maintenance tasks:
"Execute IMMEDIATE_CLEANUP actions first, then handle CONSOLIDATION_TASKS"
"Use symlinks for CLAUDE.md files to maintain consistency"

# For content organization:
"Keep AI_AGENT context files separate from HUMAN documentation"
"Phase-specific docs should go in docs/phaseN/ subdirectories"
```

## STATISTICS_SUMMARY
```
Total Files: 144 markdown files (excluding test_repos and archives)
AI Agent Context: 26 files (18%)
Human Documentation: 85 files (59%)
Technical Docs: 33 files (23%)
New Files Created: 8 files (in this update)
Files Moved: 5 files (to docs/phase5/)
Duplicate CLAUDE.md: 11 files (need symlinks)
Stale Content: 12 files (8% - need review)
Total Size: ~1.8 MB of documentation (excluding test repos)
Recently Updated: 13 files today
```

## RECOMMENDED_WORKFLOW
```
1. Remove duplicate markdown-table-of-contents.md from planning
2. Replace duplicate CLAUDE.md files with symlinks
3. Update stale MCP planning documents with current status
4. Create plugin development guide consolidating all plugin info
5. Create performance tuning guide using benchmark data
6. Review and update cross-references in main documentation
7. Update DOCUMENTATION_INDEX.md with new structure
```

## PHASE12_UPDATE_SUMMARY
```
Created Files:
- /SECURITY.md (2.7kb) - Security policy and guidelines
- /TROUBLESHOOTING.md (5.2kb) - Common issues and solutions
- /architecture/IMPLEMENTATION_STATUS.md (4.9kb) - Current implementation status
- /docs/PHASE5_IMPLEMENTATION_GUIDE.md (9.2kb) - Consolidated Phase 5 guide
- /mcp_server/plugins/jvm_plugin/AGENTS.md (3.7kb) - JVM plugin configuration
- /mcp_server/plugins/php_plugin/AGENTS.md (4.5kb) - PHP plugin configuration
- /mcp_server/plugins/ruby_plugin/AGENTS.md (4.7kb) - Ruby plugin configuration

Moved Files:
- DISTRIBUTED_SYSTEM_SUMMARY.md → docs/phase5/
- INDEXING_TEST_SUMMARY.md → docs/phase5/
- PHASE5_PROJECT_STRUCTURE.md → docs/phase5/
- PHASE5_RUBY_PHP_PLUGINS_SUMMARY.md → docs/phase5/
- PHASE5_VECTOR_SEARCH_ENHANCEMENT_SUMMARY.md → docs/phase5/

Archived:
- old_rest_api_backup/ → .archive/legacy_docs/
```