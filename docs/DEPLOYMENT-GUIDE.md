# Code-Index-MCP Deployment Guide

This guide describes the supported deployment surfaces for the current
Code-Index-MCP local-first product contract. It is not a managed-service or
orchestrator handbook. Operators remain responsible for environment setup,
promotion, rollback, observability, and repo-readiness remediation.

## Supported deployment surfaces

The supported deployment surfaces are:

- local checkout plus `uv sync --locked`
- the published package `index-it-mcp`
- the container image `ghcr.io/viperjuice/code-index-mcp`

These are the only supported deployment surfaces referenced by the GAOPS
operator path. For executable procedures, use:

- `docs/validation/ga-readiness-checklist.md`
- `docs/operations/deployment-runbook.md`
- `docs/operations/observability-verification.md`
- `docs/validation/ga-operations-evidence.md`

## Operator-owned responsibilities

This repository remains local-first and operator-owned. Operators own:

- environment preparation and dependency installation
- release qualification against the required gates
- preflight execution with `./scripts/preflight_upgrade.sh /path/to/staging.env`
- observability verification, rollback, and incident handling
- repo registration, allowed-roots policy, reindex, and readiness remediation

The topology contract remains: many unrelated repositories, one registered
worktree per git common directory, tracked/default branch indexing only, and
`index_unavailable` with `safe_fallback: "native_search"` until readiness is
`ready`.

## Release and support posture

The product-level posture remains `public-alpha` / `beta`, not `GA`.
Row-level support facts live in `docs/SUPPORT_MATRIX.md`, using the shared
labels `public-alpha`, `beta`, `GA`, `experimental`, `unsupported`, and
`disabled-by-default`.

## Qualification and rollback

Before promotion, operators should:

1. confirm the required gate set from the checklist
2. review `docs/validation/ga-governance-evidence.md`
3. review `docs/validation/ga-e2e-evidence.md`
4. run the GAOPS preflight and observability procedures

Rollback stays environment-specific but always remains operator-owned. If the
promoted build weakens readiness, observability, or support-boundary behavior,
restore the prior known-good package or image, rerun preflight, and record the
result in `docs/validation/ga-operations-evidence.md`.

## Unsupported assumptions

This guide intentionally does not promise hosted repair flows, delegated index
ownership, or infrastructure automation beyond the evidence-backed operator
path in the runbook. If your environment depends on broader infrastructure
patterns, treat that as out of scope for the current GAOPS contract and keep it
out of release evidence.
