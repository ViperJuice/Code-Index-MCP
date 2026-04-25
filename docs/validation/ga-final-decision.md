> **Historical artifact — as-of 2026-04-24, may not reflect current behavior**

# GA Final Decision

## Summary

- Evidence captured: `2026-04-24T23:17:04Z`.
- Original decision phase plan: `plans/phase-plan-v5-garel.md`.
- Original final decision: `cut another RC`.
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
  `docs/validation/ga-operations-evidence.md` remain prerelease-path evidence
  for the historical `v1.2.0-rc6` release contract; they do not independently
  authorize stable mutation.
- `docs/validation/ga-rc-evidence.md` now records the `v1.2.0-rc7` GARECUT
  recut attempt as `blocked before dispatch` while preserving the historical
  `v1.2.0-rc6` soak that motivated the recut.

## Workflow Runtime Disposition

The GARC soak recorded this warning in the `Merge Release Branch` job log:

- `Node 20` runtime warning persisted on the historical GARC path.
- `Node.js 20 actions are deprecated.`
- Affected action: `peter-evans/create-pull-request@v7`.

GAREL remediated the workflow by updating
`.github/workflows/release-automation.yml` to
`peter-evans/create-pull-request@v8`, which is the Node 24-capable line.
That removes the known deprecated runtime path from the workflow source, but it
also means the previously soaked `v1.2.0-rc6` release did not exercise the
current release workflow contract. The updated release workflow requires
another prerelease soak before a stable GA dispatch can be defended.

## Final Decision

`cut another RC`

Rationale:

- The successful `v1.2.0-rc6` soak proves the old prerelease workflow path, not
  the remediated one.
- Shipping GA immediately after changing the release workflow would skip the
  roadmap's required prerelease-soak evidence on the actual workflow that would
  own the stable release.
- Public docs, support-tier language, install defaults, and package metadata
  remain on the `v1.2.0-rc6` prerelease/public-alpha-or-beta posture, so there
  is no stable channel drift to unwind.
- GitHub Latest still points at `v2.15.0-alpha.1`, and no `v1.2.0` tag,
  stable GitHub release, stable PyPI release evidence, or Docker `latest`
  verification was generated in this phase.

Because the decision is not `ship GA`, no stable release mutation was
performed, `docs/validation/ga-release-evidence.md` remains intentionally
absent, and all stable-channel changes stay blocked.

## GARECUT Status

- Current recut target: `v1.2.0-rc7`
- Current recut outcome: `blocked before dispatch`
- Current readiness for renewed GAREL: `not ready`

The recut stopped before `gh workflow run` because the release-affecting
worktree was dirty, even though `HEAD` matched `origin/main`, the remediated
workflow was visible, and `v1.2.0-rc7` was unused locally and remotely.

A renewed GAREL reduction should happen only after fresh `v1.2.0-rc7` evidence
exists. Until then, the correct next step is to rerun GARECUT after the
release-affecting worktree is made clean enough for release mutation.

## Next Scope

The roadmap remains on the existing downstream phase:

- Roadmap artifact: `specs/phase-plans-v5.md`

- Phase 8: `Post-Remediation RC Recut (GARECUT)`

That phase must:

- freeze the next prerelease tag after `v1.2.0-rc6`,
- soak Release Automation on the remediated
  `peter-evans/create-pull-request@v8` workflow path,
- record fresh `v1.2.0-rc7` RC evidence on the remediated workflow contract,
  and
- only then reopen a renewed GAREL ship/no-ship reduction.

Any older downstream plan that assumed GAREL was terminal without this recut is
stale after the roadmap amendment, and the repo is not yet ready for that
renewed GAREL phase.

## Verification

```bash
uv run pytest tests/docs/test_garel_ga_release_contract.py -v --no-cov
uv run pytest tests/docs/test_garecut_rc_recut_contract.py -v --no-cov
uv run pytest tests/test_release_metadata.py -v --no-cov
git status --short --branch
git fetch origin main --tags --prune
git rev-parse HEAD origin/main
git tag -l v1.2.0-rc7
git ls-remote --tags origin refs/tags/v1.2.0-rc7
gh workflow view "Release Automation"
```
