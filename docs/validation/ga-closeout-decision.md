> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# GA Closeout Decision

## Summary

- Evidence captured: 2026-04-24T06:10:00Z.
- Repository: `ViperJuice/Code-Index-MCP`.
- Observed commit: `8d08545c15c53322128ef87b5e06308bd8b0dad3`.
- Active RC/public-alpha package contract: `v1.2.0-rc5`.
- Final decision: `stay on RC/public-alpha`.
- Next command: `codex-phase-roadmap-builder specs/phase-plans-v4.md`.

## Source Evidence

| Evidence | Disposition |
|---|---|
| [RC5 Release Evidence](rc5-release-evidence.md) (`docs/validation/rc5-release-evidence.md`) | Release Automation run `24869293713` succeeded; GitHub release, PyPI artifacts, and GHCR image were published for `v1.2.0-rc5`. |
| [Release Governance Evidence](release-governance-evidence.md) (`docs/validation/release-governance-evidence.md`) | Branch protection and repository rulesets were absent; public-alpha required gates remain manually enforced. GitHub Latest points at `v2.15.0-alpha.1` and is not the RC policy source. |
| [Secondary Tool Readiness Evidence](secondary-tool-readiness-evidence.md) (`docs/validation/secondary-tool-readiness-evidence.md`) | `reindex`, `write_summaries`, and `summarize_sample` reject unsafe repository scopes before mutating or summarizing repository state. |

## Post-TOOLRDY Verification

| Command | Timestamp | Result |
|---|---|---|
| `make alpha-production-matrix` | 2026-04-24T05:54:00Z | Result: passed, 93 passed. |
| `make alpha-production-matrix` | 2026-04-24T08:42:57Z | Result: passed, 93 passed. |

The final GACLOSE execution reran this command after public-surface, support
matrix, runbook, and decision-artifact cleanup.

## Rationale

The release evidence proves that `v1.2.0-rc5` is published and usable as the
active RC/public-alpha package contract. The governance evidence still leaves
required gates under manual enforcement, and the support matrix still describes
beta/public-alpha surfaces rather than GA support. TOOLRDY closes a secondary
tool readiness gap, but it does not expand the support tier or create a GA
launch claim.

The evidence therefore supports staying on RC/public-alpha while creating a
separate GA-hardening roadmap. That roadmap should cover enforced governance,
fresh end-to-end production evidence, explicit GA support-tier acceptance, and
any follow-up RC scope needed before a GA decision.

## Decision

Final decision: `stay on RC/public-alpha`.

Do not treat GitHub Latest as the RC policy source. Do not publish GA language
or GA launch instructions from this artifact. If the next workstream pursues GA,
start it with `codex-phase-roadmap-builder specs/phase-plans-v4.md` and keep it
separate from the completed v4 release-cleanup evidence chain.
