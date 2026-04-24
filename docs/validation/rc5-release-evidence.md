# RC5 Release Evidence

## Summary

- Evidence captured: 2026-04-23T23:44:50Z.
- Release target: `v1.2.0-rc5`.
- Selected commit: `a6e6b5948f2b101b3504494b935204f03d8344e9`.
- Release Automation run: https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24864227700.
- Final disposition: release dispatch attempted, but publication did not occur because Release Automation failed in `Prepare Release` before branch, release, package, or image creation.
- Rollback disposition: no rollback action taken because no RC5 tag, GitHub release, release PR, PyPI artifact, or GHCR image was created.

## Pre-Dispatch Checks

| Check | Result |
| --- | --- |
| `git status --short --branch` | Clean `main...origin/main`. |
| `git fetch origin main --tags --prune` | Completed successfully. |
| `git rev-parse HEAD origin/main` | Both resolved to `a6e6b5948f2b101b3504494b935204f03d8344e9`. |
| `git tag -l v1.2.0-rc5` | No local tag found. |
| `git ls-remote --tags origin refs/tags/v1.2.0-rc5` | No remote tag found. |
| `gh workflow view "Release Automation"` | Workflow was visible to the GitHub CLI. |

## Dispatch Inputs

Release Automation was dispatched with the frozen RC5 inputs:

- `version=v1.2.0-rc5`
- `release_type=custom`
- `auto_merge=false`

The resulting run ID was `24864227700`, and its `headSha` matched the selected commit.

## Workflow Results

| Job | Result | Notes |
| --- | --- | --- |
| `Preflight Release Gates` | Success | Completed in 8m41s. `Run alpha release gates` succeeded before any release mutation job. |
| `Prepare Release` | Failure | Failed at `Generate Changelog`. |
| `Build Release Artifacts` | Skipped | Downstream of failed prepare job. |
| `Run Release Tests` | Skipped | Downstream of failed prepare job. |
| `Create GitHub Release` | Skipped | No GitHub release was created. |
| `Merge Release Branch` | Skipped | No release branch merge occurred. |
| `Post-Release Tasks` | Skipped | No post-release publication step ran. |

Failure summary from the failed step:

- `Generate Changelog` wrote a multiline value to `$GITHUB_OUTPUT`.
- GitHub Actions rejected the output with `Invalid value. Matching delimiter not found 'EOF'`.

## Publication Checks

| Artifact | Result |
| --- | --- |
| Remote tag `refs/tags/v1.2.0-rc5` | Not found after workflow failure. |
| GitHub release `v1.2.0-rc5` | Not found. |
| PyPI package `index-it-mcp` with pre-releases | `python -m pip index versions index-it-mcp --pre` returned no matching distribution. |
| GHCR image `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5` | Not found. |
| Release PR `release/v1.2.0-rc5` | `gh pr list --head release/v1.2.0-rc5` returned `[]`. |

## Follow-Up

RC5REL remains blocked until the Release Automation changelog output handling fix is committed and the workflow is retried. The safe retry point is before publication: preflight passed, but no release artifacts were created.

The workflow failure was traced to multiline `$GITHUB_OUTPUT` handling in `Generate Changelog`. `git log --pretty=format:"- %s (%an)"` can leave `RELEASE_NOTES.md` without a trailing newline, causing the output delimiter to be appended to the final changelog line instead of appearing on its own line. The local remediation is to append a newline before writing the output and use a per-run delimiter.
