> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# RC5 Release Evidence

## Summary

- Evidence captured: 2026-04-24T02:51:46Z.
- Release target: `v1.2.0-rc5`.
- Final Release Automation run: https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24869293713.
- Final workflow source commit: `756bd1739bd4c9b62558f1a675f4d47817a58525`.
- Final disposition: RC5 release workflow succeeded; GitHub release, PyPI artifacts, and GHCR image are published.
- Rollback disposition: no rollback action taken.

## Attempt History

| Run | Source commit | Result | Disposition |
| --- | --- | --- | --- |
| `24864227700` | `a6e6b5948f2b101b3504494b935204f03d8344e9` | Failure | `Prepare Release` failed at `Generate Changelog`; no tag, release, PR, PyPI artifact, or GHCR image was created. |
| `24869046385` | `d656deca9822364eac9aeac1054b80f46d456724` | Failure | `Preflight Release Gates` failed because `tests/test_p25_release_gates.py` needed Black formatting; no release mutation occurred. |
| `24869100817` | `4d99e5b689a1077c4499397b5c8f06c0b8da44f2` | Failure | `Preflight Release Gates` failed because this evidence file was missing the historical banner and triage row required for `docs/validation/*.md`; no release mutation occurred. |
| `24869293713` | `756bd1739bd4c9b62558f1a675f4d47817a58525` | Success | Release Automation completed successfully. |

## Pre-Dispatch Checks

The final dispatch was made only after:

| Check | Result |
| --- | --- |
| `git status --short --branch` | Clean `main...origin/main`. |
| `git fetch origin main --tags --prune` | Completed successfully. |
| `git rev-parse HEAD origin/main` | Both resolved to `756bd1739bd4c9b62558f1a675f4d47817a58525`. |
| `git tag -l v1.2.0-rc5` | No local tag found before final dispatch. |
| `git ls-remote --tags origin refs/tags/v1.2.0-rc5` | No remote tag found before final dispatch. |
| `gh workflow view "Release Automation"` | Workflow was visible to the GitHub CLI. |

## Dispatch Inputs

Release Automation was dispatched with the frozen RC5 inputs:

- `version=v1.2.0-rc5`
- `release_type=custom`
- `auto_merge=false`

The successful run ID was `24869293713`, and its `headSha` matched the selected source commit `756bd1739bd4c9b62558f1a675f4d47817a58525`.

## Workflow Results

| Job | Result | Notes |
| --- | --- | --- |
| `Preflight Release Gates` | Success | Completed in 8m40s. |
| `Prepare Release` | Success | Generated changelog, updated `CHANGELOG.md`, committed version changes, and created the release branch. |
| `Run Release Tests` | Success | Release smoke tests and version consistency checks passed. |
| `Build Release Artifacts` | Success | Built Python artifacts, pushed Docker images, generated SBOM, and uploaded artifacts. |
| `Create GitHub Release` | Success | Created and pushed the tag, created GitHub release, and published to PyPI. |
| `Post-Release Tasks` | Success | Documentation update and deployment trigger steps completed; Slack notification was skipped. |
| `Merge Release Branch` | Success | Pull-request creation step completed; auto-merge was skipped because `auto_merge=false`. |

## Artifact Identity

| Artifact | Result |
| --- | --- |
| Remote tag `refs/tags/v1.2.0-rc5` | Present. Annotated tag object `fe2847ff8b0192cdb0187f77f6e32b7d23bbd8ab`; peeled commit `3db5aebb965c65adaddedc3e1eadc6e49d06a02f`. |
| Tag target commit | `3db5aebb965c65adaddedc3e1eadc6e49d06a02f` (`chore: bump version to v1.2.0-rc5`). |
| GitHub release `v1.2.0-rc5` | Published at 2026-04-24T02:49:05Z, prerelease, not draft. URL: https://github.com/ViperJuice/Code-Index-MCP/releases/tag/v1.2.0-rc5. |
| GitHub release assets | `CHANGELOG.md`, `DEPLOYMENT-GUIDE.md`, `index_it_mcp-1.2.0rc5-py3-none-any.whl`, `index_it_mcp-1.2.0rc5.tar.gz`, `sbom.spdx.json`. |
| PyPI package `index-it-mcp` | PyPI JSON exposes release `1.2.0rc5` with wheel and sdist uploaded at 2026-04-24T02:49:16Z and 2026-04-24T02:49:19Z; neither file is yanked. |
| GHCR image `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5` | Present. OCI index digest `sha256:ab8eba55e65836aa207cea71b781029f45eb7b43b242d3ee6fc911e34a8f52d7`; linux/amd64 and linux/arm64 manifests are present. |
| Release branch `release/v1.2.0-rc5` | Present, currently identical to `main` at `756bd1739bd4c9b62558f1a675f4d47817a58525`. |
| Release PR | No open or closed PR found for `ViperJuice:release/v1.2.0-rc5`; the workflow's pull-request step completed with no separate PR surfaced by the GitHub API. |

## Tag-Triggered Runs

`CI/CD Pipeline` and `Container Registry Management` both include `push.tags: v*`, but no separate tag-triggered runs for `v1.2.0-rc5` were returned by `gh run list` after the tag was created. The release workflow created the tag with GitHub Actions credentials, so downstream workflow suppression is the likely explanation. The release workflow itself still completed the release-gate tests and container image publication.

Main-branch push runs for `756bd1739bd4c9b62558f1a675f4d47817a58525` completed successfully before the final dispatch:

- CI/CD Pipeline: https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24869289517.
- Container Registry Management: https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24869289515.

## Notes

`python -m pip index versions index-it-mcp --pre` did not list the package, but PyPI JSON for `index-it-mcp` showed `1.2.0rc5` and both published files. Use the PyPI JSON/API evidence for this RC5 publication check.
