---
phase_loop_plan_version: 1
phase: MRREADY
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# MRREADY: Multi-Repo Rollout Readiness

## Context

MRREADY is the final phase in the v6 multi-repo hardening roadmap. It consumes
the completed MRE2E acceptance evidence and turns that hardening record into a
single rollout gate that an operator can use when deploying the stable package
across many local repositories on one machine.

Current repo state gathered during planning:

- `specs/phase-plans-v6.md` is tracked and clean in this worktree, and its live
  SHA matches the required
  `032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.
- The checkout is on `main` at `17b8742cc030a5cd42830604bbc7323ca2e622cf`,
  clean in content before this plan write, and ahead of `origin/main` by five
  commits after ARTPUB, IDXSAFE, WATCH, CIFLOW, and MRE2E.
- `plans/phase-plan-v6-MRREADY.md` did not exist before this planning run.
- `docs/validation/mre2e-evidence.md` now exists and intentionally defers any
  broader rollout posture, operator sequencing, and final deployment verdict to
  MRREADY.
- `RepositoryReadinessState` and `build_health_row(...)` already expose
  fail-closed readiness details such as `ready`, `missing_index`,
  `stale_commit`, `wrong_branch`, `index_building`, and
  `unsupported_worktree`, while multi-repo artifact coordination already
  exposes `artifact_health` values such as `ready`, `local_only`,
  `publish_failed`, `wrong_branch`, and `stale_commit`.
- The current operator surfaces still split that truth across multiple places:
  `mcp-index repository list -v` prints readiness and artifact health on
  separate lines, `mcp-index repository status` still focuses on older
  git/index basics, and `mcp-index artifact workspace-status` dumps raw
  key/value lifecycle rows without a single rollout-facing status summary.
- There is no current operator-facing way to distinguish an ordinary
  `stale_commit` from an IDXSAFE-style partial incremental failure without
  reading logs, even though `RepositoryInfo.staleness_reason` already exists as
  a persistable runtime field that MRREADY can reuse for a narrow surfacing fix
  instead of inventing a broad new runtime contract.
- Public docs already preserve the multi-repo beta boundary in `README.md`,
  `AGENTS.md`, `docs/guides/artifact-persistence.md`, and the operations
  runbooks, but there is no dedicated MRREADY docs-contract test and no final
  readiness note artifact that says whether rollout is broad-ready,
  controlled-rollout-only, or needs another hardening pass.

## Interface Freeze Gates

- [ ] IF-0-MRREADY-1 - Rollout status surface contract:
      `mcp-index repository list -v`, `mcp-index repository status`,
      `mcp-index artifact workspace-status`, and any shared health-row payload
      they depend on expose one deterministic operator-facing rollout status
      derived from readiness, artifact lifecycle truth, and any persisted
      partial-failure marker. The surfaced vocabulary must distinguish at
      least `ready`, `local_only`, `publish_failed`, `wrong_branch`,
      `partial_index_failure`, and query-path `index_unavailable` without log
      inspection.
- [ ] IF-0-MRREADY-2 - Narrow partial-failure persistence contract:
      MRREADY does not rewrite the P28/MRE2E query refusal model, but if the
      existing readiness plus artifact fields cannot distinguish
      `partial_index_failure`, the minimal runtime repair persists that verdict
      through existing repository metadata (for example
      `RepositoryInfo.staleness_reason`) so status/reporting surfaces can name
      it explicitly and clear it after a successful reindex or hydrate.
- [ ] IF-0-MRREADY-3 - Operator recovery contract:
      rollout-facing docs and CLI/status output map every non-ready posture to
      exact operator actions for failed publish, stale artifact or commit,
      wrong branch, missing local index, and partial incremental failure, while
      preserving `index_unavailable` plus `safe_fallback: "native_search"` as
      the query-surface fail-closed rule.
- [ ] IF-0-MRREADY-4 - Final rollout decision contract:
      a canonical MRREADY readiness note under `docs/validation/` cites MRE2E
      evidence, records the commands and commit used for MRREADY verification,
      preserves the beta boundary around multi-repo and STDIO where it still
      applies, and states exactly one verdict: ready for broad multi-repo
      deployment, controlled rollout only, or another hardening pass required.

## Lane Index & Dependencies

- SL-0 - MRREADY contract freeze tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Rollout status surfacing and narrow persistence; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Public docs and operator runbook reducer; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Final rollout readiness note; Depends on: SL-0, SL-1, SL-2; Blocks: MRREADY acceptance; Parallel-safe: no

## Lanes

### SL-0 - MRREADY Contract Freeze Tests

- **Scope**: Freeze the rollout-status vocabulary, recovery guidance, and final
  readiness-note shape before changing any status surface or operator docs.
- **Owned files**: `tests/docs/test_mrready_rollout_contract.py`
- **Interfaces provided**: IF-0-MRREADY-1, IF-0-MRREADY-2,
  IF-0-MRREADY-3, IF-0-MRREADY-4
- **Interfaces consumed**: `specs/phase-plans-v6.md`,
  `docs/validation/mre2e-evidence.md`, `README.md`, `AGENTS.md`,
  `docs/guides/artifact-persistence.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `docs/operations/artifact-retention.md`,
  `mcp_server/cli/repository_commands.py`,
  `mcp_server/cli/artifact_commands.py`,
  `mcp_server/health/repo_status.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated docs-contract test that requires a canonical
    `docs/validation/mrready-rollout-readiness.md` artifact and asserts that
    it records the exact rollout verdict, commands, commit, MRE2E dependency,
    and remaining beta limitations for MRREADY.
  - test: Freeze the operator-facing status vocabulary so the contract names
    `ready`, `local_only`, `publish_failed`, `wrong_branch`,
    `partial_index_failure`, and `index_unavailable`, while still preserving
    query-only `safe_fallback: "native_search"` semantics where applicable.
  - test: Require rollout docs to distinguish repository/workspace status
    surfaces from query-tool refusal surfaces so MRREADY does not blur a
    health/status row into a search-tool error code.
  - test: Require the final readiness note to cite
    `docs/validation/mre2e-evidence.md` and to route operators through the
    deployment runbook, user-action runbook, and artifact-retention guidance
    rather than leaving recovery as ad hoc log-reading.
  - impl: Keep this lane test-only; it freezes the MRREADY contract for SL-1
    through SL-3 without mutating runtime or docs behavior directly.
  - verify: `uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov`

### SL-1 - Rollout Status Surfacing And Narrow Persistence

- **Scope**: Surface one truthful rollout status across repository and
  workspace status commands, using the smallest runtime persistence repair
  needed to expose `partial_index_failure`.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/storage/repository_registry.py`, `mcp_server/health/repo_status.py`, `mcp_server/artifacts/multi_repo_artifact_coordinator.py`, `mcp_server/cli/repository_commands.py`, `mcp_server/cli/artifact_commands.py`, `tests/test_git_index_manager.py`, `tests/test_health_surface.py`, `tests/test_repository_commands.py`, `tests/test_multi_repo_artifact_coordinator.py`, `tests/test_artifact_commands.py`
- **Interfaces provided**: IF-0-MRREADY-1, IF-0-MRREADY-2
- **Interfaces consumed**: SL-0 MRREADY contract assertions; existing
  `RepositoryReadinessState`; existing `artifact_health` lifecycle vocabulary;
  existing `RepositoryInfo.staleness_reason`; MRE2E workspace validation
  details; IDXSAFE failure semantics that keep `last_indexed_commit` from
  advancing on partial mutation failure
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend repository, workspace, and health-surface tests so operators
    can read one rollout-facing status summary and matching remediation without
    having to infer it from separate readiness, commit-drift, and artifact
    lines.
  - test: Add regression coverage that a failed incremental index update can
    surface as `partial_index_failure` in status/reporting without changing the
    query-surface fail-closed contract from `index_unavailable`.
  - test: Preserve existing happy-path `ready` and multi-repo artifact rows so
    MRREADY remains a surfacing layer, not a topology rewrite.
  - impl: Add a small rollout-status classifier that derives operator-facing
    status from readiness, artifact health, and any persisted
    `staleness_reason`, while leaving query-time readiness/error codes intact.
  - impl: Use the minimal persistence hook needed in `GitAwareIndexManager` and
    registry metadata so partial incremental failures set a durable
    `partial_index_failure` marker and successful reindex/hydrate paths clear
    it.
  - impl: Update `mcp-index repository list -v`,
    `mcp-index repository status`, and `mcp-index artifact workspace-status` to
    print the rollout status, the underlying readiness/artifact facts, and the
    exact next-step guidance for each non-ready posture.
  - impl: Keep this lane narrow: do not invent new search-tool error codes, do
    not widen branch/topology support, and do not add new artifact providers.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov`
  - verify: `rg -n "partial_index_failure|staleness_reason|rollout_status|artifact_health|workspace-status|repository status|repository list" mcp_server/storage/git_index_manager.py mcp_server/storage/repository_registry.py mcp_server/health/repo_status.py mcp_server/artifacts/multi_repo_artifact_coordinator.py mcp_server/cli/repository_commands.py mcp_server/cli/artifact_commands.py tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py`

### SL-2 - Public Docs And Operator Runbook Reducer

- **Scope**: Reduce the frozen rollout-status surface into accurate public
  guidance and operator procedures for deploying many repositories on one
  machine.
- **Owned files**: `README.md`, `AGENTS.md`, `docs/guides/artifact-persistence.md`, `docs/operations/deployment-runbook.md`, `docs/operations/user-action-runbook.md`, `docs/operations/artifact-retention.md`
- **Interfaces provided**: IF-0-MRREADY-3
- **Interfaces consumed**: SL-0 MRREADY contract assertions; SL-1 rollout
  status and remediation surface; `docs/validation/mre2e-evidence.md`; current
  beta/support-boundary wording in README and AGENTS
- **Parallel-safe**: no
- **Tasks**:
  - test: Update docs only after SL-1 freezes the real rollout-status and
    remediation surface.
  - impl: Document the safe deployment sequence for many repositories on one
    machine: register, inspect repository/workspace status, publish or fetch
    when appropriate, reconcile readiness, and verify query-ready status before
    trusting indexed results.
  - impl: Explain recovery for failed publish, stale artifact or commit, wrong
    branch, missing local index, and partial incremental failure, with exact
    command surfaces and the runbook section each posture maps to.
  - impl: Preserve the public beta limitations around multi-repo and STDIO
    wherever they still apply; MRREADY should sharpen rollout truth, not imply
    that every beta caveat disappeared.
  - impl: Update artifact-retention guidance only as needed to explain how
    cleanup policy interacts with multi-repo restore and rollback readiness; do
    not broaden MRREADY into janitor feature work.
  - verify: `rg -n "MRREADY|ready|local_only|publish_failed|wrong_branch|partial_index_failure|index_unavailable|workspace-status|reconcile-workspace|beta" README.md AGENTS.md docs/guides/artifact-persistence.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md docs/operations/artifact-retention.md`

### SL-3 - Final Rollout Readiness Note

- **Scope**: Reduce the surfaced status contract and operator guidance into the
  canonical MRREADY verdict artifact.
- **Owned files**: `docs/validation/mrready-rollout-readiness.md`
- **Interfaces provided**: IF-0-MRREADY-4
- **Interfaces consumed**: SL-0 MRREADY contract assertions; SL-1 rollout
  status and remediation surface; SL-2 public/runbook guidance;
  `docs/validation/mre2e-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write the final readiness note only after SL-1 and SL-2 freeze the
    rollout-status vocabulary, command set, and recovery path names.
  - impl: Create `docs/validation/mrready-rollout-readiness.md` as the
    canonical MRREADY decision record with observed commit, commands run,
    surfaced rollout statuses, remaining beta limitations, and the exact
    verdict: broad deployment ready, controlled rollout only, or another
    hardening pass required.
  - impl: Cite `docs/validation/mre2e-evidence.md` as the upstream acceptance
    proof and explicitly explain any residual caveats that keep the verdict from
    being broader than controlled rollout.
  - impl: Keep this lane as a reducer; it consumes runtime/doc truth and must
    not invent new behavior, new release policy, or new topology claims.
  - verify: `uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov`
  - verify: `rg -n "MRE2E|MRREADY|broad multi-repo deployment|controlled rollout|hardening pass|required commands|Observed commit|beta" docs/validation/mrready-rollout-readiness.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual MRREADY execution.

Lane-specific contract checks:

```bash
uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov
uv run pytest tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov
rg -n "partial_index_failure|staleness_reason|rollout_status|artifact_health|workspace-status|repository status|repository list|index_unavailable" \
  mcp_server/storage/git_index_manager.py \
  mcp_server/storage/repository_registry.py \
  mcp_server/health/repo_status.py \
  mcp_server/artifacts/multi_repo_artifact_coordinator.py \
  mcp_server/cli/repository_commands.py \
  mcp_server/cli/artifact_commands.py \
  README.md \
  AGENTS.md \
  docs/guides/artifact-persistence.md \
  docs/operations/deployment-runbook.md \
  docs/operations/user-action-runbook.md \
  docs/operations/artifact-retention.md \
  docs/validation/mrready-rollout-readiness.md \
  tests/docs/test_mrready_rollout_contract.py \
  tests/test_git_index_manager.py \
  tests/test_health_surface.py \
  tests/test_repository_commands.py \
  tests/test_multi_repo_artifact_coordinator.py \
  tests/test_artifact_commands.py
```

Whole-phase regression commands:

```bash
uv run pytest tests/docs/test_mrready_rollout_contract.py tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov
make alpha-production-matrix
git status --short --branch
```

## Acceptance Criteria

- [ ] CLI/status surfaces distinguish `ready`, `local_only`,
      `publish_failed`, `wrong_branch`, `partial_index_failure`, and
      query-path `index_unavailable` without requiring log inspection.
- [ ] Any narrow runtime persistence added for `partial_index_failure` reuses
      the smallest existing repository-metadata surface possible and clears
      after successful recovery.
- [ ] Operator docs describe the safe deployment sequence for registering,
      validating, hydrating, reconciling, and querying many repositories on one
      machine.
- [ ] Runbooks explain recovery for failed publish, stale artifact or commit,
      wrong branch, missing local index, and partial incremental failure.
- [ ] Public docs preserve the beta limitation around multi-repo and STDIO
      wherever it still applies.
- [ ] `docs/validation/mrready-rollout-readiness.md` states whether the repo is
      ready for broad multi-repo deployment, controlled rollout only, or needs
      another hardening pass, and cites the exact evidence and commands used.
- [ ] MRREADY stays scoped to rollout truth surfacing and operator guidance; it
      does not widen topology support, release dispatch, or artifact-provider
      behavior.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-MRREADY.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-MRREADY.md
  artifact_state: staged
```
