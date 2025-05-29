# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-01-29

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content

## FILE_INVENTORY

### ACTIVE_DOCS

#### AI Agent Context Files
```
/CLAUDE.md | purpose:project_context_for_ai | refs:high | status:CURRENT | size:7.3kb | context:AI_AGENT
/AGENTS.md | purpose:agent_capabilities | refs:high | status:CURRENT | size:3.2kb | context:AI_AGENT
/architecture/CLAUDE.md | purpose:architecture_ai_context | refs:medium | status:CURRENT | size:2.3kb | context:AI_AGENT
/architecture/AGENTS.md | purpose:architecture_agent_tasks | refs:low | status:CURRENT | size:1.4kb | context:AI_AGENT
/mcp_server/AGENTS.md | purpose:mcp_server_agent_config | refs:medium | status:CURRENT | size:4.2kb | context:AI_AGENT
/mcp_server/plugins/python_plugin/AGENTS.md | purpose:python_plugin_actual_implementation | refs:medium | status:CURRENT | size:2.5kb | context:AI_AGENT
.claude/commands/update-documents.md | purpose:document_update_command | refs:low | status:CURRENT | size:9.4kb | context:AI_AGENT
.claude/commands/add-feature.md | purpose:feature_addition_command | refs:low | status:CURRENT | size:7.7kb | context:AI_AGENT
.claude/commands/update-table-of-contents.md | purpose:toc_generation_command | refs:low | status:CURRENT | size:6.5kb | context:AI_AGENT
```

#### Human Documentation
```
/README.md | purpose:project_overview | refs:high | status:CURRENT | size:10.4kb | context:HUMAN
/ROADMAP.md | purpose:development_timeline | refs:medium | status:CURRENT | size:9.6kb | context:HUMAN
/CONTRIBUTING.md | purpose:contribution_guide | refs:medium | status:CURRENT | size:7.1kb | context:HUMAN
/SECURITY.md | purpose:security_policy | refs:low | status:CURRENT | size:1.9kb | context:HUMAN
/TROUBLESHOOTING.md | purpose:common_issues | refs:low | status:CURRENT | size:5.6kb | context:HUMAN
/CHANGELOG.md | purpose:version_history | refs:low | status:CURRENT | size:1.7kb | context:HUMAN
/DOCUMENTATION_UPDATE_SUMMARY.md | purpose:doc_alignment_report | refs:low | status:CURRENT | size:4.0kb | context:HUMAN
/markdown-table-of-contents.md | purpose:markdown_index | refs:high | status:CURRENT | size:7.3kb | context:HUMAN
```

#### Architecture Documentation
```
/architecture/README.md | purpose:architecture_overview | refs:medium | status:CURRENT | size:6.0kb | context:HUMAN
/architecture/data_model.md | purpose:data_structures | refs:medium | status:CURRENT | size:12.2kb | context:HUMAN
/architecture/performance_requirements.md | purpose:performance_specs | refs:low | status:CURRENT | size:3.4kb | context:HUMAN
/architecture/security_model.md | purpose:security_design | refs:low | status:CURRENT | size:5.0kb | context:HUMAN
/architecture/IMPLEMENTATION_GAP_ANALYSIS.md | purpose:implementation_gaps | refs:low | status:CURRENT | size:4.6kb | context:HUMAN
/architecture/ARCHITECTURE_FIXES.md | purpose:architecture_issues | refs:low | status:CURRENT | size:3.0kb | context:HUMAN
```

#### Docs Directory
```
/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_instructions | refs:medium | status:CURRENT | size:22.7kb | context:HUMAN
/docs/api/API-REFERENCE.md | purpose:api_documentation | refs:high | status:CURRENT | size:6.5kb | context:HUMAN
/docs/configuration/ENVIRONMENT-VARIABLES.md | purpose:env_config | refs:medium | status:CURRENT | size:9.1kb | context:HUMAN
/docs/development/TESTING-GUIDE.md | purpose:testing_documentation | refs:medium | status:CURRENT | size:33.6kb | context:HUMAN
```

#### AI Documentation (Reference)
```
/ai_docs/README.md | purpose:ai_docs_index | refs:high | status:CURRENT | size:10.9kb | context:HUMAN
/ai_docs/celery_overview.md | purpose:celery_reference | refs:low | status:CURRENT | size:8.5kb | context:HUMAN
/ai_docs/fastapi_overview.md | purpose:fastapi_reference | refs:low | status:CURRENT | size:9.4kb | context:HUMAN
/ai_docs/grpc_overview.md | purpose:grpc_reference | refs:low | status:CURRENT | size:8.8kb | context:HUMAN
/ai_docs/jedi.md | purpose:jedi_reference | refs:low | status:CURRENT | size:27.8kb | context:HUMAN
/ai_docs/jwt_authentication_overview.md | purpose:jwt_reference | refs:low | status:CURRENT | size:7.9kb | context:HUMAN
/ai_docs/memgraph_overview.md | purpose:memgraph_reference | refs:low | status:CURRENT | size:8.5kb | context:HUMAN
/ai_docs/plantuml_reference.md | purpose:plantuml_reference | refs:low | status:CURRENT | size:11.9kb | context:HUMAN
/ai_docs/prometheus_overview.md | purpose:prometheus_reference | refs:low | status:CURRENT | size:11.2kb | context:HUMAN
/ai_docs/pydantic_overview.md | purpose:pydantic_reference | refs:low | status:CURRENT | size:7.6kb | context:HUMAN
/ai_docs/qdrant.md | purpose:qdrant_reference | refs:low | status:CURRENT | size:50.9kb | context:HUMAN
/ai_docs/redis.md | purpose:redis_reference | refs:low | status:CURRENT | size:32.2kb | context:HUMAN
/ai_docs/sqlite_fts5_overview.md | purpose:sqlite_reference | refs:low | status:CURRENT | size:6.4kb | context:HUMAN
/ai_docs/tree_sitter_overview.md | purpose:tree_sitter_reference | refs:low | status:CURRENT | size:11.5kb | context:HUMAN
/ai_docs/voyage_ai_overview.md | purpose:voyage_ai_reference | refs:low | status:CURRENT | size:5.1kb | context:HUMAN
/ai_docs/watchdog.md | purpose:watchdog_reference | refs:low | status:CURRENT | size:21.5kb | context:HUMAN
```

### MAINTENANCE_REQUIRED

#### Obsolete/Stale Files
```
/mcp_server/CLAUDE.md | purpose:outdated_mcp_context | refs:low | status:OBSOLETE | size:1.0kb | context:AI_AGENT | action:DELETE
  REASON: Contains incorrect API endpoints (/index instead of /symbol), conflicts with root CLAUDE.md
```

#### Plugin Documentation (Stub Implementations)
```
/mcp_server/plugins/c_plugin/CLAUDE.md | purpose:unimplemented_plugin_doc | refs:none | status:MISLEADING | size:1.2kb | context:AI_AGENT | action:DELETE
/mcp_server/plugins/cpp_plugin/CLAUDE.md | purpose:unimplemented_plugin_doc | refs:none | status:MISLEADING | size:1.4kb | context:AI_AGENT | action:DELETE
/mcp_server/plugins/js_plugin/CLAUDE.md | purpose:unimplemented_plugin_doc | refs:none | status:MISLEADING | size:1.2kb | context:AI_AGENT | action:DELETE
/mcp_server/plugins/dart_plugin/CLAUDE.md | purpose:unimplemented_plugin_doc | refs:none | status:MISLEADING | size:1.1kb | context:AI_AGENT | action:DELETE
/mcp_server/plugins/html_css_plugin/CLAUDE.md | purpose:unimplemented_plugin_doc | refs:none | status:MISLEADING | size:1.2kb | context:AI_AGENT | action:DELETE
  REASON: All describe features that don't exist (only Python plugin is implemented)

/mcp_server/plugins/c_plugin/AGENTS.md | purpose:stub_plugin_agent_doc | refs:none | status:LOW_VALUE | size:1.6kb | context:AI_AGENT | action:CONSIDER_DELETE
/mcp_server/plugins/cpp_plugin/AGENTS.md | purpose:stub_plugin_agent_doc | refs:none | status:LOW_VALUE | size:2.0kb | context:AI_AGENT | action:CONSIDER_DELETE
/mcp_server/plugins/js_plugin/AGENTS.md | purpose:stub_plugin_agent_doc | refs:none | status:LOW_VALUE | size:1.7kb | context:AI_AGENT | action:CONSIDER_DELETE
/mcp_server/plugins/dart_plugin/AGENTS.md | purpose:stub_plugin_agent_doc | refs:none | status:LOW_VALUE | size:1.5kb | context:AI_AGENT | action:CONSIDER_DELETE
/mcp_server/plugins/html_css_plugin/AGENTS.md | purpose:stub_plugin_agent_doc | refs:none | status:LOW_VALUE | size:1.5kb | context:AI_AGENT | action:CONSIDER_DELETE
  REASON: All correctly marked as STUB but provide minimal value
```

#### Low-Value Files
```
/mcp_server/plugins/python_plugin/CLAUDE.md | purpose:redundant_plugin_doc | refs:none | status:REDUNDANT | size:1.4kb | context:AI_AGENT | action:DELETE
  REASON: Duplicates information already in python_plugin/AGENTS.md

/mcp_server/plugins/CLAUDE.md | purpose:plugin_overview | refs:low | status:REDUNDANT | size:1.1kb | context:AI_AGENT | action:MERGE_INTO:/CLAUDE.md
  REASON: General plugin info better placed in main CLAUDE.md

/mcp_server/plugins/AGENTS.md | purpose:plugin_agent_overview | refs:low | status:LOW_VALUE | size:847b | context:AI_AGENT | action:MERGE_INTO:/mcp_server/AGENTS.md
  REASON: Very brief, better consolidated with parent directory AGENTS.md
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# Delete obsolete and misleading files
rm /workspaces/Code-Index-MCP/mcp_server/CLAUDE.md  # Outdated API endpoints

# Delete misleading plugin documentation for unimplemented plugins
rm /workspaces/Code-Index-MCP/mcp_server/plugins/c_plugin/CLAUDE.md
rm /workspaces/Code-Index-MCP/mcp_server/plugins/cpp_plugin/CLAUDE.md
rm /workspaces/Code-Index-MCP/mcp_server/plugins/js_plugin/CLAUDE.md
rm /workspaces/Code-Index-MCP/mcp_server/plugins/dart_plugin/CLAUDE.md
rm /workspaces/Code-Index-MCP/mcp_server/plugins/html_css_plugin/CLAUDE.md

# Delete redundant Python plugin CLAUDE.md
rm /workspaces/Code-Index-MCP/mcp_server/plugins/python_plugin/CLAUDE.md
```

### CONSOLIDATION_TASKS
```
MERGE: /mcp_server/plugins/CLAUDE.md → /CLAUDE.md
  REASON: Plugin overview info better centralized
  LOCATION: Add to "Language Plugins" section
  
MERGE: /mcp_server/plugins/AGENTS.md → /mcp_server/AGENTS.md
  REASON: Minimal content (847 bytes), better consolidated
  LOCATION: Add as subsection in parent AGENTS.md

CONSIDER: Delete stub plugin AGENTS.md files
  FILES: c_plugin, cpp_plugin, js_plugin, dart_plugin, html_css_plugin AGENTS.md
  REASON: All marked as STUB, provide minimal value
  ACTION: Delete after confirming no unique information
```

### CONTENT_UPDATES_NEEDED
```
/CLAUDE.md | UPDATE | Add correct dispatcher initialization instructions
/architecture/CLAUDE.md | UPDATE | Sync with main CLAUDE.md for consistency
```

## SEMANTIC_CLUSTERS
```
ai_agent_context: [/CLAUDE.md, /AGENTS.md, /architecture/CLAUDE.md, /architecture/AGENTS.md, /mcp_server/AGENTS.md]
project_documentation: [/README.md, /ROADMAP.md, /CONTRIBUTING.md, /SECURITY.md, /TROUBLESHOOTING.md]
architecture_docs: [/architecture/README.md, /architecture/data_model.md, /architecture/performance_requirements.md, /architecture/security_model.md]
api_documentation: [/docs/api/API-REFERENCE.md, /docs/configuration/ENVIRONMENT-VARIABLES.md]
deployment_guides: [/docs/DEPLOYMENT-GUIDE.md, /docs/development/TESTING-GUIDE.md]
technology_reference: [/ai_docs/*.md (15 files)]
plugin_documentation: [plugin CLAUDE.md and AGENTS.md files]
```

## REFERENCE_MAP
```
# Incoming references
/CONTRIBUTING.md ← [/README.md]
/docs/DEPLOYMENT-GUIDE.md ← [/README.md]
/ROADMAP.md ← [/ai_docs/README.md]
/architecture/security_model.md ← [/ai_docs/README.md]
/architecture/performance_requirements.md ← [/ai_docs/README.md]

# Outgoing references
/README.md → [/CONTRIBUTING.md, /docs/DEPLOYMENT-GUIDE.md]
/ai_docs/README.md → [all ai_docs files, /ROADMAP.md, /architecture/security_model.md, /architecture/performance_requirements.md]
/markdown-table-of-contents.md → [all markdown files]
```

## CONTENT_GAPS
```
MISSING: Proper dispatcher initialization guide (referenced in CLAUDE.md but not detailed)
MISSING: Plugin development tutorial (base class exists but no guide)
MISSING: Performance benchmarks documentation (performance_requirements.md exists but no actuals)
MISSING: Migration guide for moving from stubs to implementations
REDUNDANT: Multiple CLAUDE.md files with conflicting information
REDUNDANT: Plugin documentation for unimplemented features
```

## AGENT_PROMPTS
```
# When creating new documentation:
"Check SEMANTIC_CLUSTERS in markdown-table-of-contents.md before creating new files. Most content should go in existing files."

# When working with plugins:
"Only Python plugin is implemented. All other plugins are stubs. Check python_plugin/AGENTS.md for actual implementation details."

# For maintenance tasks:
"Execute IMMEDIATE_CLEANUP first to remove obsolete files, then handle CONSOLIDATION_TASKS."

# For AI agent context:
"CLAUDE.md and AGENTS.md files are for AI agents. Keep them updated with actual implementation status."
```

## STATISTICS
```
Total markdown files: 55
AI Agent Context files: 23 (41.8%)
Human Context files: 32 (58.2%)
Files needing deletion: 6
Files needing merge: 2
Total documentation size: ~450KB
Largest file: /docs/development/TESTING-GUIDE.md (33.6KB)
Smallest file: /mcp_server/plugins/AGENTS.md (847 bytes)
```