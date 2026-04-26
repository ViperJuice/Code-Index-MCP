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

GADISP is the v5 GA-hardening phase that dispatches the stable `v1.2.0`
release from a clean synced tree and records the post-release evidence after
the workflow reaches a terminal state. The GAREL stable surfaces are already
committed on `main`; this plan intentionally does not add pre-dispatch tests,
stable-surface edits, support-matrix updates, or customer-doc rewrites.

The current roadmap hash is
`4b09568b3e451da4b9d1d154a073ede1d3903c8e7fc5cb8111dec3fbcec10fd1`.
The previous GADISP plan is stale for execution because it mixed contract-test
and docs-alignment edits into a `phase_loop_mutation: release_dispatch` phase.
This replacement keeps the phase dispatch-only until the workflow has a
terminal outcome. The only repo-owned mutation in this phase is the
dispatch-dependent evidence artifact.

The accepted-risk disposition remains unchanged: the
`actions/download-artifact@v8` `Buffer()` warning observed on the successful
digest-verified `v1.2.0-rc8` release run is non-blocking for stable dispatch and
must be recorded as accepted release evidence metadata.

## Interface Freeze Gates

- [ ] IF-0-GADISP-1 - Clean-tree release dispatch preflight:
      execution starts from clean `main`, `HEAD` equals `origin/main`,
      `docs/validation/ga-final-decision.md` still selects `ship GA`, stable
      `v1.2.0` surfaces already exist in committed files, the Release
      Automation workflow is visible, and no local or remote `v1.2.0` tag
      exists before dispatch.
- [ ] IF-0-GADISP-2 - Stable dispatch observation:
      Release Automation is dispatched exactly with `version=v1.2.0`,
      `release_type=custom`, and `auto_merge=false`; the selected run is
      watched to terminal state; and the captured facts include run URL, run
      ID, `headSha`, job conclusions, publication states, install/container
      verification, and warning disposition.
- [ ] IF-0-GADISP-3 - GA release evidence:
      `docs/validation/ga-release-evidence.md` records one coherent stable
      dispatch attempt using redacted metadata only, including blocked/failed
      details if the workflow does not complete successfully.

## Lane Index & Dependencies

- SL-0 - Clean dispatch qualification; Depends on: GAREL; Blocks: SL-1; Parallel-safe: no
- SL-1 - Stable GA workflow dispatch and observation; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - GA release evidence reducer; Depends on: SL-1; Blocks: GADISP acceptance; Parallel-safe: no

## Lanes

### SL-0 - Clean Dispatch Qualification

- **Scope**: Prove the repository and release target are safe to dispatch
  without mutating repo files.
- **Owned files**: none
- **Interfaces provided**: IF-0-GADISP-1
- **Interfaces consumed**: `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`, `pyproject.toml`,
  `mcp_server/__init__.py`, `CHANGELOG.md`, `README.md`
- **Parallel-safe**: no
- **Tasks**:
  - verify: Run the dispatch gate probes immediately before mutation:
    `git status --short --branch`, `git fetch origin main --tags --prune`,
    `git rev-parse HEAD origin/main`, `git tag -l v1.2.0`,
    `git ls-remote --tags origin refs/tags/v1.2.0`, and
    `gh workflow view "Release Automation"`.
  - verify: Run the existing release-contract smoke without adding or editing
    tests: `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov`.
  - impl: Stop before dispatch if the worktree is dirty, `HEAD` differs from
    `origin/main`, `v1.2.0` already exists locally or remotely,
    `docs/validation/ga-final-decision.md` no longer selects `ship GA`, or the
    Release Automation workflow is unavailable.

### SL-1 - Stable GA Workflow Dispatch And Observation

- **Scope**: Dispatch the stable GA release workflow once and watch it to
  terminal state.
- **Owned files**: none
- **Interfaces provided**: IF-0-GADISP-2
- **Interfaces consumed**: IF-0-GADISP-1,
  `.github/workflows/release-automation.yml`
- **Parallel-safe**: no
- **Tasks**:
  - verify: Dispatch
    `gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false`.
  - verify: Identify the new workflow run from `gh run list --workflow "Release Automation" --limit 10`, preferring the run whose `headSha` matches the qualified `HEAD`.
  - verify: Watch the run to completion with `gh run watch <run-id> --exit-status`.
  - verify: Capture terminal workflow facts with
    `gh run view <run-id> --json url,headSha,status,conclusion,jobs`.
  - verify: Capture GitHub release state with
    `gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets`.
  - verify: Capture GitHub Latest posture with
    `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name,prerelease,draft,html_url,target_commitish,published_at}'`.
  - verify: Capture release-branch or PR disposition with
    `gh pr list --state all --head release/v1.2.0 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title`.
  - verify: Capture PyPI and GHCR identity metadata with
    `curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0/json` and
    `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0`.
  - verify: Inspect the relevant workflow logs for the accepted
    `actions/download-artifact@v8` `Buffer()` warning without copying raw
    secret-bearing output into repo artifacts.
  - impl: If the workflow fails, continue to SL-2 and record the failed
    terminal state. Do not create another dispatch attempt in the same phase
    unless an operator explicitly authorizes retry.

### SL-2 - GA Release Evidence Reducer

- **Scope**: Create the canonical evidence artifact for the stable dispatch
  attempt after SL-1 reaches terminal state.
- **Owned files**: `docs/validation/ga-release-evidence.md`
- **Interfaces provided**: IF-0-GADISP-3
- **Interfaces consumed**: IF-0-GADISP-1, IF-0-GADISP-2,
  `docs/validation/ga-final-decision.md`, `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - impl: Write `docs/validation/ga-release-evidence.md` with capture time,
    active plan, qualified commit, dispatch inputs, preflight results, run URL,
    run ID, `headSha`, terminal workflow conclusion, job conclusions, GitHub
    release state, GitHub Latest posture, release branch or PR disposition,
    PyPI publication identity, GHCR image identity, install/container
    verification outcome, rollback or no-rollback disposition, and the accepted
    `actions/download-artifact@v8` `Buffer()` warning metadata.
  - impl: If SL-1 blocked or failed, make the evidence explicit about that
    blocked or failed state rather than implying a successful GA launch.
  - impl: Preserve metadata-only reporting. Do not print raw tokens, raw
    private logs, or secret-bearing output.
  - verify: `rg -n "v1\\.2\\.0|Release Automation|GitHub Latest|PyPI|GHCR|Buffer\\(\\)|rollback|no rollback|dispatch|conclusion" docs/validation/ga-release-evidence.md`.
  - verify: `git diff --check`.

## Verification

Run during execution only:

```bash
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0
git ls-remote --tags origin refs/tags/v1.2.0
gh workflow view "Release Automation"
uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov
gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10
gh run watch <run-id> --exit-status
gh run view <run-id> --json url,headSha,status,conclusion,jobs
gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name,prerelease,draft,html_url,target_commitish,published_at}'
gh pr list --state all --head release/v1.2.0 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0/json
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0
rg -n "v1\\.2\\.0|Release Automation|GitHub Latest|PyPI|GHCR|Buffer\\(\\)|rollback|no rollback|dispatch|conclusion" docs/validation/ga-release-evidence.md
git diff --check
```

## Acceptance Criteria

- The stable release workflow is dispatched once from clean synced `main`, or
  the evidence artifact clearly records the pre-dispatch blocker.
- The workflow terminal state and publication identities are captured as
  redacted metadata.
- `docs/validation/ga-release-evidence.md` is the only repo-owned output from
  this phase.
- No customer docs, stable surfaces, support tiers, topology claims, or tests
  are changed by this dispatch phase.
