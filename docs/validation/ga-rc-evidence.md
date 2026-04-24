> **Historical artifact — as-of 2026-04-24, may not reflect current behavior**

# GA RC Evidence

## Summary

- Evidence captured: 2026-04-24T20:20:00Z.
- Observed commit: `8d08545c15c53322128ef87b5e06308bd8b0dad3`.
- Phase plan: `plans/phase-plan-v5-garc.md`.
- Canonical upstream sources:
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/validation/ga-operations-evidence.md`.
- Intended follow-up RC: `v1.2.0-rc6`.
- Conclusion: `blocked before dispatch`.
- Blocker: the required `git status --short --branch` pre-dispatch probe showed
  a dirty worktree, so GARC stopped before `gh workflow run` could mutate the
  release channel.

## Pre-dispatch Qualification

| Check | Command | Result | Evidence |
|---|---|---|---|
| Release candidate worktree state | `git status --short --branch` | blocked | `## main...origin/main` with modified/staged files still present, including active docs, tests, and phase artifacts. |
| Local versus remote branch sync | `git fetch origin main --tags --prune` then `git rev-parse HEAD origin/main` | pass | `HEAD=8d08545c15c53322128ef87b5e06308bd8b0dad3`, `origin/main=8d08545c15c53322128ef87b5e06308bd8b0dad3`. |
| Local tag reuse | `git tag -l v1.2.0-rc6` | pass | No local `v1.2.0-rc6` tag exists. |
| Remote tag reuse | `git ls-remote --tags origin refs/tags/v1.2.0-rc6` | pass | No remote `v1.2.0-rc6` tag exists. |
| Release workflow visibility | `gh workflow view "Release Automation"` | pass | Workflow visible as `Release Automation - release-automation.yml`, workflow id `167401116`. |
| Governance input freshness | `docs/validation/ga-governance-evidence.md` | pass | Current governance artifact records `enforced via branch protection` on `main`. |
| E2E input freshness | `docs/validation/ga-e2e-evidence.md` | pass | Current artifact remains the GAE2E input for release-surface validation and readiness evidence. |
| Operations input freshness | `docs/validation/ga-operations-evidence.md` | pass | Current artifact remains the GAOPS input for operator preflight and rollback procedure. |

## Intended Dispatch Inputs

If qualification had passed, GARC would have dispatched exactly:

```bash
gh workflow run "Release Automation" -f version=v1.2.0-rc6 -f release_type=custom -f auto_merge=false
```

Frozen channel-policy inputs:

- Version: `v1.2.0-rc6`
- Release type: `custom`
- Auto-merge policy: `false`
- Channel posture: prerelease `public-alpha` / `beta`

## Workflow Observation

- Dispatch attempted: `no`
- Run URL: `none`
- Run ID: `none`
- `headSha`: `none`
- Per-job conclusions: `none`
- Release branch or PR disposition: `none`
- GitHub release state for `v1.2.0-rc6`: `not created`
- Tag target: `not created`
- PyPI publication: `not attempted`
- GHCR image identity: `not attempted`

The workflow was intentionally not dispatched because the clean-worktree
qualification contract failed first. This preserves the active RC/public-alpha
channel and avoids claiming that the follow-up RC soak succeeded.

## Release-Channel Policy

- `v1.2.0-rc6` remains a prerelease/public-alpha or beta channel artifact.
- `release_type=custom` remains required for the hyphenated version.
- `auto_merge=false` remains the default policy unless a fresh governance
  decision records an exception.
- GitHub Latest remains excluded from the RC policy source.
- Docker `latest` remains stable-only.
- No GA wording or stable-channel claims were introduced by this blocked run.

## Rollback And Next-Step Disposition

No release mutation occurred, so no release rollback was required.

Next-step disposition:

- Keep the current active published RC/public-alpha contract at `v1.2.0-rc5`
  until GARC is rerun successfully.
- Clear the dirty-worktree blocker, rerun the GARC qualification probes, and
  dispatch only after the worktree is clean.
- Treat this artifact as evidence that GAREL must remain blocked on a successful
  GARC soak rather than assuming GA readiness.

## Verification

Planned or completed validation sources for this artifact:

```bash
uv run pytest tests/docs/test_garc_rc_soak_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc6
git ls-remote --tags origin refs/tags/v1.2.0-rc6
gh workflow view "Release Automation"
```
