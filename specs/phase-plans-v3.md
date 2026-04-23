# Phase roadmap v3

## Context

P26 completed the alpha evidence loop and surfaced production-readiness blockers for
outside developers using multiple repositories on the same machine. The main product
decision for this roadmap is explicit: multiple worktrees of the same git repository are
not supported for now and must be rejected clearly instead of being silently merged into
one index identity.

The review also found that the MCP handoff currently over-instructs models to use index
search even when a repository is not registered, not indexed, stale, on the wrong branch,
or otherwise known to be unsafe. This roadmap makes index readiness a first-class
contract before repairing the downstream implementation seams.

Root causes this roadmap addresses:

- `repo_id` is source-repo identity, but registration currently lets a second worktree
  overwrite the first registry entry.
- MCP server instructions and tool descriptions are unconditional, while repository
  index readiness is only visible through status output.
- Git-aware incremental indexing still calls the pre-RepoContext dispatcher interface.
- Branch drift handling bypasses its own tracked-branch guard to avoid looped rescans.
- Artifact upload/download uses mixed GitHub Actions and release-asset conventions with
  global names and root-level install paths.
- Some runtime state remains process-global or incompletely wired for per-repo use.

## Architecture North Star

Code-Index-MCP should be safe-by-default for one or more unrelated repositories on the
same machine. Every repository must have an explicit readiness state before search tools
claim authority. Unsupported same-repo worktree configurations should fail closed with a
clear remediation. Indexed search should never turn an unavailable, stale, or wrong-branch
index into a plain empty result.

For v3, the supported production model is:

- many unrelated git repositories on one machine;
- one registered worktree/path per git common directory;
- tracked default branch indexing only;
- repository-scoped SQLite and artifact hydration;
- semantic and graph behavior either repo-scoped or explicitly unavailable in status.

## Assumptions

- Public alpha may proceed only after this roadmap's blocker phases pass.
- Same-repo multiple worktree support is a future feature, not a v3 requirement.
- `MCP_ALLOWED_ROOTS` remains the path sandbox boundary for filesystem paths.
- STDIO remains the primary LLM tool surface; FastAPI remains an admin/diagnostic surface.
- Existing P21-P26 release gates stay in force unless a v3 phase explicitly narrows them.

## Non-Goals

- No support for multiple checked-out branches of the same repo at the same time.
- No GA support matrix expansion.
- No new artifact backend beyond the selected v3 provider contract.
- No cross-machine distributed indexing semantics beyond artifact publish/fetch.
- No marketing-site or docs-site redesign.

## Cross-Cutting Principles

- Fail closed when repository readiness is unknown, stale, missing, wrong-branch, or
  unsupported.
- Do not advance `last_indexed_commit` unless the durable index was actually updated.
- Do not present a missing index as "0 results".
- Keep raw local/private evidence out of git.
- Prefer one shared contract helper over repeated ad hoc readiness checks.
- Make status output, tool responses, docs, and tests use the same vocabulary.

## Top Interface-Freeze Gates

- IF-0-P27-1 - Worktree rejection contract: registering or resolving a second filesystem
  path with the same git common directory returns `multiple_worktrees_unsupported` and
  names the already-registered path plus remediation.
- IF-0-P27-2 - Repository readiness contract: every query/mutation path can classify a
  repository as `ready`, `unregistered_repository`, `missing_index`, `index_empty`,
  `stale_commit`, `wrong_branch`, `index_building`, or `unsupported_worktree`.
- IF-0-P28-1 - Model handoff contract: server instructions, tool descriptions, AGENTS,
  README, and command docs tell models to use indexed search only when readiness is
  `ready`; otherwise use native search or run `reindex`.
- IF-0-P29-1 - Incremental indexing mutation contract: git-aware sync and
  `IncrementalIndexer` call ctx-first dispatcher APIs and never mark commits indexed on
  dry-run, partial failure, or missing DB.
- IF-0-P30-1 - Tracked-branch contract: branch drift is non-mutating; only the tracked
  branch may run incremental or full index repair.
- IF-0-P31-1 - Artifact identity contract: artifact IDs and manifests include repo_id,
  tracked branch, commit, schema version, and semantic profile hash; downloads reject
  wrong-repo or wrong-branch payloads.
- IF-0-P32-1 - Runtime isolation contract: repository-scoped SQLite, semantic, graph,
  plugin, and mutation state is either correctly scoped or explicitly unavailable.
- IF-0-P33-1 - Production matrix contract: release gates cover unrelated multi-repo use,
  same-repo worktree rejection, wrong-branch safety, incremental repair, revert/rename,
  stale/missing index fallback, and wrong-artifact rejection.
- IF-0-P34-1 - Public-alpha readiness contract: docs, changelog, and release checklist
  state the supported v3 operating model and all remaining documented limitations.

## Phases

### Phase 27 — Repository Scope & Readiness Contracts (P27)

**Objective**

Freeze and implement the source-of-truth contracts for supported repository scope,
explicit same-repo worktree rejection, and repository index readiness classification.

**Exit criteria**
- [ ] Registering a second path with the same git common directory fails with
      `multiple_worktrees_unsupported`.
- [ ] Querying or resolving an unsupported sibling worktree does not silently use the
      existing registered index.
- [ ] A shared readiness helper returns the v3 readiness enum for registered and
      unregistered repositories.
- [ ] `get_status` reports readiness consistently for every registered repository.
- [ ] Tests cover clean ready repo, missing index, empty index, stale commit,
      wrong branch, unregistered path, and unsupported worktree.

**Scope notes**

This is the contract phase for v3. It should be small and decisive: reject unsupported
worktrees now, leave future multiple-worktree support to a later roadmap.

**Non-goals**

- No attempt to index multiple worktrees of the same repo.
- No artifact or incremental-indexing behavior changes beyond using the readiness helper
  where needed for contract tests.

**Key files**

- `mcp_server/storage/repo_identity.py`
- `mcp_server/storage/repository_registry.py`
- `mcp_server/core/repo_resolver.py`
- `mcp_server/health/repo_status.py`
- `mcp_server/cli/repository_commands.py`
- `mcp_server/cli/tool_handlers.py`
- `tests/test_repository_registry.py`
- `tests/test_repo_resolver.py`
- `tests/test_repository_readiness.py`

**Depends on**
- P26

**Produces**
- IF-0-P27-1 - Worktree rejection contract.
- IF-0-P27-2 - Repository readiness contract.

### Phase 28 — MCP Tool Handoff & Fail-Closed Query Behavior (P28)

**Objective**

Stop encouraging models to use indexed search when the system knows the target repository
is not safely indexed, and make search/symbol responses fail closed instead of returning
ordinary empty results for unavailable indexes.

**Exit criteria**
- [ ] `search_code` and `symbol_lookup` check readiness before querying.
- [ ] Missing, stale, wrong-branch, unsupported-worktree, and unregistered states return a
      structured `index_unavailable` response with `safe_fallback: "native_search"`.
- [ ] Empty ready indexes are distinguishable from unavailable indexes.
- [ ] `_SERVER_INSTRUCTIONS`, tool descriptions, `AGENTS.md`, README, and slash command
      docs say to use MCP search only when readiness is `ready`.
- [ ] Tests assert that unavailable indexes do not produce plain `[]` or `not_found`.

**Scope notes**

This phase is about LLM behavior and user trust. It should avoid broad documentation
rewrites and focus on every surface that currently says "use MCP first" unconditionally.

**Non-goals**

- No changes to search ranking, reranking, or language support.
- No implementation of automatic indexing on every failed query.

**Key files**

- `mcp_server/cli/stdio_runner.py`
- `mcp_server/cli/tool_handlers.py`
- `AGENTS.md`
- `README.md`
- `.claude/commands/mcp-tools.md`
- `.claude/commands/search-code.md`
- `.claude/commands/find-symbol.md`
- `.claude/commands/verify-mcp.md`
- `tests/test_stdio_tool_descriptions.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/docs/`

**Depends on**
- P27

**Produces**
- IF-0-P28-1 - Model handoff contract.

### Phase 29 — Incremental Indexing Interface Repair (P29)

**Objective**

Repair git-aware incremental/full indexing so it uses the ctx-first dispatcher contract,
updates durable indexes only, and records commit state only after a successful mutation.

**Exit criteria**
- [ ] `GitAwareIndexManager` resolves a `RepoContext` before indexing, deleting, moving,
      or full-indexing files.
- [ ] `IncrementalIndexer` uses ctx-first dispatcher calls or is retired behind the
      git-aware manager path.
- [ ] Missing `.mcp-index/current.db` forces a real full rebuild or returns a failed
      readiness/sync state; it does not dry-run success.
- [ ] Any per-file failure prevents `last_indexed_commit` from advancing unless an
      explicit full rebuild succeeds.
- [ ] Integration tests use a real temporary repo, registry, store, and ctx-signature
      dispatcher surface.

**Scope notes**

This phase should remove compatibility fallbacks that hide interface mismatches. The
outcome must be simple to reason about: commit state follows durable index state.

**Non-goals**

- No branch-drift policy changes; P30 owns that.
- No artifact publishing changes; P31 owns that.

**Key files**

- `mcp_server/storage/git_index_manager.py`
- `mcp_server/indexing/incremental_indexer.py`
- `mcp_server/dispatcher/protocol.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/core/repo_resolver.py`
- `mcp_server/storage/store_registry.py`
- `tests/test_git_index_manager.py`
- `tests/test_git_integration.py`
- `tests/test_incremental_indexer.py`

**Depends on**
- P27

**Produces**
- IF-0-P29-1 - Incremental indexing mutation contract.

### Phase 30 — Branch Drift, Reversions & Watcher Recovery (P30)

**Objective**

Make branch changes, force-pushes, reverts, renames, deletes, and dropped filesystem
events deterministic under the default-branch-only indexing policy.

**Exit criteria**
- [ ] Branch drift returns a non-mutating `wrong_branch` readiness/sync result and does
      not enqueue full rescan.
- [ ] Ref polling uses `git -C <repo>` or git-common-dir-safe commands and behaves
      correctly for ordinary repos and explicitly rejected worktrees.
- [ ] Same tracked-branch fast-forwards run incremental repair.
- [ ] Same tracked-branch divergent history or force-push runs full rebuild.
- [ ] Revert commits, deletes, and renames are applied once, not double-counted as both
      delete/add and rename.
- [ ] Dropped-event recovery is either wired by default or removed from production claims;
      if wired, it detects missed creates, deletes, and renames.

**Scope notes**

This phase consumes P29's repaired mutation contract. It should keep the branch policy
boring: tracked branch only, wrong branch never mutates the index.

**Non-goals**

- No support for indexing arbitrary feature branches.
- No multi-worktree support beyond explicit rejection and safe diagnostics.

**Key files**

- `mcp_server/storage/git_index_manager.py`
- `mcp_server/watcher_multi_repo.py`
- `mcp_server/watcher/ref_poller.py`
- `mcp_server/watcher/sweeper.py`
- `mcp_server/indexing/change_detector.py`
- `tests/test_branch_drift_rescan.py`
- `tests/test_ref_poller.py`
- `tests/test_ref_poller_edges.py`
- `tests/test_watcher_sweep.py`
- `tests/test_git_integration.py`

**Depends on**
- P27
- P29

**Produces**
- IF-0-P30-1 - Tracked-branch contract.

### Phase 31 — Artifact Identity, Hydration & Freshness (P31)

**Objective**

Unify artifact upload/download/sync around repository-scoped identity, fail-closed
freshness validation, and hydration into the runtime index location used by the registry.

**Exit criteria**
- [ ] Artifact naming and manifest schema include repo_id, tracked branch, commit, schema
      version, and semantic profile hash.
- [ ] Download rejects artifacts for the wrong repo, wrong branch, wrong schema, stale
      commit, invalid metadata, or missing checksum unless an explicit unsafe override is
      supplied.
- [ ] Install/hydration writes `.mcp-index/current.db` and associated repo-scoped semantic
      state, not root-level `code_index.db`.
- [ ] Process-wide `chdir()` is removed from multi-repo artifact coordination.
- [ ] Watcher/reindex publish paths trigger on actual successful actions and upload or
      clearly report local-only state.
- [ ] Provider configuration cannot select unimplemented S3 behavior in production.

**Scope notes**

This phase should choose one v3 artifact contract and make older naming conventions
compatibility-only. It should not preserve global `index-latest` semantics for multi-repo
use except through a migration alias that still validates repo identity.

**Non-goals**

- No full S3 backend implementation unless selected explicitly as the v3 provider.
- No delta artifact optimization unless the full-artifact contract is already correct.

**Key files**

- `mcp_server/artifacts/artifact_upload.py`
- `mcp_server/artifacts/artifact_download.py`
- `mcp_server/artifacts/publisher.py`
- `mcp_server/artifacts/commit_artifacts.py`
- `mcp_server/artifacts/multi_repo_artifact_coordinator.py`
- `mcp_server/artifacts/provider_factory.py`
- `mcp_server/artifacts/providers/`
- `.github/workflows/mcp-index.yml`
- `.github/workflows/index-artifact-management.yml`
- `docs/INDEX_MANIFEST_CONTRACT.md`
- `docs/guides/artifact-persistence.md`
- `tests/test_artifact_*.py`

**Depends on**
- P27
- P29
- P30

**Produces**
- IF-0-P31-1 - Artifact identity contract.

### Phase 32 — Runtime Isolation & Dispatcher State Cleanup (P32)

**Objective**

Finish the runtime isolation needed for many unrelated repos on one machine by removing
hard-coded repository IDs and making semantic/graph/plugin state either repo-scoped or
explicitly unavailable.

**Exit criteria**
- [ ] `remove_file` and `move_file` resolve the correct SQLite repository row instead of
      hard-coding `repository_id=1`.
- [ ] `RepoResolver` returns the repository root as `workspace_root` for ctx mutation
      paths while preserving the original requested path where needed for diagnostics.
- [ ] `SemanticIndexerRegistry` is wired through normal bootstrap when semantic search is
      enabled, or semantic search reports unavailable per repo.
- [ ] Graph search/context features are repo-scoped or disabled with explicit status.
- [ ] Plugin caches are evicted on repository unregister/remove and do not bleed mutable
      state between repos.
- [ ] Cross-repo search status clearly reports which repos are ready and which features
      are unavailable.

**Scope notes**

This phase is the cleanup for deferred P2B/P3/P4 state. It can disable advanced features
temporarily if that is safer than claiming cross-repo correctness prematurely.

**Non-goals**

- No new graph algorithm or semantic provider.
- No cross-repo dependency graph expansion beyond existing intended behavior.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/core/repo_context.py`
- `mcp_server/core/repo_resolver.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/storage/store_registry.py`
- `mcp_server/utils/semantic_indexer_registry.py`
- `mcp_server/plugins/plugin_set_registry.py`
- `mcp_server/watcher_multi_repo.py`
- `mcp_server/cli/bootstrap.py`
- `mcp_server/cli/stdio_runner.py`
- `mcp_server/gateway.py`
- `tests/test_dispatcher.py`
- `tests/test_dispatcher_p3_integration.py`
- `tests/test_semantic_indexer_registry.py`

**Depends on**
- P27
- P29

**Produces**
- IF-0-P32-1 - Runtime isolation contract.

### Phase 33 — Production Multi-Repo Matrix & Release Gates (P33)

**Objective**

Turn the v3 production-readiness risks into blocking automated tests and CI/release gates
that exercise realistic multi-repository operation.

**Exit criteria**
- [ ] A production matrix fixture creates two unrelated repos and verifies isolated
      search, symbol lookup, reindex, watcher events, and status.
- [ ] A same-repo linked worktree fixture verifies explicit rejection and safe fallback
      guidance.
- [ ] Branch drift, revert, rename/delete, force-push, missing DB, stale index,
      wrong-artifact, and wrong-branch cases are covered.
- [ ] Container smoke covers MCP readiness and an unindexed-repo fallback path.
- [ ] Release gates fail if any P27-P32 blocker contract regresses.
- [ ] CI job names and runbook gate names map cleanly to operator actions.

**Scope notes**

This phase should prefer fewer high-value integration tests over broad slow coverage. The
matrix is a production gate, not a benchmark suite.

**Non-goals**

- No exhaustive language matrix.
- No public performance claims beyond already-supported smoke thresholds.

**Key files**

- `tests/fixtures/multi_repo.py`
- `tests/test_multi_repo_*.py`
- `tests/test_repository_readiness.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/smoke/`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/release-automation.yml`
- `.github/workflows/container-registry.yml`
- `Makefile`
- `docs/operations/deployment-runbook.md`

**Depends on**
- P28
- P30
- P31
- P32

**Produces**
- IF-0-P33-1 - Production matrix contract.

### Phase 34 — Outside Developer Readiness & Public Alpha Recut (P34)

**Objective**

Prepare the corrected v3 operating model for outside developers by updating docs,
release notes, version/release checklist, and remaining limitation disclosures.

**Exit criteria**
- [ ] README, GETTING_STARTED, MCP configuration docs, deployment runbook, and AGENTS
      describe the supported v3 model: many unrelated repos, one worktree per repo,
      tracked branch only, fail-closed index readiness.
- [ ] Changelog records the v3 blocker fixes and removes stale claims about
      unrestricted multi-worktree/multi-branch operation.
- [ ] Public-alpha checklist requires P27-P33 gates and states remaining limitations.
- [ ] Container/wheel smoke and production matrix gates pass from a clean checkout.
- [ ] Next release identifier is chosen consistently with the version source of truth.

**Scope notes**

This is the release-readiness closeout after the technical blockers are fixed. It should
not reopen implementation decisions unless P33 finds a release-blocking regression.

**Non-goals**

- No GA positioning.
- No new feature work beyond truthful docs and release surface cleanup.

**Key files**

- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/MCP_CONFIGURATION.md`
- `docs/DOCKER_GUIDE.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/user-action-runbook.md`
- `docs/SUPPORT_MATRIX.md`
- `CHANGELOG.md`
- `pyproject.toml`
- `mcp_server/__init__.py`
- `AGENTS.md`
- `CLAUDE.md`

**Depends on**
- P33

**Produces**
- IF-0-P34-1 - Public-alpha readiness contract.

## Phase Dependency DAG

```text
P26
 └─> P27
      ├─> P28 ─────────────┐
      ├─> P29 ─> P30 ──────┼─> P33 ─> P34
      │     └─> P32 ───────┘
      └─> P31 <── P30
```

P27 freezes the readiness and unsupported-worktree contract. P28 can proceed once that
contract exists. P29 repairs mutation APIs before P30 can trust branch/revert behavior.
P31 depends on the same identity/readiness model and should wait for P30 where artifact
publish-on-reindex behavior consumes branch policy. P32 can proceed after P29 because it
touches dispatcher/runtime state. P33 gates the combined behavior; P34 is release closeout.

## Execution Notes

- Plan P27 first with `codex-plan-phase specs/phase-plans-v3.md P27`.
- Do not plan P28 before P27 freezes the readiness response schema; otherwise docs and
  tool descriptions will churn.
- P29 and P28 can be implemented in parallel after P27 because P29 owns mutation paths and
  P28 owns query/handoff paths.
- P30 should wait for P29 so branch drift and revert tests exercise the corrected
  ctx-first mutation path.
- P31 can start interface planning after P27, but implementation should wait until P30
  clarifies publish behavior for tracked-branch changes.
- P32 can run alongside P30/P31 if lane ownership avoids dispatcher conflicts.
- P33 is intentionally serial: it validates the whole v3 operating model.
- P34 should not begin until P33 gates are green.

## Verification

```bash
# P27
uv run pytest tests/test_repository_registry.py tests/test_repo_resolver.py tests/test_repository_readiness.py -v --no-cov

# P28
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_stdio_tool_descriptions.py tests/docs -v --no-cov
rg -n "ALWAYS use|USE BEFORE GREP|index_unavailable|safe_fallback|native_search" \
  mcp_server/cli/stdio_runner.py mcp_server/cli/tool_handlers.py AGENTS.md README.md .claude/commands

# P29
uv run pytest tests/test_git_index_manager.py tests/test_git_integration.py tests/test_incremental_indexer.py -v --no-cov

# P30
uv run pytest tests/test_branch_drift_rescan.py tests/test_ref_poller.py tests/test_ref_poller_edges.py tests/test_watcher_sweep.py tests/test_git_integration.py -v --no-cov

# P31
uv run pytest tests/test_artifact_upload.py tests/test_artifact_download.py tests/test_artifact_provider*.py tests/test_multi_repo_artifact*.py -v --no-cov

# P32
uv run pytest tests/test_dispatcher.py tests/test_dispatcher_p3_integration.py tests/test_semantic_indexer_registry.py -v --no-cov

# P33
uv run pytest tests/smoke tests/test_multi_repo_*.py tests/test_repository_readiness.py tests/test_tool_readiness_fail_closed.py -v --no-cov
make -n alpha-release-gates release-smoke release-smoke-container

# P34
uv run pytest tests/smoke tests/docs tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
rg -n "multiple worktree|tracked branch|index readiness|public alpha|support matrix|rollback" \
  README.md CHANGELOG.md docs AGENTS.md
```

No v3 phase should be accepted if a missing, stale, wrong-branch, unregistered, or
unsupported-worktree index can still appear to the model as an ordinary empty search
result.
