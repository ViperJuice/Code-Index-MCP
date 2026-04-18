# PHASE-2A-data-model-store-registry: Phase 2A — Data Model & Store Registry

> **How to use this document**: this is the P2A lane plan produced by `/plan-phase P2A`. On approval, save it to `plans/phase-plan-v1-p2a.md` in the repo and emit one `TaskCreate` per lane (SL-1 / SL-2 / SL-3). Then run `/execute-phase p2a`.

## Context

Phase 1 established worktree-aware repo identity (`compute_repo_id` + `RepoIdentity`), pinned `tracked_branch` on `RepositoryInfo`, killed the branch-change reindex behavior, and unified walker gitignore handling. Eight commits merged; all five acceptance criteria green; 77 tests passing. The blockers for the next structural step are now cleanly specified: **P2B needs `RepoContext` / `StoreRegistry` / `RepoResolver` to exist and be tested before it can rip out the dispatcher's single-repo cwd binding.**

Exploration surfaced three material simplifications vs the original spec sketch:

1. **No cross-class connection-cache duplication.** Only `MultiRepositoryManager._connections` (`multi_repo_manager.py:121`) caches `Dict[str, SQLiteStore]`. Both `CrossRepositorySearchCoordinator` (`storage/cross_repo_coordinator.py:79`) and `CrossRepositoryCoordinator` (`dispatcher/cross_repo_coordinator.py:91`) already compose `MultiRepositoryManager` and delegate connection access. The consolidation is a one-class refactor, not three.
2. **Dispatcher is not a current `RepositoryInfo` consumer.** `EnhancedDispatcher` holds `self._sqlite_store` directly; it doesn't read `RepositoryInfo` fields. That means P2A ships new types without touching the dispatcher — P2B owns the wire-up.
3. **Resolver has pre-existing helpers.** `RepositoryRegistry.find_by_path(path) -> Optional[repo_id]` at `repository_registry.py:665–688` gives a fast-path for the common case. Walk-up-to-`.git` logic exists inline inside `PathUtils.get_workspace_root` at `path_utils.py:39–61`; the resolver can reimplement the ~10-line loop locally to keep file ownership disjoint. `MultiRepositoryManager.resolve_repo_id` at `multi_repo_manager.py:239–264` already classifies input (hex-id / URL / path) and delegates to `compute_repo_id`.

Key reusable primitives from P1: `mcp_server/storage/repo_identity.py::compute_repo_id(path) -> RepoIdentity`, `mcp_server/storage/repo_identity.py::resolve_tracked_branch`, `mcp_server/storage/multi_repo_manager.py::RepositoryInfo` (25-field `@dataclass`, mutable) with `tracked_branch` + `git_common_dir` fields.

Exploration test-gap: there's no concurrent `_get_connection` test today. SL-2 fills this.

## Interface Freeze Gates
- [ ] **IF-0-P2A-1** — `RepoContext` dataclass in `mcp_server/core/repo_context.py`:
  ```python
  @dataclass(frozen=True)
  class RepoContext:
      repo_id: str                           # canonical 16-hex sha256 from compute_repo_id
      sqlite_store: SQLiteStore              # hydrated from StoreRegistry (non-Optional)
      workspace_root: Path                   # the path the caller resolved this from (pre-walk-up)
      tracked_branch: str                    # pinned default branch from RepositoryInfo
      registry_entry: RepositoryInfo         # live mutable registry record; frozen outer dataclass holds this reference for read-through access to priority/current_commit/etc.
  ```
  The outer dataclass is frozen; `registry_entry` is a *reference* to live mutable registry state, not a snapshot. Docstring must call out the asymmetry. `sqlite_store` is not Optional — tests wanting a store-less context use a stub, not None.

- [ ] **IF-0-P2A-2** — `StoreRegistry` public API in `mcp_server/storage/store_registry.py`:
  ```python
  class StoreRegistry:
      @classmethod
      def for_registry(cls, registry: RepositoryRegistry) -> "StoreRegistry": ...

      def get(self, repo_id: str) -> SQLiteStore:
          """Idempotent: same instance returned for repeated calls. Thread-safe.
          Resolves index_path from the RepositoryRegistry. Raises KeyError if repo_id is not registered."""

      def close(self, repo_id: str) -> None:
          """Close and evict the cached store for repo_id. No-op if not cached.
          Called by the watcher-unregister path (P4) and by test teardown."""

      def shutdown(self) -> None:
          """Close all cached stores and clear the cache."""
  ```
  Cache is a `Dict[str, SQLiteStore]` guarded by an explicit `threading.Lock`. SQLite WAL provides per-connection safety, but the dict itself needs the lock. `for_registry` is the sole public constructor; `__init__` is treated as private.

## Lane Index & Dependencies

```
SL-1 — RepoContext dataclass
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-2 — StoreRegistry + MultiRepositoryManager delegation
  Depends on: (none)
  Blocks: SL-3
  Parallel-safe: yes

SL-3 — RepoResolver (fan-in)
  Depends on: SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no (consumes both frozen interfaces)
```

## Lanes

### SL-1 — RepoContext dataclass

- **Scope**: Define frozen `RepoContext` dataclass in `mcp_server/core/repo_context.py` per IF-0-P2A-1 + unit tests covering construction, field access, mutation of the referenced `registry_entry` through a frozen outer, and `dataclasses.replace()` semantics.
- **Owned files**: `mcp_server/core/repo_context.py` (NEW), `tests/test_repo_context.py` (NEW)
- **Interfaces provided**: IF-0-P2A-1
- **Interfaces consumed**: none (type hints from `SQLiteStore`, `Path`, `RepositoryInfo` are pre-existing)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_repo_context.py` | field-set, frozen-outer assertion (`dataclasses.replace` works; direct attribute set raises `FrozenInstanceError`), mutation-through-reference (modifying `ctx.registry_entry.priority` is visible to another reference holder), store non-Optional (constructing with `sqlite_store=None` is a type error that the test intentionally bypasses with `# type: ignore` to prove runtime permits it but the contract doesn't), `replace()` of `repo_id` yields a new instance with the rest untouched | `pytest tests/test_repo_context.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/core/repo_context.py` | — | — |
| SL-1.3 | verify | SL-1.2 | owned files | all SL-1 tests | `pytest tests/test_repo_context.py -v` |

### SL-2 — StoreRegistry + MultiRepositoryManager delegation

- **Scope**: Create `mcp_server/storage/store_registry.py` with the IF-0-P2A-2 public API. Refactor `MultiRepositoryManager` to hold a `StoreRegistry` instance and delegate `_connections` / `_get_connection` / `close` / `unregister_repository`'s connection-cache operations to it. Public search / register APIs of `MultiRepositoryManager` are untouched. The two `cross_repo_coordinator` classes already delegate via composition; they need no changes for P2A.
- **Owned files**: `mcp_server/storage/store_registry.py` (NEW), `mcp_server/storage/multi_repo_manager.py` (EDIT — method-level changes to `_connections` init, `_get_connection` body, `close` body, `unregister_repository` cache-eviction lines only; diff-size cap: <80 lines changed to prevent scope creep into public search methods), `tests/test_store_registry.py` (NEW)
- **Interfaces provided**: IF-0-P2A-2
- **Interfaces consumed**: none from P2A. Uses pre-existing `RepositoryRegistry.get(repo_id) -> Optional[RepositoryInfo]` at `repository_registry.py:354–369` to resolve `index_path` for cache-miss construction.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_store_registry.py` | idempotency (`get(rid)` returns same instance twice), `close(rid)` evicts (subsequent `get` returns a fresh instance), `shutdown()` clears all, `KeyError` on unknown repo_id, **concurrent `get()` from 8 threads yields a single shared instance with no `sqlite3.OperationalError: database is locked`** (uses `concurrent.futures.ThreadPoolExecutor` against a tmp registry + tmp SQLite), `for_registry` is the only documented constructor, `MultiRepositoryManager.search_symbol` still works end-to-end after delegation refactor (pre/post integration check) | `pytest tests/test_store_registry.py tests/test_multi_repo_manager.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/storage/store_registry.py`, `mcp_server/storage/multi_repo_manager.py` (delegation hooks only) | — | — |
| SL-2.3 | verify | SL-2.2 | owned files | all SL-2 tests + multi_repo_manager existing tests unaffected | `pytest tests/test_store_registry.py tests/test_multi_repo_manager.py -v` |

### SL-3 — RepoResolver (fan-in)

- **Scope**: Create `mcp_server/core/repo_resolver.py` with `RepoResolver(registry, store_registry).resolve(path) -> Optional[RepoContext]`. Walks up from `path` to find the nearest `.git` (file or dir), uses `RepositoryRegistry.find_by_path` as the fast-path, falls back to `compute_repo_id(git_root).repo_id` + `registry.get(repo_id)` when `find_by_path` misses. Returns `None` for paths outside the registry (no auto-register).
- **Owned files**: `mcp_server/core/repo_resolver.py` (NEW), `tests/test_repo_resolver.py` (NEW)
- **Interfaces provided**: `RepoResolver.resolve` (consumer-facing; not an IF-0 gate because P2B is the only consumer and we don't need to freeze for downstream phases beyond P2B)
- **Interfaces consumed**:
  - **IF-0-P2A-1** (`RepoContext` dataclass) — from SL-1
  - **IF-0-P2A-2** (`StoreRegistry.get`) — from SL-2
  - Pre-existing: `compute_repo_id` (`mcp_server/storage/repo_identity.py:~30` from P1), `RepositoryRegistry.find_by_path` (`mcp_server/storage/repository_registry.py:665–688`), `RepositoryRegistry.get` (`repository_registry.py:354–369`)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_repo_resolver.py` | resolve from repo root returns hydrated RepoContext with correct repo_id + tracked_branch, resolve from a nested subdirectory walks up and returns the same context, resolve from a `.git`-as-file worktree returns the same repo_id as the bare repo (reuses P1's worktree fixture from `tests/test_repo_identity.py`), resolve of a path outside any registered repo returns None, resolve of a path whose `.git` exists but repo_id isn't registered returns None (no auto-register), `find_by_path` fast-path is used when registry has the path pre-keyed (assert via mock call-count) | `pytest tests/test_repo_resolver.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/core/repo_resolver.py` | — | — |
| SL-3.3 | verify | SL-3.2 | owned files + SL-1 + SL-2 files on read | all P2A tests | `pytest tests/test_repo_context.py tests/test_store_registry.py tests/test_repo_resolver.py -v` |

## Execution Notes

- **Single-writer files**: none — lane file ownership is disjoint. SL-2 is the sole editor of `multi_repo_manager.py` for this phase (SL-1 + SL-3 only read it via `RepositoryInfo` imports).

- **Known destructive changes**:
  - `MultiRepositoryManager._connections: Dict[str, SQLiteStore] = {}` initialization at `multi_repo_manager.py:121` is **replaced** by a `StoreRegistry` attribute. The dict is gone as a direct instance attribute.
  - `MultiRepositoryManager._get_connection` body (~lines 375–392) is **replaced** with `return self._store_registry.get(repository_id)`.
  - `MultiRepositoryManager.close` body (~lines 813–823) is **replaced** with `self._store_registry.shutdown()` (plus the registry-save line that already runs).
  - Cache-pop line in `unregister_repository` (~lines 307–310) is **replaced** with `self._store_registry.close(repository_id)`.
  - All four are within SL-2's owned file. Whitelist the method-level deletions for `execute-phase`'s pre-merge destructiveness check.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If SL-3 finds its worktree base is pre-SL-1's merge AND pre-SL-2's merge, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. SL-1 and SL-2 are parallel roots; their worktree base is session-start main and they must not assume any peer has merged before them.

- **Harness reality (carried forward from P1)**: `isolation: "worktree"` did not produce separate worktrees during P1 execution — all four P1 lanes committed directly onto main in linear order. Disjoint file ownership (which P2A preserves) was the saving grace. Expect the same pattern here. The stale-base guidance above still applies as a contract — lane teammates should not silently force-update if the harness misbehaves.

- **Thread-safety posture**: SL-2's concurrent-`get()` test is non-negotiable (fills the test-gap the exploration surfaced). SQLite's WAL mode gives per-connection safety, but the cache dict itself needs an explicit `threading.Lock`.

- **Diff-size discipline on `multi_repo_manager.py`**: SL-2's pre-merge check should include `git diff --shortstat main..HEAD -- mcp_server/storage/multi_repo_manager.py` with a human-review gate if >80 lines changed. This prevents scope creep into the public search methods that should stay untouched for P2A.

## Acceptance Criteria

- [ ] `from mcp_server.core.repo_context import RepoContext` succeeds; `@dataclass(frozen=True)` confirmed via `dataclasses.fields(RepoContext)` length == 5 and `dataclasses.is_dataclass(RepoContext)` True (exit criterion #1, owned by SL-1.1).
- [ ] `StoreRegistry.for_registry(registry).get(repo_id)` returns the SAME `SQLiteStore` instance on two consecutive calls (`id(a) == id(b)`) (exit criterion #2, owned by SL-2.1).
- [ ] `StoreRegistry.shutdown()` followed by `get(repo_id)` returns a NEW instance (different `id()`) — confirming close clears the cache (exit criterion #2, owned by SL-2.1).
- [ ] 8 concurrent threads calling `StoreRegistry.get(repo_id)` against a real tmp registry + SQLite: all receive the same instance, no `database is locked` errors, ThreadPoolExecutor completes in <5s (exit criterion #2, owned by SL-2.1).
- [ ] `RepoResolver(registry, store_registry).resolve(Path("/nested/subdir"))` where `/nested/subdir` is a subtree under a registered repo returns a `RepoContext` whose `repo_id` matches `compute_repo_id(repo_root).repo_id` (exit criterion #3, owned by SL-3.1).
- [ ] `RepoResolver.resolve(Path("/some/unregistered/path"))` where `.git` does not exist ANY level up returns `None` without raising (exit criterion #3, owned by SL-3.1).
- [ ] `MultiRepositoryManager.search_symbol` against a 2-repo test fixture returns results identical to the pre-refactor baseline (exit criterion #4 — delegation is functionally equivalent, owned by SL-2.1).

## Verification

```bash
# End-to-end after all SL lanes merge:
.venv/bin/pytest \
  tests/test_repo_identity.py tests/test_repository_registry.py \
  tests/test_multi_repo_manager.py tests/test_ignore_patterns.py \
  tests/test_git_index_manager.py \
  tests/test_repo_context.py tests/test_store_registry.py \
  tests/test_repo_resolver.py -v

# Import smoke:
.venv/bin/python3 -c "
from mcp_server.core.repo_context import RepoContext
from mcp_server.storage.store_registry import StoreRegistry
from mcp_server.core.repo_resolver import RepoResolver
from dataclasses import fields, is_dataclass
assert is_dataclass(RepoContext) and RepoContext.__dataclass_params__.frozen
assert len(fields(RepoContext)) == 5
assert {f.name for f in fields(RepoContext)} == {'repo_id', 'sqlite_store', 'workspace_root', 'tracked_branch', 'registry_entry'}
print('P2A types OK')
"

# Manual resolver smoke against the live repo:
.venv/bin/python3 - <<'EOF'
from pathlib import Path
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.store_registry import StoreRegistry
from mcp_server.core.repo_resolver import RepoResolver
reg = RepositoryRegistry(Path("/home/viperjuice/code/Code-Index-MCP/.indexes/repository_registry.json"))
store_reg = StoreRegistry.for_registry(reg)
resolver = RepoResolver(reg, store_reg)
ctx = resolver.resolve(Path.cwd() / "mcp_server" / "storage")
print(f"repo_id         = {ctx.repo_id if ctx else 'None'}")
print(f"tracked_branch  = {ctx.tracked_branch if ctx else 'None'}")
print(f"workspace_root  = {ctx.workspace_root if ctx else 'None'}")
EOF
```

All commands above should return success. A `None` from the resolver smoke is acceptable IF the current repo isn't registered in the production registry — the integration tests cover the registered case via temp fixtures.
