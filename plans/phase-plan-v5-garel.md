---
phase_loop_plan_version: 1
phase: GAREL
roadmap: specs/phase-plans-v5.md
roadmap_sha256: b7945b960e659cf0f96f8aa112af1370b65a3e007d837abdefd8836d50f4b774
---
# GAREL: GA Decision and Stable-Surface Preparation

## Context

GAREL is the renewed decision phase in the v5 GA-hardening roadmap. `GARECUT`
is complete, the checkout is on `main` at `2a538ad`, `origin/main` currently
matches `HEAD`, and the repo-owned release surfaces still reflect the
prerelease `1.2.0-rc8` / `v1.2.0-rc8` contract in
`.github/workflows/release-automation.yml`, `tests/test_release_metadata.py`,
package metadata, installer helpers, and the public prerelease docs.

`docs/validation/ga-final-decision.md` is currently a historical reducer that
records `cut another RC` after the successful `v1.2.0-rc8` soak and routes
renewed GAREL through the remaining `actions/download-artifact@v8` `Buffer()`
deprecation warning observed in the successful `Create GitHub Release` job.

The roadmap has now been repaired so GAREL is execution-ready again. Stable
release dispatch no longer lives in this phase. GAREL owns the final decision,
workflow-runtime disposition, and any repo-local stable-surface preparation. If
the decision remains `ship GA`, the external release mutation moves downstream
to `GADISP`, the dedicated `phase_loop_mutation: release_dispatch` phase.

## Interface Freeze Gates

- [ ] IF-0-GAREL-1 - Final decision contract:
      `docs/validation/ga-final-decision.md` cites
      `docs/validation/ga-readiness-checklist.md`,
      `docs/validation/ga-governance-evidence.md`,
      `docs/validation/ga-e2e-evidence.md`,
      `docs/validation/ga-operations-evidence.md`, and
      `docs/validation/ga-rc-evidence.md`, records exactly one of `ship GA`,
      `cut another RC`, or `defer GA`, and reduces the current `v1.2.0-rc8`
      soak rather than any pre-`rc8` assumption.
- [ ] IF-0-GAREL-2 - Workflow-runtime disposition contract:
      `.github/workflows/release-automation.yml`,
      `tests/test_release_metadata.py`, and
      `docs/validation/ga-final-decision.md` either remediate or explicitly
      disposition the remaining `actions/download-artifact@v8` `Buffer()`
      deprecation warning, and no GAREL contract still depends on stale
      `softprops/action-gh-release@v2` assumptions.
- [ ] IF-0-GAREL-3 - Stable-surface alignment contract:
      if the final decision is `ship GA`, package metadata, changelog, public
      docs, installer helpers, support claims, and operator runbooks align on
      stable `1.2.0` / `v1.2.0`; otherwise they remain on prerelease
      `1.2.0-rc8` / `v1.2.0-rc8` and no stable-channel mutation occurs.
- [ ] IF-0-GAREL-4 - Downstream dispatch handoff contract:
      if the final decision is `ship GA`, the next phase is `GADISP` and any
      stable release dispatch or `docs/validation/ga-release-evidence.md`
      creation remains blocked until that separate `release_dispatch` plan runs
      from a clean synced tree; if the final decision is `defer GA`, both
      `GADISP` and `GARECUT` remain blocked until a roadmap extension lands.

## Lane Index & Dependencies

- SL-0 - Renewed GAREL contract tests; Depends on: GARECUT; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Final decision and runtime disposition; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Stable-surface preparation and downstream handoff; Depends on: SL-0, SL-1; Blocks: GAREL acceptance; Parallel-safe: yes

## Lanes

### SL-0 - Renewed GAREL Contract Tests

- **Scope**: Refresh the GAREL-specific contract tests so the renewed decision
  path is frozen around the successful `rc8` soak, the current
  `actions/download-artifact@v8` warning, and the new downstream `GADISP`
  split before any stable mutation is considered.
- **Owned files**: `tests/docs/test_garel_ga_release_contract.py`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-2, IF-0-GAREL-3,
  IF-0-GAREL-4
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`,
  `tests/smoke/test_release_smoke_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the GAREL contract test to require the renewed decision
    artifact to consume the successful `v1.2.0-rc8` recut evidence and to
    treat any older pre-`rc8` GAREL assumptions as stale.
  - test: Assert that the remaining workflow-runtime concern is the current
    `actions/download-artifact@v8` `Buffer()` deprecation warning and that no
    GAREL assertions still key on the already-remediated
    `softprops/action-gh-release@v2` path.
  - test: Assert that `docs/validation/ga-release-evidence.md` remains absent
    unless a separate `GADISP` dispatch artifact set exists.
  - impl: Keep this file additive and phase-specific so GABASE, GARC, GARECUT,
    release-metadata, and release-smoke tests remain the lower-level
    contracts.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`

### SL-1 - Final Decision And Runtime Disposition

- **Scope**: Reduce the upstream GA-hardening evidence and the current workflow
  runtime disposition into one renewed final decision before any stable release
  preparation is allowed.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-2; decision input to
  IF-0-GAREL-3 and IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`,
  `.github/workflows/release-automation.yml`
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the canonical GA-readiness, governance, E2E, operations, RC,
    and workflow inputs together before writing any renewed decision language.
  - impl: Record exactly one decision: `ship GA`, `cut another RC`, or
    `defer GA`.
  - impl: Cite the successful `v1.2.0-rc8` soak and explicitly disposition the
    remaining `actions/download-artifact@v8` `Buffer()` warning in the final
    decision instead of carrying forward stale `softprops` blocker language.
  - impl: If the decision is not `ship GA`, keep all stable mutations blocked,
    leave `docs/validation/ga-release-evidence.md` absent, and name the next
    RC or roadmap scope.
  - impl: If the decision is `ship GA`, state that stable-surface preparation
    may proceed in this phase, but stable dispatch remains blocked until
    `GADISP` is planned from the committed prep state.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "ship GA|cut another RC|defer GA|ga-readiness-checklist|ga-governance-evidence|ga-e2e-evidence|ga-operations-evidence|ga-rc-evidence|actions/download-artifact@v8|Buffer\\(\\)|v1\\.2\\.0-rc8|v1\\.2\\.0|GADISP" docs/validation/ga-final-decision.md`

### SL-2 - Stable-Surface Preparation And Downstream Handoff

- **Scope**: Prepare the repo-owned stable package, docs, installer, support,
  and runbook surfaces only if the renewed decision selects `ship GA`, while
  keeping external release mutation blocked for downstream `GADISP`.
- **Owned files**: `pyproject.toml`, `mcp_server/__init__.py`,
  `CHANGELOG.md`, `README.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`
- **Interfaces provided**: IF-0-GAREL-3, IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 final decision;
  `tests/test_release_metadata.py`,
  `tests/smoke/test_release_smoke_contract.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use the GAREL contract test plus release-metadata, docs, and release
    smoke coverage to fail first on stale channel or version claims before
    editing stable surfaces.
  - impl: If the renewed decision is `ship GA`, advance repo-owned package,
    changelog, docs, installer, support, and runbook surfaces from
    `1.2.0-rc8` / `v1.2.0-rc8` to stable `1.2.0` / `v1.2.0`.
  - impl: If the renewed decision is `cut another RC` or `defer GA`, keep the
    public and repo-owned surfaces on prerelease posture and only repair any
    stale pre-`rc8` wording that conflicts with the current contract.
  - impl: Preserve the frozen support-tier vocabulary, fail-closed readiness
    language, GitHub Latest stable-only posture, Docker `latest` stable-only
    posture, and v3 topology limits from GABASE and GASUPPORT.
  - impl: Do not dispatch the stable release and do not create
    `docs/validation/ga-release-evidence.md` in this phase.
  - impl: If the renewed decision is `ship GA`, leave the tree ready for
    downstream `GADISP` planning from the committed prep state.
  - verify: `uv run pytest tests/test_release_metadata.py tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc8|1\\.2\\.0|v1\\.2\\.0-rc8|v1\\.2\\.0|public-alpha|beta|GA|GitHub Latest|docker latest|ga-final-decision|ga-release-evidence" pyproject.toml mcp_server/__init__.py CHANGELOG.md README.md docs/GETTING_STARTED.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1`

## Verification

- `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
- `make alpha-production-matrix`
- `make release-smoke`
- `make release-smoke-container`
- `git status --short --branch`
- `gh workflow view "Release Automation"`
- If `ship GA` is selected after SL-2, plan the downstream dispatch phase:
  `codex-plan-phase specs/phase-plans-v5.md GADISP`
- If `defer GA` is selected after SL-2, extend the roadmap before any
  downstream release phase is reused:
  `codex-phase-roadmap-builder specs/phase-plans-v5.md`

## Acceptance Criteria

- [ ] `docs/validation/ga-final-decision.md` cites the current `v1.2.0-rc8`
      soak, the current workflow-runtime warning disposition, and states
      exactly one of `ship GA`, `cut another RC`, or `defer GA`.
- [ ] If the decision is not `ship GA`, no stable mutation occurs,
      `docs/validation/ga-release-evidence.md` remains absent, and the next
      RC or roadmap scope is recorded explicitly.
- [ ] If the decision is `ship GA`, package metadata, changelog, public docs,
      installer helpers, support claims, and runbooks are prepared for stable
      `1.2.0` / `v1.2.0` without broadening support tiers or topology claims.
- [ ] Stable release dispatch is explicitly deferred to downstream `GADISP`,
      the dedicated `phase_loop_mutation: release_dispatch` phase.
- [ ] If the decision is `defer GA`, the artifact records the roadmap-extension
      blocker explicitly and does not route straight to the existing `GADISP`
      or `GARECUT` plans.
- [ ] `docs/validation/ga-release-evidence.md` remains absent until a
      successful downstream dispatch and post-release verification exist.
