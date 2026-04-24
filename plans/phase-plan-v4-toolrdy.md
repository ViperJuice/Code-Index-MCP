# TOOLRDY: Secondary Tool Readiness Hardening

> Plan doc produced by `codex-plan-phase specs/phase-plans-v4.md TOOLRDY`
> on 2026-04-24.
> Source roadmap `specs/phase-plans-v4.md` is tracked and clean in this
> worktree (`git status --short -- specs/phase-plans-v4.md` produced no
> output).

## Context

TOOLRDY is the fourth v4 phase. It depends on GATEPARITY and is the first
v4 code-hardening phase after the public-alpha release cleanup track. It must
not reopen the completed v3 roadmap and must preserve the existing public-alpha
model: one registered worktree per git common directory, tracked/default branch
only, and fail-closed indexed access when repository readiness is not `ready`.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545`.
- `plans/phase-plan-v4-toolrdy.md` did not exist before this planning run.
- Existing staged RELGOV work is already present in the worktree and is out of
  scope for TOOLRDY planning: `plans/phase-plan-v4-relgov.md`,
  `docs/validation/release-governance-evidence.md`, two operations runbooks,
  and release-governance tests.
- PMCP catalog search did not expose a running `code-index-mcp` tool surface in
  this session, so native `rg` and targeted file reads were used for planning.

Current implementation shape:

- `handle_search_code` and `handle_symbol_lookup` already classify non-ready
  repository targets and return `index_unavailable` with
  `safe_fallback: "native_search"` before dispatching.
- `handle_reindex` preserves path sandbox and path/repository conflict checks,
  but only short-circuits `unsupported_worktree`; other non-ready states can
  continue toward dispatcher mutation.
- `handle_write_summaries` and `handle_summarize_sample` path-check
  path-shaped `repository` values, then resolve a context or fall back to the
  passed `sqlite_store`, so unsafe or unresolved repository targets can still
  reach summarization behavior.
- `ReadinessClassifier`, `RepoResolver.classify`, `build_health_row`, and
  `GitAwareIndexManager` already provide the readiness vocabulary this phase
  should consume rather than redefining.

## Interface Freeze Gates

- [ ] IF-0-TOOLRDY-1 - Reindex mutation gate: `handle_reindex` performs
      path sandbox and path/repository conflict checks first, then rejects every
      non-ready `RepositoryReadinessState` before `dispatcher.index_file`,
      `dispatcher.index_directory`, or `rebuild_fts_code` can run.
- [ ] IF-0-TOOLRDY-2 - Secondary mutation response contract: rejected
      `reindex` calls return JSON with `results: []`, `code:
      <readiness.code>`, `tool: "reindex"`, `readiness:
      readiness.to_dict()`, `remediation`, and `mutation_performed: false`;
      they do not advertise `safe_fallback: "native_search"`.
- [ ] IF-0-TOOLRDY-3 - Summary readiness gate: `write_summaries` and
      `summarize_sample` reject non-ready repository/default targets before
      checking LLM credentials, creating summarization writers, opening random
      samples, or persisting summaries.
- [ ] IF-0-TOOLRDY-4 - Explicit path scope contract: `summarize_sample` with
      `paths` keeps `MCP_ALLOWED_ROOTS` enforcement, requires all explicit
      paths to resolve to one ready repository scope, and returns
      `conflicting_path_and_repository` when explicit paths disagree with a
      provided `repository`.
- [ ] IF-0-TOOLRDY-5 - Secondary tool schema contract: STDIO descriptions for
      `reindex`, `write_summaries`, and `summarize_sample` name readiness
      gating and clarify that mutation/summarization failures are structured
      readiness refusals, not native-search fallback instructions.
- [ ] IF-0-TOOLRDY-6 - Durable smoke contract: a fresh repository can be
      registered, reindexed, searched, and inspected for durable SQLite rows
      without relying only on pre-seeded fixture data.

## Lane Index & Dependencies

- SL-0 - Secondary readiness contract tests; Depends on: GATEPARITY; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Handler readiness implementation; Depends on: SL-0; Blocks: SL-3, SL-4, SL-5; Parallel-safe: no
- SL-2 - Tool schema and description contract; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-3 - Multi-repo secondary failure matrix; Depends on: SL-1; Blocks: SL-4, SL-5; Parallel-safe: no
- SL-4 - Fresh repository smoke; Depends on: SL-1, SL-3; Blocks: SL-5; Parallel-safe: no
- SL-5 - TOOLRDY evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: TOOLRDY acceptance; Parallel-safe: no

Lane DAG:

```text
GATEPARITY
  -> SL-0
       -> SL-1 -> SL-3 -> SL-4 -> SL-5 -> TOOLRDY acceptance
       -> SL-2 ----------------^
```

## Lanes

### SL-0 - Secondary Readiness Contract Tests

- **Scope**: Freeze the secondary-tool readiness behavior before changing the
  handlers.
- **Owned files**: `tests/test_tool_readiness_fail_closed.py`,
  `tests/test_repository_readiness.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-TOOLRDY-1,
  IF-0-TOOLRDY-2, IF-0-TOOLRDY-3, and the existing readiness-state vocabulary
- **Interfaces consumed**: pre-existing `RepositoryReadinessState`,
  `RepositoryReadiness.to_dict()`, `RepoResolver.classify`, and branch-drift
  readiness behavior from P27-P30
- **Parallel-safe**: no
- **Tasks**:
  - test: Add parametrized `handle_reindex` tests covering
    `unregistered_repository`, `missing_index`, `index_empty`, `stale_commit`,
    `wrong_branch`, `index_building`, and `unsupported_worktree`, asserting no
    dispatcher or store mutation is called.
  - test: Add parametrized `handle_write_summaries` and
    `handle_summarize_sample` tests covering the same non-ready states,
    asserting lazy summarizer and writer construction are not reached.
  - test: Add precedence tests proving `path_outside_allowed_roots` and
    `conflicting_path_and_repository` still win before readiness refusals.
  - impl: Reuse the local fake resolver/readiness helpers already in
    `tests/test_tool_readiness_fail_closed.py`; extend
    `tests/test_repository_readiness.py` or `tests/test_git_index_manager.py`
    only if a missing readiness/remediation invariant is exposed.
  - verify: `uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov`

### SL-1 - Handler Readiness Implementation

- **Scope**: Apply the shared readiness gate to the secondary handlers without
  changing dispatcher internals.
- **Owned files**: `mcp_server/cli/tool_handlers.py`
- **Interfaces provided**: IF-0-TOOLRDY-1 through IF-0-TOOLRDY-4 as handler
  behavior
- **Interfaces consumed**: SL-0 tests; pre-existing `_classify_ctx`,
  `_resolve_ctx`, `_allowed_roots`, `_path_within_allowed`, `_looks_like_path`,
  `_index_unavailable_response`, and `_unsupported_worktree_response`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 secondary-tool tests first and confirm they fail on the
    current handler behavior.
  - impl: Add one small secondary readiness refusal helper for mutation and
    summarization tools, keeping query-tool `index_unavailable` behavior
    unchanged.
  - impl: In `handle_reindex`, preserve current sandbox and conflict
    precedence, then reject every non-ready readiness state before resolving
    `active_store`, choosing `target_path`, calling dispatcher methods, or
    rebuilding FTS rows.
  - impl: In `handle_write_summaries`, classify the repository/default scope
    before summarizer availability checks and reject non-ready targets without
    falling back to the global `sqlite_store`.
  - impl: In `handle_summarize_sample`, keep per-path sandbox checks, classify
    explicit path scope, reject paths that do not share one ready repository
    context, and reject a path/repository mismatch with
    `conflicting_path_and_repository`.
  - impl: Preserve existing ready-repo behavior and legacy no-resolver fallback
    only when the resolver cannot classify at all.
  - verify: `uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_handler_path_sandbox.py tests/integration/test_multi_repo_server.py -v --no-cov`

### SL-2 - Tool Schema and Description Contract

- **Scope**: Align the STDIO tool descriptions and schema tests with the new
  secondary-tool readiness contract.
- **Owned files**: `mcp_server/cli/stdio_runner.py`,
  `tests/test_stdio_tool_descriptions.py`, `tests/docs/test_p6b_sl3.py`
- **Interfaces provided**: IF-0-TOOLRDY-5
- **Interfaces consumed**: SL-0 response contract; existing P7 repository
  schema alignment contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend STDIO description tests so `reindex`, `write_summaries`, and
    `summarize_sample` mention readiness gating and do not tell agents to use
    native search as a fallback for mutation or summarization.
  - impl: Update `_build_tool_list()` descriptions for `reindex`,
    `write_summaries`, and `summarize_sample`; keep the `repository` property
    shape and the existing P7 description contract unchanged.
  - impl: Keep `write_summaries` free of path-sandbox claims unless a path
    argument is actually added.
  - verify: `uv run pytest tests/test_stdio_tool_descriptions.py tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py -v --no-cov`

### SL-3 - Multi-Repo Secondary Failure Matrix

- **Scope**: Prove secondary tools fail closed across the same multi-repo
  states already covered for primary query tools.
- **Owned files**: `tests/test_multi_repo_failure_matrix.py`
- **Interfaces provided**: integration coverage for IF-0-TOOLRDY-1 through
  IF-0-TOOLRDY-4
- **Interfaces consumed**: SL-1 handler behavior; `tests/fixtures/multi_repo.py`
  production matrix; existing P33 query failure matrix helpers
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend the linked-worktree matrix so `reindex`, `write_summaries`,
    and `summarize_sample` all return structured readiness refusals and do not
    mutate registered-repo SQLite files.
  - test: Extend the wrong-branch, stale-commit, and missing-index matrix to
    cover `reindex` plus both summary tools.
  - test: Add an unregistered-repository case for secondary tools using a
    git repo under `MCP_ALLOWED_ROOTS` that is not registered.
  - test: Add explicit `summarize_sample(paths=...)` cases for ready repo,
    unsupported sibling worktree, and path/repository conflict.
  - impl: Reuse `_assert_index_unavailable` only for primary query assertions;
    add a secondary assertion helper that expects `mutation_performed: false`
    or `persisted: false` instead of `safe_fallback`.
  - verify: `uv run pytest tests/test_multi_repo_failure_matrix.py -v --no-cov`

### SL-4 - Fresh Repository Smoke

- **Scope**: Add an end-to-end smoke proving TOOLRDY still permits a real
  register/reindex/search path for a ready repository.
- **Owned files**: `tests/smoke/test_secondary_tool_readiness_smoke.py`
- **Interfaces provided**: IF-0-TOOLRDY-6
- **Interfaces consumed**: SL-1 ready-path handler behavior; SL-3 production
  matrix fixture patterns; `initialize_stateless_services()` boot contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Create a temporary git repository with a unique Python symbol, boot
    stateless services, register the repo, call `reindex` through the tool
    handler, call `search_code` or `symbol_lookup`, and assert the unique
    symbol/path is returned.
  - test: Inspect the repo-scoped SQLite store after reindex and assert durable
    `files` rows exist for the fresh repository rather than only fixture-seeded
    rows.
  - impl: Prefer the existing `tests/fixtures/multi_repo.py` helpers where they
    exercise the real handler path; add only small smoke-local helpers if a
    direct reindex smoke needs fresh, unseeded state.
  - verify: `uv run pytest tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov`

### SL-5 - TOOLRDY Evidence Reducer

- **Scope**: Reduce implementation, schema, integration, and smoke results into
  a single secondary-tool readiness evidence artifact for GACLOSE.
- **Owned files**: `docs/validation/secondary-tool-readiness-evidence.md`
- **Interfaces provided**: TOOLRDY evidence for GACLOSE
- **Interfaces consumed**: SL-0 readiness contract tests; SL-1 handler
  behavior; SL-2 schema contract; SL-3 multi-repo matrix; SL-4 smoke output
- **Parallel-safe**: no
- **Tasks**:
  - test: Add the evidence artifact only after SL-0 through SL-4 have terminal
    outputs.
  - impl: Record the exact secondary-tool response vocabulary, test commands,
    UTC timestamp, repo commit, and whether any non-ready state remains
    intentionally allowed.
  - impl: Record that mutation/summarization refusals are not native-search
    fallback paths and that explicit path scope remains bounded by
    `MCP_ALLOWED_ROOTS`.
  - verify: `rg -n 'TOOLRDY|reindex|write_summaries|summarize_sample|mutation_performed|MCP_ALLOWED_ROOTS|GACLOSE' docs/validation/secondary-tool-readiness-evidence.md`

## Verification

Planning-only status: not run.

Lane-specific commands:

```bash
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov
uv run pytest tests/test_handler_path_sandbox.py tests/integration/test_multi_repo_server.py -v --no-cov
uv run pytest tests/test_stdio_tool_descriptions.py tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py -v --no-cov
uv run pytest tests/test_multi_repo_failure_matrix.py -v --no-cov
uv run pytest tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov
rg -n 'TOOLRDY|reindex|write_summaries|summarize_sample|mutation_performed|MCP_ALLOWED_ROOTS|GACLOSE' docs/validation/secondary-tool-readiness-evidence.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/test_handler_path_sandbox.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/smoke -v --no-cov
make alpha-production-matrix
```

## Acceptance Criteria

- [ ] `reindex` classifies unregistered, wrong-branch, stale/missing-index,
      index-empty, index-building, and unsupported-worktree targets before any
      mutation, with explicit remediation in responses.
- [ ] `write_summaries` and `summarize_sample` reject unsafe repository targets
      before LLM credential checks, writer construction, random sampling, or
      persistence.
- [ ] Explicit path-based summary and reindex invocations keep
      `MCP_ALLOWED_ROOTS` boundaries and path/repository conflict detection.
- [ ] Tests cover secondary-tool behavior for ready repo, unregistered repo,
      unsupported sibling worktree, wrong branch, stale commit, missing index,
      index empty, index building, and explicit path scope.
- [ ] A fresh repository register/reindex/search smoke proves durable SQLite
      rows are created without relying only on seeded fixture rows.
- [ ] STDIO descriptions tell agents how secondary readiness refusals behave
      without changing the primary query-tool `safe_fallback: "native_search"`
      contract.
- [ ] `docs/validation/secondary-tool-readiness-evidence.md` exists and records
      the passing TOOLRDY verification set for GACLOSE.

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v4-toolrdy.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v4-toolrdy.md
  artifact_state: staged
```
