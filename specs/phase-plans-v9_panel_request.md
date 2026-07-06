# Advisor Panel Request: Phase Roadmap v9

Review `specs/phase-plans-v9.md` as an adversarial roadmap/design review before
implementation begins.

## Operator Decisions To Respect

- The canonical public package/install identity is `index-it-mcp`.
- `code-index-mcp` appears to be a separate/colliding package identity and must
  not be treated as the intended package name without owner-verified evidence.
- Issue #43 is approved only with a local/offloaded CI posture that avoids
  unnecessary GitHub Actions cost.
- Implementation must not begin until this three-agent panel has reviewed the
  roadmap.

## Review Questions

1. Does v9 order the phases correctly for safe public-release cleanup?
2. Are the interface-freeze gates concrete enough for downstream
   `codex-plan-phase` and `codex-execute-phase` work?
3. Does the local/offloaded CI design avoid GitHub-hosted compute creep while
   still preserving trustworthy coverage evidence?
4. Are any issues incorrectly consolidated, delayed, or missing?
5. What changes, if any, should be made to the roadmap before implementation?

## Required Output

Give a concise but substantive review with:

- blockers that must be fixed before implementation;
- non-blocking improvements;
- recommended phase-order changes, if any;
- final recommendation.
