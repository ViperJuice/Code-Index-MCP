# Known Test Debt

This file enumerates test failures that are **out of scope** for the current phase and
are deferred to a future cleanup pass.  It is updated by the terminal SL-docs lane at the
close of each phase.

---

## P18 residual snapshot (2026-04-20, post-SL-6)

**Total failures from `pytest -q --no-cov --ignore=tests/real_world`**: **4**

> P18 SL-6 burned the P17 carry-over from 19 → 4 (79% reduction).
> P17 clusters (`test_mcp_server_cli.py` 17 + `test_benchmarks.py` 2) and
> `SandboxedPlugin._ctx` contract are fully resolved.
> The 4 remaining failures require a `gh` CLI token with `attestations:write` scope
> (environment-dependent) and a P16-era vocabulary update; both are out of SL-6 scope.

### Remaining clusters

| Cluster | Count | Root cause | Resolution path |
|---|---|---|---|
| `tests/security/test_artifact_attestation.py::TestAttest` | 3 | Requires `gh` CLI token with `attestations:write` scope. `attest()` raises `AttestationError: ATTESTATION_PREREQ` when token lacks this scope. Environment-dependent; not a code defect. | Either add `@pytest.mark.skipif` for missing scope, or provision a test token with the scope. |
| `test_p16_vocabulary.py::test_validate_production_config_signature` | 1 | Production config signature mismatch; P16-era vocabulary test failure. | Update config signature or test expectation. |

### SL-6 resolved (P17 carry-overs)

| Cluster | Count | Resolved by |
|---|---|---|
| `test_mcp_server_cli.py` (17 tests) | 17 | Promoted module-level globals + `initialize_services()` + `call_tool()` to `stdio_runner.py`; pointed `CLI_PATH` at `stdio_runner.py` |
| `test_benchmarks.py::test_benchmark_symbol_lookup_performance` | 1 | Pre-seeded `_plugin_set_registry._cache` in `BenchmarkSuite.__init__`; populated sqlite store with test symbols |
| `test_benchmarks.py::test_benchmark_search_performance` | 1 | Same sqlite store population fix; BM25 `fts_code` table now has searchable content |

### SL-4b resolved (P17 pre-burn-down carry-overs)

| Cluster (from pre-SL-4b baseline) | Count | Resolved by |
|---|---|---|
| `test_cross_repo_coordinator.py` (Group A) | 9 | `f36fad4` — ported cross-repo coordinator methods to wrapper |
| `test_go_plugin.py` | 3 | `9d79870` — restored `_sqlite_store` on `GoPlugin` |
| `test_reindex_resume.py` | 2 | `9d79870` — aligned resume tests with SL-2 `_clear_ckpt` semantics |
| `test_ignore_patterns.py` | 1 | `cdc299d` — exercise `build_walker_filter` directly |
| `test_interface_contracts.py` | 1 | `cdc299d` — mirror GoPlugin fix on `GenericTreeSitterPlugin` |
| `test_multi_repo_manager.py` | 1 | `cdc299d` — mock `ConnectionPool` alongside `SQLiteStore` |
| `test_multi_repo_artifact_coordinator.py` | 1 | `cdc299d` — walk `list_all()` (registry re-keys legacy ids) |
| `test_multi_repository_support.py` | 1 | `cdc299d` — same registry re-keying fix |
| `test_multi_repo_bootstrap_order.py` | 1 | `cdc299d` — assert `.stop()` instead of `.stop_watching_all()` |
| `test_cross_repo_coordinator.py` (dispatcher retarget) | — | `0c26ade` — deleted storage shim; retargeted patches to dispatcher module |
| `test_dispatcher_advanced.py::TestRemoveFileSemanticCleanup` | 3 | `0c26ade` — stubbed missing dispatcher attrs in test helper |
| Benchmark init-order (7 of 9) | — | `0c26ade` — moved misplaced init out of unreachable block |
| `test_repository_plugin_loader_concurrency.py` | 1 | `7395fb4` — `asyncio.new_event_loop()` replaces deprecated `get_event_loop()` |

---

## P17 pre-SL-4b baseline (2026-04-19, pre-burn-down)

The following snapshot is retained for history.  **Current state is the 5-failure
snapshot above.**

**Total failures from `pytest -q --no-cov`**: **56**

Group A — `test_cross_repo_coordinator.py` (9 failures): **resolved** by `f36fad4`.
Root cause was that the tests patched `mcp_server.storage.cross_repo_coordinator`
(deleted) and called methods (`_aggregate_*`, `_search_*_in_repository`, etc.) that
only lived on the deleted implementation.  The wrapper in
`mcp_server.dispatcher.cross_repo_coordinator` was extended with those methods.

Group B — 47 additional failures at P17 close: **12 of 13 clusters resolved**; see
"SL-4b resolved" table above.  The surviving cluster (`test_mcp_server_cli.py`,
17 tests) was originally miscounted as 16 in this ledger.

---

## How to update this file

At the close of each phase, the terminal SL-docs lane runs:

```bash
pytest -q --no-cov 2>&1 | tail -30
```

and updates this file with the current failure count and categorization.
