---
phase_loop_plan_version: 1
phase: WATCH
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# WATCH: Multi-Repo Watcher Event Correctness

## Context

WATCH is the third phase in the v6 multi-repo hardening roadmap. It depends on
IDXSAFE's explicit mutation-result contract and hardens the live watcher path
so repo-dirty state, move/delete recovery, and artifact health all reflect
what actually happened instead of optimistic control flow.

Current repo state gathered during planning:

- `specs/phase-plans-v6.md` is tracked and clean in this worktree, and its live
  SHA matches the required
  `032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.
- The checkout is on `main`, clean in content, and ahead of `origin/main` by
  two commits after the ARTPUB and IDXSAFE closeout work.
- `plans/phase-plan-v6-WATCH.md` did not exist before this planning run.
- `MultiRepositoryHandler._trigger_reindex_with_ctx()` currently calls
  `dispatcher.remove_file(...)` and `dispatcher.index_file_guarded(...)`
  without inspecting the returned `IndexResult`, and `on_any_event()` marks the
  repo changed from a coarse boolean instead of explicit mutation truth.
- `_move_with_ctx()` currently calls `dispatcher.move_file(...)` without first
  verifying that the destination still exists, even though
  `GitAwareIndexManager._incremental_index_update()` already treats
  disappeared-rename destinations as a special recovery case.
- The missed-event hooks `_on_missed_create`, `_on_missed_delete`, and
  `_on_missed_rename` reuse the same boolean handler contract, so they can mark
  repos changed without distinguishing a landed mutation from a skipped or
  failed mutation.
- `_sync_repository()` only looks at `IndexSyncResult.action` plus
  `files_processed > 0` before publishing, and a successful remote
  `publish_on_reindex()` currently leaves the registry stuck at
  `artifact_health="local_only"` because only the local artifact path updates
  registry state on success.
- `GitAwareIndexManager.sync_all_repositories(parallel=True)` still advertises
  a `parallel` argument even though the implementation is explicitly sequential
  with a `TODO`, so the public manager surface still over-promises behavior
  that WATCH can correct locally without widening into a new bulk-sync system.

## Interface Freeze Gates

- [ ] IF-0-WATCH-1 - Live and missed event mutation truth contract:
      `MultiRepositoryHandler._trigger_reindex_with_ctx(...)`,
      `_remove_with_ctx(...)`, `_move_with_ctx(...)`, `on_any_event(...)`, and
      `MultiRepositoryWatcher._on_missed_create/_delete/_rename(...)` use the
      explicit IDXSAFE mutation results to decide whether a repo is marked
      changed, instead of treating handler control flow as success.
- [ ] IF-0-WATCH-2 - Move destination parity contract:
      multi-repo move handling verifies the destination still exists before
      recording a move, and a disappeared destination counts as a change only
      if the explicit safe-recovery delete of the stale source succeeds.
- [ ] IF-0-WATCH-3 - Publish health truth contract:
      `MultiRepositoryWatcher._sync_repository(...)` updates repository
      artifact state to a healthy remote-publish value after successful
      `publish_on_reindex(...)`, preserves `local_only` only when no remote
      publisher ran, and leaves failures visible as `publish_failed`.
- [ ] IF-0-WATCH-4 - Bulk sync API truth contract:
      `GitAwareIndexManager.sync_all_repositories(...)` either implements the
      advertised parallel semantics or removes the misleading `parallel=True`
      surface everywhere WATCH touches. For this phase, the minimal repair is
      to remove the unsupported argument and align nearby architecture text.

## Lane Index & Dependencies

- SL-0 - WATCH contract freeze tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Multi-repo watcher mutation and publish truth; Depends on: SL-0; Blocks: SL-3; Parallel-safe: no
- SL-2 - Bulk sync API truth cleanup; Depends on: SL-0; Blocks: SL-3; Parallel-safe: yes
- SL-3 - Architecture/docs reducer; Depends on: SL-0, SL-1, SL-2; Blocks: WATCH acceptance; Parallel-safe: no

## Lanes

### SL-0 - WATCH Contract Freeze Tests

- **Scope**: Freeze the watcher-visible mutation, recovery, publish-health, and sync-API contracts before changing runtime code.
- **Owned files**: `tests/test_watcher_multi_repo.py`, `tests/test_watcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-WATCH-1, IF-0-WATCH-2, IF-0-WATCH-3, IF-0-WATCH-4
- **Interfaces consumed**: IF-0-IDXSAFE-1; existing `IndexResult` and `IndexResultStatus`; existing `artifact_health` vocabulary used by repository listing and artifact coordination
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend the multi-repo watcher tests so live events and missed-event helpers only mark a repo changed when the dispatcher returns an explicit landed mutation or a successful safe-recovery mutation.
  - test: Add coverage for guarded-index skip statuses so wrong-branch, gitignore, unsupported-extension, missing-file, and explicit IDXSAFE skip/no-op results do not look like successful watcher mutations.
  - test: Add move-destination disappearance coverage so the multi-repo watcher matches the single-repo watcher safety rule: do not record a move when the destination vanished, and only count a stale-source delete as a change when that delete explicitly succeeds.
  - test: Extend `_sync_repository()` coverage so successful remote publish updates `last_published_commit` and `artifact_health` away from `local_only`, while publisher failures stay `publish_failed` and local-only fallback remains `local_only`.
  - test: Add a manager-surface truth check so WATCH no longer leaves an advertised `sync_all_repositories(parallel=True)` contract in place without implementation.
  - impl: Keep this lane test-only; it freezes the WATCH contract for SL-1 through SL-3.
  - verify: `uv run pytest tests/test_watcher_multi_repo.py tests/test_watcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Multi-Repo Watcher Mutation And Publish Truth

- **Scope**: Make the multi-repo watcher mark repo state and artifact state from explicit mutation and publish outcomes instead of optimistic booleans.
- **Owned files**: `mcp_server/watcher_multi_repo.py`
- **Interfaces provided**: IF-0-WATCH-1, IF-0-WATCH-2, IF-0-WATCH-3
- **Interfaces consumed**: SL-0 WATCH contract tests; IF-0-IDXSAFE-1 explicit mutation results; `ArtifactPublisher.publish_on_reindex(...)`; `RepositoryRegistry.update_artifact_state(...)`; existing `IndexSyncResult.action` contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 watcher-focused tests first and confirm the current boolean handler contract fails them.
  - impl: Add a small watcher-local decision helper so `_trigger_reindex_with_ctx()`, `_remove_with_ctx()`, and `_move_with_ctx()` interpret explicit `IndexResultStatus` values instead of returning success from control flow alone.
  - impl: Make live `created`, `modified`, `deleted`, and missed-event paths mark a repo changed only when an index/remove/move mutation actually lands, not when the dispatcher returns a skip, no-op, or hidden failure.
  - impl: Make `_move_with_ctx()` verify `new_path.exists()` before `dispatcher.move_file(...)`, and when the destination has disappeared, fall back to explicit stale-source delete handling only if that delete mutation succeeds.
  - impl: Preserve wrong-branch, gitignore, unsupported-extension, and missing-file drops as non-mutating watcher outcomes; WATCH should improve truth, not widen the mutation surface.
  - impl: After successful `publish_on_reindex(...)`, update registry state with `last_published_commit=synced_commit` and a healthy remote-publish artifact state such as `published`, while keeping `publish_failed` for publisher exceptions and `local_only` only for the no-remote-publisher path.
  - verify: `uv run pytest tests/test_watcher_multi_repo.py tests/test_watcher.py -q --no-cov`
  - verify: `rg -n "mark_repository_changed|_trigger_reindex_with_ctx|_remove_with_ctx|_move_with_ctx|publish_failed|local_only|artifact_health|publish_on_reindex" mcp_server/watcher_multi_repo.py`

### SL-2 - Bulk Sync API Truth Cleanup

- **Scope**: Repair the misleading manager API around bulk sync semantics without expanding WATCH into a new parallel sync subsystem.
- **Owned files**: `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-WATCH-4
- **Interfaces consumed**: SL-0 manager-surface truth test; existing sequential `sync_repository_index(...)`; `RepositoryRegistry.get_repositories_needing_update()`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use the SL-0 sync-surface test first so this lane repairs the actual public contract instead of inventing a new promise.
  - impl: Remove the unused `parallel` parameter and its misleading docstring wording from `sync_all_repositories(...)` instead of leaving a TODO-backed API promise in place.
  - impl: Keep the existing sequential behavior explicit; WATCH should fix the truth surface locally, not introduce executor fanout or new lock ordering risks.
  - verify: `uv run pytest tests/test_git_index_manager.py -q --no-cov`
  - verify: `rg -n "sync_all_repositories\\(|parallel|TODO: Add parallel processing support" mcp_server/storage/git_index_manager.py tests/test_git_index_manager.py`

### SL-3 - Architecture/Docs Reducer

- **Scope**: Reduce the WATCH runtime decisions into accurate architecture text and consciously handle docs impact.
- **Owned files**: `architecture/level4/index_management.puml`
- **Interfaces provided**: conscious documentation-impact handling for WATCH; aligned IF-0-WATCH-4 architecture text
- **Interfaces consumed**: SL-0 through SL-2 results; roadmap exit criteria; existing repository status vocabulary (`ready`, `prepared`, `published`, `local_only`, `publish_failed`)
- **Parallel-safe**: no
- **Tasks**:
  - test: Update architecture text only after SL-1 and SL-2 freeze the actual watcher and sync-manager behavior.
  - impl: Align the level-4 index-management diagram with the real bulk-sync contract so it no longer implies unsupported `parallel=True` semantics.
  - impl: Reflect the chosen healthy remote publish state only if the diagram already names artifact-health semantics; do not widen the product topology or invent new deployment flows in this phase.
  - verify: `rg -n "sync_all_repositories|parallel|published|local_only|publish_failed" architecture/level4/index_management.puml`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual WATCH execution.

Lane-specific contract checks:

```bash
uv run pytest tests/test_watcher_multi_repo.py tests/test_watcher.py tests/test_git_index_manager.py -q --no-cov
rg -n "mark_repository_changed|_trigger_reindex_with_ctx|_remove_with_ctx|_move_with_ctx|publish_failed|local_only|artifact_health|publish_on_reindex" \
  mcp_server/watcher_multi_repo.py
rg -n "sync_all_repositories\\(|parallel|TODO: Add parallel processing support" \
  mcp_server/storage/git_index_manager.py \
  tests/test_git_index_manager.py \
  architecture/level4/index_management.puml
```

Whole-phase regression commands:

```bash
uv run pytest tests/test_watcher_multi_repo.py tests/test_watcher.py tests/test_git_index_manager.py tests/test_ref_poller_edges.py -q --no-cov
make test
git status --short --branch
```

## Acceptance Criteria

- [ ] Multi-repo watcher reindex/remove/move paths honor explicit IDXSAFE mutation results instead of assuming success from handler control flow.
- [ ] Repositories are marked changed only when a mutation landed or a safe recovery mutation completed successfully; wrong-branch, gitignore, unsupported-extension, missing-file, and skipped/no-op outcomes remain non-mutating.
- [ ] Move events verify the destination still exists before recording a move, matching the single-repo watcher safety behavior.
- [ ] Successful remote publish updates repository artifact health away from stale `local_only` state and records the published commit, while failures remain visible as `publish_failed`.
- [ ] `sync_all_repositories()` no longer advertises unsupported `parallel=True` semantics.
- [ ] Tests cover two watched repositories, wrong-branch drops, guarded-index skips, move-destination disappearance, publish health transitions, and the bulk-sync API truth surface.
- [ ] WATCH stays within multi-repo watcher/status hardening and does not broaden product topology or add a new bulk-sync subsystem.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-WATCH.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-WATCH.md
  artifact_state: staged
```
