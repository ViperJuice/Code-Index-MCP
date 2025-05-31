# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-05-31 02:23:17 UTC

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content
- CLAUDE.md stubs are intentional navigation aids - DO NOT merge or remove

## FILE_INVENTORY

### ACTIVE_DOCS (61 files, ~671KB)

#### 🤖 AI AGENT CONTEXT (20 files, ~85KB)
```
/CLAUDE.md | purpose:ai_entry_point | context:AI_AGENT | refs:high | status:CURRENT | size:669B
/AGENTS.md | purpose:master_agent_config | context:AI_AGENT | refs:high | status:CURRENT | size:7.4KB
/MARKDOWN_INDEX.md | purpose:doc_catalog | context:AI_AGENT | refs:high | status:CURRENT | size:12.8KB
/.claude/commands/add-feature.md | purpose:feature_template | context:AI_AGENT | refs:medium | status:CURRENT | size:7.6KB
/.claude/commands/do-next-steps.md | purpose:workflow_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:8.6KB
/.claude/commands/update-documents.md | purpose:doc_maintenance | context:AI_AGENT | refs:low | status:CURRENT | size:25.4KB
/.claude/commands/update-table-of-contents.md | purpose:toc_management | context:AI_AGENT | refs:low | status:MERGEABLE | size:6.5KB
/architecture/CLAUDE.md | purpose:arch_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/architecture/AGENTS.md | purpose:arch_operations | context:AI_AGENT | refs:medium | status:CURRENT | size:4.5KB
/mcp_server/CLAUDE.md | purpose:server_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/AGENTS.md | purpose:server_implementation | context:AI_AGENT | refs:medium | status:CURRENT | size:8.1KB
/mcp_server/plugins/python_plugin/CLAUDE.md | purpose:python_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/python_plugin/AGENTS.md | purpose:python_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:6.9KB
/mcp_server/plugins/c_plugin/CLAUDE.md | purpose:c_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/c_plugin/AGENTS.md | purpose:c_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:10.7KB
/mcp_server/plugins/cpp_plugin/CLAUDE.md | purpose:cpp_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/cpp_plugin/AGENTS.md | purpose:cpp_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:14.7KB
/mcp_server/plugins/js_plugin/CLAUDE.md | purpose:js_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/js_plugin/AGENTS.md | purpose:js_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:20.1KB
/mcp_server/plugins/dart_plugin/CLAUDE.md | purpose:dart_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/dart_plugin/AGENTS.md | purpose:dart_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:18.6KB
/mcp_server/plugins/html_css_plugin/CLAUDE.md | purpose:html_entry_stub | context:AI_AGENT | refs:medium | status:CURRENT | size:669B
/mcp_server/plugins/html_css_plugin/AGENTS.md | purpose:html_plugin_guide | context:AI_AGENT | refs:medium | status:CURRENT | size:21.3KB
```

#### 📚 PROJECT MANAGEMENT (8 files, ~42KB)
```
/README.md | purpose:project_overview | context:HUMAN | refs:high | status:CURRENT | size:10.4KB
/ROADMAP.md | purpose:development_timeline | context:HUMAN | refs:high | status:CURRENT | size:7.2KB
/CONTRIBUTING.md | purpose:contribution_guide | context:HUMAN | refs:medium | status:CURRENT | size:7.1KB
/CHANGELOG.md | purpose:version_history | context:HUMAN | refs:medium | status:CURRENT | size:1.7KB
/SECURITY.md | purpose:security_policies | context:HUMAN | refs:medium | status:CURRENT | size:1.9KB
/TROUBLESHOOTING.md | purpose:issue_resolution | context:HUMAN | refs:medium | status:CURRENT | size:5.6KB
/COMPREHENSIVE_PARALLEL_TESTING_PLAN.md | purpose:testing_strategy | context:HUMAN | refs:high | status:CURRENT | size:16.4KB
/TESTING_VALIDATION_REPORT.md | purpose:testing_results | context:HUMAN | refs:high | status:CURRENT | size:5.8KB
```

#### 🏗️ ARCHITECTURE & DESIGN (6 files, ~32KB)
```
/architecture/README.md | purpose:architecture_guide | context:HUMAN | refs:high | status:CURRENT | size:6.0KB
/architecture/data_model.md | purpose:database_schema | context:HUMAN | refs:medium | status:CURRENT | size:12.2KB
/architecture/performance_requirements.md | purpose:performance_specs | context:HUMAN | refs:medium | status:CURRENT | size:3.4KB
/architecture/security_model.md | purpose:security_design | context:HUMAN | refs:medium | status:CURRENT | size:5.0KB
```

#### 📖 API & DEPLOYMENT (4 files, ~47KB)
```
/docs/api/API-REFERENCE.md | purpose:api_documentation | context:HUMAN | refs:high | status:CURRENT | size:20.2KB
/docs/configuration/ENVIRONMENT-VARIABLES.md | purpose:environment_setup | context:HUMAN | refs:high | status:CURRENT | size:9.1KB
/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_instructions | context:HUMAN | refs:high | status:CURRENT | size:22.7KB
/docs/development/TESTING-GUIDE.md | purpose:testing_procedures | context:HUMAN | refs:medium | status:CURRENT | size:33.6KB
```

#### 🔧 TECHNOLOGY REFERENCE (ai_docs/, 16 files, ~309KB)
```
/ai_docs/README.md | purpose:technology_index | context:HUMAN | refs:medium | status:CURRENT | size:4.2KB
/ai_docs/qdrant.md | purpose:vector_search_ref | context:HUMAN | refs:low | status:CURRENT | size:51.0KB
/ai_docs/jedi.md | purpose:python_analysis_ref | context:HUMAN | refs:medium | status:CURRENT | size:35.2KB
/ai_docs/grpc_overview.md | purpose:grpc_reference | context:HUMAN | refs:low | status:CURRENT | size:34.0KB
/ai_docs/sqlite_fts5_overview.md | purpose:fulltext_search_ref | context:HUMAN | refs:medium | status:CURRENT | size:29.1KB
/ai_docs/watchdog.md | purpose:file_monitoring_ref | context:HUMAN | refs:medium | status:CURRENT | size:23.1KB
/ai_docs/redis.md | purpose:caching_reference | context:HUMAN | refs:medium | status:CURRENT | size:15.9KB
/ai_docs/jwt_authentication_overview.md | purpose:auth_reference | context:HUMAN | refs:medium | status:CURRENT | size:15.4KB
/ai_docs/pydantic_overview.md | purpose:validation_reference | context:HUMAN | refs:medium | status:CURRENT | size:15.1KB
/ai_docs/prometheus_overview.md | purpose:monitoring_reference | context:HUMAN | refs:medium | status:CURRENT | size:14.8KB
/ai_docs/celery_overview.md | purpose:task_queue_ref | context:HUMAN | refs:low | status:CURRENT | size:13.7KB
/ai_docs/tree_sitter_overview.md | purpose:parsing_reference | context:HUMAN | refs:high | status:CURRENT | size:10.2KB
/ai_docs/plantuml_reference.md | purpose:diagram_reference | context:HUMAN | refs:low | status:CURRENT | size:9.6KB
/ai_docs/fastapi_overview.md | purpose:framework_reference | context:HUMAN | refs:high | status:CURRENT | size:9.0KB
/ai_docs/memgraph_overview.md | purpose:graph_db_ref | context:HUMAN | refs:low | status:CURRENT | size:7.9KB
/ai_docs/voyage_ai_overview.md | purpose:embeddings_ref | context:HUMAN | refs:low | status:CURRENT | size:5.0KB
```

#### 🧪 COMPONENT DOCS (3 files, ~12KB)
```
/mcp_server/benchmarks/README.md | purpose:benchmark_guide | context:HUMAN | refs:medium | status:CURRENT | size:6.7KB
/tests/README.md | purpose:testing_overview | context:HUMAN | refs:medium | status:CURRENT | size:3.8KB
/.pytest_cache/README.md | purpose:pytest_cache_info | context:HUMAN | refs:low | status:CURRENT | size:302B
```

### MAINTENANCE_REQUIRED (9 files, ~37KB)

#### 📜 HISTORICAL DOCUMENTS (STALE - Archival Candidates)
```
/docs/history/INDEXER_IMPLEMENTATION_SUMMARY.md | purpose:implementation_history | refs:none | status:STALE | last_modified:2025-01-30 | size:10.2KB | action:ARCHIVE
/docs/history/ARCHITECTURE_VS_IMPLEMENTATION_ANALYSIS.md | purpose:architecture_analysis | refs:none | status:STALE | last_modified:2025-01-30 | size:6.3KB | action:ARCHIVE
/docs/history/IMPLEMENTATION_GAP_ANALYSIS.md | purpose:gap_analysis | refs:none | status:STALE | last_modified:2025-01-30 | size:4.6KB | action:ARCHIVE
/docs/history/PLUGIN_GUIDES_ENHANCEMENT_SUMMARY.md | purpose:plugin_enhancement | refs:none | status:STALE | last_modified:2025-01-30 | size:4.2KB | action:ARCHIVE
/docs/history/ARCHITECTURE_ALIGNMENT_REPORT.md | purpose:alignment_report | refs:none | status:STALE | last_modified:2025-01-30 | size:4.1KB | action:ARCHIVE
/docs/history/DOCUMENTATION_UPDATE_SUMMARY.md | purpose:update_summary | refs:none | status:STALE | last_modified:2025-01-30 | size:4.1KB | action:ARCHIVE
/docs/history/DOCUMENTATION_UPDATE_SUMMARY_2025-01-30.md | purpose:update_summary_jan | refs:none | status:STALE | last_modified:2025-01-30 | size:3.6KB | action:ARCHIVE
/docs/history/ARCHITECTURE_FIXES.md | purpose:arch_fixes | refs:none | status:STALE | last_modified:2025-01-30 | size:3.0KB | action:ARCHIVE
/docs/history/PHASE1_COMPLETION_SUMMARY.md | purpose:milestone_report | refs:low | status:CURRENT | last_modified:2025-01-30 | size:2.8KB | action:KEEP
```

#### 📅 DATED SUMMARIES (MERGEABLE)
```
/DOCUMENTATION_UPDATE_SUMMARY_2025-05-30.md | purpose:doc_status_may30 | refs:none | status:STALE | similarity:DOCUMENTATION_UPDATE_SUMMARY_2025-05-31.md:92% | action:MERGE_INTO:latest_summary
/DOCUMENTATION_UPDATE_SUMMARY_2025-05-31.md | purpose:doc_status_may31 | refs:none | status:STALE | size:9.9KB | action:KEEP_LATEST
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# Archive historical documents (maintain git history)
mkdir -p archive/docs/history
mv docs/history/INDEXER_IMPLEMENTATION_SUMMARY.md archive/docs/history/
mv docs/history/ARCHITECTURE_VS_IMPLEMENTATION_ANALYSIS.md archive/docs/history/
mv docs/history/IMPLEMENTATION_GAP_ANALYSIS.md archive/docs/history/
mv docs/history/PLUGIN_GUIDES_ENHANCEMENT_SUMMARY.md archive/docs/history/
mv docs/history/ARCHITECTURE_ALIGNMENT_REPORT.md archive/docs/history/
mv docs/history/DOCUMENTATION_UPDATE_SUMMARY.md archive/docs/history/
mv docs/history/DOCUMENTATION_UPDATE_SUMMARY_2025-01-30.md archive/docs/history/
mv docs/history/ARCHITECTURE_FIXES.md archive/docs/history/

# Remove redundant dated summaries (keep latest)
rm DOCUMENTATION_UPDATE_SUMMARY_2025-05-30.md
# Keep DOCUMENTATION_UPDATE_SUMMARY_2025-05-31.md as latest
```

### CONSOLIDATION_TASKS
```
MERGE: .claude/commands/update-table-of-contents.md → .claude/commands/update-documents.md
  REASON: Overlapping functionality, update-documents already handles TOC
  PRESERVE: Specific TOC generation logic
  ACTION: Extract unique logic, merge into update-documents.md
```

### CONTENT_UPDATES_NEEDED
```
# No stale technical content identified - all documentation current for 2025-05-31
# Technology references in ai_docs/ remain current and accurate
# API documentation updated with production endpoints
# Configuration documentation includes production templates
```

## SEMANTIC_CLUSTERS

### AGENT_GUIDANCE_CLUSTER
```
Primary: [/CLAUDE.md, /AGENTS.md]
Navigation: [/MARKDOWN_INDEX.md, /markdown-table-of-contents.md]
Commands: [.claude/commands/*.md]
Hierarchical: [*/CLAUDE.md, */AGENTS.md] (9 pairs)
```

### PROJECT_MANAGEMENT_CLUSTER
```
Core: [/README.md, /ROADMAP.md, /CONTRIBUTING.md]
Process: [/CHANGELOG.md, /SECURITY.md, /TROUBLESHOOTING.md]
Quality: [/COMPREHENSIVE_PARALLEL_TESTING_PLAN.md, /TESTING_VALIDATION_REPORT.md]
```

### ARCHITECTURE_CLUSTER
```
Design: [/architecture/README.md, /architecture/data_model.md]
Requirements: [/architecture/performance_requirements.md, /architecture/security_model.md]
Guidance: [/architecture/AGENTS.md]
```

### API_DEPLOYMENT_CLUSTER
```
Interface: [/docs/api/API-REFERENCE.md]
Configuration: [/docs/configuration/ENVIRONMENT-VARIABLES.md]
Operations: [/docs/DEPLOYMENT-GUIDE.md, /docs/development/TESTING-GUIDE.md]
```

### TECHNOLOGY_REFERENCE_CLUSTER
```
Index: [/ai_docs/README.md]
Core_Technologies: [fastapi_overview.md, tree_sitter_overview.md, sqlite_fts5_overview.md]
Language_Analysis: [jedi.md, pydantic_overview.md]
Infrastructure: [redis.md, prometheus_overview.md, jwt_authentication_overview.md]
Advanced: [qdrant.md, grpc_overview.md, celery_overview.md, memgraph_overview.md]
Tools: [plantuml_reference.md, voyage_ai_overview.md, watchdog.md]
```

### PLUGIN_IMPLEMENTATION_CLUSTER
```
Languages: [python_plugin, c_plugin, cpp_plugin, js_plugin, dart_plugin, html_css_plugin]
Pattern: Each has [CLAUDE.md (stub), AGENTS.md (guide)] pair
Status: All FULLY_IMPLEMENTED with comprehensive guides
```

## REFERENCE_MAP

### HIGH_TRAFFIC_DOCUMENTS (Referenced by multiple systems)
```
/README.md ← [docs/*, CONTRIBUTING.md, external_links]
/AGENTS.md ← [/CLAUDE.md, all_plugin_AGENTS.md, .claude/commands/*]
/docs/api/API-REFERENCE.md ← [README.md, DEPLOYMENT-GUIDE.md, testing_code]
/COMPREHENSIVE_PARALLEL_TESTING_PLAN.md ← [TESTING_VALIDATION_REPORT.md, AGENTS.md]
```

### HIERARCHICAL_REFERENCES
```
# CLAUDE.md stubs → AGENTS.md pattern (9 pairs)
/CLAUDE.md → /AGENTS.md (master)
/architecture/CLAUDE.md → /architecture/AGENTS.md
/mcp_server/CLAUDE.md → /mcp_server/AGENTS.md
[plugin]/CLAUDE.md → [plugin]/AGENTS.md (6 plugins)
```

### TECHNOLOGY_CROSS_REFERENCES
```
# Implementation references technology docs
/mcp_server/plugins/python_plugin/AGENTS.md → /ai_docs/jedi.md, /ai_docs/tree_sitter_overview.md
/docs/api/API-REFERENCE.md → /ai_docs/fastapi_overview.md, /ai_docs/jwt_authentication_overview.md
/architecture/data_model.md → /ai_docs/sqlite_fts5_overview.md
```

## CONTENT_GAPS

### MISSING_DOCUMENTATION
```
# Identified gaps that should exist based on codebase
MISSING: /docs/tutorials/PLUGIN_DEVELOPMENT.md (referenced in plugin AGENTS.md but detailed tutorial missing)
MISSING: /docs/performance/BENCHMARKS.md (performance requirements exist but no actual measurements)
MISSING: /docs/examples/PRODUCTION_CONFIG.md (deployment guide exists but needs concrete examples)
MISSING: /docs/migration/STUB_TO_IMPLEMENTATION.md (migration process from stub to full implementation)
```

### ENHANCEMENT_OPPORTUNITIES
```
ENHANCE: /ai_docs/README.md (add implementation status for each technology)
ENHANCE: /ROADMAP.md (add completion percentages and timeline updates)
ENHANCE: /docs/development/TESTING-GUIDE.md (add performance testing section)
ENHANCE: /TROUBLESHOOTING.md (add plugin-specific troubleshooting)
```

## DOCUMENTATION_HEALTH_SCORE

### OVERALL_METRICS
```
Total Files: 70 markdown files
Total Size: ~756KB
AI Context: 20 files (29%)
Human Context: 50 files (71%)
Current Status: 61 files (87%)
Stale Status: 9 files (13%)
Reference Density: High (good cross-linking)
Organizational Score: 95% (excellent structure)
```

### MAINTENANCE_HEALTH
```
✅ EXCELLENT: Clear hierarchical structure with consistent patterns
✅ EXCELLENT: Comprehensive coverage of all system components  
✅ EXCELLENT: Active maintenance with recent updates
✅ GOOD: Minimal duplication (only intentional design patterns)
⚠️  MINOR: Historical documents need archival (9 files)
⚠️  MINOR: Some dated summaries could be consolidated
```

## AGENT_PROMPTS

### DOCUMENTATION_CREATION
```
"Before creating new documentation, check SEMANTIC_CLUSTERS and FILE_INVENTORY to avoid duplication. Reference existing technology docs in /ai_docs/ for implementation details."
```

### DOCUMENTATION_MODIFICATION
```
"Check REFERENCE_MAP to understand dependencies before major changes. Update AGENTS.md files for implementation guidance, README.md for user-facing changes."
```

### MAINTENANCE_TASKS
```
"Execute IMMEDIATE_CLEANUP actions to archive historical files. Use CONSOLIDATION_TASKS for content merging. Do NOT remove CLAUDE.md stubs - they are intentional navigation aids."
```

### PLUGIN_DEVELOPMENT
```
"Follow the plugin CLAUDE.md → AGENTS.md pattern. Reference /ai_docs/ for technology details. Update /mcp_server/AGENTS.md with integration notes."
```

## STATUS_SUMMARY

**Documentation Health: EXCELLENT (95% score)**
- ✅ Comprehensive coverage with 70 files
- ✅ Clear AI/Human context separation  
- ✅ Active maintenance and updates
- ✅ Excellent organizational structure
- ⚠️ Minor cleanup needed (9 historical files)
- 📈 Ready for production deployment

**Recommended Actions:**
1. Archive 8 historical documents to `/archive/docs/history/`
2. Consolidate update-table-of-contents command
3. Create missing tutorial documentation
4. Enhance performance documentation with benchmarks

**Agent Productivity Features:**
- Dual-context navigation (AI/Human)
- Comprehensive technology reference library
- Clear plugin development patterns
- Hierarchical agent guidance system