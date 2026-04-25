---
phase_loop_plan_version: 1
phase: GAREL
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 4b09568b3e451da4b9d1d154a073ede1d3903c8e7fc5cb8111dec3fbcec10fd1
---
# GAREL: GA Decision And Stable-Surface Preparation

## Context

GAREL is the renewed GA-decision phase in the v5 GA-hardening roadmap. The
current roadmap hash is
`4b09568b3e451da4b9d1d154a073ede1d3903c8e7fc5cb8111dec3fbcec10fd1`, the
checkout is on clean synced `main` at `7633b44`, and phase-loop state already
marks `GAREL` as the current planned phase under this roadmap.

The current repo state is split across two truths that the refreshed plan must
reconcile:

- `docs/validation/ga-final-decision.md` already records the renewed GAREL
  decision as `ship GA`, cites the successful `v1.2.0-rc8` soak, and
  dispositions the remaining `actions/download-artifact@v8` `Buffer()` warning
  as accepted non-blocking risk for a downstream stable dispatch.
- Repo-owned release surfaces still advertise the active prerelease contract:
  `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`, `README.md`,
  `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/DOCKER_GUIDE.md`, `docs/SUPPORT_MATRIX.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`, and the Docker installer helpers
  still point at `1.2.0-rc8` / `v1.2.0-rc8`, while several doc and smoke tests
  still freeze `rc8` as the active public surface.

That means the older GAREL plan is stale for the current roadmap contract. A
fresh execution-ready GAREL artifact must plan the repo-local stable-surface
transition to `1.2.0` / `v1.2.0`, preserve `v1.2.0-rc8` as historical soak
evidence only, and stop before any external release mutation. No
`plans/phase-plan-v5-gadisp.md` exists yet, and
`docs/validation/ga-release-evidence.md` is still intentionally absent.

## Interface Freeze Gates

- [ ] IF-0-GAREL-1 - Final decision reducer contract:
      `docs/validation/ga-final-decision.md` cites
      `docs/validation/ga-readiness-checklist.md`,
      `docs/validation/ga-governance-evidence.md`,
      `docs/validation/ga-e2e-evidence.md`,
      `docs/validation/ga-operations-evidence.md`, and
      `docs/validation/ga-rc-evidence.md`, records exactly one of `ship GA`,
      `cut another RC`, or `defer GA`, and explicitly carries the accepted
      `actions/download-artifact@v8` `Buffer()` warning disposition without
      creating `docs/validation/ga-release-evidence.md`.
- [ ] IF-0-GAREL-2 - Stable repo-owned surface contract:
      `.github/workflows/release-automation.yml`, `pyproject.toml`,
      `mcp_server/__init__.py`, `CHANGELOG.md`, public docs, support docs,
      runbooks, and installer helpers align on stable `1.2.0` / `v1.2.0`
      while preserving the v3 topology limits, tiered support vocabulary, and
      stable-only `GitHub Latest` and Docker `latest` posture.
- [ ] IF-0-GAREL-3 - Historical RC evidence preservation contract:
      `docs/validation/ga-rc-evidence.md`, `docs/validation/ga-final-decision.md`,
      and the GARC/GARECUT doc tests preserve `v1.2.0-rc8` as historical
      prerelease evidence and no longer treat it as the active public install
      surface after ship-GA prep.
- [ ] IF-0-GAREL-4 - Downstream dispatch handoff contract:
      GAREL performs no external release mutation, keeps
      `docs/validation/ga-release-evidence.md` absent, and leaves the repo in
      a state where the only next release phase is a dedicated
      `phase_loop_mutation: release_dispatch` GADISP plan.

## Lane Index & Dependencies

- SL-0 - Ship-GA contract and regression test freeze; Depends on: GARC; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Stable release identity and workflow defaults; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: yes
- SL-2 - Public docs, support matrix, installers, and runbook prep; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: yes
- SL-3 - Final decision reducer and downstream GADISP handoff; Depends on: SL-0, SL-1, SL-2; Blocks: GAREL acceptance; Parallel-safe: no

## Lanes

### SL-0 - Ship-GA Contract And Regression Test Freeze

- **Scope**: Rewrite the GAREL-era doc, metadata, and smoke tests so the
  current `ship GA` decision requires stable `1.2.0` prep, preserves
  `v1.2.0-rc8` as historical evidence only, and still blocks all stable
  dispatch evidence until GADISP.
- **Owned files**: `tests/docs/test_garel_ga_release_contract.py`,
  `tests/docs/test_gabase_ga_readiness_contract.py`,
  `tests/docs/test_garc_rc_soak_contract.py`,
  `tests/docs/test_garecut_rc_recut_contract.py`,
  `tests/docs/test_p23_doc_truth.py`,
  `tests/docs/test_gaops_operations_contract.py`,
  `tests/test_release_metadata.py`,
  `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-2, IF-0-GAREL-3,
  IF-0-GAREL-4
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`,
  `README.md`,
  `docker/README.md`,
  `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`,
  `docs/DOCKER_GUIDE.md`,
  `docs/SUPPORT_MATRIX.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `scripts/install-mcp-docker.sh`,
  `scripts/install-mcp-docker.ps1`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the GAREL contract test so `ship GA` requires stable
    repo-owned `1.2.0` / `v1.2.0` prep, keeps
    `docs/validation/ga-release-evidence.md` absent, and routes only to
    downstream GADISP for release mutation.
  - test: Rewrite the active-surface metadata and smoke tests so
    `tests/test_release_metadata.py`, `tests/smoke/test_release_smoke_contract.py`,
    and the docs truth checks stop treating `rc8` as the active public version
    while still preserving the accepted support-tier and topology language.
  - test: Convert the GABASE, GARC, GARECUT, and GAOPS doc assertions from
    "active rc8 surface" checks into "historical rc8 evidence plus stable
    release prep" checks wherever those files now reference the active channel.
  - impl: Keep this lane test-only; it defines the frozen acceptance contract
    for SL-1 through SL-3 and should not mutate implementation or docs outside
    the owned test files.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_garc_rc_soak_contract.py tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_p23_doc_truth.py tests/docs/test_gaops_operations_contract.py -v --no-cov`

### SL-1 - Stable Release Identity And Workflow Defaults

- **Scope**: Advance the repo-owned release identity from the active rc8
  baseline to stable `1.2.0` / `v1.2.0` in the workflow and package metadata
  surfaces without dispatching the release.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`
- **Interfaces provided**: IF-0-GAREL-2; repo-owned version inputs consumed by
  SL-2 and SL-3
- **Interfaces consumed**: SL-0 GAREL assertions;
  `docs/validation/ga-final-decision.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Re-run the narrowed release-metadata and GAREL contract tests first
    so this lane only changes the stable identity contract required by the
    roadmap.
  - impl: Update the workflow defaults, package metadata, runtime version, and
    changelog head section from `1.2.0-rc8` / `v1.2.0-rc8` to stable
    `1.2.0` / `v1.2.0`.
  - impl: Preserve `release_type=custom`, `auto_merge=false`,
    `peter-evans/create-pull-request@v8`,
    `softprops/action-gh-release@v3`, accepted-risk wording for the
    `actions/download-artifact@v8` warning, and stable-only `GitHub Latest`
    plus Docker `latest` behavior; do not dispatch the workflow in this lane.
  - impl: Keep rc8 references only where they are historical soak evidence or
    comments, not where they define the next active release surface.
  - verify: `uv run pytest tests/test_release_metadata.py tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc8|v1\\.2\\.0-rc8|1\\.2\\.0|v1\\.2\\.0|release_type=custom|auto_merge=false|create-pull-request@v8|softprops/action-gh-release@v3|latest" .github/workflows/release-automation.yml pyproject.toml mcp_server/__init__.py CHANGELOG.md`

### SL-2 - Public Docs, Support Matrix, Installers, And Runbook Prep

- **Scope**: Move the repo-owned public documentation, support posture, and
  installer defaults to the stable `1.2.0` contract while preserving the
  product's existing beta, experimental, unsupported, and topology limits.
- **Owned files**: `README.md`,
  `docker/README.md`,
  `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`,
  `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `scripts/install-mcp-docker.sh`,
  `scripts/install-mcp-docker.ps1`
- **Interfaces provided**: IF-0-GAREL-2, IF-0-GAREL-3, IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 stable release identity;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use the refreshed docs truth, support, runbook, and smoke checks to
    fail first on stale `rc8` public-surface claims before editing docs or
    installer defaults.
  - impl: Advance public-facing version strings, install commands, image tags,
    and operator guidance from `1.2.0-rc8` / `v1.2.0-rc8` to stable
    `1.2.0` / `v1.2.0`.
  - impl: Preserve the GASUPPORT tier labels and limits: GA release does not
    broaden language support, does not authorize unrestricted multi-worktree or
    multi-branch indexing, and does not remove beta or experimental labels
    where the support matrix still requires them.
  - impl: Retain `v1.2.0-rc8` only as historical prerelease evidence in
    narrative sections that explicitly describe the soak and accepted-risk
    disposition; remove it from active install or "current version" guidance.
  - impl: Leave `docs/validation/ga-release-evidence.md` absent and do not add
    any prose implying stable release publication already happened.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_p23_doc_truth.py tests/docs/test_gaops_operations_contract.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc8|v1\\.2\\.0-rc8|1\\.2\\.0|v1\\.2\\.0|public-alpha|beta|experimental|unsupported|disabled-by-default|GitHub Latest|docker `latest`|ga-release-evidence" README.md docker/README.md docs/GETTING_STARTED.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1`

### SL-3 - Final Decision Reducer And Downstream GADISP Handoff

- **Scope**: Reduce the refreshed stable-surface state into the canonical
  GAREL decision artifact and hand off only to dispatch-only GADISP.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-3, IF-0-GAREL-4
- **Interfaces consumed**: SL-0 ship-GA assertions; SL-1 stable release
  identity; SL-2 stable docs and runbook prep;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Rewrite the final decision artifact only after stable-surface prep is
    complete so the reducer accurately describes the repo state it is
    authorizing for downstream dispatch.
  - impl: Keep exactly one final decision and preserve the accepted
    `actions/download-artifact@v8` `Buffer()` warning disposition as
    non-blocking for downstream GADISP.
  - impl: Record that repo-owned stable surfaces now prepare stable `1.2.0`
    / `v1.2.0`, that `v1.2.0-rc8` remains historical evidence only, and that
    `docs/validation/ga-release-evidence.md` stays intentionally absent until
    GADISP dispatches and verifies the stable release.
  - impl: If SL-1 or SL-2 uncovers contradictory evidence that prevents
    `ship GA`, stop on `cut another RC` or `defer GA` language and name the
    next roadmap scope instead of silently leaving a ship-GA artifact in place.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_garc_rc_soak_contract.py tests/docs/test_garecut_rc_recut_contract.py -v --no-cov`
  - verify: `rg -n "ship GA|cut another RC|defer GA|actions/download-artifact@v8|Buffer\\(\\)|v1\\.2\\.0-rc8|v1\\.2\\.0|ga-release-evidence|GADISP" docs/validation/ga-final-decision.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual GAREL execution.

Lane-specific contract checks:

```bash
uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov
uv run pytest tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_garc_rc_soak_contract.py tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_p23_doc_truth.py tests/docs/test_gaops_operations_contract.py -v --no-cov
rg -n "1\\.2\\.0-rc8|v1\\.2\\.0-rc8|1\\.2\\.0|v1\\.2\\.0|ship GA|ga-release-evidence|GADISP|GitHub Latest|latest" \
  .github/workflows/release-automation.yml \
  pyproject.toml \
  mcp_server/__init__.py \
  CHANGELOG.md \
  README.md \
  docker/README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  docs/DOCKER_GUIDE.md \
  docs/SUPPORT_MATRIX.md \
  docs/operations/deployment-runbook.md \
  docs/operations/user-action-runbook.md \
  scripts/install-mcp-docker.sh \
  scripts/install-mcp-docker.ps1 \
  docs/validation/ga-final-decision.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container
git status --short --branch
test ! -e docs/validation/ga-release-evidence.md
```

## Acceptance Criteria

- [ ] `docs/validation/ga-final-decision.md` cites the canonical GABASE,
      GAGOV, GAE2E, GAOPS, and GARC evidence set, records exactly one final
      decision, and preserves the accepted `actions/download-artifact@v8`
      warning disposition.
- [ ] Repo-owned release surfaces align on stable `1.2.0` / `v1.2.0` without
      broadening support tiers, topology claims, or runtime surface promises.
- [ ] `v1.2.0-rc8` remains documented only as historical prerelease soak
      evidence and no longer appears as the active public install surface.
- [ ] `docs/validation/ga-release-evidence.md` remains absent and no external
      release mutation is attempted during GAREL execution.
- [ ] The repo is left ready for a dispatch-only downstream plan:
      `codex-plan-phase specs/phase-plans-v5.md GADISP`.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v5-garel.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-garel.md
  artifact_state: staged
```
