---
phase_loop_plan_version: 1
phase: GAREL
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 57de286822c56cae88a9d3ad319a51aa3609470a0fd647796b3fc4b73e983614
---
# GAREL: GA Decision and Release

## Context

GAREL is the seventh and terminal phase in the v5 GA-hardening roadmap. It
must reduce the completed GABASE, GAGOV, GASUPPORT, GAE2E, GAOPS, and GARC
artifacts into one singular release decision and must stop before mutation
unless that decision is explicitly `ship GA`.

Current repo state gathered during planning:

- The checkout is on `main` at `3d5a3aa14af5950dc3e6c20bc66d3f0c81998c28`,
  matching `origin/main`, but the worktree is intentionally dirty with
  user-owned updates in `docs/validation/ga-rc-evidence.md`,
  `tests/docs/test_garc_rc_soak_contract.py`, and
  `specs/phase-plans-v5.md`; GAREL execution must preserve those edits and
  treat the modified roadmap as the active baseline rather than reverting it.
- `.codex/phase-loop/state.json` already records `GABASE`, `GAGOV`,
  `GASUPPORT`, `GAE2E`, `GAOPS`, and `GARC` as complete while `GAREL` remains
  the current unplanned phase, so this plan should hand directly to
  `codex-execute-phase` instead of reopening earlier scope.
- `docs/validation/ga-rc-evidence.md` now records a successful `v1.2.0-rc6`
  soak and explicitly forwards one unresolved GAREL blocker: the
  `peter-evans/create-pull-request@v7` Node 20 deprecation warning emitted by
  the `Merge Release Branch` job in
  `.github/workflows/release-automation.yml`.
- `docs/validation/ga-final-decision.md` and
  `docs/validation/ga-release-evidence.md` do not exist yet; they are the
  canonical missing reducer artifacts reserved for this phase by
  `docs/validation/ga-readiness-checklist.md`.
- Public docs, support matrix text, and install helpers still present the
  `1.2.0-rc6` beta/public-alpha posture. GAREL therefore needs a conditional
  release path: if the final decision is not `ship GA`, those surfaces should
  remain prerelease-only and only the decision artifact should change.
- If the final decision is `ship GA`, the stable artifact identity should be
  derived from the current `rc6` line as `1.2.0` / `v1.2.0`, and the release
  workflow, package metadata, docs, GitHub release state, PyPI package, GHCR
  tags, install flows, and rollback documentation must all align on that
  stable channel.

## Interface Freeze Gates

- [ ] IF-0-GAREL-1 - Final decision contract:
      `docs/validation/ga-final-decision.md` states exactly one of `ship GA`,
      `cut another RC`, or `defer GA`, cites the canonical GABASE, GAGOV,
      GASUPPORT, GAE2E, GAOPS, and GARC evidence inputs, and names the next
      roadmap or RC scope when the answer is not `ship GA`.
- [ ] IF-0-GAREL-2 - Workflow-runtime disposition contract:
      `.github/workflows/release-automation.yml`,
      `tests/test_release_metadata.py`, and the final decision artifact either
      remove the `peter-evans/create-pull-request@v7` Node 20 deprecation path
      or explicitly record why the warning is acceptable before any GA dispatch.
- [ ] IF-0-GAREL-3 - Stable release channel contract:
      if the decision is `ship GA`, repo-owned version surfaces, public docs,
      support-tier claims, GitHub Latest posture, Docker `latest`, and install
      helpers all align on stable `1.2.0` / `v1.2.0`; otherwise those surfaces
      remain on `1.2.0-rc6` / `v1.2.0-rc6` with no GA mutation.
- [ ] IF-0-GAREL-4 - Post-release verification contract:
      the selected channel state is proven by targeted docs tests,
      release-metadata tests, release smoke or clean-checkout install checks,
      and GitHub release metadata probes, and any failure blocks GA instead of
      being reduced away in prose.
- [ ] IF-0-GAREL-5 - GA evidence reducer contract:
      `docs/validation/ga-release-evidence.md` is written only on the `ship GA`
      path and records dispatch inputs, workflow URL / run ID / `headSha`,
      release/channel state, PyPI and GHCR identities, install verification,
      rollback disposition, and redacted metadata only.

## Lane Index & Dependencies

- SL-0 - GAREL contract tests; Depends on: GARC; Blocks: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-1 - Release workflow runtime and GA-dispatch policy; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-2 - Final decision reducer; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-3 - Stable package and changelog contract; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-4 - Public docs and operator channel alignment; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SL-5, SL-6; Parallel-safe: yes
- SL-5 - GA dispatch and post-release verification; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: SL-6; Parallel-safe: no
- SL-6 - GA release evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4, SL-5; Blocks: GAREL acceptance; Parallel-safe: no

## Lanes

### SL-0 - GAREL Contract Tests

- **Scope**: Freeze the final-decision, workflow-runtime, stable-channel, and
  conditional evidence-writing rules before any GA mutation is attempted.
- **Owned files**: `tests/docs/test_garel_ga_release_contract.py`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-2, IF-0-GAREL-3,
  IF-0-GAREL-4, IF-0-GAREL-5
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`,
  `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`,
  `tests/smoke/test_release_smoke_contract.py`,
  `README.md`, `CHANGELOG.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GAREL docs contract test that requires
    `docs/validation/ga-final-decision.md` to state exactly one allowed
    decision, cite all prerequisite GA-hardening artifacts, and name the next
    scope when the decision is not `ship GA`.
  - test: Assert that `docs/validation/ga-release-evidence.md` is required only
    on the `ship GA` path and that non-ship paths keep stable-release claims,
    stable Docker `latest`, and GitHub Latest mutation out of active docs.
  - test: Assert that the Node 20 warning from
    `peter-evans/create-pull-request@v7` is either gone from the workflow or
    explicitly dispositioned in the final decision artifact before GA dispatch.
  - test: Keep this test additive and phase-specific so GABASE, GAGOV, GAOPS,
    GARC, release-metadata, and smoke tests remain the lower-level supporting
    contracts rather than being redefined here.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`

### SL-1 - Release Workflow Runtime And GA-Dispatch Policy

- **Scope**: Resolve or explicitly disposition the release-workflow runtime
  warning and freeze the GA dispatch policy before the final decision is made.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`, `tests/smoke/test_release_smoke_contract.py`
- **Interfaces provided**: IF-0-GAREL-2; the workflow portion of
  IF-0-GAREL-3 and IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions;
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-readiness-checklist.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Reproduce the current workflow-runtime warning from the successful
    `v1.2.0-rc6` run by inspecting the `Merge Release Branch` job logs and use
    that exact warning text as the repair target.
  - impl: Upgrade or replace `peter-evans/create-pull-request@v7` in
    `.github/workflows/release-automation.yml`, or explicitly codify the
    accepted-risk path if GitHub Actions still emits the Node 20 warning and
    the GA decision chooses not to mutate the workflow.
  - impl: Freeze the GA dispatch semantics in the workflow and tests: stable
    `v1.2.0` must not be treated as a prerelease, GitHub Latest and Docker
    `latest` must change only on the `ship GA` path, and release automation
    must keep non-ship paths mutation-free.
  - impl: Update the release-metadata and smoke-contract tests only where they
    need to distinguish the stable GA path from the current `rc6` prerelease
    path; avoid reopening unrelated RC automation behavior.
  - verify: `uv run pytest tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `gh run view 24913315931 --job 72961441162 --log`
  - verify: `rg -n "create-pull-request|Node 20|prerelease|latest|v1\\.2\\.0-rc6|v1\\.2\\.0" .github/workflows/release-automation.yml tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py`

### SL-2 - Final Decision Reducer

- **Scope**: Reduce the upstream GA-hardening evidence and workflow-runtime
  disposition into the singular go/no-go decision artifact before any stable
  mutation occurs.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: IF-0-GAREL-1; the decision input to IF-0-GAREL-3
  and IF-0-GAREL-5
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow-runtime
  disposition; `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write the decision artifact only after the workflow-runtime warning,
    support posture, operations evidence, and RC soak evidence have been read
    together; do not let a successful `rc6` soak alone imply GA approval.
  - impl: Record exactly one decision: `ship GA`, `cut another RC`, or
    `defer GA`.
  - impl: If the decision is not `ship GA`, name the next roadmap or RC scope,
    keep all stable-release mutations blocked, and make `ga-release-evidence.md`
    explicitly unnecessary for that branch.
  - impl: If the decision is `ship GA`, state the exact prerequisites that are
    satisfied for stable `1.2.0` / `v1.2.0`, including the disposition of the
    Node 20 workflow warning, before SL-3 through SL-6 mutate release surfaces.
  - impl: Preserve the historical-artifact banner and metadata-only reporting
    pattern used by the other GA evidence reducers.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "Final decision|ship GA|cut another RC|defer GA|ga-readiness-checklist|ga-governance-evidence|ga-e2e-evidence|ga-operations-evidence|ga-rc-evidence|Node 20" docs/validation/ga-final-decision.md`

### SL-3 - Stable Package And Changelog Contract

- **Scope**: Align repo-owned release metadata to the final decision without
  mutating public docs or installer guidance directly.
- **Owned files**: `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`
- **Interfaces provided**: package/version portion of IF-0-GAREL-3 and
  IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow dispatch
  policy; SL-2 final decision artifact
- **Parallel-safe**: yes
- **Tasks**:
  - test: Treat this lane as conditional on SL-2. If the decision is not
    `ship GA`, verify that `1.2.0-rc6` remains the active package contract and
    do not rewrite package metadata.
  - impl: If the decision is `ship GA`, advance the repo-owned release identity
    from `1.2.0-rc6` / `v1.2.0-rc6` to stable `1.2.0` / `v1.2.0` in
    `pyproject.toml`, `mcp_server/__init__.py`, and the new changelog section.
  - impl: Keep the changelog explicit about the release-channel transition and
    any remaining non-GA or deferred surfaces instead of silently erasing the
    prerelease history.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc6|1\\.2\\.0|v1\\.2\\.0-rc6|v1\\.2\\.0" pyproject.toml mcp_server/__init__.py CHANGELOG.md`

### SL-4 - Public Docs And Operator Channel Alignment

- **Scope**: Align user-facing docs, support tiers, and operator runbooks with
  the final GAREL decision after repo-owned metadata has settled.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`
- **Interfaces provided**: public-doc portion of IF-0-GAREL-3 and
  IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow/runtime
  policy; SL-2 final decision artifact; SL-3 package and changelog contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 to fail first on any public doc that claims GA or stable
    release before the final decision artifact authorizes it.
  - impl: If the decision is `ship GA`, switch the active docs, support matrix,
    installer defaults, and operator runbooks from the `rc6` beta/public-alpha
    posture to stable `1.2.0` guidance, including GitHub Latest and Docker
    `latest` expectations.
  - impl: If the decision is `cut another RC` or `defer GA`, keep the public
    surfaces on `rc6` posture and update only the decision-routing language so
    the repo does not imply a stable release that did not happen.
  - impl: Preserve the frozen support-tier and topology limits from GASUPPORT;
    GAREL can narrow channel wording, but it must not broaden language/runtime
    claims or multi-worktree support.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc6|1\\.2\\.0|v1\\.2\\.0-rc6|v1\\.2\\.0|public-alpha|beta|GA|GitHub Latest|stable Docker latest|ga-final-decision|ga-readiness-checklist" README.md docs/GETTING_STARTED.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1`

### SL-5 - GA Dispatch And Post-Release Verification

- **Scope**: Execute the stable release only when SL-2 chose `ship GA`, then
  capture the post-release verification needed to prove the final channel state.
- **Owned files**: none (GitHub workflow runs, release metadata, package index,
  container registry, and clean-checkout verification results)
- **Interfaces provided**: observed IF-0-GAREL-4 and release facts for
  IF-0-GAREL-5
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 release workflow and
  policy; SL-2 final decision; SL-3 stable package contract; SL-4 public docs
  alignment
- **Parallel-safe**: no
- **Tasks**:
  - test: If SL-2 did not choose `ship GA`, stop here with no release mutation
    and preserve the blocked/no-op outcome for SL-6.
  - test: On the `ship GA` path, rerun the narrowed contract tests before
    dispatch so workflow policy, package metadata, changelog, public docs, and
    support claims are coherent.
  - test: Re-qualify the release state with clean-branch, synchronized
    `origin/main`, and stable-tag non-reuse checks before dispatching GA.
  - impl: Dispatch Release Automation with the stable version input
    `v1.2.0` and governance-approved settings only after the Node 20 warning
    has been remediated or explicitly accepted in SL-2.
  - impl: Watch the run to completion, then verify GitHub release, PyPI,
    GHCR, installer/download flows, and clean-checkout smoke against the stable
    release artifacts.
  - impl: If any dispatch, publish, or clean-checkout verification step fails,
    stop before claiming GA success and route the blocker back into
    `docs/validation/ga-final-decision.md` plus `docs/validation/ga-release-evidence.md`.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `git status --short --branch`
  - verify: `git fetch origin main --tags --prune`
  - verify: `git rev-parse HEAD origin/main`
  - verify: `git tag -l v1.2.0`
  - verify: `git ls-remote --tags origin refs/tags/v1.2.0`
  - verify: `gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=stable -f auto_merge=false`
  - verify: `gh run list --workflow "Release Automation" --limit 10`
  - verify: `gh run watch <run-id> --exit-status`
  - verify: `gh run view <run-id> --json url,headSha,status,conclusion,jobs`
  - verify: `gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,isLatest,publishedAt,targetCommitish,url,assets`
  - verify: `make release-smoke`
  - verify: `make release-smoke-container`

### SL-6 - GA Release Evidence Reducer

- **Scope**: Reduce the decision, stable release execution, and post-release
  verification into the canonical GA release evidence artifact.
- **Owned files**: `docs/validation/ga-release-evidence.md`
- **Interfaces provided**: IF-0-GAREL-5
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow/runtime
  policy; SL-2 final decision artifact; SL-3 stable package contract; SL-4
  public docs alignment; SL-5 dispatch and verification results;
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write `docs/validation/ga-release-evidence.md` only when SL-2 chose
    `ship GA` and SL-5 captured an actual stable release run plus post-release
    verification results.
  - impl: Record the stable dispatch inputs, run URL / run ID / `headSha`,
    per-job conclusions, tag target, GitHub release state including Latest
    posture, PyPI and GHCR identities, install/smoke verification, and rollback
    disposition using redacted metadata only.
  - impl: If SL-2 chose a non-ship path, keep this file absent and make
    `docs/validation/ga-final-decision.md` the only reducer artifact for the
    phase.
  - impl: Preserve the historical-artifact banner pattern and make the artifact
    explicit about whether the stable release succeeded, failed after dispatch,
    or was never attempted because the final decision did not authorize it.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "Historical artifact|v1\\.2\\.0|Release Automation|run ID|GitHub release|isLatest|PyPI|GHCR|release-smoke|rollback|ship GA" docs/validation/ga-release-evidence.md`

## Verification

- `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`
- `uv run pytest tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
- `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
- `gh run view 24913315931 --job 72961441162 --log`
- `git status --short --branch`
- `git fetch origin main --tags --prune`
- `git rev-parse HEAD origin/main`
- `git tag -l v1.2.0`
- `git ls-remote --tags origin refs/tags/v1.2.0`
- `gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=stable -f auto_merge=false`
- `gh run list --workflow "Release Automation" --limit 10`
- `gh run watch <run-id> --exit-status`
- `gh run view <run-id> --json url,headSha,status,conclusion,jobs`
- `gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,isLatest,publishedAt,targetCommitish,url,assets`
- `make release-smoke`
- `make release-smoke-container`

## Acceptance Criteria

- [ ] `docs/validation/ga-final-decision.md` exists and states exactly one of
      `ship GA`, `cut another RC`, or `defer GA`, citing the canonical
      GABASE, GAGOV, GASUPPORT, GAE2E, GAOPS, and GARC evidence.
- [ ] The Node 20 workflow warning from the GARC soak is remediated or
      explicitly dispositioned before any GA dispatch is attempted.
- [ ] If the decision is not `ship GA`, no stable release mutation occurs and
      the final decision artifact names the next roadmap or RC scope.
- [ ] If the decision is `ship GA`, repo-owned metadata, public docs, support
      claims, install helpers, GitHub Latest posture, and Docker `latest`
      guidance all align on stable `1.2.0` / `v1.2.0`.
- [ ] Stable dispatch and post-release verification either succeed and are
      recorded in `docs/validation/ga-release-evidence.md`, or fail in an
      explicit blocker state without silently implying GA success.

## Automation

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-garel.md
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
