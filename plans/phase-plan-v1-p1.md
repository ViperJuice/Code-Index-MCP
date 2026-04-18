# PHASE-1-repo-identity-default-branch-pinning: Phase 1 — Repo Identity & Default-Branch Pinning

## Context

Code-Index-MCP today computes repository identity in **two divergent places**, neither of which is worktree-aware:

- `mcp_server/storage/multi_repo_manager.py:193–211::_generate_repository_id` — SHA256[:16] of `git config --get remote.origin.url` (fallback: SHA256[:16] of the absolute path).
- `mcp_server/storage/repository_registry.py:562–569::_generate_repo_id` — SHA1[:12] of the absolute path with a `{repo_name}-` prefix.

A repo registered through one path and later queried through the other resolves to a different id. Neither scheme distinguishes `.git` as a file (worktree) from `.git` as a directory, so every worktree of a given repo hashes to a fresh id. The existing registry JSON already stores `current_branch` and `last_indexed_branch` fields and `_get_preferred_branch` (`repository_registry.py:534–545`) does a `main`/`master` fallback — but the `origin/HEAD` step needed by the phase spec is missing, and `git_index_manager.py:106–113` **forces a full reindex** whenever `current_branch != last_indexed_branch`, exactly the behavior this phase must remove.

Walker coverage is partial: the dispatcher walker at `dispatcher_enhanced.py:1669–1718` already calls `IgnorePatternManager.should_ignore()` at root level via `mcp_server/core/ignore_patterns.py` (which exists, fnmatch-based, root-only). The auto-index walker at `scripts/cli/mcp_server_cli.py:370–387` does not — it only prunes a hardcoded 5-dir set. Unifying the two behind a shared `build_walker_filter(root)` closes the gitignore gap without pulling in new dependencies.

Reusable helpers already in place: the git-subprocess pattern at `repository_registry.py:465–480`, the atomic JSON-write pattern at lines 90–123, `_normalize_branch_name` at 498–502, and the `RLock` discipline on `RepositoryRegistry._lock` (reentrant, safe for load-then-migrate-inline flows).

## Interface Freeze Gates
- [ ] **IF-0-P1-1** — `mcp_server/storage/repo_identity.py::compute_repo_id(path: Path) -> RepoIdentity` where `RepoIdentity = {repo_id: str (16-hex sha256), git_common_dir: Optional[Path], source: Literal["git_common_dir", "remote_url", "abs_path"]}`. Tier order: (1) `git rev-parse --git-common-dir` → resolved POSIX path → sha256[:16]; (2) normalized `remote.origin.url` → sha256[:16]; (3) `Path(path).resolve().as_posix()` → sha256[:16]. Same id returned for every worktree of one repo.
- [ ] **IF-0-P1-2** — `RepositoryInfo` field set includes (additively): `tracked_branch: Optional[str] = None`, `git_common_dir: Optional[str] = None`. `__post_init__` accepts both str and Path for `git_common_dir`. `tracked_branch` resolution order enforced at registration time: `git symbolic-ref refs/remotes/origin/HEAD` → `main` → `master` → current HEAD branch. Backward-compatible load (optional fields default to None for legacy records).

## Lane Index & Dependencies

```
SL-1 — Identity module (compute_repo_id + RepoIdentity + resolve_tracked_branch)
  Depends on: (none)
  Blocks: SL-2, SL-3
  Parallel-safe: no (sole root; must land first)

SL-2 — Registry + RepositoryInfo + migration
  Depends on: SL-1
  Blocks: SL-3
  Parallel-safe: no (owns shared dataclass)

SL-3 — Branch-change reindex guard
  Depends on: SL-2
  Blocks: (none)
  Parallel-safe: yes (disjoint files; after SL-2 freeze)

SL-4 — Walker gitignore unification
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes (fully independent; can start day 1)
```

## Lanes

### SL-1 — Identity module

- **Scope**: Create `mcp_server/storage/repo_identity.py` with `compute_repo_id(path) -> RepoIdentity` and `resolve_tracked_branch(git_common_dir) -> str`. This is the single source of truth that replaces both legacy id schemes.
- **Owned files**: `mcp_server/storage/repo_identity.py`, `tests/test_repo_identity.py`
- **Interfaces provided**: IF-0-P1-1 (`compute_repo_id`, `RepoIdentity`), `resolve_tracked_branch`
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_repo_identity.py` | `compute_repo_id` worktree equivalence (bare + 3 worktrees → same id), URL-tier fallback, abs-path fallback, `resolve_tracked_branch` order (origin/HEAD → main → master → current), idempotency across calls | `pytest tests/test_repo_identity.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/storage/repo_identity.py` | — | — |
| SL-1.3 | verify | SL-1.2 | `mcp_server/storage/repo_identity.py`, `tests/test_repo_identity.py` | all SL-1 tests | `pytest tests/test_repo_identity.py -v` |

### SL-2 — Registry + RepositoryInfo + migration

- **Scope**: Add `tracked_branch` + `git_common_dir` fields to `RepositoryInfo`; wire `compute_repo_id` into every registration path; delete the legacy SHA1 `_generate_repo_id`; implement load-time re-keying of legacy registry entries including per-repo SQLite `UPDATE` for `repository_id` foreign keys.
- **Owned files**: `mcp_server/storage/multi_repo_manager.py`, `mcp_server/storage/repository_registry.py`, `mcp_server/storage/sqlite_store.py` (additive schema only — two nullable columns on `repositories`), `tests/test_repository_registry.py`, `tests/test_multi_repo_manager.py`
- **Interfaces provided**: IF-0-P1-2, registry auto-rekey behavior
- **Interfaces consumed**: IF-0-P1-1 (`compute_repo_id`), `resolve_tracked_branch` (both from SL-1)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | SL-1.3 | `tests/test_repository_registry.py`, `tests/test_multi_repo_manager.py` | `RepositoryInfo` accepts `tracked_branch`/`git_common_dir`, legacy JSON loads successfully with defaults, registration populates both new fields via `compute_repo_id`/`resolve_tracked_branch`, load-time migration re-keys a legacy SHA1-prefixed entry and issues `UPDATE files SET repository_id=?` (verified against an in-memory SQLite fixture), `MultiRepositoryManager._generate_repository_id` and `MultiRepositoryManager.resolve_repo_id` delegate to `compute_repo_id` | `pytest tests/test_repository_registry.py tests/test_multi_repo_manager.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/storage/multi_repo_manager.py`, `mcp_server/storage/repository_registry.py`, `mcp_server/storage/sqlite_store.py` | — | — |
| SL-2.3 | verify | SL-2.2 | owned files above + SL-1 files on read | all SL-1 + SL-2 tests | `pytest tests/test_repo_identity.py tests/test_repository_registry.py tests/test_multi_repo_manager.py -v` |

### SL-3 — Branch-change reindex guard

- **Scope**: Replace the "branch changed → force full reindex" block at `git_index_manager.py:106–113` with `should_reindex_for_branch(current, tracked)` logic: when `current_branch != tracked_branch`, skip reindex (log and return "up_to_date"). Update `watcher_multi_repo.py` + `cli/repository_commands.py` callsites to read `tracked_branch` from `RepositoryInfo`.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/watcher_multi_repo.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: internal `should_reindex_for_branch(current: str, tracked: str) -> bool`
- **Interfaces consumed**: IF-0-P1-2 (`RepositoryInfo.tracked_branch` field from SL-2)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | SL-2.3 | `tests/test_git_index_manager.py` | checkout of a non-tracked branch in a fixture repo produces zero `_full_index` / `_incremental_index_update` calls (mock the dispatcher), same-branch HEAD advance still triggers incremental update, `should_reindex_for_branch` unit tests for all four (current == tracked, current != tracked, current None, tracked None) permutations | `pytest tests/test_git_index_manager.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/storage/git_index_manager.py`, `mcp_server/watcher_multi_repo.py`, `mcp_server/cli/repository_commands.py` | — | — |
| SL-3.3 | verify | SL-3.2 | owned files + SL-1/SL-2 files on read | all SL-1 + SL-2 + SL-3 tests | `pytest tests/test_repo_identity.py tests/test_repository_registry.py tests/test_multi_repo_manager.py tests/test_git_index_manager.py -v` |

### SL-4 — Walker gitignore unification

- **Scope**: Extract `build_walker_filter(root_path) -> Callable[[Path], bool]` in `mcp_server/core/ignore_patterns.py` that combines the unified `EXCLUDED_DIR_PARTS` set with `IgnorePatternManager.should_ignore()`. Wire into both walkers so they share the same semantic. Root-level `.gitignore` only (scope-limited; nested `.gitignore` deferred — documented as future work).
- **Owned files**: `mcp_server/core/ignore_patterns.py`, `scripts/cli/mcp_server_cli.py` (walker block only, ~lines 370–387), `mcp_server/dispatcher/dispatcher_enhanced.py` (walker block only, ~lines 1669–1718), `tests/test_ignore_patterns.py`
- **Interfaces provided**: `build_walker_filter(root)`, unified `EXCLUDED_DIR_PARTS` constant
- **Interfaces consumed**: (none)
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_ignore_patterns.py` | `build_walker_filter` returns True for paths matching root `.gitignore`, False for non-ignored, True for every entry in `EXCLUDED_DIR_PARTS`, both walkers' integration test confirms gitignored files don't appear in indexed output (use a temp-repo fixture with a `.gitignore` file) | `pytest tests/test_ignore_patterns.py -v` |
| SL-4.2 | impl | SL-4.1 | `mcp_server/core/ignore_patterns.py`, `scripts/cli/mcp_server_cli.py` (walker block only), `mcp_server/dispatcher/dispatcher_enhanced.py` (walker block only) | — | — |
| SL-4.3 | verify | SL-4.2 | owned files | all SL-4 tests | `pytest tests/test_ignore_patterns.py -v` |

## Execution Notes

- **Single-writer files**: none — lane file ownership is disjoint. The two walker files (`scripts/cli/mcp_server_cli.py` and `mcp_server/dispatcher/dispatcher_enhanced.py`) are touched only by SL-4, and only their walker blocks; no other P1 lane edits them.

- **Known destructive changes**:
  - `mcp_server/storage/repository_registry.py::_generate_repo_id` is **deleted** by SL-2 (replaced by delegation to `compute_repo_id`). No external callers per the blast-radius analysis.
  - `mcp_server/storage/multi_repo_manager.py::_generate_repository_id` is **replaced** by a one-line delegator body (`return compute_repo_id(repository_path).repo_id`). The method name is preserved because tests patch it (`tests/test_multi_repo_manager.py:168`).
  - The hardcoded `{".git", "node_modules", "__pycache__", ".venv", "venv"}` dir-prune set at `scripts/cli/mcp_server_cli.py:~373` is **replaced** by the shared `EXCLUDED_DIR_PARTS` from `mcp_server/core/ignore_patterns.py` (same or superset of dirs).

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-1's merge (for SL-2) or pre-SL-2's merge (for SL-3), it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge.

- **SQLite migration risk**: SL-2's load-time re-keying runs `UPDATE files/symbols/bm25_content/imports SET repository_id=?` inside the `RepositoryRegistry._lock` before the registry is published. Failure mode: UPDATE fails → log warning, leave entry under old id, schedule re-register on next lookup miss. Do not silently discard the entry.

- **Tier-1 vs Tier-2 identity split on CI**: `compute_repo_id` prefers `git rev-parse --git-common-dir` (Tier 1) but falls back to `remote.origin.url` (Tier 2) when no git dir resolves. CI clones that run without a `.git` directory (unusual but possible) will get a URL-hash id while dev machines get a common-dir-hash id — these disagree across environments. Accepted as out-of-scope for P1; noted as a future hardening item. Document in `compute_repo_id` docstring.

- **Nested `.gitignore` scope**: SL-4 handles root `.gitignore` only. Nested `.gitignore` files up the walk are deferred — noted as future work. `IgnorePatternManager` comment updated to make the root-only semantic explicit.

## Acceptance Criteria

- [ ] `compute_repo_id(path)` returns identical ids for a bare repo + three worktrees in a fixture (exit criterion #1, owned by SL-1.1).
- [ ] `RepositoryInfo` instances produced by `register_repository()` have non-null `tracked_branch` whose value matches `git symbolic-ref refs/remotes/origin/HEAD` when present (exit criterion #2, owned by SL-2.1).
- [ ] Fixture: register repo A on branch `main`, invoke `GitIndexManager.sync_repository_index`, switch to `feature/noise`, modify a tracked file, re-invoke `sync_repository_index` → zero calls to `_full_index` or `_incremental_index_update` (exit criterion #3, owned by SL-3.1).
- [ ] Fixture: repo containing `.gitignore` with `*.log` and a file `foo.log`; both walkers' visit lists do not contain `foo.log` (exit criterion #4, owned by SL-4.1).
- [ ] Given a registry JSON with a legacy SHA1-prefixed id `myrepo-abcd1234beef`, reload via `RepositoryRegistry._load_registry`; assert (a) the in-memory registry key is the new 16-hex sha256, (b) the corresponding SQLite `files` rows now carry the new id, (c) a second reload is a no-op (exit criterion #5, owned by SL-2.1).

## Verification

```bash
# End-to-end after all SL lanes merge:
pytest tests/test_repo_identity.py tests/test_repository_registry.py \
       tests/test_multi_repo_manager.py tests/test_git_index_manager.py \
       tests/test_ignore_patterns.py -v

# Manual smoke (requires two worktrees of this repo):
python3 - <<'EOF'
from pathlib import Path
from mcp_server.storage.repo_identity import compute_repo_id
main = compute_repo_id(Path.cwd()).repo_id
# assuming a worktree checked out at ../Code-Index-MCP.wt/
wt = compute_repo_id(Path.cwd().parent / "Code-Index-MCP.wt").repo_id
assert main == wt, f"worktree identity broken: {main} vs {wt}"
print("worktree identity OK:", main)
EOF

# Confirm branch-switch no longer triggers reindex:
cd /tmp/test-repo && git checkout -b feature/noise && \
  python -c "from mcp_server.storage.git_index_manager import GitIndexManager; \
             gm = GitIndexManager(...); \
             result = gm.sync_repository_index('<repo_id>'); \
             print(result.action)"
# expect: "up_to_date" (not "full_index")

# Confirm walker respects .gitignore:
echo '*.log' > /tmp/test-repo/.gitignore && touch /tmp/test-repo/foo.log && \
  python -c "from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher; \
             d = EnhancedDispatcher(...); stats = d.index_directory('/tmp/test-repo'); \
             print('ignored count:', stats['ignored_files'])"
# expect: ignored_files >= 1, and no foo.log in the BM25 content
```
