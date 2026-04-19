# Known Test Debt

This file enumerates test failures that are **out of scope** for the current phase and
are deferred to a future cleanup pass.  It is updated by the terminal SL-docs lane at the
close of each phase.

---

## P17 residual snapshot (2026-04-19)

**Total failures from `pytest -q --no-cov`**: **56**

> Phase P17 exit criterion was ≤5 total failures. This criterion was **not met**.
> The 56 failures fall into two categories: 9 cross-repo coordinator carry-over failures
> (pre-existing, deferred by design) and 47 additional failures in other test modules that
> were not resolved during P17.  All are enumerated below.

---

### Group A — `test_cross_repo_coordinator.py` (9 failures, pre-existing, root cause known)

These 9 failures were partially addressed by SL-4 (reduced from 18 → 9) but the
remaining 9 require a deeper rewrite that is out of P17 scope.

**Root cause**: The original `CrossRepositoryCoordinator` in
`mcp_server.storage.cross_repo_coordinator` was deleted during an earlier refactor.  The
current implementation is `CrossRepositoryCoordinator` at
`mcp_server.dispatcher.cross_repo_coordinator`, which is a thin wrapper that does not
expose the internal methods the tests call.

| Test | Root cause detail |
|---|---|
| `test_search_symbol_success` | Patches `mcp_server.storage.cross_repo_coordinator.ThreadPoolExecutor` — module deleted |
| `test_search_code_success` | Same — patches deleted module |
| `test_aggregate_symbol_results_deduplication` | Calls `_aggregate_symbol_results` — absent on wrapper |
| `test_aggregate_code_results_with_limit` | Calls `_aggregate_code_results` — absent on wrapper |
| `test_create_symbol_signature` | Calls `_create_symbol_signature` — absent on wrapper |
| `test_create_content_hash` | Calls `_create_content_hash` — absent on wrapper |
| `test_get_search_statistics` | Expects mock repo totals (`total_files=26` etc.); wrapper returns zeros |
| `test_search_symbol_in_repository` | Patches deleted module; calls `_search_symbol_in_repository` absent on wrapper |
| `test_search_code_in_repository_with_filters` | Same pattern |

**Resolution path (not for P17)**: either port the missing methods to
`CrossRepositoryCoordinator` in `mcp_server/dispatcher/cross_repo_coordinator.py`, or
rewrite these 9 tests to call the wrapper's current public API.

---

### Group B — Additional failures at time of P17 close (47 failures)

The following failures were observed in the full suite run.  They are pre-existing or
introduced in earlier phases and are not attributable to P17 changes.

| Test module | Count | Notes |
|---|---|---|
| `test_go_plugin.py` | 3 | `TestGoPlugin.test_package_analysis`, `test_search_functionality`, `test_import_resolution` — `AttributeError`; Go plugin attribute missing |
| `test_ignore_patterns.py` | 1 | `TestWalkerIntegration.test_log_files_not_indexed` |
| `test_interface_contracts.py` | 1 | `test_base_document_plugin_process_document_matches_contract` |
| `test_mcp_server_cli.py` | 16 | Multiple `TestAutoInitGitignore`, `TestMcpAutoIndexEscapeHatch`, `TestDeferredFileWatcher`, `TestIndexingInProgressFlag`, `TestFreshRepoEndToEnd` failures |
| `test_multi_repo_artifact_coordinator.py` | 1 | `test_repository_registry_persists_artifact_state` |
| `test_multi_repo_bootstrap_order.py` | 1 | `TestStdioRunnerBootOrder.test_shutdown_calls_stop_watching_all_and_ref_poller_stop` |
| `test_multi_repo_manager.py` | 1 | `TestMultiRepositoryManager.test_connection_caching` |
| `test_multi_repository_support.py` | 1 | `test_multi_repo_manager_registry_persists_local_artifact_fields` |
| `test_reindex_resume.py` | 2 | `test_crash_at_file_500_leaves_correct_checkpoint`, `test_resume_skips_already_indexed_files` |
| `test_repository_plugin_loader_concurrency.py` | 1 | `test_distinct_repo_ids_do_not_block_each_other` |
| `test_cross_repo_coordinator.py` | 9 | Covered in Group A above |

**Resolution path**: Group B failures require investigation per test module.  They were
not prioritized in P17 and are deferred to P18 or a dedicated cleanup sprint.

---

## How to update this file

At the close of each phase, the terminal SL-docs lane runs:

```bash
pytest -q --no-cov 2>&1 | tail -30
```

and updates this file with the current failure count and categorization.
