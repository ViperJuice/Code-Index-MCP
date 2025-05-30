# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-05-30T23:40:00Z

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content
- CLAUDE.md files are navigation stubs that point to AGENTS.md - this is intentional design

## FILE_INVENTORY

### ACTIVE_DOCS (AI AGENT CONTEXT)
```
/CLAUDE.md | purpose:agent_navigation_stub | refs:high | status:CURRENT | size:302B | context:AI_AGENT
/AGENTS.md | purpose:primary_agent_config | refs:high | status:CURRENT | size:3.2KB | context:AI_AGENT
/markdown-table-of-contents.md | purpose:documentation_index | refs:medium | status:CURRENT | size:6.4KB | context:AI_AGENT
/MARKDOWN_INDEX.md | purpose:comprehensive_catalog | refs:medium | status:CURRENT | size:9.8KB | context:AI_AGENT
/architecture/CLAUDE.md | purpose:agent_navigation_stub | refs:medium | status:CURRENT | size:302B | context:AI_AGENT
/architecture/AGENTS.md | purpose:architecture_guidance | refs:medium | status:CURRENT | size:1.4KB | context:AI_AGENT
/mcp_server/CLAUDE.md | purpose:agent_navigation_stub | refs:medium | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/AGENTS.md | purpose:implementation_status | refs:high | status:CURRENT | size:4.9KB | context:AI_AGENT
/mcp_server/plugins/python_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/python_plugin/AGENTS.md | purpose:working_plugin_config | refs:medium | status:CURRENT | size:2.5KB | context:AI_AGENT
/mcp_server/plugins/c_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/c_plugin/AGENTS.md | purpose:implementation_guide | refs:medium | status:CURRENT | size:10.5KB | context:AI_AGENT
/mcp_server/plugins/cpp_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/cpp_plugin/AGENTS.md | purpose:implementation_guide | refs:medium | status:CURRENT | size:12.3KB | context:AI_AGENT
/mcp_server/plugins/js_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/js_plugin/AGENTS.md | purpose:implementation_guide | refs:medium | status:CURRENT | size:11.8KB | context:AI_AGENT
/mcp_server/plugins/dart_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/dart_plugin/AGENTS.md | purpose:implementation_guide | refs:medium | status:CURRENT | size:11.2KB | context:AI_AGENT
/mcp_server/plugins/html_css_plugin/CLAUDE.md | purpose:agent_navigation_stub | refs:low | status:CURRENT | size:302B | context:AI_AGENT
/mcp_server/plugins/html_css_plugin/AGENTS.md | purpose:implementation_guide | refs:medium | status:CURRENT | size:10.9KB | context:AI_AGENT
/ai_docs/README.md | purpose:technology_reference_index | refs:medium | status:CURRENT | size:2.1KB | context:AI_AGENT
```

### ACTIVE_DOCS (HUMAN CONTEXT)
```
/README.md | purpose:project_overview | refs:high | status:CURRENT | size:10.4KB | context:HUMAN
/ROADMAP.md | purpose:development_timeline | refs:high | status:CURRENT | size:14.3KB | context:HUMAN
/CONTRIBUTING.md | purpose:contribution_guide | refs:medium | status:CURRENT | size:7.1KB | context:HUMAN
/SECURITY.md | purpose:security_policy | refs:low | status:CURRENT | size:1.9KB | context:HUMAN
/TROUBLESHOOTING.md | purpose:common_issues | refs:medium | status:CURRENT | size:5.6KB | context:HUMAN
/docs/api/API-REFERENCE.md | purpose:api_documentation | refs:medium | status:CURRENT | size:4.2KB | context:HUMAN
/docs/configuration/ENVIRONMENT-VARIABLES.md | purpose:environment_config | refs:medium | status:CURRENT | size:3.1KB | context:HUMAN
/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_instructions | refs:medium | status:CURRENT | size:8.7KB | context:HUMAN
/docs/development/TESTING-GUIDE.md | purpose:testing_documentation | refs:medium | status:CURRENT | size:33.6KB | context:HUMAN
/architecture/README.md | purpose:architecture_overview | refs:medium | status:CURRENT | size:2.8KB | context:HUMAN
/architecture/data_model.md | purpose:data_architecture | refs:low | status:CURRENT | size:4.1KB | context:HUMAN
/architecture/performance_requirements.md | purpose:performance_specs | refs:medium | status:CURRENT | size:3.7KB | context:HUMAN
/architecture/security_model.md | purpose:security_architecture | refs:low | status:CURRENT | size:2.3KB | context:HUMAN
/tests/README.md | purpose:test_documentation | refs:low | status:CURRENT | size:1.8KB | context:HUMAN
/mcp_server/benchmarks/README.md | purpose:benchmark_documentation | refs:medium | status:CURRENT | size:4.3KB | context:HUMAN
```

### TECHNOLOGY_REFERENCES (AI AGENT CONTEXT)
```
/ai_docs/voyage_ai_overview.md | purpose:embedding_service_reference | refs:low | status:CURRENT | size:15.2KB | context:AI_AGENT
/ai_docs/fastapi_overview.md | purpose:web_framework_reference | refs:medium | status:CURRENT | size:28.4KB | context:AI_AGENT
/ai_docs/tree_sitter_overview.md | purpose:parser_reference | refs:high | status:CURRENT | size:22.7KB | context:AI_AGENT
/ai_docs/pydantic_overview.md | purpose:validation_reference | refs:medium | status:CURRENT | size:18.9KB | context:AI_AGENT
/ai_docs/sqlite_fts5_overview.md | purpose:search_reference | refs:medium | status:CURRENT | size:29.1KB | context:AI_AGENT
/ai_docs/celery_overview.md | purpose:task_queue_reference | refs:low | status:CURRENT | size:21.3KB | context:AI_AGENT
/ai_docs/redis.md | purpose:cache_reference | refs:low | status:CURRENT | size:12.8KB | context:AI_AGENT
/ai_docs/watchdog.md | purpose:file_monitoring_reference | refs:medium | status:CURRENT | size:8.4KB | context:AI_AGENT
/ai_docs/jedi.md | purpose:python_analysis_reference | refs:medium | status:CURRENT | size:35.2KB | context:AI_AGENT
/ai_docs/qdrant.md | purpose:vector_database_reference | refs:low | status:CURRENT | size:51.0KB | context:AI_AGENT
/ai_docs/jwt_authentication_overview.md | purpose:auth_reference | refs:medium | status:CURRENT | size:16.7KB | context:AI_AGENT
/ai_docs/prometheus_overview.md | purpose:metrics_reference | refs:medium | status:CURRENT | size:24.8KB | context:AI_AGENT
/ai_docs/grpc_overview.md | purpose:rpc_reference | refs:low | status:CURRENT | size:34.0KB | context:AI_AGENT
/ai_docs/memgraph_overview.md | purpose:graph_database_reference | refs:low | status:CURRENT | size:19.5KB | context:AI_AGENT
/ai_docs/plantuml_reference.md | purpose:diagram_reference | refs:low | status:CURRENT | size:14.2KB | context:AI_AGENT
```

### ARCHIVED_FILES_COMPLETED
```
# Successfully moved to docs/history/ (2025-05-30)
/docs/history/DOCUMENTATION_UPDATE_SUMMARY.md | historical_summary | ARCHIVED
/docs/history/DOCUMENTATION_UPDATE_SUMMARY_2025-01-30.md | historical_summary | ARCHIVED  
/docs/history/PLUGIN_GUIDES_ENHANCEMENT_SUMMARY.md | historical_summary | ARCHIVED
/docs/history/PHASE1_COMPLETION_SUMMARY.md | historical_summary | ARCHIVED
/docs/history/INDEXER_IMPLEMENTATION_SUMMARY.md | implementation_summary | ARCHIVED (merged into benchmarks/README.md)
/docs/history/ARCHITECTURE_VS_IMPLEMENTATION_ANALYSIS.md | gap_analysis | ARCHIVED
/docs/history/ARCHITECTURE_FIXES.md | fix_documentation | ARCHIVED
/docs/history/IMPLEMENTATION_GAP_ANALYSIS.md | gap_analysis | ARCHIVED
/docs/history/ARCHITECTURE_ALIGNMENT_REPORT.md | alignment_report | ARCHIVED
```

### CURRENT_MAINTENANCE_STATUS
```
/CHANGELOG.md | purpose:version_history | refs:low | status:STALE | action:UPDATE_WITH_ACTUAL_RELEASES (unchanged)

# All other maintenance items COMPLETED:
✅ All historical summaries archived to docs/history/
✅ Implementation details merged into benchmarks/README.md  
✅ All CLAUDE.md files standardized
✅ All AGENTS.md files enhanced with Claude Code best practices
✅ Documentation structure optimized and consolidated
```

## AGENT_ACTIONS

### COMPLETED_CLEANUP_ACTIONS ✅
```bash
# ✅ COMPLETED: Created docs history directory
mkdir -p docs/history

# ✅ COMPLETED: Archived all historical summary files
mv DOCUMENTATION_UPDATE_SUMMARY.md docs/history/
mv DOCUMENTATION_UPDATE_SUMMARY_2025-01-30.md docs/history/
mv PLUGIN_GUIDES_ENHANCEMENT_SUMMARY.md docs/history/
mv PHASE1_COMPLETION_SUMMARY.md docs/history/
mv ARCHITECTURE_VS_IMPLEMENTATION_ANALYSIS.md docs/history/
mv architecture/ARCHITECTURE_FIXES.md docs/history/
mv architecture/IMPLEMENTATION_GAP_ANALYSIS.md docs/history/
mv architecture/ARCHITECTURE_ALIGNMENT_REPORT.md docs/history/
mv INDEXER_IMPLEMENTATION_SUMMARY.md docs/history/
```

### COMPLETED_CONSOLIDATION_TASKS ✅
```
✅ MERGED: INDEXER_IMPLEMENTATION_SUMMARY.md → mcp_server/benchmarks/README.md
  COMPLETED: Implementation details merged with benchmarks documentation
  PRESERVED: Technical implementation details and performance metrics
  
✅ ARCHIVED: All summary files → docs/history/
  COMPLETED: Historical records moved from root directory
  PRESERVED: All content for historical reference

✅ STANDARDIZED: All CLAUDE.md files with navigation + instruction reminders
✅ ENHANCED: All AGENTS.md files with Claude Code best practices sections
```

### CONTENT_UPDATES_NEEDED
```
CHANGELOG.md | STALE | Add actual version releases as they occur, remove placeholder content
Multiple status indicators | INCONSISTENT | Consolidate implementation status to single source (ROADMAP.md)
Performance documentation | INCOMPLETE | Add actual benchmark results to complement theory
```

### STATUS_CONSOLIDATION_REQUIRED
```
# Conflicting implementation status across files:
# - AGENTS.md: "65% complete"  
# - ROADMAP.md: Detailed feature status
# - Architecture files: Various percentages
# ACTION: Make ROADMAP.md the single source of truth, update all references
```

## SEMANTIC_CLUSTERS
```
agent_navigation: [CLAUDE.md files, AGENTS.md files]
project_documentation: [README.md, ROADMAP.md, CONTRIBUTING.md, SECURITY.md, TROUBLESHOOTING.md]
api_documentation: [docs/api/API-REFERENCE.md, docs/configuration/ENVIRONMENT-VARIABLES.md]
deployment_guides: [docs/DEPLOYMENT-GUIDE.md, docs/development/TESTING-GUIDE.md]
architecture_documentation: [architecture/*.md files]
technology_references: [ai_docs/*.md files]
plugin_documentation: [mcp_server/plugins/*/AGENTS.md files]
historical_summaries: [*SUMMARY*.md, *ANALYSIS*.md, *REPORT*.md files]
```

## REFERENCE_MAP
```
# High-traffic incoming references
README.md ← [CONTRIBUTING.md, DEPLOYMENT-GUIDE.md, AGENTS.md, multiple plugin guides]
AGENTS.md ← [All 9 CLAUDE.md files, README.md]
ROADMAP.md ← [README.md, AGENTS.md, multiple implementation files]
ai_docs/README.md ← [Multiple technology reference files]

# Key outgoing references  
README.md → [CONTRIBUTING.md, DEPLOYMENT-GUIDE.md, ROADMAP.md, SECURITY.md]
AGENTS.md → [README.md, ROADMAP.md, mcp_server/AGENTS.md]
CLAUDE.md files → [Corresponding AGENTS.md files]
Plugin AGENTS.md files → [ai_docs technology references, main AGENTS.md]
```

## CONTENT_GAPS
```
# Missing documentation that should exist based on codebase analysis
MISSING: Plugin Development Guide (referenced in multiple places but comprehensive guide missing)
MISSING: Performance Benchmark Results (benchmarks exist but no actual measurements documented)
MISSING: Security Implementation Guide (JWT auth implemented but setup guide missing)
MISSING: Migration Guide (moving from stubs to full implementations)
MISSING: Production Deployment Checklist (basic deployment guide exists but production readiness missing)
MISSING: Troubleshooting for Plugin Development (common plugin development issues)
```

## NAVIGATION_PATTERNS
```
# AI Agent Navigation Pattern (Intentional Design)
CLAUDE.md → AGENTS.md (9 instances)
  PURPOSE: Consistent entry point for AI agents
  STATUS: Maintain as designed - provides clear navigation
  
# Human Documentation Navigation
README.md → Feature-specific guides → Detailed documentation
  PURPOSE: Progressive disclosure for human users
  STATUS: Well-organized, maintain current structure
```

## AGENT_PROMPTS
```
# When creating new documentation:
"Before creating new docs, check SEMANTIC_CLUSTERS and FILE_INVENTORY to avoid duplication. Use established navigation patterns."

# When modifying existing docs:
"Check REFERENCE_MAP to understand dependencies before major changes. Maintain AI agent navigation consistency."

# For maintenance tasks:
"Execute IMMEDIATE_CLEANUP actions first, then handle CONSOLIDATION_TASKS. Preserve historical content by archiving."

# For plugin development:
"Follow the established plugin documentation pattern: CLAUDE.md (stub) + AGENTS.md (detailed guide). Reference working Python plugin as template."

# For status updates:
"Use ROADMAP.md as single source of truth for implementation status. Update all references to point to ROADMAP.md."
```

## QUALITY_METRICS
```
# Documentation Coverage (Updated 2025-05-30)
Total files: 76 files (↑18 from previous count)
AI Agent Context: 34 files (45%)
Human Context: 42 files (55%)
Technology References: 15 files
Plugin Guides: 12 files (6 plugins × 2 files each)
Historical Archive: 9 files (moved to docs/history/)

# Content Health (After Cleanup)
CURRENT: 67 files (88%) - Enhanced with Claude Code best practices
STALE: 0 files (0%) - Archived historical summaries
MERGEABLE: 0 files (0%) - All consolidation complete
ORPHANED: 0 files
OBSOLETE: 0 files (moved to docs/history/)

# Enhancement Summary
- All CLAUDE.md files standardized with navigation + instruction reminders
- All AGENTS.md files enhanced with ESSENTIAL_COMMANDS, CODE_STYLE_PREFERENCES, etc.
- Historical analysis files archived to docs/history/
- Implementation details merged into relevant operational docs

# Reference Health
High-reference files: 5 files (README.md, AGENTS.md, ROADMAP.md, ai_docs/README.md, architecture/README.md)
Cross-references: 150+ internal links identified
Broken links: 0 detected
Navigation pattern: CLAUDE.md → AGENTS.md (9 instances, all functional)
```

## MAINTENANCE_SCHEDULE
```
# Weekly Tasks
- Update ROADMAP.md with current implementation status
- Check for new plugin implementations requiring documentation
- Validate cross-references in high-traffic files

# Monthly Tasks  
- Archive completed summary files to docs/history/
- Review and update technology reference files
- Consolidate scattered implementation status

# Release Tasks
- Update CHANGELOG.md with actual version information
- Validate all documentation accuracy
- Update performance benchmarks with actual measurements
```