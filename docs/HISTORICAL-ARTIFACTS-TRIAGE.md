# Historical Artifacts Triage Log

P8 SL-3 sweep — 2026-04-18. All 49 files in scope bannered; 0 deleted. All 16 scout-candidate deletions downgraded due to nav-coupling hit in `docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md` (inside grep set `docs/`). No rewrite eligible (<100 LOC + active callers) files found.

### docs/implementation/

| Path | Disposition | Rationale | As-of |
|------|-------------|-----------|-------|
| `docs/implementation/ADAPTIVE_CHUNKING_IMPLEMENTATION.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; describes adaptive_chunking module still present in mcp_server | 2026-04-18 |
| `docs/implementation/ALIGNMENT_PLAN_2025-01-06.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; design discussion snapshot of 2025-01 alignment plan | 2026-04-18 |
| `docs/implementation/BM25_HYBRID_SEARCH_IMPLEMENTATION.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; hybrid_search module still present in mcp_server/indexer | 2026-04-18 |
| `docs/implementation/COMPATIBILITY_TESTING_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical test snapshot | 2026-04-18 |
| `docs/implementation/CONTEXTUAL_EMBEDDINGS_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; contextual_embeddings module still present | 2026-04-18 |
| `docs/implementation/DOCUMENTATION_UPDATE_REPORT_2025-01-06-FINAL.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical doc-update snapshot | 2026-04-18 |
| `docs/implementation/DOCUMENTATION_UPDATE_REPORT_2025-01-06.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical doc-update snapshot | 2026-04-18 |
| `docs/implementation/DOCUMENTATION_UPDATE_REPORT_2025-06-10.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical doc-update snapshot | 2026-04-18 |
| `docs/implementation/GIT_HOOKS_IMPLEMENTATION_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; git hooks still referenced in IMPLEMENTATION_SUMMARY | 2026-04-18 |
| `docs/implementation/IMPLEMENTATION_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/markdown-table-of-contents.md and docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md | 2026-04-18 |
| `docs/implementation/INDEX_MANAGEMENT_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/markdown-table-of-contents.md and docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; index management code active | 2026-04-18 |
| `docs/implementation/MCP_SEARCH_STRATEGY_SUMMARY.md` | bannered | Subject (search strategy) active in mcp_server/dispatcher; nav-coupling in docs/ | 2026-04-18 |
| `docs/implementation/MCP_VERIFICATION_IMPLEMENTATION_SUMMARY.md` | bannered | Nav-coupling hit in docs/markdown-table-of-contents.md; scripts/verify_mcp_retrieval.py and tests still present | 2026-04-18 |
| `docs/implementation/MCP_VERIFICATION_TEST_RESULTS.md` | bannered | Subject (mcp verification) still in scripts/verify_mcp_retrieval.py and tests; historical benchmark snapshot | 2026-04-18 |
| `docs/implementation/PATH_MANAGEMENT_IMPLEMENTATION_PLAN.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; design discussion | 2026-04-18 |
| `docs/implementation/PATH_MANAGEMENT_IMPLEMENTATION_SUMMARY.md` | bannered | Scout candidate; nav-coupling hit in docs/markdown-table-of-contents.md and docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md | 2026-04-18 |
| `docs/implementation/PHASE3_CONTEXTUAL_EMBEDDINGS_SUMMARY.md` | bannered | Subject (contextual embeddings) active in mcp_server/document_processing; historical phase snapshot | 2026-04-18 |
| `docs/implementation/PRODUCTIONIZATION_PLAN_2026-02.md` | bannered | Design discussion; no code subject found but document is a design artifact worth preserving as-of | 2026-04-18 |
| `docs/implementation/PROJECT_COMPLETION_SUMMARY.md` | bannered | Nav-coupling hit in docs/markdown-table-of-contents.md; historical completion snapshot | 2026-04-18 |
| `docs/implementation/RERANKING_TEST_REPORT.md` | bannered | Subject (reranking) active in mcp_server/utils/semantic_indexer.py; historical benchmark result | 2026-04-18 |

### docs/status/

| Path | Disposition | Rationale | As-of |
|------|-------------|-----------|-------|
| `docs/status/COMPREHENSIVE_TEST_SUITE_SUMMARY.md` | bannered | Subject active in scripts/comprehensive_mcp_test_runner.py and mcp_server/benchmarks; historical snapshot | 2026-04-18 |
| `docs/status/DEBUG_AND_FIX_PLAN.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical debug snapshot | 2026-04-18 |
| `docs/status/DOCKER_SETUP_REVIEW.md` | bannered | Subject (docker/health check) active in mcp_server/utils/mcp_health_check.py; historical snapshot | 2026-04-18 |
| `docs/status/DOCUMENT_PROCESSING_TEST_REPORT.md` | bannered | Subject (document processing) active in mcp_server/plugins; historical test report | 2026-04-18 |
| `docs/status/DOCUMENT_PROCESSING_VALIDATION_REPORT.md` | bannered | Subject (document processing) active in mcp_server/plugins; historical validation snapshot | 2026-04-18 |
| `docs/status/DOCUMENT_PROCESSING_VALIDATION_SUMMARY.md` | bannered | Subject (document processing) active in mcp_server/plugins; historical validation snapshot | 2026-04-18 |
| `docs/status/DOCUMENT_QUERY_ENHANCEMENT_SUMMARY.md` | bannered | Subject active in mcp_server/dispatcher/dispatcher_enhanced.py and tests; historical snapshot | 2026-04-18 |
| `docs/status/EDGE_CASE_TESTS_SUMMARY.md` | bannered | Subject active in scripts/utilities/verify_reranking_tests.py and tests; historical snapshot | 2026-04-18 |
| `docs/status/implementation-validation-report.md` | bannered | Nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical validation snapshot | 2026-04-18 |
| `docs/status/MARKDOWN_PLUGIN_SUMMARY.md` | bannered | Subject active in mcp_server/plugins/markdown_plugin; historical snapshot | 2026-04-18 |
| `docs/status/MCP_COMPREHENSIVE_VALIDATION_REPORT.md` | bannered | Subject active in mcp_server/dispatcher and mcp_server/storage; historical validation snapshot | 2026-04-18 |
| `docs/status/MCP_VALIDATION_SUMMARY.md` | bannered | Subject active in mcp_server/dispatcher and mcp_server/storage; historical snapshot | 2026-04-18 |
| `docs/status/PHASE2_COMPLETION_SUMMARY.md` | bannered | Subject (phase2) referenced in scripts/parallel_claude_integration.py; historical phase snapshot | 2026-04-18 |
| `docs/status/PLAINTEXT_PLUGIN_SUMMARY.md` | bannered | Subject active in mcp_server/plugins/plugin_factory.py and tests; historical snapshot | 2026-04-18 |
| `docs/status/SEMANTIC_INDEXER_ENHANCEMENTS.md` | bannered | Subject active in mcp_server/utils/semantic_indexer.py; historical snapshot | 2026-04-18 |
| `docs/status/SEMANTIC_SEARCH_COMPLETE.md` | bannered | Subject active in mcp_server/dispatcher and mcp_server/indexer/hybrid_search.py; historical snapshot | 2026-04-18 |
| `docs/status/SPECIALIZED_PLUGINS_REPORT.md` | bannered | Subject active in mcp_server/plugins/specialized_plugin_base.py; historical snapshot | 2026-04-18 |
| `docs/status/SWIFT_PLUGIN_SUMMARY.md` | bannered | Subject active in mcp_server/plugins/plugin_factory.py and tests; historical snapshot | 2026-04-18 |
| `docs/status/TEST_SUITE_DEBUG_REPORT.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical debug snapshot | 2026-04-18 |
| `docs/status/TEST_SUITE_IMPLEMENTATION_REPORT.md` | bannered | Scout candidate; nav-coupling hit in docs/DOCUMENTATION_FILES_TO_CONSOLIDATE.md; historical test report | 2026-04-18 |

### docs/validation/

| Path | Disposition | Rationale | As-of |
|------|-------------|-----------|-------|
| `docs/validation/comprehensive-test-report.md` | bannered | Subject active in mcp_server/benchmarks and scripts; historical test report snapshot | 2026-04-18 |
| `docs/validation/document-processing-validation.md` | bannered | Subject (document processing) active in mcp_server/plugins; historical validation snapshot | 2026-04-18 |
| `docs/validation/ga-e2e-evidence.md` | bannered | GAE2E evidence artifact; current end-to-end release readiness and live workflow state must be rechecked before GA or follow-up release decisions | 2026-04-18 |
| `docs/validation/ga-final-decision.md` | bannered | GAREL decision artifact; current GA release posture and recut dispatch readiness must be rechecked before release decisions | 2026-04-24 |
| `docs/validation/private-alpha-decision.md` | bannered | P26 redacted private-alpha decision artifact; current release gating pointer is maintained by P26 tests | 2026-04-18 |
| `docs/validation/ga-closeout-decision.md` | bannered | GACLOSE decision artifact; current release, governance, readiness, and production-matrix evidence must be rechecked before GA or follow-up release decisions | 2026-04-18 |
| `docs/validation/ga-governance-evidence.md` | bannered | GAGOV governance evidence artifact; current branch protection, ruleset, release-channel, and required-gate state must be rechecked from GitHub before GA or follow-up release decisions | 2026-04-18 |
| `docs/validation/ga-operations-evidence.md` | bannered | GAOPS evidence artifact; current operator preflight, observability, rollback, and support-boundary results must be rechecked before GA or follow-up release decisions | 2026-04-24 |
| `docs/validation/ga-rc-evidence.md` | bannered | GARC evidence artifact; current RC soak and release-dispatch readiness must be rechecked before cutting or promoting a release candidate | 2026-04-24 |
| `docs/validation/ga-readiness-checklist.md` | bannered | GABASE checklist artifact; downstream GA-hardening phases consume its frozen release boundary, support-tier labels, evidence ownership, and rollback expectations | 2026-04-18 |
| `docs/validation/ga-release-evidence.md` | bannered | GADISP release evidence artifact; current stable release, registry, and GitHub Latest state must be rechecked from live publication surfaces before future release decisions | 2026-04-25 |
| `docs/validation/mrready-rollout-readiness.md` | bannered | MRREADY rollout readiness artifact; current multi-repo rollout posture must be rechecked before broader deployment decisions | 2026-04-25 |
| `docs/validation/mre2e-evidence.md` | bannered | MRE2E multi-repo hydration evidence artifact; current hydration acceptance and rollout posture must be rechecked before broader multi-repo deployment decisions | 2026-04-25 |
| `docs/validation/rc5-release-evidence.md` | bannered | RC5 release execution evidence artifact; current release state must be rechecked from GitHub Actions and registry surfaces | 2026-04-18 |
| `docs/validation/release-governance-evidence.md` | bannered | RELGOV release governance evidence artifact; current branch protection, ruleset, and release-channel state must be rechecked from GitHub before release decisions | 2026-04-18 |
| `docs/validation/secondary-tool-readiness-evidence.md` | bannered | TOOLRDY secondary-tool readiness evidence artifact; current repository-scoped mutation and summarization readiness must be rechecked before GA decisions | 2026-04-18 |
| `docs/validation/system-validation-report.md` | bannered | Benchmark result snapshot with actual performance numbers; no code subject found but qualifies as benchmark result worth preserving | 2026-04-18 |
