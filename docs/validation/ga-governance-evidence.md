> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# GA Governance Evidence

## Summary

- Evidence captured: 2026-04-24T18:31:00Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Default branch: `main`.
- Visibility: `PUBLIC`.
- Branch protection: `enabled`.
- Repository rulesets: `none`.
- Enforcement disposition: `enforced via branch protection`.
- Policy accepted by: `repository operator`.
- Historical input evidence: earlier RELGOV/GACLOSE artifacts recorded
  `manual enforcement` before GAGOV applied branch protection.
- Active RC/public-alpha package contract: `v1.2.0-rc5`.
- GitHub Latest: `v2.15.0-alpha.1`.
- Release-channel disposition: GitHub Latest remains excluded from the RC/GA
  policy source until a final GA release changes that channel state.

## Access Probes

| Probe | Result | Non-secret evidence |
|---|---|---|
| `gh auth status` | Authenticated GitHub CLI session available. | `github.com`, account `ViperJuice`, scopes include `repo`. |
| `gh repo view ViperJuice/Code-Index-MCP --json nameWithOwner,defaultBranchRef,visibility,viewerPermission` | Public repository with admin access on `main`. | `nameWithOwner=ViperJuice/Code-Index-MCP`, `defaultBranchRef.name=main`, `visibility=PUBLIC`, `viewerPermission=ADMIN`. |
| `gh api repos/ViperJuice/Code-Index-MCP/branches/main --jq '{name, protected, protection_url}'` | Branch exists and is protected after GAGOV update. | `name=main`, `protected=true`. |
| `gh api repos/ViperJuice/Code-Index-MCP/branches/main/protection` | Branch protection present. | Required status checks `strict`; required review count `1`; dismiss stale reviews `true`; conversation resolution `true`; linear history `true`; enforce admins `true`. |
| `gh api repos/ViperJuice/Code-Index-MCP/rulesets` | No repository rulesets returned. | Empty list. |
| `gh release view v1.2.0-rc5 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url` | Active RC release is published as a prerelease. | `tagName=v1.2.0-rc5`, `isPrerelease=true`, `isDraft=false`, `publishedAt=2026-04-24T02:49:05Z`, `targetCommitish=main`. |
| `gh api repos/ViperJuice/Code-Index-MCP/releases/latest --jq '{tag_name, draft, prerelease, published_at, html_url}'` | GitHub Latest resolves to an older alpha tag. | `tag_name=v2.15.0-alpha.1`, `draft=false`, `prerelease=false`, `published_at=2026-04-05T04:58:39Z`. |

## Required Gates

Gate authority source: `docs/validation/ga-readiness-checklist.md`.

| Required gate | Enforcement surface |
|---|---|
| Alpha Gate - Dependency Sync | Branch protection required status checks on `main`; `.github/workflows/lockfile-check.yml`. |
| Alpha Gate - Format And Lint | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |
| Alpha Gate - Unit And Release Smoke | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |
| Alpha Gate - Integration Smoke | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |
| Alpha Gate - Production Multi-Repo Matrix | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |
| Alpha Gate - Docker Build And Smoke | Branch protection required status checks on `main`; `.github/workflows/container-registry.yml`. |
| Alpha Gate - Docs Truth | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |
| Alpha Gate - Required Gates Passed | Branch protection required status checks on `main`; `.github/workflows/ci-cd-pipeline.yml`. |

## Branch Protection Configuration

- Required status checks: `strict`
- Required pull request reviews: `1 approving review`
- Dismiss stale reviews: `true`
- Require code owner reviews: `false`
- Require last push approval: `false`
- Require conversation resolution: `true`
- Require linear history: `true`
- Enforce for administrators: `true`
- Allow force pushes: `false`
- Allow deletions: `false`
- Block creations: `false`
- Lock branch: `false`
- Allow fork syncing: `false`

## Release Automation Policy

The release mutation boundary remains
`.github/workflows/release-automation.yml` job `preflight-release-gates`.
Required gates run before version mutation, release branch creation, artifact
build, tag creation, GitHub release creation, PyPI publish, and container
publish.

The RC/default release posture remains:

- Hyphenated versions are prereleases.
- Prerelease tags must use `release_type=custom`.
- GitHub release creation sets prerelease state from the computed prerelease
  flag.
- Docker latest is emitted only for stable releases.
- `auto_merge=false` is the RC default.
- GitHub Latest currently points at `v2.15.0-alpha.1` and remains excluded from
  the GA decision path until a final GA release changes that state.

## Operator Response

GAGOV succeeded without a human blocker because metadata-only GitHub probes and
admin repository access were sufficient to apply branch protection directly.

If a later probe shows branch protection drift, a missing required gate
context, or a GitHub product limitation that weakens enforcement, stop release
qualification, refresh this artifact with redacted probe metadata, and route
the blocker through GAGOV/GAOPS before GARC or GAREL attempts any release
mutation.
