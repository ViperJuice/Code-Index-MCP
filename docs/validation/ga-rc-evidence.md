> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# GA RC Evidence

## Summary

- Evidence captured: `2026-04-25T05:34:39Z`.
- Active phase plan: `plans/phase-plan-v5-garecut.md`.
- Selected commit before dispatch evaluation:
  `d2560e95f1b4e7d52eacb025d592275e4b48a084`.
- Active recut target: `v1.2.0-rc8`.
- Conclusion: `recut succeeded`.
- Dispatch attempted: `yes`.
- Run URL: `https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24923402398`
  (`run ID 24923402398`).
- Channel posture preserved: `v1.2.0-rc8` published as a prerelease only;
  GitHub Latest remained excluded and Docker `latest` remained stable-only.
- Follow-up warning: the `Create GitHub Release` job completed successfully on
  `softprops/action-gh-release@v3`, but its `actions/download-artifact@v8`
  step emitted a runtime `Buffer()` deprecation warning that renewed GAREL must
  disposition before any GA ship path is reconsidered.

## Pre-dispatch Qualification

| Check | Command | Result | Evidence |
|---|---|---|---|
| Release candidate worktree state | `git status --short --branch` | pass | `## main...origin/main` with no tracked-file dirt before dispatch. |
| Local versus remote branch sync | `git fetch origin main --tags --prune` then `git rev-parse HEAD origin/main` | pass | `HEAD=d2560e95f1b4e7d52eacb025d592275e4b48a084`, `origin/main=d2560e95f1b4e7d52eacb025d592275e4b48a084`. |
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

- Dispatch attempted: `yes`
- Run URL: `https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24923402398`
- Run ID: `24923402398`
- `headSha`: `d2560e95f1b4e7d52eacb025d592275e4b48a084`
- Workflow status / conclusion: `completed` / `success`
- Job conclusions:
  - `Preflight Release Gates`: `success`
  - `Prepare Release`: `success`
  - `Run Release Tests`: `success`
  - `Build Release Artifacts`: `success`
  - `Create GitHub Release`: `success`
  - `Merge Release Branch`: `success`
  - `Post-Release Tasks`: `success`
- `Create GitHub Release` log disposition: successful tag push, prerelease
  creation, and PyPI publish on `softprops/action-gh-release@v3`; one
  non-fatal `Buffer()` deprecation warning was emitted by
  `actions/download-artifact@v8` before release creation.
- Release branch / PR disposition: `release/v1.2.0-rc8` was created remotely at
  `d2560e95f1b4e7d52eacb025d592275e4b48a084`; the merge job reported
  `pull-request-operation = none`, so no new release PR was left open because
  the branch no longer differed from `main`.
- GitHub release state: prerelease `v1.2.0-rc8` published at
  `2026-04-25T05:30:37Z`:
  `https://github.com/ViperJuice/Code-Index-MCP/releases/tag/v1.2.0-rc8`
- Tag target commit: `079338cb70f5078db381f088e93df1e9700b5d96`
- PyPI publication: `index-it-mcp 1.2.0rc8` published at
  `https://pypi.org/project/index-it-mcp/1.2.0rc8/`
- GHCR image identity: `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8` index
  digest `sha256:352bb88eec59e3f15a19077f2880bafa10241997f3ab2619ed221ac32c9eaa05`
  with linux/amd64 and linux/arm64 manifests.

## Release-Channel Policy

- `v1.2.0-rc8` remains the frozen prerelease/public-alpha or beta recut target.
- `release_type=custom` remains required for the hyphenated RC version.
- `auto_merge=false` remains the required recut input.
- GitHub Latest remained excluded from the RC policy source.
- Docker `latest` remained stable-only.
- No GA wording or stable-channel claims were introduced by the successful recut
  itself.

## Rollback And Next-Step Disposition

No rollback was required because the rc8 recut completed successfully and did
not mutate the stable GA channel.

Next-step disposition:

- Route back through renewed GAREL planning on top of this fresh
  `v1.2.0-rc8` prerelease evidence.
- Carry forward the newly observed `actions/download-artifact@v8`
  `Buffer()` deprecation warning from the `Create GitHub Release` job as a
  required runtime-disposition item before any `ship GA` path is authorized.
- Treat any older downstream GAREL plan as stale after the roadmap amendment
  that incorporates this new warning.

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
gh workflow run "Release Automation" -f version=v1.2.0-rc8 -f release_type=custom -f auto_merge=false
gh run view 24923402398 --json url,headSha,status,conclusion,jobs
gh run view 24923402398 --job 72989683995 --log
gh release view v1.2.0-rc8 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh pr list --state all --search "release/v1.2.0-rc8" --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0rc8/json
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8
```
