---
phase_loop_plan_version: 1
phase: GARECUT
roadmap: specs/phase-plans-v5.md
roadmap_sha256: 6dcfdf73e2fb3403768e168bf6126d367864c94c8f73d6ca2f00da97ad5f6a86
phase_loop_mutation: none
status: retired
---
# GARECUT: Retired Post-Remediation RC Recut

## Disposition

GARECUT is obsolete for the v5 GA-hardening roadmap. It was the contingency
branch for a renewed GAREL decision that required another prerelease soak
before stable dispatch. Renewed GAREL instead selected `ship GA`, and GADISP
successfully published stable `v1.2.0` with release evidence in
`docs/validation/ga-release-evidence.md`.

Do not execute this plan with `codex-execute-phase`, and do not dispatch another
Release Automation prerelease from this artifact.

## Supersession Evidence

- `docs/validation/ga-rc-evidence.md` records the successful `v1.2.0-rc8`
  prerelease recut on the remediated `softprops/action-gh-release@v3` path.
- `docs/validation/ga-final-decision.md` records the renewed GAREL decision to
  ship GA and accepts the GitHub-owned
  `actions/download-artifact@v8` `Buffer()` warning as non-blocking.
- `docs/validation/ga-release-evidence.md` records the successful GADISP stable
  dispatch for `v1.2.0`, including GitHub Release, PyPI, GHCR, rollback, and
  upstream-warning disposition.
- `specs/phase-plans-v5.md` marks GARECUT retired after successful GADISP
  evidence.

## Safe Next Action

Treat v5 as closed after phase-loop state records GARECUT as a retired
contingency. Any future prerelease soak or release-workflow maintenance should
be planned as a new post-GA roadmap item, not as GARECUT execution.

## Verification

```bash
git status --short --branch
uv run pytest tests/docs/test_garecut_rc_recut_contract.py \
  tests/docs/test_garel_ga_release_contract.py \
  tests/test_release_metadata.py -v --no-cov
rg -n "GARECUT|retired|v1\\.2\\.0|ga-release-evidence" \
  specs/phase-plans-v5.md plans/phase-plan-v5-garecut.md docs/validation/ga-release-evidence.md
```
