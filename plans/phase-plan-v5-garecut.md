---
phase_loop_plan_version: 1
phase: GARECUT
roadmap: specs/phase-plans-v5.md
roadmap_sha256: df5244856bbe79d0f3fe5e6231eaf120b0ff448335a3f8f8134317ebc81f4802
---
# GARECUT: Post-Remediation RC Recut

## Context

GARECUT is the renewed phase-8 prerelease recut in the v5 GA-hardening
roadmap. The current `GAREL` decision in
`docs/validation/ga-final-decision.md` now records `cut another RC` after
remediating `softprops/action-gh-release@v2` to
`softprops/action-gh-release@v3`, so this phase is no longer the old `rc7`
recut. It is a new prerelease soak on the newly remediated release path before
any later GA decision is reconsidered.

Current repo state gathered during planning:

- The checkout is on `main` at `a3adcea5cd569571a2c4ce3d863317e9f14519bc`,
  matching `origin/main`, and the active roadmap hash is
  `df5244856bbe79d0f3fe5e6231eaf120b0ff448335a3f8f8134317ebc81f4802`.
- `.codex/phase-loop/state.json` marks `GAREL` as executed, `GARECUT` as
  unplanned, and carries ledger warnings that older GARECUT/GAREL provenance is
  stale under the amended roadmap.
- The worktree is intentionally dirty with user-owned follow-through in
  `.github/workflows/release-automation.yml`,
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-readiness-checklist.md`,
  `tests/docs/test_garecut_rc_recut_contract.py`,
  `tests/docs/test_garel_ga_release_contract.py`,
  `tests/test_release_metadata.py`, and the staged
  `plans/phase-plan-v5-garel.md`; GARECUT execution must preserve those edits
  and treat the modified roadmap as the active baseline rather than reverting
  it.
- `docs/validation/ga-final-decision.md` explicitly sets the next recut target
  to `v1.2.0-rc8`, states that another prerelease soak is required on the
  `softprops/action-gh-release@v3` path, and warns that older downstream
  GARECUT or GAREL plans are stale.
- `docs/validation/ga-rc-evidence.md` is still the successful `rc7` recut
  artifact. It remains the canonical prerelease evidence writer, but it must be
  refreshed for the next recut attempt instead of being treated as current
  proof for the new workflow path.
- Repo-owned release surfaces are still frozen to `1.2.0-rc7` /
  `v1.2.0-rc7` in `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`,
  installer helpers, and `tests/test_release_metadata.py`, while
  `.github/workflows/release-automation.yml` already carries the remediated
  `softprops/action-gh-release@v3` path plus a `GARECUT release contract
  target: v1.2.0-rc7` marker.
- Absent contradictory product input, this plan freezes the renewed recut
  target as `1.2.0-rc8` / `v1.2.0-rc8` and requires local plus remote non-reuse
  checks before dispatch.

## Interface Freeze Gates

- [ ] IF-0-GARECUT-1 - Renewed recut version and workflow contract:
      `.github/workflows/release-automation.yml`, `pyproject.toml`,
      `mcp_server/__init__.py`, `CHANGELOG.md`, installer helpers, and
      `tests/test_release_metadata.py` freeze `1.2.0-rc8` / `v1.2.0-rc8` as
      the active recut target, retain
      `peter-evans/create-pull-request@v8`, retain
      `softprops/action-gh-release@v3`, keep `release_type=custom`, and
      preserve prerelease-only GitHub Latest plus stable-only Docker `latest`
      behavior.
- [ ] IF-0-GARECUT-2 - Pre-dispatch safety contract:
      release dispatch is allowed only when the release-affecting worktree is
      clean enough for mutation, `HEAD` matches `origin/main`, the remediated
      workflow is visible, and `v1.2.0-rc8` is unused both locally and on
      origin.
- [ ] IF-0-GARECUT-3 - Remediated recut observation contract:
      GARECUT captures the Release Automation run URL, run ID, `headSha`,
      per-job conclusions, `Create GitHub Release` log disposition, release
      branch or PR disposition, GitHub release state, PyPI publication, and
      GHCR image identity for `v1.2.0-rc8`.
- [ ] IF-0-GARECUT-4 - RC-only channel policy contract:
      the recut remains prerelease-only, GitHub Latest stays excluded, Docker
      `latest` stays stable-only, and no GA docs or stable release mutation is
      introduced by the `rc8` soak itself.
- [ ] IF-0-GARECUT-5 - Decision handoff contract:
      `docs/validation/ga-rc-evidence.md` records the fresh remediated recut
      evidence, and `docs/validation/ga-final-decision.md` remains a historical
      `cut another RC` artifact while explicitly routing the next downstream
      work either back to renewed `GAREL` on top of successful `rc8` proof or
      back to GARECUT remediation/rerun if the recut blocks or fails.

## Lane Index & Dependencies

- SL-0 - Renewed GARECUT contract tests; Depends on: GAREL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - RC8 version and remediated workflow freeze; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-2 - RC8 dispatch and workflow observation; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - RC8 recut evidence reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Final decision handoff refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GARECUT acceptance; Parallel-safe: no

## Lanes

### SL-0 - Renewed GARECUT Contract Tests

- **Scope**: Refresh the phase-specific contract tests so the renewed GARECUT
  path is frozen around the `rc8` recut target and the already-remediated
  `softprops/action-gh-release@v3` workflow path before any release mutation is
  attempted.
- **Owned files**: `tests/docs/test_garecut_rc_recut_contract.py`
- **Interfaces provided**: IF-0-GARECUT-1, IF-0-GARECUT-2,
  IF-0-GARECUT-3, IF-0-GARECUT-4, IF-0-GARECUT-5
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `specs/phase-plans-v5.md`,
  `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`,
  `tests/docs/test_garel_ga_release_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the GARECUT docs contract test to require the renewed recut
    target `1.2.0-rc8` / `v1.2.0-rc8`, the remediated
    `softprops/action-gh-release@v3` workflow path, and the current roadmap
    steering that routes through another prerelease soak after GAREL.
  - test: Assert that `docs/validation/ga-final-decision.md` remains
    historical and non-authorizing for GA while naming `GARECUT` as satisfied
    only after fresh `rc8` evidence exists.
  - test: Assert that `docs/validation/ga-rc-evidence.md` remains the only
    canonical recut evidence writer and that `ga-final-decision.md` cannot
    silently become a new GA decision inside this phase.
  - test: Keep this file additive and phase-specific so the existing GAREL and
    release-metadata tests remain the lower-level contracts instead of being
    reopened here.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov`

### SL-1 - RC8 Version And Remediated Workflow Freeze

- **Scope**: Advance the repo-owned release contract from rc7 to rc8 on the
  already-remediated workflow path without widening into GA channel changes.
- **Owned files**: `.github/workflows/release-automation.yml`,
  `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`,
  `scripts/install-mcp-docker.sh`, `scripts/install-mcp-docker.ps1`,
  `tests/test_release_metadata.py`
- **Interfaces provided**: IF-0-GARECUT-1; repo-owned portions of
  IF-0-GARECUT-2 and IF-0-GARECUT-4
- **Interfaces consumed**: SL-0 GARECUT assertions;
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Re-run `tests/test_release_metadata.py` first and treat this lane as
    a repair-plus-version-bump lane only for the repo-owned recut contract.
  - impl: Advance the frozen release identity from `1.2.0-rc7` /
    `v1.2.0-rc7` to `1.2.0-rc8` / `v1.2.0-rc8` in the workflow defaults,
    package metadata, changelog, installer defaults, and release-metadata
    assertions.
  - impl: Preserve `release_type=custom`, `auto_merge=false`,
    `peter-evans/create-pull-request@v8`,
    `softprops/action-gh-release@v3`, prerelease GitHub release behavior, and
    stable-only Docker `latest`; do not introduce stable `1.2.0` behavior in
    this lane.
  - impl: Keep docs churn narrow by only touching the installer/version
    surfaces that `tests/test_release_metadata.py` already treats as part of
    the active release contract.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc8|v1\\.2\\.0-rc8|create-pull-request@v8|softprops/action-gh-release@v3|release_type=custom|auto_merge=false|latest" .github/workflows/release-automation.yml pyproject.toml mcp_server/__init__.py CHANGELOG.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1 tests/test_release_metadata.py`

### SL-2 - RC8 Dispatch And Workflow Observation

- **Scope**: Dispatch the remediated rc8 prerelease and capture the actual
  workflow and publication facts needed for downstream reduction.
- **Owned files**: none (local git and GitHub release state only)
- **Interfaces provided**: observed IF-0-GARECUT-2 and IF-0-GARECUT-3; runtime
  facts for IF-0-GARECUT-4 and IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 assertions; SL-1 rc8 release contract;
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-run the narrowed GARECUT and release-metadata checks locally
    before dispatch so the repo-owned rc8 surfaces are coherent.
  - test: Run the required pre-dispatch probes immediately before mutation:
    `git status --short --branch`, `git fetch origin main --tags --prune`,
    `git rev-parse HEAD origin/main`, `git tag -l v1.2.0-rc8`,
    `git ls-remote --tags origin refs/tags/v1.2.0-rc8`, and
    `gh workflow view "Release Automation"`.
  - impl: If the release-affecting worktree is dirty, `HEAD` differs from
    `origin/main`, or `v1.2.0-rc8` already exists locally or remotely, stop
    before dispatch and carry the blocked state into SL-3 and SL-4.
  - impl: Dispatch `gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false`, watch the run to completion, and capture run identity plus per-job outcomes.
  - impl: Record the `Create GitHub Release` job log disposition, GitHub
    prerelease state, release branch or PR disposition, PyPI publication, and
    GHCR image identity on the remediated workflow path; do not mutate GA state
    even if the recut succeeds.
  - verify: `uv run pytest tests/test_release_metadata.py tests/docs/test_garecut_rc_recut_contract.py -v --no-cov`
  - verify: `git status --short --branch`
  - verify: `git fetch origin main --tags --prune`
  - verify: `git rev-parse HEAD origin/main`
  - verify: `git tag -l v1.2.0-rc8`
  - verify: `git ls-remote --tags origin refs/tags/v1.2.0-rc8`
  - verify: `gh workflow view "Release Automation"`
  - verify: `gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false`
  - verify: `gh run list --workflow "Release Automation" --limit 10`
  - verify: `gh run watch <run-id> --exit-status`
  - verify: `gh run view <run-id> --json url,headSha,status,conclusion,jobs`
  - verify: `gh run view <run-id> --job <create-github-release-job-id> --log`
  - verify: `gh release view v1.2.0-rc8 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets`
  - verify: `gh pr list --state all --head release/v1.2.0-rc8 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title`
  - verify: `python -m pip index versions index-it-mcp --pre`
  - verify: `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8`

### SL-3 - RC8 Recut Evidence Reducer

- **Scope**: Reduce the rc8 pre-dispatch, dispatch, workflow, and publication
  facts into the canonical prerelease evidence artifact.
- **Owned files**: `docs/validation/ga-rc-evidence.md`
- **Interfaces provided**: IF-0-GARECUT-3, IF-0-GARECUT-4,
  and the evidence portion of IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 GARECUT assertions; SL-1 rc8 contract
  surfaces; SL-2 recut observation facts
- **Parallel-safe**: no
- **Tasks**:
  - test: Rewrite `docs/validation/ga-rc-evidence.md` only after SL-2 has a
    terminal outcome so the artifact reflects one coherent rc8 recut attempt.
  - impl: Record exact UTC capture time, selected commit, local and remote tag
    non-reuse results, dispatch inputs, run URL and ID, per-job conclusions,
    `Create GitHub Release` log disposition, release branch or PR disposition,
    GitHub prerelease state, PyPI package identity, GHCR tag identity, and
    rollback or no-rollback disposition for `v1.2.0-rc8`.
  - impl: If SL-2 stops before dispatch or fails mid-run, keep the artifact
    explicit about the blocked or failed state instead of implying a successful
    recut.
  - impl: Preserve metadata-only reporting; do not print tokens, raw logs, or
    secret-bearing command output.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "v1\\.2\\.0-rc8|Release Automation|PyPI|GHCR|softprops/action-gh-release@v3|prerelease|latest|blocked before dispatch|workflow failed after dispatch|recut succeeded" docs/validation/ga-rc-evidence.md`

### SL-4 - Final Decision Handoff Refresh

- **Scope**: Refresh the historical GA decision artifact so it clearly hands
  the next downstream work either back to renewed GAREL on top of fresh rc8
  evidence or back to GARECUT remediation if the recut did not land cleanly.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: final-decision portion of IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 GARECUT assertions; SL-1 rc8 workflow
  disposition; SL-2 recut observation facts; SL-3 refreshed
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Keep `docs/validation/ga-final-decision.md` historical and
    non-authorizing for GA during GARECUT; this lane may refresh next-step
    status, but it must not mutate the repo into a new stable-release decision.
  - impl: Preserve the existing GAREL decision rationale that another RC is
    required because `softprops/action-gh-release@v3` has not yet been soaked
    on a prerelease candidate.
  - impl: If the rc8 recut succeeds, add or refresh a status section that
    references the new `v1.2.0-rc8` evidence outcome and states that the
    repository is ready for a renewed GAREL decision phase.
  - impl: If the rc8 recut fails or is blocked, keep the next step on
    remediating or rerunning GARECUT rather than reopening GA.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "cut another RC|GARECUT|v1\\.2\\.0-rc8|renewed GAREL|ship GA|defer GA|softprops/action-gh-release@v3" docs/validation/ga-final-decision.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual GARECUT execution.

Contract and repo-owned version checks:

```bash
uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
rg -n "1\\.2\\.0-rc8|v1\\.2\\.0-rc8|create-pull-request@v8|softprops/action-gh-release@v3|release_type=custom|auto_merge=false|latest" \
  .github/workflows/release-automation.yml \
  pyproject.toml \
  mcp_server/__init__.py \
  CHANGELOG.md \
  scripts/install-mcp-docker.sh \
  scripts/install-mcp-docker.ps1 \
  tests/test_release_metadata.py
```

Pre-dispatch and recut observation:

```bash
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc8
git ls-remote --tags origin refs/tags/v1.2.0-rc8
gh workflow view "Release Automation"
gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10
gh run watch <run-id> --exit-status
gh run view <run-id> --json url,headSha,status,conclusion,jobs
gh run view <run-id> --job <create-github-release-job-id> --log
gh release view v1.2.0-rc8 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh pr list --state all --head release/v1.2.0-rc8 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
python -m pip index versions index-it-mcp --pre
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8
```

Reducer artifact checks:

```bash
uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garel_ga_release_contract.py -v --no-cov
rg -n "v1\\.2\\.0-rc8|Release Automation|PyPI|GHCR|softprops/action-gh-release@v3|renewed GAREL|blocked before dispatch|workflow failed after dispatch|recut succeeded" \
  docs/validation/ga-rc-evidence.md \
  docs/validation/ga-final-decision.md
git status --short -- docs/validation/ga-rc-evidence.md docs/validation/ga-final-decision.md
```

## Acceptance Criteria

- [ ] Repo-owned release surfaces and the remediated workflow freeze
      `1.2.0-rc8` / `v1.2.0-rc8`, retain
      `peter-evans/create-pull-request@v8` and
      `softprops/action-gh-release@v3`, and preserve prerelease-only GitHub
      Latest plus stable-only Docker `latest` policy.
- [ ] Pre-dispatch checks confirm a clean enough release-affecting worktree,
      `HEAD == origin/main`, workflow visibility, and no reused local or remote
      `v1.2.0-rc8` tag before dispatch.
- [ ] Release Automation is dispatched only with
      `version=v1.2.0-rc8`, `release_type=custom`, and `auto_merge=false`.
- [ ] The remediated recut run records terminal workflow results, `Create
      GitHub Release` log disposition, GitHub prerelease state, PyPI package
      publication, GHCR image identity, and release branch or PR disposition
      for `v1.2.0-rc8`.
- [ ] `docs/validation/ga-rc-evidence.md` records the fresh rc8 recut outcome
      using metadata-only reporting.
- [ ] `docs/validation/ga-final-decision.md` remains historical, references the
      rc8 outcome, and routes the next downstream work to renewed GAREL only if
      the recut succeeds; otherwise it keeps the next step on GARECUT
      remediation or rerun.
