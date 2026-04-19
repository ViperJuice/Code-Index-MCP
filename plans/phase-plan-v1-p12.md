# P12: Ops Readiness + Reindex Safety

## Context

P11 merged: dispatcher first-hit fallback (`run_gated_fallback`), bounded timeout (`MCP_DISPATCHER_FALLBACK_MS`), and the `dispatcher_fallback_histogram` accessor on `PrometheusExporter` are live. P12 builds on that hardening with five small, high-leverage safety nets that make the service kubernetes-deployable and stop silent reindex drift.

What exists today:
- `mcp_server/gateway.py` — single FastAPI app instance at `:80-83`; routes registered inline via `@app.get`/`@app.post`. Existing `/health`, `/health/detailed`, `/health/{component}` routes live at `:1033-1084`. Module-global `dispatcher`, `sqlite_store`, `_repo_registry` populated in `startup_event()`.
- `mcp_server/health/` — only `repo_status.py::build_health_row(repo_info)`; no aggregated health-view module.
- `mcp_server/metrics/health_check.py` — `ComponentHealthChecker` singleton via `get_health_checker()`; reusable from `HealthView.snapshot()`.
- `mcp_server/watcher_multi_repo.py` — three handler methods (`_trigger_reindex_with_ctx` `:141-168`, `_remove_with_ctx` `:171-185`, `_move_with_ctx` `:187-198`), `_sync_repository` + `on_git_commit` (`:363-402`), `sync_all_repositories` (`:442-458`). No per-repo lock; no `enqueue_full_rescan` method.
- `mcp_server/storage/git_index_manager.py:15-19` — `should_reindex_for_branch(current, tracked)` returns equality only when both non-None; silent on drift.
- `mcp_server/metrics/prometheus_exporter.py:58` — bucket tuple `(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)` shared with P11. `dispatcher_fallback_histogram` accessor with `if PROMETHEUS_AVAILABLE:` guard at init; attribute set to `None` otherwise.
- `mcp_server/dispatcher/dispatcher_enhanced.py` — symbol-lookup hot path is `EnhancedDispatcher.lookup(self, ctx, symbol, limit=20) -> Optional[SymbolDef]` at `:672`. Search hot path is `EnhancedDispatcher.search(self, ctx, query, semantic=False, fuzzy=False, limit=20)` at `:1075`. (Note: the MCP tool is named `symbol_lookup`; the dispatcher method is `lookup`. The histogram metric name remains `mcp_symbol_lookup_duration_seconds` per the spec.)
- `mcp_server/artifacts/artifact_download.py` — `download_artifact()` `:100`, `install_indexes()` `:359`, orchestrator `download_selected_artifact()` reads metadata at `:407` (field name `commit`) and calls `install_indexes()` at `:415`. No GitHub-outage handling today; freshness gate slots between L407 and L415.
- `uv.lock` already exists at repo root. No lockfile-CI workflow today (`.github/workflows/` has `ci-cd-pipeline.yml`, `index-management.yml`, etc.).

What constrains the design:
- `mcp_server/watcher_multi_repo.py` is the only true single-writer file: SL-2 and SL-3 both need to edit it, on non-overlapping function ranges. Serialize SL-3 after SL-2 to avoid an add/add conflict.
- The dispatcher's `lookup()` and `search()` are the OUTER public methods. SL-4 instruments those, not the inner gated-fallback path (which P11 already meters). No double-counting.
- `HealthView` must not import `gateway.py` (circular). Read state via `app.state` or accept dispatcher/store/registry as args at construction.

What this phase does NOT change:
- No upload-path changes (deferred to P13).
- No new metric endpoints beyond `/ready` + `/liveness`.
- No artifact signing (deferred to P15).
- No behavior change to `dispatcher.lookup` / `dispatcher.search` — instrumentation only.

## Interface Freeze Gates

- [ ] **IF-0-P12-1** — `mcp_server/health/probes.py::HealthView`:
  ```python
  class HealthView:
      def __init__(self, *, dispatcher=None, sqlite_store=None, registry=None, startup_time: float | None = None) -> None: ...
      def snapshot(self) -> dict[str, Any]:
          # Stable keys: {"sqlite": bool, "registry": bool, "dispatcher": bool,
          #               "last_index_ms": int | None, "uptime_s": float}
  ```
  Frozen at end of SL-1 task `SL-1.1` test pin.

- [ ] **IF-0-P12-2** — `mcp_server/indexing/lock_registry.py`:
  ```python
  class IndexingLockRegistry:
      def acquire(self, repo_id: str) -> AbstractContextManager[None]: ...
  # Module-level singleton:
  lock_registry: IndexingLockRegistry
  ```
  Reentrant per-repo (`threading.RLock` keyed on `repo_id`). Frozen at end of SL-2 task `SL-2.1`.

- [ ] **IF-0-P12-3** — log event + watcher method:
  ```python
  # Log call (SL-3 emits):
  logger.warning(
      "branch.drift.detected",
      extra={"repo_id": repo_id, "current_branch": current, "tracked_branch": tracked},
  )
  # Method on MultiRepositoryWatcher:
  def enqueue_full_rescan(self, repo_id: str) -> None: ...
  ```
  Frozen at end of SL-3 task `SL-3.1`.

- [ ] **IF-0-P12-4** — `PrometheusExporter` attributes:
  ```python
  # Same bucket tuple as P11:
  _DISPATCHER_FALLBACK_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
  self.dispatcher_lookup_histogram: Histogram | None  # name "mcp_symbol_lookup_duration_seconds"
  self.dispatcher_search_histogram: Histogram | None  # name "mcp_search_duration_seconds"
  ```
  No labels (keep cardinality at 1). `None` when `prometheus_client` unavailable. Frozen at end of SL-4 task `SL-4.1`.

- [ ] **IF-0-P12-5** — `mcp_server/artifacts/freshness.py`:
  ```python
  class FreshnessVerdict(str, Enum):
      FRESH = "fresh"
      STALE_COMMIT = "stale_commit"
      STALE_AGE = "stale_age"
      INVALID = "invalid"

  def verify_artifact_freshness(
      meta: dict, head_commit: str, max_age_days: int
  ) -> FreshnessVerdict: ...
  ```
  Frozen at end of SL-5 task `SL-5.1`.

## Lane Index & Dependencies

```
SL-1 — health-probes
  Depends on: (none)
  Blocks: (none — IF-0-P12-1 consumed by deploy-time probes only)
  Parallel-safe: yes

SL-2 — indexing-lock
  Depends on: (none)
  Blocks: SL-3 (single-writer file watcher_multi_repo.py)
  Parallel-safe: yes (with non-SL-3 lanes)

SL-3 — branch-drift-loud-path
  Depends on: SL-2 (avoid concurrent edits to watcher_multi_repo.py)
  Blocks: (none)
  Parallel-safe: yes (after SL-2 merges)

SL-4 — hot-path-histograms
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-5 — artifact-freshness
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

**Wave plan** (execute-phase default `MAX_PARALLEL_LANES=2`, three waves):

| Wave | Lanes | Rationale |
|---|---|---|
| 1 | SL-2, SL-4 | SL-2 must merge before SL-3; SL-4 is fully independent. Both small. |
| 2 | SL-1, SL-5 | After Wave 1; both touch disjoint new modules. |
| 3 | SL-3 | After SL-2 merges, to take a clean base on `watcher_multi_repo.py`. |

## Lanes

### SL-1 — health-probes

- **Scope**: Add `/ready` + `/liveness` HTTP routes backed by a new `HealthView` aggregator in a dedicated `mcp_server/health/probes.py` module.
- **Owned files**: `mcp_server/health/probes.py` (new), `mcp_server/health/__init__.py` (extend `__all__`), `mcp_server/gateway.py` (line range `:1033-1090` only — adds two `@app.get` decorators after the existing `/health` route block; one line in `startup_event()` `:614-620` to record `app.state.startup_time`), `tests/test_health_probes.py` (new).
- **Interfaces provided**: IF-0-P12-1.
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_health_probes.py` | `HealthView.snapshot()` returns the 5 stable keys; `/ready` returns 503 with dispatcher=None; 200 when all initialised; `/liveness` returns 200 within 1s when loop is responsive | `pytest tests/test_health_probes.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/health/probes.py`, `mcp_server/health/__init__.py` | — | — |
| SL-1.3 | impl | SL-1.2 | `mcp_server/gateway.py` (only `:614-620` for startup_time and the new route block after `:1034`) | — | — |
| SL-1.4 | verify | SL-1.3 | all SL-1 files | all SL-1 tests + `tests/test_gateway.py` regression | `pytest tests/test_health_probes.py tests/test_gateway.py tests/test_health_surface.py -v` |

### SL-2 — indexing-lock

- **Scope**: Add per-repo reentrant `threading.RLock` registry; wrap dispatcher write call sites in the watcher with `with lock_registry.acquire(repo_id):`.
- **Owned files**: `mcp_server/indexing/lock_registry.py` (new), `mcp_server/indexing/__init__.py` (extend if present, otherwise create), `mcp_server/watcher_multi_repo.py` **lines 141–198 and 442–458 only** (three handler methods + `sync_all_repositories`), `tests/test_indexing_lock.py` (new).
- **Interfaces provided**: IF-0-P12-2.
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_indexing_lock.py` | `IndexingLockRegistry.acquire` is reentrant for same repo_id; serializes two threads on same repo_id; concurrent watcher + manual `sync_all_repositories` on the same repo serialise dispatcher calls (assert via lock-acquisition order, not timing) | `pytest tests/test_indexing_lock.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/indexing/lock_registry.py`, `mcp_server/indexing/__init__.py` | — | — |
| SL-2.3 | impl | SL-2.2 | `mcp_server/watcher_multi_repo.py` (`:141-198`, `:442-458`) | — | — |
| SL-2.4 | verify | SL-2.3 | all SL-2 files | all SL-2 tests + watcher regression | `pytest tests/test_indexing_lock.py tests/test_watcher_multi_repo.py -v` |

### SL-3 — branch-drift-loud-path

- **Scope**: Detect branch drift loudly — emit `branch.drift.detected` WARN log and call `MultiRepositoryWatcher.enqueue_full_rescan(repo_id)` instead of silently dropping events.
- **Owned files**: `mcp_server/storage/git_index_manager.py` (entire file), `mcp_server/watcher_multi_repo.py` **lines 363–410 only** (`_sync_repository` + `on_git_commit`) and the **NEW** `enqueue_full_rescan` method appended to the `MultiRepositoryWatcher` class, `tests/test_branch_drift_rescan.py` (new), `tests/test_git_index_manager.py` (extend if exists; create otherwise).
- **Interfaces provided**: IF-0-P12-3.
- **Interfaces consumed**: (none — does not import `lock_registry`).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_branch_drift_rescan.py`, `tests/test_git_index_manager.py` | `should_reindex_for_branch` still returns False for drift; drift triggers a single `branch.drift.detected` WARN log entry with `{repo_id, current_branch, tracked_branch}`; `enqueue_full_rescan(repo_id)` is called exactly once per drift detection; rescan is enqueued (not executed inline) | `pytest tests/test_branch_drift_rescan.py tests/test_git_index_manager.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/storage/git_index_manager.py` | — | — |
| SL-3.3 | impl | SL-3.2 | `mcp_server/watcher_multi_repo.py` (`:363-410` + appended `enqueue_full_rescan`) | — | — |
| SL-3.4 | verify | SL-3.3 | all SL-3 files | all SL-3 tests + watcher regression | `pytest tests/test_branch_drift_rescan.py tests/test_git_index_manager.py tests/test_watcher_multi_repo.py -v` |

### SL-4 — hot-path-histograms

- **Scope**: Add `dispatcher_lookup_histogram` and `dispatcher_search_histogram` to `PrometheusExporter` using P11's exact bucket tuple. Instrument `EnhancedDispatcher.lookup` and `.search` entry methods. No behavior change.
- **Owned files**: `mcp_server/metrics/prometheus_exporter.py` (additions only; do not modify existing histogram), `mcp_server/dispatcher/dispatcher_enhanced.py` **method bodies of `lookup` (`:672-…`) and `search` (`:1075-…`) only** — wrap entry/exit with histogram.observe; no changes to fallback path or any other method, `tests/test_hot_path_histograms.py` (new).
- **Interfaces provided**: IF-0-P12-4.
- **Interfaces consumed**: (none — independent of SL-2's lock).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_hot_path_histograms.py` | exporter exposes `dispatcher_lookup_histogram` and `dispatcher_search_histogram` attributes; both `None` when `prometheus_client` unavailable; both share the P11 bucket tuple; histogram `_count` increments by exactly 1 per `dispatcher.lookup`/`dispatcher.search` call; metric names appear on `/metrics` scrape | `pytest tests/test_hot_path_histograms.py -v` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/metrics/prometheus_exporter.py` | — | — |
| SL-4.3 | impl | SL-4.2 | `mcp_server/dispatcher/dispatcher_enhanced.py` (`lookup` + `search` only) | — | — |
| SL-4.4 | verify | SL-4.3 | all SL-4 files | all SL-4 tests + P11 fallback regression | `pytest tests/test_hot_path_histograms.py tests/test_prometheus_dispatcher_fallback_metric.py tests/integration/test_dispatcher_fallback_metrics.py -v` |

### SL-5 — artifact-freshness

- **Scope**: Add `verify_artifact_freshness` enum-returning helper. Insert into `download_selected_artifact` between metadata-load and `install_indexes`. Catch GitHub-outage exceptions and return local-index + WARN. Add CI workflow that fails when `uv.lock` is out of date.
- **Owned files**: `mcp_server/artifacts/freshness.py` (new), `mcp_server/artifacts/__init__.py` (extend if present; otherwise additive), `mcp_server/artifacts/artifact_download.py` (only `download_selected_artifact` body around `:407-420` and the `download_artifact` GitHub-fetch try/except expansion — no other functions touched), `.github/workflows/lockfile-check.yml` (new), `tests/test_artifact_freshness.py` (new). `uv.lock` is read-only verified, not modified by this lane unless out-of-date.
- **Interfaces provided**: IF-0-P12-5.
- **Interfaces consumed**: (none).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_artifact_freshness.py` | `verify_artifact_freshness` returns `FRESH` when commit is ancestor and age < max; `STALE_COMMIT` when not ancestor; `STALE_AGE` when older; `INVALID` for missing/malformed metadata; GitHub fetch raising `RuntimeError`/`URLError` returns local-index + single WARN log (no raise); `MCP_ARTIFACT_MAX_AGE_DAYS` env defaulting to 14 honoured | `pytest tests/test_artifact_freshness.py -v` |
| SL-5.2 | impl | SL-5.1 | `mcp_server/artifacts/freshness.py`, `mcp_server/artifacts/__init__.py` | — | — |
| SL-5.3 | impl | SL-5.2 | `mcp_server/artifacts/artifact_download.py` (only call-site insert + GitHub try/except), `.github/workflows/lockfile-check.yml` | — | — |
| SL-5.4 | verify | SL-5.3 | all SL-5 files | all SL-5 tests | `pytest tests/test_artifact_freshness.py tests/test_artifact_download.py -v && uv lock --locked` |

## Execution Notes

- **Single-writer file** — `mcp_server/watcher_multi_repo.py`:
  - **SL-2 owns lines 141-198 and 442-458** (`_trigger_reindex_with_ctx`, `_remove_with_ctx`, `_move_with_ctx`, `sync_all_repositories`). SL-2's edits are local insertions of `with lock_registry.acquire(ctx.repo_id):` around four `dispatcher.*` calls (L161, L162, L181, L197, L448).
  - **SL-3 owns lines 363-410** (`_sync_repository`, `on_git_commit`) and **appends a new `enqueue_full_rescan(self, repo_id: str) -> None` method** to the class.
  - The two ranges do not overlap. SL-3 is serialized after SL-2 in Wave 3 to avoid base-stale add/add conflicts.
- **Single-writer file** — `mcp_server/dispatcher/dispatcher_enhanced.py`:
  - SL-4 owns ONLY the bodies of `lookup` (around `:672`) and `search` (around `:1075`). No edits to the fallback path, the gated-helper call sites, or any init code. The instrumentation must wrap the OUTER public method, not the inner `run_gated_fallback` helper, so we don't double-count with the P11 fallback histogram.
- **Known destructive changes**: none — every lane is purely additive.
- **Expected add/add conflicts**: none — no SL-0 preamble. The watcher_multi_repo.py partition is enforced by the wave order.
- **SL-0 re-exports**: not applicable — no preamble lane.
- **`mcp_server/indexing/__init__.py`**: currently absent (the `indexing/` directory has no `__init__.py` — it works only because all its submodules are imported by absolute path). SL-2 should create `__init__.py` exporting `lock_registry`. If that breaks import paths anywhere, switch to leaving `__init__.py` empty and importing `mcp_server.indexing.lock_registry` everywhere.
- **`mcp_server/health/__init__.py`**: today `__all__ = ["repo_status"]`. SL-1 extends to `__all__ = ["repo_status", "probes"]`. No re-exports of symbols (avoids eager-load risk per P11 SL-0 lesson).
- **Worktree naming**: `execute-phase` allocates unique worktree names via `scripts/allocate_worktree_name.sh`.
- **Stale-base guidance** (verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-2 merge (and the lane is SL-3), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Gateway circular-import**: `HealthView` MUST NOT `from mcp_server.gateway import …`. Either accept dispatcher/store/registry/startup_time as constructor args (preferred) or read them lazily via a module-level getter that imports inside the function body.
- **Watcher reference for SL-3**: `git_index_manager.py` should NOT import `watcher_multi_repo` (creates a cycle). Either pass `enqueue_full_rescan` as a callback into the manager, or have the watcher own the drift check and call `git_index_manager` for the comparison only.
- **P11 first-hit semantics** (per execute-phase handoff open item): SL-3's rescan-enqueue path triggers a full-repo reindex, not symbol-level lookups, so the first-hit fallback semantics do not affect drift behavior.
- **Pre-existing 3 failing dispatcher tests** (per execute-phase handoff): `tests/test_dispatcher.py::TestDispatcherInitialization::test_init_*` access `dispatcher._plugins` which was renamed to `_legacy_plugins` pre-P11. Out of scope for P12; do not fix in this phase.
- **`MCP_DISPATCHER_FALLBACK_MS`** documentation (per execute-phase handoff): SL-1's `/ready` endpoint should NOT block on this knob. The probe must complete in <100ms regardless.

## Acceptance Criteria

- [ ] `pytest tests/test_health_probes.py -v` passes; covers `HealthView.snapshot()` shape and the 503/200 boundaries for both routes (test file required for IF-0-P12-1).
- [ ] `pytest tests/test_indexing_lock.py -v` passes; one test spawns watcher + manual sync threads on the same repo_id and asserts serialised dispatcher entry-order via instrumented mock (test required for IF-0-P12-2; raw rg of `lock_registry.acquire` alone is insufficient — must be paired with the test).
- [ ] `pytest tests/test_branch_drift_rescan.py -v` passes; one test asserts the WARN log entry with all three fields, one asserts `enqueue_full_rescan` is called exactly once on drift (test required for IF-0-P12-3).
- [ ] `pytest tests/test_hot_path_histograms.py -v` passes; asserts both histogram attribute presence, the P11 bucket-tuple identity, the `None` fallback when `prometheus_client` is missing, and a `_count` delta of exactly 1 per dispatcher call (test required for IF-0-P12-4).
- [ ] `pytest tests/test_artifact_freshness.py -v` passes; covers all four `FreshnessVerdict` outcomes and the GitHub-outage local-fallback path with no raise (test required for IF-0-P12-5).
- [ ] `uv lock --locked` exits 0 (lockfile is up-to-date).
- [ ] `.github/workflows/lockfile-check.yml` runs `uv lock --locked` and fails the job on non-zero exit.
- [ ] All P11 tests still green: `pytest tests/test_prometheus_dispatcher_fallback_metric.py tests/integration/test_dispatcher_fallback_metrics.py tests/test_run_gated_fallback.py -v` (regression baseline).

## Verification

End-to-end after all lanes merge to `main`. Adapted from `specs/phase-plans-v1.md:879-895`:

```bash
# 1. Probes
op run --env-file=.mcp.env -- python -m mcp_server.cli.server_commands &
SERVER_PID=$!
sleep 3
curl -fsS localhost:8000/ready | jq -e '.sqlite == true and .registry == true and .dispatcher == true'
curl -fsS localhost:8000/liveness | jq -e '.alive == true'
# 503 path: kill the dispatcher init by misconfiguring, restart, and expect 503
curl -o /dev/null -s -w "%{http_code}" localhost:8000/ready  # expect 503 when not initialised

# 2. Hot-path histograms present
curl -fsS localhost:8000/metrics | grep -E '^mcp_(symbol_lookup|search)_duration_seconds_bucket'

# 3. Per-repo indexing lock — concurrent serialisation
pytest tests/test_indexing_lock.py::test_concurrent_watcher_and_manual_sync_serialise -v

# 4. Branch-drift loud path
pytest tests/test_branch_drift_rescan.py::test_drift_emits_warn_and_enqueues -v

# 5. Artifact freshness gate + offline fallback
pytest tests/test_artifact_freshness.py -v
# Force GitHub outage:
MCP_ARTIFACT_FORCE_OUTAGE=1 python -c "from mcp_server.artifacts.artifact_download import download_selected_artifact; download_selected_artifact()"
# Expect: returns without raising; logs include "artifact.fetch.failed" WARN.

# 6. Lockfile CI check (locally simulate)
uv lock --locked

# 7. P11 regression
pytest tests/test_prometheus_dispatcher_fallback_metric.py tests/integration/test_dispatcher_fallback_metrics.py tests/test_run_gated_fallback.py -v

kill $SERVER_PID
```

All commands above must return success. Any non-zero exit, missing histogram metric, or 200 from `/ready` while a component is uninitialised fails the phase.

## Risks & Mitigations

1. **Circular import gateway↔health/probes** — Mitigated by injecting dispatcher/store/registry into `HealthView.__init__` rather than importing from `gateway.py`. SL-1.1 includes a test that imports `HealthView` standalone.
2. **`watcher_multi_repo.py` add/add conflict between SL-2 and SL-3** — Mitigated by the wave plan: SL-3 in Wave 3, after SL-2 merges. Lane teammate must stop-and-report if its worktree base predates the SL-2 merge.
3. **Double-counting on hot-path histogram** — Mitigated by SL-4 instrumenting only the OUTER `lookup`/`search` methods and not the inner gated-fallback path that P11 already meters. SL-4.1 includes an assertion that `dispatcher_fallback_histogram._count` does not increment on a hot-path call that doesn't fall through.
4. **GitHub outage during artifact download crashes the server** — Mitigated by SL-5 wrapping `download_artifact` GitHub fetch in a typed try/except returning a single WARN + `FreshnessVerdict.INVALID`. SL-5.1 mocks `gh api` to raise.
5. **`/liveness` blocks on a real bug instead of detecting it** — Mitigated by `/liveness` doing only `await asyncio.sleep(0)` plus a 1ms timestamp delta; a 10s block is detected by the absence of recent timestamp updates from a background heartbeat task started in `startup_event`. SL-1.1 includes a test that asserts `/liveness` returns within 1s when the loop is responsive.

## Files Critical for Execution

- `mcp_server/gateway.py:80-90, 270-820, 1033-1090` — SL-1 edit window.
- `mcp_server/health/__init__.py`, `mcp_server/health/probes.py` (new) — SL-1 owns.
- `mcp_server/indexing/__init__.py` (new), `mcp_server/indexing/lock_registry.py` (new) — SL-2 owns.
- `mcp_server/watcher_multi_repo.py:141-198, 442-458` — SL-2 edit window.
- `mcp_server/watcher_multi_repo.py:363-410` + appended new method — SL-3 edit window.
- `mcp_server/storage/git_index_manager.py` — SL-3 owns.
- `mcp_server/metrics/prometheus_exporter.py` — SL-4 additive only.
- `mcp_server/dispatcher/dispatcher_enhanced.py:672, 1075` — SL-4 instruments method bodies only.
- `mcp_server/artifacts/freshness.py` (new), `mcp_server/artifacts/artifact_download.py:100, 359, 407-420` — SL-5 owns.
- `.github/workflows/lockfile-check.yml` (new), `uv.lock` (read-only) — SL-5 owns.
- `tests/test_health_probes.py`, `tests/test_indexing_lock.py`, `tests/test_branch_drift_rescan.py`, `tests/test_hot_path_histograms.py`, `tests/test_artifact_freshness.py` (all new) — owned by their respective lanes.
