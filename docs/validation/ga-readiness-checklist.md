> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# GA Readiness Checklist

This is the canonical GABASE checklist for the v5 GA-hardening roadmap. It
freezes the release boundary, support tiers, required gates, evidence map,
rollback expectations, and non-GA surfaces for the current
`v1.2.0-rc5` RC/public-alpha baseline before any GA claim or stable release
mutation.

## Release boundary

- Active baseline: `v1.2.0-rc5` remains the current RC/public-alpha package
  contract across `README.md`, install docs, the support matrix, and operator
  runbooks.
- Follow-up RC target: `v1.2.0-rc6` is the frozen follow-up RC version for
  `GARC`.
- Current release surfaces stay pre-GA: native Python/STDIO via
  `uv sync --locked`, the `index-it-mcp` package, and the
  `ghcr.io/viperjuice/code-index-mcp` container image remain the documented
  RC/public-alpha install paths.
- Repository-topology contract remains unchanged: one registered worktree per
  git common directory, tracked/default branch indexing only, and
  `index_unavailable` with `safe_fallback: "native_search"` until readiness is
  `ready`.
- No GA release mutation, GitHub settings mutation, support expansion, or
  runtime-behavior expansion happens in GABASE.

## Support tiers

The shared support-tier labels for this roadmap are:

- `public-alpha`
- `beta`
- `GA`
- `experimental`
- `unsupported`
- `disabled-by-default`

Current contract notes:

- Product-level release posture remains `public-alpha` / `beta`, not `GA`.
- `docs/SUPPORT_MATRIX.md` remains the canonical support-surface inventory for
  language/runtime, sandbox, extras, and install-surface facts.
- Later phases may only tighten or consume these labels; they must not invent
  alternate tier names.

## Required gates

These are the carried-forward required gates that remain blocking inputs until a
later phase changes governance explicitly:

- `Alpha Gate - Dependency Sync`
- `Alpha Gate - Format And Lint`
- `Alpha Gate - Unit And Release Smoke`
- `Alpha Gate - Integration Smoke`
- `Alpha Gate - Production Multi-Repo Matrix`
- `Alpha Gate - Docker Build And Smoke`
- `Alpha Gate - Docs Truth`
- `Alpha Gate - Required Gates Passed`

GABASE does not change enforcement posture. Required gates remain under manual
enforcement until `GAGOV` records a different disposition.

## Evidence map

### Input evidence

- `docs/validation/rc5-release-evidence.md`
- `docs/validation/release-governance-evidence.md`
- `docs/validation/secondary-tool-readiness-evidence.md`
- `docs/validation/ga-closeout-decision.md`

### Refresh evidence required before a GA ship decision

- `docs/validation/ga-governance-evidence.md` -> `GAGOV`
- `docs/validation/ga-e2e-evidence.md` -> `GAE2E`
- `docs/validation/ga-operations-evidence.md` -> `GAOPS`
- `docs/validation/ga-rc-evidence.md` -> `GARC`
- `docs/validation/ga-final-decision.md` -> `GAREL`
- `docs/validation/ga-release-evidence.md` -> `GAREL`

Input evidence explains the current RC/public-alpha baseline. Refresh evidence
must be regenerated before any later artifact can conclude `ship GA`.

## Rollback expectations

- If a downstream hardening phase fails, fall back to the documented
  `v1.2.0-rc5` RC/public-alpha contract rather than publishing GA wording.
- Rollback instructions continue to live in
  `docs/operations/deployment-runbook.md` until `GAOPS` replaces or tightens
  them with fresh evidence.
- A native-search fallback is acceptable only when the tool returned
  `index_unavailable` with `safe_fallback: "native_search"`; it is runtime
  remediation, not substitute release evidence.
- Follow-up RC or GA work must not widen repository-topology support during
  rollback handling.

## Non-GA surfaces

- Same-repo sibling worktrees and non-default branch indexed routing remain
  outside the supported topology contract.
- Secondary/admin FastAPI behavior remains a secondary surface; STDIO remains
  the primary LLM tool surface.
- Registry coverage, optional extras, semantic providers, reranking, and
  disabled-by-default or unsupported plugin paths must continue to use the
  frozen support-tier labels instead of implicit GA claims.
- No document may claim `ship GA`, `stable release`, or `generally available`
  before `GAREL` records a final `ship GA` decision.
