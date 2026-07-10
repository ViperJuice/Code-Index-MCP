# Comprehensive Hardening V10 Final Code Review

## Goal

Perform an independent, repo-grounded integration review of every change in
`origin/main...HEAD` on branch `codex/comprehensive-hardening-v10` at commit
`2a8efd1`. This is the final blocking review after all eight roadmap phases.

## Material

- Repository: `/mnt/HC_Volume_105438154/worktrees/Code-Index-MCP-comprehensive-hardening`
- Exact patch: `/tmp/code-index-mcp-hardverify/origin-main-to-head.diff`
- Roadmap: `specs/phase-plans-v10.md`
- Final evidence: `docs/status/COMPREHENSIVE_HARDENING_V10.md`
- Phase plans: `plans/phase-plan-v10-*.md`

Open the exact patch and repository files with local read-only tools. Review the
cumulative implementation, not only the final HARDVERIFY commit.

## Review Standard

Report only concrete correctness, security, data-integrity, compatibility,
release-safety, or unmet-acceptance findings. Ignore style preferences and
non-blocking cleanup. For every finding provide:

1. Severity (`P0`, `P1`, or `P2`).
2. Exact file and line.
3. Trigger and user-visible or operational impact.
4. The smallest correct repair and missing regression test.

Explicitly inspect:

- FastAPI default-deny authentication and OpenAPI security metadata.
- STDIO handshake behavior and exact repository selector refusal semantics.
- Missing/corrupt/stale index classification and atomic rebuild recovery.
- Summarization result contracts and call-site compatibility.
- Lazy plugin allocation, RSS accounting, eviction, and signal shutdown.
- Unmarked-network denial, mypy ratchet integrity, and test determinism.
- Release workflow prepare/publish separation, protected-main ancestry guards,
  immutable action pins, prerelease tags, and package version coherence.
- Whether the browser/runtime/package evidence actually proves its claims.

Do not edit files. Do not disclose credentials, environment values, or captured
application logs. If there are no blocking findings, say so explicitly. End the
last non-empty line with exactly one verdict token: `AGREE`,
`PARTIALLY AGREE`, or `DISAGREE`. Use `DISAGREE` only for a blocking defect.
