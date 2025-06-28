# Markdown Documentation Index with AI Agent Optimization
**Generated**: January 6, 2025  
**Mode**: AI_AGENT_DEVELOPMENT_GUIDE  
**Project**: Code-Index-MCP (Local-first Code Indexer)

## CRITICAL_AGENT_INSTRUCTIONS
- ✅ All CLAUDE.md files properly migrated to AGENTS.md pattern
- 🔴 **CRITICAL**: MCP sub-agent tool inheritance broken (83% failure rate) - See ROADMAP.md
- Check ARCHITECTURE_ALIGNMENT before implementation
- Follow COMPLEXITY_ORDERING for task selection  
- Reference AI_DOCS_REQUIRED for framework context

## ARCHITECTURAL_ALIGNMENT_STATUS
```
OVERALL_ALIGNMENT: 751% (406 implemented / 54 planned components)
STATUS: Over-implemented - Many components exist beyond original architecture

C4_LEVEL_COVERAGE:
DSL (L1-3):
  - /workspaces/Code-Index-MCP/architecture/workspace.dsl (Main system design)
  
PlantUML (L4) - 43 diagrams:
  - Recent additions for MCP issues:
    - mcp_sub_agent_architecture.puml (NEW)
    - mcp_configuration_flow.puml (NEW)
    - index_path_resolution.puml (NEW)
    - enhanced_dispatcher.puml (UPDATED)
  - Plugin diagrams: 16 language-specific
  - System components: 27 infrastructure

DIVERGENCE_LOG:
- Planned components: 54
- Implemented services/components: 406
- Plugin count: 16 (expected ~48 based on language support claims)
- Over-implementation suggests organic growth beyond initial design
```

## CLAUDE_MD_MIGRATION_STATUS
```
STATUS: ✅ FULLY COMPLIANT
Total CLAUDE.md files: 11
All files are pure pointers to AGENTS.md

Compliant Files:
- /workspaces/Code-Index-MCP/CLAUDE.md → AGENTS.md
- /workspaces/Code-Index-MCP/architecture/CLAUDE.md → AGENTS.md
- /workspaces/Code-Index-MCP/mcp_server/CLAUDE.md → AGENTS.md
- /workspaces/Code-Index-MCP/mcp_server/plugins/*/CLAUDE.md → AGENTS.md (8 files)

Exception:
- /workspaces/Code-Index-MCP/test_repos/jvm/kotlin/ktor/CLAUDE.md (Contains build commands - test data)
```

## ROADMAP_COMPLEXITY_MATRIX

### 🔴 CRITICAL - MCP Infrastructure Fixes [Complexity: 5]
- **Status**: Not Started - BLOCKING PRODUCTION
- **Issue**: 83% failure rate for MCP tools in sub-agents
- **Impact**: Native tools recommended for production use
- **Actions**:
  1. Fix sub-agent tool inheritance
  2. Implement robust index discovery
  3. Create pre-flight validation system
  4. Develop index management CLI

### Current Implementation Status
- **Overall**: 95% Complete (Production Ready*)
- **Complexity**: 5/5 (136k lines, 48 plugins, semantic search)
- ***Critical Issue**: MCP sub-agent failures require immediate attention

### Recently Completed [Complexity: 4-5]
- ✅ MCP Dispatcher Fixes (timeout protection, BM25 bypass)
- ✅ Local Index Storage (centralized at .indexes/)
- ✅ Directory Structure Refactoring
- ✅ Git Repository Synchronization
- ✅ Qdrant Server Mode enhancements

### Active Development [Complexity: 3-4]
- 🚀 Document Processing Plugins (Markdown, PlainText)
- 🔧 Specialized Language Plugins (Java, Go, Rust, TypeScript, C#, Swift, Kotlin)

## AI_DOCS_STATUS
```
FRAMEWORK_COVERAGE: Good
Total AI docs: 22 files
Staleness: No files older than 30 days (all current)

Covered Frameworks:
- FastAPI ✅ (main API framework)
- Pydantic ✅ (data validation)
- SQLite FTS5 ✅ (search backend)
- Tree-sitter ✅ (parsing engine)
- Qdrant ✅ (vector database)
- Docker ✅ (deployment)
- Pytest ✅ (testing)
- Redis ✅ (caching)
- MCP ✅ (Model Context Protocol)

Missing Documentation:
- Django (detected in test repos but no docs)
- React (detected in test repos but no docs)
- Express (not detected but common)
- Flask (not detected but common)
```

## IMPLEMENTATION_READY_COMPONENTS

### High Priority (Based on ROADMAP + Test Results)
1. **MCP Sub-Agent Fix** [CRITICAL]
   - Location: mcp_server/gateway.py, mcp_server/dispatcher/
   - Issue: Tool inheritance not working
   - Test data: FINAL_COMPREHENSIVE_MCP_VS_NATIVE_REPORT.md

2. **Index Discovery Enhancement** [CRITICAL]
   - Location: mcp_server/utils/index_discovery.py
   - Issue: Only checks single path
   - Architecture: index_path_resolution.puml

3. **Document Processing Plugins** [Active]
   - Markdown: mcp_server/plugins/markdown_plugin/
   - PlainText: mcp_server/plugins/plaintext_plugin/
   - Status: Partially implemented

### Plugin Implementation Status
```
Implemented: 16 plugins
Expected: 48 (based on claims)
Gap: 32 plugins missing or not fully integrated

Key Missing Plugins:
- Ruby, Perl, PHP (scripting languages)
- Haskell, Elixir, F# (functional)
- Objective-C (mobile)
- Many generic tree-sitter languages
```

## DOCUMENTATION_STRUCTURE

### Core Documentation
- **README.md**: Main project overview (997 lines)
- **ROADMAP.md**: Development roadmap (796 lines) - CRITICAL UPDATES
- **ARCHITECTURE_UPDATE_SUMMARY_2025-01-06.md**: Recent architecture changes

### Architecture Documentation
- **workspace.dsl**: C4 model system design (398 lines)
- **43 PlantUML diagrams**: Component-level details
- **Implementation status**: Over 751% of planned components

### AI Framework Documentation (/ai_docs)
- 22 framework overviews (all current)
- Good coverage of core technologies
- Missing some web framework docs

### Implementation Documentation (/docs)
- **implementation/**: 19 detailed summaries
- **status/**: 18 progress reports
- **reports/**: 7 test/verification reports
- **Recent**: MCP performance test results

## AI_PLATFORM_GUIDANCE_SYNC
```
PLATFORM_CONSISTENCY:
- CLAUDE.md files: 11 (all compliant pointers)
- AGENTS.md files: 11 (contain actual guidance)
- .cursor/rules/: Not found in current structure

RECOMMENDED_SYNC:
1. All CLAUDE.md files properly point to AGENTS.md ✅
2. Consider adding .cursor/rules/ for Cursor IDE users
3. Maintain consistency between AGENTS.md files
```

## NEXT_IMPLEMENTATION_GUIDANCE

### Immediate Actions (This Week)
1. **Fix MCP Sub-Agent Tool Inheritance** [Complexity: 5]
   - Review mcp_configuration_flow.puml
   - Implement config passing to Task agents
   - Add pre-flight validation
   - Target: 95%+ success rate

2. **Implement Multi-Path Index Discovery** [Complexity: 4]
   - Update index_discovery.py
   - Check multiple paths (.indexes/, test_indexes/, etc.)
   - Handle Docker vs native paths
   - Add detailed error messages

3. **Complete Document Processing Plugins** [Complexity: 3]
   - Finish Markdown plugin implementation
   - Complete PlainText NLP features
   - Add comprehensive tests

### Next Sprint
4. **Create Index Management CLI** [Complexity: 3]
   - claude-index create/validate/list/migrate commands
   - Path translation utilities
   - Cross-environment support

5. **Update Documentation** [Complexity: 2]
   - Create MCP troubleshooting guide
   - Document sub-agent configuration
   - Update production deployment guide

### Architecture Governance
- **Mode**: DOCUMENT_ONLY (existing architecture detected)
- **Action**: Document divergences, don't modify architecture
- **Note**: 751% implementation vs plan suggests need for architecture review

## KEY_INSIGHTS

1. **Production Readiness**: System is 95% complete but MCP has critical issues
2. **Recommendation**: Use native tools until MCP fixes are implemented
3. **Over-Implementation**: 406 components vs 54 planned indicates organic growth
4. **Documentation**: Well-maintained, current, and comprehensive
5. **Test Coverage**: Extensive real-world testing revealed MCP issues

## REFERENCES
- Performance Test Report: `/FINAL_COMPREHENSIVE_MCP_VS_NATIVE_REPORT.md`
- Architecture Updates: `/ARCHITECTURE_UPDATE_SUMMARY_2025-01-06.md`
- Roadmap: `/ROADMAP.md` (with critical MCP issue updates)
- MCP Diagrams: `/architecture/level4/mcp_*.puml`