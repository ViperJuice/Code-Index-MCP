> **Historical artifact — as-of 2026-04-24, may not reflect current behavior**

# GA Operations Evidence

## Summary

- Evidence captured: 2026-04-24T19:30:00Z.
- Observed commit: `8d08545c15c53322128ef87b5e06308bd8b0dad3`.
- Phase plan: `plans/phase-plan-v5-gaops.md`.
- Canonical upstream sources:
  `docs/validation/ga-readiness-checklist.md`,
  `docs/validation/ga-governance-evidence.md`,
  `docs/validation/ga-e2e-evidence.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/observability-verification.md`.
- Scope: freeze the GAOPS operator path for `deployment preflight`,
  `deployment qualification`, `rollback`, `index rebuild`,
  `incident response`, and `support triage`.

## Procedure Validation Matrix

| Procedure | Validation mode | Source | Disposition |
|---|---|---|---|
| `deployment preflight` | `local` | `./scripts/preflight_upgrade.sh /path/to/staging.env` contract plus `scripts/preflight_upgrade.sh` | The operator path now requires an explicit env-file argument and records warning-only output as evidence rather than silent success. |
| `deployment qualification` | `metadata-only` | `docs/operations/deployment-runbook.md`, `docs/validation/ga-governance-evidence.md`, `docs/validation/ga-e2e-evidence.md` | Qualification is defined as a reduction over frozen gate, governance, E2E, and observability inputs; no release mutation occurs in GAOPS. |
| `rollback` | `metadata-only` | `docs/operations/deployment-runbook.md` | Rollback remains environment-specific but operator-owned, and later phases must preserve that boundary. |
| `index rebuild` | `metadata-only` | `docs/operations/deployment-runbook.md`, `docs/validation/ga-e2e-evidence.md` | Rebuild and readiness remediation keep the fail-closed vocabulary; `safe_fallback: "native_search"` remains remediation, not release evidence. |
| `incident response` | `metadata-only` | `docs/operations/deployment-runbook.md`, `docs/operations/observability-verification.md` | Incidents are classified through governance, release-surface, readiness, and support-boundary drift before any downstream release phase proceeds. |
| `support triage` | `metadata-only` | `docs/operations/deployment-runbook.md`, `docs/SUPPORT_MATRIX.md` | Triage remains bounded to supported deployment surfaces and the frozen support labels. |
| `observability verification` | `CI` | `tests/integration/obs/test_obs_smoke.py`, `docs/operations/observability-verification.md` | The smoke remains the CI-backed contract for JSON logs, authenticated metrics, and redaction behavior. |

## Supported Deployment Surface

The supported deployment surface is local-first and operator-owned:

- local checkout plus `uv sync --locked`
- the published package `index-it-mcp`
- the image `ghcr.io/viperjuice/code-index-mcp`

The production boundary still preserves the v3 topology contract: many
unrelated repositories, one registered worktree per git common directory,
tracked/default branch indexing only, and `safe_fallback: "native_search"`
until readiness is `ready`.

## Remaining Limitations

- GAOPS does not prove final release disposition; it only defines the operator
  path that later GARC and GAREL must consume.
- Qualification and rollback remain environment-specific and operator-owned.
- Non-ready repositories still fail closed; native search is remediation only.
- Unsupported or disabled-by-default support-matrix rows remain outside the
  release-backed surface.

## Verification

Planned or passed validation sources for this artifact:

```bash
uv run pytest tests/docs/test_gaops_operations_contract.py -v --no-cov
```
