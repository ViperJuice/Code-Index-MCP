# PHASE-4-multi-repo-watcher: Phase 4 — Default-Branch-Only Indexing & Multi-Repo Watcher

> Plan doc produced by `/plan-phase P4 --consensus` against `specs/phase-plans-v1.md` lines 294–325. On approval, handed off to `/execute-phase p4`.
>
> Consensus note: three Plan teammates were spawned per `--consensus`; all three went idle without delivering proposals across two ping rounds. Orchestrator synthesized architecture inline from the spec + Explore findings. Record in Execution Notes.

## Context

P1 + P2A + P2B + P3 + P6A are merged. Post-P3, the dispatcher routes plugin + semantic access per `ctx: RepoContext`, but the file watcher is still single-root: it captures cwd at startup, watches only that directory, and routes every file event to `dispatcher.index_file(path)` regardless of branch. This means (a) repos other than cwd aren't watched at all, and (b) editing a file on a non-tracked branch silently pollutes the tracked-branch index — P1's `should_reindex_for_branch` lives in `GitAwareIndexManager` but isn't called at the event-handler level.

### What exists

- **`mcp_server/watcher_multi_repo.py`** (369 LOC) — already-written but dead code. Three classes:
  - `GitMonitor` (L26–47) — polls `RepositoryRegistry` for repos, invokes a callback. Has `start`/`stop`.
  - `MultiRepositoryHandler(FileSystemEventHandler)` (L106–128) — per-repo event handler with `repo_id`, `repo_path`, `parent_watcher` refs.
  - `MultiRepositoryWatcher` (L129–…) — composes a `Dict[repo_id, Observer]` (one `Observer` per repo, confirmed at L144–145 and L238). Public surface: `start_watching_all()` (L155), `stop_watching_all()` (L168), `add_repository(repo_path) -> repo_id` (L185), `remove_repository(repo_id)` (L201).
  - Nothing imports it from mainline code (verified via grep).
- **`mcp_server/watcher.py`** (245 LOC) — existing single-root `FileWatcher`. `_Handler(FileSystemEventHandler)` (L68) holds a `threading.Lock` (L93) + `threading.Event` (L94) + debouncing worker `threading.Thread` (L95). `on_any_event(event)` at L206 is the dispatch point — **does not consult `should_reindex_for_branch` or `.gitignore` here**. `_is_excluded(path)` at L47 filters vendor dirs but uses a hardcoded set, not the repo's `.gitignore`. `FileWatcher` ctor (L228) takes `root` + `dispatcher` + optional `query_cache`.
- **`mcp_server/storage/git_index_manager.py`** (475 LOC). `should_reindex_for_branch(current, tracked)` at L15. `GitAwareIndexManager.sync_repository_index(repo_id, force_full=False) -> IndexSyncResult` at L80 already implements the full "diff vs `last_indexed_commit`, trigger incremental reindex" flow, including the branch guard (`if not should_reindex_for_branch(...)` at L113) and the `last_indexed_commit` update. Incremental helpers: `_get_changed_files(repo_path, from_commit, to_commit)` at L188 shells `git diff --name-status`, `_incremental_index_update(repo_id, changes)` at L232 dispatches D→`remove_file`, R→`move_file`, M/A→`index_file`. `RepositoryRegistry.update_indexed_commit(repo_id, commit, branch)` at `repository_registry.py:506-532` is the thread-safe mutation API.
- **`RepositoryInfo`** (`mcp_server/storage/multi_repo_manager.py:28–53`) already carries `current_commit`, `last_indexed_commit`, `last_indexed_branch`, `current_branch`, `tracked_branch` — P4 needs no schema changes.
- **Entry-point wiring today**: `mcp_server/cli/stdio_runner.py:243–248` + `:284–289` constructs a single `FileWatcher(root=current_dir, dispatcher=dispatcher)` from captured cwd inside `lazy_initialize` AND the `on_initialized` callback path. `mcp_server/gateway.py:49,86,732,816` constructs a parallel `FileWatcher(Path("."), dispatcher, query_cache)` for the HTTP gateway.
- **`RepositoryRegistry.get_all_repositories() -> Dict[str, Any]`** at `mcp_server/storage/repository_registry.py:308` and `list_all() -> List[Any]` at L383 — the enumeration APIs `MultiRepoWatcher` calls on start.
- **No `mcp_server/watcher/` package directory exists today** — P4 creates `mcp_server/watcher/__init__.py` + `mcp_server/watcher/ref_poller.py`.
- **No git library (gitpython / pygit2 / dulwich) in `pyproject.toml` deps** — shell out to git.

### Why this is three parallel lanes, not a preamble + waves

The MultiRepoWatcher public surface already exists in `watcher_multi_repo.py`. No freeze needed to unblock parallel work. SL-1 owns the watcher files end-to-end; SL-2 introduces a new disjoint package (`mcp_server/watcher/`); SL-3 (bootstrap) is the sole writer of stdio_runner.py + bootstrap.py + gateway.py with respect to watcher construction and must see the post-SL-1 + post-SL-2 state — so it serializes as the tail. No SL-0 preamble required.

## Interface Freeze Gates

- [ ] **IF-0-P4-1** — `MultiRepositoryWatcher` public surface: `__init__(multi_repo_manager, dispatcher, repo_resolver)`, `start_watching_all() -> None`, `stop_watching_all() -> None`, `add_repository(repo_path: str) -> str` (returns `repo_id`), `remove_repository(repo_id: str) -> None`. Location: `mcp_server/watcher_multi_repo.py`. Consumed by SL-3 at bootstrap time; the current class already has this shape — SL-1 refines it without signature changes.
- [ ] **IF-0-P4-2** — `RefPoller` public surface: `__init__(registry, git_index_manager, dispatcher, repo_resolver, *, interval_seconds: int = 30)`, `start() -> None`, `stop() -> None`. Location: `mcp_server/watcher/ref_poller.py` (NEW). Consumed by SL-3 at bootstrap time.

## Lane Index & Dependencies

```
SL-1 — MultiRepoWatcher + handler-level branch/gitignore filters
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-2 — Tracked-ref poller (new mcp_server/watcher/ package)
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-3 — Bootstrap wiring (serialized tail)
  Depends on: SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no (solo writer of bootstrap.py + stdio_runner.py + gateway.py watcher construction)
```

DAG is acyclic. SL-1 and SL-2 dispatch in parallel. SL-3 runs solo after both merge.

## Lanes

### SL-1 — MultiRepoWatcher + handler-level branch/gitignore filters

- **Scope**: Promote `mcp_server/watcher_multi_repo.py` from dead code to mainline. Inject `RepoResolver` + `MultiRepositoryManager` at construction so each per-repo handler resolves a `RepoContext` from its `git_common_dir`-anchored workspace_root (not cwd). Add handler-level checks in `mcp_server/watcher.py`: (a) consult `should_reindex_for_branch(current_branch, ctx.tracked_branch)` in `on_any_event` and drop events on the wrong branch; (b) consult the repo's `.gitignore` at the handler level (use existing `mcp_server/core/ignore_patterns.py:build_walker_filter` from P1's SL-4) so in-flight file events on ignored paths are dropped. Teach `MultiRepositoryHandler` to accept a `RepoContext` at construction and pass `ctx` to every `dispatcher.index_file(ctx, path)` / `remove_file(ctx, path)` / `move_file(ctx, old, new)` call per the P2B Protocol. Preserve the per-repo `Observer` architecture.
- **Owned files**: `mcp_server/watcher_multi_repo.py`, `mcp_server/watcher.py`, `tests/test_watcher.py` (extend), `tests/test_watcher_multi_repo.py` (NEW).
- **Interfaces provided**: IF-0-P4-1 impl; handler-level branch+gitignore drop behavior.
- **Interfaces consumed**: `RepoContext`, `RepoResolver` (pre-existing), `should_reindex_for_branch` (pre-existing at `git_index_manager.py:15`), `build_walker_filter` (pre-existing at `mcp_server/core/ignore_patterns.py`), `DispatcherProtocol` (pre-existing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_watcher.py` (extend), `tests/test_watcher_multi_repo.py` (NEW) | Handler drops event when `current_branch != ctx.tracked_branch` (verify dispatcher.index_file NOT called via mock); Handler drops event when path matches repo `.gitignore` (verify via mock); `MultiRepositoryWatcher(manager, dispatcher, resolver).start_watching_all()` spawns one Observer per registered repo (verify count); `add_repository(path)` after start begins watching; `remove_repository(repo_id)` stops its Observer without stopping others; shutdown joins all Observers cleanly (no leftover threads after `stop_watching_all()`) | `uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/watcher_multi_repo.py`, `mcp_server/watcher.py` | — | — |
| SL-1.3 | verify | SL-1.2 | SL-1 owned files | all SL-1 tests + existing watcher tests | `uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py -v` |

### SL-2 — Tracked-ref poller

- **Scope**: Create `mcp_server/watcher/` package (NEW). Implement `RefPoller` class that, for each repo in `RepositoryRegistry`, polls `refs/heads/<tracked_branch>` every `interval_seconds` (default 30). Two poll strategies in priority order: (a) read `.git/refs/heads/<tracked_branch>` as a text file if present (fast path); (b) shell out to `git --git-dir=<path> rev-parse refs/heads/<tracked_branch>` as fallback (packed refs). On advance (`tip_sha != repo_info.last_indexed_commit`), call `GitAwareIndexManager.check_and_update_index(repo_id, ...)` — that existing method already handles the diff + incremental reindex + `last_indexed_commit` update. Shutdown via `threading.Event` + `Thread.join`. Defensive: catch + log exceptions per-repo so one failing repo doesn't kill the poller loop.
- **Owned files**: `mcp_server/watcher/__init__.py` (NEW), `mcp_server/watcher/ref_poller.py` (NEW), `tests/test_ref_poller.py` (NEW).
- **Interfaces provided**: IF-0-P4-2 impl.
- **Interfaces consumed**: `RepositoryRegistry.list_all()` (pre-existing at `repository_registry.py:383`), `GitAwareIndexManager.sync_repository_index` (pre-existing at `git_index_manager.py:80`), `RepositoryInfo.tracked_branch` / `.last_indexed_commit` (pre-existing at `multi_repo_manager.py:39-41`).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_ref_poller.py` (NEW) | Against an ephemeral `tmp_path` git repo with 2 commits on `main`: poller started, advance `main` to a new commit, assert `GitAwareIndexManager.sync_repository_index` called within `2 * interval_seconds`; a repo whose `tracked_branch` is unset is skipped; a repo whose `refs/heads/<tracked_branch>` doesn't exist is skipped with a warning, not crash; exception in one repo's poll doesn't stop polling of the others; `stop()` joins the thread within 1s | `uv run pytest tests/test_ref_poller.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/watcher/__init__.py`, `mcp_server/watcher/ref_poller.py` | — | — |
| SL-2.3 | verify | SL-2.2 | SL-2 owned files | all SL-2 tests | `uv run pytest tests/test_ref_poller.py -v` |

### SL-3 — Bootstrap wiring (serialized tail)

- **Scope**: Replace the single-root `FileWatcher(current_dir, dispatcher)` construction in `mcp_server/cli/stdio_runner.py` (L243–248, L284–289) with `MultiRepositoryWatcher(manager, dispatcher, resolver)` + `RefPoller(registry, git_index_manager, dispatcher, resolver)`. Replace the equivalent `FileWatcher(Path("."), dispatcher, query_cache)` in `mcp_server/gateway.py` (L732, L816) the same way. Ensure boot ordering: `StoreRegistry` + `PluginSetRegistry` + `RepositoryRegistry` must be ready BEFORE `MultiRepositoryWatcher.start_watching_all()` and `RefPoller.start()`. Extend `mcp_server/cli/bootstrap.py:initialize_stateless_services()` to expose the pieces needed (registry, git_index_manager handles) if not already returned. Add shutdown hook at stdio server exit: call `stop_watching_all()` + `stop()` + `join()` both before SIGTERM propagation. `tests/test_bootstrap.py` extended with a boot-order fixture that asserts the watcher/poller's `start()` is called AFTER the registries' construction.
- **Owned files**: `mcp_server/cli/bootstrap.py`, `mcp_server/cli/stdio_runner.py`, `mcp_server/gateway.py`, `tests/test_bootstrap.py` (extend), `tests/test_multi_repo_bootstrap_order.py` (NEW if bootstrap.py's existing test file is fragile).
- **Interfaces provided**: none new (consumer).
- **Interfaces consumed**: IF-0-P4-1 (MultiRepositoryWatcher), IF-0-P4-2 (RefPoller), PluginSetRegistry (pre-existing), StoreRegistry (pre-existing), RepositoryRegistry (pre-existing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_bootstrap.py` (extend), `tests/test_multi_repo_bootstrap_order.py` (NEW if needed) | With two registered repos, `stdio_runner.run()` invokes `MultiRepositoryWatcher.start_watching_all` with exactly those two repos; `RefPoller.start()` is called after that; `FileWatcher` is NOT constructed anywhere in stdio_runner.py or gateway.py; boot order assertion: a mock StoreRegistry records `.get()` calls and a mock MultiRepositoryWatcher records `.start_watching_all()` — the latter's first call timestamp > the former's last construction timestamp | `uv run pytest tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py -v` |
| SL-3.2 | impl | SL-3.1 | all SL-3 owned files | — | — |
| SL-3.3 | verify | SL-3.2 | SL-3 owned files | all SL-3 tests + existing bootstrap suite | `uv run pytest tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_gateway.py -v` |

## Execution Notes

- **Single-writer files**:
  - `mcp_server/watcher_multi_repo.py`, `mcp_server/watcher.py` — SL-1 only.
  - `mcp_server/watcher/**` — SL-2 only.
  - `mcp_server/cli/stdio_runner.py`, `mcp_server/cli/bootstrap.py`, `mcp_server/gateway.py` — SL-3 only.

- **No SL-0 preamble**: The public surfaces of both `MultiRepositoryWatcher` (already in-code) and `RefPoller` (new but fully owned by SL-2) have no cross-lane tension. SL-3 consumes concrete impls post-merge rather than stubbed interfaces.

- **Known destructive changes** (stale-base whitelist — for `pre_merge_destructiveness_check.sh`):
  - SL-3 removes the `FileWatcher` construction blocks at `stdio_runner.py:243–248,284–289` and `gateway.py:732,816`. The `FileWatcher` class in `mcp_server/watcher.py` stays (used by SL-1's `MultiRepositoryWatcher` as the per-repo underlying implementation). No files are deleted.

- **Expected add/add conflicts**: none — SL-2's new `mcp_server/watcher/` package has no overlap with SL-1's existing `watcher.py` / `watcher_multi_repo.py`. No SL-0 stub pattern in this phase.

- **SL-0 re-exports**: none — no new `__init__.py` re-exports; `mcp_server/watcher/__init__.py` is empty (no `from .ref_poller import RefPoller`) to avoid the eager-re-export risk. Consumers import `from mcp_server.watcher.ref_poller import RefPoller` directly.

- **Worktree naming**: execute-phase allocates unique worktree names via `scripts/allocate_worktree_name.sh`.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-1 or pre-SL-2 merge (SL-3's upstream dependencies), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.

- **Harness preflight**: Before dispatch, orchestrator runs `bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh`. All checks must pass.

- **Architectural choices (consensus unavailable — single-architect synthesis)**:
  - Plan teammates failed to deliver across two ping rounds. Orchestrator synthesized the lane decomposition from the spec + inline Explore findings. Choices below are single-architect rather than majority-of-three; user should review and flag dissent during ExitPlanMode approval.
  - **Per-repo Observers, not shared Observer**: the existing `watcher_multi_repo.py` already does this; spec agrees ("Keep existing shape unless a reason emerges"). Accepted.
  - **Handler-level branch/gitignore drop, not walker-level only**: P1 landed the walker-level fix; P4 hardens the event handler path too. Spec requires this.
  - **Subprocess-based ref polling, not git library**: no git lib in deps; shelling out to `git rev-parse` is idiomatic in the existing codebase. `.git/refs/heads/<branch>` text-file fast-path for unpacked refs.
  - **SL-3 as a dedicated serialized tail, not line-range split**: prior phases showed line-range splitting dispatcher/entry-point files is fragile. One solo writer post parallel lanes is cleaner.
  - **No SL-0 preamble**: unlike P2B/P3 where interface freezes unblocked 4+ parallel lanes, P4's 3 lanes have clean ownership without one.

- **Spec inaccuracies flagged for phase-plans v2**:
  1. Spec line 300 says "`MultiRepoWatcher` is imported and instantiated in the entry point" — class is actually named `MultiRepositoryWatcher`. Update naming in v2.
  2. Spec line 317 implies `mcp_server/watcher/ref_poller.py` — confirm the new package is acceptable vs a flat `mcp_server/ref_poller.py`. The plan uses the package form per spec.

## Acceptance Criteria

- [ ] `.venv/bin/python -c "from mcp_server.watcher_multi_repo import MultiRepositoryWatcher; print('OK')"` exits 0.
- [ ] `.venv/bin/python -c "from mcp_server.watcher.ref_poller import RefPoller; print('OK')"` exits 0.
- [ ] `tests/test_watcher_multi_repo.py::test_handler_drops_event_on_non_tracked_branch` asserts that an event on `current_branch != tracked_branch` does NOT call `dispatcher.index_file` (paired behavioral test, not bare grep).
- [ ] `tests/test_watcher_multi_repo.py::test_handler_drops_event_matching_gitignore` asserts that events on paths in `.gitignore` do NOT call `dispatcher.index_file`.
- [ ] `tests/test_ref_poller.py::test_ref_advance_triggers_reindex` boots a poller against a `tmp_path` repo, advances `refs/heads/main`, asserts `GitAwareIndexManager.sync_repository_index` called within `2 * interval_seconds`.
- [ ] `tests/test_ref_poller.py::test_repo_error_does_not_kill_poller` induces an exception in one repo's poll, asserts other repos keep polling.
- [ ] `tests/test_bootstrap.py::test_watcher_starts_after_registries` asserts boot order — `StoreRegistry` constructed before `MultiRepositoryWatcher.start_watching_all()`.
- [ ] `rg -nE 'FileWatcher\s*\(' mcp_server/cli/stdio_runner.py mcp_server/gateway.py` returns zero hits (paired with the `test_watcher_starts_after_registries` test — not bare grep).
- [ ] `uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py tests/test_ref_poller.py tests/test_bootstrap.py tests/test_gateway.py -v` exits 0.

## Verification

```bash
# Pre-flight
bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh

# Sync environment
uv sync --extra dev

# Imports + public surface
.venv/bin/python - <<'PY'
from mcp_server.watcher_multi_repo import MultiRepositoryWatcher
from mcp_server.watcher.ref_poller import RefPoller
import inspect
mr_sig = inspect.signature(MultiRepositoryWatcher.__init__)
rp_sig = inspect.signature(RefPoller.__init__)
print("MultiRepositoryWatcher:", list(mr_sig.parameters))
print("RefPoller:", list(rp_sig.parameters))
print("MRW methods:", [m for m in dir(MultiRepositoryWatcher) if not m.startswith("_")])
print("RP methods:", [m for m in dir(RefPoller) if not m.startswith("_")])
PY

# FileWatcher is gone from entry points
rg -nE 'FileWatcher\s*\(' mcp_server/cli/stdio_runner.py mcp_server/gateway.py && echo "FAIL: single-root FileWatcher remains" || echo "entry-points OK"

# Integration: boot the server with two mock registered repos, verify watcher starts per repo
.venv/bin/python -m pytest tests/test_bootstrap.py::test_watcher_starts_after_registries -v

# Full targeted test suite
.venv/bin/python -m pytest \
  tests/test_watcher.py \
  tests/test_watcher_multi_repo.py \
  tests/test_ref_poller.py \
  tests/test_bootstrap.py \
  tests/test_gateway.py \
  tests/test_dispatcher.py \
  tests/test_dispatcher_advanced.py \
  -v
```

---

### Hand-off

On ExitPlanMode approval, the orchestrator will:

1. Write this doc to `plans/phase-plan-v1-p4.md` (already done).
2. Run `python ~/.claude/skills/plan-phase/scripts/validate_plan_doc.py plans/phase-plan-v1-p4.md` and fix any errors.
3. Emit three `TaskCreate` calls (SL-1 / SL-2 / SL-3) with `test / impl / verify` children and DAG metadata.
4. User invokes `/execute-phase p4` when ready.
