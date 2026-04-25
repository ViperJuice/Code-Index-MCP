# Production Deployment Guide

This document narrows production guidance to the current evidence-backed,
local-first Code-Index-MCP operator contract. It does not broaden the product
surface beyond what the GA checklist, runbook, and evidence artifacts already
freeze.

## Current production posture

- Product-level posture remains `public-alpha` / `beta`, not `GA`.
- Operators own promotion, rollback, observability, and support triage.
- The supported deployment surfaces are the local checkout, the `index-it-mcp`
  package at `1.2.0-rc8`, and the
  `ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc8` image.
- The authoritative procedure sources are
  `docs/validation/ga-readiness-checklist.md`,
  `docs/operations/deployment-runbook.md`,
  `docs/operations/observability-verification.md`, and
  `docs/validation/ga-operations-evidence.md`.

## Operator-owned production workflow

Use this sequence for production qualification:

1. Review the required gates in `docs/validation/ga-readiness-checklist.md`.
2. Confirm governance posture in `docs/validation/ga-governance-evidence.md`.
3. Confirm release-surface and readiness evidence in
   `docs/validation/ga-e2e-evidence.md`.
4. Run `./scripts/preflight_upgrade.sh /path/to/staging.env`.
5. Run the observability verification procedure.
6. Record the result in `docs/validation/ga-operations-evidence.md`.

## Readiness and topology expectations

Production support remains local-first and operator-owned:

- many unrelated repositories are supported
- one registered worktree per git common directory is supported
- tracked/default branch indexing only
- non-ready repos must fail closed with `index_unavailable` and
  `safe_fallback: "native_search"` until readiness is `ready`

These behaviors are part of the frozen support boundary. They are not optional
operator conventions.

## Rollback and incident handling

Rollback remains mandatory whenever the promoted build regresses gate posture,
readiness behavior, observability, or support-boundary accuracy. Restore the
prior known-good package or image, rerun preflight and observability checks,
and route any contract drift back through GAOPS before GARC or GAREL proceeds.

Incident handling also stays operator-owned. Use the deployment runbook to
classify the issue as governance drift, release-surface drift, readiness drift,
or an out-of-scope support request.

## Support boundary

Use `docs/SUPPORT_MATRIX.md` for support labels:

- `public-alpha`
- `beta`
- `GA`
- `experimental`
- `unsupported`
- `disabled-by-default`

Production evidence must not present unsupported or disabled-by-default paths
as release-backed behavior. The same rule applies to any request that assumes a
hosted control plane rather than the current operator-owned deployment model.
