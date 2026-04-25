---
phase_loop_plan_version: 1
phase: GAREL
roadmap: specs/phase-plans-v5.md
roadmap_sha256: aab3b0f990ecc5f821e2d94dbc48faa6cc3f8a14e6a53da68f983b8be85730dd
---
# GAREL: GA Decision and Release

## Context

GAREL is the renewed terminal decision phase in the v5 GA-hardening roadmap.
Its job is to reduce the completed GABASE, GAGOV, GASUPPORT, GAE2E, GAOPS,
and GARECUT evidence into one final release decision and to stop before any
stable release mutation unless that decision is explicitly `ship GA`.

Current repo state gathered during planning:

- The checkout is on `main` at `a3adcea5cd569571a2c4ce3d863317e9f14519bc`,
  matching `origin/main`.
- `specs/phase-plans-v5.md` is already modified and staged in the worktree, so
  the amended roadmap is the active user-owned baseline and is protected from
  `git clean -fd`.
- `.codex/phase-loop/state.json` records roadmap SHA
  `aab3b0f990ecc5f821e2d94dbc48faa6cc3f8a14e6a53da68f983b8be85730dd`,
  marks `GARECUT` complete, marks `GAREL` unplanned, and carries ledger
  warnings that older GAREL plan/event provenance no longer matches the
  amended roadmap.
- `docs/validation/ga-final-decision.md` now exists as a historical artifact
  recording the earlier `cut another RC` outcome and explicitly routes the
  next decision back through renewed GAREL after the successful `v1.2.0-rc7`
  recut.
- `docs/validation/ga-rc-evidence.md` records the successful
  `v1.2.0-rc7` GARECUT run and the new remaining release blocker: a GitHub
  Actions Node 20 deprecation annotation from
  `softprops/action-gh-release@v2` in `Create GitHub Release`.
- `.github/workflows/release-automation.yml` already uses
  `peter-evans/create-pull-request@v8`, still uses
  `softprops/action-gh-release@v2`, defaults to `v1.2.0-rc7`, and accepts
  `release_type` values `custom|patch|minor|major`; there is no separate
  `stable` input, so a stable GA dispatch must use the real workflow contract.
- `tests/test_release_metadata.py` still freezes the active prerelease
  contract to `1.2.0-rc7` / `v1.2.0-rc7`.
- `docs/validation/ga-release-evidence.md` remains intentionally absent and is
  still reserved for the `ship GA` branch only.
- The worktree also contains user-owned in-flight updates in
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`,
  `tests/docs/test_garecut_rc_recut_contract.py`, and
  `tests/docs/test_garel_ga_release_contract.py`; GAREL execution must build
  on those edits rather than revert them.

## Interface Freeze Gates

- [ ] IF-0-GAREL-1 - Final decision contract:
      `docs/validation/ga-final-decision.md` states exactly one of `ship GA`,
      `cut another RC`, or `defer GA`, cites the canonical GABASE, GAGOV,
      GASUPPORT, GAE2E, GAOPS, and GARECUT evidence inputs, carries the
      `softprops/action-gh-release@v2` disposition, and names the next roadmap
      or RC scope whenever the answer is not `ship GA`.
- [ ] IF-0-GAREL-2 - Workflow-runtime and dispatch contract:
      `.github/workflows/release-automation.yml` and
      `tests/test_release_metadata.py` either remove the
      `softprops/action-gh-release@v2` Node 20 warning from the stable path or
      freeze an explicit accepted-risk posture in the final decision artifact
      before any GA dispatch, and the GA dispatch command uses the actual
      workflow interface.
- [ ] IF-0-GAREL-3 - Release-channel alignment contract:
      if the decision is `ship GA`, repo-owned version surfaces, public docs,
      support claims, installer defaults, GitHub Latest posture, and Docker
      `latest` guidance align on stable `1.2.0` / `v1.2.0`; otherwise those
      surfaces remain on prerelease `1.2.0-rc7` / `v1.2.0-rc7` with no stable
      mutation.
- [ ] IF-0-GAREL-4 - Post-release verification contract:
      the selected channel state is proven by targeted docs tests,
      release-metadata checks, release-smoke coverage, clean-checkout or fresh
      install verification, and GitHub release metadata probes, and any
      failure blocks GA instead of being reduced away in prose.
- [ ] IF-0-GAREL-5 - GA evidence reducer contract:
      `docs/validation/ga-release-evidence.md` is written only on the
      `ship GA` branch and records dispatch inputs, workflow URL and run ID,
      `headSha`, release/channel state, GitHub Latest posture, PyPI and GHCR
      identities, install verification, rollback disposition, and redacted
      metadata only.

## Lane Index & Dependencies

- SL-0 - Renewed GAREL contract tests; Depends on: GARECUT; Blocks: SL-1, SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-1 - Release workflow warning remediation and dispatch policy; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-2 - Final decision reducer; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4, SL-5, SL-6; Parallel-safe: no
- SL-3 - Stable package and changelog contract; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4, SL-5, SL-6; Parallel-safe: yes
- SL-4 - Public docs and operator channel alignment; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SL-5, SL-6; Parallel-safe: yes
- SL-5 - GA dispatch and post-release verification; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: SL-6; Parallel-safe: no
- SL-6 - GA release evidence reducer; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4, SL-5; Blocks: GAREL acceptance; Parallel-safe: no

## Lanes

### SL-0 - Renewed GAREL Contract Tests

- **Scope**: Refresh the phase-specific contract tests so the renewed GAREL
  path is frozen around the `rc7` evidence and the `softprops` runtime
  warning before any stable mutation is attempted.
- **Owned files**: `tests/docs/test_garel_ga_release_contract.py`
- **Interfaces provided**: IF-0-GAREL-1, IF-0-GAREL-2, IF-0-GAREL-3,
  IF-0-GAREL-4, IF-0-GAREL-5
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`,
  `tests/smoke/test_release_smoke_contract.py`,
  `README.md`, `CHANGELOG.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the GAREL docs contract test to require the renewed decision
    artifact to consume the successful `v1.2.0-rc7` recut evidence and to
    treat any older pre-GARECUT GAREL assumptions as stale.
  - test: Assert that the `softprops/action-gh-release@v2` Node 20 warning is
    either remediated in the workflow or explicitly dispositioned in
    `docs/validation/ga-final-decision.md` before any stable dispatch is
    allowed.
  - test: Assert that `docs/validation/ga-release-evidence.md` remains absent
    unless the renewed decision actually chooses `ship GA`.
  - test: Keep this file phase-specific and additive so GABASE, GARECUT,
    release-metadata, and release-smoke tests remain the lower-level contracts
    rather than being redefined here.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`

### SL-1 - Release Workflow Warning Remediation And Dispatch Policy

- **Scope**: Resolve or explicitly disposition the remaining release-workflow
  runtime warning and freeze the real GA dispatch interface before the final
  decision is reduced.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`
- **Interfaces provided**: IF-0-GAREL-2; workflow portions of
  IF-0-GAREL-3 and IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions;
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-readiness-checklist.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Reproduce the current workflow-runtime concern from the GARECUT
    evidence and use that exact `softprops/action-gh-release@v2` Node 20
    warning as the repair or acceptance target.
  - impl: Upgrade, replace, or explicitly risk-accept the
    `softprops/action-gh-release@v2` path for stable GA dispatch without
    reopening the already-remediated `create-pull-request@v8` work.
  - impl: Freeze the stable dispatch semantics against the real workflow
    shape: GA dispatch must use `gh workflow run "Release Automation" -f
    version=v1.2.0 -f release_type=custom -f auto_merge=false` unless the
    workflow contract itself is intentionally changed first.
  - impl: Update `tests/test_release_metadata.py` only where it needs to
    distinguish the stable `v1.2.0` path from the active `v1.2.0-rc7`
    prerelease contract; do not broaden this lane into unrelated release
    automation cleanup.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "softprops/action-gh-release|create-pull-request@v8|release_type|is_prerelease|v1\\.2\\.0-rc7|v1\\.2\\.0" .github/workflows/release-automation.yml tests/test_release_metadata.py`
  - verify: `gh run view 24919438766 --json url,headSha,status,conclusion,jobs`

### SL-2 - Final Decision Reducer

- **Scope**: Reduce the upstream GA-hardening evidence and workflow-runtime
  disposition into the singular renewed GAREL decision artifact before any
  stable mutation occurs.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: IF-0-GAREL-1; the decision input to
  IF-0-GAREL-3 and IF-0-GAREL-5
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow-runtime
  disposition; `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Write the renewed decision artifact only after the `softprops`
    warning disposition, support posture, operations evidence, and `rc7`
    evidence have been read together; a successful recut alone does not imply
    GA approval.
  - impl: Record exactly one decision: `ship GA`, `cut another RC`, or
    `defer GA`.
  - impl: If the decision is not `ship GA`, name the next roadmap or RC scope,
    keep all stable mutations blocked, and make
    `docs/validation/ga-release-evidence.md` explicitly unnecessary for that
    branch.
  - impl: If the decision is `ship GA`, state the exact prerequisites
    satisfied for stable `1.2.0` / `v1.2.0`, including the final disposition
    of the `softprops` runtime warning, before SL-3 through SL-6 mutate
    release surfaces.
  - impl: Preserve the historical-artifact and metadata-only reporting pattern
    already used by the GA evidence artifacts.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "ship GA|cut another RC|defer GA|ga-readiness-checklist|ga-governance-evidence|ga-e2e-evidence|ga-operations-evidence|ga-rc-evidence|softprops/action-gh-release@v2|Node 20|v1\\.2\\.0-rc7|v1\\.2\\.0" docs/validation/ga-final-decision.md`

### SL-3 - Stable Package And Changelog Contract

- **Scope**: Align repo-owned release metadata to the renewed final decision
  without directly mutating the public docs or runbooks.
- **Owned files**: `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`
- **Interfaces provided**: package/version portions of IF-0-GAREL-3 and
  IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow dispatch
  policy; SL-2 final decision artifact
- **Parallel-safe**: yes
- **Tasks**:
  - test: Treat this lane as conditional on SL-2. If the renewed decision is
    not `ship GA`, verify that `1.2.0-rc7` remains the active package contract
    and do not rewrite package metadata.
  - impl: If the renewed decision is `ship GA`, advance the repo-owned release
    identity from `1.2.0-rc7` / `v1.2.0-rc7` to stable `1.2.0` / `v1.2.0` in
    `pyproject.toml`, `mcp_server/__init__.py`, and the active changelog
    section.
  - impl: Keep the changelog explicit about the release-channel transition and
    any remaining non-GA or deferred surfaces instead of erasing prerelease
    history.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc7|1\\.2\\.0|v1\\.2\\.0-rc7|v1\\.2\\.0" pyproject.toml mcp_server/__init__.py CHANGELOG.md`

### SL-4 - Public Docs And Operator Channel Alignment

- **Scope**: Align user-facing docs, support tiers, installer defaults, and
  operator runbooks with the renewed GAREL decision after repo-owned metadata
  has settled.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`,
  `docs/DOCKER_GUIDE.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`
- **Interfaces provided**: public-doc portions of IF-0-GAREL-3 and
  IF-0-GAREL-4
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 workflow/runtime
  policy; SL-2 final decision artifact; SL-3 package and changelog contract
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use SL-0 to fail first on any doc or installer surface that claims
    GA or a stable release before the renewed decision artifact authorizes it.
  - impl: If the decision is `ship GA`, switch the active docs, support
    matrix, installer defaults, and operator runbooks from the current
    prerelease `rc7` posture to stable `1.2.0` guidance, including GitHub
    Latest and Docker `latest` expectations.
  - impl: If the decision is `cut another RC` or `defer GA`, keep the public
    surfaces on prerelease posture, but still refresh stale `rc5` or `rc6`
    wording so the repo describes the current `rc7` state accurately.
  - impl: Preserve the frozen support-tier vocabulary and v3 topology limits
    from GABASE and GASUPPORT; GAREL may narrow channel wording, but it must
    not broaden language/runtime claims or multi-worktree support.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc5|1\\.2\\.0-rc6|1\\.2\\.0-rc7|1\\.2\\.0|public-alpha|beta|GA|GitHub Latest|docker latest|ga-final-decision|ga-release-evidence" README.md docs/GETTING_STARTED.md docs/DOCKER_GUIDE.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1`

### SL-5 - GA Dispatch And Post-Release Verification

- **Scope**: Execute the stable release only when SL-2 chooses `ship GA`, then
  capture the operational verification needed to prove the final channel
  state.
- **Owned files**: none
- **Interfaces provided**: observed IF-0-GAREL-4 and runtime facts for
  IF-0-GAREL-5
- **Interfaces consumed**: SL-0 GAREL assertions; SL-1 release workflow and
  dispatch policy; SL-2 final decision; SL-3 stable package contract; SL-4
  public docs alignment
- **Parallel-safe**: no
- **Tasks**:
  - test: If SL-2 does not choose `ship GA`, stop here with no release
    mutation and preserve the no-op path for SL-6.
  - test: On the `ship GA` path, rerun the narrowed contract checks before
    dispatch so workflow policy, package metadata, changelog, docs, support
    claims, and installer defaults are coherent.
  - test: Re-qualify the release state with clean-branch, synchronized
    `origin/main`, stable-tag non-reuse, and release-workflow visibility checks
    immediately before dispatching GA.
  - impl: Dispatch Release Automation only after the `softprops` warning has
    been remediated or explicitly accepted in SL-2, using the real workflow
    input contract for stable `v1.2.0`.
  - impl: Watch the run to completion, then verify GitHub release, PyPI,
    GHCR, clean-checkout install flows, and release smokes against the stable
    artifacts.
  - impl: If any dispatch, publish, or post-release verification step fails,
    stop before claiming GA success and route the blocker back into
    `docs/validation/ga-final-decision.md` plus
    `docs/validation/ga-release-evidence.md`.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `git status --short --branch`
  - verify: `git fetch origin main --tags --prune`
  - verify: `git rev-parse HEAD origin/main`
  - verify: `git tag -l v1.2.0`
  - verify: `git ls-remote --tags origin refs/tags/v1.2.0`
  - verify: `gh workflow view "Release Automation"`
  - verify: `gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false`
  - verify: `gh run list --workflow "Release Automation" --limit 10`
  - verify: `gh run watch <run-id> --exit-status`
  - verify: `gh run view <run-id> --json url,headSha,status,conclusion,jobs`
  - verify: `gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,isLatest,publishedAt,targetCommitish,url,assets`
  - verify: `python -m pip index versions index-it-mcp`
  - verify: `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0`
  - verify: `make release-smoke`
  - verify: `make release-smoke-container`

### SL-6 - GA Release Evidence Reducer

- **Scope**: Reduce the renewed decision, stable release execution, and
  post-release verification into the canonical GA release evidence artifact.
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
    `ship GA` and SL-5 captured an actual stable release run plus
    post-release verification results.
  - impl: Record the stable dispatch inputs, run URL and run ID, `headSha`,
    per-job conclusions, tag target, GitHub release state including Latest
    posture, PyPI and GHCR identities, install and smoke verification, and
    rollback disposition using redacted metadata only.
  - impl: If SL-2 chose a non-ship path, keep this file absent and make
    `docs/validation/ga-final-decision.md` the only reducer artifact for the
    phase.
  - impl: Preserve the historical-artifact banner pattern and make the
    artifact explicit about whether the stable release succeeded, failed after
    dispatch, or was never attempted because the renewed decision did not
    authorize it.
  - verify: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py tests/smoke/test_release_smoke_contract.py -v --no-cov`
  - verify: `rg -n "Historical artifact|v1\\.2\\.0|Release Automation|run ID|GitHub release|isLatest|PyPI|GHCR|release-smoke|rollback|ship GA" docs/validation/ga-release-evidence.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual GAREL execution.

Contract and workflow checks:

```bash
uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
uv run pytest tests/smoke/test_release_smoke_contract.py -v --no-cov
rg -n "softprops/action-gh-release|create-pull-request@v8|release_type|is_prerelease|v1\\.2\\.0-rc7|v1\\.2\\.0" \
  .github/workflows/release-automation.yml \
  tests/test_release_metadata.py
gh run view 24919438766 --json url,headSha,status,conclusion,jobs
```

Decision and doc alignment checks:

```bash
uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py -v --no-cov
rg -n "ship GA|cut another RC|defer GA|softprops/action-gh-release@v2|Node 20|v1\\.2\\.0-rc7|v1\\.2\\.0" \
  docs/validation/ga-final-decision.md
rg -n "1\\.2\\.0-rc5|1\\.2\\.0-rc6|1\\.2\\.0-rc7|1\\.2\\.0|public-alpha|beta|GA|GitHub Latest|docker latest" \
  README.md \
  docs/GETTING_STARTED.md \
  docs/DOCKER_GUIDE.md \
  docs/MCP_CONFIGURATION.md \
  docs/SUPPORT_MATRIX.md \
  docs/operations/deployment-runbook.md \
  docs/operations/user-action-runbook.md \
  scripts/install-mcp-docker.sh \
  scripts/install-mcp-docker.ps1
```

Stable-release execution checks, only if SL-2 chooses `ship GA`:

```bash
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0
git ls-remote --tags origin refs/tags/v1.2.0
gh workflow view "Release Automation"
gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10
gh run watch <run-id> --exit-status
gh run view <run-id> --json url,headSha,status,conclusion,jobs
gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,isLatest,publishedAt,targetCommitish,url,assets
python -m pip index versions index-it-mcp
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0
make release-smoke
make release-smoke-container
```

## Acceptance Criteria

- [ ] `docs/validation/ga-final-decision.md` exists and states exactly one of
      `ship GA`, `cut another RC`, or `defer GA`, citing the canonical
      GABASE, GAGOV, GASUPPORT, GAE2E, GAOPS, and GARECUT evidence.
- [ ] The remaining `softprops/action-gh-release@v2` Node 20 warning is
      remediated or explicitly dispositioned before any GA dispatch is
      attempted.
- [ ] If the renewed decision is not `ship GA`, no stable release mutation
      occurs and the final decision artifact names the next roadmap or RC
      scope.
- [ ] If the renewed decision is `ship GA`, repo-owned metadata, public docs,
      support claims, installer defaults, GitHub Latest posture, and Docker
      `latest` guidance all align on stable `1.2.0` / `v1.2.0`.
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
