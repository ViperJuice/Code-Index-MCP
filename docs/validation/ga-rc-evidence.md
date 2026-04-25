> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# GA RC Evidence

## Summary

- Evidence captured: `2026-04-25T02:31:42Z`.
- Active phase plan: `plans/phase-plan-v5-garecut.md`.
- Selected commit before dispatch evaluation:
  `a3adcea5cd569571a2c4ce3d863317e9f14519bc`.
- Active recut target: `v1.2.0-rc8`.
- Conclusion: `blocked before dispatch`.
- Dispatch attempted: `no`.
- Blocker: release-affecting worktree remained dirty during the rc8 recut
  attempt, so `gh workflow run` did not execute.
- Channel posture preserved: no `v1.2.0-rc8` prerelease was published; GitHub
  Latest remained excluded and Docker `latest` remained stable-only.

## Pre-dispatch Qualification

| Check | Command | Result | Evidence |
|---|---|---|---|
| Release candidate worktree state | `git status --short --branch` | fail | `## main...origin/main` with release-affecting dirty files in `.github/workflows/release-automation.yml`, `pyproject.toml`, `mcp_server/__init__.py`, installer helpers, validation docs, and release-contract tests. |
| Local versus remote branch sync | `git fetch origin main --tags --prune` then `git rev-parse HEAD origin/main` | pass | `HEAD=a3adcea5cd569571a2c4ce3d863317e9f14519bc`, `origin/main=a3adcea5cd569571a2c4ce3d863317e9f14519bc`. |
| Local tag reuse | `git tag -l v1.2.0-rc8` | pass | No local `v1.2.0-rc8` tag existed before dispatch evaluation. |
| Remote tag reuse | `git ls-remote --tags origin refs/tags/v1.2.0-rc8` | pass | No remote `v1.2.0-rc8` tag existed before dispatch evaluation. |
| Release workflow visibility | `gh workflow view "Release Automation"` | pass | Workflow visible as `Release Automation - release-automation.yml`, workflow id `167401116`. |

## Intended Dispatch Inputs

GARECUT would dispatch exactly:

```bash
gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false
```

Frozen channel-policy inputs:

- Version: `v1.2.0-rc8`
- Release type: `custom`
- Auto-merge policy: `false`
- Channel posture: prerelease `public-alpha` / `beta`
- Workflow path under test: `softprops/action-gh-release@v3`

## Workflow Observation

- Dispatch attempted: `no`
- Run URL: `none - blocked before dispatch`
- Run ID: `none - blocked before dispatch`
- `headSha`: `a3adcea5cd569571a2c4ce3d863317e9f14519bc`
- Workflow status / conclusion: `not started` / `blocked before dispatch`
- Release branch / PR disposition: no `release/v1.2.0-rc8` branch or PR was
  created because the recut stopped at the dirty-worktree gate.
- GitHub release state: no `v1.2.0-rc8` release exists because dispatch did not
  occur.
- PyPI publication: none - blocked before dispatch.
- GHCR image identity: none - blocked before dispatch.

## Release-Channel Policy

- `v1.2.0-rc8` remains the frozen prerelease/public-alpha or beta recut target.
- `release_type=custom` remains required for the hyphenated RC version.
- `auto_merge=false` remains the required recut input.
- GitHub Latest remained excluded from the RC policy source.
- Docker `latest` remained stable-only.
- No GA wording or stable-channel claims were introduced by the blocked recut.

## Rollback And Next-Step Disposition

No rollback was required because no rc8 release mutation occurred.

Next-step disposition:

- Rerun GARECUT after the release-affecting worktree is clean enough for
  mutation and the intended rc8 surfaces are preserved.
- A renewed GAREL decision is not yet ready; it still depends on fresh
  `v1.2.0-rc8` prerelease evidence on the remediated
  `softprops/action-gh-release@v3` workflow path.
- Until that rerun succeeds, keep the work inside GARECUT rather than
  reopening GA or treating older downstream GAREL plans as authoritative.

## Historical GARC Baseline

The prior follow-up RC soak remains historical input evidence, not the active
recut result:

- Historical phase plan: `plans/phase-plan-v5-garc.md`
- Historical soak target: `v1.2.0-rc6`
- Historical conclusion: `follow-up RC soak succeeded`
- Historical Release Automation run:
  `https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24913315931`
  (`run ID 24913315931`)
- Historical workflow path warning:
  `peter-evans/create-pull-request@v7` emitted a GitHub Actions Node 20
  deprecation warning, which is why the rc7 recut exists at all.

## Verification

Completed validation sources for this artifact:

```bash
uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
uv run pytest tests/docs/test_garc_rc_soak_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc8
git ls-remote --tags origin refs/tags/v1.2.0-rc8
gh workflow view "Release Automation"
```
