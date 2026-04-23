# P27: Repository Scope & Readiness Contracts

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P27` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is currently untracked; do not run `git clean -fd` before preserving it.

## Context

P27 is the first v3 blocker phase. It freezes the supported repository scope before the downstream phases change tool handoff, mutation behavior, branch policy, artifact identity, runtime isolation, and release gates.

The v3 production model supports many unrelated repositories on one machine, but only one registered filesystem path per git common directory. Multiple worktrees of the same source repository are explicitly unsupported for v3 and must fail closed with a structured `multiple_worktrees_unsupported` error instead of silently sharing one registry entry and index.

The repo already has the identity basis for this contract: `compute_repo_id()` hashes `git rev-parse --git-common-dir`, and `RepositoryRegistry.register_repository()` stores `git_common_dir`. The current gap is enforcement and shared readiness vocabulary. `RepositoryRegistry.find_by_path()` only matches exact registered paths, `RepoResolver.resolve()` falls back from path miss to `compute_repo_id()` and can therefore resolve an unsupported sibling worktree to the existing index, and `build_health_row()` reports only a partial staleness view.

P27 should add one shared readiness classifier that later phases can reuse. P28 will make query tools fail closed based on that classifier; P27 only needs every query/mutation entrypoint to be able to classify repository readiness and must stop unsupported sibling worktrees from resolving to a usable `RepoContext`.

## Interface Freeze Gates

- [ ] IF-0-P27-1 - Worktree rejection contract: registering or resolving a second filesystem path with the same resolved `git_common_dir` returns code `multiple_worktrees_unsupported`, includes `registered_path`, `requested_path`, and `remediation`, and does not update the registry.
- [ ] IF-0-P27-2 - Repository readiness enum contract: the only readiness states are `ready`, `unregistered_repository`, `missing_index`, `index_empty`, `stale_commit`, `wrong_branch`, `index_building`, and `unsupported_worktree`.
- [ ] IF-0-P27-3 - Readiness response contract: shared readiness results expose `state`, `ready`, `code`, `repository_id`, `repository_name`, `registered_path`, `requested_path`, `tracked_branch`, `current_branch`, `current_commit`, `last_indexed_commit`, `index_path`, and `remediation` with absent fields represented as `None` or omitted consistently.
- [ ] IF-0-P27-4 - Resolver contract: `RepoResolver` can classify arbitrary paths without auto-registering, and `resolve()` returns `None` for `unregistered_repository` and `unsupported_worktree` instead of returning another worktree's `RepoContext`.
- [ ] IF-0-P27-5 - Status contract: `get_status` repository rows include the shared readiness state and preserve existing health keys for compatibility.
- [ ] IF-0-P27-6 - CLI registration contract: `mcp repository register <path>` surfaces `multiple_worktrees_unsupported` with the already-registered path and remediation while preserving idempotent registration of the same path.

## Lane Index & Dependencies

- SL-0 - Readiness model and contract tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-1 - Registry worktree rejection; Depends on: SL-0; Blocks: SL-2, SL-4, SL-6; Parallel-safe: yes
- SL-2 - Resolver readiness classification; Depends on: SL-0, SL-1; Blocks: SL-5, SL-6; Parallel-safe: no
- SL-3 - Status readiness surface; Depends on: SL-0; Blocks: SL-6; Parallel-safe: yes
- SL-4 - Repository CLI readiness messaging; Depends on: SL-0, SL-1, SL-3; Blocks: SL-6; Parallel-safe: yes
- SL-5 - Tool-handler classification hooks; Depends on: SL-0, SL-2; Blocks: SL-6; Parallel-safe: yes
- SL-6 - P27 contract audit; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4, SL-5; Blocks: P28, P29, P31; Parallel-safe: no

Lane DAG:

```text
SL-0
 ├─> SL-1 ─> SL-2 ─> SL-5 ─┐
 ├─> SL-3 ─> SL-4 ─────────┤
 └─────────────────────────> SL-6
```

## Lanes

### SL-0 - Readiness Model And Contract Tests

- **Scope**: Define the shared readiness data model, enum vocabulary, and executable P27 contract tests before implementation lanes depend on them.
- **Owned files**: `mcp_server/health/repository_readiness.py`, `tests/test_repository_readiness.py`
- **Interfaces provided**: `RepositoryReadinessState`; `RepositoryReadiness`; `ReadinessClassifier.classify_registered(repo_info, requested_path=None, indexing_active=False)`; `ReadinessClassifier.classify_path(registry, path, indexing_active=False)`; IF-0-P27-2 and IF-0-P27-3 assertions
- **Interfaces consumed**: `RepositoryInfo` from `mcp_server/storage/multi_repo_manager.py`; `compute_repo_id()` from `mcp_server/storage/repo_identity.py`; existing SQLite index paths from registry entries
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_repository_readiness.py` cases for the exact readiness enum values and serialized response keys.
  - test: Add classifier tests for clean ready repo, missing index, empty SQLite index, stale commit, wrong branch, index building, unregistered path, and unsupported worktree.
  - impl: Add `RepositoryReadinessState` as a `str` enum or `Literal`-backed constants with exactly the IF-0-P27-2 states.
  - impl: Add `RepositoryReadiness` as a small dataclass with `ready`, `state`, `code`, context fields, and `to_dict()`.
  - impl: Add a classifier that treats an existing index file with no durable indexed content as `index_empty`; prefer existing SQLite schema/stat helpers when available and fall back to file existence only when schema inspection is unavailable.
  - impl: Add current git commit/branch lookup through existing registry helpers or narrowly scoped local helpers without updating registry state.
  - verify: `uv run pytest tests/test_repository_readiness.py -v --no-cov`

### SL-1 - Registry Worktree Rejection

- **Scope**: Make registration fail closed when a new path has the same git common directory as an existing different registered path.
- **Owned files**: `mcp_server/storage/repository_registry.py`, `tests/test_repository_registry.py`
- **Interfaces provided**: `RepositoryRegistry.find_by_git_common_dir(git_common_dir: Path) -> Optional[str]`; `RepositoryRegistry.find_unsupported_worktree(path: Path) -> Optional[RepositoryInfo]`; `MultipleWorktreesUnsupportedError` with `code = "multiple_worktrees_unsupported"` and `to_dict()`
- **Interfaces consumed**: `compute_repo_id()` and `RepoIdentity.git_common_dir` from `mcp_server/storage/repo_identity.py`; `RepositoryReadinessState.UNSUPPORTED_WORKTREE` from SL-0
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add a same-path idempotency test proving registering the already-registered path still returns the existing repo id.
  - test: Add a git-worktree fixture where registering a sibling worktree raises `MultipleWorktreesUnsupportedError`, preserves the original registry entry, and reports `registered_path`, `requested_path`, `git_common_dir`, and remediation.
  - test: Add a non-git or unrelated-git repo case proving unrelated repositories still register independently.
  - impl: Normalize stored and computed `git_common_dir` with `Path(...).resolve(strict=False)` before comparing.
  - impl: Check for same `git_common_dir` after exact-path idempotency and before creating `RepositoryInfo`.
  - impl: Keep migration tolerant of legacy entries without `git_common_dir`; do not reject entries that cannot be classified.
  - verify: `uv run pytest tests/test_repository_registry.py -v --no-cov`

### SL-2 - Resolver Readiness Classification

- **Scope**: Teach path resolution to classify unsupported and unregistered paths without accidentally resolving sibling worktrees to the existing source repo index.
- **Owned files**: `mcp_server/core/repo_resolver.py`, `tests/test_repo_resolver.py`
- **Interfaces provided**: `RepoResolver.classify(path: Path) -> RepositoryReadiness`; `RepoResolver.resolve(path: Path) -> Optional[RepoContext]` returns a context only when readiness is `ready`, `missing_index`, `index_empty`, `stale_commit`, `wrong_branch`, or `index_building` for the registered path, and returns `None` for `unregistered_repository` and `unsupported_worktree`
- **Interfaces consumed**: SL-0 `ReadinessClassifier`; SL-1 `find_unsupported_worktree()` and `MultipleWorktreesUnsupportedError` semantics; existing `StoreRegistry.get(repo_id)` behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `test_resolve_from_worktree` to match v3 policy: a registered bare/main path may resolve itself, but an unregistered sibling worktree with the same `git_common_dir` returns `None` and classifies as `unsupported_worktree`.
  - test: Add `classify()` tests for registered root, nested path, unregistered git repo, path outside git, and unsupported sibling worktree.
  - impl: Add `RepoResolver.classify()` as the non-mutating classification API for P28 and later phases.
  - impl: Change `resolve()` so a `find_by_path()` miss checks unsupported-worktree status before falling back to repo-id lookup.
  - impl: Preserve existing behavior that unregistered repositories are not auto-registered.
  - verify: `uv run pytest tests/test_repo_resolver.py tests/test_repository_readiness.py -v --no-cov`

### SL-3 - Status Readiness Surface

- **Scope**: Make status repository rows report the shared readiness state while keeping existing health output stable for callers.
- **Owned files**: `mcp_server/health/repo_status.py`, `tests/test_health_surface.py`, `tests/fixtures/health_repo.py`
- **Interfaces provided**: `build_health_row(repo_info, readiness: RepositoryReadiness | None = None) -> dict` rows containing existing keys plus `readiness`, `ready`, `readiness_code`, and `remediation`
- **Interfaces consumed**: SL-0 `ReadinessClassifier.classify_registered()` and `RepositoryReadiness.to_dict()`; existing status assembly in `mcp_server/cli/tool_handlers.py` and `mcp_server/gateway.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update `EXPECTED_KEYS` in `tests/test_health_surface.py` to include readiness keys without removing existing compatibility keys.
  - test: Add status-row cases for ready, missing index, empty index, stale commit, wrong branch, and index building.
  - impl: Have `build_health_row()` call the shared classifier when no readiness object is supplied.
  - impl: Map legacy `staleness_reason` consistently from readiness for backward compatibility: `None` for `ready`, otherwise the readiness state or existing `missing_git_dir` where applicable.
  - impl: Extend `tests/fixtures/health_repo.py` with optional commit, branch, and empty-index controls rather than creating ad hoc fixture files in tests.
  - verify: `uv run pytest tests/test_health_surface.py tests/test_repository_readiness.py -v --no-cov`

### SL-4 - Repository CLI Readiness Messaging

- **Scope**: Surface P27 readiness states and same-repo worktree rejection through repository management commands.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: CLI output for IF-0-P27-6; verbose `mcp repository list -v` readiness line using shared readiness vocabulary
- **Interfaces consumed**: SL-1 `MultipleWorktreesUnsupportedError`; SL-3 `build_health_row()` readiness keys
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add a `repository register` CLI test where the fake registry raises `MultipleWorktreesUnsupportedError` and output includes `multiple_worktrees_unsupported`, the registered path, requested path, and remediation.
  - test: Add a verbose list test requiring `Readiness: ready` or the concrete non-ready state from `build_health_row()`.
  - impl: Catch `MultipleWorktreesUnsupportedError` before the broad `Exception` handler and print the structured code plus remediation.
  - impl: Replace artifact-health-derived `Status: Ready` wording in verbose list with readiness-derived output while keeping artifact fields visible.
  - verify: `uv run pytest tests/test_repository_commands.py tests/test_repository_registry.py -v --no-cov`

### SL-5 - Tool-Handler Classification Hooks

- **Scope**: Make STDIO query and mutation handlers able to classify repository readiness without implementing P28's fail-closed response behavior yet.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: `_classify_ctx(repo_resolver, path_arg) -> RepositoryReadiness`; `_resolve_ctx()` uses resolver readiness and never returns a context for `unsupported_worktree`; `get_status` repository rows consume readiness from SL-3
- **Interfaces consumed**: SL-0 `RepositoryReadiness`; SL-2 `RepoResolver.classify()` and `RepoResolver.resolve()`; existing `_looks_like_path()`, path sandbox checks, and dispatcher protocol
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add handler-level tests with a fake resolver proving unsupported worktree classification is available to `search_code`, `symbol_lookup`, and `reindex` plumbing without dispatching against the registered index.
  - test: Add a `get_status` test proving repositories include readiness rows from `build_health_row()`.
  - impl: Add `_classify_ctx()` as a small helper near `_resolve_ctx()`.
  - impl: Update `_resolve_ctx()` to call resolver classification when available and return `None` for `unsupported_worktree` and `unregistered_repository`.
  - impl: Keep current search/symbol empty-result behavior for non-ready indexes unless the state is `unsupported_worktree`; P28 owns structured `index_unavailable` responses.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py tests/test_health_surface.py -v --no-cov`

### SL-6 - P27 Contract Audit

- **Scope**: Run the P27 contract suite and confirm the frozen interfaces are ready for P28/P29/P31 planning and implementation.
- **Owned files**: (none)
- **Interfaces provided**: completed IF-0-P27-1 and IF-0-P27-2 evidence; readiness schema handoff for P28; unsupported-worktree behavior handoff for P31
- **Interfaces consumed**: SL-0 through SL-5 outputs; roadmap exit criteria from `specs/phase-plans-v3.md`; existing multi-repo tests that depend on registry/resolver behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P27 targeted tests after implementation lanes land.
  - verify: `uv run pytest tests/test_repository_registry.py tests/test_repo_resolver.py tests/test_repository_readiness.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_tool_handlers_readiness.py -v --no-cov`
  - verify: `uv run pytest tests/test_multi_repo_manager.py tests/test_multi_repository_support.py tests/test_multi_repo_search.py -v --no-cov`
  - verify: `rg -n "multiple_worktrees_unsupported|unsupported_worktree|RepositoryReadiness|index_empty|wrong_branch|stale_commit" mcp_server tests`
  - impl: If existing multi-repo tests intentionally exercised old worktree sharing, update only those expectations to the v3 unsupported-worktree contract.
  - impl: Record any P28 follow-up needed for structured `index_unavailable` query responses without broadening P27.

## Verification

Required P27 targeted checks:

```bash
uv run pytest tests/test_repository_registry.py tests/test_repo_resolver.py tests/test_repository_readiness.py -v --no-cov
uv run pytest tests/test_health_surface.py tests/test_repository_commands.py tests/test_tool_handlers_readiness.py -v --no-cov
```

Compatibility checks around multi-repo behavior:

```bash
uv run pytest tests/test_multi_repo_manager.py tests/test_multi_repository_support.py tests/test_multi_repo_search.py -v --no-cov
```

Contract search:

```bash
rg -n "multiple_worktrees_unsupported|unsupported_worktree|RepositoryReadiness|index_empty|wrong_branch|stale_commit" mcp_server tests
```

Whole-phase optional regression:

```bash
make test
```

## Acceptance Criteria

- [ ] Registering a second path with the same resolved git common directory fails with `multiple_worktrees_unsupported`.
- [ ] The rejection response includes the already-registered path, requested path, git common directory, and a remediation that tells the user to use the registered path or unregister it before registering another worktree.
- [ ] Registering the exact same path remains idempotent and does not become an unsupported-worktree error.
- [ ] Querying or resolving an unsupported sibling worktree does not return the existing registered index's `RepoContext`.
- [ ] A shared readiness helper returns only `ready`, `unregistered_repository`, `missing_index`, `index_empty`, `stale_commit`, `wrong_branch`, `index_building`, or `unsupported_worktree`.
- [ ] Readiness results serialize with stable fields that P28 can use for fail-closed tool responses and documentation updates.
- [ ] `get_status` reports readiness consistently for every registered repository while preserving existing status keys.
- [ ] Tests cover clean ready repo, missing index, empty index, stale commit, wrong branch, index building, unregistered path, and unsupported worktree.
- [ ] P27 does not implement multi-worktree indexing, artifact behavior changes, or P28's `index_unavailable` query response contract.
