# Advisor Panel Request: Phase Roadmap v10

Review `specs/phase-plans-v10.md` as an adversarial architecture and execution
roadmap before any implementation begins.

## Required Panel

- GPT-5.5 through the Codex leg
- Gemini 3.1 Pro through the Gemini leg
- Fable (`claude-fable-5`) through the Claude leg

## Operator Intent To Respect

- Fix every confirmed repository-review gap and bug, not only the P0.
- Reconcile panel recommendations before implementation.
- Execute the reconciled roadmap end to end.
- Preserve STDIO as primary and FastAPI as the secondary admin surface.
- Avoid broad indexing and external release dispatch during hardening.
- Prepare a coherent patch release only after release automation is made safe.

## Review Questions

1. Are all ten confirmed findings mapped to a phase and machine-checkable exit gate?
2. Are the phase boundaries and serial dependencies justified, or should any phase
   split, merge, or reorder before planning?
3. Are the authentication, repository-selector, readiness, and reindex contracts
   fail-closed and complete?
4. Is the proposed plugin lifecycle contract strong enough to prevent fleet-scale
   subprocess and child-RSS growth without weakening sandbox isolation?
5. Is requiring zero `mypy` errors for `mcp_server` appropriate, or should the
   roadmap use a stricter incremental gate with an explicit bounded legacy debt plan?
6. Does the release topology guarantee merged-main reachability before every
   external mutation?
7. Are browser, MCP, package, and worker-lifecycle verification sufficient?
8. What blockers must be amended before implementation?

## Required Output

End with exactly one of `AGREE`, `PARTIALLY AGREE`, or `DISAGREE`, and include:

- blocking roadmap amendments;
- non-blocking improvements;
- missing acceptance tests or evidence;
- recommended phase-order changes;
- explicit implementation recommendation.
