# P17: Durability & Multi-Instance Safety

## Context

P16 landed the shared vocabulary: error taxonomy, env-var lazy getters, `ValidationError` dataclass, and `reset_process_singletons()`. P17 is the first of the two consumer phases (P17 and P18 run in parallel). P17 owns durability: the registry must survive concurrent multi-instance writes, the watcher/indexer must recover cleanly from three classes of failure (branch-ref edges, sweep exceptions, partial-error indexing), SQLite must fail closed under `ENOSPC`, `SchemaMigrator` must back up before mutating, and the 46 pre-existing test failures must be burned down to ≤5.

### What actually exists today (vs. what spec / handoff assert)

The P16 execute-phase handoff and the IF-0-P16-* register had several drift points that the Explore reconnaissance surfaced. Capturing here so every lane reads against reality, not the handoff's memory:

- **Error taxonomy lives at `mcp_server/core/errors.py`** — handoff incorrectly said `security/errors.py`. `ArtifactError:118`, `TransientArtifactError:124`, `TerminalArtifactError:128`, `SchemaMigrationError:132`. All subclass `MCPError` via `ArtifactError`. `SecurityViolationError` / `StartupError` do NOT exist — P17 does not need them.
- **`ValidationError` lives at `mcp_server/config/validation.py:20`** as a frozen dataclass `{code, message, severity}` — NOT an exception. A separate `ValidationError(Exception)` exists at `mcp_server/interfaces/shared_interfaces.py:396`; P17 must not import from that module by accident.
- **`validate_production_config`** at `mcp_server/config/validation.py:263`. `SecurityConfig` at `mcp_server/security/models.py:146` (not `.security.config` — that path does not exist).
- **`reset_process_singletons`** at `mcp_server/cli/bootstrap.py:67` — handoff wrongly said `lifecycle/singletons.py`. No `mcp_server/lifecycle/` directory exists.
- **P16's `reset_process_singletons` is INCOMPLETE.** It nulls `prometheus_exporter._exporter`, `gateway._repo_registry`, `plugin_system.loader._loader`, `plugin_system.discovery._discovery`, `plugin_system.config._config_manager`, `plugins.memory_aware_manager._manager_instance`. It does NOT yet null the three singletons IF-0-P16-4 enumerated: `storage.multi_repo_manager._manager_instance`, `dispatcher.cross_repo_coordinator._coordinator_instance`, `plugins.repository_plugin_loader._loader_instance`. P17 SL-1 adds them.
- **`initialize_stateless_services` at `bootstrap.py:25` does NOT yet call `reset_process_singletons()`**. P17 SL-1's job is to add that call at the top.
- **`MultiRepoWatcher` / `enqueue_full_rescan` do NOT exist** — IF-0-P12-3 never shipped. `ref_poller.py:61` currently invokes `self._git_index_manager.sync_repository_index(repo_info.repository_id)` (incremental). For the three new edge-case events (detached HEAD, force-push, branch-rename) SL-2 adds `GitAwareIndexManager.enqueue_full_rescan(repo_id)` — the minimal new surface sufficient to distinguish full-rescan from incremental-sync at the observability layer. This is promoted to **IF-0-P17-2** since P18 SL-4 (observability counters) will want to reference it, and freezing now prevents drift.
- **`SchemaMigrator.apply(from_version, to_version, db_path)` does NOT exist** — IF-0-P14-3 shipped as `migrate_artifact(extracted_dir: Path, from_version: str, to_version: str) -> Path` at `schema_migrator.py:30`. The "DB" in this codebase is a directory of extracted artifact files, not a single `.sqlite` file. SL-3's backup/rollback adapts accordingly: backup = timestamped copy of `extracted_dir`; rollback on `SchemaMigrationError` = `rmtree(extracted_dir); shutil.move(backup, extracted_dir)`. The exit-criterion phrase "`.backup` copy of the DB" is honored at the directory level.
- **`SchemaMigrationError` is DUPLICATED.** Canonical at `core/errors.py:132`; local duplicate at `schema_migrator.py:16` (with a separate `UnknownSchemaVersionError` sibling). SL-3 deletes the local duplicate and imports the canonical one. `publisher.py:19`'s local `ArtifactError` is P18 territory, not P17's concern.
- **`CrossRepositorySearchCoordinator` exists** at `dispatcher/cross_repo_coordinator.py:632` — the spec's SL-4 hypothesis ("class at wrong module path") was wrong. The real SL-4 root cause: `tests/test_cross_repo_coordinator.py` calls `coordinator._get_target_repositories(scope)` which does not exist on either the outer `CrossRepositorySearchCoordinator` or the inner `CrossRepositoryCoordinator`. SL-4 adds the method to the outer class (scope-resolution helper returning `list[str]` of repo_ids).
- **`RerankerFactory` at `mcp_server/indexer/reranker.py:761`** — NOT `plugins/reranker_factory.py` (the spec's Key-files section was wrong). SL-4 adds `RerankerFactory.create_default()` classmethod returning `TFIDFReranker({})` (no external deps per Explore).
- **`ruff F401` baseline is only 4 offenders**, all in `mcp_server/dispatcher/`: `dispatcher_enhanced.py:{17,32,35}` + `simple_dispatcher.py:11`. Zero in `storage/` or `watcher/`. SL-4's F401 task is tiny.

### Lane-owned file-path realities (vs. spec wording)

The spec wording diverges from reality in a few SL-2/SL-3 ownership claims; fix-up in lane ownership blocks below:

- Spec says SL-2 owns `_walk_directory` in `dispatcher_enhanced.py`. The actual method is `index_directory` at `:1855` with the per-file filter block at `:1897–1928`. The file-size guard inserts after `is_excluded(path)` at `:1918`, before the `index_file` call at `:1928`. SL-2 ownership is **line-range**, not the whole method — scope down to that 10-line block.
- Spec says SL-2 owns `watcher/sweeper.py` end-to-end. It does, but note: `sweeper.py` has no `logging` import today; SL-2 adds it.
- `prometheus_exporter.py` is the natural home for new module-level Counters (pattern at `:62-66`). SL-2 adds `mcp_watcher_sweep_errors_total`; SL-3 adds `mcp_storage_readonly_total`. Both append-only, disjoint lines — single-writer block below pre-authorizes the format.

### Cross-phase landscape

P17 and P18 run in parallel after P16. P16's freeze means **neither phase writes to the same file as the other** (Spec `:906, :963`). The one subtle cross-phase coupling: both phases add counters to `prometheus_exporter.py`. Nothing serial about it — each appends to the module-level counter block. Listed under Execution Notes.

## Interface Freeze Gates

- [ ] **IF-0-P17-1** — Registry save protocol. In `mcp_server/storage/repository_registry.py::save()`:
  - Acquires `fcntl.flock(fd, fcntl.LOCK_EX)` on a sibling file `self.registry_path.with_suffix(".lock")` (created with `O_CREAT | O_WRONLY` if absent, mode `0o600`). Lock is held for the duration of the tmp-write + atomic rename, then released in `finally`.
  - Blocking acquire (no timeout): `save()` callers today (registry.py 13 call sites + multi_repo_manager.py:810) all run in mutation paths, never in tight hot loops. Contention is sub-millisecond (JSON serialize + rename).
  - Atomic-rename pattern (`temp_path.replace(self.registry_path)` at `repository_registry.py:203`) is preserved verbatim. flock wraps it; does not replace it.
  - Idempotent under `OSError` (already-locked) path: re-raise — do NOT fall through to the unlocked rename.
  - Documented in `docs/operations/multi-instance.md` by SL-docs.
- [ ] **IF-0-P17-2** — Full-rescan hook. New method `GitAwareIndexManager.enqueue_full_rescan(repo_id: str) -> None` in `mcp_server/storage/git_index_manager.py`. Semantics: mark the repo's index as stale + invoke the same underlying sync primitive that `sync_repository_index` uses, but without the fast-path that short-circuits when `last_indexed_commit` equals the current tip. Distinct from `sync_repository_index` so ref-poller edge-case events are individually countable (observability + SL-2 test assertions). Idempotent; safe to call when no sync is in progress.

## Lane Index & Dependencies

```
SL-1 — Registry + singleton hygiene
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes

SL-2 — Watcher/indexing resilience
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes

SL-3 — Disk & schema safety
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes

SL-4 — Carry-over debt
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes (see single-writer note on dispatcher_enhanced.py)

SL-docs — Documentation & spec reconciliation (terminal)
  Depends on: SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no (terminal)
```

All four impl lanes are independent roots → max-parallel dispatch by execute-phase.

## Lanes

### SL-1 — Registry + singleton hygiene

- **Scope**: Make `RepositoryRegistry.save()` multi-process safe via flock. Extend `reset_process_singletons()` to cover the three missing singletons from IF-0-P16-4. Wire `reset_process_singletons()` into the top of `initialize_stateless_services()`. Fix the two failing `test_repository_registry_commits.py` tests by using `compute_repo_id(path).repo_id` as the read-back key.
- **Owned files**: `mcp_server/storage/repository_registry.py`, `mcp_server/cli/bootstrap.py`, `tests/test_repository_registry_commits.py` (fix in place), `tests/test_registry_concurrency.py` (new), `tests/test_singleton_reset.py` (new).
- **Interfaces provided**: IF-0-P17-1 (registry flock). Extended `reset_process_singletons()` body (same name, same signature — additive inside the function body, nulling 3 more singletons).
- **Interfaces consumed**: `compute_repo_id` from `mcp_server.storage.repo_identity`; existing `threading.RLock` in `RepositoryRegistry`; module-level singletons at `storage/multi_repo_manager.py:816`, `dispatcher/cross_repo_coordinator.py:573`, `plugins/repository_plugin_loader.py:542`.
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_registry_concurrency.py` (new), `tests/test_singleton_reset.py` (new), `tests/test_repository_registry_commits.py` (fix) | flock contract, extended singleton reset contract, commit-round-trip via `compute_repo_id` | `pytest -q tests/test_registry_concurrency.py tests/test_singleton_reset.py tests/test_repository_registry_commits.py` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/storage/repository_registry.py` | IF-0-P17-1 | `pytest -q tests/test_registry_concurrency.py` |
| SL-1.3 | impl | SL-1.1 | `mcp_server/cli/bootstrap.py` | extended reset + wiring | `pytest -q tests/test_singleton_reset.py` |
| SL-1.4 | impl | SL-1.1 | `tests/test_repository_registry_commits.py` | helper uses real persisted id | `pytest -q tests/test_repository_registry_commits.py` |
| SL-1.5 | verify | SL-1.2, SL-1.3, SL-1.4 | lane-owned | all SL-1 tests + import smoke | `pytest -q tests/test_registry_concurrency.py tests/test_singleton_reset.py tests/test_repository_registry_commits.py` |

**Test outline for SL-1.1**:
- `test_registry_concurrency.py`:
  1. `test_save_is_flocked` — subprocess-spawn two workers that both call `RepositoryRegistry.save()` on the same `tmp_path` registry 50× each with distinct `repo_id` insertions; after both exit, load the file, assert all 100 entries present (no lost writes). Uses `multiprocessing.Process`, not threads, to exercise cross-process flock.
  2. `test_save_holds_lock_during_rename` — monkeypatch `Path.replace` to sleep 50 ms; spawn two processes; measure wall time of the loser — must exceed the 50 ms window (proves exclusivity). Upper-bound assert: total runtime < 5 s (safety).
  3. `test_save_releases_lock_on_exception` — monkeypatch `json.dumps` to raise once; call `save()`; catch; call `save()` again without intervention; assert the second call succeeds (lock was released in `finally`).
  4. `test_lock_file_mode_0o600` — stat the sidecar `.lock` file; assert mode is `0o600` (no world/group read).
- `test_singleton_reset.py`:
  1. `test_reset_nulls_extended_singletons` — parametrized over `[("mcp_server.storage.multi_repo_manager", "_manager_instance"), ("mcp_server.dispatcher.cross_repo_coordinator", "_coordinator_instance"), ("mcp_server.plugins.repository_plugin_loader", "_loader_instance")]`. Set each to sentinel object; call `reset_process_singletons()`; assert each is `None`.
  2. `test_initialize_stateless_services_calls_reset` — set each of the nine singleton attrs (6 P16 + 3 new) to a sentinel; call `initialize_stateless_services(registry_path=tmp_path/"r.json")`; assert all nine were nulled before the function returned its 5-tuple. (Proves the call-at-top wiring exists and runs before any singleton construction.)
  3. `test_initialize_stateless_services_idempotent_under_repeat_init` — call `initialize_stateless_services()` twice in the same process; assert the two returned `RepositoryRegistry` instances are distinct (`is not`) — proves no cached pre-P17 state survives.
- `test_repository_registry_commits.py` fix:
  - Change `_create_registry_with_repo` to return `compute_repo_id(repo_path).repo_id` (the persisted key) alongside `repo_info`, or use `registry.register_repository(str(repo_path))` which handles id derivation. Update the two failing assertions to read-back via the real persisted id. Remove reliance on `repository_id=f"{repo_name}_id"` round-trip — that contract never existed.

**SL-1 impl notes**:
- `repository_registry.py` flock pattern: import `fcntl` at module top; wrap the existing `_save_locked` body (under `self._lock`) with an outer block that opens/creates `self.registry_path.with_suffix(".lock")` and `fcntl.flock(fd, fcntl.LOCK_EX)` before the in-process `RLock`. Release order: in-process lock first, flock second, in `finally` clauses. Do not close the lock fd across process lifetime — open on each `save()`, close after.
- `bootstrap.py::reset_process_singletons()` — append three new `try: import ...; setattr(_m, "_attr", None); except ImportError: pass` blocks. Order does not matter. Preserve existing six blocks verbatim.
- `bootstrap.py::initialize_stateless_services()` — insert `reset_process_singletons()` as line 1 of the body (before `resolved_registry_path = ...`). Wiring via direct call, not via side-import.

---

### SL-2 — Watcher/indexing resilience

- **Scope**: Ref-poller detects detached HEAD, force-push, and branch-rename; each triggers `enqueue_full_rescan`. Sweeper exception emits WARNING + `mcp_watcher_sweep_errors_total` counter increment. Incremental indexer clears checkpoint on clean exit regardless of `errors` list. Dispatcher walker honors `MCP_MAX_FILE_SIZE_BYTES`.
- **Owned files**:
  - `mcp_server/watcher/ref_poller.py` (whole file)
  - `mcp_server/watcher/sweeper.py` (whole file)
  - `mcp_server/indexing/incremental_indexer.py` (line range :230-234 — the checkpoint-clear conditional only)
  - `mcp_server/indexing/checkpoint.py` (defensive ownership; spec lists it; no edits expected — `clear()` already exists)
  - `mcp_server/dispatcher/dispatcher_enhanced.py` (line range :1918-1928 only — the file-size guard insertion inside `index_directory`'s per-file filter block)
  - `mcp_server/storage/git_index_manager.py` (adds `enqueue_full_rescan` method only — append-only past existing methods; declared owner of that one new method body, not the whole file)
  - `mcp_server/metrics/prometheus_exporter.py` (append-only: one new module-level Counter `mcp_watcher_sweep_errors_total` at file end, after existing module-level counter block at :62-66)
  - `tests/test_ref_poller_edges.py` (new)
  - `tests/test_sweeper_observability.py` (new)
  - `tests/test_incremental_indexer_checkpoint.py` (new — checkpoint-clear regression test)
  - `tests/test_walker_file_size_guard.py` (new — file-size guard test)
- **Interfaces provided**: IF-0-P17-2 (`enqueue_full_rescan`). New counter `mcp_watcher_sweep_errors_total` (no labels).
- **Interfaces consumed**: `get_max_file_size_bytes` (IF-0-P16-2); `checkpoint.clear()` at `indexing/checkpoint.py:63`; `sync_repository_index` at `git_index_manager.py` (underlying primitive that `enqueue_full_rescan` also drives); `prometheus_exporter.Counter` pattern at `:62-66`.
- **Parallel-safe**: yes. No file overlap with SL-1, SL-3, or SL-4 outside the declared shared files (`prometheus_exporter.py`, `dispatcher_enhanced.py`) — both handled as line-range / append-only single-writer (see Execution Notes).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | 4 new test files listed above | 3 ref-poller edges, sweeper observability, checkpoint clear, file-size guard | `pytest -q tests/test_ref_poller_edges.py tests/test_sweeper_observability.py tests/test_incremental_indexer_checkpoint.py tests/test_walker_file_size_guard.py` |
| SL-2.2 | impl | SL-2.1 | `git_index_manager.py`, `ref_poller.py` | IF-0-P17-2 + ref-poller edges | `pytest -q tests/test_ref_poller_edges.py` |
| SL-2.3 | impl | SL-2.1 | `sweeper.py`, `prometheus_exporter.py` (new counter only) | sweeper WARN + counter | `pytest -q tests/test_sweeper_observability.py` |
| SL-2.4 | impl | SL-2.1 | `incremental_indexer.py` (line range :230-234) | checkpoint always clears | `pytest -q tests/test_incremental_indexer_checkpoint.py` |
| SL-2.5 | impl | SL-2.1 | `dispatcher_enhanced.py` (line range :1918-1928) | file-size guard | `pytest -q tests/test_walker_file_size_guard.py` |
| SL-2.6 | verify | SL-2.2, SL-2.3, SL-2.4, SL-2.5 | lane-owned | all SL-2 tests | `pytest -q tests/test_ref_poller_edges.py tests/test_sweeper_observability.py tests/test_incremental_indexer_checkpoint.py tests/test_walker_file_size_guard.py` |

**SL-2 impl notes**:
- `ref_poller.py::_poll_one`: extend beyond today's SHA-compare. Track per-repo last-seen branch name and whether HEAD is symbolic. Detect:
  - **detached HEAD**: `_read_ref()` returns `None` for the tracked branch → if previous state was attached, fire `enqueue_full_rescan`. (Record the prior state on the `RepositoryInfo` `last_branch_state` field or equivalent — if no such field exists, carry it in a module-level `dict[str, Literal["attached","detached"]]` keyed by repo_id. Prefer the existing `RepositoryInfo` if it has a writable slot; otherwise module-level dict is acceptable since ref-poller is single-threaded per poll loop iteration.)
  - **force-push**: current tip SHA differs from `last_indexed_commit`, AND the new tip is not an ancestor of the old tip. Use `git merge-base --is-ancestor <old> <new>` via `subprocess.run(check=False)`; nonzero = not an ancestor = force-push (or branch-rewound). Fire `enqueue_full_rescan` instead of `sync_repository_index`.
  - **branch-rename**: `repo_info.tracked_branch` unchanged, but `refs/heads/<tracked_branch>` no longer exists AND another ref matches the old tip. Simplest form: if `_read_ref(tracked_branch)` returns `None` but a `_read_ref(fallback_branches)` hit finds the commit we were tracking, fire `enqueue_full_rescan`. (Fallback list: `main`, `master`, `HEAD`.) If no fallback matches, fire `enqueue_full_rescan` anyway — branch has genuinely disappeared.
- `sweeper.py::_loop`: replace the `except Exception: pass` at `:78` with `except Exception as e: logger.warning("watcher sweep error: %s", e); mcp_watcher_sweep_errors_total.inc()`. Import `logging`, add `logger = logging.getLogger(__name__)` at module top, and `from mcp_server.metrics.prometheus_exporter import mcp_watcher_sweep_errors_total`.
- `prometheus_exporter.py`: append after the existing module-level block (after `:66`):
  ```python
  mcp_watcher_sweep_errors_total = Counter(
      "mcp_watcher_sweep_errors_total",
      "Count of watcher sweep iterations that raised an exception.",
  )
  ```
  No labels. Registered on default registry (same pattern as `mcp_tool_calls_total`).
- `incremental_indexer.py:230-234`: change `if not errors: _clear_ckpt(self.repo_path)` to `_clear_ckpt(self.repo_path)` (unconditional on clean-exit code path). Keep the `errors` list for reporting; just don't gate checkpoint-clear on it. Add a short comment: `# Always clear on clean loop exit; errors list is for reporting, not state resumption.`
- `dispatcher_enhanced.py::index_directory` lines 1918-1928: after `if is_excluded(path): continue`, insert:
  ```python
  try:
      size = path.stat().st_size
  except OSError:
      continue
  if size > get_max_file_size_bytes():
      logger.warning("skipping oversized file: %s (%d bytes)", path, size)
      stats["ignored_files"] = stats.get("ignored_files", 0) + 1
      continue
  ```
  Add `from mcp_server.config.env_vars import get_max_file_size_bytes` to imports block if not already present. No change to the walker's closure or surrounding `os.walk` call.
- `git_index_manager.py::enqueue_full_rescan`: new method, append-only past existing methods. Body: mark `RepositoryInfo.last_indexed_commit = None` via the registry's mutator (forces the next `sync_repository_index` to do a full re-index), call `self.sync_repository_index(repo_id)`. Idempotent — re-calling before the first finishes is safe because `sync_repository_index` is already idempotent per P12.

---

### SL-3 — Disk & schema safety

- **Scope**: SQLite `ENOSPC` on commit → store enters read-only mode + emits counter; reads continue. `SchemaMigrator.migrate_artifact` writes timestamped backup of `extracted_dir` before migration loop; rollback-on-`SchemaMigrationError` restores. Delete duplicate `SchemaMigrationError` at `schema_migrator.py:16`; import canonical one from `core.errors`.
- **Owned files**:
  - `mcp_server/storage/sqlite_store.py` (ENOSPC handling + `_readonly` state)
  - `mcp_server/storage/schema_migrator.py` (backup/rollback + duplicate-class removal + import swap)
  - `mcp_server/metrics/prometheus_exporter.py` (append-only: one new Counter `mcp_storage_readonly_total`, after SL-2's addition — single-writer block below pre-authorizes order)
  - `tests/test_disk_full.py` (new)
  - `tests/test_schema_migration_backup.py` (new)
- **Interfaces provided**: new counter `mcp_storage_readonly_total` (no labels). `SQLiteStore._readonly: bool` flag (internal but covered by tests).
- **Interfaces consumed**: `SchemaMigrationError` from `mcp_server.core.errors` (IF-0-P16-1).
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_disk_full.py`, `tests/test_schema_migration_backup.py` | ENOSPC→readonly+counter; backup+rollback | `pytest -q tests/test_disk_full.py tests/test_schema_migration_backup.py` |
| SL-3.2 | impl | SL-3.1 | `sqlite_store.py`, `prometheus_exporter.py` (new counter only) | ENOSPC path | `pytest -q tests/test_disk_full.py` |
| SL-3.3 | impl | SL-3.1 | `schema_migrator.py` | backup/rollback + import swap | `pytest -q tests/test_schema_migration_backup.py` |
| SL-3.4 | verify | SL-3.2, SL-3.3 | lane-owned | all SL-3 tests | `pytest -q tests/test_disk_full.py tests/test_schema_migration_backup.py` |

**SL-3 impl notes**:
- `sqlite_store.py:232-262`: wrap both commit-path `except Exception` blocks (pool path + non-pool path) with a tighter `except sqlite3.OperationalError as e` first-branch that inspects `str(e)` for `"disk I/O error"` or `"database or disk is full"` (SQLite's wording for ENOSPC) — if matched, set `self._readonly = True` via `__setattr__` on the store, call `mcp_storage_readonly_total.inc()`, rollback, and RE-RAISE as `DiskFullError(TransientArtifactError)` if that subclass exists (if not, raise `TransientArtifactError` directly). Do not suppress — callers must know the commit failed. Keep the outer `except Exception: rollback; raise` as fallback. Constructor adds `self._readonly = False` at `__init__:~85`. Writes (`.execute("INSERT"...)`) check the flag before acquiring a connection and raise `TransientArtifactError("store is read-only after ENOSPC")`.
- `schema_migrator.py`:
  - Delete lines 12-16 (`class UnknownSchemaVersionError` and duplicate `class SchemaMigrationError`). Add `from mcp_server.core.errors import SchemaMigrationError, UnknownSchemaVersionError` — note: `UnknownSchemaVersionError` also needs to be added to `core/errors.py`. **Scope adjustment**: `UnknownSchemaVersionError` addition belongs in `core/errors.py`, which is owned by P16. Since P16 is merged and P17 SL-3 needs one more class, this is an additive extension that SL-3 owns for this phase. Declare `core/errors.py` in SL-3 ownership for a single append: `class UnknownSchemaVersionError(ArtifactError): pass`. Document in Execution Notes as a P17 amendment to P16's frozen taxonomy.
  - `migrate_artifact` body (`:30-83`): before the migration loop at `:66`, create `backup_dir = extracted_dir.parent / f"{extracted_dir.name}.backup.{int(time.time())}"` and `shutil.copytree(extracted_dir, backup_dir)`. Wrap the loop in `try/except SchemaMigrationError: shutil.rmtree(extracted_dir, ignore_errors=True); shutil.move(backup_dir, extracted_dir); raise`. On success (post-loop), `shutil.rmtree(backup_dir)`. `time.time()` granular to seconds is sufficient — tests use `freezegun` or accept wall-clock variance.
- `prometheus_exporter.py`: append after SL-2's `mcp_watcher_sweep_errors_total` block:
  ```python
  mcp_storage_readonly_total = Counter(
      "mcp_storage_readonly_total",
      "Count of SQLite stores that transitioned to read-only mode due to ENOSPC.",
  )
  ```

**Test outline for SL-3.1**:
- `test_disk_full.py`:
  1. `test_commit_enospc_sets_readonly` — use `unittest.mock.patch` to make `conn.commit()` raise `sqlite3.OperationalError("database or disk is full")` once; assert the store's `_readonly` is True post-call; assert `mcp_storage_readonly_total._value.get() == 1` via Prometheus introspection (see prometheus_client internals).
  2. `test_reads_work_after_readonly` — set `_readonly = True`; call a read method (pick an existing one like `.query_symbols()` or whatever the minimal read surface is in `sqlite_store.py`); assert it returns normally.
  3. `test_writes_raise_after_readonly` — set `_readonly = True`; call a write method; assert `TransientArtifactError` is raised.
- `test_schema_migration_backup.py`:
  1. `test_backup_created_before_migration` — set up a small `extracted_dir` with 1-2 files; invoke `migrate_artifact(extracted_dir, from_version="1", to_version="2")` (where 1→2 is a real migration pair in `_MIGRATIONS` registry, or monkeypatched); assert during the migration the `.backup.<ts>` dir exists; after success the `.backup.<ts>` dir is removed.
  2. `test_rollback_restores_on_schema_error` — register a monkeypatched migration step that mutates `extracted_dir` then raises `SchemaMigrationError`; invoke `migrate_artifact`; catch the error; assert `extracted_dir` contents are identical to the pre-call state (restored from backup).
  3. `test_canonical_error_class` — assert `from mcp_server.storage.schema_migrator import SchemaMigrationError; from mcp_server.core.errors import SchemaMigrationError as Canonical; assert SchemaMigrationError is Canonical` — pins that the duplicate has been removed.

---

### SL-4 — Carry-over debt

- **Scope**: Add `_get_target_repositories` method to `CrossRepositorySearchCoordinator` (the real SL-4 root cause per Explore). Add `RerankerFactory.create_default()` classmethod returning `TFIDFReranker({})`. Remove 4 `F401` unused imports in `dispatcher/`. Burn down the remaining carry-over test failures (target: 46 → ≤5) — residuals enumerated by SL-docs.2 from a fresh run.
- **Owned files**:
  - `mcp_server/dispatcher/cross_repo_coordinator.py` (append `_get_target_repositories` method to `CrossRepositorySearchCoordinator` — declared single-writer with any other lane that touches this file; no other lane does)
  - `mcp_server/indexer/reranker.py` (append `create_default()` classmethod to `RerankerFactory` at `:761`; no other lane touches)
  - `mcp_server/dispatcher/dispatcher_enhanced.py` (import-block only — lines 17, 32, 35; SL-2 owns line 1918-1928 body of `index_directory` — disjoint line ranges, see Execution Notes)
  - `mcp_server/dispatcher/simple_dispatcher.py` (line 11 only — single `F401` removal)
  - `tests/test_cross_repo_coordinator.py` (may need follow-up tweaks if `_get_target_repositories` returns a different shape than the tests currently assert; preserve the test intent)
  - `tests/test_reranker_factory_default.py` (new — pins IF against regression)
- **Interfaces provided**: `CrossRepositorySearchCoordinator._get_target_repositories(scope) -> list[str]`. `RerankerFactory.create_default() -> TFIDFReranker`.
- **Interfaces consumed**: `TFIDFReranker` at `mcp_server/indexer/reranker.py` (same module — zero new import). `SearchScope` enum (existing).
- **Parallel-safe**: yes (single-writer declaration on `dispatcher_enhanced.py`).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_reranker_factory_default.py` (new); extend `test_cross_repo_coordinator.py` expectations if needed | `_get_target_repositories` + `create_default` + F401 baseline | `pytest -q tests/test_reranker_factory_default.py tests/test_cross_repo_coordinator.py` |
| SL-4.2 | impl | SL-4.1 | `dispatcher/cross_repo_coordinator.py` | `_get_target_repositories` | `pytest -q tests/test_cross_repo_coordinator.py` |
| SL-4.3 | impl | SL-4.1 | `indexer/reranker.py` | `RerankerFactory.create_default` | `pytest -q tests/test_reranker_factory_default.py` |
| SL-4.4 | impl | SL-4.1 | `dispatcher_enhanced.py` (imports only), `simple_dispatcher.py` | ruff F401 | `ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher` |
| SL-4.5 | verify | SL-4.2, SL-4.3, SL-4.4 | lane-owned | all SL-4 tests + ruff | `pytest -q tests/test_cross_repo_coordinator.py tests/test_reranker_factory_default.py && ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher` |

**SL-4 impl notes**:
- `cross_repo_coordinator.py::_get_target_repositories`: the tests call `coordinator._get_target_repositories(scope)` where `scope` is a `SearchScope` enum. Implementation: for `SearchScope.ALL` → return `list(self._multi_repo_manager.list_repositories())` repo_ids; for `SearchScope.PRIMARY_ONLY` → return `[self._multi_repo_manager.get_primary_repo().repository_id]`; for `SearchScope.DEPENDENCIES` → call `_get_repository_dependencies(primary_id)` (already exists per IF-0-P14-2). Return type `list[str]` (repo_ids). Keep the method private (leading underscore) per test call-site convention. Exact enum variants validated by reading `SearchScope` definition in SL-4.2.
- `reranker.py::RerankerFactory.create_default`: classmethod `@classmethod def create_default(cls) -> TFIDFReranker: return TFIDFReranker({})`. Zero external deps per Explore finding. `TFIDFReranker` is in same module.
- F401 cleanup: simple `ruff check --fix` on the four offenders. If any offender is referenced via `__all__` or re-exported, keep the import and add it to `__all__`. Otherwise delete the import line.

---

### SL-docs — Documentation & spec reconciliation

- **Scope**: Multi-instance runbook, enumerate residual carry-over test failures after SL-1..SL-4 merge, ARCHITECTURE concurrency addendum, env-var doc extension for `MCP_MAX_FILE_SIZE_BYTES` usage, CHANGELOG, spec amendments. Terminal; mandatory.
- **Owned files** (catalog is authoritative; minimum set below):
  - `.claude/docs-catalog.json` if present (skip rescan — `scaffold_docs_catalog.py` absent per P16 handoff)
  - `docs/operations/multi-instance.md` (new — file-locking protocol, singleton reset semantics, DR/recovery procedure)
  - `docs/operations/known-test-debt.md` (new — enumerate residuals from fresh test run; count must be ≤5 per exit criterion)
  - `docs/configuration/ENVIRONMENT-VARIABLES.md` — extend P16 reserved section: note that `MCP_MAX_FILE_SIZE_BYTES` is now enforced in dispatcher walker (state change: reserved → enforced)
  - `ARCHITECTURE.md` — concurrency addendum: flock protocol, multi-instance safety boundary, ref-poller edge-case semantics, singleton-reset rule
  - `CHANGELOG.md` — Unreleased entry for P17
  - `specs/phase-plans-v1.md` — `### Post-execution amendments` subsection under P17 section IF any IF-0-P17-* signature drifted; record the `UnknownSchemaVersionError` → `core/errors.py` amendment (P16 taxonomy extension)
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-1, SL-2, SL-3, SL-4
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | Skip rescan — helper script absent in this repo. Record rationale in commit. Precedent: P14/P15/P16 SL-docs. |
| SL-docs.2 | docs | SL-docs.1 | `docs/operations/known-test-debt.md`, `docs/operations/multi-instance.md`, `ARCHITECTURE.md` | Run `pytest -q --no-header --tb=no 2>&1 \| tail -20` after merge; enumerate residuals in known-test-debt.md (assert ≤5). Author multi-instance.md (flock semantics, singleton reset, DR). Append concurrency section to ARCHITECTURE.md. |
| SL-docs.3 | docs | SL-docs.2 | `CHANGELOG.md`, `docs/configuration/ENVIRONMENT-VARIABLES.md` | Unreleased P17 entry. Update MCP_MAX_FILE_SIZE_BYTES status (reserved → enforced in walker). |
| SL-docs.4 | docs | SL-docs.3 | `specs/phase-plans-v1.md` | Append `### Post-execution amendments` to P17 section: (a) `UnknownSchemaVersionError` promoted to `core/errors.py`; (b) `SchemaMigrator.apply(db_path)` signature was never shipped — `migrate_artifact(extracted_dir)` was the real surface (name clarified); (c) any IF-0-P17-* drift observed during impl. |
| SL-docs.5 | verify | SL-docs.4 | — | Repo has no markdownlint/vale/prettier-check per P16 precedent; no-op. Confirm on first run. |

## Execution Notes

- **Single-writer files**:
  - `mcp_server/metrics/prometheus_exporter.py` — SL-2 appends `mcp_watcher_sweep_errors_total` Counter; SL-3 appends `mcp_storage_readonly_total` Counter. Both additions are append-only at file end, after the existing module-level block at `:62-66`. No order dependency; merge conflicts (if any at merge time) resolve by concatenating both blocks — two disjoint Counter declarations. If execute-phase sees an add/add conflict here, accept both hunks.
  - `mcp_server/dispatcher/dispatcher_enhanced.py` — SL-2 owns line-range `:1918-1928` (file-size guard inside `index_directory`'s per-file filter); SL-4 owns `:17, :32, :35` (F401 import removal). Disjoint line ranges; separate hunks. If SL-4 adds a new import for a symbol referenced by SL-2's guard, merge alphabetically — precedent from P14/P15 lane merges.
  - `mcp_server/core/errors.py` — SL-3 appends `class UnknownSchemaVersionError(ArtifactError): pass` at file end. This is an extension of P16's frozen taxonomy; no other P17 lane touches `core/errors.py`. P16 is merged so no cross-phase collision.
- **Known destructive changes**:
  - `schema_migrator.py` — SL-3 deletes the duplicate `class SchemaMigrationError(ArtifactError)` (file-local, lines 14-16) and the adjacent `class UnknownSchemaVersionError` (lines 10-12). Both are replaced by imports from `core.errors`. Declared legitimate; whitelist for execute-phase's pre-merge check.
  - `incremental_indexer.py:230-234` — SL-2 removes the `if not errors:` conditional gate around `_clear_ckpt`. Two lines of existing logic removed.
  - No other deletions. Every other touch is additive.
- **Expected add/add conflicts**: none — no SL-0 preamble in this phase. P16 was the preamble; it's merged.
- **SL-0 re-exports**: n/a — no SL-0 lane.
- **Worktree naming**: execute-phase allocates via `scripts/allocate_worktree_name.sh`. No plan-specified worktree paths.
- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-`548963d` (P16 tip sha, merged before P17 dispatch), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. Since all four P17 impl lanes are DAG roots (zero cross-lane dependencies), stale-base risk applies only to SL-docs consuming pre-SL-N merges.
- **Architectural choices** (baseline, no `--consensus` requested):
  - Flock at process boundary (file-locking via `fcntl.flock`) chosen over distributed coordination (etcd/Redis) per spec Non-goals. flock is the minimum-viable lock for the documented threat (two instances on the same host writing the same registry).
  - `enqueue_full_rescan` added as new method on `GitAwareIndexManager` (not as a flag on `sync_repository_index`) so observability + tests can distinguish full-rescan events from incremental-syncs. Promoted to IF-0-P17-2 since P18 SL-4 observability counters will key on it — freezing now prevents rename drift.
  - Schema backup adapted to `extracted_dir` (not a DB file) — the P14 promise of `apply(db_path)` was never kept; working against the real `migrate_artifact(extracted_dir)` signature keeps P17 scope wiring-only vs. inventing a new live-DB migration surface.
  - `UnknownSchemaVersionError` added to `core/errors.py` (extending P16 taxonomy) rather than kept in `schema_migrator.py` — consistency: both migration-family errors should live in the canonical taxonomy. Documented in SL-docs.4 amendment to P17 section of spec.
- **Repo-specific gotchas** (carried from P16 handoff):
  - Coverage threshold noise: use targeted `pytest -q <path>` invocations, not plain `pytest` from repo root, when running narrow lane tests. Verify commands above follow this pattern.
  - `audit_lane_file_touches.py` requires SL-N lane IDs. `SL-docs` is non-numeric; expect the `"lane not found"` error — fall back to manual `git diff --name-only` against `Owned files` globs (P16 precedent).
  - `scaffold_docs_catalog.py` still absent; SL-docs.1 skips catalog rescan (P14/P15/P16 precedent).
  - `scripts/validate_plan_doc.py` is also absent in this repo — Step 7 validator in plan-phase SKILL points to a path that doesn't exist. Plan-phase main-thread check of structural invariants (disjoint ownership, DAG acyclicity, test-before-impl, grep-paired-with-tests) is performed inline above; skip the external validator.
  - `TeamCreate` switches the active task list: defer all per-lane `TaskCreate` calls to AFTER the execute-phase team is created. Plan doc's `## Lane Index` is the source of truth in the meantime.

## Acceptance Criteria

- [ ] **IF-0-P17-1 flock contract**: `pytest -q tests/test_registry_concurrency.py` reports 0 failures, ≥4 tests passing. *(Paired with shape grep: `grep -n "fcntl.flock" mcp_server/storage/repository_registry.py` returns ≥1 match.)*
- [ ] **IF-0-P17-2 enqueue_full_rescan**: `python -c "from mcp_server.storage.git_index_manager import GitAwareIndexManager; import inspect; assert 'enqueue_full_rescan' in dir(GitAwareIndexManager); sig = inspect.signature(GitAwareIndexManager.enqueue_full_rescan); assert list(sig.parameters)[1] == 'repo_id'"` exits 0. *(Paired with `test_ref_poller_edges.py` firing this method on all three edge cases.)*
- [ ] **Extended singleton reset**: `pytest -q tests/test_singleton_reset.py` reports 0 failures. `python -c "from mcp_server.cli.bootstrap import reset_process_singletons; import inspect; src = inspect.getsource(reset_process_singletons); assert all(s in src for s in ('multi_repo_manager', 'cross_repo_coordinator', 'repository_plugin_loader'))"` exits 0.
- [ ] **initialize_stateless_services wiring**: `python -c "from mcp_server.cli.bootstrap import initialize_stateless_services; import inspect; src = inspect.getsource(initialize_stateless_services); body = src.split(':', 1)[1].lstrip(); assert 'reset_process_singletons()' in body.split('\n')[0:5]"` exits 0 (reset is called in first 5 body lines). *(Paired with `test_initialize_stateless_services_calls_reset`.)*
- [ ] **test_repository_registry_commits.py passes**: `pytest -q tests/test_repository_registry_commits.py` reports 0 failures.
- [ ] **Ref-poller edges**: `pytest -q tests/test_ref_poller_edges.py` reports 0 failures, exactly 3 test functions (detached-HEAD, force-push, branch-rename).
- [ ] **Sweeper observability**: `pytest -q tests/test_sweeper_observability.py` reports 0 failures. *(Paired with source grep: `grep -n "mcp_watcher_sweep_errors_total" mcp_server/watcher/sweeper.py mcp_server/metrics/prometheus_exporter.py` returns ≥2 matches.)*
- [ ] **Checkpoint clears with errors**: `pytest -q tests/test_incremental_indexer_checkpoint.py` reports 0 failures. Regression guard: `grep -nE "if not errors:" mcp_server/indexing/incremental_indexer.py` returns 0 matches (the deleted conditional).
- [ ] **File-size guard**: `pytest -q tests/test_walker_file_size_guard.py` reports 0 failures. *(Paired with: `grep -n "get_max_file_size_bytes" mcp_server/dispatcher/dispatcher_enhanced.py` returns ≥1 match.)*
- [ ] **ENOSPC → readonly**: `pytest -q tests/test_disk_full.py` reports 0 failures, ≥3 tests passing.
- [ ] **Schema migration backup/rollback**: `pytest -q tests/test_schema_migration_backup.py` reports 0 failures, ≥3 tests passing.
- [ ] **SchemaMigrationError de-duplication**: `python -c "from mcp_server.storage.schema_migrator import SchemaMigrationError as A; from mcp_server.core.errors import SchemaMigrationError as B; assert A is B"` exits 0.
- [ ] **CrossRepositorySearchCoordinator fix**: `pytest -q tests/test_cross_repo_coordinator.py` reports 0 failures OR regression baseline reduced by ≥17 failures (from 18 to ≤1).
- [ ] **RerankerFactory.create_default**: `python -c "from mcp_server.indexer.reranker import RerankerFactory; r = RerankerFactory.create_default(); assert hasattr(r, 'rerank')"` exits 0. *(Paired with `test_reranker_factory_default.py`.)*
- [ ] **ruff F401**: `ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher` reports 0 errors.
- [ ] **Carry-over burn-down**: `pytest -q 2>&1 | tail -1` shows failure count ≤5 (down from 46). Residuals enumerated in `docs/operations/known-test-debt.md`.
- [ ] **Repo-wide collection healthy**: `pytest --collect-only -q` exits 0.
- [ ] **SL-docs lane ran**: `docs/operations/multi-instance.md` exists; `docs/operations/known-test-debt.md` exists; `ARCHITECTURE.md` contains "concurrency" section mentioning flock.

## Verification

End-to-end commands to run after all five lanes merge:

```bash
# IF gates
pytest -q tests/test_registry_concurrency.py tests/test_singleton_reset.py tests/test_repository_registry_commits.py
pytest -q tests/test_ref_poller_edges.py tests/test_sweeper_observability.py tests/test_incremental_indexer_checkpoint.py tests/test_walker_file_size_guard.py
pytest -q tests/test_disk_full.py tests/test_schema_migration_backup.py
pytest -q tests/test_cross_repo_coordinator.py tests/test_reranker_factory_default.py

# Shape gates (grep paired with tests above)
grep -n "fcntl.flock" mcp_server/storage/repository_registry.py
python -c "from mcp_server.storage.schema_migrator import SchemaMigrationError as A; from mcp_server.core.errors import SchemaMigrationError as B; assert A is B; print('ok')"
python -c "from mcp_server.storage.git_index_manager import GitAwareIndexManager; assert hasattr(GitAwareIndexManager, 'enqueue_full_rescan'); print('ok')"
python -c "from mcp_server.indexer.reranker import RerankerFactory; r = RerankerFactory.create_default(); assert hasattr(r, 'rerank'); print('ok')"

# Anti-regression grep (paired with test_incremental_indexer_checkpoint.py)
! grep -nE "^[[:space:]]*if not errors:" mcp_server/indexing/incremental_indexer.py

# Hygiene gates
ruff check --select F401 mcp_server/dispatcher mcp_server/storage mcp_server/watcher

# Carry-over burn-down gate
pytest -q 2>&1 | tail -5    # total failure count must be ≤5

# Repo-wide collect
pytest --collect-only -q

# Smoke: initialize_stateless_services runs and returns the 5-tuple
python -c "from mcp_server.cli.bootstrap import initialize_stateless_services; t = initialize_stateless_services(); assert len(t) == 5; print('ok')"
```

All 12 commands must exit 0 (modulo the `tail -5` which is informational) before the phase is ready to ship.
