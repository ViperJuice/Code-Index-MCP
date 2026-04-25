---
phase_loop_plan_version: 1
phase: GADISP
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 4b09568b3e451da4b9d1d154a073ede1d3903c8e7fc5cb8111dec3fbcec10fd1
phase_loop_mutation: release_dispatch
release_base_ref: origin/main
---
# GADISP: GA Stable Dispatch And Release Evidence

## Context

GADISP is the eighth phase in the v5 GA-hardening roadmap and the only stable
GA mutation phase. The roadmap hash is
`4b09568b3e451da4b9d1d154a073ede1d3903c8e7fc5cb8111dec3fbcec10fd1`, the
checkout is on clean synced `main` at
`fbac09c931236d97d4457d041fbf358654999274`, and `.codex/phase-loop/state.json`
already marks `GADISP` as the current planned phase under this roadmap.

Current repo state gathered during planning:

- `docs/validation/ga-final-decision.md` is already the renewed GAREL artifact.
  It records `ship GA`, routes stable mutation only to downstream `GADISP`,
  preserves `v1.2.0-rc8` as historical evidence, and carries the accepted
  non-blocking `actions/download-artifact@v8` `Buffer()` warning disposition.
- Repo-owned stable surfaces are already prepared for `v1.2.0` / `v1.2.0`:
  `.github/workflows/release-automation.yml`, package metadata, installer
  defaults, and active customer docs already point at the stable version.
- `docs/validation/ga-release-evidence.md` does not exist yet. That absence is
  still explicitly referenced by the current README, runbooks, checklist, and
  GAREL-focused tests, so execution must update only the files that are
  supposed to flip once stable dispatch actually happens.
- Existing contract tests still freeze a pre-dispatch world in a few places:
  `tests/docs/test_garel_ga_release_contract.py`,
  `tests/docs/test_gabase_ga_readiness_contract.py`, and
  `tests/test_release_metadata.py` still assume release evidence is deferred or
  absent, and there is no dedicated `GADISP` contract test yet.
- The accepted-risk disposition is part of the stable dispatch contract:
  `actions/download-artifact@v8` is still GitHub's current published line, and
  the successful `v1.2.0-rc8` run already showed the same non-fatal
  `Buffer()` warning. GADISP must record that warning as accepted metadata in
  stable release evidence rather than reopening stable-surface prep or cutting
  another RC.

## Interface Freeze Gates

- [ ] IF-0-GADISP-1 - Stable pre-dispatch qualification contract:
      local execution requires a clean expected release branch, synchronized
      `origin/main`, a live `ship GA` decision in
      `docs/validation/ga-final-decision.md`, already-committed stable
      `v1.2.0` surfaces, visible Release Automation workflow metadata, and no
      reused local or remote `v1.2.0` tag before dispatch.
- [ ] IF-0-GADISP-2 - Stable dispatch observation contract:
      Release Automation is dispatched exactly with
      `version=v1.2.0`, `release_type=custom`, and `auto_merge=false`; the run
      is watched to completion; and the captured facts include run URL, run ID,
      `headSha`, per-job conclusions, stable GitHub release state, GitHub
      Latest posture, release branch or PR disposition, PyPI publication, GHCR
      image identity, and the accepted
      `actions/download-artifact@v8` `Buffer()` warning metadata.
- [ ] IF-0-GADISP-3 - GA release evidence reducer contract:
      `docs/validation/ga-release-evidence.md` becomes the canonical stable
      release artifact, records only redacted metadata, and explicitly states
      dispatch inputs, preflight qualification, workflow observation,
      publication identities, install/container verification, and rollback or
      no-rollback disposition for `v1.2.0`.
- [ ] IF-0-GADISP-4 - Post-dispatch docs and regression contract:
      the README, getting-started/support/runbook surfaces, readiness checklist,
      and GADISP-adjacent tests no longer describe stable dispatch as pending or
      `ga-release-evidence.md` as absent, but they also do not widen support
      tiers, topology claims, or non-GA/runtime promises beyond what the
      release evidence actually proves.

## Lane Index & Dependencies

- SL-0 - GADISP contract tests; Depends on: GAREL; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Stable GA dispatch qualification and workflow observation; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - GA release evidence reducer; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Post-release docs and regression alignment; Depends on: SL-0, SL-1, SL-2; Blocks: GADISP acceptance; Parallel-safe: no

## Lanes

### SL-0 - GADISP Contract Tests

- **Scope**: Freeze the post-dispatch contract before mutation so execution
  changes only the stable release evidence and the small set of docs/tests that
  must reflect a completed GA dispatch.
- **Owned files**: `tests/docs/test_gadisp_ga_dispatch_contract.py`,
  `tests/docs/test_garel_ga_release_contract.py`,
  `tests/docs/test_gabase_ga_readiness_contract.py`,
  `tests/test_release_metadata.py`
- **Interfaces provided**: IF-0-GADISP-1, IF-0-GADISP-2, IF-0-GADISP-3,
  IF-0-GADISP-4
- **Interfaces consumed**: `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-rc-evidence.md`,
  `.github/workflows/release-automation.yml`,
  `README.md`,
  `docs/GETTING_STARTED.md`,
  `docs/SUPPORT_MATRIX.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated `tests/docs/test_gadisp_ga_dispatch_contract.py`
    that freezes the required `ga-release-evidence.md` sections, stable
    dispatch inputs, workflow observation fields, GitHub Latest posture, PyPI
    and GHCR identities, install/container verification, and rollback
    disposition.
  - test: Update `tests/docs/test_garel_ga_release_contract.py` so GAREL stays
    a historical pre-dispatch artifact after GADISP instead of asserting that
    `docs/validation/ga-release-evidence.md` must remain absent forever.
  - test: Update `tests/docs/test_gabase_ga_readiness_contract.py` so the
    checklist's evidence map routes `docs/validation/ga-release-evidence.md`
    to `GADISP` rather than `GAREL` and still preserves the pre-ship boundary.
  - test: Update `tests/test_release_metadata.py` so stable tag reuse and
    release metadata assertions reference the stable GA evidence path once
    `v1.2.0` exists, while still freezing `release_type=custom`,
    `auto_merge=false`, and the prepared workflow defaults.
  - impl: Keep this lane test-only; it defines the exact post-dispatch contract
    for SL-1 through SL-3 and should not mutate docs or evidence directly.
  - verify: `uv run pytest tests/docs/test_gadisp_ga_dispatch_contract.py tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov`

### SL-1 - Stable GA Dispatch Qualification And Workflow Observation

- **Scope**: Qualify the current stable `v1.2.0` release contract on clean
  synced `main`, dispatch Release Automation, and capture the live workflow and
  publication facts to terminal state.
- **Owned files**: `none`
- **Interfaces provided**: IF-0-GADISP-1, IF-0-GADISP-2; observed release
  facts consumed by SL-2 and SL-3
- **Interfaces consumed**: SL-0 GADISP assertions;
  `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`,
  `pyproject.toml`,
  `mcp_server/__init__.py`,
  `CHANGELOG.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-run the narrowed post-dispatch contract checks first so stable
    mutation starts only from the already-prepared `v1.2.0` repo state.
  - test: Run the required pre-dispatch probes immediately before mutation:
    `git status --short --branch`, `git fetch origin main --tags --prune`,
    `git rev-parse HEAD origin/main`, `git tag -l v1.2.0`,
    `git ls-remote --tags origin refs/tags/v1.2.0`, and
    `gh workflow view "Release Automation"`.
  - impl: If the worktree is dirty, `HEAD` differs from `origin/main`, the
    stable `ship GA` decision is no longer authoritative, the workflow is not
    visible, or `v1.2.0` already exists locally or remotely, stop before
    dispatch and carry the blocked state into SL-2 and SL-3.
  - impl: Dispatch `gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false`, watch the run to completion, and capture the run URL, run ID, `headSha`, and per-job conclusions.
  - impl: Record GitHub release state, GitHub Latest posture, release branch or
    PR disposition, PyPI `index-it-mcp 1.2.0` publication, GHCR
    `ghcr.io/viperjuice/code-index-mcp:v1.2.0` identity, and the accepted
    `actions/download-artifact@v8` `Buffer()` warning disposition from the
    `Create GitHub Release` job logs.
  - impl: If any preflight or publish-stage job fails, stop before claiming
    success and preserve the blocked or failed outcome for downstream evidence
    reduction.
  - verify: `uv run pytest tests/docs/test_gadisp_ga_dispatch_contract.py tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py -v --no-cov`
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
  - verify: `gh run view <run-id> --job <create-github-release-job-id> --log`
  - verify: `gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets`
  - verify: `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name,prerelease,draft,html_url,target_commitish,published_at}'`
  - verify: `gh pr list --state all --head release/v1.2.0 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title`
  - verify: `curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0/json`
  - verify: `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0`

### SL-2 - GA Release Evidence Reducer

- **Scope**: Reduce the stable pre-dispatch, dispatch, workflow, publication,
  and install-verification facts into the canonical GA release evidence
  artifact.
- **Owned files**: `docs/validation/ga-release-evidence.md`
- **Interfaces provided**: IF-0-GADISP-3; release facts consumed by SL-3
- **Interfaces consumed**: SL-0 GADISP assertions; SL-1 stable dispatch and
  publication facts; `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Rewrite `docs/validation/ga-release-evidence.md` only after SL-1 has
    a terminal outcome so the artifact reflects one coherent stable dispatch
    attempt.
  - impl: Record capture time, active phase plan, selected commit, dispatch
    inputs, qualification results, run URL and ID, `headSha`, per-job
    conclusions, GitHub stable release state, GitHub Latest posture, release
    branch or PR disposition, PyPI publication, GHCR image identity,
    install/container verification outcome, rollback or no-rollback
    disposition, and the accepted
    `actions/download-artifact@v8` `Buffer()` warning metadata.
  - impl: If dispatch is blocked before mutation or fails mid-run, keep the
    artifact explicit about the blocked or failed state instead of implying a
    successful GA launch.
  - impl: Preserve metadata-only reporting. Do not print raw tokens, raw logs,
    or secret-bearing output.
  - verify: `uv run pytest tests/docs/test_gadisp_ga_dispatch_contract.py tests/docs/test_garel_ga_release_contract.py tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "v1\\.2\\.0|Release Automation|GitHub Latest|PyPI|GHCR|Buffer\\(\\)|rollback|no rollback|dispatch attempted|conclusion" docs/validation/ga-release-evidence.md`

### SL-3 - Post-Release Docs And Regression Alignment

- **Scope**: Update the current docs and checklist surfaces that still describe
  stable dispatch as pending so they align with the completed release evidence
  without reopening support or topology decisions.
- **Owned files**: `README.md`,
  `docs/GETTING_STARTED.md`,
  `docs/SUPPORT_MATRIX.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/user-action-runbook.md`,
  `docs/validation/ga-readiness-checklist.md`
- **Interfaces provided**: IF-0-GADISP-4
- **Interfaces consumed**: SL-0 GADISP assertions; SL-1 stable dispatch facts;
  SL-2 `docs/validation/ga-release-evidence.md`;
  `docs/validation/ga-final-decision.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Use the refreshed GADISP, GAREL, GABASE, release-metadata, and GAOPS
    checks to fail first on stale "prepared stable", "dispatch pending", or
    "`ga-release-evidence.md` belongs to GAREL" wording.
  - impl: Update README, getting-started, support-matrix, and operator-runbook
    status language so the stable `v1.2.0` release points at
    `docs/validation/ga-release-evidence.md` as the canonical post-dispatch
    artifact instead of describing dispatch as still pending.
  - impl: Update the readiness checklist evidence map so
    `docs/validation/ga-release-evidence.md` is owned by `GADISP`, while
    preserving the historical pre-ship boundary and the frozen topology/support
    labels.
  - impl: Keep GAREL historical. Do not rewrite `docs/validation/ga-final-decision.md`
    into a post-release artifact; treat it as the authorizing decision that SL-2
    completed.
  - impl: Preserve the existing beta, experimental, unsupported, and
    disabled-by-default support tiers, the one-worktree-per-git-common-dir
    topology contract, and the accepted `GitHub Latest` / Docker `latest`
    channel posture exactly as observed in SL-1 and recorded in SL-2.
  - verify: `uv run pytest tests/docs/test_gadisp_ga_dispatch_contract.py tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/docs/test_gaops_operations_contract.py tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "ga-release-evidence|GADISP|prepared stable|dispatch still pending|stable release mutation and release evidence remain downstream-only|GitHub Latest|docker `latest`|v1\\.2\\.0" README.md docs/GETTING_STARTED.md docs/SUPPORT_MATRIX.md docs/operations/deployment-runbook.md docs/operations/user-action-runbook.md docs/validation/ga-readiness-checklist.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual GADISP execution.

Lane-specific contract checks:

```bash
uv run pytest tests/docs/test_gadisp_ga_dispatch_contract.py tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov
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
gh run view <run-id> --job <create-github-release-job-id> --log
gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name,prerelease,draft,html_url,target_commitish,published_at}'
gh pr list --state all --head release/v1.2.0 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0/json
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0
rg -n "v1\\.2\\.0|Release Automation|GitHub Latest|PyPI|GHCR|Buffer\\(\\)|rollback|dispatch attempted" docs/validation/ga-release-evidence.md
```

Whole-phase regression commands:

```bash
uv run pytest tests/docs tests/smoke tests/test_release_metadata.py tests/test_requirements_consolidation.py -v --no-cov
make alpha-production-matrix
make release-smoke
make release-smoke-container
git status --short --branch
test -e docs/validation/ga-release-evidence.md
```

## Acceptance Criteria

- [ ] Local pre-dispatch checks confirm clean release state, expected branch,
      synchronized `origin/main`, a live `ship GA` decision, and already
      committed stable `v1.2.0` surfaces before mutation begins.
- [ ] Release Automation dispatch uses stable `v1.2.0` with
      `release_type=custom` and `auto_merge=false` from this dedicated
      `phase_loop_mutation: release_dispatch` plan.
- [ ] Preflight gates, release artifact build, GitHub release creation, PyPI
      publish, GHCR publish, and release-smoke/container-smoke observation are
      watched to completion or captured explicitly as blocked/failed.
- [ ] `docs/validation/ga-release-evidence.md` records workflow URL, run ID,
      `headSha`, stable tag and release state, GitHub Latest posture, PyPI and
      GHCR identities, install/container verification, rollback disposition,
      and the accepted `actions/download-artifact@v8` `Buffer()` warning using
      metadata-only reporting.
- [ ] Docs and tests that previously described stable dispatch as pending now
      align to the completed release evidence without broadening support tiers,
      topology claims, or non-GA/runtime promises.
- [ ] No additional stable-surface preparation is mixed into the dispatch plan
      beyond evidence and status updates that depend on the actual stable
      release outcome.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v5-gadisp.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v5-gadisp.md
  artifact_state: staged
```
