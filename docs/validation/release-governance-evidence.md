> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# Release Governance Evidence

## Summary

- Evidence captured: 2026-04-24T03:04:22Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Default branch: `main`.
- Visibility: `PUBLIC`.
- Branch protection: `not protected`.
- Repository rulesets: `none`.
- Enforcement disposition: required public-alpha gates use manual enforcement.
- Policy accepted by: `repository operator`.
- Active RC/public-alpha package contract: `v1.2.0-rc5`.
- GitHub Latest: `v2.15.0-alpha.1`.
- Release-channel disposition: GitHub Latest is not the RC policy source unless
  a later release operation deliberately changes channel state.
- RC versus GA disposition: stay on RC/public-alpha until RC5 release evidence,
  RELGOV evidence, TOOLRDY evidence, and GACLOSE acceptance justify GA hardening
  or another follow-up RC.

## Access Probes

| Probe | Result | Non-secret evidence |
|---|---|---|
| `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility` | Public repository, default branch `main`. | `nameWithOwner=ViperJuice/Code-Index-MCP`, `defaultBranchRef.name=main`, `visibility=PUBLIC`. |
| `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'` | Branch exists and is not protected. | `name=main`, `protected=false`. |
| `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection` | Branch protection is absent. | `Branch not protected (HTTP 404)`. |
| `gh api repos/ViperJuice/Code-Index-MCP/rulesets` | No repository rulesets returned. | Empty list. |
| `gh release list --repo ViperJuice/Code-Index-MCP --limit 10` | `v1.2.0-rc5` is a prerelease; `v2.15.0-alpha.1` is GitHub Latest. | Both tags appeared in the release list. |
| `gh api repos/ViperJuice/Code-Index-MCP/releases/latest` | GitHub Latest resolves to `v2.15.0-alpha.1`. | Latest release tag `v2.15.0-alpha.1`, published 2026-04-05T04:58:39Z. |
| `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url` | Active RC release is published as a prerelease. | `tagName=v1.2.0-rc5`, `isPrerelease=true`, `isDraft=false`, `publishedAt=2026-04-24T02:49:05Z`, `targetCommitish=main`. |

## Required Gates

| Required gates | Workflow or command source |
|---|---|
| Alpha Gate - Dependency Sync | `.github/workflows/lockfile-check.yml` -> `make alpha-dependency-sync`. |
| Alpha Gate - Format And Lint | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-format-lint`. |
| Alpha Gate - Unit And Release Smoke | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-unit-release-smoke` and `make release-smoke`. |
| Alpha Gate - Integration Smoke | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-integration-smoke`. |
| Alpha Gate - Production Multi-Repo Matrix | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-production-matrix`. |
| Alpha Gate - Docker Build And Smoke | `.github/workflows/container-registry.yml` -> `make release-smoke-container`. |
| Alpha Gate - Docs Truth | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-docs-truth`. |
| Alpha Gate - Required Gates Passed | `.github/workflows/ci-cd-pipeline.yml` aggregator job. |

## Release Automation Policy

The release mutation boundary remains
`.github/workflows/release-automation.yml` job `preflight-release-gates`.
Required gates run before version mutation, release branch creation, artifact
build, tag creation, GitHub release creation, PyPI publish, and container
publish.

The RC/default release posture is:

- Hyphenated versions are prereleases.
- Prerelease tags must use `release_type=custom`.
- GitHub release creation sets prerelease state from the computed prerelease
  flag.
- Docker latest is emitted only for stable releases.
- `auto_merge=false` is the RC default.

## Disposition

No GitHub repository setting was changed during this phase. Because branch
protection and repository rulesets are absent, the release operator must use
manual enforcement for public-alpha required gates. The active RC/public-alpha
contract remains `v1.2.0-rc5`, while GitHub Latest remains
`v2.15.0-alpha.1`; GitHub Latest must not be used as the RC policy source unless
a later release operation intentionally changes that channel state.
