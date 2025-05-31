# Markdown Documentation Index
# This file is auto-generated for AI agent reference - do not edit manually
# Last updated: 2025-05-31T04:10:00Z

## AGENT_INSTRUCTIONS
- Use this index to locate relevant documentation before making changes
- Always check MERGE_CANDIDATES before creating new documentation
- Execute CLEANUP_ACTIONS to maintain documentation hygiene
- Reference FILE_PURPOSES when deciding where to add new content
- CLAUDE.md stubs are navigation patterns - do not modify
- Follow 95% implementation status from TESTING_VALIDATION_REPORT.md

## FILE_INVENTORY

### AI_AGENT_CONTEXT (24 files)
```
/CLAUDE.md | purpose:main_agent_entry | context:AI_AGENT | status:STUB | size:669B | refs:AGENTS.md
/AGENTS.md | purpose:primary_agent_config | context:AI_AGENT | status:CURRENT | size:7.4KB | refs:high
/architecture/CLAUDE.md | purpose:architecture_stub | context:AI_AGENT | status:STUB | size:669B | refs:AGENTS.md
/architecture/AGENTS.md | purpose:architecture_guidance | context:AI_AGENT | status:CURRENT | size:4.5KB | refs:medium
/mcp_server/CLAUDE.md | purpose:server_stub | context:AI_AGENT | status:STUB | size:669B | refs:AGENTS.md
/mcp_server/AGENTS.md | purpose:server_implementation | context:AI_AGENT | status:CURRENT | size:8.1KB | refs:high
/mcp_server/plugins/python_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/python_plugin/AGENTS.md | purpose:python_plugin_guide | context:AI_AGENT | status:CURRENT | size:6.9KB
/mcp_server/plugins/c_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/c_plugin/AGENTS.md | purpose:c_plugin_guide | context:AI_AGENT | status:ENHANCED | size:10.7KB
/mcp_server/plugins/cpp_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/cpp_plugin/AGENTS.md | purpose:cpp_plugin_guide | context:AI_AGENT | status:ENHANCED | size:14.7KB
/mcp_server/plugins/js_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/js_plugin/AGENTS.md | purpose:js_plugin_guide | context:AI_AGENT | status:ENHANCED | size:20.1KB
/mcp_server/plugins/dart_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/dart_plugin/AGENTS.md | purpose:dart_plugin_guide | context:AI_AGENT | status:ENHANCED | size:18.6KB
/mcp_server/plugins/html_css_plugin/CLAUDE.md | purpose:plugin_nav | context:AI_AGENT | status:STUB | size:669B
/mcp_server/plugins/html_css_plugin/AGENTS.md | purpose:html_css_plugin_guide | context:AI_AGENT | status:ENHANCED | size:21.3KB
```

### ACTIVE_DOCS (43 files)
```
/README.md | purpose:project_overview | context:HUMAN | status:CURRENT | size:10.4KB | refs:high
/ROADMAP.md | purpose:development_timeline | context:HUMAN | status:CURRENT | size:7.2KB | refs:medium
/CONTRIBUTING.md | purpose:contribution_guide | context:HUMAN | status:CURRENT | size:7.1KB | refs:medium
/SECURITY.md | purpose:security_policy | context:HUMAN | status:CURRENT | size:1.9KB | refs:low
/TROUBLESHOOTING.md | purpose:support_guide | context:HUMAN | status:CURRENT | size:5.6KB | refs:low
/DORMANT_FEATURES_ACTIVATION.md | purpose:feature_activation | context:HUMAN | status:CURRENT | size:10.7KB | last_modified:2025-05-31
/TESTING_VALIDATION_REPORT.md | purpose:testing_results | context:HUMAN | status:CURRENT | size:5.8KB | last_modified:2025-05-31
/COMPREHENSIVE_PARALLEL_TESTING_PLAN.md | purpose:testing_strategy | context:HUMAN | status:CURRENT | size:46.4KB | last_modified:2025-05-31
/architecture/README.md | purpose:architecture_overview | context:HUMAN | status:CURRENT | size:6.0KB | refs:medium
/architecture/data_model.md | purpose:data_structures | context:HUMAN | status:CURRENT | size:12.2KB | refs:medium
/architecture/performance_requirements.md | purpose:performance_specs | context:HUMAN | status:CURRENT | size:3.4KB | refs:low
/architecture/security_model.md | purpose:security_design | context:HUMAN | status:CURRENT | size:5.0KB | refs:low
/docs/api/API-REFERENCE.md | purpose:api_documentation | context:HUMAN | status:CURRENT | size:20.2KB | refs:medium
/docs/DEPLOYMENT-GUIDE.md | purpose:deployment_guide | context:HUMAN | status:CURRENT | size:22.7KB | refs:medium
/docs/development/TESTING-GUIDE.md | purpose:testing_procedures | context:HUMAN | status:CURRENT | size:33.6KB | refs:medium
/docs/configuration/ENVIRONMENT-VARIABLES.md | purpose:env_config | context:HUMAN | status:CURRENT | size:9.1KB | refs:low
/ai_docs/README.md | purpose:tech_catalog | context:HUMAN | status:CURRENT | size:3.8KB | refs:medium
/ai_docs/qdrant.md | purpose:vector_search_ref | context:HUMAN | status:CURRENT | size:51.0KB | refs:low
/ai_docs/jedi.md | purpose:python_analysis_ref | context:HUMAN | status:CURRENT | size:35.2KB | refs:low
/ai_docs/grpc_overview.md | purpose:rpc_framework_ref | context:HUMAN | status:CURRENT | size:34.0KB | refs:low
/tests/README.md | purpose:test_documentation | context:HUMAN | status:CURRENT | size:12.3KB | refs:low
/mcp_server/benchmarks/README.md | purpose:benchmark_guide | context:HUMAN | status:CURRENT | size:6.7KB | refs:low
```

### MAINTENANCE_REQUIRED (4 files)
```
/CHANGELOG.md | purpose:version_history | context:HUMAN | status:STALE | size:1.7KB | action:UPDATE_WHEN_RELEASED | issue:no_released_versions
/docs/history/ARCHITECTURE_ALIGNMENT_REPORT.md | purpose:historical_analysis | context:HUMAN | status:STALE | size:4.1KB | action:ARCHIVE | last_modified:2025-01-29
/docs/history/IMPLEMENTATION_GAP_ANALYSIS.md | purpose:gap_analysis | context:HUMAN | status:STALE | size:4.6KB | action:ARCHIVE | last_modified:2025-01-29
/docs/history/PHASE1_COMPLETION_SUMMARY.md | purpose:phase1_status | context:HUMAN | status:STALE | size:2.8KB | action:ARCHIVE | last_modified:2025-01-29
```

## AGENT_ACTIONS

### IMMEDIATE_CLEANUP
```bash
# No immediate cleanup needed - all files serve current purposes
# Historical docs should be archived when convenient, not deleted
```

### CONSOLIDATION_TASKS
```
NO_MERGES_NEEDED: CLAUDE.md navigation pattern is intentional design
KEEP_SEPARATE: Plugin AGENTS.md files have unique implementation details
PRESERVE_STRUCTURE: Current documentation hierarchy supports both AI and human contexts
```

### CONTENT_UPDATES_NEEDED
```
CHANGELOG.md | STALE | Update when first version is released
docs/history/*.md | STALE | Archive to separate historical directory when convenient
ai_docs/README.md | CURRENT | Consider adding recently enhanced plugin documentation references
```

## SEMANTIC_CLUSTERS
```
agent_configuration: [CLAUDE.md, AGENTS.md, architecture/AGENTS.md, mcp_server/AGENTS.md]
plugin_documentation: [mcp_server/plugins/*/AGENTS.md, mcp_server/plugins/*/CLAUDE.md]
project_management: [README.md, ROADMAP.md, CONTRIBUTING.md, CHANGELOG.md]
architecture_docs: [architecture/README.md, architecture/data_model.md, architecture/performance_requirements.md, architecture/security_model.md]
deployment_guides: [docs/DEPLOYMENT-GUIDE.md, docs/configuration/ENVIRONMENT-VARIABLES.md]
testing_framework: [TESTING_VALIDATION_REPORT.md, COMPREHENSIVE_PARALLEL_TESTING_PLAN.md, docs/development/TESTING-GUIDE.md, tests/README.md]
technology_references: [ai_docs/*.md]
project_status: [DORMANT_FEATURES_ACTIVATION.md, TESTING_VALIDATION_REPORT.md, ROADMAP.md]
```

## REFERENCE_MAP
```
# High-priority reference targets (frequently linked)
README.md ← [CONTRIBUTING.md, DEPLOYMENT-GUIDE.md, multiple plugin docs]
AGENTS.md ← [CLAUDE.md, all plugin CLAUDE.md stubs]
ROADMAP.md ← [README.md, architecture docs, project status reports]
CONTRIBUTING.md ← [README.md, plugin documentation]

# Agent navigation pattern (by design)
CLAUDE.md → AGENTS.md (main entry point)
architecture/CLAUDE.md → architecture/AGENTS.md
mcp_server/CLAUDE.md → mcp_server/AGENTS.md
plugins/*/CLAUDE.md → plugins/*/AGENTS.md (6 instances)

# Cross-domain references
API-REFERENCE.md ← [DEPLOYMENT-GUIDE.md, plugin docs]
TESTING-GUIDE.md ← [CONTRIBUTING.md, TESTING_VALIDATION_REPORT.md]
```

## CONTENT_GAPS
```
# Missing documentation that should exist based on codebase analysis
MISSING: Plugin development tutorial using Python plugin as reference template
MISSING: Migration guide from development to production deployment
NEEDED: Performance benchmark results (framework exists but no published results)
FUTURE: API endpoint examples with actual request/response samples
FUTURE: Troubleshooting guide for production deployment issues
```

## PROJECT_STATUS_INDICATORS
```
IMPLEMENTATION_COMPLETION: 95% (from TESTING_VALIDATION_REPORT.md)
LAST_MAJOR_UPDATE: 2025-05-31 (comprehensive testing validation)
PLUGIN_STATUS: 6/6 language plugins implemented and enhanced
TESTING_STATUS: 377+ test files with parallel execution framework
DOCUMENTATION_HEALTH: 94% current, 6% historical
DEPLOYMENT_READINESS: Production configurations implemented
```

## AGENT_PROMPTS
```
# For AI agents starting work:
"Check AGENTS.md for primary configuration, then consult relevant plugin AGENTS.md for language-specific work"

# For plugin development:
"Reference mcp_server/plugins/python_plugin/AGENTS.md as the template implementation, then enhance other plugins following the same pattern"

# For architecture work:
"Use architecture/AGENTS.md for C4 model operations and consult architecture/data_model.md for current system design"

# For testing:
"Follow TESTING_VALIDATION_REPORT.md for current status and COMPREHENSIVE_PARALLEL_TESTING_PLAN.md for framework usage"

# For documentation updates:
"Maintain CLAUDE.md→AGENTS.md navigation pattern. Add new content to existing AGENTS.md files rather than creating new documentation"
```

## NAVIGATION_PATTERNS
```
# Standard AI agent entry points
MAIN_ENTRY: /CLAUDE.md → /AGENTS.md
ARCHITECTURE: /architecture/CLAUDE.md → /architecture/AGENTS.md  
SERVER: /mcp_server/CLAUDE.md → /mcp_server/AGENTS.md
PLUGINS: /mcp_server/plugins/{lang}/CLAUDE.md → /mcp_server/plugins/{lang}/AGENTS.md

# Human developer entry points
PROJECT_START: README.md → CONTRIBUTING.md → ROADMAP.md
DEVELOPMENT: docs/development/TESTING-GUIDE.md → CONTRIBUTING.md
DEPLOYMENT: docs/DEPLOYMENT-GUIDE.md → docs/configuration/ENVIRONMENT-VARIABLES.md
TROUBLESHOOTING: TROUBLESHOOTING.md → docs/history/ (if needed)
```

## RECENT_ACTIVITY_SUMMARY
```
2025-05-31: Major testing validation completed, comprehensive parallel testing framework implemented
2025-05-31: All 6 plugin AGENTS.md files enhanced with Claude Code best practices
2025-05-31: DORMANT_FEATURES_ACTIVATION.md created for advanced feature enablement
2025-05-30: Multiple AGENTS.md files updated with current implementation status
2025-05-30: Project status updated to 95% completion from previous 65%

NEXT_PRIORITIES:
1. Complete remaining 5% implementation (primarily C++ plugin details)
2. Publish first release version and update CHANGELOG.md
3. Create plugin development tutorial
4. Archive historical documentation
5. Add performance benchmark results
```