# Comprehensive Hardening V10 Post-Repair Confirmation

## Goal

Confirm that the final repair patch correctly resolves every substantive
finding from the blocking three-agent integration review, plus the gateway
authorization defect exposed by the first canonical post-repair gate.

## Material

- Repository: `/mnt/HC_Volume_105438154/worktrees/Code-Index-MCP-comprehensive-hardening`
- Frozen repair patch: `/tmp/code-index-mcp-hardverify/post-repair.diff`
- Initial review brief: `specs/phase-plans-v10_final_code_review_request.md`
- Reconciliation: `specs/phase-plans-v10_final_code_review.md`
- Final evidence: `docs/status/COMPREHENSIVE_HARDENING_V10.md`

Use read-only local tools. Review the frozen patch and relevant surrounding
code. Do not edit files and do not broaden this into a new comprehensive review.

## Required Checks

1. Container push and signing mutations have adjacent exact-SHA,
   protected-main ancestry, and version guards.
2. STDIO handshake rejection/acceptance occurs before all lazy service and
   request-context initialization.
3. Exact registered repository IDs/names and ambiguous aliases are classified
   before filesystem sandbox checks, while explicit paths remain guarded.
4. Authentication executes before authorization under Starlette's reverse
   middleware wrapping.
5. Readiness integrity caching is bounded, keyed by DB/WAL/SHM identity,
   invalidated on atomic publication, and never caches failures.
6. Pre-publication Docker docs/installers default to a local smoke image rather
   than the unpublished 1.3.1 registry image.
7. The active authorization layer explicitly covers every real gateway route,
   retains stricter overrides for privileged operations, preserves router
   404/405 behavior, and still default-denies a real unlisted route. In
   particular, `/api/v1/security/events` must require admin authorization in
   middleware rather than relying only on its route dependency.

Report only a concrete remaining correctness, security, compatibility, or
release-safety defect in these repairs. For each finding include severity,
exact file/line, trigger and impact, and smallest repair. If all checks are
satisfied, say so explicitly. End the last non-empty line with exactly one
verdict token: `AGREE`, `PARTIALLY AGREE`, or `DISAGREE`. Use `DISAGREE` only
for a blocking remaining defect.
