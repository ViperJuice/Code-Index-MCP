---
phase_loop_plan_version: 1
phase: GARECUT
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 5f5c4b9cb20473287bad25c49816faf9bc110915e70010896436b3abc9cb4dca
---
# GARECUT: Post-Remediation RC Recut

## Context

GARECUT is the eighth phase in the v5 GA-hardening roadmap. GAREL already
concluded `cut another RC` in `docs/validation/ga-final-decision.md`, so this
phase is not another GA decision. It is a narrowly scoped operational recut on
the remediated release workflow path before any renewed GA ship/no-ship
reduction is reconsidered.

Current repo state gathered during planning:

- The checkout is on `main` at `3d5a3aa`, and `.codex/phase-loop/state.json`
  records `GAREL` as executed, `GARECUT` as unplanned, and the currently
  selected roadmap hash as
  `5f5c4b9cb20473287bad25c49816faf9bc110915e70010896436b3abc9cb4dca`.
- The worktree is intentionally dirty with user-owned GAREL follow-through in
  `.github/workflows/release-automation.yml`,
  `docs/validation/ga-rc-evidence.md`, `docs/validation/ga-final-decision.md`,
  `tests/test_release_metadata.py`, `tests/docs/test_garc_rc_soak_contract.py`,
  `tests/docs/test_garel_ga_release_contract.py`, and
  `specs/phase-plans-v5.md`; GARECUT execution must preserve those edits and
  treat the modified roadmap as the active baseline rather than reverting it.
- `docs/validation/ga-final-decision.md` already records the GAREL outcome as
  `cut another RC` because the prior successful `v1.2.0-rc6` soak did not
  exercise the remediated workflow contract.
- `.github/workflows/release-automation.yml` already uses
  `peter-evans/create-pull-request@v8`, so GARECUT should treat the Node 20
  path as remediated in source and focus on proving that remediated path under
  one more prerelease run.
- The repo-owned release surfaces that must move in lockstep for a recut are
  still frozen to `1.2.0-rc6` / `v1.2.0-rc6` in `pyproject.toml`,
  `mcp_server/__init__.py`, `CHANGELOG.md`, installer helpers, and
  `tests/test_release_metadata.py`.
- The roadmap exit criteria require a new RC after `v1.2.0-rc6`; absent any
  contradictory product input, this plan freezes that recut target as
  `1.2.0-rc7` / `v1.2.0-rc7` and requires local plus remote non-reuse checks
  before dispatch.
- `docs/validation/ga-rc-evidence.md` remains the canonical prerelease evidence
  artifact, while `docs/validation/ga-final-decision.md` remains the canonical
  historical record of why GA was deferred pending this recut.

## Interface Freeze Gates

- [ ] IF-0-GARECUT-1 - Recut version and workflow contract:
      `.github/workflows/release-automation.yml`, `pyproject.toml`,
      `mcp_server/__init__.py`, `CHANGELOG.md`, installer helpers, and
      `tests/test_release_metadata.py` freeze `1.2.0-rc7` / `v1.2.0-rc7` as
      the active recut target, retain `peter-evans/create-pull-request@v8`,
      keep `release_type=custom`, and preserve prerelease-only GitHub Latest
      and Docker `latest` behavior.
- [ ] IF-0-GARECUT-2 - Pre-dispatch safety contract:
      release dispatch is allowed only when the checkout is clean enough for
      release mutation, `HEAD` matches `origin/main`, the remediated workflow is
      visible, and `v1.2.0-rc7` is unused both locally and on origin.
- [ ] IF-0-GARECUT-3 - Remediated recut observation contract:
      GARECUT captures the Release Automation run URL, run ID, `headSha`,
      per-job conclusions, release branch or PR disposition, GitHub release
      state, PyPI publication, and GHCR image identity for `v1.2.0-rc7`.
- [ ] IF-0-GARECUT-4 - RC-only channel policy contract:
      the recut remains prerelease-only, GitHub Latest stays excluded, Docker
      `latest` stays stable-only, and no GA docs or stable release mutation is
      introduced by the `rc7` soak itself.
- [ ] IF-0-GARECUT-5 - Decision handoff contract:
      `docs/validation/ga-rc-evidence.md` records the fresh remediated recut
      evidence, and `docs/validation/ga-final-decision.md` remains a historical
      `cut another RC` artifact while explicitly pointing the next downstream
      work back to a renewed `GAREL` decision on top of the fresh `rc7` proof.

## Lane Index & Dependencies

- SL-0 - GARECUT contract tests; Depends on: GAREL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Recut version and remediated workflow freeze; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: yes
- SL-2 - Recut dispatch and workflow observation; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - RC recut evidence reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Final decision handoff refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: GARECUT acceptance; Parallel-safe: no

## Lanes

### SL-0 - GARECUT Contract Tests

- **Scope**: Freeze the rc7 recut target, remediated workflow expectations, and
  downstream decision handoff before any release mutation is attempted.
- **Owned files**: `tests/docs/test_garecut_rc_recut_contract.py`
- **Interfaces provided**: IF-0-GARECUT-1, IF-0-GARECUT-2,
  IF-0-GARECUT-3, IF-0-GARECUT-4, IF-0-GARECUT-5
- **Interfaces consumed**: `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-rc-evidence.md`,
  `docs/validation/ga-final-decision.md`,
  `.github/workflows/release-automation.yml`,
  `tests/test_release_metadata.py`,
  `tests/docs/test_garc_rc_soak_contract.py`,
  `tests/docs/test_garel_ga_release_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a dedicated GARECUT docs contract test that requires
    `docs/validation/ga-final-decision.md` to remain historical and
    non-authorizing for GA while naming `GARECUT` as fulfilled only after fresh
    `rc7` evidence exists.
  - test: Assert that the active recut target is exactly `1.2.0-rc7` /
    `v1.2.0-rc7`, that `peter-evans/create-pull-request@v8` remains the only
    allowed create-pull-request action, and that prerelease/latest policy stays
    frozen through the recut.
  - test: Assert that `ga-rc-evidence.md` is the only canonical recut evidence
    writer and that `ga-final-decision.md` cannot silently become a new GA
    decision inside this phase.
  - test: Keep this file additive and phase-specific so the existing GARC and
    GAREL tests remain the lower-level contracts instead of being reopened.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov`

### SL-1 - Recut Version And Remediated Workflow Freeze

- **Scope**: Advance the repo-owned release contract from rc6 to rc7 on the
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
  - impl: Advance the frozen release identity from `1.2.0-rc6` /
    `v1.2.0-rc6` to `1.2.0-rc7` / `v1.2.0-rc7` in the workflow defaults,
    package metadata, changelog, installer defaults, and release-metadata
    assertions.
  - impl: Preserve `release_type=custom`, `auto_merge=false`,
    `peter-evans/create-pull-request@v8`, prerelease GitHub release behavior,
    and stable-only Docker `latest`; do not introduce stable `1.2.0` behavior
    in this lane.
  - impl: Keep docs churn narrow by only touching the installer/version
    surfaces that `tests/test_release_metadata.py` already treats as part of
    the active release contract.
  - verify: `uv run pytest tests/test_release_metadata.py -v --no-cov`
  - verify: `rg -n "1\\.2\\.0-rc7|v1\\.2\\.0-rc7|create-pull-request@v8|release_type=custom|auto_merge=false|latest" .github/workflows/release-automation.yml pyproject.toml mcp_server/__init__.py CHANGELOG.md scripts/install-mcp-docker.sh scripts/install-mcp-docker.ps1 tests/test_release_metadata.py`

### SL-2 - Recut Dispatch And Workflow Observation

- **Scope**: Dispatch the remediated rc7 prerelease and capture the actual
  workflow and publication facts needed for downstream reduction.
- **Owned files**: none (local git and GitHub release state only)
- **Interfaces provided**: observed IF-0-GARECUT-2 and IF-0-GARECUT-3; runtime
  facts for IF-0-GARECUT-4 and IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 assertions; SL-1 rc7 release contract;
  `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-run the narrowed GARECUT and release-metadata checks locally
    before dispatch so the repo-owned rc7 surfaces are coherent.
  - test: Run the required pre-dispatch probes immediately before mutation:
    `git status --short --branch`, `git fetch origin main --tags --prune`,
    `git rev-parse HEAD origin/main`, `git tag -l v1.2.0-rc7`,
    `git ls-remote --tags origin refs/tags/v1.2.0-rc7`, and
    `gh workflow view "Release Automation"`.
  - impl: If the release-affecting worktree is dirty, `HEAD` differs from
    `origin/main`, or `v1.2.0-rc7` already exists locally or remotely, stop
    before dispatch and carry the blocked state into SL-3.
  - impl: Dispatch `gh workflow run "Release Automation" -f version=v1.2.0-rc7 -f release_type=custom -f auto_merge=false`, watch the run to completion, and capture run identity plus per-job outcomes.
  - impl: Record the resulting GitHub prerelease state, release branch or PR
    disposition, PyPI publication, and GHCR image identity on the remediated
    workflow path; do not mutate GA state even if the recut succeeds.
  - verify: `uv run pytest tests/test_release_metadata.py tests/docs/test_garecut_rc_recut_contract.py -v --no-cov`
  - verify: `git status --short --branch`
  - verify: `git fetch origin main --tags --prune`
  - verify: `git rev-parse HEAD origin/main`
  - verify: `git tag -l v1.2.0-rc7`
  - verify: `git ls-remote --tags origin refs/tags/v1.2.0-rc7`
  - verify: `gh workflow view "Release Automation"`
  - verify: `gh workflow run "Release Automation" -f version=v1.2.0-rc7 -f release_type=custom -f auto_merge=false`
  - verify: `gh run list --workflow "Release Automation" --limit 10`
  - verify: `gh run watch <run-id> --exit-status`
  - verify: `gh run view <run-id> --json url,headSha,status,conclusion,jobs`
  - verify: `gh release view v1.2.0-rc7 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets`
  - verify: `gh pr list --state all --head release/v1.2.0-rc7 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title`
  - verify: `python -m pip index versions index-it-mcp --pre`
  - verify: `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc7`

### SL-3 - RC Recut Evidence Reducer

- **Scope**: Reduce the rc7 pre-dispatch, dispatch, workflow, and publication
  facts into the canonical prerelease evidence artifact.
- **Owned files**: `docs/validation/ga-rc-evidence.md`
- **Interfaces provided**: IF-0-GARECUT-3, IF-0-GARECUT-4,
  and the evidence portion of IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 GARECUT assertions; SL-1 rc7 contract
  surfaces; SL-2 recut observation facts
- **Parallel-safe**: no
- **Tasks**:
  - test: Rewrite `docs/validation/ga-rc-evidence.md` only after SL-2 has a
    terminal outcome so the artifact reflects one coherent rc7 recut attempt.
  - impl: Record exact UTC capture time, selected commit, local and remote tag
    non-reuse results, dispatch inputs, run URL and ID, per-job conclusions,
    release branch or PR disposition, GitHub prerelease state, PyPI package
    identity, GHCR tag identity, and rollback or no-rollback disposition for
    `v1.2.0-rc7`.
  - impl: If SL-2 stops before dispatch or fails mid-run, keep the artifact
    explicit about the blocked or failed state instead of implying a successful
    recut.
  - impl: Preserve metadata-only reporting; do not print tokens, raw logs, or
    secret-bearing command output.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garc_rc_soak_contract.py -v --no-cov`
  - verify: `rg -n "v1\\.2\\.0-rc7|Release Automation|PyPI|GHCR|prerelease|latest|blocked before dispatch|workflow failed after dispatch|recut succeeded" docs/validation/ga-rc-evidence.md`

### SL-4 - Final Decision Handoff Refresh

- **Scope**: Refresh the historical GA decision artifact so it clearly hands
  the next downstream work back to a renewed GAREL reduction on top of the
  fresh rc7 evidence.
- **Owned files**: `docs/validation/ga-final-decision.md`
- **Interfaces provided**: final-decision portion of IF-0-GARECUT-5
- **Interfaces consumed**: SL-0 GARECUT assertions; SL-1 rc7 workflow
  disposition; SL-2 recut observation facts; SL-3 refreshed
  `docs/validation/ga-rc-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Keep `docs/validation/ga-final-decision.md` historical and
    non-authorizing for GA during GARECUT; this lane may refresh the next-step
    status, but it must not mutate the repo into a new stable-release decision.
  - impl: Preserve the original GAREL decision rationale that required another
    RC because the old `rc6` soak predated the remediated workflow path.
  - impl: Add or refresh a status section that references the new
    `v1.2.0-rc7` recut evidence outcome and states whether the repository is
    now ready for a renewed GAREL decision phase.
  - impl: If the rc7 recut failed or was blocked, keep the next step on
    remediating or rerunning GARECUT rather than reopening GA.
  - verify: `uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garel_ga_release_contract.py -v --no-cov`
  - verify: `rg -n "cut another RC|GARECUT|v1\\.2\\.0-rc7|renewed GAREL|ship GA|defer GA" docs/validation/ga-final-decision.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual GARECUT execution.

Contract and repo-owned version checks:

```bash
uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
rg -n "1\\.2\\.0-rc7|v1\\.2\\.0-rc7|create-pull-request@v8|release_type=custom|auto_merge=false|latest" \
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
git tag -l v1.2.0-rc7
git ls-remote --tags origin refs/tags/v1.2.0-rc7
gh workflow view "Release Automation"
gh workflow run "Release Automation" -f version=v1.2.0-rc7 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10
gh run watch <run-id> --exit-status
gh run view <run-id> --json url,headSha,status,conclusion,jobs
gh release view v1.2.0-rc7 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh pr list --state all --head release/v1.2.0-rc7 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
python -m pip index versions index-it-mcp --pre
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc7
```

Reducer artifact checks:

```bash
uv run pytest tests/docs/test_garecut_rc_recut_contract.py tests/docs/test_garc_rc_soak_contract.py tests/docs/test_garel_ga_release_contract.py -v --no-cov
rg -n "v1\\.2\\.0-rc7|Release Automation|PyPI|GHCR|renewed GAREL|blocked before dispatch|workflow failed after dispatch|recut succeeded" \
  docs/validation/ga-rc-evidence.md \
  docs/validation/ga-final-decision.md
git status --short -- docs/validation/ga-rc-evidence.md docs/validation/ga-final-decision.md
```

## Acceptance Criteria

- [ ] Repo-owned release surfaces and the remediated workflow freeze
      `1.2.0-rc7` / `v1.2.0-rc7`, retain
      `peter-evans/create-pull-request@v8`, and preserve prerelease-only
      GitHub Latest plus stable-only Docker `latest` policy.
- [ ] Pre-dispatch checks confirm a clean enough release worktree,
      `HEAD == origin/main`, workflow visibility, and no reused local or remote
      `v1.2.0-rc7` tag before dispatch.
- [ ] Release Automation is dispatched only with
      `version=v1.2.0-rc7`, `release_type=custom`, and `auto_merge=false`.
- [ ] The remediated recut run records terminal workflow results, GitHub
      prerelease state, PyPI package publication, GHCR image identity, and
      release branch or PR disposition for `v1.2.0-rc7`.
- [ ] `docs/validation/ga-rc-evidence.md` records the fresh rc7 recut outcome
      using metadata-only reporting.
- [ ] `docs/validation/ga-final-decision.md` remains historical, references the
      recut outcome, and points the next downstream work to a renewed GAREL
      decision instead of silently authorizing GA.
