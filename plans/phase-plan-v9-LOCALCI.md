---
phase_loop_plan_version: 1
phase: LOCALCI
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 4bdeba36d7fdba2d849c35deaaadbf73e0223b2272969f0f712c4970d63f55a5
---
# LOCALCI: Local Validation And CI Offload Contract

## Context

LOCALCI is Phase 3 in `specs/phase-plans-v9.md`. PUBNAME and REPOCLEAN are
complete in the canonical `.phase-loop/state.json`, the current phase is
`LOCALCI`, and the worktree was clean at planning time. Legacy
`.codex/phase-loop/` files are compatibility artifacts only and are not used to
supersede the canonical runner state.

Planning observations:

- `specs/phase-plans-v9.md` is tracked and its SHA-256 matches
  `4bdeba36d7fdba2d849c35deaaadbf73e0223b2272969f0f712c4970d63f55a5`.
- `plans/phase-plan-v9-LOCALCI.md` did not exist before this planning run.
- `Makefile` exposes `alpha-*` validation gates, `release-smoke`, and
  container smoke commands, but it does not yet expose the required
  `agent-doctor`, `agent-fast`, `agent-gate`, `agent-full`, `agent-fix`, or
  `agent-affected` targets.
- `.github/workflows/ci-cd-pipeline.yml` currently runs multiple per-PR alpha
  jobs directly on `ubuntu-latest`; `lockfile-check.yml` adds a separate
  dependency-sync job; `container-registry.yml`, `index-management.yml`,
  `mcp-index.yml`, `maintenance.yml`, `index-artifact-management.yml`, and
  `release-automation.yml` each need an explicit protected evidence,
  manual-only, offloaded, or retired classification.
- Existing tests such as `tests/test_p25_release_gates.py` and
  `tests/smoke/test_release_smoke_contract.py` freeze the pre-LOCALCI hosted
  gate shape, so LOCALCI must update those tests with the command contract and
  workflow posture instead of merely adding a parallel Makefile vocabulary.
- `docs/development/TESTING-GUIDE.md` still includes a sample GitHub Actions
  workflow that predates the repo-local/offloaded validation policy.
- No Dagger or remote-host validation helper exists yet; this phase may add a
  repo-local helper, but it must not register self-hosted runners, mutate
  GitHub secrets, or silently fall back to hosted compute when offload is
  unavailable.

Planning boundary:

- LOCALCI may add a small Python validation helper, Makefile targets, command
  contract tests, local/offload docs, workflow posture tests, workflow YAML
  reductions, and one metadata-only evidence artifact.
- LOCALCI must not add coverage thresholds, Codecov/upload behavior, GitHub
  secret changes, self-hosted runner registration, package release dispatch, or
  live cloud provisioning.
- Hosted GitHub Actions may remain as protected evidence or manual orchestration,
  but the normal agent contract must be the repo-local `make agent-*` surface.
- Any optional Dagger or `AGENT_REMOTE_HOST` path must fail closed when
  requested but unavailable, and the failure must not be converted into a green
  hosted check.

## Interface Freeze Gates

- [ ] IF-0-LOCALCI-1 - Local validation contract: `make agent-doctor`,
      `make agent-fast`, `make agent-gate`, `make agent-full`,
      `make agent-fix`, and `make agent-affected` exist with documented,
      machine-tested semantics; `agent-fast` is cheap, offline by default, and
      covers lock sanity, static checks, and focused docs/package truth;
      `agent-gate` is the pre-PR gate and maps to the same substantive suite
      protected CI consumes; optional Dagger or `AGENT_REMOTE_HOST` offload is
      explicit and fail-closed; every workflow is classified as protected
      evidence, manual-only, offloaded, or retired; hosted per-PR work is
      collapsed, path-scoped, or offloaded so it does not duplicate the
      `agent-*` vocabulary; and unavailable offload never becomes a silent
      hosted-runner pass.

## Lane Index & Dependencies

- SL-0 - Repo-local agent command contract; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Offload and local validation documentation; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Hosted workflow orchestration reduction; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - LOCALCI evidence reducer and acceptance verification; Depends on: SL-0, SL-1, SL-2; Blocks: LOCALCI acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> LOCALCI acceptance
```

## Lanes

### SL-0 - Repo-local Agent Command Contract

- **Scope**: Add the required `make agent-*` entrypoints and a small helper
  that keeps cheap, gate, full, fix, affected, doctor, and optional offload
  behavior testable from one repo-local contract.
- **Owned files**: `Makefile`, `scripts/agent_validation.py`, `tests/test_agent_validation.py`
- **Interfaces provided**: `make agent-doctor`, `make agent-fast`,
  `make agent-gate`, `make agent-full`, `make agent-fix`,
  `make agent-affected`; helper contract for changed-path classification,
  offload availability checks, Dagger/remote-host selection, and fail-closed
  exit codes
- **Interfaces consumed**: existing `alpha-dependency-sync`,
  `alpha-format-lint`, `alpha-unit-release-smoke`, `alpha-integration-smoke`,
  `alpha-docs-truth`, `alpha-production-matrix`, `alpha-release-gates`,
  `release-smoke`, `release-smoke-container`, `uv lock --locked`,
  `uv sync --locked --extra dev --link-mode=copy`, `git diff --name-only`,
  `AGENT_REMOTE_HOST`, optional `dagger`, and the roadmap requirement that
  `agent-fast` is offline by default
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_agent_validation.py` to assert every required
    Makefile target exists, `agent-fast` does not require network by default,
    `agent-gate` maps to the substantive pre-PR suite consumed by protected CI,
    `agent-full` includes the heavier/full validation surface, `agent-fix`
    runs only local formatting or deterministic fixes, and `agent-affected`
    routes docs-only diffs to the cheap gate while source, workflow, package,
    lockfile, or unknown diffs route to the pre-PR gate.
  - test: Cover `scripts/agent_validation.py` classification and offload
    decisions with fixture path lists and mocked command availability; tests
    must not require live Dagger, SSH, network, GitHub credentials, or secrets.
  - impl: Add `.PHONY` entries and Makefile targets for `agent-doctor`,
    `agent-fast`, `agent-gate`, `agent-full`, `agent-fix`, and
    `agent-affected`, wiring them through `scripts/agent_validation.py` where
    branching or offload selection is needed.
  - impl: Implement `scripts/agent_validation.py` as a metadata-only helper that
    prints the selected command plan, exits non-zero when an explicitly
    requested Dagger or `AGENT_REMOTE_HOST` offload is unavailable, and never
    prints secret-bearing environment values.
  - impl: Keep existing `alpha-*` targets usable as implementation details
    during the migration, but make the `agent-*` targets the stable contract for
    agents and downstream phases.
  - verify: `uv run pytest tests/test_agent_validation.py -q --no-cov`
  - verify: `make agent-doctor`
  - verify: `make agent-fast`

### SL-1 - Offload And Local Validation Documentation

- **Scope**: Document the `agent-*` command semantics and fail-closed offload
  policy in development and operations docs, replacing stale hosted-first CI
  guidance.
- **Owned files**: `docs/development/agent-validation.md`, `docs/development/TESTING-GUIDE.md`, `docs/operations/user-action-runbook.md`, `tests/docs/test_localci_agent_validation_docs.py`
- **Interfaces provided**: documented command contract, local/offloaded proof
  posture, and operator runbook notes for IF-0-LOCALCI-1
- **Interfaces consumed**: SL-0 command names and helper behavior; existing
  testing guide structure; existing user-action runbook release-gate language;
  roadmap non-goals for no self-hosted runner registration and no GitHub secret
  mutation
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_localci_agent_validation_docs.py` to require the
    development docs to define all six `agent-*` commands, mark `agent-fast` as
    cheap/offline by default, explain `agent-gate` as the pre-PR gate, document
    `AGENT_REMOTE_HOST` and optional Dagger offload as opt-in/fail-closed, and
    forbid silent hosted fallback language.
  - test: Require the runbook to classify human/operator actions that remain
    out of scope: self-hosted runner registration, GitHub secret changes, and
    manual release dispatch.
  - impl: Add `docs/development/agent-validation.md` with command matrix,
    expected runtime/expense posture, local/offload environment variables,
    fail-closed behavior, and examples for docs-only vs source/workflow diffs.
  - impl: Update `docs/development/TESTING-GUIDE.md` so current CI guidance
    points at `make agent-fast`, `make agent-gate`, `make agent-full`, and
    `make agent-affected` instead of the stale sample workflow that expands
    hosted coverage by default.
  - impl: Update `docs/operations/user-action-runbook.md` so release and alpha
    gate references explain the LOCALCI command contract and when protected
    hosted evidence is still expected.
  - verify: `uv run pytest tests/docs/test_localci_agent_validation_docs.py -q --no-cov`
  - verify: `rg -n "agent-doctor|agent-fast|agent-gate|agent-full|agent-fix|agent-affected|AGENT_REMOTE_HOST|Dagger|fail-closed|hosted" docs/development/agent-validation.md docs/development/TESTING-GUIDE.md docs/operations/user-action-runbook.md tests/docs/test_localci_agent_validation_docs.py`

### SL-2 - Hosted Workflow Orchestration Reduction

- **Scope**: Audit every GitHub Actions workflow and reduce hosted per-PR work
  so protected CI consumes the `agent-*` contract rather than duplicating a
  separate alpha-gate vocabulary.
- **Owned files**: `.github/workflows/*.yml`, `.github/workflows/*.yaml`, `tests/test_p25_release_gates.py`, `tests/smoke/test_release_smoke_contract.py`, `tests/test_localci_workflow_posture.py`
- **Interfaces provided**: workflow classification and reduced hosted
  orchestration for IF-0-LOCALCI-1
- **Interfaces consumed**: SL-0 `agent-gate` and `agent-full` command contract;
  SL-1 documented offload policy; existing workflow names and jobs in
  `ci-cd-pipeline.yml`, `container-registry.yml`,
  `index-artifact-management.yml`, `index-management.yml`,
  `lockfile-check.yml`, `maintenance.yml`, `mcp-index.yml`, and
  `release-automation.yml`; existing P25 release-gate and release-smoke tests
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_localci_workflow_posture.py` to load every
    `.github/workflows/*.yml` and `.github/workflows/*.yaml` file and require a
    classification for each workflow: protected evidence, manual-only,
    offloaded, or retired.
  - test: Update `tests/test_p25_release_gates.py` and
    `tests/smoke/test_release_smoke_contract.py` so protected required gates
    are expressed through `make agent-gate` or documented protected evidence,
    and release automation refuses before mutation by running the LOCALCI gate
    before release/container smoke.
  - impl: Collapse, path-scope, offload, or retire hosted per-PR alpha jobs so
    ordinary PRs do not run both the old alpha matrix and the new `agent-*`
    gate vocabulary.
  - impl: Keep manual-only or protected evidence workflows where they are still
    needed, including release dispatch and artifact/index management, but record
    their classification in the workflow tests and the SL-3 evidence artifact.
  - impl: Ensure any workflow path that requests offload fails closed when the
    offload surface is unavailable; do not add fallback hosted jobs that mark
    the same validation green after a failed offload probe.
  - impl: Preserve secret redaction and do not add, rename, or require GitHub
    secrets or self-hosted runner labels in this phase.
  - verify: `uv run pytest tests/test_localci_workflow_posture.py tests/test_p25_release_gates.py tests/smoke/test_release_smoke_contract.py -q --no-cov`
  - verify: `rg -n "make agent-|alpha-release-gates|runs-on:|workflow_dispatch:|pull_request:|AGENT_REMOTE_HOST|offload|continue-on-error" .github/workflows tests/test_localci_workflow_posture.py tests/test_p25_release_gates.py tests/smoke/test_release_smoke_contract.py`

### SL-3 - LOCALCI Evidence Reducer And Acceptance Verification

- **Scope**: Reduce the command contract, documentation, workflow audit, and
  verification output into one metadata-only LOCALCI evidence artifact.
- **Owned files**: `docs/status/localci-validation-contract.md`, `tests/docs/test_localci_validation_contract.py`
- **Interfaces provided**: final IF-0-LOCALCI-1 local validation contract and
  phase acceptance evidence
- **Interfaces consumed**: SL-0 command contract and helper tests; SL-1 docs and
  runbook updates; SL-2 workflow classifications and test results; current
  roadmap requirement that coverage waits for LOCALCI
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_localci_validation_contract.py` to require
    `docs/status/localci-validation-contract.md` to include the audit date,
    all six `agent-*` commands, command-to-suite mapping, docs-only/source diff
    routing rules, offload/fail-closed semantics, workflow classification table,
    hosted-work reduction summary, and verification commands.
  - test: Require the evidence artifact to state that no self-hosted runner
    registration, GitHub secret mutation, coverage threshold change, or hosted
    coverage upload was performed in LOCALCI.
  - impl: Write `docs/status/localci-validation-contract.md` as metadata-only
    evidence. Include summarized command output and workflow classification, but
    do not include tokens, secrets, raw credential values, or private remote-host
    details.
  - impl: If any workflow cannot be confidently classified or any required
    command target is missing, keep execution blocked with
    `blocker_class=contract_bug` rather than treating partial docs as
    acceptance.
  - verify: `uv run pytest tests/docs/test_localci_validation_contract.py tests/docs/test_localci_agent_validation_docs.py tests/test_localci_workflow_posture.py tests/test_agent_validation.py -q --no-cov`
  - verify: `git diff --stat -- Makefile scripts/agent_validation.py tests/test_agent_validation.py docs/development/agent-validation.md docs/development/TESTING-GUIDE.md docs/operations/user-action-runbook.md tests/docs/test_localci_agent_validation_docs.py .github/workflows tests/test_p25_release_gates.py tests/smoke/test_release_smoke_contract.py tests/test_localci_workflow_posture.py docs/status/localci-validation-contract.md tests/docs/test_localci_validation_contract.py`

## Verification

Plan artifact creation is complete once this artifact is written and staged. Do
not execute the commands below during `codex-plan-phase`; run them during
`codex-execute-phase` or manual LOCALCI execution.

Lane-specific checks:

```bash
uv run pytest tests/test_agent_validation.py -q --no-cov
make agent-doctor
make agent-fast
uv run pytest tests/docs/test_localci_agent_validation_docs.py -q --no-cov
uv run pytest tests/test_localci_workflow_posture.py tests/test_p25_release_gates.py tests/smoke/test_release_smoke_contract.py -q --no-cov
uv run pytest tests/docs/test_localci_validation_contract.py tests/docs/test_localci_agent_validation_docs.py tests/test_localci_workflow_posture.py tests/test_agent_validation.py -q --no-cov
```

Whole-phase verification after LOCALCI changes:

```bash
uv sync --locked --extra dev
make agent-doctor
make agent-fast
make agent-gate
make agent-affected
uv run pytest \
  tests/test_agent_validation.py \
  tests/test_localci_workflow_posture.py \
  tests/test_p25_release_gates.py \
  tests/smoke/test_release_smoke_contract.py \
  tests/docs/test_localci_agent_validation_docs.py \
  tests/docs/test_localci_validation_contract.py \
  -q --no-cov
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  Makefile \
  scripts/agent_validation.py \
  tests/test_agent_validation.py \
  docs/development/agent-validation.md \
  docs/development/TESTING-GUIDE.md \
  docs/operations/user-action-runbook.md \
  tests/docs/test_localci_agent_validation_docs.py \
  .github/workflows \
  tests/test_p25_release_gates.py \
  tests/smoke/test_release_smoke_contract.py \
  tests/test_localci_workflow_posture.py \
  docs/status/localci-validation-contract.md \
  tests/docs/test_localci_validation_contract.py \
  plans/phase-plan-v9-LOCALCI.md
```

Full gate when execution time allows:

```bash
make agent-full
```

## Acceptance Criteria

- [ ] Repo-local commands exist with exact names: `make agent-doctor`,
      `make agent-fast`, `make agent-gate`, `make agent-full`,
      `make agent-fix`, and `make agent-affected`.
- [ ] `agent-fast` is cheap and offline: dependency lock sanity, static checks,
      focused docs/package truth checks, and no network by default.
- [ ] `agent-gate` is the pre-PR gate and maps to the same substantive suite CI
      uses, preferably through an optional Dagger path when available.
- [ ] `agent-affected` routes docs-only changes to the cheap gate and source,
      workflow, package, or unknown diffs to the full pre-PR gate.
- [ ] Optional `AGENT_REMOTE_HOST` or equivalent offload is documented for heavy
      validation on owned tailnet compute, fail-closed when unreachable.
- [ ] Every `.github/workflows/*.yml` and `.github/workflows/*.yaml` file is
      audited and classified as protected evidence, manual-only, offloaded, or
      retired.
- [ ] GitHub Actions posture is documented as minimal orchestration/protected
      evidence, with heavy compute either local/offloaded or explicitly
      operator-triggered.
- [ ] The existing hosted per-PR alpha gates are collapsed, path-scoped,
      offloaded, or otherwise reduced so `agent-*` does not merely add a second
      validation vocabulary beside the current hosted matrix.
- [ ] No hosted runner fallback silently converts an unavailable offload host
      into a green check.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `Makefile`, `scripts/agent_validation.py`, `tests/test_agent_validation.py`, `docs/development/agent-validation.md`, `docs/development/TESTING-GUIDE.md`, `docs/operations/user-action-runbook.md`, `tests/docs/test_localci_agent_validation_docs.py`, `.github/workflows/*.yml`, `.github/workflows/*.yaml`, `tests/test_p25_release_gates.py`, `tests/smoke/test_release_smoke_contract.py`, `tests/test_localci_workflow_posture.py`, `docs/status/localci-validation-contract.md`, `tests/docs/test_localci_validation_contract.py`
- evidence paths: `docs/status/localci-validation-contract.md`
- redaction posture: `metadata_only`
- downstream handling: roadmap amendment

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-LOCALCI.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-LOCALCI.md
  artifact_state: staged
```
