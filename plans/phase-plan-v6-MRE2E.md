---
phase_loop_plan_version: 1
phase: MRE2E
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# MRE2E: Multi-Repo Hydration Evidence

## Context

MRE2E is the acceptance phase for the v6 multi-repo hardening roadmap. It
depends on ARTPUB, IDXSAFE, WATCH, and CIFLOW, and it is the first phase that
must prove the full lifecycle from clean state: register, index, publish,
hydrate, reconcile, and query across multiple unrelated repositories.

Current repo state gathered during planning:

- `specs/phase-plans-v6.md` is tracked and its live SHA matches the required
  `032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.
- The checkout is on `main` at `09b777992cd6cd22211c860f1014676250319990`,
  ahead of `origin/main` by four commits after the ARTPUB, WATCH, and CIFLOW
  closeout work. `plans/phase-plan-v6-MRE2E.md` did not exist before this run.
- Multi-repo fixture and server coverage already exists in
  `tests/fixtures/multi_repo.py`, `tests/test_multi_repo_production_matrix.py`,
  `tests/test_multi_repo_failure_matrix.py`, and
  `tests/integration/test_multi_repo_server.py`, but there is no dedicated
  `tests/integration/test_multi_repo_hydration.py` that proves
  `register -> index -> publish -> hydrate -> reconcile -> query` across at
  least two repositories from clean workspace state.
- `tests/test_artifact_download.py` already proves fail-closed direct-publish
  restore for a single repository, and
  `tests/test_multi_repo_artifact_coordinator.py` plus
  `tests/test_artifact_commands.py` already cover local-first workspace
  commands, but they stop short of surfacing the metadata, checksum, branch,
  commit, schema, and semantic-profile validation evidence that MRE2E must
  report after hydration.
- `mcp_server/artifacts/multi_repo_artifact_coordinator.py` currently records
  `artifact_health="prepared"` after `publish_workspace()` and `artifact_health`
  based on local file presence after `fetch_workspace()` or
  `reconcile_workspace()`, but the result details do not yet preserve the full
  validation story that the roadmap exit criteria require.
- `mcp_server/cli/artifact_commands.py` already exposes
  `workspace-status`, `publish-workspace`, `fetch-workspace`, and
  `reconcile-workspace`, so MRE2E should reuse those surfaces instead of
  inventing a parallel operator path.
- There is no `docs/validation/mre2e-evidence.md` yet. Existing
  `docs/validation/` evidence artifacts provide the format to reuse for this
  phase's supported deployment-shape and beta-limitations record.

## Interface Freeze Gates

- [ ] IF-0-MRE2E-1 - Fresh-state multi-repo lifecycle harness:
      a deterministic integration harness registers at least two unrelated
      repositories, indexes the tracked/default branch repository, publishes
      and hydrates artifact state into a clean local workspace, reconciles the
      registry, and proves add, modify, delete, and rename behavior reaches
      `ready`.
- [ ] IF-0-MRE2E-2 - Wrong-branch non-mutation contract:
      a repository on a non-tracked branch fails closed for query and artifact
      lifecycle actions without mutating the tracked repository's index rows,
      registry state, or ready query results.
- [ ] IF-0-MRE2E-3 - Hydration validation surfacing contract:
      workspace publish, fetch, and reconcile results preserve and expose the
      metadata, checksum, branch, commit, schema-version, and
      semantic-profile evidence needed to prove a hydrated artifact passed
      validation instead of merely restoring local files.
- [ ] IF-0-MRE2E-4 - Evidence and beta-limitations contract:
      `docs/validation/mre2e-evidence.md` and
      `docs/guides/artifact-persistence.md` record the exact supported
      deployment shape for this phase, the deterministic local GitHub/CLI mock
      strategy used in CI, the optional live-operator validation boundary, and
      the remaining beta limitations without widening into MRREADY rollout
      claims.

## Lane Index & Dependencies

- SL-0 - MRE2E contract and evidence freeze; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Fresh-state hydration harness and fixture extensions; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Workspace artifact coordinator and CLI truth; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Query and readiness acceptance matrix; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: yes
- SL-4 - MRE2E validation evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: MRE2E acceptance; Parallel-safe: no

## Lanes

### SL-0 - MRE2E Contract And Evidence Freeze

- **Scope**: Freeze the required MRE2E lifecycle, validation, and evidence
  artifact shape before changing fixtures, coordinator behavior, or docs.
- **Owned files**: `tests/docs/test_mre2e_evidence_contract.py`
- **Interfaces provided**: IF-0-MRE2E-1, IF-0-MRE2E-2, IF-0-MRE2E-3,
  IF-0-MRE2E-4
- **Interfaces consumed**: `specs/phase-plans-v6.md`,
  `tests/fixtures/multi_repo.py`,
  `tests/test_multi_repo_artifact_coordinator.py`,
  `tests/test_artifact_commands.py`,
  `tests/test_artifact_download.py`,
  `tests/test_multi_repo_production_matrix.py`,
  `tests/test_multi_repo_failure_matrix.py`,
  `tests/integration/test_multi_repo_server.py`,
  `docs/guides/artifact-persistence.md`, existing `docs/validation/` evidence
  artifacts
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated docs-contract test that requires a canonical
    `docs/validation/mre2e-evidence.md` artifact and asserts that it records
    the exact two-repository lifecycle, wrong-branch fail-closed row,
    validation fields, commands, commit, and beta limitations that this phase
    must prove.
  - test: Require the evidence artifact to distinguish deterministic CI-safe
    local GitHub/CLI mock validation from any optional live-operator
    confirmation path, so MRE2E does not imply that routine CI uses live
    publication.
  - test: Freeze the expectation that downstream MRREADY consumes this artifact
    instead of a new ad hoc status format or an unstructured test log dump.
  - impl: Keep this lane test-only; it defines the MRE2E contract for SL-1
    through SL-4 without mutating runtime behavior directly.
  - verify: `uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov`

### SL-1 - Fresh-State Hydration Harness And Fixture Extensions

- **Scope**: Build the end-to-end fresh-state test harness that proves the
  multi-repo lifecycle from clean registration through hydrated query results.
- **Owned files**: `tests/integration/test_multi_repo_hydration.py`, `tests/fixtures/multi_repo.py`
- **Interfaces provided**: IF-0-MRE2E-1, fixture helpers consumed by SL-2 and
  SL-3
- **Interfaces consumed**: SL-0 MRE2E contract assertions; existing
  `build_temp_repo`, `build_production_matrix`, `boot_test_server`, and direct
  SQLite seeding helpers; workspace artifact command surface owned by
  `mcp_server/cli/artifact_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated integration test that registers at least two
    unrelated repositories, proves the tracked/default branch repository can be
    indexed and published, wipes or recreates clean local artifact state,
    hydrates via the workspace lifecycle surface, reconciles registry state,
    and reaches `ready`.
  - test: Extend the fixture helpers only as needed to support clean hydration
    setup, deterministic fake artifact download payloads, and post-hydration
    add, modify, delete, and rename assertions without changing global cwd or
    introducing live-network coupling.
  - test: Prove that hydrated query results reflect the reconciled file set
    after tracked-branch changes, not only the original seed content.
  - impl: Keep the harness local and deterministic; normal CI should rely on
    the existing test fixtures and mocked artifact transport, with any live
    GitHub validation deferred to the evidence path described in SL-4.
  - verify: `uv run pytest tests/integration/test_multi_repo_hydration.py -q --no-cov`

### SL-2 - Workspace Artifact Coordinator And CLI Truth

- **Scope**: Make the workspace publish, fetch, reconcile, and status surfaces
  report truthful per-repo hydration validation details instead of only local
  file presence.
- **Owned files**: `mcp_server/artifacts/multi_repo_artifact_coordinator.py`, `mcp_server/cli/artifact_commands.py`, `tests/test_multi_repo_artifact_coordinator.py`, `tests/test_artifact_commands.py`
- **Interfaces provided**: IF-0-MRE2E-3
- **Interfaces consumed**: SL-0 MRE2E assertions; SL-1 fresh-state harness
  expectations; `IndexArtifactUploader.create_metadata(...)`,
  `IndexArtifactDownloader.download_latest(...)`,
  `WorkspaceArtifactManifest`, existing registry artifact-state fields
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend coordinator and CLI tests so publish, fetch, reconcile, and
    workspace-status rows assert exact `artifact_backend`, `artifact_health`,
    `last_published_commit`, `last_recovered_commit`, and validation-detail
    output rather than only success booleans.
  - test: Require fetch results to surface the metadata and validation reasons
    that prove checksum, branch, commit, schema, and semantic-profile checks
    passed or were explicitly overridden.
  - impl: Thread the downloader's validation outcome and recovered artifact
    identity through `MultiRepoArtifactCoordinator.fetch_workspace()` and the
    CLI formatting layer so hydrated evidence can be recorded without parsing
    logs.
  - impl: Preserve the current local-first wording for `publish-workspace`,
    while making the result details explicit about whether the repo is merely
    prepared locally, hydrated from a validated artifact, or still missing a
    ready local index.
  - impl: Keep this lane scoped to lifecycle truth surfacing; do not broaden it
    into a new remote provider model or MRREADY rollout policy.
  - verify: `uv run pytest tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov`
  - verify: `rg -n "artifact_health|artifact_backend|last_published_commit|last_recovered_commit|validation_reasons|publish_workspace|fetch_workspace|reconcile_workspace|workspace-status" mcp_server/artifacts/multi_repo_artifact_coordinator.py mcp_server/cli/artifact_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py`

### SL-3 - Query And Readiness Acceptance Matrix

- **Scope**: Prove that hydrated state and wrong-branch refusals are reflected
  in the real query/readiness surfaces, and apply only the narrow surfacing fix
  needed if the fresh-state harness exposes stale state.
- **Owned files**: `mcp_server/dispatcher/cross_repo_coordinator.py`, `mcp_server/health/repository_readiness.py`, `mcp_server/storage/repository_registry.py`, `tests/test_multi_repo_production_matrix.py`, `tests/test_multi_repo_failure_matrix.py`, `tests/integration/test_multi_repo_server.py`
- **Interfaces provided**: IF-0-MRE2E-1, IF-0-MRE2E-2
- **Interfaces consumed**: SL-0 MRE2E assertions; SL-1 hydration harness; SL-2
  workspace artifact truth; existing fail-closed readiness vocabulary
  (`ready`, `wrong_branch`, `stale_commit`, `missing_index`,
  `unsupported_worktree`, `unregistered_repository`)
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend the production matrix and integration server tests so
    post-hydration search and symbol lookup prove the tracked repository shows
    reconciled add, modify, delete, and rename behavior while unrelated
    repositories remain isolated.
  - test: Extend the failure matrix so a wrong-branch repository fails closed
    for query and artifact lifecycle operations without mutating the tracked
    repository's SQLite rows, indexed commit bookkeeping, or ready results.
  - impl: If the fresh-state harness exposes stale readiness or stale
    repository-state caching, apply the smallest fix in the coordinator,
    readiness classifier, or registry update path needed to surface the real
    hydrated state without broadening fallback or auto-mutation behavior.
  - impl: Preserve the existing fail-closed vocabulary and remediation wording;
    MRE2E should prove the acceptance matrix, not invent a new status taxonomy.
  - verify: `uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov`
  - verify: `rg -n "ready|wrong_branch|stale_commit|missing_index|unsupported_worktree|unregistered_repository|cross_repo|update_indexed_commit|update_git_state" mcp_server/dispatcher/cross_repo_coordinator.py mcp_server/health/repository_readiness.py mcp_server/storage/repository_registry.py tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py`

### SL-4 - MRE2E Validation Evidence Reducer

- **Scope**: Reduce the frozen harness, lifecycle truth, and readiness matrix
  into the canonical MRE2E evidence artifact and the exact supported
  deployment-shape documentation.
- **Owned files**: `docs/validation/mre2e-evidence.md`, `docs/guides/artifact-persistence.md`
- **Interfaces provided**: IF-0-MRE2E-4
- **Interfaces consumed**: SL-0 contract assertions; SL-1 fresh-state
  lifecycle results; SL-2 workspace validation details; SL-3 query/readiness
  matrix results; existing `docs/validation/` evidence format
- **Parallel-safe**: no
- **Tasks**:
  - test: Write the MRE2E evidence artifact only after SL-1 through SL-3 have
    frozen the actual command set, validation details, and fail-closed rows.
  - impl: Create `docs/validation/mre2e-evidence.md` as the canonical record of
    the two-repository lifecycle, the wrong-branch non-mutation proof, the
    exact commands used, the commit under test, and the artifact validation
    fields that passed.
  - impl: Update `docs/guides/artifact-persistence.md` so it names the supported
    MRE2E deployment shape precisely: deterministic local GitHub/CLI mock for
    CI acceptance, optional live-operator validation only when explicitly
    needed, and the remaining multi-repo beta limits that still defer to
    MRREADY.
  - impl: Keep the docs scoped to evidence and supported shape; do not widen
    this phase into rollout readiness, benchmark publication, or release
    dispatch.
  - verify: `uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov`
  - verify: `rg -n "MRE2E|register|publish|hydrate|reconcile|wrong_branch|checksum|schema_version|semantic_profile|beta|mock|live operator" docs/validation/mre2e-evidence.md docs/guides/artifact-persistence.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual MRE2E execution.

Lane-specific contract checks:

```bash
uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov
uv run pytest tests/integration/test_multi_repo_hydration.py -q --no-cov
uv run pytest tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov
uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov
rg -n "artifact_health|artifact_backend|last_published_commit|last_recovered_commit|validation_reasons|publish_workspace|fetch_workspace|reconcile_workspace|workspace-status|ready|wrong_branch|stale_commit|missing_index|unsupported_worktree|unregistered_repository" \
  mcp_server/artifacts/multi_repo_artifact_coordinator.py \
  mcp_server/cli/artifact_commands.py \
  mcp_server/dispatcher/cross_repo_coordinator.py \
  mcp_server/health/repository_readiness.py \
  mcp_server/storage/repository_registry.py \
  tests/test_multi_repo_artifact_coordinator.py \
  tests/test_artifact_commands.py \
  tests/test_multi_repo_production_matrix.py \
  tests/test_multi_repo_failure_matrix.py \
  tests/integration/test_multi_repo_server.py
```

Whole-phase regression commands:

```bash
uv run pytest tests/docs/test_mre2e_evidence_contract.py tests/integration/test_multi_repo_hydration.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov
make test
git status --short --branch
```

## Acceptance Criteria

- [ ] An end-to-end test registers at least two unrelated repositories and
      proves the tracked/default branch repository can be indexed, published,
      hydrated, reconciled, and queried from clean local state.
- [ ] The tracked/default branch repository proves add, modify, delete, and
      rename behavior and returns to `ready` after reconcile.
- [ ] A wrong-branch repository fails closed without mutating the tracked
      repository's index rows, registry state, or ready query results.
- [ ] A hydrated artifact surfaces passing metadata, checksum, branch, commit,
      schema, and semantic-profile validation evidence rather than only local
      file restoration.
- [ ] Search and symbol lookup results reflect the hydrated and reconciled file
      changes while unrelated repositories remain isolated.
- [ ] `docs/validation/mre2e-evidence.md` records the exact supported
      deployment shape, commands, commit, outcomes, and remaining beta
      limitations for the accepted MRE2E workflow.
- [ ] MRE2E stays scoped to multi-repo hydration acceptance and evidence; any
      broader rollout-gating or status-language work is deferred to MRREADY.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-MRE2E.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-MRE2E.md
  artifact_state: staged
```
