# P33: Production Multi-Repo Matrix & Release Gates

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P33` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is clean in this worktree
> (`git status --short -- specs/phase-plans-v3.md` produced no output).

## Context

P33 is the serial production gate for the v3 multi-repo operating model. It should start
only after P28, P30, P31, and P32 are implemented, because this phase intentionally tests
the combined behavior rather than reopening individual implementation decisions.

The current repo already has the core ingredients P33 should compose into a blocking
release matrix:

- `tests/fixtures/multi_repo.py` can build git repos and boot an in-process STDIO test
  server, but it does not yet expose `get_status`, linked worktree helpers, or mutation
  helpers for branch/revert/rename/delete cases.
- Existing P27-P32 tests cover many individual contracts: readiness classification,
  query fail-closed behavior, branch drift, force-push detection, artifact identity
  rejection, rename atomicity, and runtime isolation.
- Release smoke currently verifies wheel install, lexical STDIO search on one indexed
  fixture repo, and production container health, but it does not yet verify an unindexed
  repository fallback path.
- Alpha CI gates already exist in Makefile and workflows, but there is no separate gate
  name that maps to the P33 production multi-repo matrix.

P33 should prefer a small number of realistic integration tests over a broad language
matrix. The production matrix should prove that unrelated repositories are isolated and
that unavailable, stale, wrong-branch, unsupported-worktree, or wrong-artifact states
fail closed instead of looking like ordinary empty results.

## Interface Freeze Gates

- [ ] IF-0-P33-1 - Production matrix contract: release gates cover unrelated multi-repo
      use, same-repo worktree rejection, wrong-branch safety, incremental repair,
      revert/rename/delete, stale/missing index fallback, force-push recovery, and
      wrong-artifact rejection.
- [ ] IF-0-P33-2 - Production fixture contract:
      `tests.fixtures.multi_repo.build_production_matrix(tmp_path)` or equivalent
      returns two unrelated git repos with distinct tokens/symbols, their `repo_id`s,
      tracked branch/commit helpers, and a linked same-repo worktree helper; fixture
      helpers must keep all generated evidence under `tmp_path`.
- [ ] IF-0-P33-3 - STDIO gate contract: `TestServerHandle.call_tool()` supports
      `get_status` with the same JSON shape as the real STDIO handler, and matrix tests
      assert readiness rows for every registered repo.
- [ ] IF-0-P33-4 - Release smoke fallback contract: `scripts/release_smoke.py --stdio`
      and the production container smoke both exercise at least one indexed ready repo
      path and one unindexed/unregistered fallback path that returns
      `code: "index_unavailable"` with `safe_fallback: "native_search"`.
- [ ] IF-0-P33-5 - Alpha gate command contract: `make alpha-production-matrix` is the
      canonical P33 operator command, `make alpha-release-gates` depends on it, and CI
      exposes it through a job named `Alpha Gate - Production Multi-Repo Matrix`.
- [ ] IF-0-P33-6 - Runbook gate mapping contract:
      `docs/operations/deployment-runbook.md` lists the P33 gate name, command, workflow
      source, covered blocker contracts, and failure action.

## Lane Index & Dependencies

- SL-0 - Production matrix fixture helpers; Depends on: P28, P30, P31, P32; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Unrelated repo isolation matrix; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-2 - Fail-closed regression matrix; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-3 - Release smoke fallback coverage; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-4 - Alpha gate wiring; Depends on: SL-1, SL-2, SL-3; Blocks: SL-5; Parallel-safe: no
- SL-5 - Runbook and contract synthesis; Depends on: SL-1, SL-2, SL-3, SL-4; Blocks: P34; Parallel-safe: no

Lane DAG:

```text
P28 + P30 + P31 + P32
  -> SL-0
       -> SL-1 --.
       -> SL-2 ----> SL-4 -> SL-5 -> P34
       -> SL-3 --'
```

## Lanes

### SL-0 - Production Matrix Fixture Helpers

- **Scope**: Extend the existing multi-repo test fixture so P33 tests can build realistic
  repos, linked worktrees, git mutations, status calls, and readiness edge cases without
  duplicating setup code.
- **Owned files**: `tests/fixtures/multi_repo.py`
- **Interfaces provided**: `build_production_matrix(tmp_path)` or equivalent;
  linked-worktree helper returning the worktree path and registered source path;
  git helpers for commit, branch checkout, revert, rename/delete, and missing-index
  setup; `TestServerHandle.call_tool("get_status", {})`
- **Interfaces consumed**: `build_temp_repo()`, `boot_test_server()`,
  `mcp_server.cli.tool_handlers.handle_get_status`, P27 readiness response schema, P32
  repo-scoped runtime status
- **Parallel-safe**: no
- **Tasks**:
  - test: Add fixture self-tests only if helper behavior is not naturally covered by
    SL-1 and SL-2.
  - impl: Add a compact production matrix dataclass with repo paths, repo ids, unique
    search tokens, unique symbol names, and git branch/commit helper methods.
  - impl: Add a linked-worktree helper that registers the source repo and returns a
    sibling worktree path suitable for unsupported-worktree assertions.
  - impl: Extend `TestServerHandle.call_tool()` to dispatch `get_status` through
    `handle_get_status()` using the same dispatcher and resolver as other tools.
  - verify: `uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py -v --no-cov`

### SL-1 - Unrelated Repo Isolation Matrix

- **Scope**: Add the positive production matrix proving two unrelated repositories remain
  isolated across search, symbol lookup, reindex, watcher events, and status.
- **Owned files**: `tests/test_multi_repo_production_matrix.py`
- **Interfaces provided**: IF-0-P33-1 positive unrelated-repo evidence; isolated
  `search_code`, `symbol_lookup`, `reindex`, watcher, and `get_status` assertions
- **Interfaces consumed**: SL-0 production fixture helpers; P27 ready readiness schema;
  P32 runtime feature status; existing `search_code`, `symbol_lookup`, and `reindex`
  tool handlers
- **Parallel-safe**: yes
- **Tasks**:
  - test: Create two unrelated repos with distinct Python symbols and tokens, boot the
    in-process server, and assert each repo returns only its own search and lookup
    results.
  - test: Assert `get_status` returns one row per registered repo with `readiness:
    "ready"` and repo-scoped feature availability fields from P32.
  - test: Mutate one repo on the tracked branch, run `reindex`, and assert the other
    repo's results and readiness are unchanged.
  - test: With watchers enabled, exercise create/modify/delete or rename events in one
    repo and assert dispatcher mutations resolve through that repo's `RepoContext`.
  - impl: Keep the test data lexical-only and Python-only unless an existing fixture
    makes broader language coverage free.
  - verify: `uv run pytest tests/test_multi_repo_production_matrix.py -v --no-cov`

### SL-2 - Fail-Closed Regression Matrix

- **Scope**: Add the negative matrix proving unsupported, stale, wrong-branch, missing,
  force-push, rename/delete/revert, and wrong-artifact states block unsafe indexed use.
- **Owned files**: `tests/test_multi_repo_failure_matrix.py`
- **Interfaces provided**: IF-0-P33-1 negative regression evidence for same-repo
  worktree rejection, branch drift, stale/missing index fallback, incremental repair,
  revert/rename/delete behavior, force-push recovery, and wrong-artifact rejection
- **Interfaces consumed**: SL-0 fixture helpers; P27 `RepositoryReadinessState`; P28
  `index_unavailable` response shape; P30 `GitAwareIndexManager` and `RefPoller`
  contracts; P31 `IndexArtifactDownloader.validate_artifact_identity()`; P32
  dispatcher mutation isolation
- **Parallel-safe**: yes
- **Tasks**:
  - test: Register a source repo, create a linked git worktree from it, and assert
    `search_code` and `symbol_lookup` on the worktree return `index_unavailable` with
    `safe_fallback: "native_search"` and `readiness.state == "unsupported_worktree"`.
  - test: Assert `reindex` against the linked worktree returns the unsupported-worktree
    mutation error without dispatching against the registered source index.
  - test: Switch a registered repo to a non-tracked branch and assert query tools fail
    closed with `readiness.state == "wrong_branch"`.
  - test: Remove or move the repo index DB and assert query tools return
    `missing_index` or `index_empty` as `index_unavailable`, not empty results.
  - test: Cover tracked-branch revert, rename/delete, and normal incremental repair
    through a small end-to-end git mutation sequence, asserting old symbols disappear
    and new or restored symbols match the durable SQLite index.
  - test: Cover force-push detection by asserting non-ancestor ref movement schedules a
    full rescan path rather than a normal incremental sync.
  - test: Feed a wrong repo id, wrong tracked branch, wrong commit, or wrong semantic
    profile artifact into the artifact validator and assert installation is rejected
    unless the existing unsafe override path is explicit.
  - impl: Reuse existing unit-level helpers from P27-P32 where possible instead of
    copying lower-level setup into the matrix.
  - verify: `uv run pytest tests/test_multi_repo_failure_matrix.py -v --no-cov`

### SL-3 - Release Smoke Fallback Coverage

- **Scope**: Extend release smoke so package and container qualification exercise both a
  ready indexed MCP path and an unindexed fallback path.
- **Owned files**: `scripts/release_smoke.py`, `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: IF-0-P33-4 release smoke fallback evidence; updated smoke
  contract tests for CLI flags, Makefile commands, and fallback assertions
- **Interfaces consumed**: SL-0 fixture helpers; P28 `index_unavailable` response shape;
  current `release-smoke` and `release-smoke-container` Makefile targets; production
  Docker image entrypoints
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update `tests/smoke/test_release_smoke_contract.py` to require the smoke script
    to check `index_unavailable`, `safe_fallback`, `native_search`, and `get_status`.
  - impl: Extend `smoke_stdio()` so it keeps the existing ready indexed repo assertion
    and also queries an unindexed or unregistered fixture path, asserting fail-closed
    fallback guidance.
  - impl: Extend `smoke_container()` to verify MCP readiness and the same unindexed
    fallback contract from the production image using only files and env vars available
    inside the container smoke harness.
  - impl: Keep semantic search disabled in smoke paths unless the smoke explicitly tests
    semantic unavailability metadata.
  - verify: `uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `make -n release-smoke release-smoke-container`

### SL-4 - Alpha Gate Wiring

- **Scope**: Add a named P33 alpha gate command and wire it into required CI/release
  qualification without making informational jobs blockers.
- **Owned files**: `Makefile`, `.github/workflows/ci-cd-pipeline.yml`,
  `.github/workflows/release-automation.yml`, `.github/workflows/container-registry.yml`
- **Interfaces provided**: IF-0-P33-5 `make alpha-production-matrix`; CI job
  `Alpha Gate - Production Multi-Repo Matrix`; `alpha-release-gates` dependency on the
  P33 matrix
- **Interfaces consumed**: SL-1, SL-2, and SL-3 verification commands; existing alpha
  gate names and required-gates aggregator pattern
- **Parallel-safe**: no
- **Tasks**:
  - test: Use `make -n alpha-production-matrix alpha-release-gates release-smoke release-smoke-container`
    to validate command wiring without executing the full gate during planning or review.
  - impl: Add `alpha-production-matrix` to `.PHONY`, help text, and the
    `alpha-release-gates` dependency list.
  - impl: Have `alpha-production-matrix` run the focused P33 matrix and the already
    relevant P27-P32 contract files:
    `tests/test_multi_repo_production_matrix.py`,
    `tests/test_multi_repo_failure_matrix.py`, `tests/test_repository_readiness.py`,
    `tests/test_tool_readiness_fail_closed.py`, `tests/test_git_index_manager.py`,
    `tests/test_ref_poller_edges.py`, `tests/test_rename_atomicity.py`,
    `tests/test_artifact_download.py`, and `tests/smoke/test_release_smoke_contract.py`.
  - impl: Add a required CI job named `Alpha Gate - Production Multi-Repo Matrix` and
    include it in `alpha-required-gates-passed.needs`.
  - impl: Keep release automation invoking `make alpha-release-gates`; update comments
    or job names only if needed so the P33 gate is visible to operators.
  - impl: Leave container scan/sign/publish jobs informational unless an existing release
    contract already treats them as blockers.
  - verify: `make -n alpha-production-matrix alpha-release-gates`

### SL-5 - Runbook And Contract Synthesis

- **Scope**: Update operator-facing release gate documentation so the P33 matrix maps
  directly from CI job name to command, covered contracts, and failure action.
- **Owned files**: `docs/operations/deployment-runbook.md`
- **Interfaces provided**: IF-0-P33-6 runbook mapping; docs decision for P33; handoff
  context for P34 public-alpha closeout
- **Interfaces consumed**: SL-1 positive matrix evidence; SL-2 negative matrix evidence;
  SL-3 release smoke fallback evidence; SL-4 gate names and commands; roadmap P33 exit
  criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Review the final runbook table against Makefile and workflow job names so every
    required job has a concrete operator action and no P33 gate is hidden under a generic
    smoke name.
  - impl: Add `Alpha Gate - Production Multi-Repo Matrix` to the public alpha gate
    checklist with `make alpha-production-matrix` as the command source.
  - impl: State that the gate blocks release on regressions in unrelated multi-repo
    isolation, same-repo worktree rejection, wrong-branch safety, stale/missing index
    fallback, incremental repair, rename/delete/revert, force-push recovery, or
    wrong-artifact rejection.
  - impl: Do not broaden public support claims; P34 remains responsible for full
    outside-developer release docs.
  - verify: `rg -n "Production Multi-Repo Matrix|alpha-production-matrix|same-repo worktree|wrong-artifact" docs/operations/deployment-runbook.md Makefile .github/workflows`

## Verification

Lane-specific verification:

```bash
uv run pytest tests/test_multi_repo_production_matrix.py -v --no-cov
uv run pytest tests/test_multi_repo_failure_matrix.py -v --no-cov
uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov
make -n alpha-production-matrix alpha-release-gates release-smoke release-smoke-container
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/smoke \
  tests/test_multi_repo_*.py \
  tests/test_repository_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_git_index_manager.py \
  tests/test_ref_poller_edges.py \
  tests/test_rename_atomicity.py \
  tests/test_artifact_download.py \
  -v --no-cov

make alpha-production-matrix
make -n alpha-release-gates release-smoke release-smoke-container
```

Full release qualification after the focused gate is green:

```bash
make alpha-release-gates
make release-smoke-container
```

## Acceptance Criteria

- [ ] A production matrix fixture creates two unrelated repos and verifies isolated
      search, symbol lookup, reindex, watcher events, and status.
- [ ] A same-repo linked worktree fixture verifies explicit rejection and safe fallback
      guidance.
- [ ] Branch drift, revert, rename/delete, force-push, missing DB, stale index,
      wrong-artifact, and wrong-branch cases are covered.
- [ ] Container smoke covers MCP readiness and an unindexed-repo fallback path.
- [ ] Release gates fail if any P27-P32 blocker contract regresses.
- [ ] CI job names and runbook gate names map cleanly to operator actions.
- [ ] No missing, stale, wrong-branch, unregistered, or unsupported-worktree index state
      can appear to release gates as an ordinary empty search result.
