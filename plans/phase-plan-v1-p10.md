# P10: Production Hardening

## Context

P10 closes the production-readiness gaps deferred through P1–P6B: STDIO observability parity with FastAPI, SIGTERM graceful shutdown, symlink-escape hardening, multi-repo health surface, SQLite connection pooling, and schema-version enforcement with a breaking-changes log. Spec: `specs/phase-plans-v1.md` L501–539.

Reconnaissance established:

- `stdio_runner._serve()` at `mcp_server/cli/stdio_runner.py` L147–518 is the async entrypoint; its finally block (L500–517) already calls `multi_watcher.stop_watching_all()` and `ref_poller.stop()`, but no SIGTERM handler is installed.
- `PrometheusExporter` at `mcp_server/metrics/prometheus_exporter.py` owns a registry + counters (`mcp_requests_total`, `mcp_search_requests_total`, `mcp_symbols_indexed_total`) but has **no** `start(port)` method, **no** HTTP server, and **no** `mcp_tool_calls_total` counter.
- `MultiRepositoryWatcher` exposes `.stop_watching_all()` (not `.stop()` as the spec phrases it). `RefPoller.stop()` and `StoreRegistry.shutdown()` already exist.
- `_path_within_allowed` lives at `mcp_server/cli/bootstrap.py` L101–113 — not inside `mcp_server/security/` (which exists and holds `auth_manager.py`, `security_middleware.py`, `models.py`). It calls `.resolve()` on the candidate (the symlink-escape bug) and `_allowed_roots()` recomputes uncached per call (L74–98, `.resolve()` at L87, L95).
- `get_status` has two surfaces: stdio at `mcp_server/cli/tool_handlers.py::handle_get_status` (L294), wired in `stdio_runner.py` L84/L432; HTTP at `mcp_server/gateway.py` L1460–1558. Both must gain the `repositories` array.
- `RepositoryInfo` at `mcp_server/storage/multi_repo_manager.py` L27–82 already exposes `repository_id`, `tracked_branch`, `index_path`, `git_common_dir`, `last_indexed_commit`; `staleness_reason` is new.
- `SQLiteStore._get_connection()` at `mcp_server/storage/sqlite_store.py` L226–239 opens+closes per-call (WAL + `busy_timeout=5000`); `StoreRegistry.get()` at `mcp_server/storage/store_registry.py` L71 is the single construction point — ideal pool-injection linchpin.
- `IndexManager.select_best_index()` at `mcp_server/storage/index_manager.py` L288–334 takes `strict_compatibility` kwarg defaulting `False`, logs+continues on mismatch. No `SchemaMismatchError` type exists. CLI is Click-based (`mcp_server/cli/__main__.py` + `mcp_server/cli/server_commands.py`). Five migrations exist (001–005); current schema version is 5. `BREAKING-CHANGES.md` does not exist at repo root.

Architectural consensus (3 Plan teammates: `arch-minimal`, `arch-clean`, `arch-parallel`):

- **Unanimous**: `PrometheusExporter.start(port)`/`.stop()` owns its HTTP thread; standalone `ConnectionPool` class composed into `SQLiteStore`; `SchemaMismatchError` published as a cross-lane type; `staleness_reason` added to `RepositoryInfo`; red-test-first for symlink; `--rebuild-on-schema-mismatch` as a Click flag; `BREAKING-CHANGES.md` seeded with migrations 001–005.
- **Majority (clean + parallel)**: move allowlist into `mcp_server/security/path_allowlist.py`. The directory exists (verified), so the spec's acceptance grep `grep -rn '\.resolve()' mcp_server/security/` becomes meaningful rather than vacuous. arch-minimal's objection ("directory doesn't exist") was factually wrong.
- **Tie-broken**: one-line alias `MultiRepositoryWatcher.stop = stop_watching_all` (arch-minimal — simplest, spec-literal, zero call-site churn); **no SL-0 preamble** — feature lanes are already file-disjoint and only one cross-lane type dependency exists (SL-2 importing `PrometheusExporter.start` from SL-1), resolved via DAG edge not a preamble commit; SL-2 owns `stdio_runner.py` fully (consumes SL-1's frozen API) — helper-file split was overengineered for <10 lines of init code.

## Interface Freeze Gates

- [ ] **IF-0-P10-1** — `PrometheusExporter.start(port: int) -> None` and `.stop() -> None` (idempotent; no-op when `prometheus_client` missing or port occupied, logs warn). Module-level `mcp_tool_calls_total = Counter("mcp_tool_calls_total", ..., ["tool", "status"])` and helper `record_tool_call(tool: str, status: str)`. Owned & published by SL-1; consumed by SL-2.
- [ ] **IF-0-P10-2** — `mcp_server/security/path_allowlist.py` exports `resolve_allowed_roots() -> tuple[Path, ...]` (boot-cached via `functools.lru_cache`; `resolve_allowed_roots.cache_clear()` exposed for tests) and `path_within_allowed(candidate: Path, roots: tuple[Path, ...] | None = None) -> bool` (uses `os.path.commonpath` on the un-resolved candidate; no `.resolve()` on candidate). Owned & published by SL-3.
- [ ] **IF-0-P10-3** — `MultiRepositoryWatcher.stop = stop_watching_all` alias at class body bottom of `mcp_server/watcher_multi_repo.py`, making `watcher.stop()` spec-literal and symmetric with `RefPoller.stop()` / `StoreRegistry.shutdown()`. Owned & published by SL-2 (consumer of its own alias).
- [ ] **IF-0-P10-4** — `RepositoryInfo.staleness_reason: Optional[str] = None` field on the dataclass in `mcp_server/storage/multi_repo_manager.py`; values are `None` (healthy) or one of `"missing_index"`, `"missing_git_dir"`, `"commit_drift"`. Owned & published by SL-4.
- [ ] **IF-0-P10-5** — `mcp_server/storage/connection_pool.py::ConnectionPool(factory: Callable[[], sqlite3.Connection], size: int = 4)` with `@contextmanager def acquire() -> Iterator[sqlite3.Connection]` and `close_all() -> None`. Thread-safe via bounded `queue.Queue`. Owned & published by SL-5.
- [ ] **IF-0-P10-6** — `mcp_server/storage/schema_errors.py::SchemaMismatchError(expected: int, found: int, index_path: Path)` — frozen signature; `__str__` includes rebuild-command hint. Owned & published by SL-6.
- [ ] **IF-0-P10-7** — `mcp_server/health/repo_status.py::build_health_row(repo_info: RepositoryInfo) -> dict` returning `{repo_id, tracked_branch, index_path_exists, git_dir_exists, last_indexed_commit, staleness_reason}` — shared builder consumed by both stdio `handle_get_status` and HTTP `gateway.get_status` (both owned by SL-4).

Each gate lives inside the lane that owns its body. There is no SL-0 preamble: the lane DAG is simple enough (one dependency edge, SL-2→SL-1) that sequenced merges do the coordination without a separate preamble commit.

## Lane Index & Dependencies

```
SL-1 — Metrics exporter (PrometheusExporter.start + mcp_tool_calls_total)
  Depends on: (none)
  Blocks: SL-2
  Parallel-safe: yes

SL-2 — SIGTERM graceful shutdown + metrics wiring in _serve()
  Depends on: SL-1
  Blocks: (none)
  Parallel-safe: yes (sole owner of stdio_runner.py and watcher_multi_repo.py)

SL-3 — Symlink-escape hardening (red-test-first)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-4 — Multi-repo health surface
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-5 — SQLite connection pool
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes (sole owner of sqlite_store.py)

SL-6 — Schema enforcement + BREAKING-CHANGES.md
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes
```

SL-1 and SL-2 serialize. SL-3/SL-4/SL-5/SL-6 run fully in parallel with SL-1 and with each other.

## Lanes

### SL-1 — Metrics exporter

- **Scope**: Add `PrometheusExporter.start(port)`, `.stop()`, the `mcp_tool_calls_total` Counter, and the `record_tool_call(tool, status)` helper. Exporter owns its own HTTP server thread (via `prometheus_client.start_http_server` or an aiohttp wrapper), idempotent start/stop, no-op when `prometheus_client` is missing or the port is already bound.
- **Owned files**: `mcp_server/metrics/prometheus_exporter.py`, `tests/test_prometheus_exporter_http.py`
- **Interfaces provided**: IF-0-P10-1
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_prometheus_exporter_http.py` | `start(port)` binds HTTP; `record_tool_call` increments counter; missing-dep no-op; double-`start` is idempotent | `pytest -q tests/test_prometheus_exporter_http.py` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/metrics/prometheus_exporter.py` | — | — |
| SL-1.3 | verify | SL-1.2 | `mcp_server/metrics/prometheus_exporter.py` | all SL-1 tests + existing metrics tests | `pytest -q tests/test_prometheus_exporter_http.py tests/test_metrics*.py` |

### SL-2 — SIGTERM graceful shutdown + metrics wiring

- **Scope**: Install SIGTERM/SIGINT handlers in `_serve()` via `loop.add_signal_handler`; implement `async def _graceful_shutdown(multi_watcher, ref_poller, store_registry, timeout=5.0)` calling `multi_watcher.stop()` → `ref_poller.stop()` → `store_registry.shutdown()` in order, each wrapped in `asyncio.wait_for`; replace the existing finally-block body with the call. Add `exporter = PrometheusExporter(); exporter.start(int(os.getenv("MCP_METRICS_PORT", "9090")))` in `_serve()` startup and `exporter.stop()` in the shutdown helper. Add exactly one `record_tool_call(name, "success"|"error")` line inside the existing `@server.call_tool()` handler at `stdio_runner.py` L346+ wrapping the return path. Add the one-line alias `stop = stop_watching_all` to `MultiRepositoryWatcher` in `watcher_multi_repo.py`. Audit `grep -n '\.resolve()' mcp_server/cli/stdio_runner.py` and either remove occurrences or annotate with `# resolve() exempt: <reason>` inline to satisfy the P10 acceptance grep.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `mcp_server/watcher_multi_repo.py`, `tests/integration/test_sigterm_shutdown.py`, `tests/fixtures/multi_repo.py`
- **Interfaces provided**: IF-0-P10-3 (`stop` alias)
- **Interfaces consumed**: IF-0-P10-1 (`PrometheusExporter.start`, `record_tool_call`)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/integration/test_sigterm_shutdown.py`, `tests/fixtures/multi_repo.py` (extend as needed) | SIGTERM delivery → components stop in declared order within 5s; `curl localhost:9090/metrics` after a tool call shows `mcp_tool_calls_total` nonzero | `pytest -q tests/integration/test_sigterm_shutdown.py` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/cli/stdio_runner.py`, `mcp_server/watcher_multi_repo.py` | — | — |
| SL-2.3 | verify | SL-2.2 | `mcp_server/cli/stdio_runner.py`, `mcp_server/watcher_multi_repo.py` | all SL-2 tests + stdio multi-repo regression | `pytest -q tests/integration/test_sigterm_shutdown.py tests/integration/test_multi_repo_server.py` |

### SL-3 — Symlink-escape hardening

- **Scope**: Write a failing symlink-escape test first (red gate); implement `mcp_server/security/path_allowlist.py` with `resolve_allowed_roots()` (boot-cached `functools.lru_cache` wrapping `os.path.realpath` over allowed roots) and `path_within_allowed(candidate, roots)` (uses `os.path.commonpath` on the un-resolved candidate — no `.resolve()` on candidate); replace `bootstrap._path_within_allowed` body with a thin delegating shim `return path_within_allowed(target, tuple(roots))` so existing call sites in `tool_handlers.py` continue to work unchanged; annotate `bootstrap.py` L87/L95 (the root-canonicalization `.resolve()` calls, which are intentional and distinct from the candidate-resolution bug) with inline `# resolve() exempt: boot-time root canonicalization` comments.
- **Owned files**: `mcp_server/security/path_allowlist.py`, `mcp_server/cli/bootstrap.py`, `tests/security/__init__.py`, `tests/security/test_symlink_escape.py`
- **Interfaces provided**: IF-0-P10-2
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/security/test_symlink_escape.py`, `tests/security/__init__.py` | symlink inside allowed root → `/etc/passwd` returns False; candidate inside allowed root returns True; candidate outside returns False | `pytest -q tests/security/test_symlink_escape.py` — must fail before SL-3.2 |
| SL-3.2 | impl | SL-3.1 | `mcp_server/security/path_allowlist.py`, `mcp_server/cli/bootstrap.py` | — | — |
| SL-3.3 | verify | SL-3.2 | `mcp_server/security/path_allowlist.py`, `mcp_server/cli/bootstrap.py` | all SL-3 tests + existing bootstrap/allowlist tests + grep-assertion pair | `pytest -q tests/security/ tests/test_bootstrap*.py` and `grep -rn '\.resolve()' mcp_server/security/ mcp_server/cli/stdio_runner.py` returns zero un-exempted occurrences in the allowlist-check path |

### SL-4 — Multi-repo health surface

- **Scope**: Add `staleness_reason: Optional[str] = None` to `RepositoryInfo` (IF-0-P10-4); implement `mcp_server/health/repo_status.py::build_health_row` (checks `Path(index_path).exists()`, `Path(git_common_dir).exists()`, assigns `staleness_reason` from the first failure encountered, else None); extend stdio `handle_get_status` to include `repositories: [build_health_row(info) for info in repo_registry.get_all_repositories().values()]`; extend HTTP `gateway.get_status` identically so both surfaces share the builder.
- **Owned files**: `mcp_server/storage/multi_repo_manager.py`, `mcp_server/health/__init__.py`, `mcp_server/health/repo_status.py`, `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py`, `tests/test_health_surface.py`, `tests/fixtures/health_repo.py`
- **Interfaces provided**: IF-0-P10-4, IF-0-P10-7
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_health_surface.py`, `tests/fixtures/health_repo.py` | `repositories[]` present on both surfaces with full field shape; stale repos (missing `.git`, missing `index_path`) get non-null `staleness_reason`; healthy repos get `None` | `pytest -q tests/test_health_surface.py` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/storage/multi_repo_manager.py`, `mcp_server/health/__init__.py`, `mcp_server/health/repo_status.py`, `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py` | — | — |
| SL-4.3 | verify | SL-4.2 | `mcp_server/health/`, `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py` | all SL-4 tests + existing gateway/tool-handler tests | `pytest -q tests/test_health_surface.py tests/test_tool_handlers.py tests/test_gateway*.py` |

### SL-5 — SQLite connection pool

- **Scope**: Implement `mcp_server/storage/connection_pool.py::ConnectionPool` (bounded `queue.Queue` of `sqlite3.Connection`; `acquire()` contextmanager with blocking get/put; `close_all()` drains and closes every connection); wire `SQLiteStore` to compose an optional pool — when a pool is provided at construction, `_get_connection()` yields from `pool.acquire()` instead of opening-per-call; pass a shared pool at `StoreRegistry.get()` construction so every call site benefits transparently. Read-oriented: writes (migrations, `store_symbol`, `store_chunk`) continue through the existing single-connection WAL path to avoid write-contention regressions.
- **Owned files**: `mcp_server/storage/connection_pool.py`, `mcp_server/storage/sqlite_store.py`, `mcp_server/storage/store_registry.py`, `tests/test_sqlite_pool.py`
- **Interfaces provided**: IF-0-P10-5
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_sqlite_pool.py` | 16 concurrent readers against default-size-4 pool complete with zero `database is locked`; `close_all` is idempotent; write path unchanged under load | `pytest -q tests/test_sqlite_pool.py` |
| SL-5.2 | impl | SL-5.1 | `mcp_server/storage/connection_pool.py`, `mcp_server/storage/sqlite_store.py`, `mcp_server/storage/store_registry.py` | — | — |
| SL-5.3 | verify | SL-5.2 | `mcp_server/storage/connection_pool.py`, `mcp_server/storage/sqlite_store.py`, `mcp_server/storage/store_registry.py` | all SL-5 tests + existing SQLite store and store-registry tests | `pytest -q tests/test_sqlite_pool.py tests/test_sqlite_store*.py tests/test_store_registry*.py` |

### SL-6 — Schema enforcement + BREAKING-CHANGES

- **Scope**: Add `mcp_server/storage/schema_errors.py` with `SchemaMismatchError(expected, found, index_path)` whose `__str__` includes the rebuild-command hint. Flip `IndexManager.select_best_index(strict_compatibility=...)` default from `False` to `True`; on mismatch, raise `SchemaMismatchError` instead of logging-and-continuing. Add `--rebuild-on-schema-mismatch` Click flag to both `serve` and `stdio` subcommands in `server_commands.py`; when set, catch `SchemaMismatchError` at index-load time, invoke the existing rebuild path, retry load. Create `BREAKING-CHANGES.md` at repo root, seeded with migrations 001–005 and the P10 strict-flip entry.
- **Owned files**: `mcp_server/storage/schema_errors.py`, `mcp_server/storage/index_manager.py`, `mcp_server/cli/server_commands.py`, `BREAKING-CHANGES.md`, `tests/test_schema_strict.py`
- **Interfaces provided**: IF-0-P10-6
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-6.1 | test | — | `tests/test_schema_strict.py` | strict-default raises `SchemaMismatchError` with rebuild hint in `__str__`; `--rebuild-on-schema-mismatch` rebuilds and retries successfully; matched-schema index loads unchanged | `pytest -q tests/test_schema_strict.py` |
| SL-6.2 | impl | SL-6.1 | `mcp_server/storage/schema_errors.py`, `mcp_server/storage/index_manager.py`, `mcp_server/cli/server_commands.py`, `BREAKING-CHANGES.md` | — | — |
| SL-6.3 | verify | SL-6.2 | `mcp_server/storage/index_manager.py`, `mcp_server/cli/server_commands.py` | all SL-6 tests + existing index-manager tests | `pytest -q tests/test_schema_strict.py tests/test_index_manager*.py` |

## Execution Notes

- **Single-writer files** — every file is owned by exactly one lane. Key high-traffic call-outs:
  - `mcp_server/cli/stdio_runner.py` → SL-2 (metrics wiring + SIGTERM handler + finally-block rewrite, single commit)
  - `mcp_server/storage/sqlite_store.py` → SL-5 (pool composition)
  - `mcp_server/storage/index_manager.py` → SL-6 (strict-flip + mismatch raise)
  - `mcp_server/cli/bootstrap.py` → SL-3 (shim + resolve exemption comments)
  - `mcp_server/cli/tool_handlers.py` → SL-4 (handle_get_status extension)
  - `mcp_server/gateway.py` → SL-4 (HTTP get_status extension)
  - `mcp_server/watcher_multi_repo.py` → SL-2 (stop alias)
  - `mcp_server/storage/multi_repo_manager.py` → SL-4 (staleness_reason field)
  - `mcp_server/cli/server_commands.py` → SL-6 (`--rebuild-on-schema-mismatch` Click flag)
  - `tests/fixtures/multi_repo.py` → SL-2 (extends if SIGTERM integration test needs new repo fixture). SL-4's health-surface test uses a separate `tests/fixtures/health_repo.py` to avoid shared-writer contention. (Lesson from P9 SL-1: when an integration test needs fixture extension, the lane must own the fixture file explicitly, else audit flags ORPHAN_FILES.)
- **Known destructive changes** — `bootstrap.py::_path_within_allowed` body is replaced with a thin delegating shim to `path_allowlist.path_within_allowed` (SL-3). `IndexManager.select_best_index` mismatch-handling changes from log-and-continue to raise-unless-rebuild-flag (SL-6). All other changes are purely additive.
- **Expected add/add conflicts** — none. There is no SL-0 preamble; each new file (`path_allowlist.py`, `connection_pool.py`, `schema_errors.py`, `repo_status.py`, `BREAKING-CHANGES.md`, fixture files, test files) is created by exactly one lane in exactly one commit.
- **SL-0 re-exports** — no SL-0 preamble in this plan (see Context §3); lanes do not share `__init__.py` edits. If a lane later decides it wants `from mcp_server.storage import SchemaMismatchError`, SL-6 can add the re-export as part of its own owned edits — no cross-lane coordination needed.
- **Plan-doc single-line Owned-files format** — every `- **Owned files**:` bullet is on one line (audit-script parser constraint from P9 lessons).
- **Red-test-first gate for SL-3** — SL-3.1 must produce a failing pytest run before SL-3.2 touches `path_allowlist.py` or `bootstrap.py`. Orchestrator verifies the red state before merging SL-3.1's test commit.
- **Grep-assertion paired with tests** — SL-3.3's final check runs both `grep -rn '\.resolve()' mcp_server/security/ mcp_server/cli/stdio_runner.py` AND `pytest -q tests/security/test_symlink_escape.py`. Grep alone is defeated by renaming to pass regex; the pytest run is the load-bearing assertion per plan-phase checklist.
- **ConnectionPool scope note** — the pool is read-oriented. Writes continue through the existing single-connection WAL path; the 16-concurrent-reader acceptance test is the concurrency proof. Rewriting the write path is explicitly out of scope (user brief — "do NOT rewrite SQLiteStore wholesale").
- **MCP tool call increment site** — SL-2 adds exactly one `record_tool_call(name, "success"|"error")` line inside the existing `@server.call_tool()` handler at `stdio_runner.py` L346+, wrapping the existing return-path branches (no refactor). SL-1 provides the `record_tool_call` helper; SL-1 does not touch `stdio_runner.py`.
- **Worktree naming** — execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`.
- **Stale-base guidance** — Lane teammates working in isolated worktrees do NOT see sibling-lane merges automatically. SL-2 specifically must rebase onto SL-1's merge commit before final commit (its only DAG dependency). If a lane finds its worktree base is pre-SL-1 (for SL-2 specifically) or any sibling lane has already merged into `main`, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. Every lane runs `git rebase main` immediately after `EnterWorktree` AND again before final commit. The three-outcome destructiveness check in execute-phase handles `STALE_BASE_DETECTED` via a 3-way merge preview.
- **Architectural choices** — consensus on all seven interface freezes (3/3). Majority chose `mcp_server/security/path_allowlist.py` over keeping `_path_within_allowed` in `bootstrap.py` (arch-clean + arch-parallel; arch-minimal dissent based on a factual error that the directory didn't exist — directory was verified to exist, dissent withdrawn). Tie-broken against SL-0 preamble in favor of simpler DAG (file-disjoint lanes, single DAG edge SL-2→SL-1); tie-broken against helper-file split of `stdio_runner._serve()` in favor of SL-2 owning the file fully (consumes SL-1's frozen API). No unresolved dissent.

## Cross-Repo Gates

None — P10 is single-repo.

## Acceptance Criteria

- [ ] `curl -s localhost:9090/metrics | grep mcp_tool_calls_total` returns a nonzero counter after any stdio tool call — verifies SL-1 and SL-2 end-to-end wiring. Paired test: `tests/test_prometheus_exporter_http.py` (SL-1) and `tests/integration/test_sigterm_shutdown.py` (SL-2) assert the counter and the HTTP endpoint in CI.
- [ ] `tests/integration/test_sigterm_shutdown.py` passes: SIGTERM delivery causes `MultiRepositoryWatcher.stop()`, then `RefPoller.stop()`, then `StoreRegistry.shutdown()` to complete in that order within 5s wall-time. (verifies SL-2)
- [ ] `tests/security/test_symlink_escape.py` passes: a symlink inside an allowed root pointing to `/etc/passwd` returns `False` from `path_within_allowed`; candidates inside allowed roots return `True`. (verifies SL-3)
- [ ] `grep -rn '\.resolve()' mcp_server/security/ mcp_server/cli/stdio_runner.py` returns zero un-exempted occurrences in the allowlist-check path. Paired pytest: `tests/security/test_symlink_escape.py`. (verifies SL-3)
- [ ] `tests/test_health_surface.py` passes: both `handle_get_status` and `gateway.get_status` responses include a `repositories` array; each entry has `{repo_id, tracked_branch, index_path_exists, git_dir_exists, last_indexed_commit, staleness_reason}`; stale repos (missing `.git` or missing `index_path`) carry non-null `staleness_reason`. (verifies SL-4)
- [ ] `tests/test_sqlite_pool.py` passes: 16 concurrent readers against a default-size-4 pool complete with zero `database is locked`. (verifies SL-5)
- [ ] `tests/test_schema_strict.py` passes: default-strict schema mismatch raises `SchemaMismatchError` with rebuild instructions in `__str__`; `--rebuild-on-schema-mismatch` performs the rebuild and retries the load successfully. (verifies SL-6)
- [ ] `BREAKING-CHANGES.md` exists at repo root and documents migrations 001–005 plus the P10 strict-compatibility default flip. (verifies SL-6)

## Verification

End-to-end after all lanes merge to `main`:

```sh
# 1. Acceptance greps + file existence
grep -rn '\.resolve()' mcp_server/security/ mcp_server/cli/stdio_runner.py   # expect zero un-exempted
test -f BREAKING-CHANGES.md

# 2. Unit + integration suites
pytest -q \
  tests/test_prometheus_exporter_http.py \
  tests/integration/test_sigterm_shutdown.py \
  tests/security/test_symlink_escape.py \
  tests/test_health_surface.py \
  tests/test_sqlite_pool.py \
  tests/test_schema_strict.py

# 3. Live metrics + SIGTERM smoke
MCP_METRICS_PORT=9090 python -m mcp_server.cli stdio &
PID=$!
sleep 2
# Exercise a tool call via stdio (symbol_lookup or get_status) using the existing integration harness
curl -s localhost:9090/metrics | grep mcp_tool_calls_total    # expect nonzero
kill -TERM $PID
wait $PID   # must exit within 5s

# 4. Full regression
pytest -q
```

On ExitPlanMode approval, copy this plan to `plans/phase-plan-v1-p10.md` in the repo and commit with `chore(plans): add P10 phase plan` BEFORE `/execute-phase p10` is invoked (per P9 lesson — `verify_harness.sh` blocks on untracked plan files).
