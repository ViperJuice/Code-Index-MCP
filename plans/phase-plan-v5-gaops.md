---
phase_loop_plan_version: 1
phase: GAOPS
roadmap: specs/phase-plans-v5.md
roadmap_sha256: cad74cc0a8ba6c41a82c9efa5b014bc689c5127f25564b3ff3c0f6de0031c130
---
# GAOPS: GA Operational Readiness

## Context

GAOPS is the fifth phase in the v5 GA-hardening roadmap. It depends on
GABASE, GAGOV, and GAE2E, and `.codex/phase-loop/state.json` already records
all three as `complete` while `GAOPS` remains `unplanned`. This phase should
turn the frozen GA checklist, live governance posture, and refreshed E2E
evidence into an operator path that is explicit, testable, and supportable
without relying on project-history knowledge.

Current repo state gathered during planning:

- The checkout is on `main` at `8d08545c15c5`.
- `specs/phase-plans-v5.md` is already staged in this worktree
  (`git status --short -- specs/phase-plans-v5.md` returned
  `A  specs/phase-plans-v5.md`), so it must be treated as the active
  user-owned roadmap baseline.
- The current roadmap bytes hash to
  `cad74cc0a8ba6c41a82c9efa5b014bc689c5127f25564b3ff3c0f6de0031c130`, which
  matches the active phase-loop state and the latest GAE2E artifact lineage.
- Existing v5 plan artifacts for `GABASE`, `GAGOV`, `GASUPPORT`, and `GAE2E`
  are already staged, so `plans/phase-plan-v5-gaops.md` should hand directly
  to `codex-execute-phase` instead of reopening earlier phase scope.
- `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`, and
  `docs/validation/ga-e2e-evidence.md` now exist and should be treated as
  frozen upstream contracts rather than rewritten here.
- `docs/validation/ga-operations-evidence.md` does not exist yet and is the
  canonical new artifact required by this phase.
- `docs/operations/deployment-runbook.md` already contains GABASE/GAGOV
  additions but still mixes older P12-P26 material with newer GA-hardening
  posture, and its preflight section currently shows `bash scripts/preflight_upgrade.sh`
  with no env-file argument even though the wrapper script requires one.
- `docs/operations/user-action-runbook.md` still has no dedicated GAOPS section;
  it currently mentions `GAOPS` only as a downstream owner in the GABASE/GAGOV
  mapping and blocker-routing text.
- `docs/operations/observability-verification.md`,
  `tests/integration/obs/test_obs_smoke.py`, `tests/test_preflight_upgrade.py`,
  and `scripts/preflight_upgrade.sh` already cover real operator procedures and
  should be hardened instead of replaced with a second ops harness.
- `docs/DEPLOYMENT-GUIDE.md` and `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` still
  read like broad generic deployment manuals, including unsupported or
  unverified managed-operation claims (`blue-green deployment`, `Kubernetes`,
  `Helm`, `Docker Swarm`, `multi-region`) that exceed the evidence-backed
  local-first GA contract this roadmap is trying to freeze.

## Interface Freeze Gates

- [ ] IF-0-GAOPS-1 - Operator procedure contract:
      `docs/operations/deployment-runbook.md` and
      `docs/operations/user-action-runbook.md` define explicit GAOPS sections
      for preflight, deployment qualification, rollback, index rebuild,
      incident response, and support triage, and they cite
      `docs/validation/ga-readiness-checklist.md`,
      `docs/validation/ga-governance-evidence.md`,
      `docs/validation/ga-e2e-evidence.md`, and
      `docs/validation/ga-operations-evidence.md` as the canonical decision
      sources.
- [ ] IF-0-GAOPS-2 - Observability and preflight contract:
      `docs/operations/observability-verification.md` and
      `scripts/preflight_upgrade.sh` agree on the exact env-file invocation,
      `/metrics` authentication posture, health/log/metrics verification
      steps, redaction expectations, and escalation boundaries without
      requiring secret values in docs or evidence.
- [ ] IF-0-GAOPS-3 - Deployment-surface support-boundary contract:
      `docs/DEPLOYMENT-GUIDE.md` and `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`
      describe only deployment surfaces, operator responsibilities, and
      rollback/observability expectations that match the current local-first
      product contract, and they distinguish operator-owned infrastructure from
      unsupported hosted or managed-service assumptions.
- [ ] IF-0-GAOPS-4 - Operations evidence provenance contract:
      `docs/validation/ga-operations-evidence.md` is the canonical GAOPS
      artifact and records each validated procedure with one explicit evidence
      mode (`local`, `CI`, or `metadata-only`), plus timestamp, commit,
      artifact/doc source, and any remaining non-GA limitation or operator-only
      assumption.

## Lane Index & Dependencies

- SL-0 - GAOPS contract tests; Depends on: GABASE, GAGOV, GAE2E; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Operator runbook GAOPS hardening; Depends on: SL-0; Blocks: SL-4; Parallel-safe: yes
- SL-2 - Observability and preflight procedure parity; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-3 - Deployment guide support-boundary alignment; Depends on: SL-0, SL-2; Blocks: SL-4; Parallel-safe: yes
- SL-4 - GA operations evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GAOPS acceptance; Parallel-safe: no

## Lanes

### SL-0 - GAOPS Contract Tests

- **Scope**: Freeze the GAOPS operator-procedure, observability, support-boundary,
  and evidence-provenance assertions before editing operational docs.
- **Owned files**: `tests/docs/test_gaops_operations_contract.py`
- **Interfaces provided**: IF-0-GAOPS-1, IF-0-GAOPS-2, IF-0-GAOPS-3,
  IF-0-GAOPS-4
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `docs/operations/observability-verification.md`,
  `docs/DEPLOYMENT-GUIDE.md`, `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`,
  `scripts/preflight_upgrade.sh`, `tests/test_preflight_upgrade.py`,
  `tests/integration/obs/test_obs_smoke.py`,
  `tests/test_deployment_runbook_shape.py`,
  `tests/docs/test_gabase_ga_readiness_contract.py`,
  `tests/docs/test_gagov_governance_contract.py`,
  `tests/docs/test_gae2e_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GAOPS docs contract test that requires a canonical
    `docs/validation/ga-operations-evidence.md` artifact and asserts that the
    runbooks define GAOPS sections for preflight, deployment qualification,
    rollback, index rebuild, incident response, and support triage.
  - test: Assert that observability docs and the preflight wrapper agree on the
    exact `scripts/preflight_upgrade.sh <env_file>` invocation, `/metrics`
    authentication posture, JSON-log verification path, and metadata-only
    evidence handling.
  - test: Assert that deployment guides do not present unsupported hosted or
    managed-service operations as current GA-backed behavior and instead route
    readers to the runbooks and checklist for the supported local-first path.
  - test: Assert that the GA operations evidence artifact labels every check as
    `local`, `CI`, or `metadata-only` and references the frozen GABASE,
    GAGOV, and GAE2E artifacts without inventing a second GA contract.
  - impl: Keep this file additive and phase-specific so earlier GABASE, GAGOV,
    GAE2E, deployment-runbook-shape, preflight, and observability tests remain
    lower-level supporting contracts.
  - verify: `uv run pytest tests/docs/test_gaops_operations_contract.py -v --no-cov`

### SL-1 - Operator Runbook GAOPS Hardening

- **Scope**: Make the operator-facing runbooks explicit about the GAOPS
  procedure set without broad documentation redesign or release execution.
- **Owned files**: `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Interfaces provided**: IF-0-GAOPS-1
- **Interfaces consumed**: SL-0 GAOPS assertions;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  current release/operator guidance in both runbooks
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 to fail first on missing GAOPS sections, missing incident or
    rollback procedures, stale RC-only wording that should now be generalized
    into GA-hardening ops posture, or continued references to the wrong
    preflight invocation.
  - impl: Add or revise dedicated GAOPS sections in both runbooks that name the
    preflight boundary, deployment qualification flow, rollback path, index
    rebuild commands, incident-response steps, and operator support-triage
    boundary.
  - impl: Keep local-first repository ownership explicit: operators own repo
    registration, reindex, allowed-roots policy, and readiness remediation; do
    not imply a hosted indexing service or managed branch-repair path.
  - impl: Preserve historical P12-P26 and GAGOV context only where it still
    explains current responsibilities; GAOPS should tighten or supersede stale
    sections instead of leaving contradictory instructions in place.
  - verify: `uv run pytest tests/docs/test_gaops_operations_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gagov_governance_contract.py tests/test_deployment_runbook_shape.py -v --no-cov`
  - verify: `rg -n "GAOPS|ga-operations-evidence|preflight|rollback|index rebuild|incident response|support triage|local-first|managed service|v1\\.2\\.0-rc5" docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md`

### SL-2 - Observability And Preflight Procedure Parity

- **Scope**: Align the observability verification guide and preflight wrapper
  with the actual test-backed operator procedure set.
- **Owned files**: `docs/operations/observability-verification.md`,
  `scripts/preflight_upgrade.sh`
- **Interfaces provided**: IF-0-GAOPS-2
- **Interfaces consumed**: SL-0 GAOPS assertions;
  `tests/integration/obs/test_obs_smoke.py`,
  `tests/test_preflight_upgrade.py`, `mcp_server.gateway` metrics/auth
  behavior, `mcp_server.cli.preflight_commands.preflight_env`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 plus the existing preflight and observability tests to
    identify any mismatch between documented commands, script usage, metrics
    auth posture, and the real smoke harness.
  - impl: Fix the operator procedure to use the exact env-file invocation
    required by `scripts/preflight_upgrade.sh`, and tighten the surrounding
    docs so the wrapper, CLI subcommand, and verification text all describe the
    same behavior.
  - impl: Keep `/metrics`, log, and redaction guidance evidence-based and
    explicit about which checks are locally runnable versus CI-automated.
  - impl: Avoid adding a second ops harness; reuse the existing smoke and
    preflight surfaces unless a small wrapper improvement is required to make
    the documented operator path testable.
  - verify: `uv run pytest tests/test_preflight_upgrade.py tests/integration/obs/test_obs_smoke.py -v --no-cov`
  - verify: `rg -n "preflight_upgrade\\.sh|preflight_env|/metrics|Authorization: Bearer|JSON log|metadata-only|CI" docs/operations/observability-verification.md scripts/preflight_upgrade.sh`

### SL-3 - Deployment Guide Support-Boundary Alignment

- **Scope**: Reconcile the broad deployment guides with the supported GAOPS
  contract so they stop over-promising managed operations.
- **Owned files**: `docs/DEPLOYMENT-GUIDE.md`,
  `docs/PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Interfaces provided**: IF-0-GAOPS-3
- **Interfaces consumed**: SL-0 GAOPS assertions; SL-2 observability/preflight
  vocabulary; `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/operations/deployment-runbook.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 to fail first on unsupported deployment claims,
    infrastructure assumptions, or monitoring/rollback promises that are not
    backed by the current runbooks and evidence artifacts.
  - impl: Tighten `docs/DEPLOYMENT-GUIDE.md` and
    `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` so they describe the current
    supported/operator-owned deployment surfaces, point to the runbooks for
    executable procedures, and treat generic cluster or managed-service
    examples as non-authoritative or out of scope if they cannot be justified.
  - impl: Preserve useful environment and topology guidance, but remove or
    clearly bound claims such as blue-green automation, Helm/Kubernetes/Docker
    Swarm production support, or multi-region readiness when they are not part
    of the frozen GA evidence set.
  - impl: Keep the local-first indexing boundary explicit and avoid implying
    that operators can delegate indexing, readiness repair, or observability
    ownership to a hosted service.
  - verify: `uv run pytest tests/docs/test_gaops_operations_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
  - verify: `rg -n "blue-green|Helm|Kubernetes|Docker Swarm|multi-region|managed|local-first|ga-readiness-checklist|deployment-runbook|ga-operations-evidence" docs/DEPLOYMENT-GUIDE.md docs/PRODUCTION_DEPLOYMENT_GUIDE.md`

### SL-4 - GA Operations Evidence Reducer

- **Scope**: Reduce the final runbook, observability/preflight, and
  deployment-guide posture into the canonical GAOPS evidence artifact.
- **Owned files**: `docs/validation/ga-operations-evidence.md`
- **Interfaces provided**: IF-0-GAOPS-4; canonical GAOPS evidence for GARC and
  GAREL
- **Interfaces consumed**: SL-0 GAOPS assertions; SL-1 runbook procedures;
  SL-2 observability and preflight procedure set; SL-3 deployment-guide
  support boundaries; `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write `docs/validation/ga-operations-evidence.md` only after SL-1
    through SL-3 have settled the exact operator procedure set and support
    boundaries.
  - impl: Record deployment preflight, deployment qualification, rollback,
    index rebuild, incident response, observability verification, and support
    triage procedures, and label each one with exactly one validation mode:
    `local`, `CI`, or `metadata-only`.
  - impl: Record the observed commit, artifact/guide sources, any redacted
    metadata probes, and the remaining non-GA limitations or unsupported hosted
    assumptions that later GARC/GAREL decisions must preserve.
  - impl: Keep the artifact redacted and evidence-backed; do not turn GAOPS
    into a release-execution log, managed-service launch plan, or new support
    matrix.
  - verify: `uv run pytest tests/docs/test_gaops_operations_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gagov_governance_contract.py tests/docs/test_gae2e_evidence_contract.py tests/test_preflight_upgrade.py tests/integration/obs/test_obs_smoke.py tests/test_deployment_runbook_shape.py -v --no-cov`
  - verify: `rg -n "local|CI|metadata-only|deployment preflight|rollback|index rebuild|incident response|support triage|ga-readiness-checklist|ga-governance-evidence|ga-e2e-evidence" docs/validation/ga-operations-evidence.md`

## Verification

- `uv run pytest tests/docs/test_gaops_operations_contract.py -v --no-cov`
- `uv run pytest tests/test_preflight_upgrade.py tests/integration/obs/test_obs_smoke.py tests/test_deployment_runbook_shape.py -v --no-cov`
- `uv run pytest tests/docs/test_gaops_operations_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gagov_governance_contract.py tests/docs/test_gae2e_evidence_contract.py tests/test_preflight_upgrade.py tests/integration/obs/test_obs_smoke.py tests/test_deployment_runbook_shape.py -v --no-cov`
- `rg -n "GAOPS|ga-operations-evidence|preflight_upgrade\\.sh|index rebuild|incident response|support triage|local-first|managed|metadata-only|ga-readiness-checklist|ga-governance-evidence|ga-e2e-evidence" docs/operations docs/validation docs/DEPLOYMENT-GUIDE.md docs/PRODUCTION_DEPLOYMENT_GUIDE.md scripts/preflight_upgrade.sh`

## Acceptance Criteria

- [ ] `docs/operations/deployment-runbook.md` and
      `docs/operations/user-action-runbook.md` define explicit GAOPS operator
      procedures for preflight, deployment qualification, rollback, index
      rebuild, incident response, and support triage.
- [ ] `docs/operations/observability-verification.md` and
      `scripts/preflight_upgrade.sh` agree on the real preflight invocation,
      metrics/log verification path, and redaction/auth expectations without
      leaking secret values.
- [ ] `docs/DEPLOYMENT-GUIDE.md` and
      `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` stop presenting unsupported hosted
      or managed-service behavior as current GA-backed deployment posture.
- [ ] Docs tests prevent stale RC/public-alpha operational instructions from
      silently becoming GA operator guidance, and existing preflight,
      observability, and runbook-shape tests continue to cover the executable
      procedure surface.
- [ ] `docs/validation/ga-operations-evidence.md` exists as the canonical
      redacted GAOPS artifact and records which procedures were validated
      locally, in CI, or as metadata-only checks.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gaops.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gaops.md
  artifact_state: staged
```
