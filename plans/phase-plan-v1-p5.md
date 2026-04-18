# P5: STDIO Hardening & Multi-Repo Integration Tests

## Context

Phases 1–4 landed the multi-repo foundation: repo identity (`compute_repo_id` at `mcp_server/repository/repo_identity.py:69-112`, Tier 1 `git rev-parse --git-common-dir` → worktree-safe), registry + store layering (`RepositoryRegistry.register_repository` at `mcp_server/storage/repository_registry.py:245-297`), plugin/semantic registries (P3), and `MultiRepositoryWatcher` + `RefPoller` wiring into `stdio_runner` and the gateway (P4, commit `cb7eccf`).

The STDIO server's public tool handlers live in `mcp_server/cli/tool_handlers.py` (647 LOC) and are dispatched from `mcp_server/cli/stdio_runner.py::_serve()` (lines 126–485, dispatch at 379–430). `reindex` (line 402) already validates its `path` arg against `_allowed_roots()` + `_path_within_allowed()` (both in `mcp_server/cli/bootstrap.py:74-113`). Three other public handlers that accept path-shaped arguments bypass the guard today:

- `search_code` (line 142): `repository` arg passes directly to `_resolve_ctx()` (line 163) without path validation.
- `symbol_lookup` (line 84): accepts optional `repository` via `_resolve_ctx()` at line 97 — same bypass.
- `summarize_sample` (line 523): `paths` list is passed to DB queries (line 553) unvalidated.

`write_summaries` (line 475) has no path-shaped argument; excluded from the guard.

No `handshake` tool exists. `MCP_CLIENT_SECRET` is not consumed anywhere. `stdio_runner._serve()` has local closures (`init_lock`, `lazy_summarizer`) suitable for holding per-process handshake state.

Test infrastructure (`tests/conftest.py`) provides `temp_db_path`, `sqlite_store`, `populated_sqlite_store`, `repo_ctx`, `store_registry`, `repo_resolver`, `dispatcher_factory`. Reusable temp-repo idioms in `tests/test_ref_poller.py:19-32` (`_make_git_repo`) and mocked-registry patterns in `tests/test_dispatcher_p3_integration.py:50-64`. `RefPoller.interval_seconds` defaults to 30 (`mcp_server/watcher/ref_poller.py:22`) — must be overridden for fast tests. Hazard: `mock_file_system` in conftest monkey-patches `Path.exists()` globally — avoid; use `tmp_path` only.

In-process boot is clean: `initialize_stateless_services()` at `mcp_server/cli/bootstrap.py:25-64` returns registries + dispatcher with no module-level singletons. Watchers are optional (cleanup via `stop_watching_all()` + `RefPoller.stop()` with bounded timeout).

## Interface Freeze Gates

- [ ] **IF-0-P5-1** — Every public MCP tool handler that accepts a path-shaped argument (`reindex.path`, `search_code.repository`, `symbol_lookup.repository`, `summarize_sample.paths[*]`) validates it via `_path_within_allowed(p, _allowed_roots())` before dispatch. On mismatch the handler returns an MCP error payload with code `path_outside_allowed_roots`. `write_summaries` is explicitly exempt (no path args). Guard only fires when the argument resolves to a filesystem path (`_looks_like_path` predicate gates the check so repo-name registry lookups still work for `search_code.repository`).
- [ ] **IF-0-P5-2** — Handshake protocol. `handshake.py::HandshakeGate` class: constructor reads `MCP_CLIENT_SECRET` env once; `.check(name: str, arguments: dict) -> Optional[dict]` returns `None` when authenticated or tool is `handshake`, else returns an MCP error payload with code `handshake_required`; `.verify(secret: str) -> bool` uses `hmac.compare_digest`. `_serve()` instantiates one `HandshakeGate` per process; `call_tool()` invokes `.check()` before dispatch. When `MCP_CLIENT_SECRET` is unset, `_serve()` logs exactly one warning line `running unauthenticated — MCP_CLIENT_SECRET not set` at startup via the `mcp_server.cli.stdio_runner` logger; no gate enforcement.
- [ ] **IF-0-P5-3** — Integration-test fixture API. `tests/fixtures/multi_repo.py` exports `build_temp_repo(tmp_path: Path, name: str, *, seed_files: dict[str, str] | None = None) -> tuple[Path, str]` (returns `(repo_path, repo_id)`) and `boot_test_server(tmp_path: Path, repos: list[Path], *, enable_watchers: bool = False, poll_interval: float = 2.0, client_secret: str | None = None) -> ContextManager[TestServerHandle]` where `TestServerHandle` exposes `.call_tool(name, arguments) -> dict`, `.registry`, `.dispatcher`, `.stop()`. Teardown is synchronous with a 5s bounded timeout on watcher joins.

## Lane Index & Dependencies

```
SL-1 — Handler-level path sandbox
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-2 — Optional client handshake
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-3 — Multi-repo integration test
  Depends on: SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no (serialized after SL-1 + SL-2 merge)
```

## Lanes

### SL-1 — Handler-level path sandbox

- **Scope**: Extend `_path_within_allowed()` enforcement from `reindex` to the three other path-accepting public handlers: `search_code.repository` (when path-shaped), `symbol_lookup.repository` (when path-shaped), and every entry of `summarize_sample.paths`. Guard returns an MCP error payload with code `path_outside_allowed_roots` on mismatch. `write_summaries` is untouched (no path args). Introduce a `_looks_like_path(x: str) -> bool` helper that returns True when the string contains a path separator or resolves to an existing filesystem entity — needed because `search_code.repository` also accepts registered repo names/aliases.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `tests/test_handler_path_sandbox.py` (new).
- **Interfaces provided**: IF-0-P5-1.
- **Interfaces consumed**: `_allowed_roots()`, `_path_within_allowed()` from `mcp_server/cli/bootstrap.py` (pre-existing).
- **Execution hint**: `claude-sonnet-4-6` / medium — contract-authoring lane (SL-3 pins the error-code string verbatim).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_handler_path_sandbox.py` | `path_outside_allowed_roots` error for `search_code`, `symbol_lookup`, `summarize_sample`; pass-through for `reindex` (unchanged) and `write_summaries` (no-arg); `_looks_like_path` unit tests including repo-name pass-through | `pytest tests/test_handler_path_sandbox.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/cli/tool_handlers.py` | — | — |
| SL-1.3 | verify | SL-1.2 | `mcp_server/cli/**`, `tests/test_handler_path_sandbox.py`, `tests/test_*handlers*.py` | all SL-1 tests + any existing handler tests | `pytest tests/test_handler_path_sandbox.py tests/test_*handlers*.py -v` |

### SL-2 — Optional client handshake

- **Scope**: Add a new `handshake` MCP tool and an `MCP_CLIENT_SECRET` env gate. Introduce `mcp_server/cli/handshake.py` exporting `class HandshakeGate`: constructor reads env once; `.check(name, arguments)` returns `None` when `authenticated` flag is True or the tool being called is `handshake`, else returns the `handshake_required` error payload; `.verify(secret)` uses `hmac.compare_digest` to prevent timing leaks and flips the flag on match. In `stdio_runner.py::_serve()`, instantiate one `HandshakeGate` per process (closure-scoped, not module-level, so test fixtures can boot fresh instances). `call_tool()` invokes `gate.check()` as its first action; the `handshake` branch calls `gate.verify()`. When `MCP_CLIENT_SECRET` is unset, emit exactly one `running unauthenticated — MCP_CLIENT_SECRET not set` warning via the `mcp_server.cli.stdio_runner` logger at `_serve()` entry. Register `handshake` in the tool-list builder.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `mcp_server/cli/handshake.py` (new), `tests/test_handshake.py` (new).
- **Interfaces provided**: IF-0-P5-2.
- **Interfaces consumed**: (pre-existing) — root lane with no cross-lane deps.
- **Execution hint**: `claude-sonnet-4-6` / medium — security-adjacent code; constant-time compare and single-warning-line semantics must be right.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_handshake.py` | `HandshakeGate` unit: pre-handshake returns `handshake_required`; `handshake(wrong)` returns `handshake_required`; `handshake(correct)` returns `{authenticated: True}`; subsequent calls pass. `hmac.compare_digest` usage verified via `inspect.getsource`. Startup-warning-once test via `caplog` + `mcp_server.cli.stdio_runner` logger | `pytest tests/test_handshake.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/cli/handshake.py`, `mcp_server/cli/stdio_runner.py` | — | — |
| SL-2.3 | verify | SL-2.2 | `mcp_server/cli/**`, `tests/test_handshake.py` | all SL-2 tests + any existing stdio_runner tests | `pytest tests/test_handshake.py tests/test_*stdio*.py -v` |

### SL-3 — Multi-repo integration test

- **Scope**: Build `tests/fixtures/multi_repo.py` (temp-repo builder, in-process server boot helper, optional watcher start with short interval, bounded-timeout teardown) and `tests/integration/test_multi_repo_server.py` (four tests mapped to the spec's exit criteria). Fixture uses `initialize_stateless_services()` + `RepositoryRegistry.register_repository()` unchanged. `boot_test_server` accepts an optional `client_secret` so handshake-enabled variants exercise SL-2's gate via per-test `monkeypatch.setenv`. `poll_interval` parameter passed to `RefPoller(interval_seconds=poll_interval)` so branch-switch test runs in seconds, not minutes. Context manager calls `.stop_watching_all()` and `RefPoller.stop()` with a 5s bounded join; log-but-swallow on timeout.
- **Owned files**: `tests/fixtures/multi_repo.py` (new), `tests/integration/test_multi_repo_server.py` (new).
- **Interfaces provided**: IF-0-P5-3.
- **Interfaces consumed**: IF-0-P5-1, IF-0-P5-2, `initialize_stateless_services` (pre-existing) at `mcp_server/cli/bootstrap.py:25-64`, `RepositoryRegistry.register_repository` (pre-existing) at `mcp_server/storage/repository_registry.py:245-297`, `compute_repo_id` (pre-existing) at `mcp_server/repository/repo_identity.py:69-112`.
- **Execution hint**: `claude-sonnet-4-6` / medium — algorithmic/computed logic with tests-first; four independent exit-criterion tests to author.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/integration/test_multi_repo_server.py` | `test_repo_isolation` (A-search returns no B paths, vice versa); `test_branch_switch_ignored` (non-tracked branch mutation ignored after 2× poll interval); `test_worktree_equals_main` (worktree of A resolves to same `repo_id` as A, `symbol_lookup` returns same results); `test_concurrent_no_db_lock` (two threads, distinct repos, no `sqlite3.OperationalError: database is locked`) | `pytest tests/integration/test_multi_repo_server.py -v` |
| SL-3.2 | impl | SL-3.1 | `tests/fixtures/multi_repo.py`, `tests/integration/test_multi_repo_server.py` | — | — |
| SL-3.3 | verify | SL-3.2 | `tests/**` | full SL-3 suite + smoke of existing integration tests | `pytest tests/integration/test_multi_repo_server.py tests/integration/test_phase1_foundation.py -v` |

## Execution Notes

- **Single-writer files**: none. SL-1 owns `tool_handlers.py`; SL-2 owns `stdio_runner.py` + `handshake.py`; SL-3 owns both new test files. No shared barrel indexes, generated types, or routers.
- **Known destructive changes**: none — every lane is purely additive. SL-1 adds imports and wraps handler bodies with guards; SL-2 adds a new module, a new tool, and a gate-check line in `call_tool`; SL-3 adds two new files.
- **Expected add/add conflicts**: none. SL-2's edit to `stdio_runner.py` is sole-writer; SL-1 does not touch that file.
- **SL-0 re-exports**: none — no SL-0 preamble lane in this phase.
- **Worktree naming**: execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`. Plan doc does not need to spell out lane worktree paths.
- **Stale-base guidance**: Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. SL-3 executes strictly after SL-1 and SL-2 merge, so its base is never pre-SL-1/SL-2 if execute-phase's DAG gating works. If SL-3 finds its worktree base is pre-SL-1 or pre-SL-2 merge, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.
- **Secret-compare discipline**: SL-2 MUST use `hmac.compare_digest` for secret comparison, not `==`. Timing-side-channel rejection is a testable invariant (SL-2.1 asserts via `inspect.getsource(HandshakeGate.verify)` containing `compare_digest`).
- **Test-fixture concurrency hygiene**: SL-3 must NOT import or use `mock_file_system` from conftest — it monkey-patches `Path.exists()` globally and breaks pytest-xdist. Use `tmp_path` fixtures only. Documented in `tests/fixtures/multi_repo.py` module docstring.
- **Watcher teardown timeout**: 5s bounded join; log-but-swallow on timeout. `RefPoller.stop()` joins a daemon thread; unbounded join makes test suites flaky on CI.
- **Error-code string is part of the contract**: IF-0-P5-1 pins the MCP error code to `path_outside_allowed_roots`; SL-3's `test_repo_isolation` does not assert the code but SL-1's unit tests and the handler contract both do. Changing the string in SL-1 breaks the contract SL-3 consumes.

## Acceptance Criteria

- [ ] `pytest tests/test_handler_path_sandbox.py::test_every_path_handler_guards -v` — parametrized over `(reindex, path=/etc), (search_code, repository=/etc), (symbol_lookup, repository=/etc), (summarize_sample, paths=[/etc])`; every case returns an MCP error payload containing the string `path_outside_allowed_roots`.
- [ ] `pytest tests/test_handler_path_sandbox.py::test_non_path_handlers_untouched -v` — `write_summaries(limit=1)` with narrow `MCP_ALLOWED_ROOTS` succeeds (no false guard).
- [ ] `pytest tests/test_handler_path_sandbox.py::test_repository_name_passthrough -v` — `search_code(repository="registered-repo-name")` passes to registry lookup, is NOT rejected by the path guard.
- [ ] `pytest tests/test_handshake.py::test_startup_warning_when_unset -v` — `_serve()` boot with `MCP_CLIENT_SECRET` unset produces exactly one `running unauthenticated` log record on the `mcp_server.cli.stdio_runner` logger (via `caplog`; count == 1).
- [ ] `pytest tests/test_handshake.py::test_handshake_required_when_set -v` — with env set: first tool call returns error code `handshake_required`; `handshake(secret="wrong")` returns `handshake_required`; `handshake(secret=correct)` returns `{authenticated: True}`; subsequent tool calls succeed.
- [ ] `pytest tests/test_handshake.py::test_constant_time_compare -v` — `inspect.getsource(HandshakeGate.verify)` contains `compare_digest`.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_repo_isolation -v` — indexing two distinct temp repos and running `search_code(query, repository=A)` returns zero results whose file paths are under repo B; vice versa.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_branch_switch_ignored -v` — after checking out a non-tracked branch in repo A and modifying a file, waiting `2 × poll_interval` produces zero new index entries.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_worktree_equals_main -v` — `git worktree add` a second path to repo A; `compute_repo_id(worktree_path).repo_id == compute_repo_id(main_path).repo_id`; `symbol_lookup` through the worktree path returns identical results to the main path.
- [ ] `pytest tests/integration/test_multi_repo_server.py::test_concurrent_no_db_lock -v` — two threads, each calling `search_code` against a distinct repo simultaneously; neither raises `sqlite3.OperationalError: database is locked`.

## Verification

```bash
# SL-1 unit
pytest tests/test_handler_path_sandbox.py -v

# SL-2 unit
pytest tests/test_handshake.py -v

# SL-3 integration (the phase-gate quality bar per spec line 418)
pytest tests/integration/test_multi_repo_server.py -v

# Full P5 suite
pytest tests/test_handler_path_sandbox.py tests/test_handshake.py tests/integration/test_multi_repo_server.py -v

# End-to-end smoke (from spec lines 422-441, condensed)
MCP_ALLOWED_ROOTS=/tmp/repo-a,/tmp/repo-b python -m mcp_server.cli.server_commands &
# ... register both, run scoped searches, confirm no cross-contamination
# (full sequence in specs/phase-plans-v1.md:420-441)
```

Any `database is locked` error, cross-contamination between repo A and repo B results, reindex-on-non-tracked-branch-switch observation, or missing `running unauthenticated` warning when `MCP_CLIENT_SECRET` is unset fails the phase.
