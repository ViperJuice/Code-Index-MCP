# RC5REL: RC5 Release Execution & Observation

> Plan doc produced by `codex-plan-phase specs/phase-plans-v4.md RC5REL`
> on 2026-04-23.
> Source roadmap `specs/phase-plans-v4.md` is staged as a new artifact in this
> worktree (`git status --short -- specs/phase-plans-v4.md` shows `A`).

## Context

RC5REL is the second v4 phase and depends on GATEPARITY. It is an operational
release execution and evidence-capture phase for `v1.2.0-rc5`, not a new
implementation phase.

The current release surface is already RC5-shaped:

- `pyproject.toml` uses `version = "1.2.0-rc5"`.
- `mcp_server/__init__.py` exposes `__version__ = "1.2.0-rc5"`.
- `.github/workflows/release-automation.yml` defaults to
  `version=v1.2.0-rc5`, `release_type=custom`, and `auto_merge=false`.
- `tests/test_release_metadata.py` freezes the active RC5 version/tag contract.
- `docs/operations/deployment-runbook.md` and
  `docs/operations/user-action-runbook.md` contain the public-alpha gate and
  P34 recut checklists.
- `plans/phase-plan-v4-gateparity.md` is staged, but this planning run did not
  verify that GATEPARITY has been executed and accepted.

Because the phase mutates public release state through GitHub Actions, PyPI, and
GHCR, execution must stop before dispatch unless GATEPARITY is accepted, the
worktree is clean, `main` matches `origin/main`, and neither the local nor remote
`v1.2.0-rc5` tag already exists.

## Interface Freeze Gates

- [ ] IF-0-RC5REL-1 - RC5 release evidence contract: the `v1.2.0-rc5`
      tag/release flow records the exact commit, Release Automation workflow
      run URL, job conclusions, PyPI artifact identifier, GHCR image tag, GitHub
      release URL, release branch or PR URL, and rollback disposition.
- [ ] IF-0-RC5REL-2 - Pre-dispatch safety contract: release dispatch is allowed
      only when `git status --short --branch` is clean, local `HEAD` equals
      `origin/main`, `git tag -l v1.2.0-rc5` is empty, and
      `git ls-remote --tags origin refs/tags/v1.2.0-rc5` is empty.
- [ ] IF-0-RC5REL-3 - Release Automation input contract: the only allowed RC5
      dispatch inputs are `version=v1.2.0-rc5`, `release_type=custom`, and
      `auto_merge=false` unless RELGOV has already changed the policy.
- [ ] IF-0-RC5REL-4 - Publication observation contract: preflight, release
      tests, artifact build, GitHub release creation, PyPI publish, release
      branch/PR creation, tag-triggered CI, and GHCR publish/smoke are watched
      to terminal success or recorded rollback.
- [ ] IF-0-RC5REL-5 - Artifact identity contract: the GitHub release is a
      prerelease for `v1.2.0-rc5`, points at the expected commit, PyPI exposes
      the normalized RC5 package version, and GHCR exposes
      `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`.

## Lane Index & Dependencies

- SL-0 - Pre-dispatch safety check; Depends on: GATEPARITY; Blocks: SL-1; Parallel-safe: no
- SL-1 - Release Automation dispatch; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Workflow and tag observation; Depends on: SL-1; Blocks: SL-4; Parallel-safe: yes
- SL-3 - Publication and rollback disposition; Depends on: SL-1; Blocks: SL-4; Parallel-safe: yes
- SL-4 - RC5 evidence note; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: RC5REL acceptance; Parallel-safe: no

Lane DAG:

```text
GATEPARITY
  -> SL-0
       -> SL-1
            -> SL-2 --.
            -> SL-3 ----> SL-4 -> RC5REL acceptance
```

## Lanes

### SL-0 - Pre-dispatch Safety Check

- **Scope**: Prove the release can be dispatched without overwriting local work,
  diverging from `origin/main`, or reusing an existing RC5 tag.
- **Owned files**: none; local git state, remote tag state, and GitHub auth
  checks only
- **Interfaces provided**: IF-0-RC5REL-2; release commit SHA selected for RC5
- **Interfaces consumed**: GATEPARITY acceptance; existing
  `tests/test_release_metadata.py` RC5 contract; current
  `.github/workflows/release-automation.yml` dispatch contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Confirm GATEPARITY acceptance evidence exists before any release
    dispatch attempt.
  - test: Run `git status --short --branch` and require no unstaged, staged, or
    untracked release-affecting changes.
  - test: Run `git fetch origin main --tags --prune`, then confirm
    `git rev-parse HEAD` equals `git rev-parse origin/main`.
  - test: Confirm `git tag -l v1.2.0-rc5` and
    `git ls-remote --tags origin refs/tags/v1.2.0-rc5` return no tag.
  - test: Confirm GitHub CLI auth can view and dispatch the release workflow
    without printing secrets.
  - impl: Record the selected commit SHA, remote URL owner/repo, and preflight
    command results for SL-4.
  - verify: `git status --short --branch`
  - verify: `git rev-parse HEAD origin/main`
  - verify: `git tag -l v1.2.0-rc5`
  - verify: `git ls-remote --tags origin refs/tags/v1.2.0-rc5`
  - verify: `gh workflow view "Release Automation"`

### SL-1 - Release Automation Dispatch

- **Scope**: Dispatch the GitHub Release Automation workflow with the frozen RC5
  inputs and capture the workflow run identity.
- **Owned files**: none; GitHub Actions workflow dispatch state only
- **Interfaces provided**: IF-0-RC5REL-3; Release Automation run URL and run ID
- **Interfaces consumed**: SL-0 selected release commit; workflow dispatch inputs
  from `.github/workflows/release-automation.yml`
- **Parallel-safe**: no
- **Tasks**:
  - test: Verify the workflow still exposes `version`, `release_type`, and
    `auto_merge` workflow-dispatch inputs before dispatch.
  - impl: Dispatch Release Automation with:
    `gh workflow run "Release Automation" -f version=v1.2.0-rc5 -f release_type=custom -f auto_merge=false`.
  - impl: Capture the newest matching run ID and URL from
    `gh run list --workflow "Release Automation" --limit 5 --json databaseId,displayTitle,headBranch,headSha,status,conclusion,url,createdAt`.
  - impl: Confirm the run `headSha` matches the SL-0 selected release commit or
    stop and record the mismatch before any manual approval.
  - verify: `gh run list --workflow "Release Automation" --limit 5`
  - verify: `gh run view <run-id> --json databaseId,headSha,status,conclusion,url,jobs`

### SL-2 - Workflow and Tag Observation

- **Scope**: Watch Release Automation and tag-triggered CI/container workflows
  to terminal state and collect their URLs and conclusions.
- **Owned files**: none; GitHub Actions run state only
- **Interfaces provided**: IF-0-RC5REL-4 workflow conclusions; tag-triggered
  CI/container run evidence
- **Interfaces consumed**: SL-1 Release Automation run ID; existing workflow job
  names in `.github/workflows/release-automation.yml`,
  `.github/workflows/ci-cd-pipeline.yml`, and
  `.github/workflows/container-registry.yml`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Watch the Release Automation run through `preflight-release-gates`,
    `prepare-release`, `run-tests`, `build-artifacts`, `create-release`,
    `merge-release`, and `post-release`.
  - test: After tag creation, identify tag-triggered CI and Container Registry
    runs for `refs/tags/v1.2.0-rc5`.
  - impl: Capture job names, conclusions, URLs, and failure summaries for SL-4.
  - impl: If any required job fails, stop release promotion and hand SL-3 the
    failure details for rollback/disposition.
  - verify: `gh run watch <release-automation-run-id> --exit-status`
  - verify: `gh run view <release-automation-run-id> --json jobs,status,conclusion,url`
  - verify: `gh run list --branch v1.2.0-rc5 --limit 20`

### SL-3 - Publication and Rollback Disposition

- **Scope**: Verify public release artifacts or record the exact rollback and
  non-announcement disposition when publication fails.
- **Owned files**: none; GitHub release, PyPI package, GHCR image, release
  branch, and rollback state only
- **Interfaces provided**: IF-0-RC5REL-5; rollback/no-rollback disposition for
  SL-4
- **Interfaces consumed**: SL-1 Release Automation run; SL-2 workflow
  conclusions; deployment and user-action runbook rollback guidance
- **Parallel-safe**: yes
- **Tasks**:
  - test: Inspect `gh release view v1.2.0-rc5` and confirm the release is
    marked prerelease, targets the SL-0 commit, and has expected release
    assets.
  - test: Inspect PyPI for the RC5 package version, using the normalized
    package version if PyPI displays `1.2.0rc5`.
  - test: Inspect GHCR for
    `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`.
  - test: Record the `release/v1.2.0-rc5` branch and PR URL created by the
    workflow, if present; do not auto-merge unless RELGOV has changed policy.
  - impl: If GitHub release/tag creation succeeded but downstream publication
    failed, document the rollback decision before deleting tags, deleting the
    GitHub release, closing the release PR, or yanking PyPI artifacts.
  - impl: Never print token values, PyPI credentials, package secrets, or
    GitHub token output in the evidence note.
  - verify: `gh release view v1.2.0-rc5 --json tagName,targetCommitish,isPrerelease,isLatest,url,assets,publishedAt`
  - verify: `python -m pip index versions index-it-mcp --pre`
  - verify: `docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`
  - verify: `gh pr list --head release/v1.2.0-rc5 --json number,title,state,url,headRefName,headRefOid`

### SL-4 - RC5 Evidence Note

- **Scope**: Reduce all preflight, dispatch, workflow, publication, and
  rollback findings into a single committed evidence note.
- **Owned files**: `docs/validation/rc5-release-evidence.md`
- **Interfaces provided**: IF-0-RC5REL-1; release evidence note for GACLOSE and
  future release-governance decisions
- **Interfaces consumed**: SL-0 selected commit and preflight results; SL-1
  workflow dispatch run ID/URL; SL-2 job conclusions and tag-triggered run
  URLs; SL-3 artifact identities and rollback/no-rollback disposition
- **Parallel-safe**: no
- **Tasks**:
  - test: Create `docs/validation/rc5-release-evidence.md` only after every
    producer lane has a terminal result.
  - impl: Record exact UTC timestamp, release commit SHA, local/remote tag
    preflight results, Release Automation run URL, required job conclusions,
    tag-triggered CI/container URLs, GitHub release URL, PyPI version evidence,
    GHCR tag evidence, release branch/PR URL, and rollback disposition.
  - impl: If release execution is abandoned before dispatch, write the evidence
    note as "not dispatched" with the blocking reason instead of leaving the
    phase ambiguous.
  - impl: Keep raw logs, private tokens, package credentials, and secret-bearing
    command output out of the evidence note.
  - verify: `rg -n "v1\\.2\\.0-rc5|Release Automation|PyPI|GHCR|rollback|not dispatched" docs/validation/rc5-release-evidence.md`
  - verify: `git diff -- docs/validation/rc5-release-evidence.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual RC5 release execution after GATEPARITY is
accepted.

Pre-dispatch checks:

```bash
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc5
git ls-remote --tags origin refs/tags/v1.2.0-rc5
gh workflow view "Release Automation"
```

Dispatch and observation:

```bash
gh workflow run "Release Automation" \
  -f version=v1.2.0-rc5 \
  -f release_type=custom \
  -f auto_merge=false
gh run list --workflow "Release Automation" --limit 5
gh run view <release-automation-run-id> --json databaseId,headSha,status,conclusion,url,jobs
gh run watch <release-automation-run-id> --exit-status
gh run list --branch v1.2.0-rc5 --limit 20
```

Publication checks:

```bash
gh release view v1.2.0-rc5 --json tagName,targetCommitish,isPrerelease,isLatest,url,assets,publishedAt
python -m pip index versions index-it-mcp --pre
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5
gh pr list --head release/v1.2.0-rc5 --json number,title,state,url,headRefName,headRefOid
```

Evidence checks:

```bash
rg -n "v1\\.2\\.0-rc5|Release Automation|PyPI|GHCR|rollback|not dispatched" docs/validation/rc5-release-evidence.md
git status --short -- docs/validation/rc5-release-evidence.md
```

## Acceptance Criteria

- [ ] GATEPARITY is accepted before any RC5 release dispatch.
- [ ] Local pre-dispatch checks confirm a clean worktree, `HEAD == origin/main`,
      no reused local `v1.2.0-rc5` tag, and no reused remote
      `v1.2.0-rc5` tag.
- [ ] Release Automation is dispatched only with `version=v1.2.0-rc5`,
      `release_type=custom`, and `auto_merge=false`.
- [ ] Release Automation preflight, release tests, artifact build, GitHub
      release creation, PyPI publish, release branch/PR creation, and
      post-release jobs reach terminal success or are tied to a documented
      rollback decision.
- [ ] Tag-triggered CI and Container Registry workflows for `v1.2.0-rc5` are
      observed and recorded.
- [ ] GitHub release `v1.2.0-rc5` is marked prerelease and points at the
      expected commit.
- [ ] PyPI exposes the RC5 package artifact and GHCR exposes
      `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`, or rollback/yank/manual
      follow-up is documented.
- [ ] `docs/validation/rc5-release-evidence.md` records workflow URLs, artifact
      identifiers, release branch/PR state, and rollback disposition without
      secret values.
