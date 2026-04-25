> **Historical artifact — as-of 2026-04-25, may not reflect current behavior**

# GA Final Decision

## Summary

- Evidence captured: `2026-04-25T03:40:00Z`.
- Executed decision phase plan: `plans/phase-plan-v5-garel.md`.
- Final decision: `cut another RC`.
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
- This GAREL execution remediated the remaining `Create GitHub Release`
  Node 20 warning by upgrading `softprops/action-gh-release@v2` to
  `softprops/action-gh-release@v3`, which shifts the release workflow again and
  requires one more prerelease soak before GA can be reduced safely.

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

GARECUT has now provided that fresh prerelease soak through successful run
`24923402398`, release `v1.2.0-rc8`, PyPI package `1.2.0rc8`, and the matching
GHCR image. That clears the specific `softprops/action-gh-release@v3` soak
requirement. However, the same successful `Create GitHub Release` job emitted a
new non-fatal runtime warning from `actions/download-artifact@v8`:
`Buffer()` deprecation. Renewed GAREL must disposition that warning before any
future `ship GA` path is authorized.

## Final Decision

`cut another RC`

Rationale:

- Fresh `v1.2.0-rc7` evidence exists for the remediated
  `peter-evans/create-pull-request@v8` path.
- This GAREL execution changed the release workflow again by moving
  `softprops/action-gh-release` from `@v2` to `@v3`.
- Shipping GA immediately after that workflow remediation would skip the
  roadmap's required prerelease-soak evidence on the actual release path that
  would own stable `v1.2.0`.
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
`softprops/action-gh-release@v3` path is now soaked, so the immediate next step
is renewed GAREL planning. The remaining release-runtime follow-up is the new
`actions/download-artifact@v8` `Buffer()` deprecation warning observed in the
successful `Create GitHub Release` job.

## Next Scope

The roadmap now routes to the nearest downstream phase with amended steering:

- Roadmap artifact: `specs/phase-plans-v5.md`
- Phase 7: `GA Decision and Release (GAREL)` as a renewed downstream reducer on
  top of successful `v1.2.0-rc8` evidence.

That renewed phase must:

- reduce the refreshed `v1.2.0-rc8` prerelease evidence instead of reusing the
  stale blocked-run assumption,
- disposition the newly observed `actions/download-artifact@v8`
  `Buffer()` deprecation warning before any `ship GA` path is allowed,
- keep GitHub Latest and Docker `latest` stable-only until a deliberate GA
  release changes those channels, and
- either authorize GA with explicit release evidence or return to another RC /
  defer-GA decision with the new runtime warning accounted for.

Any older downstream GARECUT or GAREL plan that predates this roadmap
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
