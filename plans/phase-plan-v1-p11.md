# PHASE-11: Dispatcher Dependability (P11)

## Context

During Phase 5, an `EnhancedDispatcher.lookup()` call hung indefinitely on a C plugin's `_find_nodes` recursive tree-sitter traversal. The hang was believed to be caught by a SIGALRM per-plugin timeout, but wasn't.

Reconnaissance at commit `6a42c4f` established the real root cause: the SIGALRM context manager at `mcp_server/cli/bootstrap.py:166-182` is an unused utility — it is NEVER wired into the dispatcher's fallback path. The production fallback at `mcp_server/dispatcher/dispatcher_enhanced.py:751-779` has no timeout at all. It iterates every registered plugin and calls `plugin.getDefinition(symbol)` synchronously, exposing the caller to any plugin's worst-case latency. Secondarily, the iteration is not extension-gated: a lookup for a `.py` symbol will still invoke a C plugin's `getDefinition()` if a CPlugin instance happens to be in the repo plugin set.

P11 closes both gaps: (1) bounds every fallback plugin call at `MCP_DISPATCHER_FALLBACK_MS` (default 2000) via `ThreadPoolExecutor.submit(...).result(timeout=...)` — signals are unreliable in CPython worker threads, so we abandon SIGALRM entirely; (2) filters candidate plugins by the symbol's source-file extension using the non-instantiating static map `PluginRegistry.get_plugins_by_extension()`; (3) records `mcp_dispatcher_fallback_duration_seconds` on every attempt, exported via P10's `/metrics` surface. The investigation note captures the code-gap reproducer — no runtime reproducer is needed because the unbounded loop is self-evident in the diff.

Architecture: a new thin helper module `mcp_server/dispatcher/fallback.py` owns the gated, bounded, observed fallback. The dispatcher's two fallback blocks (`:751-770` advanced aggregator path and `:772-779` basic path, plus the matching loop in `search()` at `:829-834`) become mechanical delegations to the helper. This isolates the dangerous I/O behind one testable seam and keeps the diff in `dispatcher_enhanced.py` minimal.

## Interface Freeze Gates

- [ ] IF-0-P11-1 — Function `run_gated_fallback(plugins: Iterable[IPlugin], symbol: str, *, source_ext: Optional[str], timeout_ms: int, histogram: Optional[Any] = None) -> Optional[SymbolDef]` in `mcp_server/dispatcher/fallback.py`. Contract: returns `None` if `source_ext is None`; filters `plugins` by `PluginRegistry.get_plugins_by_extension(source_ext)` (non-instantiating static map); submits each survivor to a `ThreadPoolExecutor(max_workers=1)` scoped to the call; `.result(timeout=timeout_ms/1000)`; observes `histogram.labels(outcome=...).observe(duration)` with outcome in `{"hit","miss","timeout","error"}`; returns the first truthy `SymbolDef` or `None`.
- [ ] IF-0-P11-2 — Env var `MCP_DISPATCHER_FALLBACK_MS`, integer milliseconds, default `2000`. Read inside `EnhancedDispatcher.__init__` via `int(os.environ.get("MCP_DISPATCHER_FALLBACK_MS", "2000"))` (invalid → default + warning); cached as `self._fallback_timeout_ms`; passed into `run_gated_fallback` per call.
- [ ] IF-0-P11-3 — Prometheus `Histogram` named `mcp_dispatcher_fallback_duration_seconds`, label set `["outcome"]` (values `"hit" | "miss" | "timeout" | "error"`), buckets `(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)`. Registered in `PrometheusExporter._initialize_metrics()` guarded by `PROMETHEUS_AVAILABLE`. Exposed as attribute `PrometheusExporter.dispatcher_fallback_histogram` — returns the `Histogram` object or `None` when prometheus_client is unavailable.
- [ ] IF-0-P11-4 — `EnhancedDispatcher.lookup(self, ctx, symbol, limit=20)` and `EnhancedDispatcher.search(self, ...)` signatures unchanged. `source_ext` is derived inside each method from the BM25/symbols-table row's `filepath` via `os.path.splitext(filepath)[1].lower()` before the fallback; absent → `None` → fallback returns `None` immediately (per exit criterion 2: "returns empty if extension unknown").

## Lane Index & Dependencies

SL-1 — fallback-helper
  Depends on: (none)
  Blocks: SL-4
  Parallel-safe: yes

SL-2 — prometheus-histogram
  Depends on: (none)
  Blocks: SL-4
  Parallel-safe: yes

SL-3 — investigation-note
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-4 — dispatcher-rewire
  Depends on: SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no

Wave 1 (EXECUTE_MAX_PARALLEL_LANES=2): SL-1 + SL-2. Wave 2: SL-3 + SL-4.

## Lanes

### SL-1 — fallback-helper
- **Scope**: Implement the new `run_gated_fallback` helper with extension-gating (non-instantiating), thread-based timeout, and histogram observation. Publish the slow-plugin fixture reused by SL-4.
- **Owned files**: `mcp_server/dispatcher/fallback.py`, `mcp_server/dispatcher/__init__.py`, `tests/fixtures/slow_plugin.py`, `tests/test_dispatcher_fallback_timeout.py`
- **Interfaces provided**: IF-0-P11-1 (full), IF-0-P11-2 (consumes value, no ownership of reader), slow-plugin fixture API `SlowPlugin(sleep_seconds: float, symbol_def: SymbolDef | None = None)`.
- **Interfaces consumed**: `PluginRegistry.get_plugins_by_extension` at `mcp_server/plugin_system/plugin_registry.py:152` (existing); `IPlugin.getDefinition` at `mcp_server/plugin_base.py:83-115` (existing); accepts any `histogram` object with `.labels(...).observe(float)` (IF-0-P11-3 duck-typed — no import coupling).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/fixtures/slow_plugin.py`, `tests/test_dispatcher_fallback_timeout.py` | SlowPlugin sleeps 5s; `run_gated_fallback([SlowPlugin], "foo", source_ext=".c", timeout_ms=200, histogram=fake)` returns `None` within 400ms wall-clock; fake histogram observed once with `outcome="timeout"`; `source_ext=None` returns `None` without invoking plugin; `.py` with only CPlugin in list returns `None` and plugin's `getDefinition` was never called | `pytest tests/test_dispatcher_fallback_timeout.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/dispatcher/fallback.py` | — | — |
| SL-1.3 | impl | SL-1.2 | `mcp_server/dispatcher/__init__.py` (export `run_gated_fallback`) | — | — |
| SL-1.4 | verify | SL-1.3 | `mcp_server/dispatcher/fallback.py`, `tests/test_dispatcher_fallback_timeout.py` | all SL-1 tests | `pytest tests/test_dispatcher_fallback_timeout.py -v` |

### SL-2 — prometheus-histogram
- **Scope**: Register the new `mcp_dispatcher_fallback_duration_seconds` histogram in `PrometheusExporter._initialize_metrics()` and expose it as `PrometheusExporter.dispatcher_fallback_histogram`. Add a unit test asserting its presence in the registry with correct labels and buckets.
- **Owned files**: `mcp_server/metrics/prometheus_exporter.py`, `tests/test_prometheus_dispatcher_fallback_metric.py`
- **Interfaces provided**: IF-0-P11-3 (histogram + accessor).
- **Interfaces consumed**: `prometheus_client.Histogram` (via existing `PROMETHEUS_AVAILABLE` guard).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_prometheus_dispatcher_fallback_metric.py` | exporter exposes `dispatcher_fallback_histogram`; `None` when `PROMETHEUS_AVAILABLE=False`; registered metric carries label set `{"outcome"}` and the frozen bucket tuple; registry `collect()` finds metric by name `mcp_dispatcher_fallback_duration_seconds` | `pytest tests/test_prometheus_dispatcher_fallback_metric.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/metrics/prometheus_exporter.py` | — | — |
| SL-2.3 | verify | SL-2.2 | `mcp_server/metrics/prometheus_exporter.py`, `tests/test_prometheus_dispatcher_fallback_metric.py` | all SL-2 tests plus the existing `tests/test_prometheus_exporter_http.py` (no regressions) | `pytest tests/test_prometheus_dispatcher_fallback_metric.py tests/test_prometheus_exporter_http.py -v` |

### SL-3 — investigation-note
- **Scope**: Author `docs/investigations/dispatcher-sigalrm-failure.md` with the code-gap reproducer, acceptable root cause (the SIGALRM utility at `bootstrap.py:166-182` was never wired into the dispatcher fallback; additionally, CPython only delivers signals on the main thread, so even a wired SIGALRM would not fire inside an ASGI worker thread), and remediation pointer to `fallback.py`. No runtime reproducer required per the spec's one-lane-day fallback clause.
- **Owned files**: `docs/investigations/dispatcher-sigalrm-failure.md`
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none — doc-only, reads source but writes nothing else)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | impl | — | `docs/investigations/dispatcher-sigalrm-failure.md` | — | — |
| SL-3.2 | verify | SL-3.1 | `docs/investigations/dispatcher-sigalrm-failure.md` | grep `bootstrap.py:166-182` and `dispatcher_enhanced.py:751-779` citations present; `run_gated_fallback` referenced as remediation; `search()` at `:829-834` noted as follow-up or covered-in-SL-4 | `grep -q 'bootstrap.py:166' docs/investigations/dispatcher-sigalrm-failure.md && grep -q 'dispatcher_enhanced.py:751' docs/investigations/dispatcher-sigalrm-failure.md && grep -q 'run_gated_fallback' docs/investigations/dispatcher-sigalrm-failure.md` |

### SL-4 — dispatcher-rewire
- **Scope**: Replace the three unprotected plugin-iteration blocks in `dispatcher_enhanced.py` with `run_gated_fallback()` delegations: (a) advanced aggregator path `:752-770`, (b) basic fallback path `:772-779`, (c) `search()` iteration at `:829-834`. Read the env var once in `__init__`. Thread `source_ext` from the BM25 row's `filepath` in both `lookup()` and `search()`. Add the extension-gating unit test (CPlugin not instantiated when dispatching `.py`) and the end-to-end integration test asserting the histogram appears in `/metrics` after a triggering slow-plugin fallback.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_dispatcher_extension_gating.py`, `tests/integration/test_dispatcher_fallback_metrics.py`
- **Interfaces provided**: (none — all consumer)
- **Interfaces consumed**: IF-0-P11-1 (`run_gated_fallback`), IF-0-P11-2 (env var), IF-0-P11-3 (`PrometheusExporter.dispatcher_fallback_histogram`), IF-0-P11-4 (signature stability); reuses `tests/fixtures/slow_plugin.py` from SL-1.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_dispatcher_extension_gating.py` | monkeypatch `CPlugin.__init__` to raise `AssertionError("must not instantiate")`; call `EnhancedDispatcher.lookup(ctx, "foo", limit=20)` against a ctx with SQLite row whose `filepath` ends in `.py`; assert returns `None` and no AssertionError; assert when BM25 row is absent (no extension hint) fallback returns `None` without invoking any plugin's `getDefinition`; assert when extension is `.c` only `c` plugin is called (via spy) | `pytest tests/test_dispatcher_extension_gating.py -v` |
| SL-4.2 | test | — | `tests/integration/test_dispatcher_fallback_metrics.py` | boot gateway `TestClient`; register a `SlowPlugin` (sleep 5s) via fixture; seed SQLite with a row whose `filepath` matches the slow plugin's extension; call lookup → times out; GET `/metrics`; assert body contains `mcp_dispatcher_fallback_duration_seconds_bucket` and `mcp_dispatcher_fallback_duration_seconds_count{outcome="timeout"}` with `count >= 1`; use `asyncio.new_event_loop()` if any asyncio needed (never `get_event_loop`); no hardcoded worktree paths | `pytest tests/integration/test_dispatcher_fallback_metrics.py -v` |
| SL-4.3 | impl | SL-4.1, SL-4.2 | `mcp_server/dispatcher/dispatcher_enhanced.py` (`__init__` reads `MCP_DISPATCHER_FALLBACK_MS`; stores `self._fallback_timeout_ms`; resolves `self._fallback_histogram` from the prometheus exporter accessor; imports `run_gated_fallback`) | — | — |
| SL-4.4 | impl | SL-4.3 | `mcp_server/dispatcher/dispatcher_enhanced.py` (replace `:752-770` advanced path and `:772-779` basic path with a single delegation to `run_gated_fallback`; derive `source_ext` from the BM25 row's `filepath` when available, else `None`) | — | — |
| SL-4.5 | impl | SL-4.4 | `mcp_server/dispatcher/dispatcher_enhanced.py` (replace search's plugin iteration at `:829-834` with the same helper call; use the query's first hit's `filepath` for `source_ext`, or `None`) | — | — |
| SL-4.6 | verify | SL-4.5 | all of SL-4's owned files plus dispatcher regressions | all P11 tests + prior dispatcher suites green when run together | `pytest tests/test_dispatcher_fallback_timeout.py tests/test_prometheus_dispatcher_fallback_metric.py tests/test_dispatcher_extension_gating.py tests/integration/test_dispatcher_fallback_metrics.py tests/root_tests/test_enhanced_dispatcher.py tests/test_dispatcher.py tests/test_prometheus_exporter_http.py -v` |

## Execution Notes

- **Search-path scope**: The spec's exit criteria name only `lookup()`. SL-4 intentionally extends the helper call to `search()` at `dispatcher_enhanced.py:829-834` because it has the identical unprotected shape and would remain a latent hang source if left. One-line addition in a file SL-4 already owns; no scope creep beyond the same bug class.
- **Single-writer files**: `mcp_server/dispatcher/dispatcher_enhanced.py` is written only by SL-4. `mcp_server/metrics/prometheus_exporter.py` is written only by SL-2. `mcp_server/dispatcher/__init__.py` is written only by SL-1. The slow-plugin fixture lives in SL-1's `tests/fixtures/slow_plugin.py` and is consumed read-only by SL-4.
- **Known destructive changes**: none — every lane is purely additive or in-place rewires bounded by file ownership. SL-4 replaces blocks inside `dispatcher_enhanced.py` but deletes no file.
- **Expected add/add conflicts**: none — no SL-0 preamble.
- **SL-0 re-exports**: none — no SL-0 lane in this phase.
- **Worktree naming**: execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`. Lanes do not spell out worktree paths.
- **Stale-base guidance** (verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If SL-4 finds its worktree base is pre-SL-1 (no `mcp_server/dispatcher/fallback.py`) or pre-SL-2 (no `dispatcher_fallback_histogram` attribute on `PrometheusExporter`), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- ...` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Test-quality guardrails (lessons from P10)**: no hardcoded absolute worktree paths in any test; no `asyncio.get_event_loop()` (use `asyncio.new_event_loop()`); SL-4.6 runs the combined suite — a per-lane pass is insufficient because prior phases saw isolation-only regressions.
- **ThreadPoolExecutor lifecycle**: SL-1's helper constructs a per-call executor using `with ThreadPoolExecutor(max_workers=1) as ex: ...` so no process-global thread pool lingers and no atexit hook is needed. `future.cancel()` cannot interrupt a running Python thread, but the caller is released on timeout — documented in SL-3's investigation note as residual risk.
- **CPlugin instantiation guarantee**: criterion 6 is satisfied at the **instantiation** boundary, not the **import** boundary. `mcp_server/plugins/plugin_factory.py:31-100` imports CPlugin at module-load time (tree_sitter loads eagerly). SL-4.1's test asserts `CPlugin.__init__` not called during `.py` dispatch — the static `PluginRegistry.get_plugins_by_extension(".py")` filter excludes the `c` plugin name before any factory `create_plugin` is invoked.
- **Architectural choices** (consensus summary): Three Plan teammates (arch-minimal, arch-clean, arch-parallel) converged on extracting a new `fallback.py` helper. arch-minimal dissented with in-place edits to `dispatcher_enhanced.py` sharing a module-level recorder hook between two lanes — rejected because the shared-symbol pattern violated prior-phase lessons (co-ownership of a file by two lanes is brittle). arch-clean and arch-parallel both proposed helper extraction; this plan adopts the clean 4-lane form rather than arch-parallel's 5-lane form because MAX_PARALLEL_LANES=2 collapses wall-clock equivalently while reducing IF surface. Dissent recorded above; no further disagreement.

## Acceptance Criteria

- [ ] `docs/investigations/dispatcher-sigalrm-failure.md` exists and cites `mcp_server/cli/bootstrap.py:166-182` and `mcp_server/dispatcher/dispatcher_enhanced.py:751-779` as the code-gap reproducer, and names `run_gated_fallback` as the remediation. Verified by grep AND by SL-3.2's assertion.
- [ ] `EnhancedDispatcher.lookup()` no longer iterates every registered plugin on SQLite miss — it calls `run_gated_fallback(...)` which filters via `PluginRegistry.get_plugins_by_extension(source_ext)`. Verified by `tests/test_dispatcher_extension_gating.py::test_cplugin_not_instantiated_for_py_dispatch` (monkeypatched `CPlugin.__init__` raising assertion is never triggered).
- [ ] `MCP_DISPATCHER_FALLBACK_MS` (default 2000) hard-caps any `plugin.getDefinition()` fallback call. Verified by `tests/test_dispatcher_fallback_timeout.py::test_slow_plugin_respects_timeout` — `SlowPlugin(sleep_seconds=5.0)` returns control within `timeout_ms + 200ms`.
- [ ] Fallback timeout mechanism uses `concurrent.futures.ThreadPoolExecutor.submit(...).result(timeout=...)`. Verified by: `tests/test_dispatcher_fallback_timeout.py::test_no_sigalrm_usage` asserts `signal.SIGALRM` handler is unchanged after a fallback call AND grep `grep -n "SIGALRM\|signal\.alarm" mcp_server/dispatcher/fallback.py` returns no matches. (Grep is paired with the test per lane-validation rule.)
- [ ] Prometheus histogram `mcp_dispatcher_fallback_duration_seconds` is registered in `PrometheusExporter._initialize_metrics` and records every fallback attempt. Verified by `tests/test_prometheus_dispatcher_fallback_metric.py::test_histogram_registered` AND `tests/integration/test_dispatcher_fallback_metrics.py::test_metrics_endpoint_exposes_fallback_duration`.
- [ ] `CPlugin` is not instantiated when dispatching a non-C/C++ symbol. Verified by `tests/test_dispatcher_extension_gating.py::test_cplugin_not_instantiated_for_py_dispatch`.
- [ ] `validate_plan_doc.py plans/phase-plan-v1-p11.md` passes with zero errors.
- [ ] Full combined test suite runs green: `pytest tests/test_dispatcher_fallback_timeout.py tests/test_prometheus_dispatcher_fallback_metric.py tests/test_dispatcher_extension_gating.py tests/integration/test_dispatcher_fallback_metrics.py tests/root_tests/test_enhanced_dispatcher.py tests/test_dispatcher.py tests/test_prometheus_exporter_http.py -v` — reflecting the P10 lesson that per-lane isolation pass is insufficient.

## Verification

```bash
# 1. Unit-level verification
pytest tests/test_dispatcher_fallback_timeout.py \
       tests/test_prometheus_dispatcher_fallback_metric.py \
       tests/test_dispatcher_extension_gating.py -v

# 2. Integration-level verification
pytest tests/integration/test_dispatcher_fallback_metrics.py -v

# 3. Dispatcher regression suite (combined — catches cross-test state leaks)
pytest tests/root_tests/test_enhanced_dispatcher.py \
       tests/test_dispatcher.py \
       tests/test_prometheus_exporter_http.py -v

# 4. Grep assertions paired with their tests
! grep -rn 'SIGALRM\|signal\.alarm' mcp_server/dispatcher/fallback.py
grep -n 'run_gated_fallback' mcp_server/dispatcher/dispatcher_enhanced.py        # expect 3 call sites (advanced path, basic path, search())
grep -n 'dispatcher_fallback_histogram' mcp_server/metrics/prometheus_exporter.py  # expect register + accessor

# 5. End-to-end /metrics scrape (manual smoke)
op run --env-file=.mcp.env -- python -m mcp_server.cli.server_commands &
curl -s localhost:8000/metrics | grep -c 'mcp_dispatcher_fallback_duration_seconds'  # expect >= 1

# 6. Plan-doc validator
python scripts/validate_plan_doc.py plans/phase-plan-v1-p11.md
```
