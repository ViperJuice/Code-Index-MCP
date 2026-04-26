> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# GA Release Evidence

## Summary

- Evidence captured: `2026-04-26T02:09:26Z`.
- Executed phase plan: `plans/phase-plan-v5-gadisp.md`.
- Qualified commit before dispatch: `94dc83709f48af6447ddfc1d22e1ee5aa670de91`.
- Stable release target: `v1.2.0`.
- Conclusion: `stable dispatch succeeded`.
- Dispatch attempted: `yes`.
- Run URL: `https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24945689189`
  (`run ID 24945689189`).
- GitHub release posture: stable `v1.2.0` published and GitHub Latest now
  points at the same stable release.
- Accepted runtime warning: the successful `Create GitHub Release` job again
  emitted the `actions/download-artifact@v8` `Buffer()` deprecation warning,
  but digest verification, GitHub release publication, PyPI publication, and
  GHCR publication all completed successfully.

## Pre-dispatch Qualification

| Check | Command | Result | Evidence |
|---|---|---|---|
| Stable dispatch worktree state | `git status --short --branch` | pass | `## main...origin/main` with no tracked-file dirt before dispatch. |
| Local versus remote branch sync | `git fetch origin main --tags --prune` then `git rev-parse HEAD origin/main` | pass | `HEAD=94dc83709f48af6447ddfc1d22e1ee5aa670de91`, `origin/main=94dc83709f48af6447ddfc1d22e1ee5aa670de91`. |
| Local stable tag reuse | `git tag -l v1.2.0` | pass | No local `v1.2.0` tag existed before dispatch. |
| Remote stable tag reuse | `git ls-remote --tags origin refs/tags/v1.2.0` | pass | No remote `v1.2.0` tag existed before dispatch; after success the remote tag resolves to `c9686efbf80eafaa7f8b4e4a42478b88f93d9ecc`. |
| Final GA decision posture | `rg -n "ship GA|cut another RC|defer GA" docs/validation/ga-final-decision.md` | pass | `docs/validation/ga-final-decision.md` still selected `ship GA`. |
| Stable surface already prepared | `rg -n "1\\.2\\.0|v1\\.2\\.0|Version|release" ...` | pass | `pyproject.toml`, `mcp_server/__init__.py`, `CHANGELOG.md`, and `README.md` already reflected the stable `1.2.0` / `v1.2.0` surface before dispatch. |
| Release workflow visibility | `gh workflow view "Release Automation"` | pass | Workflow visible as `Release Automation - release-automation.yml`, workflow id `167401116`. |
| Release contract smoke | `uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov` | pass | 17 tests passed. |

## Dispatch Inputs

GADISP dispatched exactly:

```bash
gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false
```

Frozen inputs:

- Version: `v1.2.0`
- Release type: `custom`
- Auto-merge policy: `false`
- Release base ref: `origin/main`

## Workflow Observation

- Dispatch attempted: `yes`
- Run URL: `https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24945689189`
- Run ID: `24945689189`
- `headSha`: `94dc83709f48af6447ddfc1d22e1ee5aa670de91`
- Workflow status / conclusion: `completed` / `success`
- Job conclusions:
  - `Preflight Release Gates`: `success`
  - `Prepare Release`: `success`
  - `Run Release Tests`: `success`
  - `Build Release Artifacts`: `success`
  - `Create GitHub Release`: `success`
  - `Merge Release Branch`: `success`
  - `Post-Release Tasks`: `success`
- Install/container verification outcome: `pass`
  - `Run Release Tests` succeeded, including release smoke and version
    consistency.
  - `Build Release Artifacts` succeeded, including Python package build,
    multi-arch Docker build/push, SBOM generation, and release artifact upload.
- Release-branch / PR disposition:
  - the merge job refreshed `origin/release/v1.2.0`,
  - `peter-evans/create-pull-request@v8` reported
    `pull-request-branch = release/v1.2.0`,
    `pull-request-operation = none`, and
    `pull-request-head-sha = 94dc83709f48af6447ddfc1d22e1ee5aa670de91`,
  - `gh pr list --state all --head release/v1.2.0 ...` returned `[]`, so no
    open release PR remained after the successful run because the branch no
    longer differed from `main`.

## Publication State

- GitHub release state: stable `v1.2.0` published at `2026-04-26T02:07:57Z`
  with URL
  `https://github.com/ViperJuice/Code-Index-MCP/releases/tag/v1.2.0`
- GitHub Latest posture: stable Latest now points at `v1.2.0` with
  `prerelease=false`, `draft=false`, and `target_commitish=main`
- GitHub release assets:
  - `index_it_mcp-1.2.0-py3-none-any.whl`
    `sha256:10413bd7f46d88c97d2d0fa71c859e6d6f83d5ad441c28208d49244f437ade8d`
  - `index_it_mcp-1.2.0.tar.gz`
    `sha256:57644871a3281f94b7845b25f8500e1aaf76c5ec2092f4e5ab41c0743577bdc6`
  - `sbom.spdx.json`
    `sha256:ce8423f15f7f3fc13398ea9c3851b99639734c599b0c25a2d1930c3031b94fa0`
  - `CHANGELOG.md`
    `sha256:a694fd55e7feb0f3ddcf779e6977d3535bb5fd02bff670260333772af6bca169`
  - `DEPLOYMENT-GUIDE.md`
    `sha256:253545d2a0f0484a0d24691206394079d3b31544ea060f43098a302da6dfb54e`
- PyPI publication:
  - project: `index-it-mcp`
  - version: `1.2.0`
  - project URL: `https://pypi.org/project/index-it-mcp/`
  - wheel upload: `2026-04-26T02:08:08.078356Z`
    `sha256:10413bd7f46d88c97d2d0fa71c859e6d6f83d5ad441c28208d49244f437ade8d`
  - sdist upload: `2026-04-26T02:08:10.388843Z`
    `sha256:57644871a3281f94b7845b25f8500e1aaf76c5ec2092f4e5ab41c0743577bdc6`
- GHCR image identity:
  - image: `ghcr.io/viperjuice/code-index-mcp:v1.2.0`
  - OCI index digest:
    `sha256:31511a4baa16fc7ca812c6fe63f33bb1e2521a157b5d6054c6e91385fbfa7a4e`
  - linux/amd64 manifest:
    `sha256:cd94ddf19d1216248e55ecb628b8feb0168e9e7ab045672210fd9ae321230f8b`
  - linux/arm64 manifest:
    `sha256:f34507d156bae1f250d2cd9e20078008c620745e1060085ad46fc53d1e7c7c58`

## Warning Disposition

The successful `Create GitHub Release` job used
`actions/download-artifact@v8`, downloaded artifact `release-artifacts`
(`ID 6644158290`), and verified the expected digest
`sha256:a7096ea5a68fe7c717b726194a0afe39f74b40702bd3c382d33c4b1b8009a01d`.
During that step, the log again emitted:

- `(node:2300) [DEP0005] DeprecationWarning: Buffer() is deprecated ...`
- `Artifact download completed successfully.`

Accepted disposition:

- The warning matches the already-accepted GAREL/GARECUT runtime concern on the
  current `actions/download-artifact@v8` line.
- Digest verification still succeeded.
- The workflow still completed GitHub release creation, PyPI publication, and
  GHCR publication successfully.
- This warning is therefore recorded as accepted non-blocking GA release
  evidence metadata, not as a new blocker or roadmap-change trigger.

## Rollback And Roadmap Disposition

- Rollback required: `no`
- Rollback disposition: stable dispatch completed successfully; no rollback was
  needed.
- Downstream roadmap steering change discovered: `no`
- Roadmap amendment performed in this phase: `no`

GADISP closed the stable dispatch and evidence objective that GAREL had already
authorized. This execution did not discover new steering that changes
downstream work, so no downstream roadmap phase was amended.

## Verification

```bash
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0
git ls-remote --tags origin refs/tags/v1.2.0
gh workflow view "Release Automation"
rg -n "ship GA|cut another RC|defer GA" docs/validation/ga-final-decision.md
rg -n "1\\.2\\.0|v1\\.2\\.0|Version|release" pyproject.toml mcp_server/__init__.py CHANGELOG.md README.md docs/validation/ga-final-decision.md
uv run pytest tests/docs/test_garel_ga_release_contract.py tests/docs/test_gabase_ga_readiness_contract.py tests/test_release_metadata.py -v --no-cov
gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false
gh run list --workflow "Release Automation" --limit 10 --json databaseId,headSha,status,conclusion,workflowName,event,url,displayTitle,createdAt
gh run watch 24945689189 --exit-status
gh run view 24945689189 --json url,headSha,status,conclusion,createdAt,updatedAt,jobs
gh run view 24945689189 --log | rg -n "Buffer\\(|download-artifact|artifact"
gh run view 24945689189 --job 73047327232 --log | rg -n "pull request|Pull Request|Created|https://github.com/ViperJuice/Code-Index-MCP/pull/|release/v1\\.2\\.0|Auto-merge"
gh release view v1.2.0 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name,prerelease,draft,html_url,target_commitish,published_at}'
gh pr list --state all --head release/v1.2.0 --json number,state,isDraft,mergedAt,url,headRefName,baseRefName,title
curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0/json
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0
```
