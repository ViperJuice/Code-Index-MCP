> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# GA Final Decision

## Summary

- Evidence captured: `2026-04-25T12:36:07Z`.
- Executed decision phase plan: `plans/phase-plan-v5-garel.md`.
- Final decision: `defer GA`.
- Stable GA dispatch: `not authorized`.
- Stable release evidence artifact: `docs/validation/ga-release-evidence.md`
  remains intentionally absent because no GA release was attempted.

## Decision Inputs

This decision still reduces the canonical GA-hardening inputs:

- `docs/validation/ga-readiness-checklist.md`
- `docs/validation/ga-governance-evidence.md`
- `docs/validation/ga-e2e-evidence.md`
- `docs/validation/ga-operations-evidence.md`
- `docs/validation/ga-rc-evidence.md`

Evidence summary:

- `docs/validation/ga-governance-evidence.md` still records enforced branch
  protection on `main` and keeps GitHub Latest excluded from the prerelease
  policy source until a final GA release changes that state.
- `docs/validation/ga-e2e-evidence.md` and
  `docs/validation/ga-operations-evidence.md` remain prerelease-path evidence.
  They support GA evaluation, but they do not independently authorize stable
  mutation.
- `docs/validation/ga-rc-evidence.md` now records the `v1.2.0-rc8` GARECUT
  recut as `recut succeeded` while preserving the earlier successful
  `v1.2.0-rc7` recut as historical evidence.
- This GAREL execution rechecked the remaining workflow-runtime warning against
  the live `actions/download-artifact` release line. As of 2026-04-25, GitHub
  still publishes `actions/download-artifact` `v8.0.1` (published
  2026-03-11T15:44:25Z), and the successful `v1.2.0-rc8` release run still
  emitted the same `Buffer()` deprecation from the current `@v8` line.

## Workflow Runtime Disposition

The historical GARC soak recorded a Node 20 warning on the old
`peter-evans/create-pull-request@v7` path. GARECUT later proved that path was
successfully remediated during run `24919438766`, but the same run surfaced a
new GitHub Actions deprecation annotation in `Create GitHub Release` for
`softprops/action-gh-release@v2`.

This GAREL execution remediated that remaining warning by updating
`.github/workflows/release-automation.yml` to
`softprops/action-gh-release@v3`, the current Node 24-capable release line.
That is the correct repair for the workflow runtime, but it means the release
path that would own a stable GA dispatch has changed again and has not yet been
soaked on a prerelease candidate.

GARECUT then provided a fresh prerelease soak through successful run
`24923402398`, release `v1.2.0-rc8`, PyPI package `1.2.0rc8`, and the matching
GHCR image. That cleared the specific `softprops/action-gh-release@v3` soak
requirement. However, the same successful `Create GitHub Release` job emitted a
new non-fatal runtime warning from `actions/download-artifact@v8`:
`Buffer()` deprecation.

This phase revalidated that warning against GitHub's current published action
metadata instead of assuming the repo pin was stale. The workflow already uses
`actions/download-artifact@v8`, GitHub's latest published release is still
`v8.0.1`, and no repo-local workflow change landed in this phase that would
exercise a meaningfully different artifact-download path.

That means the remaining warning is not evidence that one more prerelease soak
would answer a new question. Another RC on the same artifact-download line
would likely reproduce the same warning, while stable GA dispatch remains
downstream-only and is not owned by this phase. The warning therefore remains an
unresolved workflow-runtime concern, but it is now classified as a roadmap
steering blocker rather than a reason to cut another identical RC immediately.

## Final Decision

`defer GA`

Rationale:

- Successful `v1.2.0-rc8` evidence already exists for the current
  `softprops/action-gh-release@v3` path.
- GitHub's latest published `actions/download-artifact` release remains
  `v8.0.1`, and the repo is already on `actions/download-artifact@v8`.
- The surviving `Buffer()` deprecation therefore appears on the current
  artifact-download line rather than on an obviously stale repo pin.
- Another prerelease soak without a workflow-artifact transport change would
  likely reproduce the same warning and would not materially reduce GA risk.
- This phase can disposition the blocker, but it does not own a separate
  workflow-runtime remediation lane or the downstream stable dispatch itself.
- GitHub Latest still points at `v2.15.0-alpha.1`, and no `v1.2.0` tag,
  stable GitHub release, stable PyPI release evidence, or Docker `latest`
  verification was generated in this phase.

Because the decision is not `ship GA`, no stable release mutation was
performed, `docs/validation/ga-release-evidence.md` remains intentionally
absent, and all stable-channel changes stay blocked.

## GARECUT Status

- Previous recut target: `v1.2.0-rc7`
- Previous recut outcome: `recut succeeded`
- Current recut target: `v1.2.0-rc8`
- Current recut outcome: `recut succeeded`
- Current readiness: `ready for renewed GAREL planning`

The prior recut dispatched and completed successfully on
`https://github.com/ViperJuice/Code-Index-MCP/actions/runs/24919438766`,
published prerelease `v1.2.0-rc7`, pushed the multi-arch GHCR image, and
published the `1.2.0rc7` wheel plus sdist to PyPI.

The current rc8 recut dispatched from clean pre-dispatch state on
`d2560e95f1b4e7d52eacb025d592275e4b48a084`, completed successfully on run
`24923402398`, published prerelease `v1.2.0-rc8`, uploaded
`index_it_mcp-1.2.0rc8` wheel plus sdist to PyPI, and pushed the multi-arch
GHCR image. The merge job left no new release PR open because the release
branch no longer differed from `main`.

That advances the repository beyond the old rerun state: the
`softprops/action-gh-release@v3` path is now soaked. The remaining
release-runtime follow-up is the `actions/download-artifact@v8` `Buffer()`
deprecation warning observed in the successful `Create GitHub Release` job.

## Next Scope

The roadmap now records that existing downstream `ship GA` and `cut another RC`
plans are both blocked by the unresolved artifact-download warning:

- Roadmap artifact: `specs/phase-plans-v5.md`
- Nearest downstream phase boundary: `GADISP`
- Downstream disposition: `roadmap extension required before GADISP or GARECUT`

The next roadmap work must:

- decide whether a future phase will remediate the workflow-artifact transport
  path, explicitly accept the remaining `actions/download-artifact@v8`
  `Buffer()` warning as non-blocking, or wait for an upstream GitHub fix,
- keep GitHub Latest and Docker `latest` stable-only until a deliberate GA
  release changes those channels, and
- avoid reusing the current `GADISP` or `GARECUT` plans until the roadmap is
  extended with that explicit warning-disposition owner.

Any older downstream `GADISP` or `GARECUT` plan that predates this roadmap
amendment is stale and must not be treated as authoritative.

## Verification

```bash
uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov
uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
uv run pytest tests/docs/test_garc_rc_soak_contract.py -v --no-cov
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc8
git ls-remote --tags origin refs/tags/v1.2.0-rc8
gh workflow view "Release Automation"
gh run view 24923402398 --json url,headSha,status,conclusion,jobs
gh run view 24923402398 --job 72989683995 --log
gh release view v1.2.0-rc8 --repo ViperJuice/Code-Index-MCP --json tagName,isPrerelease,isDraft,publishedAt,targetCommitish,url,assets
curl -sSf https://pypi.org/pypi/index-it-mcp/1.2.0rc8/json
docker buildx imagetools inspect ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8
```
